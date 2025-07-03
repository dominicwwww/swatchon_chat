"""
FBO 발주 확인 테이블 컴포넌트 - 평면 구조 지원
"""
from typing import List, Dict, Any, Optional
from PySide6.QtWidgets import (
    QCheckBox, QLabel, QHBoxLayout, QWidget, QTableWidgetItem, QPushButton, QHeaderView
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QIcon
from ui.components.table import BaseTable
from ui.theme import get_theme
from core.constants import TABLE_COLUMN_NAMES, MESSAGE_STATUS_LABELS, apply_message_status_color
from core.types import ShipmentStatus

class FboPoTable(BaseTable):
    selection_changed = Signal(list)  # 선택된 항목 변경 시그널
    product_show_requested = Signal(str)  # 프로덕트 표시 요청 시그널 (JSON에서 로드)

    def __init__(self, parent=None, log_function=None):
        super().__init__(parent, log_function=log_function)
        
        # JSON 필드명 순서 (실제 데이터 순서)
        self.field_names = [
            "id", "store_name", "quality_code", "quality_name", "swatch_pickupable", 
            "swatch_storage", "color_number", "color_code", "quantity", "order_code", 
            "purchase_code", "last_pickup_at", "status", "message_status", "processed_at", 
            "price", "unit_price", "unit_price_origin", "additional_info", "created_at", "updated_at"
        ]
        
        # 컬럼 헤더 (한글명)
        self.column_headers = ["선택"] + [TABLE_COLUMN_NAMES.get(field, field) for field in self.field_names]
        
        # 필드 타입 정의 (포맷팅용)
        self.field_types = {
            "id": "text",
            "store_name": "text", 
            "quality_code": "text",
            "quality_name": "text",
            "swatch_pickupable": "boolean",
            "swatch_storage": "text",
            "color_number": "text",
            "color_code": "text",
            "quantity": "text",
            "order_code": "text",
            "purchase_code": "text",
            "last_pickup_at": "datetime",
            "status": "text",
            "message_status": "text",
            "processed_at": "datetime",
            "price": "price",
            "unit_price": "price", 
            "unit_price_origin": "price",
            "additional_info": "text",
            "created_at": "datetime",
            "updated_at": "datetime"
        }
        
        # 혼합 모드로 컬럼 설정 (선택 컬럼은 고정, 나머지는 내용에 맞게)
        self.setup_columns(self.column_headers, resize_mode="mixed")
        
        # 숫자 정렬이 필요한 컬럼들 설정
        numeric_column_names = ["수량(yd)", "총가격", "단가", "원본단가"]
        self.set_numeric_columns_by_names(numeric_column_names)
        
        self.setSelectionBehavior(BaseTable.SelectRows)
        self.setSelectionMode(BaseTable.SingleSelection)
        self.setEditTriggers(BaseTable.NoEditTriggers)
        self.setSortingEnabled(True)  # 정렬 기능 활성화
        self.apply_alternating_row_colors(False)  # 메시지 상태별 배경색 우선시
        
        # 추가 컬럼 너비 조정 (선택적)
        header = self.horizontalHeader()
        # ID 컬럼을 좀 더 좁게
        if len(self.column_headers) > 1:
            header.resizeSection(1, 80)  # ID 컬럼

    def update_data(self, data: List[Dict[str, Any]]):
        """테이블 데이터 업데이트"""
        self.clear_table()
        for row_data in data:
            self._add_row(row_data)
        self._update_selection_label()

    def _add_row(self, row_data: Dict[str, Any]):
        """행 추가 (개선된 포맷팅 포함)"""
        row_index = self.rowCount()
        self.insertRow(row_index)
        
        # 체크박스 추가
        checkbox = QCheckBox()
        checkbox.setProperty("row_index", row_index)
        checkbox.setProperty("row_type", "purchase")
        checkbox.stateChanged.connect(self._on_any_checkbox_changed)
        self.setCellWidget(row_index, 0, self._create_checkbox_widget(checkbox))
        
        # 데이터 컬럼 추가 (포맷팅 포함)
        for col, field_name in enumerate(self.field_names, start=1):
            raw_value = row_data.get(field_name)
            field_type = self.field_types.get(field_name, "text")
            
            # BaseTable의 공통 포맷팅 사용
            formatted_value, is_empty = self.format_cell_value(raw_value, field_type)
            
            # 메시지 상태는 별도 처리 (빈 값이 아닌 경우만)
            if field_name == "message_status" and not is_empty:
                formatted_value = MESSAGE_STATUS_LABELS.get(str(raw_value), str(raw_value))
                
                # 적절한 테이블 아이템 생성
                item = self._create_table_item(formatted_value, col, raw_value)
                self.setItem(row_index, col, item)
                
                # 상태별 배경색 적용
                apply_message_status_color(self, row_index, col, str(raw_value))
                
                continue  # 이미 아이템을 설정했으므로 다음 필드로
            
            # 스와치픽업 필드는 공통 불린 처리 사용
            if field_name == "swatch_pickupable":
                # BaseTable의 공통 불린 아이템 생성 메서드 사용
                item = self.create_boolean_table_item(raw_value, field_name)
                self.setItem(row_index, col, item)
            else:
                # 적절한 테이블 아이템 생성 (숫자 컬럼 고려)
                item = self._create_table_item(formatted_value, col, raw_value)
                self.setItem(row_index, col, item)
                
                # 빈 값인 경우 빨간색 X 표시
                if is_empty:
                    self.set_cell_empty_style(row_index, col)
            
            # 하이퍼링크 설정
            self._set_hyperlink_if_needed(row_index, col, field_name, row_data)

    def _set_hyperlink_if_needed(self, row: int, col: int, field_name: str, row_data: Dict[str, Any]):
        """필요한 경우 하이퍼링크 설정"""
        url = None
        
        if field_name == "purchase_code" and row_data.get("purchase_url"):
            url = row_data["purchase_url"]
        elif field_name == "order_code" and row_data.get("order_url"):
            url = row_data["order_url"]
        elif field_name == "store_name" and row_data.get("store_url"):
            url = row_data["store_url"]
        elif field_name == "quality_name" and row_data.get("quality_url"):
            url = row_data["quality_url"]
        
        if url:
            # 하이퍼링크 스타일과 함께 설정 (밑줄, 색상, 툴팁)
            self.set_cell_link(row, col, url, show_link_style=True)

    def _create_checkbox_widget(self, checkbox):
        """체크박스 위젯 생성"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignCenter)
        layout.addWidget(checkbox)
        return widget

    def _on_any_checkbox_changed(self, state: int):
        """체크박스 상태 변경 처리"""
        if not getattr(self, '_is_bulk_update', False):
            self._emit_selection_changed()

    def _emit_selection_changed(self, is_bulk_update: bool = False):
        """선택 변경 시그널 발생"""
        selected_items = []
        for row in range(self.rowCount()):
            checkbox_widget = self.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox and checkbox.isChecked():
                    item_data = {}
                    for col in range(1, self.columnCount()):
                        # 영문 필드명을 사용 (col-1 인덱스로 field_names 접근)
                        field_name = self.field_names[col-1] if col-1 < len(self.field_names) else str(col)
                        cell_item = self.item(row, col)
                        item_data[field_name] = cell_item.text() if cell_item else ""
                    selected_items.append(item_data)
        
        self._update_selection_label()
        self.selection_changed.emit(selected_items)

    def _update_selection_label(self):
        """선택된 항목 수 라벨 업데이트"""
        selected_count = 0
        for row in range(self.rowCount()):
            checkbox_widget = self.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox and checkbox.isChecked():
                    selected_count += 1
        self.selection_label.setText(f"선택된 항목: {selected_count:,}개")

    def get_selected_rows(self) -> List[Dict[str, Any]]:
        """선택된 행 데이터 반환"""
        selected_items = []
        for row in range(self.rowCount()):
            checkbox_widget = self.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox and checkbox.isChecked():
                    row_data = {}
                    for col in range(1, self.columnCount()):
                        # 영문 필드명을 사용 (col-1 인덱스로 field_names 접근)
                        field_name = self.field_names[col-1] if col-1 < len(self.field_names) else str(col)
                        cell_item = self.item(row, col)
                        row_data[field_name] = cell_item.text() if cell_item else ""
                    selected_items.append(row_data)
        return selected_items

    def select_all(self):
        """모든 항목 선택"""
        self._is_bulk_update = True
        for row in range(self.rowCount()):
            checkbox_widget = self.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox:
                    checkbox.setChecked(True)
        self._emit_selection_changed(is_bulk_update=True)
        self._is_bulk_update = False

    def clear_selection(self):
        """모든 선택 해제"""
        self._is_bulk_update = True
        for row in range(self.rowCount()):
            checkbox_widget = self.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox:
                    checkbox.setChecked(False)
        self._emit_selection_changed(is_bulk_update=True)
        self._is_bulk_update = False

    def update_item_status(self, item_id: str, status: str, processed_at: str = None):
        """특정 항목의 상태 업데이트"""
        for row in range(self.rowCount()):
            # ID 컬럼 (인덱스 1)에서 해당 ID 찾기
            id_item = self.item(row, 1)
            if id_item and id_item.text() == item_id:
                # field_names에서 각 필드의 컬럼 인덱스 계산 (체크박스 컬럼 고려해서 +1)
                # message_status = 인덱스 13 → 컬럼 14 (체크박스 때문에 +1)
                # processed_at = 인덱스 14 → 컬럼 15 (체크박스 때문에 +1)
                
                try:
                    message_status_col = self.field_names.index("message_status") + 1
                    processed_at_col = self.field_names.index("processed_at") + 1
                    
                    # 메시지 상태 컬럼 업데이트 - 새로운 아이템 생성
                    korean_status = MESSAGE_STATUS_LABELS.get(status, status)
                    status_item = self._create_table_item(korean_status, message_status_col, status)
                    self.setItem(row, message_status_col, status_item)
                    
                    # 상태별 배경색 적용
                    apply_message_status_color(self, row, message_status_col, status)
                    
                    # 처리시각 컬럼 업데이트 (제공된 경우)
                    if processed_at:
                        # 날짜/시간 포맷팅
                        formatted_time = self.format_datetime(processed_at) if hasattr(self, 'format_datetime') else processed_at
                        processed_item = self._create_table_item(formatted_time, processed_at_col, processed_at)
                        self.setItem(row, processed_at_col, processed_item)
                    
                except ValueError as e:
                    # 필드명을 찾을 수 없는 경우 기존 방식 사용
                    korean_status = MESSAGE_STATUS_LABELS.get(status, status)
                    status_item = self._create_table_item(korean_status, 14, status)
                    self.setItem(row, 14, status_item)
                    apply_message_status_color(self, row, 14, status)
                break

    def get_all_data(self):
        """테이블의 모든 데이터 반환"""
        all_data = []
        for row in range(self.rowCount()):
            row_data = {}
            for col in range(1, self.columnCount()):
                field_name = self.field_names[col-1] if col-1 < len(self.field_names) else str(col)
                cell_item = self.item(row, col)
                row_data[field_name] = cell_item.text() if cell_item else ""
            all_data.append(row_data)
        return all_data 