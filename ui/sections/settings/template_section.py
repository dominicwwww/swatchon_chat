"""
템플릿 섹션 - 메시지 템플릿 관리
"""
from typing import List, Dict, Any, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QListWidget, QListWidgetItem, QFrame, QSplitter,
    QCheckBox, QComboBox, QLineEdit, QGridLayout, QGroupBox,
    QFormLayout, QFileDialog, QSpacerItem, QSizePolicy,
    QTextEdit, QTabWidget, QTreeWidget, QTreeWidgetItem, QMessageBox
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QFont, QColor

from core.types import LogType, OrderType, FboOperationType, SboOperationType
from ui.sections.base_section import BaseSection
from ui.theme import get_theme
from core.config import ConfigManager
from ui.components.log_widget import LOG_INFO, LOG_DEBUG, LOG_WARNING, LOG_ERROR, LOG_SUCCESS

class TemplateSection(BaseSection):
    """
    템플릿 섹션 - 메시지 템플릿 관리
    """
    
    def __init__(self, parent=None):
        super().__init__("템플릿 관리", parent)
        
        # 저장 버튼 추가
        self.save_button = self.add_header_button("저장", self._on_save_clicked, primary=True)
        
        # 콘텐츠 설정
        self.setup_content()
        
        # 현재 선택된 템플릿 정보
        self._current_order_type = None
        self._current_operation_type = None
    
    def setup_content(self):
        """콘텐츠 설정"""
        # 스플리터 생성
        splitter = QSplitter(Qt.Horizontal)
        
        # 왼쪽 패널 (템플릿 트리)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # 템플릿 트리 위젯
        self.template_tree = QTreeWidget()
        self.template_tree.setHeaderHidden(True)
        self.template_tree.setColumnCount(1)
        self.template_tree.setSelectionMode(QTreeWidget.SingleSelection)
        
        # 트리 아이템 생성
        self._populate_template_tree()
        
        # 템플릿 선택 이벤트 연결
        self.template_tree.itemClicked.connect(self._on_template_selected)
        
        left_layout.addWidget(self.template_tree)
        
        # 오른쪽 패널 (템플릿 편집)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # 템플릿 편집 폼
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        
        # 템플릿 제목
        self.template_title = QLineEdit()
        form_layout.addRow("제목:", self.template_title)
        
        # 템플릿 내용
        self.template_content = QTextEdit()
        self.template_content.setMinimumHeight(200)
        form_layout.addRow("내용:", self.template_content)
        
        # 템플릿 변수 목록
        self.variables_label = QLabel("템플릿 변수: 없음")
        form_layout.addRow("사용 가능한 변수:", self.variables_label)
        
        # 변수 사용 예시
        example_label = QLabel("변수 사용 예시: {seller_name}, {order_number}, {product_name} 등")
        example_label.setWordWrap(True)
        form_layout.addRow("", example_label)
        
        # 오른쪽 패널에 폼 추가
        right_layout.addLayout(form_layout)
        
        # 미리보기 영역
        preview_group = QGroupBox("미리보기")
        preview_layout = QVBoxLayout(preview_group)
        
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        preview_layout.addWidget(self.preview_text)
        
        # 미리보기 버튼
        preview_button = QPushButton("미리보기 생성")
        preview_button.clicked.connect(self._on_preview_clicked)
        preview_layout.addWidget(preview_button)
        
        right_layout.addWidget(preview_group)
        
        # 스플리터에 패널 추가
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        
        # 스플리터 비율 설정 (왼쪽 30%, 오른쪽 70%)
        splitter.setSizes([int(self.width() * 0.3), int(self.width() * 0.7)])
        
        # 메인 레이아웃에 스플리터 추가
        self.content_layout.addWidget(splitter)
    
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
        # TODO: 실제로 템플릿 서비스에서 로드
        
        # 더미 데이터 - 실제로는 템플릿 서비스에서 가져와야 함
        dummy_templates = {
            OrderType.FBO.value: {
                FboOperationType.SHIPMENT_REQUEST.value: {
                    "title": "FBO 출고 요청",
                    "content": "[SwatchOn] {seller_name}님 안녕하세요.\n\n다음 주문의 출고를 요청드립니다.\n\n- 주문번호: {order_number}\n- 상품명: {product_name}\n- 수량: {quantity}개\n\n감사합니다.",
                    "variables": ["seller_name", "order_number", "product_name", "quantity"]
                },
                FboOperationType.SHIPMENT_CONFIRM.value: {
                    "title": "FBO 출고 확인",
                    "content": "[SwatchOn] {seller_name}님\n\n출고 확인되었습니다.\n\n- 주문번호: {order_number}\n- 송장번호: {tracking_number}\n\n감사합니다.",
                    "variables": ["seller_name", "order_number", "tracking_number"]
                },
                FboOperationType.PO.value: {
                    "title": "FBO 발주 확인 요청",
                    "content": "[SwatchOn] {seller_name}님\n\n발주 확인 요청드립니다.\n\n- 발주번호: {po_number}\n- 상품명: {product_name}\n- 수량: {quantity}개\n\n감사합니다.",
                    "variables": ["seller_name", "po_number", "product_name", "quantity"]
                }
            },
            OrderType.SBO.value: {
                SboOperationType.PO.value: {
                    "title": "SBO 스와치 발주",
                    "content": "[SwatchOn] {seller_name}님\n\n스와치 발주합니다.\n\n- 주문번호: {order_number}\n- 스와치 정보: {swatch_details}\n\n감사합니다.",
                    "variables": ["seller_name", "order_number", "swatch_details"]
                },
                SboOperationType.PICKUP_REQUEST.value: {
                    "title": "SBO 스와치 픽업 요청",
                    "content": "[SwatchOn] {seller_name}님\n\n스와치 픽업 요청드립니다.\n\n- 주문번호: {order_number}\n- 픽업 날짜: {pickup_date}\n- 픽업 시간: {pickup_time}\n\n감사합니다.",
                    "variables": ["seller_name", "order_number", "pickup_date", "pickup_time"]
                }
            }
        }
        
        # 템플릿 가져오기
        template = dummy_templates.get(order_type, {}).get(operation_type, None)
        
        if template:
            # UI 업데이트
            self.template_title.setText(template["title"])
            self.template_content.setText(template["content"])
            
            # 변수 목록 표시
            variables = template.get("variables", [])
            if variables:
                self.variables_label.setText("템플릿 변수: " + ", ".join(["{" + var + "}" for var in variables]))
            else:
                self.variables_label.setText("템플릿 변수: 없음")
        else:
            self.template_title.clear()
            self.template_content.clear()
            self.variables_label.setText("템플릿 변수: 없음")
    
    def _on_preview_clicked(self):
        """미리보기 버튼 클릭 이벤트"""
        if not self._current_order_type or not self._current_operation_type:
            self.log("템플릿을 먼저 선택해주세요.", LOG_WARNING)
            return
        
        # 템플릿 내용 가져오기
        template_content = self.template_content.toPlainText()
        
        # 더미 데이터로 미리보기 생성
        preview_data = self._get_dummy_preview_data(self._current_order_type, self._current_operation_type)
        
        # 변수 치환
        for var_name, var_value in preview_data.items():
            placeholder = "{" + var_name + "}"
            template_content = template_content.replace(placeholder, str(var_value))
        
        # 미리보기 업데이트
        self.preview_text.setText(template_content)
        
        self.log("미리보기가 생성되었습니다.", LOG_INFO)
    
    def _get_dummy_preview_data(self, order_type: str, operation_type: str) -> Dict[str, str]:
        """더미 미리보기 데이터 가져오기"""
        if order_type == OrderType.FBO.value:
            if operation_type == FboOperationType.SHIPMENT_REQUEST.value:
                return {
                    "seller_name": "홍길동",
                    "order_number": "FBO-2023-001",
                    "product_name": "면 원단 30수",
                    "quantity": "100"
                }
            elif operation_type == FboOperationType.SHIPMENT_CONFIRM.value:
                return {
                    "seller_name": "홍길동",
                    "order_number": "FBO-2023-001",
                    "tracking_number": "123456789"
                }
            elif operation_type == FboOperationType.PO.value:
                return {
                    "seller_name": "홍길동",
                    "po_number": "PO-2023-001",
                    "product_name": "면 원단 30수",
                    "quantity": "200"
                }
        elif order_type == OrderType.SBO.value:
            if operation_type == SboOperationType.PO.value:
                return {
                    "seller_name": "홍길동",
                    "order_number": "SBO-2023-001",
                    "swatch_details": "면 원단 외 3종"
                }
            elif operation_type == SboOperationType.PICKUP_REQUEST.value:
                return {
                    "seller_name": "홍길동",
                    "order_number": "SBO-2023-001",
                    "pickup_date": "2023-05-25",
                    "pickup_time": "오전 10:00"
                }
        
        return {}
    
    def _on_save_clicked(self):
        """저장 버튼 클릭 이벤트"""
        if not self._current_order_type or not self._current_operation_type:
            self.log("템플릿을 먼저 선택해주세요.", LOG_WARNING)
            return
        
        # 템플릿 데이터 가져오기
        title = self.template_title.text()
        content = self.template_content.toPlainText()
        
        if not title or not content:
            self.log("제목과 내용을 모두 입력해주세요.", LOG_WARNING)
            return
        
        # TODO: 실제로 템플릿 서비스에 저장
        
        self.log("템플릿이 저장되었습니다.", LOG_SUCCESS)
    
    def on_section_activated(self):
        """섹션이 활성화될 때 호출"""
        self.log("템플릿 관리 섹션이 활성화되었습니다.", LOG_INFO)
    
    def on_section_deactivated(self):
        """섹션이 비활성화될 때 호출"""
        pass 