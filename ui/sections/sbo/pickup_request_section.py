"""
SBO 픽업 요청 섹션 - 스와치 픽업 요청 기능
"""
from typing import List, Dict, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTableWidget, QTableWidgetItem, QFrame, QHeaderView,
    QCheckBox, QComboBox, QLineEdit
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QFont, QColor

from core.types import LogType
from ui.sections.base_section import BaseSection
from ui.theme import get_theme

class PickupRequestSection(BaseSection):
    """
    SBO 픽업 요청 섹션 - 스와치 픽업 요청 관련 기능
    """
    
    def __init__(self, parent=None):
        super().__init__("SBO 픽업 요청", parent)
        
        # 헤더 버튼 추가
        self.refresh_button = self.add_header_button("새로고침", self._on_refresh_clicked)
        self.send_button = self.add_header_button("메시지 전송", self._on_send_clicked, primary=True)
        
        # 콘텐츠 설정
        self.setup_content()
    
    def setup_content(self):
        """콘텐츠 설정"""
        # 필터 영역
        filter_widget = QWidget()
        filter_layout = QHBoxLayout(filter_widget)
        filter_layout.setContentsMargins(0, 0, 0, 0)
        
        # 검색창
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("판매자, 픽업번호 검색...")
        self.search_input.textChanged.connect(self._on_search_changed)
        
        # 상태 필터
        self.status_filter = QComboBox()
        self.status_filter.addItem("모든 상태", "all")
        self.status_filter.addItem("대기중", "pending")
        self.status_filter.addItem("전송완료", "sent")
        self.status_filter.addItem("전송실패", "failed")
        self.status_filter.currentIndexChanged.connect(self._on_filter_changed)
        
        # 필터 레이아웃에 추가
        filter_layout.addWidget(QLabel("검색:"))
        filter_layout.addWidget(self.search_input)
        filter_layout.addWidget(QLabel("상태:"))
        filter_layout.addWidget(self.status_filter)
        filter_layout.addStretch()
        
        self.content_layout.addWidget(filter_widget)
        
        # 테이블 위젯
        self.table = QTableWidget()
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        # 테이블 헤더 설정
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "선택", "판매자", "픽업번호", "스와치 정보", "픽업 날짜", "픽업 시간", "주소", "상태"
        ])
        
        # 테이블 헤더 설정
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # 선택
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # 판매자
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # 픽업번호
        header.setSectionResizeMode(3, QHeaderView.Stretch)           # 스와치 정보
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # 픽업 날짜
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # 픽업 시간
        header.setSectionResizeMode(6, QHeaderView.Stretch)           # 주소
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
        
        # 테스트 데이터 로드
        self._load_dummy_data()
    
    def _load_dummy_data(self):
        """테스트 목적의 더미 데이터 로드"""
        dummy_data = [
            {"seller": "판매자A", "pickup_number": "PK-2023-001", "swatch_info": "면 원단 외 3종", "pickup_date": "2023-05-25", "pickup_time": "오전 10:00", "address": "서울시 강남구 테헤란로 123", "status": "대기중"},
            {"seller": "판매자B", "pickup_number": "PK-2023-002", "swatch_info": "실크 혼방 외 2종", "pickup_date": "2023-05-26", "pickup_time": "오후 2:00", "address": "서울시 서초구 서초대로 456", "status": "대기중"},
            {"seller": "판매자C", "pickup_number": "PK-2023-003", "swatch_info": "울 개버딘 외 1종", "pickup_date": "2023-05-27", "pickup_time": "오전 11:30", "address": "서울시 성동구 왕십리로 789", "status": "전송완료"},
            {"seller": "판매자A", "pickup_number": "PK-2023-004", "swatch_info": "폴리에스터 트윌 외 4종", "pickup_date": "2023-05-28", "pickup_time": "오후 3:30", "address": "서울시 강남구 테헤란로 123", "status": "전송실패"}
        ]
        
        # 테이블 데이터 설정
        self.table.setRowCount(len(dummy_data))
        
        for row, item in enumerate(dummy_data):
            # 체크박스 셀
            checkbox = QCheckBox()
            self.table.setCellWidget(row, 0, self._create_checkbox_widget(checkbox))
            
            # 나머지 데이터 셀
            self.table.setItem(row, 1, QTableWidgetItem(item["seller"]))
            self.table.setItem(row, 2, QTableWidgetItem(item["pickup_number"]))
            self.table.setItem(row, 3, QTableWidgetItem(item["swatch_info"]))
            self.table.setItem(row, 4, QTableWidgetItem(item["pickup_date"]))
            self.table.setItem(row, 5, QTableWidgetItem(item["pickup_time"]))
            self.table.setItem(row, 6, QTableWidgetItem(item["address"]))
            self.table.setItem(row, 7, QTableWidgetItem(item["status"]))
            
            # 상태에 따른 배경색 설정
            status_item = self.table.item(row, 7)
            if item["status"] == "대기중":
                status_item.setBackground(QColor(get_theme().get_color("warning")))
            elif item["status"] == "전송완료":
                status_item.setBackground(QColor(get_theme().get_color("success")))
            elif item["status"] == "전송실패":
                status_item.setBackground(QColor(get_theme().get_color("error")))
        
        # 통계 업데이트
        self.stats_label.setText(f"총 {len(dummy_data)}건")
    
    def _create_checkbox_widget(self, checkbox):
        """체크박스를 위한 위젯 생성"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignCenter)
        layout.addWidget(checkbox)
        return widget
    
    def _on_refresh_clicked(self):
        """새로고침 버튼 클릭 이벤트"""
        self.log("픽업 요청 데이터를 새로고침합니다.", LogType.INFO.value)
        # TODO: 실제로 데이터 새로고침 구현
    
    def _on_send_clicked(self):
        """메시지 전송 버튼 클릭 이벤트"""
        # 선택된 항목 찾기
        selected_rows = []
        for row in range(self.table.rowCount()):
            checkbox_widget = self.table.cellWidget(row, 0)
            checkbox = checkbox_widget.findChild(QCheckBox)
            if checkbox and checkbox.isChecked():
                selected_rows.append(row)
        
        if not selected_rows:
            self.log("선택된 항목이 없습니다.", LogType.WARNING.value)
            return
        
        self.log(f"{len(selected_rows)}건의 픽업 요청 메시지를 전송합니다.", LogType.INFO.value)
        # TODO: 실제로 메시지 전송 구현
    
    def _on_search_changed(self, text):
        """검색어 변경 이벤트"""
        # TODO: 검색 기능 구현
        self.log(f"검색어: {text}", LogType.DEBUG.value)
    
    def _on_filter_changed(self, index):
        """필터 변경 이벤트"""
        filter_value = self.status_filter.itemData(index)
        self.log(f"상태 필터: {filter_value}", LogType.DEBUG.value)
        # TODO: 필터링 기능 구현
    
    def _on_select_all_clicked(self):
        """모두 선택 버튼 클릭 이벤트"""
        for row in range(self.table.rowCount()):
            checkbox_widget = self.table.cellWidget(row, 0)
            checkbox = checkbox_widget.findChild(QCheckBox)
            if checkbox:
                checkbox.setChecked(True)
    
    def _on_deselect_all_clicked(self):
        """모두 해제 버튼 클릭 이벤트"""
        for row in range(self.table.rowCount()):
            checkbox_widget = self.table.cellWidget(row, 0)
            checkbox = checkbox_widget.findChild(QCheckBox)
            if checkbox:
                checkbox.setChecked(False)
    
    def on_section_activated(self):
        """섹션이 활성화될 때 호출"""
        self.log("SBO 픽업 요청 섹션이 활성화되었습니다.", LogType.INFO.value)
        
        # 새로고침 버튼을 통해서만 데이터 로드
        # '새로고침' 버튼을 클릭하여 픽업 요청 데이터를 가져오세요.
    
    def on_section_deactivated(self):
        """섹션이 비활성화될 때 호출"""
        pass 