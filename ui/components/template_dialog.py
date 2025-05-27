"""
템플릿 관리 다이얼로그 모듈
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QMessageBox, QDialogButtonBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from core.constants import ConfigKey
from core.logger import get_logger
from core.config import ConfigManager
from ui.theme import get_theme
from ui.components.condition_dialog import ConditionDialog

class TemplateDialog(QDialog):
    """템플릿 관리 다이얼로그 클래스"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = get_logger(__name__)
        self.config = ConfigManager()
        self.theme = get_theme()
        
        self.setWindowTitle("템플릿 관리")
        self.setMinimumWidth(400)
        self.setMinimumHeight(500)
        
        self._init_ui()
        self._load_templates()
        
    def _init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 템플릿 목록
        self.template_list = QListWidget()
        self.template_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {self.theme.colors['card_bg']};
                border: 1px solid {self.theme.colors['border']};
                border-radius: 4px;
                padding: 5px;
            }}
            QListWidget::item {{
                color: {self.theme.colors['text_primary']};
                padding: 5px;
                border-bottom: 1px solid {self.theme.colors['border']};
            }}
            QListWidget::item:selected {{
                background-color: {self.theme.colors['primary']};
                color: white;
            }}
        """)
        layout.addWidget(self.template_list)
        
        # 버튼 영역
        button_layout = QHBoxLayout()
        
        # 새로 만들기 버튼
        self.new_btn = QPushButton("새로 만들기")
        self.new_btn.setIcon(QIcon("assets/icons/add.png"))
        self.new_btn.clicked.connect(self._on_new_clicked)
        button_layout.addWidget(self.new_btn)
        
        # 수정 버튼
        self.edit_btn = QPushButton("수정")
        self.edit_btn.setIcon(QIcon("assets/icons/edit.png"))
        self.edit_btn.clicked.connect(self._on_edit_clicked)
        button_layout.addWidget(self.edit_btn)
        
        # 삭제 버튼
        self.delete_btn = QPushButton("삭제")
        self.delete_btn.setIcon(QIcon("assets/icons/delete.png"))
        self.delete_btn.clicked.connect(self._on_delete_clicked)
        button_layout.addWidget(self.delete_btn)
        
        button_layout.addStretch()
        
        # 확인/취소 버튼
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        button_layout.addWidget(self.button_box)
        
        layout.addLayout(button_layout)
        
    def _load_templates(self):
        """템플릿 목록 로드"""
        templates = self.config.get(ConfigKey.TEMPLATES.value, [])
        self.template_list.clear()
        
        for template in templates:
            item = QListWidgetItem(template["name"])
            item.setData(Qt.UserRole, template)
            self.template_list.addItem(item)
    
    def _on_new_clicked(self):
        """새로 만들기 버튼 클릭 시 호출되는 메서드"""
        dialog = ConditionDialog(self)
        if dialog.exec():
            self._load_templates()
    
    def _on_edit_clicked(self):
        """수정 버튼 클릭 시 호출되는 메서드"""
        current_item = self.template_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "경고", "수정할 템플릿을 선택해주세요.")
            return
            
        template = current_item.data(Qt.UserRole)
        dialog = ConditionDialog(self, template)
        if dialog.exec():
            self._load_templates()
    
    def _on_delete_clicked(self):
        """삭제 버튼 클릭 시 호출되는 메서드"""
        current_item = self.template_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "경고", "삭제할 템플릿을 선택해주세요.")
            return
            
        template = current_item.data(Qt.UserRole)
        reply = QMessageBox.question(
            self,
            "확인",
            f"'{template['name']}' 템플릿을 삭제하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            templates = self.config.get(ConfigKey.TEMPLATES.value, [])
            templates = [t for t in templates if t["name"] != template["name"]]
            self.config.set(ConfigKey.TEMPLATES.value, templates)
            self.config.save()
            self._load_templates() 