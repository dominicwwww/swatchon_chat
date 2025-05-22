"""
테마 관리 모듈 - 다크 모드 및 라이트 모드 지원
"""
from enum import Enum
from typing import Dict, Any
from PySide6.QtCore import QObject, Signal, Property, QSettings, Slot, Qt
from PySide6.QtGui import QColor, QPalette
from core.types import ThemeMode

class Theme(QObject):
    """
    애플리케이션 테마 관리 클래스
    """
    # 테마 변경 시그널
    theme_changed = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._settings = QSettings("SwatchOn", "KakaoAutomation")
        self._current_theme = self._settings.value("theme", ThemeMode.SYSTEM.value)
        self._colors = self._get_theme_colors(self._current_theme)
    
    def _get_theme_colors(self, theme_name: str) -> Dict[str, Any]:
        """테마별 색상 정보 가져오기"""
        # 시스템 테마 적용
        if theme_name == ThemeMode.SYSTEM.value:
            # 시스템이 다크 모드인지 확인
            from PySide6.QtGui import QGuiApplication
            app = QGuiApplication.instance()
            if app.styleHints().colorScheme() == Qt.ColorScheme.Dark:
                theme_name = ThemeMode.DARK.value
            else:
                theme_name = ThemeMode.LIGHT.value
        
        # 다크 모드
        if theme_name == ThemeMode.DARK.value:
            return {
                # 기본 색상
                "background": "#1E1E2E",
                "foreground": "#CDD6F4",
                "sidebar_bg": "#181825",
                "card_bg": "#313244",
                
                # 강조 색상
                "primary": "#89B4FA",
                "secondary": "#F5C2E7",
                "accent": "#94E2D5",
                
                # 상태 색상
                "success": "#A6E3A1",
                "warning": "#F9E2AF",
                "error": "#F38BA8",
                "info": "#74C7EC",
                
                # 경계선 및 분리선
                "border": "#45475A",
                "divider": "#313244",
                
                # 스크롤바 및 기타
                "scrollbar": "#45475A",
                "scrollbar_hover": "#585B70",
                
                # 로그 배경
                "log_bg": "#11111B",
                
                # 그림자
                "shadow": "#00000066",
                
                # 텍스트 색상
                "text_primary": "#CDD6F4",
                "text_secondary": "#BAC2DE",
                "text_disabled": "#6C7086",
                
                # 입력 필드
                "input_bg": "#313244",
                "input_border": "#45475A",
                "input_focused_border": "#89B4FA",
                
                # 버튼 색상
                "button_primary_bg": "#89B4FA",
                "button_primary_fg": "#1E1E2E",
                "button_secondary_bg": "#585B70",
                "button_secondary_fg": "#CDD6F4",
            }
        # 라이트 모드
        else:
            return {
                # 기본 색상
                "background": "#EFF1F5",
                "foreground": "#4C4F69",
                "sidebar_bg": "#E6E9EF", 
                "card_bg": "#DCE0E8",
                
                # 강조 색상
                "primary": "#1E66F5",
                "secondary": "#EA76CB",
                "accent": "#179299",
                
                # 상태 색상
                "success": "#40A02B",
                "warning": "#DF8E1D",
                "error": "#D20F39",
                "info": "#209FB5",
                
                # 경계선 및 분리선
                "border": "#BCC0CC",
                "divider": "#DCE0E8",
                
                # 스크롤바 및 기타
                "scrollbar": "#BCC0CC",
                "scrollbar_hover": "#9CA0B0",
                
                # 로그 배경
                "log_bg": "#CCD0DA",
                
                # 그림자
                "shadow": "#00000033",
                
                # 텍스트 색상
                "text_primary": "#4C4F69",
                "text_secondary": "#5C5F77",
                "text_disabled": "#ACB0BE",
                
                # 입력 필드
                "input_bg": "#FFFFFF",
                "input_border": "#BCC0CC",
                "input_focused_border": "#1E66F5",
                
                # 버튼 색상
                "button_primary_bg": "#1E66F5",
                "button_primary_fg": "#FFFFFF",
                "button_secondary_bg": "#DCE0E8",
                "button_secondary_fg": "#4C4F69",
            }
    
    @Slot(str)
    def set_theme(self, theme_name: str) -> None:
        """테마 설정"""
        if theme_name not in [t.value for t in ThemeMode]:
            theme_name = ThemeMode.SYSTEM.value
        
        self._current_theme = theme_name
        self._colors = self._get_theme_colors(theme_name)
        self._settings.setValue("theme", theme_name)
        self.theme_changed.emit(theme_name)
    
    def get_color(self, color_name: str) -> str:
        """색상 가져오기"""
        return self._colors.get(color_name, "#000000")
    
    def get_theme_name(self) -> str:
        """현재 테마 이름 가져오기"""
        return self._current_theme
    
    def create_palette(self) -> QPalette:
        """현재 테마에 맞는 QPalette 생성"""
        palette = QPalette()
        
        # 기본 색상 설정
        palette.setColor(QPalette.Window, QColor(self.get_color("background")))
        palette.setColor(QPalette.WindowText, QColor(self.get_color("text_primary")))
        palette.setColor(QPalette.Base, QColor(self.get_color("card_bg")))
        palette.setColor(QPalette.AlternateBase, QColor(self.get_color("sidebar_bg")))
        palette.setColor(QPalette.ToolTipBase, QColor(self.get_color("card_bg")))
        palette.setColor(QPalette.ToolTipText, QColor(self.get_color("text_primary")))
        palette.setColor(QPalette.Text, QColor(self.get_color("text_primary")))
        palette.setColor(QPalette.Button, QColor(self.get_color("button_secondary_bg")))
        palette.setColor(QPalette.ButtonText, QColor(self.get_color("button_secondary_fg")))
        palette.setColor(QPalette.Link, QColor(self.get_color("primary")))
        palette.setColor(QPalette.Highlight, QColor(self.get_color("primary")))
        palette.setColor(QPalette.HighlightedText, QColor("#FFFFFF"))
        
        # 비활성화 상태 색상
        palette.setColor(QPalette.Disabled, QPalette.WindowText, QColor(self.get_color("text_disabled")))
        palette.setColor(QPalette.Disabled, QPalette.Text, QColor(self.get_color("text_disabled")))
        palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(self.get_color("text_disabled")))
        
        return palette
    
    def get_stylesheet(self) -> str:
        """현재 테마에 맞는 기본 스타일시트 생성"""
        return f"""
        QWidget {{
            background-color: {self.get_color("background")};
            color: {self.get_color("text_primary")};
            font-family: 'Segoe UI', 'Noto Sans', sans-serif;
        }}
        
        QMainWindow, QDialog {{
            background-color: {self.get_color("background")};
        }}
        
        QScrollBar:vertical {{
            background-color: {self.get_color("background")};
            width: 12px;
            margin: 0;
        }}
        
        QScrollBar::handle:vertical {{
            background-color: {self.get_color("scrollbar")};
            min-height: 20px;
            border-radius: 6px;
        }}
        
        QScrollBar::handle:vertical:hover {{
            background-color: {self.get_color("scrollbar_hover")};
        }}
        
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        
        QScrollBar:horizontal {{
            background-color: {self.get_color("background")};
            height: 12px;
            margin: 0;
        }}
        
        QScrollBar::handle:horizontal {{
            background-color: {self.get_color("scrollbar")};
            min-width: 20px;
            border-radius: 6px;
        }}
        
        QScrollBar::handle:horizontal:hover {{
            background-color: {self.get_color("scrollbar_hover")};
        }}
        
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0px;
        }}
        
        QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox {{
            background-color: {self.get_color("input_bg")};
            border: 1px solid {self.get_color("input_border")};
            border-radius: 4px;
            padding: 4px;
            color: {self.get_color("text_primary")};
        }}
        
        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus, QSpinBox:focus {{
            border: 1px solid {self.get_color("input_focused_border")};
        }}
        
        QPushButton {{
            background-color: {self.get_color("button_secondary_bg")};
            color: {self.get_color("button_secondary_fg")};
            border: none;
            border-radius: 4px;
            padding: 6px 12px;
            font-weight: bold;
        }}
        
        QPushButton:hover {{
            background-color: {self.get_color("button_primary_bg")};
            color: {self.get_color("button_primary_fg")};
        }}
        
        QPushButton:pressed {{
            background-color: {self.get_color("primary")};
            color: {self.get_color("button_primary_fg")};
        }}
        
        QPushButton:disabled {{
            background-color: {self.get_color("button_secondary_bg")};
            color: {self.get_color("text_disabled")};
        }}
        
        QTableView, QListView, QTreeView {{
            background-color: {self.get_color("card_bg")};
            border: 1px solid {self.get_color("border")};
            border-radius: 4px;
        }}
        
        QTableView::item, QListView::item, QTreeView::item {{
            padding: 4px;
        }}
        
        QTableView::item:selected, QListView::item:selected, QTreeView::item:selected {{
            background-color: {self.get_color("primary")};
            color: white;
        }}
        
        QHeaderView::section {{
            background-color: {self.get_color("sidebar_bg")};
            color: {self.get_color("text_primary")};
            padding: 4px;
            border: none;
            border-right: 1px solid {self.get_color("border")};
            border-bottom: 1px solid {self.get_color("border")};
        }}
        
        QTabWidget::pane {{
            border: 1px solid {self.get_color("border")};
            border-radius: 4px;
        }}
        
        QTabBar::tab {{
            background-color: {self.get_color("sidebar_bg")};
            color: {self.get_color("text_primary")};
            padding: 8px 12px;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
            border: 1px solid {self.get_color("border")};
            margin-right: 2px;
        }}
        
        QTabBar::tab:selected {{
            background-color: {self.get_color("background")};
            border-bottom-color: {self.get_color("background")};
        }}
        
        QGroupBox {{
            border: 1px solid {self.get_color("border")};
            border-radius: 4px;
            margin-top: 1.5ex;
        }}
        
        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top center;
            padding: 0 5px;
            color: {self.get_color("text_primary")};
        }}
        
        QProgressBar {{
            border: 1px solid {self.get_color("border")};
            border-radius: 4px;
            text-align: center;
            background-color: {self.get_color("card_bg")};
        }}
        
        QProgressBar::chunk {{
            background-color: {self.get_color("primary")};
            width: 1px;
        }}
        
        QMenu {{
            background-color: {self.get_color("card_bg")};
            border: 1px solid {self.get_color("border")};
            border-radius: 4px;
        }}
        
        QMenu::item {{
            padding: 5px 25px 5px 25px;
        }}
        
        QMenu::item:selected {{
            background-color: {self.get_color("primary")};
            color: white;
        }}
        """

# 싱글톤 인스턴스
_theme_instance = None

def get_theme() -> Theme:
    """테마 싱글톤 인스턴스 가져오기"""
    global _theme_instance
    if _theme_instance is None:
        _theme_instance = Theme()
    return _theme_instance 