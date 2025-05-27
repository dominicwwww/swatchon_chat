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
        self.condition = condition
        
        self.setWindowTitle("조건부 템플릿" + (" 수정" if condition else " 생성"))
        self.setMinimumWidth(400)
        
        self._init_ui()
        if condition:
            self._load_condition()
        
    def _init_ui(self):
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
            "delivery_method", "logistics_company", "quantity",
            "store_name", "quality_name", "color_number", "color_code"
        ])
        form_layout.addRow("필드:", self.field_combo)
        
        # 연산자 선택
        self.operator_combo = QComboBox()
        self.operator_combo.addItems(["==", "!=", ">", ">=", "<", "<=", "in", "not in", "contains", "not contains"])
        form_layout.addRow("연산자:", self.operator_combo)
        
        # 값 입력
        self.value_edit = QLineEdit()
        self.value_edit.setPlaceholderText("값을 입력하세요")
        form_layout.addRow("값:", self.value_edit)
        
        # 조건 내용
        self.content_edit = QTextEdit()
        self.content_edit.setPlaceholderText("조건이 만족될 때 사용할 템플릿 내용을 입력하세요")
        self.content_edit.setMinimumHeight(100)
        form_layout.addRow("조건 내용:", self.content_edit)
        
        layout.addLayout(form_layout)
        
        # 버튼 영역
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        self.button_box.accepted.connect(self._on_accept)
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
        self.content_edit.setText(self.condition.get("content", ""))
    
    def _on_accept(self):
        """확인 버튼 클릭 시 호출되는 메서드"""
        # 필수 입력 검증
        field = self.field_combo.currentText()
        operator = self.operator_combo.currentText()
        value = self.value_edit.text().strip()
        content = self.content_edit.toPlainText().strip()
        
        if not all([field, operator, value, content]):
            QMessageBox.warning(self, "경고", "모든 필드를 입력해주세요.")
            return
        
        # 값 변환 (필요한 경우)
        if field == "quantity":
            try:
                value = int(value)
            except ValueError:
                QMessageBox.warning(self, "오류", "수량은 숫자로 입력해주세요.")
                return
        
        # 조건 데이터 생성
        condition_data = {
            "field": field,
            "operator": operator,
            "value": value,
            "content": content
        }
        
        self.condition = condition_data
        self.accept() 