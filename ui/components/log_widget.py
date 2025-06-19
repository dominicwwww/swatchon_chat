"""
로그 위젯 컴포넌트 - 로그 메시지 표시
"""
from typing import Optional, List, Tuple
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QPlainTextEdit, QHBoxLayout, 
    QPushButton, QLabel, QFrame
)
from PySide6.QtCore import Qt, Signal, QSize, QTimer
from PySide6.QtGui import QFont, QColor, QTextCharFormat, QTextCursor, QIcon

from core.types import LogType
from ui.theme import get_theme

# 로그 타입 문자열 상수 (재귀 호출 문제 방지)
LOG_INFO = "info"
LOG_DEBUG = "debug"
LOG_WARNING = "warning"
LOG_ERROR = "error"
LOG_SUCCESS = "success"

# 로그 메시지 최대 길이
MAX_LOG_MESSAGE_LENGTH = 500

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
        self.log_text.setMaximumBlockCount(1000)  # 최대 로그 줄 수 제한
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
        
        # 로그 버퍼링 설정
        self._log_buffer: List[Tuple[str, str]] = []
        self._buffer_timer = QTimer()
        self._buffer_timer.timeout.connect(self._flush_buffer)
        self._buffer_timer.start(100)  # 100ms마다 버퍼 플러시
        
        # 예외 처리 플래그
        self._handling_exception = False
    
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
    
    def _add_log_internal(self, message: str, log_type: str = LOG_INFO):
        """내부 로그 추가 메서드 (버퍼링 없이 직접 추가)"""
        try:
            # 여러 줄 메시지 처리: 빈 줄/공백만 있는 줄은 무시
            for line in str(message).splitlines():
                if not line.strip():
                    continue
                
                # 메시지 길이 제한
                msg = line
                if len(msg) > MAX_LOG_MESSAGE_LENGTH:
                    msg = msg[:MAX_LOG_MESSAGE_LENGTH] + "... (생략됨)"
                
                # 텍스트 포맷 설정
                format = QTextCharFormat()
                color = self.log_colors.get(log_type, QColor("#CDD6F4"))
                format.setForeground(color)
                if log_type in [LOG_SUCCESS, LOG_ERROR]:
                    format.setFontWeight(QFont.Bold)
                
                text = self.log_text.toPlainText()
                if text and not text.endswith("\n"):
                    msg = "\n" + msg
                
                cursor = self.log_text.textCursor()
                cursor.movePosition(QTextCursor.MoveOperation.End)
                cursor.setCharFormat(format)
                cursor.insertText(msg)
                
                self.log_text.setTextCursor(cursor)
                self.log_text.ensureCursorVisible()
                print(f"[LOG] {msg}")
                
        except Exception as e:
            if not self._handling_exception:
                self._handling_exception = True
                try:
                    print(f"로그 추가 중 오류 발생: {str(e)}")
                finally:
                    self._handling_exception = False
    
    def _flush_buffer(self):
        """로그 버퍼 플러시"""
        if self._log_buffer:
            try:
                for message, log_type in self._log_buffer:
                    self._add_log_internal(message, log_type)
            except Exception as e:
                print(f"로그 버퍼 플러시 중 오류: {str(e)}")
            finally:
                self._log_buffer.clear()
    
    def add_log(self, message: str, log_type: str = LOG_INFO):
        """로그 메시지 추가 (버퍼링 사용)"""
        try:
            self._log_buffer.append((message, log_type))
        except Exception as e:
            # 버퍼링 실패 시 직접 추가
            self._add_log_internal(message, log_type)
    
    def clear_logs(self):
        """로그 메시지 지우기"""
        self.log_text.clear()
        self._log_buffer.clear()
    
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