"""
통계 위젯 컴포넌트 - 재사용 가능한 통계 정보 표시 위젯
"""
from typing import Dict, Optional
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QFrame
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from ui.theme import get_theme
from core.types import ShipmentStatus


class StatisticsCard(QFrame):
    """개별 통계 카드 위젯"""
    
    def __init__(self, title: str, value: int = 0, color: str = "primary"):
        super().__init__()
        self.title = title
        self.color = color
        
        self.setup_ui()
        self.update_value(value)
    
    def setup_ui(self):
        """UI 설정"""
        theme = get_theme()
        
        # 프레임 스타일 설정
        self.setFrameStyle(QFrame.Box)
        self.setLineWidth(1)
        self.setStyleSheet(f"""
            QFrame {{
                border: 1px solid {theme.get_color('border')};
                border-radius: 8px;
                background-color: {theme.get_color('card_background')};
                padding: 8px;
            }}
            QLabel {{
                border: none;
                background: transparent;
            }}
        """)
        
        # 레이아웃 설정
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)
        
        # 제목 라벨
        self.title_label = QLabel(self.title)
        self.title_label.setAlignment(Qt.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(9)
        self.title_label.setFont(title_font)
        self.title_label.setStyleSheet(f"color: {theme.get_color('text_secondary')};")
        
        # 값 라벨
        self.value_label = QLabel("0")
        self.value_label.setAlignment(Qt.AlignCenter)
        value_font = QFont()
        value_font.setPointSize(16)
        value_font.setBold(True)
        self.value_label.setFont(value_font)
        self.value_label.setStyleSheet(f"color: {theme.get_color(self.color)};")
        
        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)
    
    def update_value(self, value):
        """값 업데이트 - 정수와 소수점 모두 지원"""
        if isinstance(value, float):
            # 소수점이 있는 경우
            if value == int(value):
                # 소수점이 0인 경우 정수로 표시
                self.value_label.setText(str(int(value)))
            else:
                # 소수점 1자리로 표시
                self.value_label.setText(f"{value:.1f}")
        else:
            # 정수인 경우
            self.value_label.setText(str(value))


