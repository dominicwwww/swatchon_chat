"""
FBO 출고 요청 테이블 컴포넌트
"""
from typing import List, Dict, Any
from PySide6.QtWidgets import (
    QTableWidget, QTableWidgetItem, QHeaderView, QWidget, QHBoxLayout,
    QCheckBox, QLabel, QVBoxLayout, QComboBox, QPushButton, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPixmap, QImage, QBrush
from datetime import datetime
from functools import partial
import requests

from ui.theme import get_theme
from ui.components.log_widget import LOG_INFO, LOG_WARNING, LOG_ERROR, LOG_DEBUG
from ui.components.table import BaseTable
from core.schemas import PurchaseProduct
from core.constants import (
    DELIVERY_METHODS, LOGISTICS_COMPANIES, TABLE_COLUMN_NAMES, API_FIELDS, 
    MESSAGE_STATUS_LABELS, TABLE_DISPLAY_CONFIG, apply_message_status_color
)
from core.types import ShipmentStatus

class ShipmentRequestTable(BaseTable):
    """FBO 출고 요청 테이블 컴포넌트"""
    
    # 시그널 정의
    selection_changed = Signal(list)  # 선택된 항목 변경 시그널
    
    def __init__(self, parent=None, log_function=None):
        super().__init__(parent, log_function=log_function)
        self.load_photo = False  # 사진 로드 여부 (기본값: 비활성화)
        
        # 컬럼 헤더 정의
        self.column_headers = [
            "",  # 체크박스
            TABLE_COLUMN_NAMES[API_FIELDS["IMAGE_URL"]],   # 1
            TABLE_COLUMN_NAMES[API_FIELDS["ID"]],          # 2
            TABLE_COLUMN_NAMES[API_FIELDS["STORE_NAME"]],  # 3
            TABLE_COLUMN_NAMES[API_FIELDS["STORE_DDM_ADDRESS"]], # 4
            TABLE_COLUMN_NAMES[API_FIELDS["QUALITY_NAME"]],      # 5
            TABLE_COLUMN_NAMES[API_FIELDS["SWATCH_PICKUPABLE"]], # 6
            TABLE_COLUMN_NAMES[API_FIELDS["SWATCH_STORAGE"]],    # 7
            TABLE_COLUMN_NAMES[API_FIELDS["COLOR_NUMBER"]],      # 8
            TABLE_COLUMN_NAMES[API_FIELDS["COLOR_CODE"]],        # 9
            TABLE_COLUMN_NAMES[API_FIELDS["QUANTITY"]],          # 10
            TABLE_COLUMN_NAMES[API_FIELDS["PURCHASE_CODE"]],     # 11
            TABLE_COLUMN_NAMES[API_FIELDS["ORDER_CODE"]],        # 12
            TABLE_COLUMN_NAMES[API_FIELDS["PICKUP_AT"]],         # 13
            TABLE_COLUMN_NAMES[API_FIELDS["LAST_PICKUP_AT"]],    # 14
            TABLE_COLUMN_NAMES[API_FIELDS["DELIVERY_METHOD"]],   # 15
            TABLE_COLUMN_NAMES[API_FIELDS["LOGISTICS_COMPANY"]], # 16
            TABLE_COLUMN_NAMES[API_FIELDS["MESSAGE_STATUS"]],    # 17
            TABLE_COLUMN_NAMES["processed_at"],                  # 18
            TABLE_COLUMN_NAMES[API_FIELDS["ADDITIONAL_INFO"]]    # 19
        ]
        
        # 추가 UI 요소들을 BaseTable의 상단 레이아웃에 추가
        self._add_custom_ui_elements()
        
        # 컬럼 설정 (mixed 모드로 반응형 지원)
        self.setup_columns(self.column_headers, resize_mode="mixed")
        
        # 숫자 정렬이 필요한 컬럼들 설정
        numeric_column_names = [TABLE_COLUMN_NAMES[API_FIELDS["ID"]], TABLE_COLUMN_NAMES[API_FIELDS["QUANTITY"]]]
        self.set_numeric_columns_by_names(numeric_column_names)
        
        # 교대로 나타나는 행 색상 비활성화 (메시지 상태별 배경색 우선시)
        self.apply_alternating_row_colors(False)
        
        # 추가 컬럼 너비 조정 (선택적)
        header = self.horizontalHeader()
        # 이미지 컬럼을 좀 더 좁게
        if len(self.column_headers) > 1:
            header.resizeSection(1, 60)  # 이미지 컬럼
        # ID 컬럼 너비는 BaseTable의 mixed 모드에서 이미 80으로 설정됨
        
    def _add_custom_ui_elements(self):
        """BaseTable의 상단 레이아웃에 출고요청 테이블 전용 UI 요소 추가"""
        # 사진 로드 체크박스를 맨 앞에 추가
        self.photo_checkbox = QCheckBox("사진 로드")
        self.photo_checkbox.setChecked(False)  # 초기값: 비활성화
        self.photo_checkbox.stateChanged.connect(self._on_photo_checkbox_changed)
        # BaseTable의 top_layout 맨 앞에 삽입
        self.top_layout.insertWidget(0, self.photo_checkbox)
        
        # 출고일 필터 드롭다운을 선택 라벨 뒤에 추가
        self.pickup_date_filter = QComboBox()
        self.pickup_date_filter.addItem("전체", "all")
        self.pickup_date_filter.setMinimumWidth(65)  # 최소 너비 설정
        self.pickup_date_filter.currentIndexChanged.connect(self._on_pickup_date_filter_changed)
        
        # 라벨과 콤보박스를 stretch 앞에 추가
        pickup_label = QLabel("출고일:")
        # stretch 위젯을 찾아서 그 앞에 삽입
        stretch_index = -1
        for i in range(self.top_layout.count()):
            item = self.top_layout.itemAt(i)
            if item.spacerItem():  # stretch는 spacer item
                stretch_index = i
                break
        
        if stretch_index >= 0:
            self.top_layout.insertWidget(stretch_index, pickup_label)
            self.top_layout.insertWidget(stretch_index + 1, self.pickup_date_filter)
        else:
            # stretch를 찾지 못한 경우 끝에 추가
            self.top_layout.addWidget(pickup_label)
            self.top_layout.addWidget(self.pickup_date_filter)
        
    def update_data(self, data: List[PurchaseProduct]):
        """테이블 데이터 업데이트"""
        self.load_photo = self.photo_checkbox.isChecked()
        try:
            # 입력 데이터 검증
            if not data:
                self.clear_table()
                return
                
            # 데이터가 올바른 타입인지 확인
            if not isinstance(data, list):
                error_msg = f"잘못된 데이터 타입: {type(data)}"
                if self.log_function:
                    self.log_function(error_msg, "ERROR")
                else:
                    print(error_msg)
                return
            
            self._current_data = data
            
            # 출고일 필터 드롭다운 값 세팅
            prev_value = self.pickup_date_filter.currentData() if self.pickup_date_filter.count() > 0 else "all"
            pickup_dates = sorted({item.pickup_at.strftime('%Y-%m-%d') if hasattr(item.pickup_at, 'strftime') else str(item.pickup_at) for item in data})
            self.pickup_date_filter.blockSignals(True)
            self.pickup_date_filter.clear()
            self.pickup_date_filter.addItem("전체", "all")
            for d in pickup_dates:
                label = d[5:] if len(d) >= 7 else d
                self.pickup_date_filter.addItem(label, d)
            # 기존 선택값 복원
            idx = self.pickup_date_filter.findData(prev_value)
            if idx != -1:
                self.pickup_date_filter.setCurrentIndex(idx)
            self.pickup_date_filter.blockSignals(False)
            
            # 필터 적용
            filter_value = self.pickup_date_filter.currentData()
            if not filter_value or filter_value == "all":
                filtered = data
            else:
                filtered = [item for item in data if (item.pickup_at.strftime('%Y-%m-%d') if hasattr(item.pickup_at, 'strftime') else str(item.pickup_at)) == filter_value]
            
            # 테이블 초기화
            self.clear_table()
            
            if not filtered:
                return
                
            # 데이터 추가
            for item in filtered:
                try:
                    self._add_row(item)
                except Exception as row_error:
                    if self.log_function:
                        self.log_function(f"행 처리 중 오류: {str(row_error)}", "WARNING")
                    else:
                        print(f"행 처리 중 오류: {str(row_error)}")
                    continue
                    
        except Exception as e:
            error_msg = f"테이블 업데이트 중 오류: {str(e)}"
            if self.log_function:
                self.log_function(error_msg, "ERROR")
            else:
                print(error_msg)
    
    def _add_row(self, item: PurchaseProduct):
        """행 추가 (BaseTable의 기능 활용)"""
        row_index = self.rowCount()
        self.insertRow(row_index)
        
        # 체크박스 추가
        checkbox = QCheckBox()
        checkbox.setProperty("row_index", row_index)
        checkbox.stateChanged.connect(self._on_any_checkbox_changed)
        self.setCellWidget(row_index, 0, self._create_checkbox_widget(checkbox))
        
        # 1. 이미지 썸네일 (사진 로드 체크박스 체크 시만)
        image_url = getattr(item, 'image_url', None) or getattr(item, 'print_url', None)
        
        if self.load_photo and image_url:
            # 이미지가 있는 경우 QLabel로 표시
            label = QLabel()
            label.setAlignment(Qt.AlignCenter)
            try:
                headers = {"User-Agent": "Mozilla/5.0"}
                response = requests.get(image_url, headers=headers, timeout=3)
                if response.status_code == 200:
                    image = QImage.fromData(response.content)
                    if not image.isNull():
                        pixmap = QPixmap.fromImage(image).scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        label.setPixmap(pixmap)
            except Exception:
                pass
            self.setCellWidget(row_index, 1, label)
            
            # 이미지 URL이 있으면 더미 아이템 생성하고 하이퍼링크 설정
            image_item = self._create_table_item("", 1, image_url)
            self.setItem(row_index, 1, image_item)
            self.set_cell_link(row_index, 1, image_url, show_link_style=False)  # 이미지는 스타일 적용 안 함
        else:
            # 이미지가 없거나 로드하지 않는 경우 빈 아이템
            image_item = self._create_table_item("", 1, None)
            self.setItem(row_index, 1, image_item)
        
        # 2. ID (숫자 정렬 지원)
        item_id = getattr(item, 'id', 0)
        id_item = self._create_table_item(str(item_id), 2, item_id)
        self.setItem(row_index, 2, id_item)

        # 3. store_name (하이퍼링크)
        store_name = getattr(item, 'store_name', '')
        store_name_item = self._create_table_item(store_name, 3, store_name)
        self.setItem(row_index, 3, store_name_item)
        store_url = getattr(item, 'store_url', None)
        if store_url:
            self.set_cell_link(row_index, 3, store_url, show_link_style=True)
        elif not store_name:
                self.set_cell_empty_style(row_index, 3)
        
        # 4. 동대문주소
        store_ddm_address = getattr(item, 'store_ddm_address', '')
        ddm_item = self._create_table_item(store_ddm_address, 4, store_ddm_address)
        self.setItem(row_index, 4, ddm_item)
        if not store_ddm_address:
            self.set_cell_empty_style(row_index, 4)
        
        # 5. 퀄리티 | 품질코드 (하이퍼링크)
        quality_code = getattr(item, 'quality_code', None)
        quality_name = getattr(item, 'quality_name', '')
        quality_display = quality_name
        if quality_code:
            quality_display += f" | {quality_code}"
        quality_item = self._create_table_item(quality_display, 5, quality_display)
        self.setItem(row_index, 5, quality_item)
        quality_url = getattr(item, 'quality_url', None)
        if quality_url:
            self.set_cell_link(row_index, 5, quality_url, show_link_style=True)
        elif not quality_display:
            self.set_cell_empty_style(row_index, 5)
        
        # 6. 스와치픽업 (O/X, 컬러) - BaseTable의 공통 메서드 사용
        swatch_pickupable = getattr(item, 'swatch_pickupable', None)
        swatch_item = self.create_boolean_table_item(swatch_pickupable, 'swatch_pickupable')
        self.setItem(row_index, 6, swatch_item)
        
        # 7. 스와치보관 - BaseTable의 공통 빈 값 처리 사용
        swatch_storage = getattr(item, 'swatch_storage', None)
        swatch_storage_item = self._create_table_item(str(swatch_storage) if swatch_storage else "", 7, swatch_storage)
        self.setItem(row_index, 7, swatch_storage_item)
        if not swatch_storage:
            self.set_cell_empty_style(row_index, 7)
        
        # 8. 컬러번호
        color_number = getattr(item, 'color_number', 0)
        color_number_item = self._create_table_item(str(color_number), 8, color_number)
        self.setItem(row_index, 8, color_number_item)
        
        # 9. 컬러코드
        color_code = getattr(item, 'color_code', None) or ""
        color_code_item = self._create_table_item(str(color_code), 9, color_code)
        self.setItem(row_index, 9, color_code_item)
        if not color_code:
            self.set_cell_empty_style(row_index, 9)
        
        # 10. 수량 (숫자 정렬 지원)
        try:
            quantity = getattr(item, 'quantity', 0)
            qty = int(quantity) if quantity is not None else 0
        except (ValueError, TypeError):
            qty = 0
        quantity_item = self._create_table_item(str(qty), 10, qty)
        self.setItem(row_index, 10, quantity_item)
        
        # 11. 발주번호 (하이퍼링크)
        purchase_code = getattr(item, 'purchase_code', '')
        purchase_code_item = self._create_table_item(purchase_code, 11, purchase_code)
        self.setItem(row_index, 11, purchase_code_item)
        purchase_url = getattr(item, 'purchase_url', None)
        if purchase_url:
            self.set_cell_link(row_index, 11, purchase_url, show_link_style=True)
        elif not purchase_code:
            self.set_cell_empty_style(row_index, 11)
        
        # 12. 주문코드 (하이퍼링크)
        order_code = getattr(item, 'order_code', None) or ""
        order_code_item = self._create_table_item(order_code, 12, order_code)
        self.setItem(row_index, 12, order_code_item)
        order_url = getattr(item, 'order_url', None)
        if order_url:
            self.set_cell_link(row_index, 12, order_url, show_link_style=True)
        elif not order_code:
            self.set_cell_empty_style(row_index, 12)
        
        # 13. 출고일 (날짜 포맷팅)
        pickup_at = getattr(item, 'pickup_at', None)
        pickup_date = self.format_datetime(str(pickup_at)) if pickup_at else ""
        pickup_item = self._create_table_item(pickup_date, 13, pickup_at)
        self.setItem(row_index, 13, pickup_item)
        if not pickup_date:
            self.set_cell_empty_style(row_index, 13)
        
        # 14. 최종출고일 (날짜 포맷팅)
        last_pickup_at = getattr(item, 'last_pickup_at', None)
        last_pickup_date = self.format_datetime(str(last_pickup_at)) if last_pickup_at else ""
        last_pickup_item = self._create_table_item(last_pickup_date, 14, last_pickup_at)
        self.setItem(row_index, 14, last_pickup_item)
        if not last_pickup_date:
            self.set_cell_empty_style(row_index, 14)
        
        # 15. 배송방법
        delivery_method_value = item.delivery_method or ""
        delivery_method = DELIVERY_METHODS.get(delivery_method_value, delivery_method_value) if delivery_method_value else ""
        delivery_item = self._create_table_item(delivery_method, 15, delivery_method_value)
        self.setItem(row_index, 15, delivery_item)
        if not delivery_method:
            self.set_cell_empty_style(row_index, 15)
        
        # 16. 택배사
        logistics_company_value = item.logistics_company or ""
        logistics_company = LOGISTICS_COMPANIES.get(logistics_company_value, logistics_company_value) if logistics_company_value else ""
        logistics_item = self._create_table_item(logistics_company, 16, logistics_company_value)
        self.setItem(row_index, 16, logistics_item)
        if not logistics_company:
            self.set_cell_empty_style(row_index, 16)
        
        # 17. 메시지상태 (색상 포함)
        message_status_text = getattr(item, 'message_status', ShipmentStatus.PENDING.value) if hasattr(item, 'message_status') else ShipmentStatus.PENDING.value
        # 한글 매핑 적용
        message_status_display = MESSAGE_STATUS_LABELS.get(message_status_text, message_status_text)
        message_status_item = self._create_table_item(message_status_display, 17, message_status_text)
        self.setItem(row_index, 17, message_status_item)
        
        # 상태별 색상 적용
        apply_message_status_color(self, row_index, 17, message_status_text)
        
        # 18. 처리시각 (날짜 포맷팅)
        processed_at = getattr(item, 'processed_at', None)
        processed_at_str = self.format_datetime(str(processed_at)) if processed_at else ""
        processed_item = self._create_table_item(processed_at_str, 18, processed_at)
        self.setItem(row_index, 18, processed_item)
        if not processed_at_str:
            self.set_cell_empty_style(row_index, 18)
        
        # 19. 메모 (additional_info)
        additional_info = getattr(item, 'additional_info', "") or ""
        additional_item = self._create_table_item(additional_info, 19, additional_info)
        self.setItem(row_index, 19, additional_item)
        if not additional_info:
            self.set_cell_empty_style(row_index, 19)
    
    def _on_photo_checkbox_changed(self, state):
        """사진 로드 체크박스 상태 변경"""
        self.load_photo = (state == Qt.Checked)
        # 현재 데이터로 테이블 업데이트
        if hasattr(self, '_current_data'):
            self.update_data(self._current_data)

    def _on_pickup_date_filter_changed(self, idx):
        """출고일 필터 변경"""
        if hasattr(self, '_current_data'):
            self.update_data(self._current_data)

    def update_status(self, item_ids: List[int], message_status: str, processed_at: str = None):
        """특정 항목들의 메시지 상태와 처리시각만 업데이트"""
        try:
            if self.rowCount() == 0 or not self.isVisible():
                return
                
            for row in range(self.rowCount()):
                id_item = self.item(row, 2)  # ID 컬럼
                if id_item is None:
                    continue
                
                try:
                    row_id = int(id_item.text())
                    if row_id in item_ids:
                        # 메시지 상태 업데이트 (컬럼 17)
                        message_status_display = MESSAGE_STATUS_LABELS.get(message_status, message_status)
                        message_status_item = self._create_table_item(message_status_display, 17, message_status)
                        
                        # 먼저 아이템을 설정한 후 색상 적용
                        self.setItem(row, 17, message_status_item)
                        
                        # 상태별 색상 적용
                        apply_message_status_color(self, row, 17, message_status)
                        
                        # 처리시각 업데이트 (컬럼 18)
                        if processed_at:
                            processed_at_formatted = self.format_datetime(processed_at)
                            processed_item = self._create_table_item(processed_at_formatted, 18, processed_at)
                            self.setItem(row, 18, processed_item)
                            
                except ValueError:
                    continue
                    
        except Exception as e:
            error_msg = f"상태 업데이트 중 오류: {str(e)}"
            if self.log_function:
                self.log_function(error_msg, "ERROR")
            else:
                print(error_msg)

    def _on_any_checkbox_changed(self, state: int):
        """체크박스 상태 변경 이벤트"""
        # 개별 체크박스 변경 시에만 시그널 발생
        if not getattr(self, '_is_bulk_update', False):
            self._emit_selection_changed()
    
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
                        # id 필드 추가 (컬럼 2에 있는 ID 값 사용)
                        id_item = self.item(row, 2)
                        if id_item:
                            item_data['id'] = int(id_item.text())
                        selected_items.append(item_data)
                    except (ValueError, AttributeError) as e:
                        print(f"행 {row} 데이터 수집 중 오류: {e}")
                        continue
        # 선택된 항목 수 업데이트
        self._update_selection_label()
        # 시그널 발생 (정렬 순서 반영된 selected_items)
        self.selection_changed.emit(selected_items)
    
    def _create_checkbox_widget(self, checkbox):
        """체크박스를 위한 위젯 생성"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignCenter)
        layout.addWidget(checkbox)
        return widget

    def mousePressEvent(self, event):
        # 하이퍼링크 셀 클릭 시 브라우저로 열기
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtCore import QUrl
        index = self.indexAt(event.pos())
        if index.isValid():
            col = index.column()
            item = self.item(index.row(), col)
            if item and item.data(Qt.UserRole):
                QDesktopServices.openUrl(QUrl(item.data(Qt.UserRole)))
        super().mousePressEvent(event) 