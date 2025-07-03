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

from ui.theme import get_theme
from core.constants import TABLE_DISPLAY_CONFIG, SWATCH_PICKUP_CONFIG

class NumericTableWidgetItem(QTableWidgetItem):
    """숫자 정렬을 지원하는 테이블 아이템"""
    
    def __init__(self, text: str, numeric_value: float = None):
        super().__init__(text)
        self._numeric_value = numeric_value
        
        # 숫자 값이 제공되지 않은 경우 텍스트에서 추출 시도
        if self._numeric_value is None:
            self._numeric_value = self._extract_numeric_value(text)
    
    def _extract_numeric_value(self, text: str) -> float:
        """텍스트에서 숫자 값 추출"""
        if not text:
            return 0.0
        
        try:
            # 콤마와 통화 기호 제거
            clean_text = text.replace(',', '').replace('원', '').replace('$', '').strip()
            return float(clean_text)
        except (ValueError, TypeError):
            return 0.0
    
    def __lt__(self, other):
        """정렬을 위한 비교 연산자"""
        if isinstance(other, NumericTableWidgetItem):
            return self._numeric_value < other._numeric_value
        return super().__lt__(other)

class BaseTable(QTableWidget):
    """테이블 기본 컴포넌트"""
    
    # 시그널 정의
    selection_changed = Signal(list)  # 선택된 항목 변경 시그널
    
    def __init__(self, parent=None, log_function=None):
        super().__init__(parent)
        self.log_function = log_function
        
        # 숫자 컬럼 인덱스 저장
        self.numeric_columns = set()
        
        # 벌크 업데이트 플래그
        self._is_bulk_update = False
        
        # 메인 레이아웃 설정
        self.main_widget = QWidget()
        self.main_layout = QVBoxLayout(self.main_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        self._init_ui()
        self.setup_table()
        
        # 테이블을 메인 레이아웃에 추가
        self.main_layout.addWidget(self)
        
        # 테마 변경 시 스타일 업데이트
        self._update_table_style()
        get_theme().theme_changed.connect(self._update_table_style)
    
    def _update_table_style(self):
        """테마에 맞게 테이블 스타일 업데이트"""
        theme = get_theme()
        
        # 테이블 전체 스타일 (개별 아이템 색상 덮어쓰기 방지)
        self.setStyleSheet(f"""
            QTableWidget {{
                background-color: {theme.get_color("card_bg")};
                gridline-color: {theme.get_color("border")};
                border: 1px solid {theme.get_color("border")};
                border-radius: 4px;
                selection-background-color: {theme.get_color("primary")};
                selection-color: white;
            }}
            
            QTableWidget::item {{
                padding: 4px;
                border: none;
                /* 개별 아이템의 배경색과 텍스트 색상 강제 적용 방지 */
                /* background-color와 color 속성 제거하여 개별 설정 우선시 */
            }}
            
            QTableWidget::item:selected {{
                /* 선택된 아이템만 스타일 적용 */
                background-color: {theme.get_color("primary")} !important;
                color: white !important;
            }}
            
            QTableWidget::item:hover:!selected {{
                /* hover 시에는 배경색 변경하지 않고 약간의 효과만 */
                border: 1px solid {theme.get_color("primary")};
                /* 개별 설정된 배경색과 텍스트 색상 유지 */
            }}
            
            QHeaderView::section {{
                background-color: {theme.get_color("sidebar_bg")};
                color: {theme.get_color("text_primary")};
                padding: 6px;
                border: none;
                border-right: 1px solid {theme.get_color("border")};
                border-bottom: 1px solid {theme.get_color("border")};
                font-weight: bold;
            }}
            
            QHeaderView::section:hover {{
                background-color: {theme.get_color("input_bg")};
            }}
            
            QCheckBox {{
                background-color: transparent;
                color: {theme.get_color("text_primary")};
            }}
            
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border: 2px solid {theme.get_color("border")};
                border-radius: 3px;
                background-color: {theme.get_color("input_bg")};
            }}
            
            QCheckBox::indicator:checked {{
                background-color: {theme.get_color("primary")};
                border-color: {theme.get_color("primary")};
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iMTIiIHZpZXdCb3g9IjAgMCAxMiAxMiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTEwIDNMNC41IDguNUwyIDYiIHN0cm9rZT0id2hpdGUiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIi8+Cjwvc3ZnPgo=);
            }}
            
            QCheckBox::indicator:hover {{
                border-color: {theme.get_color("primary")};
            }}
        """)
        
        # 선택 라벨 스타일 업데이트
        if hasattr(self, 'selection_label'):
            self.selection_label.setStyleSheet(f"""
                QLabel {{
                    color: {theme.get_color("primary")};
                    font-weight: bold;
                    padding: 4px 8px;
                    background-color: {theme.get_color("sidebar_bg")};
                    border-radius: 4px;
                    border: 1px solid {theme.get_color("border")};
                }}
            """)
    
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
        
        # 정렬 상태 추적을 위한 변수
        self._last_sorted_column = -1
        self._last_sort_order = Qt.AscendingOrder
        
        # 헤더 클릭 이벤트 연결 (정렬용)
        self.horizontalHeader().sectionClicked.connect(self._on_header_section_clicked)
        
        # 선택 컬럼 헤더에 체크박스 추가
        self.header_checkbox = QCheckBox()
        self.header_checkbox.stateChanged.connect(self._on_header_checkbox_changed)
        
        # 헤더 아이템 생성 및 체크박스 설정
        header_item = QTableWidgetItem()
        header_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
        header_item.setCheckState(Qt.Unchecked)
        self.setHorizontalHeaderItem(0, header_item)
    
    def _on_header_section_clicked(self, column):
        """헤더 섹션 클릭 처리 (체크박스 + 정렬)"""
        if column == 0:  # 선택 컬럼 - 체크박스 처리
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
        else:  # 다른 컬럼 - 정렬 처리
            self._handle_column_sort(column)
    
    def _handle_column_sort(self, column):
        """컬럼 정렬 처리"""
        # 현재 정렬 상태 확인
        if self._last_sorted_column == column:
            # 같은 컬럼을 다시 클릭한 경우 정렬 방향 토글
            if self._last_sort_order == Qt.AscendingOrder:
                new_order = Qt.DescendingOrder
            else:
                new_order = Qt.AscendingOrder
        else:
            # 다른 컬럼을 클릭한 경우 오름차순으로 시작
            new_order = Qt.AscendingOrder
        
        # 정렬 실행
        self.sortItems(column, new_order)
        
        # 정렬 인디케이터 표시
        self.horizontalHeader().setSortIndicator(column, new_order)
        
        # 상태 저장
        self._last_sorted_column = column
        self._last_sort_order = new_order
        
        if self.log_function:
            order_text = "오름차순" if new_order == Qt.AscendingOrder else "내림차순"
            header_text = self.horizontalHeaderItem(column).text() if self.horizontalHeaderItem(column) else f"컬럼 {column}"
            self.log_function(f"정렬: {header_text} ({order_text})")
    
    def _on_header_checkbox_changed(self, state):
        """헤더 체크박스 상태 변경 처리"""
        for row in range(self.rowCount()):
            checkbox = self.cellWidget(row, 0).findChild(QCheckBox)
            if checkbox:
                checkbox.setChecked(state == Qt.Checked)
        # 선택 상태 업데이트 및 시그널 발생
        self._emit_selection_changed()
    
    def _on_header_clicked(self, column):
        """헤더 클릭 시 정렬 처리 (더 이상 사용하지 않음)"""
        # 이 메서드는 _on_header_section_clicked로 통합됨
        pass
    
    def setup_columns(self, column_names: List[str], resize_mode: str = "content"):
        """컬럼 설정"""
        self.setColumnCount(len(column_names))
        self.setHorizontalHeaderLabels(column_names)
        
        # 컬럼 너비 설정
        header = self.horizontalHeader()
        
        if resize_mode == "content":
            # 내용에 맞게 자동 조정 (기본값)
            for i in range(len(column_names)):
                header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        elif resize_mode == "stretch":
            # 테이블 너비에 맞게 균등 분할
            for i in range(len(column_names)):
                header.setSectionResizeMode(i, QHeaderView.Stretch)
        elif resize_mode == "interactive":
            # 사용자가 직접 조정 가능
            for i in range(len(column_names)):
                header.setSectionResizeMode(i, QHeaderView.Interactive)
        elif resize_mode == "mixed":
            # 혼합 모드: 첫 번째는 고정, 나머지는 내용에 맞게
            for i in range(len(column_names)):
                if i == 0:  # 선택 컬럼은 고정 크기
                    header.setSectionResizeMode(i, QHeaderView.Fixed)
                    header.resizeSection(i, 60)
                elif i == 1:  # ID 컬럼도 고정 크기
                    header.setSectionResizeMode(i, QHeaderView.Fixed)
                    header.resizeSection(i, 80)
                else:
                    header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        
        # 정렬 화살표를 위한 여유 공간 추가 (ResizeToContents 모드에서)
        if resize_mode in ["content", "mixed"]:
            # 테이블이 완전히 로드된 후 여백 추가를 위해 타이머 사용
            from PySide6.QtCore import QTimer
            QTimer.singleShot(100, self._adjust_column_widths_for_sort_indicator)
    
    def _adjust_column_widths_for_sort_indicator(self):
        """정렬 화살표를 위한 컬럼 너비 조정"""
        header = self.horizontalHeader()
        
        for i in range(self.columnCount()):
            # 선택 컬럼(0)과 고정 크기 컬럼은 제외
            if i == 0:
                continue
                
            # ResizeToContents 모드인 컬럼만 조정
            if header.sectionResizeMode(i) == QHeaderView.ResizeToContents:
                current_width = header.sectionSize(i)
                
                # 정렬 화살표를 위한 여유 공간 추가 (25px)
                # 헤더 텍스트가 짧은 경우 최소 너비도 보장
                min_width = 80  # 최소 너비
                arrow_padding = 25  # 정렬 화살표 여유 공간
                new_width = max(current_width + arrow_padding, min_width)
                
                # Interactive 모드로 변경하고 새 너비 설정
                header.setSectionResizeMode(i, QHeaderView.Interactive)
                header.resizeSection(i, new_width)
    
    def _create_checkbox_widget(self, checkbox):
        """체크박스를 위한 위젯 생성"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignCenter)
        layout.addWidget(checkbox)
        return widget
    
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
                item = self._create_table_item(str(value) if value is not None else "", col, value)
                self.setItem(row_index, col, item)
        
        # 첫 번째 행이 추가된 경우 컬럼 너비 재조정
        if self.rowCount() == 1:
            from PySide6.QtCore import QTimer
            QTimer.singleShot(50, self._adjust_column_widths_for_sort_indicator)
    
    def update_row(self, row_index: int, row_data: Dict[str, Any]):
        """행 업데이트"""
        if 0 <= row_index < self.rowCount():
            for col, (key, value) in enumerate(row_data.items(), start=1):
                if col < self.columnCount():
                    item = self._create_table_item(str(value) if value is not None else "", col, value)
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
        """셀 색상 설정 (강화된 버전 - 배경색 우선 적용)"""
        if 0 <= row < self.rowCount() and 0 <= col < self.columnCount():
            item = self.item(row, col)
            if item:
                # 배경색과 전경색 설정 (여러 방법으로 강력하게 적용)
                item.setBackground(QBrush(background_color))
                item.setForeground(QBrush(text_color))
                
                # 더 강력한 색상 적용을 위해 데이터로도 저장
                item.setData(Qt.UserRole + 1, background_color.name())
                item.setData(Qt.UserRole + 2, text_color.name())
                
                # 개별 셀에 인라인 스타일 적용 (가장 강력한 방법)
                from PySide6.QtCore import QModelIndex
                from PySide6.QtWidgets import QStyledItemDelegate
                
                # 셀의 인덱스를 가져와서 직접 스타일 설정
                index = self.model().index(row, col)
                if index.isValid():
                    # 백그라운드 롤과 포그라운드 롤 직접 설정
                    self.model().setData(index, QBrush(background_color), Qt.BackgroundRole)
                    self.model().setData(index, QBrush(text_color), Qt.ForegroundRole)
                
                # 아이템의 display role도 확실히 설정
                item.setData(Qt.BackgroundRole, QBrush(background_color))
                item.setData(Qt.ForegroundRole, QBrush(text_color))
    
    def set_cell_theme_color(self, row: int, col: int, bg_color_name: str, text_color_name: str):
        """테마 색상으로 셀 색상 설정"""
        theme = get_theme()
        bg_color = QColor(theme.get_color(bg_color_name))
        text_color = QColor(theme.get_color(text_color_name))
        self.set_cell_color(row, col, bg_color, text_color)
    
    def set_cell_link(self, row: int, col: int, url: str, show_link_style: bool = True):
        """셀에 링크 설정"""
        if 0 <= row < self.rowCount() and 0 <= col < self.columnCount():
            item = self.item(row, col)
            if item:
                # URL 데이터 저장
                item.setData(Qt.UserRole, url)
                
                if show_link_style:
                    # 하이퍼링크 스타일 적용
                    self._apply_link_style(item)
    
    def _apply_link_style(self, item: QTableWidgetItem):
        """하이퍼링크 스타일 적용 (강화된 버전)"""
        theme = get_theme()
        from PySide6.QtGui import QFont
        
        # 링크 색상 설정 (매우 강력한 방법)
        link_color = QColor(theme.get_color("primary"))
        item.setForeground(QBrush(link_color))
        
        # 밑줄 폰트 설정
        font = item.font()
        font.setUnderline(True)
        item.setFont(font)
        
        # 툴팁 설정
        url = item.data(Qt.UserRole)
        if url:
            item.setToolTip(f"클릭하여 링크 열기: {url}")
    
    def set_cell_link_with_icon(self, row: int, col: int, url: str, icon_text: str = "🔗"):
        """아이콘과 함께 링크 설정"""
        if 0 <= row < self.rowCount() and 0 <= col < self.columnCount():
            item = self.item(row, col)
            if item:
                # 기존 텍스트에 아이콘 추가
                current_text = item.text()
                item.setText(f"{current_text} {icon_text}")
                
                # 링크 설정
                self.set_cell_link(row, col, url, show_link_style=True)
    
    def is_cell_link(self, row: int, col: int) -> bool:
        """셀이 링크인지 확인"""
        if 0 <= row < self.rowCount() and 0 <= col < self.columnCount():
            item = self.item(row, col)
            if item:
                return bool(item.data(Qt.UserRole))
        return False
    
    def get_cell_link_url(self, row: int, col: int) -> str:
        """셀의 링크 URL 반환"""
        if 0 <= row < self.rowCount() and 0 <= col < self.columnCount():
            item = self.item(row, col)
            if item:
                return item.data(Qt.UserRole) or ""
        return ""
    
    def clear_cell_link(self, row: int, col: int):
        """셀의 링크 제거"""
        if 0 <= row < self.rowCount() and 0 <= col < self.columnCount():
            item = self.item(row, col)
            if item:
                # URL 데이터 제거
                item.setData(Qt.UserRole, None)
                
                # 스타일 초기화
                theme = get_theme()
                default_color = QColor(theme.get_color("text_primary"))
                item.setForeground(QBrush(default_color))
                item.setData(Qt.UserRole + 2, default_color.name())
                
                font = item.font()
                font.setUnderline(False)
                item.setFont(font)
                
                item.setToolTip("")
    
    def apply_alternating_row_colors(self, enable: bool = True):
        """교대로 나타나는 행 색상 활성화/비활성화 (개별 셀 색상과 충돌 방지)"""
        # 개별 셀에 색상이 적용된 경우 교대 색상이 덮어쓰지 않도록 확실히 비활성화
        # 메시지 상태별 배경색을 우선시하기 위해 기본적으로 비활성화
        self.setAlternatingRowColors(False)
        
        # Qt의 내부 플래그도 확실히 설정
        if hasattr(self, 'model') and self.model():
            # 모델에서도 교대 색상 비활성화
            self.model().setProperty("alternatingRowColors", False)
    
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
    
    def format_datetime(self, datetime_str: str) -> str:
        """날짜/시간 문자열을 YYYY-MM-DD HH:MM 형식으로 포맷팅"""
        if not datetime_str:
            return ""
        
        try:
            # 다양한 형식 처리
            datetime_str = str(datetime_str).strip()
            
            # ISO 형식 처리 (2025-06-27T08:17:29+09:00 또는 2025-06-27 08:17:29+09:00)
            if '+' in datetime_str:
                datetime_str = datetime_str.split('+')[0]  # 타임존 제거
            elif 'Z' in datetime_str:
                datetime_str = datetime_str.replace('Z', '')  # UTC 표시 제거
            
            # T를 공백으로 변경
            datetime_str = datetime_str.replace('T', ' ')
            
            # 초 단위 제거 (HH:MM:SS -> HH:MM)
            if len(datetime_str) >= 16:  # YYYY-MM-DD HH:MM:SS 이상
                return datetime_str[:16]  # YYYY-MM-DD HH:MM만 반환
            
            return datetime_str
            
        except Exception:
            # 파싱 실패 시 원본 반환
            return str(datetime_str)
    
    def format_price(self, price_str: str, currency: str = "원") -> str:
        """가격 문자열을 포맷팅"""
        if not price_str:
            return ""
        
        try:
            price = float(price_str)
            return f"{price:,.0f}{currency}"
        except (ValueError, TypeError):
            return str(price_str)
    
    def format_boolean(self, bool_value: bool, true_text: str = "O", false_text: str = "X") -> str:
        """불린 값을 텍스트로 포맷팅"""
        if bool_value is None:
            return ""
        return true_text if bool_value else false_text
    
    def set_cell_empty_style(self, row: int, col: int, empty_text: str = "✗", color: str = "error"):
        """빈 셀에 스타일 적용 (강화된 버전)"""
        if 0 <= row < self.rowCount() and 0 <= col < self.columnCount():
            item = self.item(row, col)
            if item:
                # 텍스트가 비어있는 경우에만 empty_text로 설정
                if not item.text() or item.text().strip() == "":
                    item.setText(empty_text)
                
                # 색상 설정 (매우 강력한 방법)
                theme = get_theme()
                error_color = QColor(theme.get_color(color))
                
                # 여러 방법으로 색상 적용
                item.setForeground(QBrush(error_color))
                
                # 폰트 색상도 설정
                font = item.font()
                font.setBold(True)  # 굵게 표시
                item.setFont(font)
                
                item.setToolTip("데이터가 없습니다")
    
    def format_cell_value(self, value: Any, field_type: str = "text") -> tuple[str, bool]:
        """셀 값 포맷팅 및 빈 값 여부 반환"""
        is_empty = False
        
        # null, None, 빈 문자열 체크
        if value is None or value == "" or str(value).strip() == "":
            is_empty = True
            return "", is_empty
        
        # 필드 타입별 포맷팅
        if field_type == "datetime":
            return self.format_datetime(str(value)), is_empty
        elif field_type == "price":
            return self.format_price(str(value)), is_empty
        elif field_type == "boolean":
            return self.format_boolean(value), is_empty
        else:
            return str(value), is_empty
    
    def add_row_with_formatting(self, row_data: Dict[str, Any], field_types: Dict[str, str] = None, row_index: Optional[int] = None):
        """포맷팅과 빈 값 처리가 포함된 행 추가"""
        if row_index is None:
            row_index = self.rowCount()
        
        self.insertRow(row_index)
        
        # 체크박스 추가
        checkbox = QCheckBox()
        checkbox.setProperty("row_index", row_index)
        checkbox.stateChanged.connect(self._on_any_checkbox_changed)
        self.setCellWidget(row_index, 0, self._create_checkbox_widget(checkbox))
        
        # 데이터 추가 (포맷팅 포함)
        field_types = field_types or {}
        for col, (key, value) in enumerate(row_data.items(), start=1):
            if col < self.columnCount():
                field_type = field_types.get(key, "text")
                formatted_value, is_empty = self.format_cell_value(value, field_type)
                
                item = QTableWidgetItem(formatted_value)
                self.setItem(row_index, col, item)
                
                # 빈 값인 경우 스타일 적용
                if is_empty:
                    self.set_cell_empty_style(row_index, col)
    
    def set_numeric_columns(self, column_indices: List[int]):
        """숫자 정렬을 사용할 컬럼 인덱스 설정"""
        self.numeric_columns = set(column_indices)
    
    def set_numeric_columns_by_names(self, column_names: List[str]):
        """컬럼명으로 숫자 정렬을 사용할 컬럼 설정"""
        indices = []
        for i in range(self.columnCount()):
            header_item = self.horizontalHeaderItem(i)
            if header_item and header_item.text() in column_names:
                indices.append(i)
        self.set_numeric_columns(indices)
    
    def _create_table_item(self, text: str, column_index: int, raw_value: Any = None) -> QTableWidgetItem:
        """컬럼 타입에 따라 적절한 테이블 아이템 생성 (기본 색상 포함)"""
        if column_index in self.numeric_columns:
            # 숫자 컬럼인 경우 NumericTableWidgetItem 사용
            numeric_value = None
            if raw_value is not None:
                try:
                    numeric_value = float(str(raw_value).replace(',', '').replace('원', ''))
                except (ValueError, TypeError):
                    numeric_value = None
            item = NumericTableWidgetItem(text, numeric_value)
        else:
            # 일반 컬럼인 경우 기본 QTableWidgetItem 사용
            item = QTableWidgetItem(text)
        
        # 기본 텍스트 색상만 설정 (배경색은 설정하지 않음 - 나중에 적용하는 색상이 제대로 보이도록)
        theme = get_theme()
        default_color = QColor(theme.get_color("text_primary"))
        item.setForeground(QBrush(default_color))
        
        # 기본 배경색은 설정하지 않음 - 개별 색상 적용이 제대로 작동하도록
        # default_bg = QColor(theme.get_color("card_bg"))
        # item.setBackground(QBrush(default_bg))
        
        return item
    
    def format_boolean_with_color(self, value: Any, field_name: str = None) -> tuple[str, str, str]:
        """
        불린/빈 값을 O/X로 포맷팅하고 색상 정보 반환
        
        Args:
            value: 원본 값
            field_name: 필드명 (특별한 처리가 필요한 경우)
        
        Returns:
            tuple: (표시_텍스트, 색상_키, 툴팁_텍스트)
        """
        config = TABLE_DISPLAY_CONFIG
        
        # 빈 값 체크
        if value in config["EMPTY_VALUES"]:
            return (
                config["EMPTY_TEXT"],
                config["EMPTY_COLOR"],
                "데이터가 없습니다"
            )
        
        # False 값 체크
        if value in config["FALSE_VALUES"]:
            return (
                config["BOOLEAN_FALSE_TEXT"],
                config["BOOLEAN_FALSE_COLOR"],
                "비활성화/불가능"
            )
        
        # True 값 (나머지 모든 값)
        return (
            config["BOOLEAN_TRUE_TEXT"],
            config["BOOLEAN_TRUE_COLOR"],
            "활성화/가능"
        )
    
    def set_cell_boolean_style(self, row: int, col: int, value: Any, field_name: str = None):
        """
        셀에 불린 값을 O/X로 표시하고 색상 적용 (강화된 버전)
        
        Args:
            row: 행 인덱스
            col: 열 인덱스
            value: 원본 값
            field_name: 필드명 (선택사항)
        """
        if 0 <= row < self.rowCount() and 0 <= col < self.columnCount():
            display_text, color_key, tooltip = self.format_boolean_with_color(value, field_name)
            
            item = self.item(row, col)
            if not item:
                item = QTableWidgetItem()
                self.setItem(row, col, item)
            
            # 텍스트와 색상 설정 (매우 강력한 방법)
            item.setText(display_text)
            theme = get_theme()
            cell_color = QColor(theme.get_color(color_key))
            item.setForeground(QBrush(cell_color))
            
            # 폰트 설정
            font = item.font()
            font.setBold(True)  # 굵게 표시
            item.setFont(font)
            
            item.setToolTip(tooltip)
    
    def create_boolean_table_item(self, value: Any, field_name: str = None) -> QTableWidgetItem:
        """
        불린 값을 위한 테이블 아이템 생성 (색상 포함, 강화된 버전)
        
        Args:
            value: 원본 값
            field_name: 필드명 (선택사항)
            
        Returns:
            QTableWidgetItem: 색상이 적용된 테이블 아이템
        """
        display_text, color_key, tooltip = self.format_boolean_with_color(value, field_name)
        
        item = QTableWidgetItem(display_text)
        theme = get_theme()
        cell_color = QColor(theme.get_color(color_key))
        item.setForeground(QBrush(cell_color))
        
        # 폰트 설정
        font = item.font()
        font.setBold(True)  # 굵게 표시
        item.setFont(font)
        
        item.setToolTip(tooltip)
        
        return item
    
    def adjust_column_widths(self):
        """컬럼 너비를 수동으로 조정 (정렬 화살표 고려)"""
        from PySide6.QtCore import QTimer
        QTimer.singleShot(10, self._adjust_column_widths_for_sort_indicator)
    
    def _on_any_checkbox_changed(self, state):
        """개별 체크박스 상태 변경 처리"""
        if not self._is_bulk_update:
            # 벌크 업데이트가 아닌 경우에만 시그널 발생
            self._emit_selection_changed()
    
    def _adjust_column_widths_for_sort_indicator(self):
        """정렬 화살표를 위한 컬럼 너비 조정"""
        header = self.horizontalHeader()
        
        for i in range(self.columnCount()):
            # 선택 컬럼(0)과 고정 크기 컬럼은 제외
            if i == 0:
                continue
                
            # ResizeToContents 모드인 컬럼만 조정
            if header.sectionResizeMode(i) == QHeaderView.ResizeToContents:
                current_width = header.sectionSize(i)
                
                # 정렬 화살표를 위한 여유 공간 추가 (25px)
                # 헤더 텍스트가 짧은 경우 최소 너비도 보장
                min_width = 80  # 최소 너비
                arrow_padding = 25  # 정렬 화살표 여유 공간
                new_width = max(current_width + arrow_padding, min_width)
                
                # Interactive 모드로 변경하고 새 너비 설정
                header.setSectionResizeMode(i, QHeaderView.Interactive)
                header.resizeSection(i, new_width) 