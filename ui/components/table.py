"""
테이블 공통 컴포넌트 - 재사용 가능한 테이블 기능
"""
from typing import List, Dict, Any, Optional, Callable
from PySide6.QtWidgets import (
    QTableWidget, QTableWidgetItem, QHeaderView, QWidget, QHBoxLayout,
    QCheckBox, QLabel, QVBoxLayout, QPushButton, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QBrush

class BaseTable(QTableWidget):
    """테이블 기본 컴포넌트"""
    
    # 시그널 정의
    selection_changed = Signal(list)  # 선택된 항목 변경 시그널
    
    def __init__(self, parent=None, log_function=None):
        super().__init__(parent)
        self.log_function = log_function
        
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
        
        # 전체 선택/해제 버튼
        self.select_all_button = QPushButton("전체 선택")
        self.select_all_button.clicked.connect(self._on_select_all_clicked)
        self.select_all_button.setMaximumWidth(80)
        self.top_layout.addWidget(self.select_all_button)

        self.clear_selection_button = QPushButton("선택 해제")
        self.clear_selection_button.clicked.connect(self._on_clear_selection_clicked)
        self.clear_selection_button.setMaximumWidth(80)
        self.top_layout.addWidget(self.clear_selection_button)
        
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
        
        # 레이아웃 정렬
        self.top_layout.addStretch()
        
        # 상단 위젯을 메인 레이아웃에 추가
        self.main_layout.addWidget(self.top_widget)
    
    def setup_table(self):
        """테이블 초기 설정"""
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setSelectionMode(QTableWidget.SingleSelection)
        self.setEditTriggers(QTableWidget.NoEditTriggers)
        self.setSortingEnabled(True)
        
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
    
    def setup_columns(self, column_names: List[str]):
        """컬럼 설정"""
        self.setColumnCount(len(column_names))
        self.setHorizontalHeaderLabels(column_names)
        
        # 컬럼 너비 자동 조정
        header = self.horizontalHeader()
        for i in range(len(column_names)):
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
    
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
        self.selection_label.setText(f"선택된 항목: {selected_count:,}개")

    def _emit_selection_changed(self, is_bulk_update: bool = False):
        """선택된 항목 변경 시그널 발생 (테이블 정렬 순서 반영)"""
        selected_items = []
        selected_count = 0
        # 테이블의 현재 row 순서대로 순회
        for row in range(self.rowCount()):
            checkbox_widget = self.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox and checkbox.isChecked():
                    selected_count += 1
                    try:
                        # 각 컬럼의 데이터 확인 (전체 row 데이터를 dict로 수집)
                        item_data = {}
                        for col in range(self.columnCount()):
                            header = self.horizontalHeaderItem(col)
                            key = header.text() if header else str(col)
                            cell_item = self.item(row, col)
                            item_data[key] = cell_item.text() if cell_item else None
                        selected_items.append(item_data)
                    except (ValueError, AttributeError) as e:
                        print(f"행 {row} 데이터 수집 중 오류: {e}")
                        continue
        # 선택된 항목 수 업데이트
        self._update_selection_label()
        # 시그널 발생 (정렬 순서 반영된 selected_items)
        self.selection_changed.emit(selected_items)
    
    def add_row(self, row_data: Dict[str, Any], row_index: Optional[int] = None):
        """행 추가"""
        if row_index is None:
            row_index = self.rowCount()
        
        self.insertRow(row_index)
        
        # 체크박스 추가
        checkbox = QCheckBox()
        checkbox.setProperty("row_index", row_index)
        checkbox.stateChanged.connect(self._on_any_checkbox_changed)
        self.setCellWidget(row_index, 0, self._create_checkbox_widget(checkbox))
        
        # 데이터 추가
        for col, (key, value) in enumerate(row_data.items(), start=1):
            if col < self.columnCount():
                item = QTableWidgetItem(str(value) if value is not None else "")
                self.setItem(row_index, col, item)
    
    def update_row(self, row_index: int, row_data: Dict[str, Any]):
        """행 업데이트"""
        if 0 <= row_index < self.rowCount():
            for col, (key, value) in enumerate(row_data.items(), start=1):
                if col < self.columnCount():
                    item = QTableWidgetItem(str(value) if value is not None else "")
                    self.setItem(row_index, col, item)
    
    def remove_row(self, row_index: int):
        """행 삭제"""
        if 0 <= row_index < self.rowCount():
            self.removeRow(row_index)
    
    def clear_table(self):
        """테이블 초기화"""
        self.setRowCount(0)
        self._update_selection_label()
    
    def get_selected_rows(self) -> List[Dict[str, Any]]:
        """선택된 행 데이터 반환"""
        selected_items = []
        for row in range(self.rowCount()):
            checkbox = self.cellWidget(row, 0).findChild(QCheckBox)
            if checkbox and checkbox.isChecked():
                row_data = {}
                for col in range(1, self.columnCount()):
                    header = self.horizontalHeaderItem(col)
                    key = header.text() if header else str(col)
                    cell_item = self.item(row, col)
                    row_data[key] = cell_item.text() if cell_item else None
                selected_items.append(row_data)
        return selected_items
    
    def set_cell_color(self, row: int, col: int, background_color: QColor, text_color: QColor):
        """셀 색상 설정"""
        if 0 <= row < self.rowCount() and 0 <= col < self.columnCount():
            item = self.item(row, col)
            if item:
                item.setBackground(background_color)
                item.setForeground(text_color)
    
    def set_cell_link(self, row: int, col: int, url: str):
        """셀에 링크 설정"""
        if 0 <= row < self.rowCount() and 0 <= col < self.columnCount():
            item = self.item(row, col)
            if item:
                item.setForeground(QBrush(QColor(0, 102, 204)))
                item.setData(Qt.UserRole, url)
    
    def mousePressEvent(self, event):
        """마우스 클릭 이벤트 처리"""
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtCore import QUrl
        index = self.indexAt(event.pos())
        if index.isValid():
            col = index.column()
            item = self.item(index.row(), col)
            if item and item.data(Qt.UserRole):
                QDesktopServices.openUrl(QUrl(item.data(Qt.UserRole)))
        super().mousePressEvent(event) 