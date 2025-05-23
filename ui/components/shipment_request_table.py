"""
FBO 출고 요청 테이블 컴포넌트
"""
from typing import List, Dict, Any
from PySide6.QtWidgets import (
    QTableWidget, QTableWidgetItem, QHeaderView, QWidget, QHBoxLayout,
    QCheckBox, QLabel, QVBoxLayout, QComboBox, QPushButton, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPixmap
from datetime import datetime

from ui.theme import get_theme
from ui.components.log_widget import LOG_INFO, LOG_WARNING, LOG_ERROR
from core.schemas import PurchaseProduct

class ShipmentRequestTable(QTableWidget):
    """FBO 출고 요청 테이블 컴포넌트"""
    
    # 시그널 정의
    selection_changed = Signal(list)  # 선택된 항목 변경 시그널
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.load_photo = False  # 사진 로드 여부 (기본값: 비활성화)
        
        # 메인 레이아웃 설정
        self.main_widget = QWidget()
        self.main_layout = QVBoxLayout(self.main_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        self._init_ui()
        self.setup_table()
        
        # 테이블을 메인 레이아웃에 추가
        self.main_layout.addWidget(self)
        
    def _init_ui(self):
        """상단 UI 초기화"""
        self.top_widget = QWidget()
        self.top_layout = QHBoxLayout(self.top_widget)
        self.top_layout.setContentsMargins(0, 0, 0, 8)  # 하단 여백 추가
        
        # 사진 로드 체크박스
        self.photo_checkbox = QCheckBox("사진 로드")
        self.photo_checkbox.setChecked(False)  # 초기값: 비활성화
        self.photo_checkbox.stateChanged.connect(self._on_photo_checkbox_changed)
        self.top_layout.addWidget(self.photo_checkbox)
        
        # 레이아웃 정렬
        self.top_layout.addStretch()
        
        # 상단 위젯을 메인 레이아웃에 추가
        self.main_layout.addWidget(self.top_widget)
        
    def setup_table(self):
        """테이블 초기 설정"""
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setSelectionMode(QTableWidget.SingleSelection)
        self.setEditTriggers(QTableWidget.NoEditTriggers)
        self.setSortingEnabled(True)  # 헤더 클릭 정렬 활성화
        
        # 컬럼 정의
        self.setColumnCount(10)
        self.setHorizontalHeaderLabels([
            "", "ID", "스토어명", "동대문주소", "품질명", 
            "컬러번호", "컬러코드", "수량", "구매코드", "픽업일시"
        ])
        
        # 컬럼 너비 설정
        header = self.horizontalHeader()
        for i in range(10):
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
            
        # 헤더 클릭 이벤트 연결
        self.horizontalHeader().sectionClicked.connect(self._on_header_clicked)
        
        # 선택 컬럼 헤더에 체크박스 추가
        self.header_checkbox = QCheckBox()
        self.header_checkbox.stateChanged.connect(self._on_header_checkbox_changed)
        
        # 헤더 아이템 생성 및 체크박스 설정
        header_item = QTableWidgetItem()
        header_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
        header_item.setCheckState(Qt.Unchecked)
        self.setHorizontalHeaderItem(0, header_item)
        
        # 헤더 아이템 클릭 이벤트 처리
        self.horizontalHeader().sectionClicked.connect(self._on_header_section_clicked)
        
    def update_data(self, data: List[PurchaseProduct]):
        """테이블 데이터 업데이트"""
        try:
            print(f"[update_data] 테이블 데이터 업데이트 시작: {len(data)}건")
            
            # 현재 데이터 저장
            self._current_data = data
            
            self.setRowCount(0)
            if not data:
                print("[update_data] 데이터 없음")
                return
                
            total_rows = len(data)
            self.setRowCount(total_rows)
            
            for row_idx, item in enumerate(data):
                try:
                    print(f"[update_data] {row_idx+1}/{total_rows}행 처리 시작")
                    
                    # 체크박스
                    checkbox = QCheckBox()
                    checkbox.stateChanged.connect(
                        lambda state, r=row_idx: self._on_checkbox_changed(state, r)
                    )
                    self.setCellWidget(row_idx, 0, self._create_checkbox_widget(checkbox))
                    
                    # ID
                    self.setItem(row_idx, 1, QTableWidgetItem(str(item.id)))
                    
                    # 스토어명
                    self.setItem(row_idx, 2, QTableWidgetItem(item.store_name))
                    
                    # 동대문주소
                    self.setItem(row_idx, 3, QTableWidgetItem(item.store_ddm_address))
                    
                    # 품질명
                    self.setItem(row_idx, 4, QTableWidgetItem(item.quality_name))
                    
                    # 컬러번호
                    self.setItem(row_idx, 5, QTableWidgetItem(str(item.color_number)))
                    
                    # 컬러코드
                    self.setItem(row_idx, 6, QTableWidgetItem(str(item.color_code or "")))
                    
                    # 수량
                    quantity_item = QTableWidgetItem(str(item.quantity))
                    quantity_item.setData(Qt.UserRole, item.quantity)  # 정렬을 위한 데이터
                    self.setItem(row_idx, 7, quantity_item)
                    
                    # 구매코드
                    self.setItem(row_idx, 8, QTableWidgetItem(item.purchase_code))
                    
                    # 픽업일시
                    pickup_date = item.pickup_at.strftime("%Y-%m-%d %H:%M")
                    self.setItem(row_idx, 9, QTableWidgetItem(pickup_date))
                    
                    print(f"[update_data] {row_idx+1}/{total_rows}행 처리 완료")
                except Exception as row_error:
                    print(f"[update_data] {row_idx+1}행 처리 중 오류: {str(row_error)}")
                    for col in range(self.columnCount()):
                        self.setItem(row_idx, col, QTableWidgetItem(""))
            
            print(f"[update_data] {total_rows}행까지 처리 완료")
        except Exception as e:
            print(f"테이블 업데이트 중 오류: {str(e)}")
            self.setRowCount(0)
    
    def _on_checkbox_changed(self, state: int, row: int):
        """체크박스 상태 변경 이벤트"""
        selected_items = []
        for row in range(self.rowCount()):
            checkbox = self.cellWidget(row, 0).findChild(QCheckBox)
            if checkbox and checkbox.isChecked():
                selected_items.append({
                    "id": int(self.item(row, 1).text()),
                    "store_name": self.item(row, 2).text(),
                    "purchase_code": self.item(row, 8).text()
                })
        self.selection_changed.emit(selected_items)
    
    def _create_checkbox_widget(self, checkbox):
        """체크박스를 위한 위젯 생성"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignCenter)
        layout.addWidget(checkbox)
        return widget
    
    def _on_header_section_clicked(self, column):
        """헤더 섹션 클릭 처리"""
        if column == 0:  # 선택 컬럼
            header_item = self.horizontalHeaderItem(0)
            if header_item:
                # 현재 상태의 반대로 변경
                new_state = Qt.Unchecked if header_item.checkState() == Qt.Checked else Qt.Checked
                header_item.setCheckState(new_state)
                # 모든 행의 체크박스 상태 변경
                for row in range(self.rowCount()):
                    checkbox = self.cellWidget(row, 0).findChild(QCheckBox)
                    if checkbox:
                        checkbox.setChecked(new_state == Qt.Checked)
    
    def _on_header_checkbox_changed(self, state):
        """헤더 체크박스 상태 변경 처리"""
        for row in range(self.rowCount()):
            checkbox = self.cellWidget(row, 0).findChild(QCheckBox)
            if checkbox:
                checkbox.setChecked(state == Qt.Checked)
    
    def _on_header_clicked(self, column):
        """헤더 클릭 시 정렬 처리"""
        if column == 0:  # 선택 컬럼은 정렬 제외
            return
            
        # 현재 정렬 방향 확인
        current_order = self.horizontalHeader().sortIndicatorOrder()
        new_order = Qt.DescendingOrder if current_order == Qt.AscendingOrder else Qt.AscendingOrder
        
        # 데이터 정렬
        self.sortItems(column, new_order)
        
        # 정렬 방향 표시
        self.horizontalHeader().setSortIndicator(column, new_order)
    
    def _on_photo_checkbox_changed(self, state):
        """사진 로드 체크박스 상태 변경"""
        self.load_photo = (state == Qt.Checked)
        # 현재 데이터로 테이블 업데이트
        if hasattr(self, '_current_data'):
            self.update_data(self._current_data) 