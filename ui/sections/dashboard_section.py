"""
대시보드 섹션 - 애플리케이션의 메인 화면
"""
from typing import Dict, Any, List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFrame, QGridLayout, QSpacerItem, QSizePolicy
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from core.types import LogType
from ui.sections.base_section import BaseSection
from ui.theme import get_theme

class StatCard(QFrame):
    """통계 카드 위젯"""
    
    def __init__(self, title: str, value: str, icon: str = None, parent=None):
        super().__init__(parent)
        
        # 테두리 및 그림자 설정
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)
        
        # 레이아웃
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)
        
        # 제목
        title_label = QLabel(title)
        title_font = title_label.font()
        title_font.setPointSize(10)
        title_label.setFont(title_font)
        
        # 값
        value_label = QLabel(value)
        value_font = value_label.font()
        value_font.setPointSize(24)
        value_font.setBold(True)
        value_label.setFont(value_font)
        
        # 레이아웃에 추가
        layout.addWidget(title_label)
        layout.addWidget(value_label)
        
        # 스타일 업데이트
        self._update_style()
        
        # 테마 변경 이벤트 연결
        get_theme().theme_changed.connect(self._update_style)
    
    def _update_style(self):
        """테마에 맞게 스타일 업데이트"""
        theme = get_theme()
        
        self.setStyleSheet(f"""
            StatCard {{
                background-color: {theme.get_color("card_bg")};
                border-radius: 8px;
                border: 1px solid {theme.get_color("border")};
            }}
        """)

class DashboardSection(BaseSection):
    """
    대시보드 섹션 - 애플리케이션의 메인 화면
    """
    
    def __init__(self, parent=None):
        super().__init__("대시보드", parent)
        
        # 콘텐츠 설정
        self.setup_content()
    
    def setup_content(self):
        """콘텐츠 설정"""
        # 환영 메시지
        welcome_label = QLabel("안녕하세요, SwatchOn 카카오톡 자동화 시스템입니다.")
        welcome_font = welcome_label.font()
        welcome_font.setPointSize(14)
        welcome_label.setFont(welcome_font)
        welcome_label.setAlignment(Qt.AlignLeft)
        
        self.content_layout.addWidget(welcome_label)
        
        # 설명 텍스트
        description_label = QLabel(
            "이 애플리케이션은 SwatchOn의 업무 자동화를 위해 설계되었습니다. "
            "왼쪽 사이드바를 통해 다양한 기능에 접근할 수 있습니다."
        )
        description_label.setWordWrap(True)
        self.content_layout.addWidget(description_label)
        
        # 구분선
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet(f"background-color: {get_theme().get_color('divider')};")
        separator.setFixedHeight(1)
        self.content_layout.addWidget(separator)
        
        # 통계 카드 영역
        stats_layout = QGridLayout()
        stats_layout.setContentsMargins(0, 16, 0, 16)
        stats_layout.setSpacing(16)
        
        # 통계 카드 추가
        stats_layout.addWidget(StatCard("출고 요청", "0"), 0, 0)
        stats_layout.addWidget(StatCard("출고 확인", "0"), 0, 1)
        stats_layout.addWidget(StatCard("발주 확인", "0"), 0, 2)
        stats_layout.addWidget(StatCard("스와치 발주", "0"), 1, 0)
        stats_layout.addWidget(StatCard("픽업 요청", "0"), 1, 1)
        stats_layout.addWidget(StatCard("총 메시지", "0"), 1, 2)
        
        self.content_layout.addLayout(stats_layout)
        
        # 최근 활동 섹션
        activity_label = QLabel("최근 활동")
        activity_font = activity_label.font()
        activity_font.setPointSize(14)
        activity_font.setBold(True)
        activity_label.setFont(activity_font)
        self.content_layout.addWidget(activity_label)
        
        # 활동 내역이 없는 경우 메시지
        no_activity_label = QLabel("아직 활동 내역이 없습니다.")
        no_activity_label.setAlignment(Qt.AlignCenter)
        no_activity_label.setStyleSheet(f"color: {get_theme().get_color('text_secondary')};")
        self.content_layout.addWidget(no_activity_label)
        
        # 여백 추가
        self.content_layout.addItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
    
    def on_section_activated(self):
        """섹션이 활성화될 때 호출"""
        self.log("대시보드가 활성화되었습니다.", LogType.INFO.value)
        
        # TODO: 통계 데이터 및 최근 활동 불러오기 