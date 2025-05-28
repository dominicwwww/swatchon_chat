"""
관리비 정산 테이블 컴포넌트
"""
from typing import List, Dict, Any
from PySide6.QtWidgets import (
    QTableWidget, QTableWidgetItem, QHeaderView, QWidget, QHBoxLayout,
    QCheckBox, QLabel, QVBoxLayout, QPushButton, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from datetime import datetime

from ui.theme import get_theme
from ui.components.log_widget import LOG_INFO, LOG_WARNING, LOG_ERROR

class MaintenanceFeeTable(QTableWidget):
    """관리비 정산 테이블 컴포넌트"""
    
    # 시그널 정의
    selection_changed = Signal(list)  # 선택된 항목 변경 시그널
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
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
        
        # 선택된 항목 수 표시 라벨
        self.selection_label = QLabel("선택된 항목: 0개")
        self.selection_label.setStyleSheet("""
            QLabel {
                color: #007bff;
                font-weight: bold;
                padding: 4px 8px;
                background-color: #e3f2fd;
                border-radius: 4px;
                border: 1px solid #bbdefb;
            }
        """)
        self.top_layout.addWidget(self.selection_label)
        
        # 전체 선택/해제 버튼
        self.select_all_button = QPushButton("전체 선택")
        self.select_all_button.clicked.connect(self._on_select_all_clicked)
        self.select_all_button.setMaximumWidth(80)
        self.top_layout.addWidget(self.select_all_button)
        
        self.clear_selection_button = QPushButton("선택 해제")
        self.clear_selection_button.clicked.connect(self._on_clear_selection_clicked)
        self.clear_selection_button.setMaximumWidth(80)
        self.top_layout.addWidget(self.clear_selection_button)
        
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
        self.setColumnCount(6)
        self.setHorizontalHeaderLabels([
            "",  # 체크박스 컬럼
            "날짜",
            "호수",
            "공급가액",
            "부가세",
            "합계"
        ])
        
        # 컬럼 너비 설정
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # 체크박스
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # 날짜
        header.setSectionResizeMode(2, QHeaderView.Stretch)           # 호수
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # 공급가액
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # 부가세
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # 합계
        
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
        
    def update_data(self, data: List[Dict[str, Any]]):
        """테이블 데이터 업데이트"""
        try:
            self.setRowCount(0)
            if not data:
                return
                
            total_rows = len(data)
            self.setRowCount(total_rows)
            
            for row_idx, item in enumerate(data):
                try:
                    # 체크박스
                    checkbox = QCheckBox()
                    checkbox.setProperty("row_index", row_idx)
                    checkbox.stateChanged.connect(self._on_any_checkbox_changed)
                    self.setCellWidget(row_idx, 0, self._create_checkbox_widget(checkbox))
                    
                    # 날짜
                    date_str = item.get('date', '')
                    self.setItem(row_idx, 1, QTableWidgetItem(date_str))
                    
                    # 호수
                    unit_number = item.get('unit_number', '')
                    self.setItem(row_idx, 2, QTableWidgetItem(unit_number))
                    
                    # 공급가액
                    supply_amount = item.get('supply_amount', 0)
                    supply_item = QTableWidgetItem(f"{supply_amount:,}원")
                    supply_item.setData(Qt.UserRole, supply_amount)  # 정렬을 위한 데이터
                    self.setItem(row_idx, 3, supply_item)
                    
                    # 부가세
                    vat_amount = item.get('vat_amount', 0)
                    vat_item = QTableWidgetItem(f"{vat_amount:,}원")
                    vat_item.setData(Qt.UserRole, vat_amount)  # 정렬을 위한 데이터
                    self.setItem(row_idx, 4, vat_item)
                    
                    # 합계
                    total_amount = supply_amount + vat_amount
                    total_item = QTableWidgetItem(f"{total_amount:,}원")
                    total_item.setData(Qt.UserRole, total_amount)  # 정렬을 위한 데이터
                    self.setItem(row_idx, 5, total_item)
                    
                except Exception as row_error:
                    print(f"행 처리 중 오류: {str(row_error)}")
                    for col in range(self.columnCount()):
                        self.setItem(row_idx, col, QTableWidgetItem(""))
            
        except Exception as e:
            print(f"테이블 업데이트 중 오류: {str(e)}")
            self.setRowCount(0)
    
    def _on_any_checkbox_changed(self, state: int):
        """체크박스 상태 변경 이벤트"""
        if not getattr(self, '_is_bulk_update', False):
            self._emit_selection_changed()
    
    def _emit_selection_changed(self, is_bulk_update: bool = False):
        """선택된 항목 변경 시그널 발생"""
        selected_items = []
        selected_count = 0
        
        for row in range(self.rowCount()):
            checkbox_widget = self.cellWidget(row, 0)
            
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                
                if checkbox and checkbox.isChecked():
                    selected_count += 1
                    try:
                        # 각 컬럼의 데이터 확인
                        date_item = self.item(row, 1)
                        unit_item = self.item(row, 2)
                        supply_item = self.item(row, 3)
                        vat_item = self.item(row, 4)
                        total_item = self.item(row, 5)
                        
                        if all([date_item, unit_item, supply_item, vat_item, total_item]):
                            selected_item = {
                                "date": date_item.text(),
                                "unit_number": unit_item.text(),
                                "supply_amount": supply_item.data(Qt.UserRole),
                                "vat_amount": vat_item.data(Qt.UserRole),
                                "total_amount": total_item.data(Qt.UserRole)
                            }
                            selected_items.append(selected_item)
                            
                    except (ValueError, AttributeError) as e:
                        print(f"행 {row} 데이터 수집 중 오류: {e}")
                        continue
        
        # 선택된 항목 수 업데이트
        self._update_selection_label()
        
        # 시그널 발생
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
                self._is_bulk_update = True
                for row in range(self.rowCount()):
                    checkbox = self.cellWidget(row, 0).findChild(QCheckBox)
                    if checkbox:
                        checkbox.setChecked(new_state == Qt.Checked)
                # 선택 상태 업데이트 및 시그널 발생 (한 번만)
                self._emit_selection_changed(is_bulk_update=True)
                self._is_bulk_update = False
    
    def _on_header_checkbox_changed(self, state):
        """헤더 체크박스 상태 변경 처리"""
        for row in range(self.rowCount()):
            checkbox = self.cellWidget(row, 0).findChild(QCheckBox)
            if checkbox:
                checkbox.setChecked(state == Qt.Checked)
        # 선택 상태 업데이트 및 시그널 발생
        self._emit_selection_changed()
    
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
    
    def _on_select_all_clicked(self):
        """전체 선택 버튼 클릭 처리"""
        self._is_bulk_update = True
        for row in range(self.rowCount()):
            checkbox = self.cellWidget(row, 0).findChild(QCheckBox)
            if checkbox:
                checkbox.setChecked(True)
        # 선택 상태 업데이트 및 시그널 발생 (한 번만)
        self._emit_selection_changed(is_bulk_update=True)
        self._is_bulk_update = False
    
    def _on_clear_selection_clicked(self):
        """선택 해제 버튼 클릭 처리"""
        self._is_bulk_update = True
        for row in range(self.rowCount()):
            checkbox = self.cellWidget(row, 0).findChild(QCheckBox)
            if checkbox:
                checkbox.setChecked(False)
        # 선택 상태 업데이트 및 시그널 발생 (한 번만)
        self._emit_selection_changed(is_bulk_update=True)
        self._is_bulk_update = False
    
    def _update_selection_label(self):
        """선택된 항목 수 업데이트"""
        selected_count = sum(1 for row in range(self.rowCount()) if self.cellWidget(row, 0).findChild(QCheckBox).isChecked())
        self.selection_label.setText(f"선택된 항목: {selected_count}개") 