"""
SBO 스와치 발주 섹션 - 스와치 발주 기능
"""
from typing import List, Dict, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTableWidget, QTableWidgetItem, QFrame, QHeaderView,
    QCheckBox, QComboBox, QLineEdit
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QFont, QColor

from core.types import LogType, OrderType, SboOperationType
from ui.sections.base_section import BaseSection
from ui.components.message_section_mixin import MessageSectionMixin
from ui.theme import get_theme
from ui.components.log_widget import LOG_INFO, LOG_SUCCESS, LOG_WARNING, LOG_ERROR

class SboPoSection(BaseSection, MessageSectionMixin):
    """
    SBO 스와치 발주 섹션 - 스와치 발주 관련 기능
    MessageSectionMixin을 사용하여 공통 기능 활용
    """
    
    def __init__(self, parent=None):
        super().__init__("SBO 스와치 발주", parent)
        
        # 공통 메시지 컴포넌트 설정
        self.setup_message_components(
            order_type=OrderType.SBO,
            operation_type=SboOperationType.PO,
            enable_preview_features=True,  # SBO는 미리보기 기능 활용
            enable_emergency_stop=True
        )
        
        # 콘텐츠 설정
        self.setup_content()
    
    def setup_content(self):
        """콘텐츠 설정"""
        # 공통 레이아웃 설정 (필터, 통계)
        self.setup_message_content_layout()
        
        # 테이블
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "선택", "판매자", "스와치 번호", "원단명", "색상", "수량", "발주일", "상태"
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        
        # 테이블 헤더 설정
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # 선택 체크박스
        header.setSectionResizeMode(1, QHeaderView.Stretch)           # 판매자
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # 스와치 번호
        header.setSectionResizeMode(3, QHeaderView.Stretch)           # 원단명
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # 색상
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # 수량
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)  # 발주일
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)  # 상태
        
        self.content_layout.addWidget(self.table)
        
        # 통계 정보
        stats_widget = QWidget()
        stats_layout = QHBoxLayout(stats_widget)
        stats_layout.setContentsMargins(0, 8, 0, 0)
        
        self.stats_label = QLabel("총 0건")
        stats_layout.addWidget(self.stats_label)
        stats_layout.addStretch()
        
        # 선택 버튼들
        self.select_all_button = QPushButton("모두 선택")
        self.select_all_button.clicked.connect(self._on_select_all_clicked)
        
        self.deselect_all_button = QPushButton("모두 해제")
        self.deselect_all_button.clicked.connect(self._on_deselect_all_clicked)
        
        stats_layout.addWidget(self.select_all_button)
        stats_layout.addWidget(self.deselect_all_button)
        
        self.content_layout.addWidget(stats_widget)
        
        # 추가 통계 카드 설정
        self._setup_additional_statistics()
        
        # 테스트 데이터 로드
        self._load_dummy_data()
    
    def _setup_additional_statistics(self):
        """SBO 스와치 발주에 특화된 통계 카드들 설정"""
        self.statistics_widget.add_custom_card("swatch_count", "스와치 건수", "info", 0)
        self.statistics_widget.add_custom_card("store_count", "판매자 수", "primary", 0)
        self.statistics_widget.add_custom_card("total_quantity", "총 수량", "success", 0)
        self.statistics_widget.add_custom_card("urgent_count", "긴급 발주", "warning", 0)
    
    def _load_dummy_data(self):
        """더미 데이터 로드"""
        dummy_data = [
            {
                "id": "1",
                "store_name": "패브릭스토어A",
                "swatch_number": "SW001",
                "fabric_name": "코튼 원단",
                "color": "화이트",
                "quantity": 5,
                "order_date": "2024-01-15",
                "status": "pending",
                "message_status": "대기중"
            },
            {
                "id": "2", 
                "store_name": "패브릭스토어B",
                "swatch_number": "SW002",
                "fabric_name": "실크 원단",
                "color": "블랙",
                "quantity": 3,
                "order_date": "2024-01-16",
                "status": "sent",
                "message_status": "전송완료"
            },
            {
                "id": "3",
                "store_name": "패브릭스토어C", 
                "swatch_number": "SW003",
                "fabric_name": "린넨 원단",
                "color": "베이지",
                "quantity": 7,
                "order_date": "2024-01-17",
                "status": "failed",
                "message_status": "전송실패"
            },
        ]
        
        self._update_table_with_data(dummy_data)
        self._update_all_statistics(dummy_data)
        self.log(f"SBO 스와치 발주 더미 데이터 {len(dummy_data)}건을 로드했습니다.", LOG_SUCCESS)
    
    def _update_table_with_data(self, data: List[Dict]):
        """테이블에 데이터 업데이트"""
        self.table.setRowCount(len(data))
        
        for row_idx, item in enumerate(data):
            # 선택 체크박스
            checkbox = QCheckBox()
            checkbox.stateChanged.connect(self._on_checkbox_changed)
            self.table.setCellWidget(row_idx, 0, checkbox)
            
            # 데이터 컬럼들
            self.table.setItem(row_idx, 1, QTableWidgetItem(item.get("store_name", "")))
            self.table.setItem(row_idx, 2, QTableWidgetItem(item.get("swatch_number", "")))
            self.table.setItem(row_idx, 3, QTableWidgetItem(item.get("fabric_name", "")))
            self.table.setItem(row_idx, 4, QTableWidgetItem(item.get("color", "")))
            self.table.setItem(row_idx, 5, QTableWidgetItem(str(item.get("quantity", 0))))
            self.table.setItem(row_idx, 6, QTableWidgetItem(item.get("order_date", "")))
            self.table.setItem(row_idx, 7, QTableWidgetItem(item.get("message_status", "대기중")))
            
            # 데이터 저장 (나중에 선택된 항목 추출용)
            for col in range(1, 8):
                if self.table.item(row_idx, col):
                    self.table.item(row_idx, col).setData(Qt.UserRole, item)
        
        self.stats_label.setText(f"총 {len(data)}건")
    
    def _update_all_statistics(self, data: List[Dict]):
        """모든 통계 정보 업데이트"""
        try:
            # 기본 통계
            total_count = len(data)
            store_names = set(item.get('store_name', '') for item in data)
            total_quantity = sum(int(item.get('quantity', 0)) for item in data)
            urgent_count = sum(1 for item in data if item.get('urgent', False))
            
            # 통계 카드 업데이트 - 올바른 메서드명 사용
            self.statistics_widget.update_single_statistic("swatch_count", total_count)
            self.statistics_widget.update_single_statistic("store_count", len(store_names))
            self.statistics_widget.update_single_statistic("total_quantity", total_quantity)
            self.statistics_widget.update_single_statistic("urgent_count", urgent_count)
            
            # 상태별 통계
            status_stats = {}
            for item in data:
                status = item.get('message_status', '대기중')
                status_stats[status] = status_stats.get(status, 0) + 1
            
            # 기본 상태 카드 업데이트 - 올바른 메서드명 사용
            pending_count = status_stats.get('대기중', 0)
            sent_count = status_stats.get('전송완료', 0)
            failed_count = status_stats.get('전송실패', 0)
            
            self.statistics_widget.update_single_statistic("pending", pending_count)
            self.statistics_widget.update_single_statistic("sent", sent_count)
            self.statistics_widget.update_single_statistic("failed", failed_count)
            self.statistics_widget.update_single_statistic("total", total_count)
            
        except Exception as e:
            self.log(f"통계 업데이트 중 오류: {str(e)}", LOG_ERROR)
    
    def _on_checkbox_changed(self):
        """체크박스 변경 시 선택된 항목 업데이트"""
        selected_items = []
        for row in range(self.table.rowCount()):
            checkbox = self.table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                # 첫 번째 데이터 컬럼에서 저장된 원본 데이터 추출
                item_widget = self.table.item(row, 1)
                if item_widget:
                    item_data = item_widget.data(Qt.UserRole)
                    if item_data:
                        selected_items.append(item_data)
        
        self._selected_items = selected_items
        
        # 선택된 항목이 있으면 미리보기/전송 버튼 활성화
        has_selection = len(selected_items) > 0
        if hasattr(self, 'preview_button'):
            self.preview_button.setEnabled(has_selection)
        
        self.log(f"선택된 항목: {len(selected_items)}건", LogType.DEBUG.value)
    
    def _on_select_all_clicked(self):
        """모두 선택 버튼 클릭"""
        for row in range(self.table.rowCount()):
            checkbox = self.table.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(True)
    
    def _on_deselect_all_clicked(self):
        """모두 해제 버튼 클릭"""
        for row in range(self.table.rowCount()):
            checkbox = self.table.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(False)
    
    # MessageSectionMixin 인터페이스 구현
    def _convert_item_to_dict(self, item) -> Dict[str, Any]:
        """아이템을 딕셔너리로 변환"""
        if isinstance(item, dict):
            return item
        else:
            return {"id": getattr(item, 'id', ''), "store_name": getattr(item, 'store_name', '')}
    
    def _update_item_status(self, item_ids: List[int], status: str, set_processed_time: bool = False):
        """항목 상태 업데이트 콜백"""
        # 테이블에서 해당 항목들의 상태 업데이트
        for row in range(self.table.rowCount()):
            item_widget = self.table.item(row, 1)
            if item_widget:
                item_data = item_widget.data(Qt.UserRole)
                if item_data and str(item_data.get('id', '')) in [str(id) for id in item_ids]:
                    # 상태 컬럼 업데이트
                    status_item = self.table.item(row, 7)
                    if status_item:
                        status_item.setText(status)
                    
                    # 원본 데이터도 업데이트
                    item_data['message_status'] = status
                    item_widget.setData(Qt.UserRole, item_data)
        
        # 통계 재계산
        current_data = []
        for row in range(self.table.rowCount()):
            item_widget = self.table.item(row, 1)
            if item_widget:
                item_data = item_widget.data(Qt.UserRole)
                if item_data:
                    current_data.append(item_data)
        
        self._update_all_statistics(current_data)
    
    def _on_data_loaded(self, data):
        """데이터 로드 완료 이벤트"""
        self._update_table_with_data(data)
        self._update_all_statistics(data)
        self.log(f"SBO 스와치 발주 데이터 {len(data)}건이 로드되었습니다.", LOG_SUCCESS)
    
    def on_section_activated(self):
        """섹션이 활성화될 때 호출"""
        self.log("SBO 스와치 발주 섹션이 활성화되었습니다.", LogType.INFO.value)
    
    def on_section_deactivated(self):
        """섹션이 비활성화될 때 호출"""
        # 메시지 전송 중단
        self.emergency_stop_all_sending() 