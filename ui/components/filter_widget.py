"""
필터 위젯 컴포넌트 - 재사용 가능한 검색 및 필터링 기능
"""
from typing import Dict, List, Optional, Callable, Any
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit, 
    QComboBox, QPushButton, QFrame, QCheckBox, QButtonGroup
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont

from ui.theme import get_theme
from core.types import ShipmentStatus


class FilterWidget(QWidget):
    """
    필터 위젯 - 여러 섹션에서 재사용 가능한 검색 및 필터링 기능
    
    기능:
    - 검색어 입력
    - 상태 필터링
    - 날짜 범위 필터링
    - 사용자 정의 필터 추가
    """
    
    # 시그널 정의
    search_changed = Signal(str)  # 검색어 변경
    filter_changed = Signal(str, str)  # 필터 변경 (filter_type, value)
    filters_applied = Signal(dict)  # 모든 필터 적용
    filters_cleared = Signal()  # 필터 초기화
    
    def __init__(self, parent=None, show_search: bool = True, show_status_filter: bool = True):
        """
        초기화
        
        Args:
            parent: 부모 위젯
            show_search: 검색창 표시 여부
            show_status_filter: 상태 필터 표시 여부
        """
        super().__init__(parent)
        
        self.show_search = show_search
        self.show_status_filter = show_status_filter
        
        # 필터 상태 저장
        self.current_filters: Dict[str, Any] = {}
        
        # 검색 딜레이 타이머
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self._emit_search_changed)
        
        self.setup_ui()
    
    def setup_ui(self):
        """UI 설정"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        
        # 검색창
        if self.show_search:
            self.setup_search_section(layout)
        
        # 상태 필터
        if self.show_status_filter:
            self.setup_status_filter_section(layout)
        
        # 사용자 정의 필터 영역
        self.custom_filters_layout = QHBoxLayout()
        layout.addLayout(self.custom_filters_layout)
        
        # 필터 제어 버튼들
        self.setup_control_buttons(layout)
        
        # 신축성 있는 공간
        layout.addStretch()
    
    def setup_search_section(self, parent_layout: QHBoxLayout):
        """검색 섹션 설정"""
        search_label = QLabel("검색:")
        parent_layout.addWidget(search_label)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("판매자, 발주번호 검색...")
        self.search_input.setMinimumWidth(200)
        self.search_input.textChanged.connect(self._on_search_text_changed)
        parent_layout.addWidget(self.search_input)
    
    def setup_status_filter_section(self, parent_layout: QHBoxLayout):
        """상태 필터 섹션 설정"""
        status_label = QLabel("상태:")
        parent_layout.addWidget(status_label)
        
        self.status_filter = QComboBox()
        self.status_filter.setMinimumWidth(120)
        self.status_filter.addItem("모든 상태", "all")
        self.status_filter.addItem("대기중", ShipmentStatus.PENDING.value)
        self.status_filter.addItem("전송중", ShipmentStatus.SENDING.value)
        self.status_filter.addItem("전송완료", ShipmentStatus.SENT.value)
        self.status_filter.addItem("전송실패", ShipmentStatus.FAILED.value)
        self.status_filter.addItem("취소됨", ShipmentStatus.CANCELLED.value)
        self.status_filter.addItem("재시도대기", ShipmentStatus.RETRY.value)
        
        # 기본값을 "대기중"으로 설정
        self.status_filter.setCurrentIndex(1)
        self.status_filter.currentIndexChanged.connect(self._on_status_filter_changed)
        parent_layout.addWidget(self.status_filter)
    
    def setup_control_buttons(self, parent_layout: QHBoxLayout):
        """제어 버튼들 설정"""
        # 필터 적용 버튼
        self.apply_button = QPushButton("필터 적용")
        self.apply_button.clicked.connect(self._apply_filters)
        parent_layout.addWidget(self.apply_button)
        
        # 필터 초기화 버튼
        self.clear_button = QPushButton("초기화")
        self.clear_button.clicked.connect(self._clear_filters)
        parent_layout.addWidget(self.clear_button)
    
    def _on_search_text_changed(self, text: str):
        """검색어 변경 이벤트 (딜레이 적용)"""
        self.search_timer.stop()
        self.search_timer.start(300)  # 300ms 딜레이
        self.current_filters['search'] = text
    
    def _emit_search_changed(self):
        """검색어 변경 시그널 발생"""
        if hasattr(self, 'search_input'):
            text = self.search_input.text()
            self.search_changed.emit(text)
    
    def _on_status_filter_changed(self, index: int):
        """상태 필터 변경 이벤트"""
        value = self.status_filter.currentData()
        self.current_filters['status'] = value
        self.filter_changed.emit('status', value)
    
    def _apply_filters(self):
        """모든 필터 적용"""
        self.filters_applied.emit(self.current_filters.copy())
    
    def _clear_filters(self):
        """필터 초기화"""
        # 검색창 초기화
        if hasattr(self, 'search_input'):
            self.search_input.clear()
        
        # 상태 필터 초기화 (모든 상태로)
        if hasattr(self, 'status_filter'):
            self.status_filter.setCurrentIndex(0)
        
        # 사용자 정의 필터 초기화
        self._clear_custom_filters()
        
        # 필터 상태 초기화
        self.current_filters.clear()
        
        # 시그널 발생
        self.filters_cleared.emit()
    
    def add_combo_filter(self, key: str, label: str, items: List[tuple], default_index: int = 0):
        """
        콤보박스 필터 추가
        
        Args:
            key: 필터 키
            label: 라벨 텍스트
            items: (표시명, 값) 튜플 리스트
            default_index: 기본 선택 인덱스
        """
        filter_label = QLabel(f"{label}:")
        self.custom_filters_layout.addWidget(filter_label)
        
        combo_box = QComboBox()
        combo_box.setMinimumWidth(120)
        
        for display_text, value in items:
            combo_box.addItem(display_text, value)
        
        combo_box.setCurrentIndex(default_index)
        combo_box.currentIndexChanged.connect(
            lambda index, k=key, cb=combo_box: self._on_custom_filter_changed(k, cb.currentData())
        )
        
        self.custom_filters_layout.addWidget(combo_box)
        
        # 초기값 저장
        if items:
            self.current_filters[key] = items[default_index][1]
    
    def add_text_filter(self, key: str, label: str, placeholder: str = ""):
        """
        텍스트 입력 필터 추가
        
        Args:
            key: 필터 키
            label: 라벨 텍스트
            placeholder: 플레이스홀더 텍스트
        """
        filter_label = QLabel(f"{label}:")
        self.custom_filters_layout.addWidget(filter_label)
        
        line_edit = QLineEdit()
        line_edit.setPlaceholderText(placeholder)
        line_edit.setMinimumWidth(150)
        line_edit.textChanged.connect(
            lambda text, k=key: self._on_custom_filter_changed(k, text)
        )
        
        self.custom_filters_layout.addWidget(line_edit)
    
    def add_checkbox_filter(self, key: str, label: str, default_checked: bool = False):
        """
        체크박스 필터 추가
        
        Args:
            key: 필터 키
            label: 라벨 텍스트
            default_checked: 기본 체크 상태
        """
        checkbox = QCheckBox(label)
        checkbox.setChecked(default_checked)
        checkbox.toggled.connect(
            lambda checked, k=key: self._on_custom_filter_changed(k, checked)
        )
        
        self.custom_filters_layout.addWidget(checkbox)
        
        # 초기값 저장
        self.current_filters[key] = default_checked
    
    def _on_custom_filter_changed(self, key: str, value: Any):
        """사용자 정의 필터 변경 이벤트"""
        self.current_filters[key] = value
        self.filter_changed.emit(key, str(value))
    
    def _clear_custom_filters(self):
        """사용자 정의 필터 초기화"""
        # 현재 추가된 모든 사용자 정의 필터 위젯들을 초기값으로 설정
        for i in range(self.custom_filters_layout.count()):
            widget = self.custom_filters_layout.itemAt(i).widget()
            if isinstance(widget, QComboBox):
                widget.setCurrentIndex(0)
            elif isinstance(widget, QLineEdit):
                widget.clear()
            elif isinstance(widget, QCheckBox):
                widget.setChecked(False)
    
    def get_current_filters(self) -> Dict[str, Any]:
        """현재 필터 상태 반환"""
        return self.current_filters.copy()
    
    def set_search_text(self, text: str):
        """검색어 설정"""
        if hasattr(self, 'search_input'):
            self.search_input.setText(text)
    
    def get_search_text(self) -> str:
        """검색어 반환"""
        if hasattr(self, 'search_input'):
            return self.search_input.text()
        return ""
    
    def set_status_filter(self, status: str):
        """상태 필터 설정"""
        if hasattr(self, 'status_filter'):
            for i in range(self.status_filter.count()):
                if self.status_filter.itemData(i) == status:
                    self.status_filter.setCurrentIndex(i)
                    break
    
    def get_status_filter(self) -> str:
        """상태 필터 반환"""
        if hasattr(self, 'status_filter'):
            return self.status_filter.currentData()
        return "all"
    
    def set_filter_value(self, key: str, value: Any):
        """특정 필터 값 설정"""
        self.current_filters[key] = value
        
        # UI 위젯도 업데이트
        if key == 'search' and hasattr(self, 'search_input'):
            self.search_input.setText(str(value))
        elif key == 'status' and hasattr(self, 'status_filter'):
            self.set_status_filter(str(value))
    
    def remove_custom_filter(self, key: str):
        """사용자 정의 필터 제거"""
        if key in self.current_filters:
            del self.current_filters[key]
        
        # UI에서도 제거 (구현 복잡도로 인해 향후 필요시 구현)
        # TODO: UI 위젯 제거 로직 구현
    
    def set_enabled(self, enabled: bool):
        """필터 위젯 활성화/비활성화"""
        self.setEnabled(enabled)
    
    def get_filter_summary(self) -> str:
        """현재 적용된 필터의 요약 문자열 반환"""
        active_filters = []
        
        if 'search' in self.current_filters and self.current_filters['search']:
            active_filters.append(f"검색: '{self.current_filters['search']}'")
        
        if 'status' in self.current_filters and self.current_filters['status'] != 'all':
            status_text = self._get_status_display_text(self.current_filters['status'])
            active_filters.append(f"상태: {status_text}")
        
        # 기타 사용자 정의 필터들
        for key, value in self.current_filters.items():
            if key not in ['search', 'status'] and value:
                active_filters.append(f"{key}: {value}")
        
        if active_filters:
            return "활성 필터: " + ", ".join(active_filters)
        else:
            return "필터 없음"
    
    def _get_status_display_text(self, status_value: str) -> str:
        """상태 값에 대한 표시 텍스트 반환"""
        status_map = {
            ShipmentStatus.PENDING.value: "대기중",
            ShipmentStatus.SENDING.value: "전송중",
            ShipmentStatus.SENT.value: "전송완료",
            ShipmentStatus.FAILED.value: "전송실패",
            ShipmentStatus.CANCELLED.value: "취소됨",
            ShipmentStatus.RETRY.value: "재시도대기"
        }
        return status_map.get(status_value, status_value) 