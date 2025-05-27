"""
조건부 템플릿 생성/수정 다이얼로그 모듈
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QFormLayout, QDialogButtonBox, QMessageBox,
    QTextEdit
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from core.constants import ConfigKey, DELIVERY_METHODS, LOGISTICS_COMPANIES
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
        self.setMinimumWidth(400)
        
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
        
        # 필드 선택
        self.field_combo = QComboBox()
        self.field_combo.addItems([
            "pickup_at", "delivery_method", "logistics_company", "quantity",
            "store_name", "quality_name", "color_number", "color_code"
        ])
        form_layout.addRow("필드:", self.field_combo)
        
        # 연산자 선택
        self.operator_combo = QComboBox()
        self.operator_combo.addItems(["==", "!=", ">", "<", ">=", "<="])
        form_layout.addRow("연산자:", self.operator_combo)
        
        # 값 입력
        self.value_edit = QLineEdit()
        self.value_edit.setPlaceholderText("값을 입력하세요 (예: {today} 사용 가능)")
        form_layout.addRow("값:", self.value_edit)
        
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
        
    def _load_condition(self):
        """조건 데이터 로드"""
        if not self.condition:
            return
            
        # 필드 설정
        field = self.condition.get("field", "")
        index = self.field_combo.findText(field)
        if index >= 0:
            self.field_combo.setCurrentIndex(index)
        
        # 연산자 설정
        operator = self.condition.get("operator", "")
        index = self.operator_combo.findText(operator)
        if index >= 0:
            self.operator_combo.setCurrentIndex(index)
        
        # 값 설정
        self.value_edit.setText(str(self.condition.get("value", "")))
        
        # 내용 설정
        self.template_edit.setText(self.condition.get("template", ""))
    
    def accept(self):
        """확인 버튼 클릭 시 호출되는 메서드"""
        field = self.field_combo.currentText()
        operator = self.operator_combo.currentText()
        value = self.value_edit.text().strip()
        template_content = self.template_edit.toPlainText().strip()

        # 숫자 필드라면 int로 변환
        if field in ["quantity", "color_number"]:
            try:
                value = int(value)
            except ValueError:
                pass  # 변환 실패 시 그대로 문자열

        if not field or not operator or not value or not template_content:
            QMessageBox.warning(self, "입력 오류", "모든 필드와 템플릿 내용을 입력해주세요.")
            return

        self.condition = {
            "field": field,
            "operator": operator,
            "value": value,
            "template": template_content
        }
        super().accept() 