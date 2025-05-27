"""
템플릿 섹션 - 메시지 템플릿 관리
"""
from typing import List, Dict, Any, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QListWidget, QListWidgetItem, QFrame, QSplitter,
    QCheckBox, QComboBox, QLineEdit, QGridLayout, QGroupBox,
    QFormLayout, QFileDialog, QSpacerItem, QSizePolicy,
    QTextEdit, QTabWidget, QTreeWidget, QTreeWidgetItem, QMessageBox,
    QTableWidget, QTableWidgetItem, QHeaderView
)
from PySide6.QtCore import Qt, Signal, QSize, QTimer
from PySide6.QtGui import QFont, QColor

from core.types import LogType, OrderType, FboOperationType, SboOperationType
from ui.sections.base_section import BaseSection
from ui.theme import get_theme
from core.config import ConfigManager
from ui.components.log_widget import LOG_INFO, LOG_DEBUG, LOG_WARNING, LOG_ERROR, LOG_SUCCESS
from services.template.template_service import TemplateService
from ui.components.condition_dialog import ConditionDialog
from services.api_service import ApiService
from core.constants import DEFAULT_ORDER_DETAILS_FORMAT, API_FIELDS, DELIVERY_METHODS, LOGISTICS_COMPANIES
import random
from datetime import datetime
from collections import Counter

