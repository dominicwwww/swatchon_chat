"""
컨트롤 바 컴포넌트 - 상단 제어 버튼 및 다크 모드 전환
"""
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QComboBox, 
    QLabel, QSpacerItem, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QIcon, QPixmap
import qtawesome as qta

from core.types import ThemeMode
from ui.theme import get_theme

class ThemeToggleButton(QPushButton):
    """테마 토글 버튼 - 다크모드/라이트모드 전환"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(32, 32)
        
        # 현재 테마로 버튼 상태 초기화
        theme = get_theme().get_theme_name()
        if theme == ThemeMode.DARK.value:
            self.setChecked(True)
        elif theme == ThemeMode.LIGHT.value:
            self.setChecked(False)
        else:  # 시스템 테마
            # 현재 실제 적용된 색상으로 결정
            # 다크 모드에 사용되는 배경 색상인지 확인
            bg_color = get_theme().get_color("background")
            is_dark = self._is_dark_color(bg_color)
            self.setChecked(is_dark)
        
        # 스타일 업데이트
        self._update_style()
    
    def _is_dark_color(self, color_str):
        """색상이 어두운지 확인"""
        # 16진수 색상에서 RGB 값 추출
        color_str = color_str.lstrip('#')
        if len(color_str) == 6:
            r, g, b = int(color_str[0:2], 16), int(color_str[2:4], 16), int(color_str[4:6], 16)
            # 밝기 계산: 어두운 색상이면 True 반환
            brightness = (r * 299 + g * 587 + b * 114) / 1000
            return brightness < 128
        return False
    
    def _update_style(self):
        """현재 상태에 따라 스타일 업데이트"""
        theme = get_theme()
        
        # 아이콘 설정
        if self.isChecked():
            # 다크 모드: 달 아이콘
            icon_style = f"color: {theme.get_color('primary')};"
            self.setToolTip("라이트 모드로 전환")
        else:
            # 라이트 모드: 해 아이콘
            icon_style = f"color: {theme.get_color('warning')};"
            self.setToolTip("다크 모드로 전환")
        
        # CSS 스타일 업데이트
        self.setStyleSheet(f"""
            ThemeToggleButton {{
                background-color: {theme.get_color('card_bg')};
                border: 1px solid {theme.get_color('border')};
                border-radius: 16px;
                padding: 4px;
                {icon_style}
            }}
            
            ThemeToggleButton:hover {{
                background-color: {theme.get_color('primary')};
                color: white;
            }}
        """)
        
        # 상태에 따라 아이콘 설정
        if self.isChecked():
            self.setText("🌙")  # 달 이모지
        else:
            self.setText("☀️")  # 해 이모지

class ControlBar(QWidget):
    """
    상단 제어 버튼 및 테마 변경 컨트롤 바
    """
    
    # 테마 변경 시그널
    theme_changed = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 레이아웃 설정
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # 왼쪽 여백
        layout.addItem(QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        
        # 업데이트 체크 버튼
        self.update_check_button = QPushButton()
        self.update_check_button.setIcon(qta.icon('ph.arrow-clockwise'))
        self.update_check_button.setToolTip("업데이트 확인")
        self.update_check_button.setFixedSize(32, 32)
        self.update_check_button.setCursor(Qt.PointingHandCursor)
        layout.addWidget(self.update_check_button)
        
        # 테마 토글 버튼
        self.theme_toggle = ThemeToggleButton()
        self.theme_toggle.clicked.connect(self._on_theme_toggled)
        
        # 레이아웃에 추가
        layout.addWidget(QLabel("테마:"))
        layout.addWidget(self.theme_toggle)
        
        # 스타일 업데이트
        self._update_style()
        
        # 테마 변경 이벤트 연결
        get_theme().theme_changed.connect(self._update_style)
    
    def add_update_check_button(self, callback):
        """업데이트 체크 버튼 클릭 이벤트 연결"""
        self.update_check_button.clicked.connect(callback)
    
    def _on_theme_toggled(self, checked):
        """테마 토글 버튼 클릭 이벤트 처리"""
        if checked:
            # 다크모드로 전환
            get_theme().set_theme(ThemeMode.DARK.value)
        else:
            # 라이트모드로 전환
            get_theme().set_theme(ThemeMode.LIGHT.value)
        
        # 버튼 상태 업데이트
        self.theme_toggle._update_style()
    
    def _update_style(self):
        """테마에 맞게 스타일 업데이트"""
        theme = get_theme()
        
        # 업데이트 체크 버튼 스타일
        self.update_check_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.get_color('card_bg')};
                border: 1px solid {theme.get_color('border')};
                border-radius: 16px;
                padding: 4px;
                color: {theme.get_color('primary')};
            }}
            
            QPushButton:hover {{
                background-color: {theme.get_color('primary')};
                color: white;
            }}
        """)
        
        # 컨트롤바 스타일
        self.setStyleSheet(f"""
            ControlBar {{
                background-color: {theme.get_color("sidebar_bg")};
                border-bottom: 1px solid {theme.get_color("border")};
            }}
        """)
        
        # 테마 토글 버튼 업데이트
        self.theme_toggle._update_style() 