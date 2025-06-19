"""
FBO 발주 확인 테이블 컴포넌트 - 계층형 구조 지원
"""
from typing import List, Dict, Any, Optional
from PySide6.QtWidgets import (
    QCheckBox, QLabel, QHBoxLayout, QWidget, QTableWidgetItem, QPushButton
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QIcon
from ui.components.table import BaseTable

class HierarchicalTableItem(QTableWidgetItem):
    """계층형 테이블 아이템"""
    def __init__(self, text: str, level: int = 0, item_type: str = "purchase", expandable: bool = False):
        super().__init__(text)
        self.level = level
        self.item_type = item_type  # "purchase" 또는 "product"
        self.expandable = expandable
        self.expanded = False
        self.parent_purchase_code = None
        self.product_data = None
        
        # 스타일 적용
        self._apply_style()
    
    def _apply_style(self):
        """아이템 스타일 적용"""
        font = QFont()
        
        if self.item_type == "purchase":
            # 발주 행 스타일
            font.setBold(True)
            self.setFont(font)
            if self.expandable:
                # 확장 가능한 경우 배경색 변경
                self.setBackground(QColor(240, 248, 255))  # 연한 파란색
        else:
            # 프로덕트 행 스타일
            font.setBold(False)
            self.setFont(font)
            self.setBackground(QColor(248, 250, 252))  # 연한 회색

class FboPoTable(BaseTable):
    selection_changed = Signal(list)  # 선택된 항목 변경 시그널
    product_show_requested = Signal(str)  # 프로덕트 표시 요청 시그널 (JSON에서 로드)

    def __init__(self, parent=None, log_function=None):
        super().__init__(parent, log_function=log_function)
        
        # 기본 발주 테이블 컬럼
        self.purchase_columns = [
            "선택", "발주번호", "거래타입", "생성시각", "주문", "판매자", 
            "발주담당자", "발주수량", "공급가액", "단가변경여부", "지연허용여부", 
            "상태", "정산상태", "내부메모"
        ]
        
        # 프로덕트 확장 시 추가 컬럼 (필요한 것만 선택)
        self.product_columns = [
            "", "제품ID", "판매방식", "퀄리티", "컬러", "프로덕트코드", 
            "수량", "금액", "단가", "상태", "", "", "", ""
        ]
        
        self.setup_columns(self.purchase_columns)
        self.setSelectionBehavior(BaseTable.SelectRows)
        self.setSelectionMode(BaseTable.SingleSelection)
        self.setEditTriggers(BaseTable.NoEditTriggers)
        self.setSortingEnabled(False)  # 계층 구조에서는 정렬 비활성화
        self._is_bulk_update = False
        
        # 데이터 저장소
        self.hierarchical_data = []  # 계층형 데이터
        self.expanded_purchases = set()  # 확장된 발주번호들
        
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

    def update_data(self, data: List[Dict[str, Any]]):
        """
        데이터 업데이트 - 계층형 구조로 변환
        
        Args:
            data: 발주 목록 데이터
        """
        self.clear_table()
        self.hierarchical_data = []
        
        for purchase_data in data:
            # 발주 행 추가
            purchase_row = {
                "type": "purchase",
                "level": 0,
                "data": purchase_data,
                "is_expandable": True,
                "is_expanded": False,
                "products": []  # 나중에 로드
            }
            self.hierarchical_data.append(purchase_row)
        
        self._refresh_table_display()

    def _refresh_table_display(self):
        """테이블 표시 새로고침"""
        self.clear_table()
        
        for row_data in self.hierarchical_data:
            if row_data["type"] == "purchase":
                self._add_purchase_row(row_data)
                
                # 확장된 상태이고 프로덕트가 있으면 프로덕트 행들도 추가
                purchase_code = row_data["data"].get("발주번호", "")
                if (row_data["is_expanded"] and 
                    purchase_code in self.expanded_purchases and 
                    row_data["products"]):
                    
                    for product_data in row_data["products"]:
                        self._add_product_row(product_data, purchase_code)
        
        self._update_selection_label()

    def _add_purchase_row(self, purchase_row_data: Dict[str, Any]):
        """발주 행 추가"""
        row_index = self.rowCount()
        self.insertRow(row_index)
        
        purchase_data = purchase_row_data["data"]
        
        # 체크박스 추가
        checkbox = QCheckBox()
        checkbox.setProperty("row_index", row_index)
        checkbox.setProperty("row_type", "purchase")
        checkbox.stateChanged.connect(self._on_any_checkbox_changed)
        self.setCellWidget(row_index, 0, self._create_checkbox_widget(checkbox))
        
        # 발주번호에 확장/축소 버튼 추가
        purchase_code = purchase_data.get("발주번호", "")
        expand_widget = self._create_expand_widget(purchase_code, purchase_row_data["is_expanded"])
        self.setCellWidget(row_index, 1, expand_widget)
        
        # 나머지 컬럼 데이터 추가
        data_columns = [
            "거래타입", "생성시각", "주문", "판매자", 
            "발주담당자", "발주수량", "공급가액", "단가변경여부", "지연허용여부", 
            "상태", "정산상태", "내부메모"
        ]
        
        for col, column_key in enumerate(data_columns, start=2):
            if col < self.columnCount():
                value = purchase_data.get(column_key, "")
                item = HierarchicalTableItem(
                    str(value) if value is not None else "", 
                    level=0, 
                    item_type="purchase", 
                    expandable=True
                )
                self.setItem(row_index, col, item)

    def _create_expand_widget(self, purchase_code: str, is_expanded: bool) -> QWidget:
        """확장/축소 위젯 생성"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(2, 0, 2, 0)
        
        # 확장/축소 버튼
        expand_btn = QPushButton("▼" if is_expanded else "▶")
        expand_btn.setFixedSize(20, 20)
        expand_btn.setProperty("purchase_code", purchase_code)
        expand_btn.clicked.connect(self._on_expand_clicked)
        expand_btn.setStyleSheet("""
            QPushButton {
                border: none;
                background: transparent;
                font-weight: bold;
                color: #666;
            }
            QPushButton:hover {
                color: #007bff;
            }
        """)
        
        # 발주번호 라벨
        code_label = QLabel(purchase_code)
        code_label.setStyleSheet("font-weight: bold; color: #007bff;")
        
        layout.addWidget(expand_btn)
        layout.addWidget(code_label)
        layout.addStretch()
        
        return widget

    def _add_product_row(self, product_data: Dict[str, Any], parent_purchase_code: str):
        """프로덕트 행 추가"""
        row_index = self.rowCount()
        self.insertRow(row_index)
        
        # 첫 번째 컬럼은 들여쓰기 표시
        indent_widget = QWidget()
        indent_layout = QHBoxLayout(indent_widget)
        indent_layout.setContentsMargins(30, 0, 0, 0)  # 30px 들여쓰기
        indent_label = QLabel("└")
        indent_label.setStyleSheet("color: #ccc;")
        indent_layout.addWidget(indent_label)
        indent_layout.addStretch()
        self.setCellWidget(row_index, 0, indent_widget)
        
        # 프로덕트 데이터 매핑
        product_display_data = [
            product_data.get("product_id", ""),
            product_data.get("sale_type", ""),
            product_data.get("quality_name", ""),
            f"{product_data.get('color_name', '')} ({product_data.get('color_code', '')})",
            product_data.get("product_code", ""),
            product_data.get("quantity", ""),
            f"{int(product_data.get('total_price', 0)):,}" if product_data.get('total_price', '').isdigit() else product_data.get('total_price', ''),
            f"{int(product_data.get('unit_price', 0)):,}" if product_data.get('unit_price', '').isdigit() else product_data.get('unit_price', ''),
            product_data.get("status", ""),
            "", "", "", ""  # 빈 컬럼들
        ]
        
        for col, value in enumerate(product_display_data, start=1):
            if col < self.columnCount():
                item = HierarchicalTableItem(
                    str(value) if value is not None else "", 
                    level=1, 
                    item_type="product"
                )
                item.parent_purchase_code = parent_purchase_code
                item.product_data = product_data
                self.setItem(row_index, col, item)

    def _on_expand_clicked(self):
        """확장/축소 버튼 클릭 처리"""
        button = self.sender()
        purchase_code = button.property("purchase_code")
        
        if purchase_code in self.expanded_purchases:
            # 축소
            self.expanded_purchases.remove(purchase_code)
            self._update_purchase_expanded_state(purchase_code, False)
        else:
            # 확장 - JSON 데이터에서 프로덕트 로드 요청
            self.expanded_purchases.add(purchase_code)
            self._update_purchase_expanded_state(purchase_code, True)
            self.product_show_requested.emit(purchase_code)

    def _update_purchase_expanded_state(self, purchase_code: str, expanded: bool):
        """발주의 확장 상태 업데이트"""
        for row_data in self.hierarchical_data:
            if (row_data["type"] == "purchase" and 
                row_data["data"].get("발주번호") == purchase_code):
                row_data["is_expanded"] = expanded
                break
        
        self._refresh_table_display()

    def add_products_to_purchase(self, purchase_code: str, products: List[Dict[str, Any]]):
        """발주에 프로덕트 데이터 추가"""
        for row_data in self.hierarchical_data:
            if (row_data["type"] == "purchase" and 
                row_data["data"].get("발주번호") == purchase_code):
                row_data["products"] = products
                break
        
        # 확장된 상태면 테이블 새로고침
        if purchase_code in self.expanded_purchases:
            self._refresh_table_display()

    def _create_checkbox_widget(self, checkbox):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignCenter)
        layout.addWidget(checkbox)
        return widget

    def _on_any_checkbox_changed(self, state: int):
        if not getattr(self, '_is_bulk_update', False):
            self._emit_selection_changed()

    def _emit_selection_changed(self, is_bulk_update: bool = False):
        selected_items = []
        for row in range(self.rowCount()):
            checkbox_widget = self.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox and checkbox.isChecked():
                    # 발주 행만 선택 가능 (프로덕트 행은 제외)
                    row_type = checkbox.property("row_type")
                    if row_type == "purchase":
                        item_data = {}
                        for col in range(1, self.columnCount()):
                            header = self.horizontalHeaderItem(col)
                            key = header.text() if header else str(col)
                            
                            if col == 1:  # 발주번호 컬럼
                                # 위젯에서 발주번호 추출
                                widget = self.cellWidget(row, col)
                                if widget:
                                    label = widget.findChild(QLabel)
                                    if label:
                                        item_data[key] = label.text()
                            else:
                                cell_item = self.item(row, col)
                                item_data[key] = cell_item.text() if cell_item else ""
                        selected_items.append(item_data)
        
        self._update_selection_label()
        self.selection_changed.emit(selected_items)

    def _update_selection_label(self):
        selected_count = 0
        for row in range(self.rowCount()):
            checkbox_widget = self.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox and checkbox.isChecked():
                    row_type = checkbox.property("row_type")
                    if row_type == "purchase":
                        selected_count += 1
        self.selection_label.setText(f"선택된 항목: {selected_count:,}개")

    def get_selected_rows(self) -> List[Dict[str, Any]]:
        selected_items = []
        for row in range(self.rowCount()):
            checkbox_widget = self.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox and checkbox.isChecked():
                    row_type = checkbox.property("row_type")
                    if row_type == "purchase":
                        row_data = {}
                        for col in range(1, self.columnCount()):
                            header = self.horizontalHeaderItem(col)
                            key = header.text() if header else str(col)
                            
                            if col == 1:  # 발주번호 컬럼
                                widget = self.cellWidget(row, col)
                                if widget:
                                    label = widget.findChild(QLabel)
                                    if label:
                                        row_data[key] = label.text()
                            else:
                                cell_item = self.item(row, col)
                                row_data[key] = cell_item.text() if cell_item else ""
                        selected_items.append(row_data)
        return selected_items

    def select_all(self):
        self._is_bulk_update = True
        for row in range(self.rowCount()):
            checkbox_widget = self.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox:
                    row_type = checkbox.property("row_type")
                    if row_type == "purchase":  # 발주 행만 선택
                        checkbox.setChecked(True)
        self._emit_selection_changed(is_bulk_update=True)
        self._is_bulk_update = False

    def clear_selection(self):
        self._is_bulk_update = True
        for row in range(self.rowCount()):
            checkbox_widget = self.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox:
                    checkbox.setChecked(False)
        self._emit_selection_changed(is_bulk_update=True)
        self._is_bulk_update = False 