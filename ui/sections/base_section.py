"""
기본 섹션 클래스 - 모든 기능 섹션의 기본 클래스
"""
from typing import Optional, Callable
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QStackedWidget
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QFont

from core.types import LogFunction
from ui.components.log_widget import LogWidget, LOG_INFO, LOG_DEBUG, LOG_WARNING, LOG_ERROR, LOG_SUCCESS
from ui.theme import get_theme

class BaseSection(QWidget):
    """
    모든 기능 섹션의 기본 클래스
    """
    
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        
        # 메인 레이아웃
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # 헤더 영역
        self.header_widget = QWidget()
        self.header_layout = QHBoxLayout(self.header_widget)
        self.header_layout.setContentsMargins(16, 16, 16, 16)
        
        # 제목
        self.title_label = QLabel(title)
        title_font = self.title_label.font()
        title_font.setPointSize(16)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        
        self.header_layout.addWidget(self.title_label)
        self.header_layout.addStretch()
        
        # 우측 헤더 버튼을 위한 영역
        self.header_buttons_layout = QHBoxLayout()
        self.header_buttons_layout.setSpacing(8)
        self.header_layout.addLayout(self.header_buttons_layout)
        
        self.main_layout.addWidget(self.header_widget)
        
        # 구분선
        self.separator = QFrame()
        self.separator.setFrameShape(QFrame.HLine)
        self.separator.setFrameShadow(QFrame.Sunken)
        self.separator.setFixedHeight(1)
        
        self.main_layout.addWidget(self.separator)
        
        # 콘텐츠 영역 (중앙)
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(16, 16, 16, 16)
        self.content_layout.setSpacing(16)
        
        self.main_layout.addWidget(self.content_widget, 1)  # stretch=1로 확장
        
        # 로그 영역 (하단)
        self.log_widget = LogWidget()
        self.main_layout.addWidget(self.log_widget)
        
        # 스타일 설정
        self._update_style()
        
        # 테마 변경 시 스타일 업데이트
        get_theme().theme_changed.connect(self._update_style)
    
    def add_header_button(self, text: str, on_click: Callable = None, primary: bool = False) -> QPushButton:
        """헤더에 버튼 추가"""
        button = QPushButton(text)
        button.setCursor(Qt.PointingHandCursor)
        
        if primary:
            # 강조 버튼 스타일
            theme = get_theme()
            button.setStyleSheet(f"""
                QPushButton {{
                    background-color: {theme.get_color("primary")};
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 6px 12px;
                    font-weight: bold;
                }}
                
                QPushButton:hover {{
                    background-color: {theme.get_color("accent")};
                }}
            """)
        
        if on_click:
            button.clicked.connect(on_click)
        
        self.header_buttons_layout.addWidget(button)
        return button
    
    def log(self, message: str, log_type: str = LOG_INFO):
        """로그 메시지 추가"""
        try:
            # 로그 타입 정규화
            if isinstance(log_type, str):
                # 이미 정의된 상수인지 확인
                if log_type in [LOG_INFO, LOG_DEBUG, LOG_WARNING, LOG_ERROR, LOG_SUCCESS]:
                    normalized_type = log_type
                else:
                    # 문자열을 소문자로 변환하여 매핑
                    type_mapping = {
                        "info": LOG_INFO,
                        "debug": LOG_DEBUG,
                        "warning": LOG_WARNING,
                        "error": LOG_ERROR,
                        "success": LOG_SUCCESS
                    }
                    normalized_type = type_mapping.get(log_type.lower(), LOG_INFO)
            else:
                # Enum 객체인 경우 value 속성 확인
                try:
                    if hasattr(log_type, 'value'):
                        type_str = str(log_type.value).lower()
                        type_mapping = {
                            "info": LOG_INFO,
                            "debug": LOG_DEBUG,
                            "warning": LOG_WARNING,
                            "error": LOG_ERROR,
                            "success": LOG_SUCCESS
                        }
                        normalized_type = type_mapping.get(type_str, LOG_INFO)
                    else:
                        normalized_type = LOG_INFO
                except Exception:
                    normalized_type = LOG_INFO
            
            # 로그 위젯에 메시지 추가
            self.log_widget.add_log(message, normalized_type)
            
        except Exception as e:
            # 로그 추가 실패 시 콘솔에 출력
            print(f"로그 추가 오류: {str(e)}")
            print(f"메시지: {message}, 타입: {log_type}")
            # 최소한 콘솔에는 메시지 출력
            print(f"[{log_type}] {message}")
    
    def clear_logs(self):
        """로그 지우기"""
        self.log_widget.clear_logs()
    
    def _update_style(self):
        """테마에 맞게 스타일 업데이트"""
        theme = get_theme()
        
        # 헤더 스타일
        self.header_widget.setStyleSheet(f"""
            QWidget {{
                background-color: {theme.get_color("background")};
            }}
        """)
        
        # 구분선 스타일
        self.separator.setStyleSheet(f"""
            background-color: {theme.get_color("divider")};
        """)
        
        # 콘텐츠 영역 스타일
        self.content_widget.setStyleSheet(f"""
            QWidget {{
                background-color: {theme.get_color("background")};
            }}
        """)
    
    def setup_content(self):
        """콘텐츠 설정 - 하위 클래스에서 구현"""
        pass
    
    def on_section_activated(self):
        """섹션이 활성화될 때 호출 - 하위 클래스에서 구현"""
        pass
    
    def on_section_deactivated(self):
        """섹션이 비활성화될 때 호출 - 하위 클래스에서 구현"""
        pass 