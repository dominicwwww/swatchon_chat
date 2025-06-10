"""
로그 위젯 컴포넌트 - 로그 메시지 표시
"""
from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QPlainTextEdit, QHBoxLayout, 
    QPushButton, QLabel, QFrame
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QFont, QColor, QTextCharFormat, QTextCursor, QIcon

from core.types import LogType
from ui.theme import get_theme

# 로그 타입 문자열 상수 (재귀 호출 문제 방지)
LOG_INFO = "info"
LOG_DEBUG = "debug"
LOG_WARNING = "warning"
LOG_ERROR = "error"
LOG_SUCCESS = "success"

class LogWidget(QWidget):
    """
    로그 메시지를 표시하는 위젯
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 메인 레이아웃
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # 헤더 레이아웃
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        # 헤더 제목
        title_label = QLabel("로그")
        title_font = title_label.font()
        title_font.setBold(True)
        title_label.setFont(title_font)
        
        # 헤더 버튼
        clear_button = QPushButton("지우기")
        clear_button.setFixedSize(70, 24)
        clear_button.setCursor(Qt.PointingHandCursor)
        clear_button.clicked.connect(self.clear_logs)
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(clear_button)
        
        layout.addLayout(header_layout)
        
        # 로그 텍스트 영역
        self.log_text = QPlainTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumBlockCount(10000)  # 최대 로그 줄 수 제한
        self.log_text.setMinimumHeight(400)  # 최소 높이 설정
        
        # 글꼴 설정
        log_font = QFont("Consolas, 'Courier New', monospace")
        log_font.setPointSize(9)
        self.log_text.setFont(log_font)
        
        # 스타일 설정 (초기화)
        self.log_text.setStyleSheet("""
            QPlainTextEdit {
                background-color: #11111B;
                color: #CDD6F4;
                border: 1px solid #45475A;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        
        # 로그 색상 고정 정의 (테마 변경에 영향받지 않게)
        self.log_colors = {
            LOG_INFO: QColor("#CDD6F4"),    # 정보 (밝은 텍스트)
            LOG_DEBUG: QColor("#9399B2"),   # 디버그 (회색)
            LOG_WARNING: QColor("#F9E2AF"), # 경고 (노랑)
            LOG_ERROR: QColor("#F38BA8"),   # 오류 (빨강)
            LOG_SUCCESS: QColor("#A6E3A1")  # 성공 (녹색)
        }
        
        layout.addWidget(self.log_text)
        
        # 테마 변경 이벤트 연결
        theme = get_theme()
        theme.theme_changed.connect(self._update_style)
        
        # 초기 스타일 적용
        self._update_style()
    
    def _update_style(self):
        """테마에 맞게 스타일 업데이트"""
        theme = get_theme()
        
        # 로그 텍스트 스타일 (배경만 업데이트)
        log_bg = theme.get_color("log_bg")
        border_color = theme.get_color("border")
        
        self.log_text.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: {log_bg};
                color: #CDD6F4;
                border: 1px solid {border_color};
                border-radius: 4px;
                padding: 8px;
            }}
        """)
    
    def add_log(self, message: str, log_type: str = LOG_INFO):
        """로그 메시지 추가"""
        try:
            # 텍스트 포맷 설정
            format = QTextCharFormat()
            
            # log_type에 따라 미리 정의된 색상 사용
            color = self.log_colors.get(log_type, QColor("#CDD6F4"))
            format.setForeground(color)
            
            # 성공 또는 오류 로그는 굵게 표시
            if log_type in [LOG_SUCCESS, LOG_ERROR]:
                format.setFontWeight(QFont.Bold)
            
            # 현재 문서에 텍스트가 있으면 개행 추가
            text = self.log_text.toPlainText()
            if text and not text.endswith("\n"):
                message = "\n" + message
            
            # 커서 생성 및 끝으로 이동
            cursor = self.log_text.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            
            # 포맷 적용하여 메시지 추가
            cursor.setCharFormat(format)
            cursor.insertText(message)
            
            # 커서를 항상 문서 끝으로 이동
            self.log_text.setTextCursor(cursor)
            self.log_text.ensureCursorVisible()
            
            # 터미널에도 로그 출력 (디버깅용)
            print(f"[LOG] {message}")
            
        except Exception as e:
            # 오류가 발생하면 터미널에 출력
            print(f"로그 추가 중 오류 발생: {str(e)}")
    
    def clear_logs(self):
        """로그 메시지 지우기"""
        self.log_text.clear()
    
    def save_logs(self, file_path: str) -> bool:
        """로그 메시지를 파일로 저장"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(self.log_text.toPlainText())
            print(f"로그를 파일에 저장했습니다: {file_path}")
            return True
        except Exception as e:
            print(f"로그 저장 실패: {str(e)}")
            return False 