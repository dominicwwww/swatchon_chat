"""
조건부 템플릿 생성/수정 다이얼로그 모듈
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QFormLayout, QDialogButtonBox, QMessageBox,
    QTextEdit, QListWidget, QListWidgetItem, QGroupBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QWidget
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from core.constants import ConfigKey, DELIVERY_METHODS, LOGISTICS_COMPANIES, API_FIELDS
from core.logger import get_logger
from core.config import ConfigManager
from ui.theme import get_theme

class ConditionDialog(QDialog):
    """조건부 템플릿 생성/수정 다이얼로그 클래스"""
    
    def __init__(self, parent=None, condition=None):
        super().__init__(parent)
        self.logger = get_logger(__name__)
        self.config = ConfigManager()
        self.theme = get_theme()
        self.condition = condition or {}
        
        self.setWindowTitle("조건 추가/수정")
        self.setMinimumWidth(800)  # 다중 선택을 위해 너비 증가
        self.setMinimumHeight(600)  # 높이도 증가
        
        self.setup_ui()
        if condition:
            self._load_condition()
        
    def setup_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 폼 레이아웃
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        
        # 필드 선택 그룹
        field_group = QGroupBox("필드 선택")
        field_layout = QVBoxLayout(field_group)
        
        # 필드 선택 리스트
        self.field_list = QListWidget()
        self.field_list.setSelectionMode(QListWidget.MultiSelection)
        # API_FIELDS에서 필드 목록 가져오기
        field_list = list(API_FIELDS.values())
        self.field_list.addItems(field_list)
        field_layout.addWidget(self.field_list)
        
        # 필드 설명
        field_desc = QLabel("Ctrl 키를 누른 상태에서 여러 필드를 선택할 수 있습니다.")
        field_desc.setStyleSheet("color: gray; font-size: 10px;")
        field_layout.addWidget(field_desc)
        
        form_layout.addRow(field_group)
        
        # 필드별 조건 입력 테이블
        condition_group = QGroupBox("필드별 조건 입력")
        condition_layout = QVBoxLayout(condition_group)
        
        self.condition_table = QTableWidget()
        self.condition_table.setColumnCount(3)
        self.condition_table.setHorizontalHeaderLabels(["필드", "연산자", "값"])
        
        # 컬럼 크기 조정 - 고정 크기로 설정하여 오버랩 방지
        header = self.condition_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)  # 필드 컬럼 고정
        header.setSectionResizeMode(1, QHeaderView.Fixed)  # 연산자 컬럼 고정
        header.setSectionResizeMode(2, QHeaderView.Stretch)  # 값 컬럼만 늘어남
        
        # 컬럼 너비 설정
        self.condition_table.setColumnWidth(0, 120)  # 필드 컬럼 너비
        self.condition_table.setColumnWidth(1, 120)   # 연산자 컬럼 너비 증가
        
        # 행 높이 설정 - 콤보박스가 겹치지 않도록
        self.condition_table.verticalHeader().setDefaultSectionSize(35)
        
        condition_layout.addWidget(self.condition_table)
        
        # 값 입력 도움말
        value_help = QLabel("값 입력 도움말: {today} = 오늘, {today-1} = 어제, {today+1} = 내일, null = null 값")
        value_help.setStyleSheet("color: gray; font-size: 10px;")
        condition_layout.addWidget(value_help)
        
        # 필드 선택 변경 시 테이블 업데이트
        self.field_list.itemSelectionChanged.connect(self._update_condition_table)
        
        form_layout.addRow(condition_group)
        
        # 템플릿 타입 변경 섹션 추가
        self._setup_template_type_section(form_layout)
        
        # 템플릿 내용 입력
        self.template_edit = QTextEdit()
        self.template_edit.setPlaceholderText("조건이 만족될 때 기존 템플릿 뒤에 추가할 내용을 입력하세요")
        self.template_edit.setMinimumHeight(100)
        form_layout.addRow("추가할 내용:", self.template_edit)
        
        layout.addLayout(form_layout)
        
        # 버튼 영역
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)
    
    def _update_condition_table(self):
        """필드 선택 변경 시 조건 입력 테이블 업데이트"""
        selected_fields = [item.text() for item in self.field_list.selectedItems()]
        
        # 테이블 완전 초기화
        self.condition_table.clear()
        self.condition_table.setHorizontalHeaderLabels(["필드", "연산자", "값"])
        self.condition_table.setRowCount(len(selected_fields))
        
        for row, field in enumerate(selected_fields):
            # 필드명 - 완전히 편집 불가능한 아이템으로 설정
            field_item = QTableWidgetItem(field)
            field_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)  # 편집 불가, 선택만 가능
            self.condition_table.setItem(row, 0, field_item)
            
            # 연산자 콤보박스 - 명확히 1번 컬럼에 설정
            operator_combo = QComboBox()
            operator_combo.addItems(["==", "!=", ">", "<", ">=", "<=", "is_null", "is_not_null", "contains", "not_contains"])
            self.condition_table.setCellWidget(row, 1, operator_combo)
            
            # 값 입력 - 명확히 2번 컬럼에 설정
            value_item = QTableWidgetItem("")
            value_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable)  # 편집 가능
            self.condition_table.setItem(row, 2, value_item)
        
    def _setup_template_type_section(self, form_layout):
        """액션 타입 섹션 설정"""
        type_group = QGroupBox("조건 만족 시 액션")
        type_layout = QVBoxLayout(type_group)
        
        # 액션 타입 선택
        self.action_type = QComboBox()
        self.action_type.addItems(["내용 추가", "내용 변경"])
        self.action_type.currentTextChanged.connect(self._on_action_type_changed)
        type_layout.addWidget(QLabel("액션 타입:"))
        type_layout.addWidget(self.action_type)
        
        # 액션 설명 라벨
        self.action_description = QLabel()
        self.action_description.setWordWrap(True)
        self.action_description.setStyleSheet("color: gray; font-size: 11px; margin: 5px;")
        type_layout.addWidget(self.action_description)
        
        form_layout.addRow(type_group)
    
    def _on_action_type_changed(self, action_type):
        """액션 타입 변경 이벤트"""
        if action_type == "내용 추가":
            self.action_description.setText("기존 템플릿 뒤에 추가 내용을 덧붙입니다.")
            self.template_edit.setPlaceholderText("조건이 만족될 때 기존 템플릿 뒤에 추가할 내용을 입력하세요")
            self.template_edit.setVisible(True)
        elif action_type == "내용 변경":
            self.action_description.setText("기존 템플릿을 완전히 다른 내용으로 교체합니다.")
            self.template_edit.setPlaceholderText("조건이 만족될 때 사용할 새로운 템플릿 내용을 입력하세요")
            self.template_edit.setVisible(True)
        else:
            self.action_description.setText("")
            self.template_edit.setVisible(True)

    def _load_condition(self):
        """조건 데이터 로드"""
        if not self.condition:
            return
            
        # 필드 설정
        if "fields" in self.condition:
            fields = self.condition["fields"]
        else:
            # 이전 형식의 조건을 새로운 형식으로 변환
            field = self.condition.get("field", "")
            fields = [field] if field else []
            
        if isinstance(fields, str):
            fields = [fields]  # 문자열도 리스트로 변환
            
        for field in fields:
            items = self.field_list.findItems(field, Qt.MatchExactly)
            for item in items:
                item.setSelected(True)
        
        # 조건 테이블 업데이트 후 값들 설정
        self._update_condition_table()
        
        # 연산자와 값 설정
        if "operators" in self.condition:
            # 새로운 형식 (필드별 연산자)
            operators = self.condition["operators"]
            values = self.condition.get("value", {})
            
            for row in range(self.condition_table.rowCount()):
                field_item = self.condition_table.item(row, 0)
                if field_item:
                    field = field_item.text()
                    
                    # 연산자 설정
                    if field in operators:
                        operator_combo = self.condition_table.cellWidget(row, 1)
                        if operator_combo and isinstance(operator_combo, QComboBox):
                            index = operator_combo.findText(operators[field])
                            if index >= 0:
                                operator_combo.setCurrentIndex(index)
                    
                    # 값 설정
                    if field in values:
                        value_item = self.condition_table.item(row, 2)
                        if value_item:
                            value_item.setText(str(values[field]))
        else:
            # 기존 형식 (단일 연산자)
            operator = self.condition.get("operator", "==")
            value = self.condition.get("value", {})
            
            if not isinstance(value, dict):
                # 이전 형식의 값을 새로운 형식으로 변환
                value = {field: value for field in fields}
                
            for row in range(self.condition_table.rowCount()):
                field_item = self.condition_table.item(row, 0)
                if field_item:
                    field = field_item.text()
                    
                    # 연산자 설정
                    operator_combo = self.condition_table.cellWidget(row, 1)
                    if operator_combo and isinstance(operator_combo, QComboBox):
                        index = operator_combo.findText(operator)
                        if index >= 0:
                            operator_combo.setCurrentIndex(index)
                    
                    # 값 설정
                    if field in value:
                        value_item = self.condition_table.item(row, 2)
                        if value_item:
                            value_item.setText(str(value[field]))
        
        # 액션 타입 설정
        action_type = self.condition.get("action_type", "내용 추가")
        # 기존 데이터 호환성을 위해 매핑
        if action_type == "템플릿 내용 변경":
            action_type = "내용 추가"
        elif action_type == "템플릿 타입 변경":
            action_type = "내용 변경"
        self.action_type.setCurrentText(action_type)
        self._on_action_type_changed(action_type)
        
        # 내용 설정
        self.template_edit.setText(self.condition.get("template", ""))
    
    def accept(self):
        """확인 버튼 클릭 시 호출되는 메서드"""
        selected_fields = [item.text() for item in self.field_list.selectedItems()]
        action_type = self.action_type.currentText()
        
        if not selected_fields:
            QMessageBox.warning(self, "입력 오류", "필드를 선택해주세요.")
            return

        # 액션 타입에 따른 유효성 검사
        if action_type in ["내용 추가", "내용 변경"]:
            template_content = self.template_edit.toPlainText().strip()
            if not template_content:
                action_name = "추가할" if action_type == "내용 추가" else "변경할"
                QMessageBox.warning(self, "입력 오류", f"{action_name} 내용을 입력해주세요.")
                return
        
        # 필드별 연산자와 값 수집
        field_operators = {}
        field_values = {}
        
        for row in range(self.condition_table.rowCount()):
            field_item = self.condition_table.item(row, 0)
            operator_combo = self.condition_table.cellWidget(row, 1)
            value_item = self.condition_table.item(row, 2)
            
            if not field_item or not operator_combo:
                continue
                
            field = field_item.text()
            operator = operator_combo.currentText()
            
            # null 체크 연산자는 값이 필요없음
            if operator in ["is_null", "is_not_null"]:
                value = ""
            else:
                if not value_item:
                    continue
                value = value_item.text().strip()
                if not value:
                    QMessageBox.warning(self, "입력 오류", f"'{field}' 필드의 값을 입력해주세요.")
                    return
            
            # 숫자 필드라면 int로 변환 (특수 값 제외)
            if field in [API_FIELDS["QUANTITY"], API_FIELDS["COLOR_NUMBER"]] and not value.startswith("{"):
                try:
                    value = int(value)
                except ValueError:
                    pass  # 변환 실패 시 그대로 문자열
            
            field_operators[field] = operator
            field_values[field] = value

        # 조건 객체 생성
        self.condition = {
            "fields": selected_fields,
            "operators": field_operators,
            "value": field_values,
            "action_type": action_type
        }
        
        # 액션 타입별 추가 정보
        if action_type in ["내용 추가", "내용 변경"]:
            self.condition["template"] = self.template_edit.toPlainText().strip()
        
        super().accept() 