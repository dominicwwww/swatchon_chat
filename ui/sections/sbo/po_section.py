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

from core.types import LogType
from ui.sections.base_section import BaseSection
from ui.theme import get_theme

class SboPoSection(BaseSection):
    """
    SBO 스와치 발주 섹션 - 스와치 발주 관련 기능
    """
    
    def __init__(self, parent=None):
        super().__init__("SBO 스와치 발주", parent)
        
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
        self.search_input.setPlaceholderText("판매자, 발주번호 검색...")
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
            "선택", "판매자", "스와치 번호", "원단명", "색상", "수량", "발주일", "상태"
        ])
        
        # 테이블 헤더 설정
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # 선택
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # 판매자
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
        
        # 테스트 데이터 로드
        self._load_dummy_data()
    
    def _load_dummy_data(self):
        """테스트 목적의 더미 데이터 로드"""
        dummy_data = [
            {"seller": "판매자A", "swatch_number": "SW-2023-001", "fabric_name": "면 원단 30수", "color": "화이트", "quantity": 5, "date": "2023-05-15", "status": "대기중"},
            {"seller": "판매자B", "swatch_number": "SW-2023-002", "fabric_name": "실크 혼방 원단", "color": "네이비", "quantity": 3, "date": "2023-05-16", "status": "대기중"},
            {"seller": "판매자C", "swatch_number": "SW-2023-003", "fabric_name": "울 개버딘", "color": "그레이", "quantity": 4, "date": "2023-05-17", "status": "전송완료"},
            {"seller": "판매자A", "swatch_number": "SW-2023-004", "fabric_name": "폴리에스터 트윌", "color": "블랙", "quantity": 2, "date": "2023-05-18", "status": "전송실패"}
        ]
        
        # 테이블 데이터 설정
        self.table.setRowCount(len(dummy_data))
        
        for row, item in enumerate(dummy_data):
            # 체크박스 셀
            checkbox = QCheckBox()
            self.table.setCellWidget(row, 0, self._create_checkbox_widget(checkbox))
            
            # 나머지 데이터 셀
            self.table.setItem(row, 1, QTableWidgetItem(item["seller"]))
            self.table.setItem(row, 2, QTableWidgetItem(item["swatch_number"]))
            self.table.setItem(row, 3, QTableWidgetItem(item["fabric_name"]))
            self.table.setItem(row, 4, QTableWidgetItem(item["color"]))
            self.table.setItem(row, 5, QTableWidgetItem(str(item["quantity"])))
            self.table.setItem(row, 6, QTableWidgetItem(item["date"]))
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
        self.log("스와치 발주 데이터를 새로고침합니다.", LogType.INFO.value)
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
        
        self.log(f"{len(selected_rows)}건의 스와치 발주 메시지를 전송합니다.", LogType.INFO.value)
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
        self.log("SBO 스와치 발주 섹션이 활성화되었습니다.", LogType.INFO.value)
        
        # 새로고침 버튼을 통해서만 데이터 로드
        # '새로고침' 버튼을 클릭하여 스와치 발주 데이터를 가져오세요.
    
    def on_section_deactivated(self):
        """섹션이 비활성화될 때 호출"""
        pass 