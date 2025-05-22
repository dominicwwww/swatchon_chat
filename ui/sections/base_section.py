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
        # LogType enum 값 변환 (이미 문자열 상수라면 그대로 사용)
        if isinstance(log_type, str):
            # 이미 문자열 상수이면 그대로 사용
            if log_type in [LOG_INFO, LOG_DEBUG, LOG_WARNING, LOG_ERROR, LOG_SUCCESS]:
                pass
            # 문자열 형태의 로그 레벨인 경우 적절한 상수로 변환
            elif log_type.lower() == "info":
                log_type = LOG_INFO
            elif log_type.lower() == "warning":
                log_type = LOG_WARNING
            elif log_type.lower() == "error":
                log_type = LOG_ERROR
            elif log_type.lower() == "success":
                log_type = LOG_SUCCESS
            elif log_type.lower() == "debug":
                log_type = LOG_DEBUG
            else:
                # 알 수 없는 로그 타입은 기본값 사용
                log_type = LOG_INFO
                print(f"알 수 없는 로그 타입: {log_type}, 기본값(INFO)으로 설정")
        else:
            # LogType enum 객체인 경우 value 값을 사용
            try:
                log_type_value = getattr(log_type, "value", None)
                if log_type_value:
                    # 문자열로 변환 후 매핑
                    log_type_str = str(log_type_value).lower()
                    if log_type_str == "info":
                        log_type = LOG_INFO
                    elif log_type_str == "warning":
                        log_type = LOG_WARNING
                    elif log_type_str == "error":
                        log_type = LOG_ERROR
                    elif log_type_str == "success":
                        log_type = LOG_SUCCESS
                    elif log_type_str == "debug":
                        log_type = LOG_DEBUG
                    else:
                        log_type = LOG_INFO
                else:
                    log_type = LOG_INFO
            except Exception as e:
                # 오류 발생 시 기본값 사용
                print(f"로그 타입 변환 오류: {str(e)}, 기본값(INFO)으로 설정")
                log_type = LOG_INFO
            
        try:
            self.log_widget.add_log(message, log_type)
        except Exception as e:
            # 로그 추가 오류 시 콘솔에 출력
            print(f"로그 추가 오류: {str(e)}")
            print(f"메시지: {message}, 타입: {log_type}")
    
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