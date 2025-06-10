"""
조건부 템플릿 생성/수정 다이얼로그 모듈
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QFormLayout, QDialogButtonBox, QMessageBox,
    QTextEdit, QListWidget, QListWidgetItem, QGroupBox,
    QTableWidget, QTableWidgetItem, QHeaderView
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
        
        # 연산자 선택
        self.operator_combo = QComboBox()
        self.operator_combo.addItems(["==", "!=", ">", "<", ">=", "<="])
        form_layout.addRow("연산자:", self.operator_combo)
        
        # 필드별 값 입력 테이블
        value_group = QGroupBox("필드별 값 입력")
        value_layout = QVBoxLayout(value_group)
        
        self.value_table = QTableWidget()
        self.value_table.setColumnCount(2)
        self.value_table.setHorizontalHeaderLabels(["필드", "값"])
        self.value_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.value_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        value_layout.addWidget(self.value_table)
        
        # 필드 선택 변경 시 테이블 업데이트
        self.field_list.itemSelectionChanged.connect(self._update_value_table)
        
        form_layout.addRow(value_group)
        
        # 템플릿 내용 입력
        self.template_edit = QTextEdit()
        self.template_edit.setPlaceholderText("조건이 만족될 때 사용할 템플릿 내용을 입력하세요")
        self.template_edit.setMinimumHeight(100)
        form_layout.addRow("템플릿 내용:", self.template_edit)
        
        layout.addLayout(form_layout)
        
        # 버튼 영역
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)
    
    def _update_value_table(self):
        """필드 선택 변경 시 값 입력 테이블 업데이트"""
        selected_fields = [item.text() for item in self.field_list.selectedItems()]
        self.value_table.setRowCount(len(selected_fields))
        
        for row, field in enumerate(selected_fields):
            # 필드명
            field_item = QTableWidgetItem(field)
            field_item.setFlags(field_item.flags() & ~Qt.ItemIsEditable)  # 읽기 전용
            self.value_table.setItem(row, 0, field_item)
            
            # 값 입력
            value_item = QTableWidgetItem("")
            self.value_table.setItem(row, 1, value_item)
        
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
        
        # 연산자 설정
        operator = self.condition.get("operator", "")
        index = self.operator_combo.findText(operator)
        if index >= 0:
            self.operator_combo.setCurrentIndex(index)
        
        # 값 설정
        value = self.condition.get("value", {})
        if not isinstance(value, dict):
            # 이전 형식의 값을 새로운 형식으로 변환
            value = {field: value for field in fields}
            
        for row in range(self.value_table.rowCount()):
            field = self.value_table.item(row, 0).text()
            if field in value:
                self.value_table.item(row, 1).setText(str(value[field]))
        
        # 내용 설정
        self.template_edit.setText(self.condition.get("template", ""))
    
    def accept(self):
        """확인 버튼 클릭 시 호출되는 메서드"""
        selected_fields = [item.text() for item in self.field_list.selectedItems()]
        operator = self.operator_combo.currentText()
        template_content = self.template_edit.toPlainText().strip()

        if not selected_fields or not operator or not template_content:
            QMessageBox.warning(self, "입력 오류", "필드, 연산자, 템플릿 내용을 모두 입력해주세요.")
            return

        # 필드별 값 수집
        field_values = {}
        for row in range(self.value_table.rowCount()):
            field = self.value_table.item(row, 0).text()
            value = self.value_table.item(row, 1).text().strip()
            
            if not value:
                QMessageBox.warning(self, "입력 오류", f"'{field}' 필드의 값을 입력해주세요.")
                return
                
            # 숫자 필드라면 int로 변환
            if field in [API_FIELDS["QUANTITY"], API_FIELDS["COLOR_NUMBER"]]:
                try:
                    value = int(value)
                except ValueError:
                    pass  # 변환 실패 시 그대로 문자열
            
            field_values[field] = value

        self.condition = {
            "fields": selected_fields,
            "operator": operator,
            "value": field_values,
            "template": template_content
        }
        super().accept() 