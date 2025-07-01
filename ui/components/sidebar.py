"""
사이드바 컴포넌트 - 애플리케이션 주요 메뉴 표시
"""
from typing import List, Dict, Any, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QScrollArea, QFrame, QSizePolicy, QSpacerItem
)
from PySide6.QtCore import Qt, Signal, QSize, QMargins
from PySide6.QtGui import QIcon, QPixmap, QColor, QFont
import qtawesome as qta

from core.types import SectionType, SidebarItemType
from ui.theme import get_theme

class SidebarButton(QPushButton):
    """사이드바 버튼 위젯"""
    
    def __init__(self, text: str, icon_name: str = None, parent=None):
        super().__init__(text, parent)
        
        # 아이콘 설정 (qtawesome)
        if icon_name:
            self.setIcon(qta.icon(icon_name))
            self.setIconSize(QSize(18, 18))
        
        # 고정 높이 설정
        self.setFixedHeight(36)
        
        # 정렬 설정
        self.setStyleSheet("""
            QPushButton {
                border: none;
                border-radius: 4px;
                text-align: left;
                padding-left: 12px;
                font-size: 13px;
            }
        """)
        
        # 커서 설정
        self.setCursor(Qt.PointingHandCursor)
        
        # 선택되지 않은 상태로 초기화
        self._selected = False
        self._update_style()
    
    def set_selected(self, selected: bool):
        """버튼 선택 상태 설정"""
        # 상태가 변경될 때만 업데이트
        if self._selected != selected:
            self._selected = selected
            self._update_style()
    
    def _update_style(self):
        """현재 상태에 따라 스타일 업데이트"""
        theme = get_theme()
        
        if self._selected:
            background_color = theme.get_color("primary")
            text_color = "#FFFFFF"  # 선택된 아이템은 항상 밝은 텍스트
        else:
            background_color = "transparent"
            text_color = theme.get_color("text_primary")
        
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {background_color};
                color: {text_color};
                border: none;
                border-radius: 4px;
                text-align: left;
                padding-left: 12px;
                font-size: 13px;
                font-weight: {500 if self._selected else 400};
            }}
            
            QPushButton:hover {{
                background-color: {theme.get_color("primary") if self._selected else theme.get_color("card_bg")};
            }}
        """)

class SidebarCategory(QWidget):
    """사이드바 카테고리 위젯"""
    
    def __init__(self, name: str, parent=None):
        super().__init__(parent)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(2)
        
        # 카테고리 라벨
        label = QLabel(name.upper())
        theme = get_theme()
        label.setStyleSheet(f"""
            color: {theme.get_color("text_secondary")};
            font-size: 10px;
            font-weight: bold;
        """)
        
        layout.addWidget(label)

class SidebarSpacer(QWidget):
    """사이드바 여백 위젯"""
    
    def __init__(self, height: int = 10, parent=None):
        super().__init__(parent)
        self.setFixedHeight(height)

class Sidebar(QWidget):
    """애플리케이션 사이드바 위젯"""
    
    # 섹션 선택 시그널
    section_selected = Signal(str)  # SectionType.value
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 고정 너비 설정
        self.setFixedWidth(220)
        
        # 메인 레이아웃
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 로고 영역
        logo_widget = QWidget()
        logo_layout = QHBoxLayout(logo_widget)
        logo_layout.setContentsMargins(16, 16, 16, 16)
        
        logo_label = QLabel("SwatchOn")
        font = logo_label.font()
        font.setPointSize(16)
        font.setBold(True)
        logo_label.setFont(font)
        
        logo_layout.addWidget(logo_label)
        main_layout.addWidget(logo_widget)
        
        # 구분선
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet(f"background-color: {get_theme().get_color('divider')};")
        separator.setFixedHeight(1)
        main_layout.addWidget(separator)
        
        # 스크롤 영역
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # 스크롤 내부 위젯
        scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(scroll_content)
        self.scroll_layout.setContentsMargins(0, 8, 0, 8)
        self.scroll_layout.setSpacing(2)
        
        # 버튼 매핑 저장 (초기화)
        self._buttons = {}
        
        # 버튼 추가
        self._create_sidebar_items()
        
        # 하단 여백을 위한 스페이서
        self.scroll_layout.addItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        
        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)
        
        # 하단 설정 버튼
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(8, 8, 8, 8)
        
        settings_button = SidebarButton("설정", icon_name="ph.gear")
        settings_button.clicked.connect(lambda: self._on_button_clicked(SectionType.SETTINGS.value))
        
        bottom_layout.addWidget(settings_button)
        
        # 하단 구분선
        bottom_separator = QFrame()
        bottom_separator.setFrameShape(QFrame.HLine)
        bottom_separator.setFrameShadow(QFrame.Sunken)
        bottom_separator.setStyleSheet(f"background-color: {get_theme().get_color('divider')};")
        bottom_separator.setFixedHeight(1)
        
        main_layout.addWidget(bottom_separator)
        main_layout.addWidget(bottom_widget)
        
        # 테마에 맞게 스타일 설정
        self._update_style()
        
        # 테마 변경 시 스타일 업데이트
        get_theme().theme_changed.connect(self._update_style)
    
    def _create_sidebar_items(self):
        """사이드바 아이템 생성"""
        # 대시보드
        dashboard_btn = SidebarButton("대시보드", icon_name="ph.house")
        dashboard_btn.clicked.connect(lambda: self._on_button_clicked(SectionType.DASHBOARD.value))
        self.scroll_layout.addWidget(dashboard_btn)
        self._buttons[SectionType.DASHBOARD.value] = dashboard_btn
        
        # 구분선
        self.scroll_layout.addWidget(SidebarSpacer(10))
        
        # FBO 카테고리
        self.scroll_layout.addWidget(SidebarCategory("FBO"))
        
        # FBO 출고 요청
        fbo_shipment_req_btn = SidebarButton("출고 요청", icon_name="ph.truck")
        fbo_shipment_req_btn.clicked.connect(lambda: self._on_button_clicked(SectionType.FBO_SHIPMENT_REQUEST.value))
        self.scroll_layout.addWidget(fbo_shipment_req_btn)
        self._buttons[SectionType.FBO_SHIPMENT_REQUEST.value] = fbo_shipment_req_btn
        
        # FBO 출고 확인 - 현재 사용하지 않는 기능으로 임시 숨김
        # fbo_shipment_conf_btn = SidebarButton("출고 확인", icon_name="ph.check")
        # fbo_shipment_conf_btn.clicked.connect(
        #     lambda: self._on_button_clicked(SectionType.FBO_SHIPMENT_CONFIRM.value)
        # )
        # self.scroll_layout.addWidget(fbo_shipment_conf_btn)
        # self._buttons[SectionType.FBO_SHIPMENT_CONFIRM.value] = fbo_shipment_conf_btn
        
        # FBO 발주 확인
        fbo_po_btn = SidebarButton("발주 확인", icon_name="ph.clipboard-text")
        fbo_po_btn.clicked.connect(
            lambda: self._on_button_clicked(SectionType.FBO_PO.value)
        )
        self.scroll_layout.addWidget(fbo_po_btn)
        self._buttons[SectionType.FBO_PO.value] = fbo_po_btn
        
        # 구분선
        self.scroll_layout.addWidget(SidebarSpacer(10))
        
        # GA 카테고리
        self.scroll_layout.addWidget(SidebarCategory("GA"))
        
        ga_maintenance_btn = SidebarButton("관리비 정산", icon_name="ph.calculator")
        ga_maintenance_btn.clicked.connect(
            lambda: self._on_button_clicked(SectionType.GA_MAINTENANCE.value)
        )
        self.scroll_layout.addWidget(ga_maintenance_btn)
        self._buttons[SectionType.GA_MAINTENANCE.value] = ga_maintenance_btn
        
        # 구분선
        self.scroll_layout.addWidget(SidebarSpacer(10))
        
        # SBO 카테고리
        self.scroll_layout.addWidget(SidebarCategory("SBO"))
        
        # SBO 스와치 발주
        sbo_po_btn = SidebarButton("스와치 발주", icon_name="ph.tag")
        sbo_po_btn.clicked.connect(
            lambda: self._on_button_clicked(SectionType.SBO_PO.value)
        )
        self.scroll_layout.addWidget(sbo_po_btn)
        self._buttons[SectionType.SBO_PO.value] = sbo_po_btn
        
        # SBO 픽업 요청
        sbo_pickup_btn = SidebarButton("픽업 요청", icon_name="ph.package")
        sbo_pickup_btn.clicked.connect(
            lambda: self._on_button_clicked(SectionType.SBO_PICKUP_REQUEST.value)
        )
        self.scroll_layout.addWidget(sbo_pickup_btn)
        self._buttons[SectionType.SBO_PICKUP_REQUEST.value] = sbo_pickup_btn
        
        # 구분선
        self.scroll_layout.addWidget(SidebarSpacer(10))
        
        # 도구 카테고리
        self.scroll_layout.addWidget(SidebarCategory("도구"))
        
        # 템플릿 관리
        template_btn = SidebarButton("템플릿 관리", icon_name="ph.squares-four")
        template_btn.clicked.connect(
            lambda: self._on_button_clicked(SectionType.TEMPLATE.value)
        )
        self.scroll_layout.addWidget(template_btn)
        self._buttons[SectionType.TEMPLATE.value] = template_btn
        
        # 설정 버튼 추가
        self._buttons[SectionType.SETTINGS.value] = SidebarButton("설정", icon_name="ph.gear")
    
    def _on_button_clicked(self, section_type: str):
        """버튼 클릭 이벤트 처리"""
        # 모든 버튼 선택 해제
        for btn in self._buttons.values():
            btn.set_selected(False)
        
        # 현재 버튼 선택
        if section_type in self._buttons:
            self._buttons[section_type].set_selected(True)
        
        # 섹션 변경 시그널 발생
        self.section_selected.emit(section_type)
    
    def _update_style(self):
        """테마에 맞게 스타일 업데이트"""
        theme = get_theme()
        self.setStyleSheet(f"""
            Sidebar {{
                background-color: {theme.get_color("sidebar_bg")};
            }}
        """)
        
        # 현재 선택된 버튼 유지
        for section_type, button in self._buttons.items():
            button._update_style()
    
    def set_active_section(self, section_type: str):
        """현재 활성 섹션 설정 (신호 발생 없이)"""
        # 이미 선택된 버튼인지 확인
        if section_type in self._buttons:
            current_button = self._buttons[section_type]
            if current_button._selected:
                return  # 이미 선택된 상태면 아무 것도 하지 않음
                
        # 모든 버튼 선택 해제
        for btn in self._buttons.values():
            btn.set_selected(False)
        
        # 현재 버튼 선택 (신호 발생 없이)
        if section_type in self._buttons:
            self._buttons[section_type].set_selected(True) 