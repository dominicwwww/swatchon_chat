"""
메인 윈도우 - 애플리케이션의 메인 윈도우 클래스
"""
import sys
from typing import Dict, Optional
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
    QStackedWidget, QApplication, QFrame, QSplitter
)
from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QIcon

from core.config import ConfigManager
from core.types import SectionType
from ui.theme import get_theme
from ui.components.sidebar import Sidebar
from ui.components.control_bar import ControlBar
from ui.sections.base_section import BaseSection

class MainWindow(QMainWindow):
    """
    애플리케이션의 메인 윈도우 클래스
    전체적인 애플리케이션 수명 주기 관리
    """
    
    def __init__(self):
        super().__init__()
        
        # 설정 로드
        self.config = ConfigManager()
        
        # 윈도우 설정
        self.setWindowTitle("SwatchOn Partner Hub")
        self.setMinimumSize(1200, 1200)
        
        # 메인 위젯
        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(30, 30, 30, 30)  # 전체 패딩 추가
        main_layout.setSpacing(0)
        
        # 사이드바
        self.sidebar = Sidebar()
        
        # 오른쪽 컨테이너
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        
        # 컨트롤 바
        self.control_bar = ControlBar()
        right_layout.addWidget(self.control_bar)
        
        # 스택 위젯 (내용 영역)
        self.stack_widget = QStackedWidget()
        right_layout.addWidget(self.stack_widget)
        
        # 섹션 맵
        self._sections: Dict[str, BaseSection] = {}
        
        # 섹션 초기화
        self._initialize_sections()
        
        # 사이드바 이벤트 연결
        self.sidebar.section_selected.connect(self._on_section_selected)
        
        # 레이아웃 구성
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.sidebar)
        splitter.addWidget(right_container)
        
        # 사이드바와 콘텐츠 영역 비율 설정 (사이드바 20%, 콘텐츠 80%)
        splitter.setSizes([int(self.width() * 0.2), int(self.width() * 0.8)])
        
        main_layout.addWidget(splitter)
        self.setCentralWidget(main_widget)
        
        # 초기 섹션 설정
        initial_section = self.config.get("last_section", SectionType.DASHBOARD.value)
        
        # 안전하게 초기 섹션 설정 (설정 섹션이 초기 섹션이면 대시보드로 변경)
        if initial_section == SectionType.SETTINGS.value:
            print("설정 섹션이 초기 섹션으로 지정되어 있어 대시보드로 변경합니다.")
            initial_section = SectionType.DASHBOARD.value
            
        # 초기 섹션 설정 (사이드바 버튼 먼저 선택)
        if initial_section in self._sections:
            # 사이드바 버튼 선택
            self.sidebar.set_active_section(initial_section)
            
            # 섹션 표시
            section = self._sections[initial_section]
            self.stack_widget.setCurrentWidget(section)
            
            # 초기 섹션 활성화는 제거 (사용자가 직접 섹션을 선택할 때만 활성화)
        
        # 테마 적용
        self._apply_theme()
        
        # 테마 변경 이벤트 연결
        get_theme().theme_changed.connect(self._apply_theme)
    
    def _initialize_sections(self):
        """섹션 초기화"""
        try:
            # 대시보드 섹션
            from ui.sections.dashboard_section import DashboardSection
            dashboard_section = DashboardSection()
            self._add_section(SectionType.DASHBOARD.value, dashboard_section)
            
            # FBO 섹션
            from ui.sections.fbo.shipment_request_section import ShipmentRequestSection
            from ui.sections.fbo.shipment_confirm_section import ShipmentConfirmSection
            from ui.sections.fbo.po_section import PoSection
            
            self._add_section(SectionType.FBO_SHIPMENT_REQUEST.value, ShipmentRequestSection())
            self._add_section(SectionType.FBO_SHIPMENT_CONFIRM.value, ShipmentConfirmSection())
            self._add_section(SectionType.FBO_PO.value, PoSection())
            
            # SBO 섹션
            from ui.sections.sbo.po_section import SboPoSection
            from ui.sections.sbo.pickup_request_section import PickupRequestSection
            
            self._add_section(SectionType.SBO_PO.value, SboPoSection())
            self._add_section(SectionType.SBO_PICKUP_REQUEST.value, PickupRequestSection())
            
            # 설정 섹션
            from ui.sections.settings.settings_section import SettingsSection
            
            self._add_section(SectionType.SETTINGS.value, SettingsSection())
            
            # 템플릿 섹션
            from ui.sections.settings.template_section import TemplateSection
            
            self._add_section(SectionType.TEMPLATE.value, TemplateSection())
            
            # GA 관리비 정산 섹션
            from ui.sections.ga.maintenance_fee_section import MaintenanceFeeSection
            self._add_section(SectionType.GA_MAINTENANCE.value, MaintenanceFeeSection())
            
        except Exception as e:
            print(f"섹션 초기화 중 오류 발생: {str(e)}")
            # 최소한 대시보드 섹션은 생성
            try:
                from ui.sections.dashboard_section import DashboardSection
                dashboard_section = DashboardSection()
                self._add_section(SectionType.DASHBOARD.value, dashboard_section)
            except Exception as dashboard_error:
                print(f"대시보드 섹션 생성 실패: {str(dashboard_error)}")
    
    def _add_section(self, section_type: str, section: BaseSection):
        """섹션 추가"""
        try:
            self._sections[section_type] = section
            self.stack_widget.addWidget(section)
        except Exception as e:
            print(f"섹션 추가 중 오류 발생 ({section_type}): {str(e)}")
    
    def _on_section_selected(self, section_type: str):
        """섹션 선택 시 호출되는 함수"""
        try:
            # 이미 활성화된 섹션인지 확인하여 중복 호출 방지
            current_index = self.stack_widget.currentIndex()
            if current_index >= 0:
                current_widget = self.stack_widget.widget(current_index)
                if isinstance(current_widget, BaseSection) and current_widget == self._sections.get(section_type):
                    # 이미 현재 섹션이 활성화되어 있으면 중복 처리 방지
                    print(f"이미 활성화된 섹션입니다: {section_type}")
                    return
                    
                # 이전 섹션 비활성화
                if isinstance(current_widget, BaseSection):
                    try:
                        current_widget.on_section_deactivated()
                    except Exception as e:
                        print(f"이전 섹션 비활성화 중 오류: {str(e)}")
            
            # 섹션 존재 확인
            if section_type not in self._sections:
                print(f"섹션을 찾을 수 없습니다: {section_type}")
                return
            
            # 마지막 섹션 저장 (중복 저장 방지)
            try:
                current_last_section = self.config.get("last_section", "")
                if current_last_section != section_type:
                    self.config.set("last_section", section_type)
            except Exception as e:
                print(f"마지막 섹션 저장 중 오류: {str(e)}")
            
            # 사이드바 업데이트
            try:
                self.sidebar.set_active_section(section_type)
            except Exception as e:
                print(f"사이드바 업데이트 중 오류: {str(e)}")
            
            # 섹션 변경 및 활성화
            try:
                section = self._sections[section_type]
                self.stack_widget.setCurrentWidget(section)
                
                # 섹션 활성화
                section.on_section_activated()
                
            except Exception as e:
                print(f"섹션 활성화 중 오류 발생: {str(e)}")
                
        except Exception as e:
            print(f"섹션 선택 중 예상치 못한 오류 발생: {str(e)}")
    
    def _apply_theme(self):
        """테마 적용"""
        try:
            theme = get_theme()
            
            # 애플리케이션 팔레트 설정
            app = QApplication.instance()
            if app:
                app.setPalette(theme.create_palette())
                app.setStyleSheet(theme.get_stylesheet())
                
        except Exception as e:
            print(f"테마 적용 중 오류: {str(e)}")
    
    def closeEvent(self, event):
        """애플리케이션 종료 시 호출되는 함수"""
        try:
            # 설정 저장
            self.config.set("window_size", [self.width(), self.height()])
            self.config.set("window_pos", [self.x(), self.y()])
            
            # 모든 섹션 비활성화
            for section in self._sections.values():
                try:
                    if hasattr(section, 'on_section_deactivated'):
                        section.on_section_deactivated()
                except Exception as e:
                    print(f"섹션 비활성화 중 오류: {str(e)}")
            
            # 종료 이벤트 처리
            event.accept()
            
        except Exception as e:
            print(f"애플리케이션 종료 중 오류: {str(e)}")
            event.accept()  # 오류가 있어도 종료는 허용

def create_app():
    """애플리케이션 및 메인 윈도우 생성"""
    app = QApplication(sys.argv)
    app.setApplicationName("SwatchOn 카카오톡 자동화")
    app.setOrganizationName("SwatchOn")
    
    # 테마 초기화
    theme = get_theme()
    app.setPalette(theme.create_palette())
    app.setStyleSheet(theme.get_stylesheet())
    
    # 메인 윈도우 생성 및 표시
    window = MainWindow()
    window.show()
    
    return app, window

if __name__ == "__main__":
    app, window = create_app()
    sys.exit(app.exec_()) 