class StatisticsWidget(QWidget):
    """
    통계 위젯 - 여러 섹션에서 재사용 가능한 통계 정보 표시
    
    기능:
    - 상태별 통계 카드 표시
    - 실시간 업데이트
    - 테마 적용
    - 2행 레이아웃 지원
    """
    
    # 시그널 정의
    card_clicked = Signal(str)  # 카드 클릭 시그널
    
    def __init__(self, parent=None, use_two_rows=False):
        super().__init__(parent)
        
        # 통계 카드들
        self.cards: Dict[str, StatisticsCard] = {}
        self.use_two_rows = use_two_rows
        
        self.setup_ui()
    
    def setup_ui(self):
        """UI 설정"""
        if self.use_two_rows:
            # 2행 레이아웃
            main_layout = QVBoxLayout(self)
            main_layout.setContentsMargins(0, 0, 0, 0)
            main_layout.setSpacing(8)
            
            # 첫 번째 행 (메시지 관련)
            self.first_row_widget = QWidget()
            self.first_row_layout = QHBoxLayout(self.first_row_widget)
            self.first_row_layout.setContentsMargins(0, 0, 0, 0)
            self.first_row_layout.setSpacing(12)
            
            # 두 번째 행 (데이터 관련)
            self.second_row_widget = QWidget()
            self.second_row_layout = QHBoxLayout(self.second_row_widget)
            self.second_row_layout.setContentsMargins(0, 0, 0, 0)
            self.second_row_layout.setSpacing(12)
            
            main_layout.addWidget(self.first_row_widget)
            main_layout.addWidget(self.second_row_widget)
            
            # 기본 통계 카드들 생성 (첫 번째 행에 메시지 관련)
            self.create_card("total", "전체", "primary", row=1)
            self.create_card("pending", "대기중", "warning", row=1)
            self.create_card("sending", "전송중", "info", row=1)
            self.create_card("sent", "전송완료", "success", row=1)
            self.create_card("failed", "전송실패", "error", row=1)
            self.create_card("cancelled", "취소됨", "secondary", row=1)
            
            # 각 행에 신축성 있는 공간 추가
            self.first_row_layout.addStretch()
            self.second_row_layout.addStretch()
        else:
            # 기존 1행 레이아웃
            layout = QHBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(12)
            
            # 기본 통계 카드들 생성
            self.create_card("total", "전체", "primary")
            self.create_card("pending", "대기중", "warning")
            self.create_card("sending", "전송중", "info")
            self.create_card("sent", "전송완료", "success")
            self.create_card("failed", "전송실패", "error")
            self.create_card("cancelled", "취소됨", "secondary")
            
            # 신축성 있는 공간 추가
            layout.addStretch()
    
    def create_card(self, key: str, title: str, color: str, row: int = 1):
        """통계 카드 생성"""
        card = StatisticsCard(title, 0, color)
        self.cards[key] = card
        
        # 클릭 이벤트 처리
        card.mousePressEvent = lambda event, k=key: self._on_card_clicked(k)
        
        if self.use_two_rows:
            if row == 1:
                self.first_row_layout.insertWidget(self.first_row_layout.count() - 1, card)
            else:
                self.second_row_layout.insertWidget(self.second_row_layout.count() - 1, card)
        else:
            self.layout().addWidget(card)
    
    def _on_card_clicked(self, key: str):
        """카드 클릭 이벤트"""
        self.card_clicked.emit(key)
    
    def update_statistics(self, stats: Dict[str, int]):
        """
        통계 정보 업데이트
        
        Args:
            stats: 통계 정보 딕셔너리
        """
        for key, value in stats.items():
            if key in self.cards:
                self.cards[key].update_value(value)
    
    def update_single_statistic(self, key: str, value):
        """
        개별 통계 업데이트
        
        Args:
            key: 통계 키
            value: 값 (int 또는 float)
        """
        if key in self.cards:
            self.cards[key].update_value(value)
    
    def get_card_value(self, key: str) -> int:
        """
        카드 값 조회
        
        Args:
            key: 통계 키
            
        Returns:
            int: 현재 값
        """
        if key in self.cards:
            return int(self.cards[key].value_label.text())
        return 0
    
    def set_card_visibility(self, key: str, visible: bool):
        """
        카드 표시/숨김 설정
        
        Args:
            key: 통계 키
            visible: 표시 여부
        """
        if key in self.cards:
            self.cards[key].setVisible(visible)
    
    def add_custom_card(self, key: str, title: str, color: str = "primary", value: int = 0, row: int = 2):
        """
        사용자 정의 카드 추가
        
        Args:
            key: 카드 키
            title: 카드 제목
            color: 카드 색상
            value: 초기 값
            row: 행 번호 (1: 첫 번째 행, 2: 두 번째 행) - 2행 레이아웃에서만 적용
        """
        if key not in self.cards:
            card = StatisticsCard(title, value, color)
            self.cards[key] = card
            
            # 클릭 이벤트 처리
            card.mousePressEvent = lambda event, k=key: self._on_card_clicked(k)
            
            if self.use_two_rows:
                # 2행 레이아웃에서는 row 매개변수에 따라 배치
                if row == 1:
                    self.first_row_layout.insertWidget(self.first_row_layout.count() - 1, card)
                else:
                    self.second_row_layout.insertWidget(self.second_row_layout.count() - 1, card)
            else:
                # 1행 레이아웃에서는 stretch 위젯 앞에 삽입
                layout = self.layout()
                layout.insertWidget(layout.count() - 1, card)
    
    def remove_card(self, key: str):
        """
        카드 제거
        
        Args:
            key: 제거할 카드 키
        """
        if key in self.cards:
            card = self.cards[key]
            self.layout().removeWidget(card)
            card.deleteLater()
            del self.cards[key]
    
    def clear_statistics(self):
        """모든 통계를 0으로 초기화"""
        for card in self.cards.values():
            card.update_value(0)
    
    def set_card_style(self, key: str, color: str):
        """
        카드 스타일 변경
        
        Args:
            key: 카드 키
            color: 새로운 색상
        """
        if key in self.cards:
            theme = get_theme()
            self.cards[key].value_label.setStyleSheet(f"color: {theme.get_color(color)};")
    
    def get_all_statistics(self) -> Dict[str, int]:
        """
        모든 통계 값 반환
        
        Returns:
            Dict[str, int]: 모든 통계 값
        """
        return {key: self.get_card_value(key) for key in self.cards.keys()}
    
    def animate_value_change(self, key: str, new_value: int):
        """
        값 변경 애니메이션 (향후 구현)
        
        Args:
            key: 카드 키
            new_value: 새로운 값
        """
        # TODO: 값 변경 애니메이션 구현
        self.update_single_statistic(key, new_value) 