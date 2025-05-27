"""
필터 다이얼로그 모듈
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QFormLayout, QDialogButtonBox, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from core.constants import DELIVERY_METHODS, LOGISTICS_COMPANIES
from core.logger import get_logger
from ui.theme import get_theme

class FilterDialog(QDialog):
    """필터 다이얼로그 클래스"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = get_logger(__name__)
        self.theme = get_theme()
        
        self.setWindowTitle("필터")
        self.setMinimumWidth(400)
        
        self._init_ui()
        
    def _init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 폼 레이아웃
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        
        # 스토어명
        self.store_name_edit = QLineEdit()
        self.store_name_edit.setPlaceholderText("스토어명을 입력하세요")
        form_layout.addRow("스토어명:", self.store_name_edit)
        
        # 품질명
        self.quality_name_edit = QLineEdit()
        self.quality_name_edit.setPlaceholderText("품질명을 입력하세요")
        form_layout.addRow("품질명:", self.quality_name_edit)
        
        # 컬러번호
        self.color_number_edit = QLineEdit()
        self.color_number_edit.setPlaceholderText("컬러번호를 입력하세요")
        form_layout.addRow("컬러번호:", self.color_number_edit)
        
        # 컬러코드
        self.color_code_edit = QLineEdit()
        self.color_code_edit.setPlaceholderText("컬러코드를 입력하세요")
        form_layout.addRow("컬러코드:", self.color_code_edit)
        
        # 배송방법
        self.delivery_method_combo = QComboBox()
        self.delivery_method_combo.addItem("전체", "")
        for key, value in DELIVERY_METHODS.items():
            self.delivery_method_combo.addItem(value, key)
        form_layout.addRow("배송방법:", self.delivery_method_combo)
        
        # 물류회사
        self.logistics_company_combo = QComboBox()
        self.logistics_company_combo.addItem("전체", "")
        for key, value in LOGISTICS_COMPANIES.items():
            self.logistics_company_combo.addItem(value, key)
        form_layout.addRow("물류회사:", self.logistics_company_combo)
        
        layout.addLayout(form_layout)
        
        # 버튼 영역
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)
    
    def get_filter_data(self):
        """필터 데이터 반환"""
        return {
            "store_name": self.store_name_edit.text().strip(),
            "quality_name": self.quality_name_edit.text().strip(),
            "color_number": self.color_number_edit.text().strip(),
            "color_code": self.color_code_edit.text().strip(),
            "delivery_method": self.delivery_method_combo.currentData(),
            "logistics_company": self.logistics_company_combo.currentData()
        } 