class TemplateSection(BaseSection):
    """
    템플릿 섹션 - 메시지 템플릿 관리
    """
    
    def __init__(self, parent=None):
        super().__init__("템플릿 관리", parent)
        
        # 템플릿 서비스 초기화
        self.template_service = TemplateService()
        
        # 저장 버튼 추가
        self.save_button = self.add_header_button("저장", self._on_save_clicked, primary=True)
        
        # 콘텐츠 설정
        self.setup_content()
        
        # 현재 선택된 템플릿 정보
        self._current_order_type = None
        self._current_operation_type = None
    
    def setup_content(self):
        """콘텐츠 설정"""
        # 메인 스플리터 생성 (수평)
        main_splitter = QSplitter(Qt.Horizontal)
        
        # 왼쪽 패널 (템플릿 네비게이션)
        self._setup_left_panel(main_splitter)
        
        # 오른쪽 패널 (탭 기반 편집 영역)
        self._setup_right_panel(main_splitter)
        
        # 스플리터 크기 설정 (왼쪽:오른쪽 = 20%:80%)
        main_splitter.setSizes([250, 1000])
        
        # 메인 레이아웃에 스플리터 추가
        self.content_layout.addWidget(main_splitter)
        
        # 스플리터 크기를 위젯이 표시된 후에 설정
        QTimer.singleShot(0, self._set_initial_splitter_sizes)
    
    def _setup_left_panel(self, parent_splitter):
        """왼쪽 패널 설정 - 템플릿 네비게이션"""
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(5, 5, 5, 5)
        
        # 템플릿 트리 위젯
        self.template_tree = QTreeWidget()
        self.template_tree.setHeaderHidden(True)
        self.template_tree.setColumnCount(1)
        self.template_tree.setSelectionMode(QTreeWidget.SingleSelection)
        
        # 트리 아이템 생성
        self._populate_template_tree()
        
        # 템플릿 선택 이벤트 연결
        self.template_tree.itemClicked.connect(self._on_template_selected)
        
        left_layout.addWidget(QLabel("템플릿 목록"))
        left_layout.addWidget(self.template_tree)
        
        # 템플릿 관리 버튼들
        button_layout = QVBoxLayout()
        
        new_template_btn = QPushButton("새 템플릿")
        new_template_btn.clicked.connect(self._on_new_template_clicked)
        button_layout.addWidget(new_template_btn)
        
        copy_template_btn = QPushButton("템플릿 복사")
        copy_template_btn.clicked.connect(self._on_copy_template_clicked)
        button_layout.addWidget(copy_template_btn)
        
        delete_template_btn = QPushButton("템플릿 삭제")
        delete_template_btn.clicked.connect(self._on_delete_template_clicked)
        button_layout.addWidget(delete_template_btn)
        
        left_layout.addLayout(button_layout)
        left_layout.addStretch()
        
        parent_splitter.addWidget(left_panel)
    
    def _setup_right_panel(self, parent_splitter):
        """오른쪽 패널 설정 - 탭 기반 편집 영역"""
        # 탭 위젯 생성
        self.tab_widget = QTabWidget()
        
        # 기본 설정 탭
        self._setup_basic_tab()
        
        # 조건부 템플릿 탭
        self._setup_conditions_tab()
        
        # 미리보기 탭
        self._setup_preview_tab()
        
        parent_splitter.addWidget(self.tab_widget)
    
    def _setup_basic_tab(self):
        """기본 설정 탭 설정"""
        basic_tab = QWidget()
        basic_layout = QVBoxLayout(basic_tab)
        basic_layout.setContentsMargins(10, 10, 10, 10)
        
        # 상단: 기본 정보
        info_layout = QFormLayout()
        info_layout.setSpacing(10)
        
        # 템플릿 제목
        self.template_title = QLineEdit()
        self.template_title.setPlaceholderText("템플릿 제목을 입력하세요")
        info_layout.addRow("제목:", self.template_title)
        
        # 템플릿 설명
        self.template_description = QLineEdit()
        self.template_description.setPlaceholderText("템플릿 설명을 입력하세요 (선택사항)")
        info_layout.addRow("설명:", self.template_description)
        
        basic_layout.addLayout(info_layout)
        
        # 하단: 편집 영역 (수직 스플리터)
        edit_splitter = QSplitter(Qt.Vertical)
        
        # 템플릿 내용 편집기
        content_group = QGroupBox("템플릿 내용")
        content_layout = QVBoxLayout(content_group)
        
        self.template_content = QTextEdit()
        self.template_content.setMinimumHeight(150)
        self.template_content.setPlaceholderText(
            "템플릿 내용을 입력하세요.\n\n"
            "사용 가능한 변수 예시:\n"
            "- {store_name}: 판매자명\n"
            "- {order_details}: 주문 상세 정보\n"
            "- {pickup_at}: 출고일\n"
            "기타 변수는 하단 변수 목록을 참고하세요."
        )
        content_layout.addWidget(self.template_content)
        edit_splitter.addWidget(content_group)
        
        # 주문 상세 정보 형식 편집기
        order_details_group = QGroupBox("주문 상세 정보 형식")
        order_details_layout = QVBoxLayout(order_details_group)
        
        self.order_details_format = QTextEdit()
        self.order_details_format.setMinimumHeight(100)
        self.order_details_format.setPlaceholderText(
            "주문 상세 정보 형식을 설정하세요.\n\n"
            "기본 형식 예시:\n"
            "[{quality_name}] | #{color_number} | {quantity}yd | {pickup_at} | {delivery_method}-{logistics_company}\n\n"
            "사용 가능한 변수:\n" +
            f"- {{{API_FIELDS['ID']}}}: ID\n" +
            f"- {{{API_FIELDS['STORE_NAME']}}}: 판매자명\n" +
            f"- {{{API_FIELDS['QUALITY_NAME']}}}: 퀄리티명\n" +
            f"- {{{API_FIELDS['COLOR_NUMBER']}}}: 컬러순서\n" +
            f"- {{{API_FIELDS['COLOR_CODE']}}}: 컬러코드\n" +
            f"- {{{API_FIELDS['QUANTITY']}}}: 수량\n" +
            f"- {{{API_FIELDS['PURCHASE_CODE']}}}: 발주번호\n" +
            f"- {{{API_FIELDS['PICKUP_AT']}}}: 출고일\n" +
            f"- {{{API_FIELDS['DELIVERY_METHOD']}}}: 배송방법\n" +
            f"- {{{API_FIELDS['LOGISTICS_COMPANY']}}}: 택배사\n" +
            "- {order_index}: 주문 순서\n" +
            "- {total_orders}: 전체 주문 수\n" +
            "- {product_index}: 상품 순서\n" +
            "- {total_products}: 전체 상품 수"
        )
        order_details_layout.addWidget(self.order_details_format)
        edit_splitter.addWidget(order_details_group)
        
        # 스플리터 크기 설정 (템플릿 내용:주문 상세 = 60%:40%)
        edit_splitter.setSizes([300, 200])
        basic_layout.addWidget(edit_splitter)
        
        # 변수 정보 표시
        variables_group = QGroupBox("사용 가능한 변수")
        variables_layout = QVBoxLayout(variables_group)
        
        self.variables_label = QLabel()
        self.variables_label.setWordWrap(True)
        self.variables_label.setStyleSheet("QLabel { color: #666; font-size: 11px; }")
        self._update_variables_display()
        variables_layout.addWidget(self.variables_label)
        
        basic_layout.addWidget(variables_group)
        
        self.tab_widget.addTab(basic_tab, "기본 설정")
    
    def _setup_conditions_tab(self):
        """조건부 템플릿 탭 설정"""
        conditions_tab = QWidget()
        conditions_layout = QVBoxLayout(conditions_tab)
        conditions_layout.setContentsMargins(10, 10, 10, 10)
        
        # 설명 라벨
        desc_label = QLabel("특정 조건에 따라 다른 템플릿을 사용할 수 있습니다.")
        desc_label.setStyleSheet("QLabel { color: #666; margin-bottom: 10px; }")
        conditions_layout.addWidget(desc_label)
        
        # 조건 테이블
        self.conditions_table = QTableWidget()
        self.conditions_table.setColumnCount(4)
        self.conditions_table.setHorizontalHeaderLabels(["필드", "연산자", "값", "템플릿 내용"])
        
        # 테이블 헤더 설정
        header = self.conditions_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        
        self.conditions_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.conditions_table.setAlternatingRowColors(True)
        self.conditions_table.itemDoubleClicked.connect(self._on_condition_table_double_clicked)
        
        conditions_layout.addWidget(self.conditions_table)
        
        # 조건 관리 버튼
        button_layout = QHBoxLayout()
        
        add_condition_btn = QPushButton("조건 추가")
        add_condition_btn.clicked.connect(self._on_add_condition_clicked)
        button_layout.addWidget(add_condition_btn)
        
        edit_condition_btn = QPushButton("조건 수정")
        edit_condition_btn.clicked.connect(self._on_edit_condition_clicked)
        button_layout.addWidget(edit_condition_btn)
        
        delete_condition_btn = QPushButton("조건 삭제")
        delete_condition_btn.clicked.connect(self._on_delete_condition_clicked)
        button_layout.addWidget(delete_condition_btn)
        
        button_layout.addStretch()
        conditions_layout.addLayout(button_layout)
        
        self.tab_widget.addTab(conditions_tab, "조건부 템플릿")
    
    def _setup_preview_tab(self):
        """미리보기 탭 설정"""
        preview_tab = QWidget()
        preview_layout = QVBoxLayout(preview_tab)
        preview_layout.setContentsMargins(10, 10, 10, 10)
        
        # 미리보기 설정
        settings_group = QGroupBox("미리보기 설정")
        settings_layout = QFormLayout(settings_group)
        
        # 데이터 소스 선택
        self.data_source_combo = QComboBox()
        self.data_source_combo.addItems(["실제 데이터", "샘플 데이터"])
        settings_layout.addRow("데이터 소스:", self.data_source_combo)
        
        # 판매자 선택
        self.seller_combo = QComboBox()
        self.seller_combo.setEditable(True)
        self.seller_combo.setPlaceholderText("판매자를 선택하거나 입력하세요")
        settings_layout.addRow("판매자:", self.seller_combo)
        
        # 날짜 선택
        self.date_edit = QLineEdit()
        self.date_edit.setPlaceholderText("YYYY-MM-DD (비워두면 오늘 날짜)")
        settings_layout.addRow("출고일:", self.date_edit)
        
        preview_layout.addWidget(settings_group)
        
        # 미리보기 버튼
        preview_btn_layout = QHBoxLayout()
        
        self.preview_button = QPushButton("미리보기 생성")
        self.preview_button.clicked.connect(self._on_preview_clicked)
        self.preview_button.setStyleSheet("QPushButton { font-weight: bold; padding: 8px; }")
        preview_btn_layout.addWidget(self.preview_button)
        
        refresh_data_btn = QPushButton("데이터 새로고침")
        refresh_data_btn.clicked.connect(self._on_refresh_data_clicked)
        preview_btn_layout.addWidget(refresh_data_btn)
        
        preview_btn_layout.addStretch()
        preview_layout.addLayout(preview_btn_layout)
        
        # 미리보기 결과
        result_group = QGroupBox("미리보기 결과")
        result_layout = QVBoxLayout(result_group)
        
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setMinimumHeight(300)
        self.preview_text.setPlaceholderText("미리보기 생성 버튼을 클릭하여 결과를 확인하세요.")
        result_layout.addWidget(self.preview_text)
        
        # 미리보기 결과 관리 버튼
        result_btn_layout = QHBoxLayout()
        
        copy_result_btn = QPushButton("결과 복사")
        copy_result_btn.clicked.connect(self._on_copy_result_clicked)
        result_btn_layout.addWidget(copy_result_btn)
        
        export_result_btn = QPushButton("결과 내보내기")
        export_result_btn.clicked.connect(self._on_export_result_clicked)
        result_btn_layout.addWidget(export_result_btn)
        
        result_btn_layout.addStretch()
        result_layout.addLayout(result_btn_layout)
        
        preview_layout.addWidget(result_group)
        
        self.tab_widget.addTab(preview_tab, "미리보기")
    
    def _update_variables_display(self):
        """변수 목록 표시 업데이트"""
        api_vars = [f"{{{v}}}" for v in API_FIELDS.values()]
        custom_vars = ["{order_index}", "{total_orders}", "{product_index}", "{total_products}", "{order_details}"]
        all_vars = api_vars + custom_vars
        
        # 변수를 그룹별로 정리
        var_text = "API 필드: " + ", ".join(api_vars[:8]) + "...\n"
        var_text += "커스텀 변수: " + ", ".join(custom_vars)
        
        self.variables_label.setText(var_text)
    
    def _populate_template_tree(self):
        """템플릿 트리 아이템 생성"""
        self.template_tree.clear()
        
        # FBO 카테고리
        fbo_category = QTreeWidgetItem(self.template_tree, ["FBO (Fabric Bulk Order)"])
        fbo_category.setExpanded(True)
        
        # FBO 하위 템플릿
        for op_type in FboOperationType:
            display_name = ""
            if op_type == FboOperationType.SHIPMENT_REQUEST:
                display_name = "출고 요청"
            elif op_type == FboOperationType.SHIPMENT_CONFIRM:
                display_name = "출고 확인"
            elif op_type == FboOperationType.PO:
                display_name = "발주 확인 요청"
            
            item = QTreeWidgetItem(fbo_category, [display_name])
            item.setData(0, Qt.UserRole, {"order_type": OrderType.FBO.value, "operation_type": op_type.value})
        
        # SBO 카테고리
        sbo_category = QTreeWidgetItem(self.template_tree, ["SBO (Swatch Box Order)"])
        sbo_category.setExpanded(True)
        
        # SBO 하위 템플릿
        for op_type in SboOperationType:
            display_name = ""
            if op_type == SboOperationType.PO:
                display_name = "스와치 발주"
            elif op_type == SboOperationType.PICKUP_REQUEST:
                display_name = "픽업 요청"
            
            item = QTreeWidgetItem(sbo_category, [display_name])
            item.setData(0, Qt.UserRole, {"order_type": OrderType.SBO.value, "operation_type": op_type.value})
    
    def _on_template_selected(self, item: QTreeWidgetItem, column: int):
        """템플릿 선택 이벤트"""
        # 상위 카테고리 항목인 경우 무시
        if item.parent() is None:
            return
        
        # 아이템 데이터 가져오기
        data = item.data(0, Qt.UserRole)
        if not data:
            return
        
        # 현재 선택된 템플릿 유형 저장
        self._current_order_type = data["order_type"]
        self._current_operation_type = data["operation_type"]
        
        # 템플릿 로드
        self._load_template(self._current_order_type, self._current_operation_type)
    
    def _load_template(self, order_type: str, operation_type: str):
        """템플릿 로드"""
        try:
            # 템플릿 서비스에서 템플릿 로드
            template = self.template_service.load_template(
                OrderType(order_type),
                FboOperationType(operation_type) if order_type == OrderType.FBO.value else SboOperationType(operation_type)
            )
            
            if template:
                # UI 업데이트
                self.template_title.setText(template.get("title", ""))
                self.template_description.setText(template.get("description", ""))
                self.template_content.setText(template.get("content", ""))
                self.order_details_format.setText(template.get("order_details_format", DEFAULT_ORDER_DETAILS_FORMAT))
                
                # 조건 테이블 업데이트
                self._update_conditions_table(template.get("conditions", []))
            else:
                # 새 템플릿인 경우 기본값 설정
                self.template_title.clear()
                self.template_description.clear()
                self.template_content.clear()
                self.order_details_format.setText(DEFAULT_ORDER_DETAILS_FORMAT)
                self._update_conditions_table([])
                
        except Exception as e:
            self.log(f"템플릿 로드 중 오류: {str(e)}", LOG_ERROR)
            QMessageBox.critical(self, "오류", f"템플릿 로드 중 오류가 발생했습니다:\n{str(e)}")
    
    def _update_conditions_table(self, conditions: List[Dict]):
        """조건 테이블 업데이트"""
        self.conditions_table.setRowCount(len(conditions))
        
        for row, condition in enumerate(conditions):
            self.conditions_table.setItem(row, 0, QTableWidgetItem(condition.get("field", "")))
            self.conditions_table.setItem(row, 1, QTableWidgetItem(condition.get("operator", "")))
            self.conditions_table.setItem(row, 2, QTableWidgetItem(str(condition.get("value", ""))))
            self.conditions_table.setItem(row, 3, QTableWidgetItem(condition.get("template", "")))
    
    # 새로운 버튼 이벤트 핸들러들
    def _on_new_template_clicked(self):
        """새 템플릿 버튼 클릭"""
        self.log("새 템플릿 기능은 아직 구현되지 않았습니다.", LOG_INFO)
    
    def _on_copy_template_clicked(self):
        """템플릿 복사 버튼 클릭"""
        self.log("템플릿 복사 기능은 아직 구현되지 않았습니다.", LOG_INFO)
    
    def _on_delete_template_clicked(self):
        """템플릿 삭제 버튼 클릭"""
        self.log("템플릿 삭제 기능은 아직 구현되지 않았습니다.", LOG_INFO)
    
    def _on_condition_table_double_clicked(self, item):
        """조건 테이블 더블클릭 이벤트"""
        self._on_edit_condition_clicked()
    
    def _on_edit_condition_clicked(self):
        """조건 수정 버튼 클릭"""
        current_row = self.conditions_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "경고", "수정할 조건을 선택해주세요.")
            return
        
        # 기존 조건 데이터 가져오기
        field = self.conditions_table.item(current_row, 0).text() if self.conditions_table.item(current_row, 0) else ""
        operator = self.conditions_table.item(current_row, 1).text() if self.conditions_table.item(current_row, 1) else ""
        value = self.conditions_table.item(current_row, 2).text() if self.conditions_table.item(current_row, 2) else ""
        template = self.conditions_table.item(current_row, 3).text() if self.conditions_table.item(current_row, 3) else ""
        
        condition = {
            "field": field,
            "operator": operator,
            "value": value,
            "template": template
        }
        
        dialog = ConditionDialog(self, condition)
        if dialog.exec():
            self._update_condition_in_table(current_row, dialog.condition)
    
    def _update_condition_in_table(self, row: int, condition: Dict):
        """테이블의 조건 업데이트"""
        self.conditions_table.setItem(row, 0, QTableWidgetItem(condition.get("field", "")))
        self.conditions_table.setItem(row, 1, QTableWidgetItem(condition.get("operator", "")))
        self.conditions_table.setItem(row, 2, QTableWidgetItem(str(condition.get("value", ""))))
        self.conditions_table.setItem(row, 3, QTableWidgetItem(condition.get("template", "")))
    
    def _on_refresh_data_clicked(self):
        """데이터 새로고침 버튼 클릭"""
        self.log("데이터를 새로고침합니다.", LOG_INFO)
        # TODO: 판매자 목록 새로고침 구현
    
    def _on_copy_result_clicked(self):
        """결과 복사 버튼 클릭"""
        import pyperclip
        text = self.preview_text.toPlainText()
        if text:
            pyperclip.copy(text)
            self.log("미리보기 결과가 클립보드에 복사되었습니다.", LOG_SUCCESS)
        else:
            self.log("복사할 내용이 없습니다.", LOG_WARNING)
    
    def _on_export_result_clicked(self):
        """결과 내보내기 버튼 클릭"""
        text = self.preview_text.toPlainText()
        if not text:
            QMessageBox.warning(self, "경고", "내보낼 내용이 없습니다.")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "미리보기 결과 저장", "", "텍스트 파일 (*.txt);;모든 파일 (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(text)
                self.log(f"미리보기 결과가 저장되었습니다: {file_path}", LOG_SUCCESS)
            except Exception as e:
                self.log(f"파일 저장 중 오류: {str(e)}", LOG_ERROR)
                QMessageBox.critical(self, "오류", f"파일 저장 중 오류가 발생했습니다:\n{str(e)}")
    
    def _on_add_condition_clicked(self):
        """조건 추가 버튼 클릭 이벤트"""
        if not self._current_order_type or not self._current_operation_type:
            self.log("템플릿을 먼저 선택해주세요.", LOG_WARNING)
            return
            
        dialog = ConditionDialog(self)
        if dialog.exec():
            # 테이블에 새 조건 추가
            row_count = self.conditions_table.rowCount()
            self.conditions_table.insertRow(row_count)
            self._update_condition_in_table(row_count, dialog.condition)
            
            self.log("조건이 추가되었습니다.", LOG_SUCCESS)
    
    def _on_delete_condition_clicked(self):
        """조건 삭제 버튼 클릭 이벤트"""
        current_row = self.conditions_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "경고", "삭제할 조건을 선택해주세요.")
            return
            
        reply = QMessageBox.question(
            self,
            "확인",
            "선택한 조건을 삭제하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.conditions_table.removeRow(current_row)
            self.log("조건이 삭제되었습니다.", LOG_SUCCESS)
    
    def _on_preview_clicked(self):
        """미리보기 버튼 클릭 이벤트"""
        if not self._current_order_type or not self._current_operation_type:
            self.log("템플릿을 먼저 선택해주세요.", LOG_WARNING)
            return
            
        try:
            self.log(f"API 호출 시작: {self._current_order_type}/{self._current_operation_type}", LOG_INFO)
            data = self.template_service.get_api_data(self._current_order_type, self._current_operation_type)
            if not data:
                self.log("미리보기 데이터를 가져올 수 없습니다.", LOG_ERROR)
                QMessageBox.warning(self, "미리보기 실패", "데이터를 가져올 수 없습니다.")
                return
                
            items = data.get("items", []) if isinstance(data, dict) else data
            if not items:
                self.log("미리보기 데이터가 비어있습니다.", LOG_ERROR)
                QMessageBox.warning(self, "미리보기 실패", "데이터가 비어있습니다.")
                return

            # 날짜 필터링
            target_date = self.date_edit.text().strip() or datetime.now().strftime("%Y-%m-%d")
            self.log(f"1. {target_date} 출고 예정 데이터 필터링 시작", LOG_INFO)
            pickup_items = [item for item in items if item.get("pickup_at", "").startswith(target_date)]
            
            if not pickup_items:
                self.log(f"{target_date} 출고 예정인 데이터가 없습니다.", LOG_WARNING)
                QMessageBox.warning(self, "미리보기 실패", f"{target_date} 출고 예정인 데이터가 없습니다.")
                return
                
            self.log(f"1. 필터링 완료: {len(pickup_items)}개의 출고 예정 데이터", LOG_INFO)

            # 판매자별로 데이터 그룹핑
            self.log("2. 판매자별 데이터 그룹핑 시작", LOG_INFO)
            seller_groups = {}
            for item in pickup_items:
                seller_name = item.get("store_name", "알 수 없음")
                if seller_name not in seller_groups:
                    seller_groups[seller_name] = []
                seller_groups[seller_name].append(item)

            # 판매자 선택
            selected_seller = self.seller_combo.currentText().strip()
            if selected_seller and selected_seller in seller_groups:
                current_seller = selected_seller
            else:
                current_seller = random.choice(list(seller_groups.keys()))
            
            seller_items = seller_groups[current_seller]
            
            # 주문번호별로 그룹핑
            order_groups = {}
            for item in seller_items:
                order_number = item.get("purchase_code", "")
                if order_number not in order_groups:
                    order_groups[order_number] = []
                order_groups[order_number].append(item)

            # 주문별 order_details 생성
            order_details_blocks = []
            for order_idx, (order_number, products) in enumerate(order_groups.items(), 1):
                # id와 purchase_code 기준 중복 제거된 상품 리스트 생성
                unique_products = []
                seen_identifiers = set()
                for data in products:
                    # id와 purchase_code 조합으로 고유성 확인
                    product_id = data.get("id", "")
                    purchase_code = data.get("purchase_code", "")
                    identifier = f"{product_id}_{purchase_code}"
                    
                    if identifier in seen_identifiers:
                        continue
                    seen_identifiers.add(identifier)
                    unique_products.append(data)
                    
                order_details_lines = []
                for prod_idx, data in enumerate(unique_products, 1):
                    # 데이터 복사 및 추가 정보 설정
                    processed_data = data.copy()
                    processed_data["order_index"] = order_idx
                    processed_data["total_orders"] = len(order_groups)
                    processed_data["product_index"] = prod_idx
                    processed_data["total_products"] = len(unique_products)
                    
                    # delivery_method와 logistics_company 치환
                    delivery_method = processed_data.get("delivery_method", "")
                    logistics_company = processed_data.get("logistics_company", "")
                    
                    # None 값을 문자열로 변환
                    if delivery_method is None:
                        delivery_method = "None"
                    if logistics_company is None:
                        logistics_company = "None"
                    
                    # pickup_at 날짜 형식 변환 (YYYY-MM-DDTHH:MM:SS+TZ -> YYYY-MM-DD)
                    pickup_at = processed_data.get("pickup_at", "")
                    if pickup_at and "T" in pickup_at:
                        pickup_at = pickup_at.split("T")[0]  # T 앞부분만 추출
                        processed_data["pickup_at"] = pickup_at
                    
                    self.log(f"치환 전: delivery_method='{delivery_method}', logistics_company='{logistics_company}'", LOG_DEBUG)
                    
                    processed_data["delivery_method"] = DELIVERY_METHODS.get(delivery_method, delivery_method)
                    processed_data["logistics_company"] = LOGISTICS_COMPANIES.get(logistics_company, logistics_company)
                    
                    self.log(f"치환 후: delivery_method='{processed_data['delivery_method']}', logistics_company='{processed_data['logistics_company']}'", LOG_DEBUG)
                    
                    order_details_format = self.order_details_format.toPlainText()
                    order_details_line = order_details_format
                    for k, v in {**processed_data, **{k: processed_data.get(k, '') for k in API_FIELDS.values()}}.items():
                        order_details_line = order_details_line.replace(f"{{{k}}}", str(v))
                    order_details_lines.append(order_details_line)
                    
                # 주문별 블록 생성 (주문번호 + 상품 목록)
                if order_details_lines:
                    block = f"{order_idx}. {order_number}\n" + "\n".join([f"    {prod_idx}) {line}" for prod_idx, line in enumerate(order_details_lines, 1)])
                else:
                    # 상품이 없는 경우에도 주문번호는 표시
                    block = f"{order_idx}. {order_number}\n    (상품 정보 없음)"
                
                order_details_blocks.append(block)

            # 메시지 데이터 준비
            msg_data = dict(seller_items[0])  # 기본 데이터는 첫 번째 아이템에서 가져옴
            msg_data["order_details"] = "\n".join(order_details_blocks)
            msg_data["store_name"] = current_seller

            # 템플릿 렌더링
            message = self.template_service.render_message(
                OrderType(self._current_order_type),
                FboOperationType(self._current_operation_type) if self._current_order_type == OrderType.FBO.value else SboOperationType(self._current_operation_type),
                msg_data
            )

            if message:
                self.preview_text.setText(message)
                self.log(f"미리보기 생성 완료: {current_seller} 판매자", LOG_SUCCESS)
            else:
                self.log("미리보기 생성에 실패했습니다.", LOG_ERROR)
                QMessageBox.warning(self, "미리보기 실패", "미리보기 생성에 실패했습니다.")
                
        except Exception as e:
            self.log(f"미리보기 생성 중 오류: {str(e)}", LOG_ERROR)
            QMessageBox.critical(self, "오류", f"미리보기 생성 중 오류가 발생했습니다:\n{str(e)}")
    
    def _on_save_clicked(self):
        """저장 버튼 클릭 이벤트"""
        if not self._current_order_type or not self._current_operation_type:
            self.log("템플릿을 먼저 선택해주세요.", LOG_WARNING)
            return
        
        # 템플릿 데이터 가져오기
        title = self.template_title.text()
        content = self.template_content.toPlainText()
        order_details_format = self.order_details_format.toPlainText()
        
        if not title or not content:
            self.log("제목과 내용을 모두 입력해주세요.", LOG_WARNING)
            return
        
        # 조건 데이터 수집
        conditions = []
        for row in range(self.conditions_table.rowCount()):
            field_item = self.conditions_table.item(row, 0)
            operator_item = self.conditions_table.item(row, 1)
            value_item = self.conditions_table.item(row, 2)
            template_item = self.conditions_table.item(row, 3)
            
            if field_item and operator_item and value_item:
                condition = {
                    "field": field_item.text(),
                    "operator": operator_item.text(),
                    "value": value_item.text(),
                    "template": template_item.text() if template_item else ""
                }
                conditions.append(condition)
        
        try:
            # 템플릿 서비스에 저장
            success = self.template_service.update_template(
                OrderType(self._current_order_type),
                FboOperationType(self._current_operation_type) if self._current_order_type == OrderType.FBO.value else SboOperationType(self._current_operation_type),
                title,
                content,
                order_details_format=order_details_format,
                conditions=conditions
            )
            
            if success:
                self.log("템플릿이 저장되었습니다.", LOG_SUCCESS)
                QMessageBox.information(self, "저장 완료", "템플릿이 성공적으로 저장되었습니다.")
            else:
                self.log("템플릿 저장에 실패했습니다.", LOG_ERROR)
                QMessageBox.critical(self, "저장 실패", "템플릿 저장에 실패했습니다.")
                
        except Exception as e:
            self.log(f"템플릿 저장 중 오류: {str(e)}", LOG_ERROR)
            QMessageBox.critical(self, "오류", f"템플릿 저장 중 오류가 발생했습니다:\n{str(e)}")
    
    def on_section_activated(self):
        """섹션이 활성화될 때 호출"""
        self.log("템플릿 관리 섹션이 활성화되었습니다.", LOG_INFO)
    
    def on_section_deactivated(self):
        """섹션이 비활성화될 때 호출"""
        pass 
    
    def _set_initial_splitter_sizes(self):
        """스플리터 초기 크기 설정"""
        try:
            # 메인 스플리터 찾기
            splitter = self.content_layout.itemAt(0).widget()
            if isinstance(splitter, QSplitter):
                # 현재 위젯의 실제 크기 가져오기
                total_width = self.width()
                
                # 왼쪽:오른쪽 = 20%:80% 비율로 설정
                if total_width > 800:
                    left_size = max(200, int(total_width * 0.2))
                    right_size = total_width - left_size
                else:
                    left_size = min(180, int(total_width * 0.25))
                    right_size = total_width - left_size
                
                splitter.setSizes([left_size, right_size])
                        
        except Exception as e:
            self.log(f"스플리터 크기 설정 중 오류: {str(e)}", LOG_DEBUG)
    
    def resizeEvent(self, event):
        """창 크기 변경 시 호출"""
        super().resizeEvent(event)
        # 크기 변경 후 스플리터 크기 재조정
        QTimer.singleShot(10, self._set_initial_splitter_sizes)
    