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
from core.schemas import PurchaseProduct
from core.constants import DELIVERY_METHODS, LOGISTICS_COMPANIES, TABLE_COLUMN_NAMES, API_FIELDS
from core.types import MessageStatus

class ShipmentRequestTable(QTableWidget):
    """FBO 출고 요청 테이블 컴포넌트"""
    
    # 시그널 정의
    selection_changed = Signal(list)  # 선택된 항목 변경 시그널
    
    def __init__(self, parent=None, log_function=None):
        super().__init__(parent)
        self.load_photo = False  # 사진 로드 여부 (기본값: 비활성화)
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
        
        # 사진 로드 체크박스
        self.photo_checkbox = QCheckBox("사진 로드")
        self.photo_checkbox.setChecked(False)  # 초기값: 비활성화
        self.photo_checkbox.stateChanged.connect(self._on_photo_checkbox_changed)
        self.top_layout.addWidget(self.photo_checkbox)

        # 전체 선택/해제 버튼 (왼쪽으로 이동)
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
        
        # 출고일 필터 드롭다운 추가
        self.pickup_date_filter = QComboBox()
        self.pickup_date_filter.addItem("전체", "all")
        self.pickup_date_filter.currentIndexChanged.connect(self._on_pickup_date_filter_changed)
        self.top_layout.addWidget(QLabel("출고일:"))
        self.top_layout.addWidget(self.pickup_date_filter)
        
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
        
        # 이미지, store_name(링크), 나머지 주요 필드만 컬럼으로 표시
        self.setColumnCount(19)
        self.setHorizontalHeaderLabels([
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
            TABLE_COLUMN_NAMES["processed_at"]                   # 18
        ])
        header = self.horizontalHeader()
        for i in range(19):
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
        self.load_photo = self.photo_checkbox.isChecked()
        try:
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
            self.setRowCount(0)
            if not filtered:
                return
            total_rows = len(filtered)
            self.setRowCount(total_rows)
            for row_idx, item in enumerate(filtered):
                try:
                    checkbox = QCheckBox()
                    checkbox.setProperty("row_index", row_idx)
                    checkbox.stateChanged.connect(self._on_any_checkbox_changed)
                    self.setCellWidget(row_idx, 0, self._create_checkbox_widget(checkbox))
                    
                    # 1. 이미지 썸네일 (사진 로드 체크박스 체크 시만)
                    label = QLabel()
                    label.setAlignment(Qt.AlignCenter)
                    if self.load_photo:
                        image_url = getattr(item, 'image_url', None) or getattr(item, 'print_url', None)
                        print(f"[썸네일] 이미지 URL: {image_url}")
                        if self.log_function:
                            self.log_function(f"[썸네일] 이미지 URL: {image_url}", LOG_DEBUG)
                        if image_url:
                            try:
                                headers = {"User-Agent": "Mozilla/5.0"}
                                response = requests.get(image_url, headers=headers, timeout=3)
                                print(f"[썸네일] status_code: {response.status_code}")
                                if self.log_function:
                                    self.log_function(f"[썸네일] status_code: {response.status_code}", LOG_DEBUG)
                                if response.status_code == 200:
                                    image = QImage.fromData(response.content)
                                    print(f"[썸네일] QImage isNull: {image.isNull()}")
                                    if self.log_function:
                                        self.log_function(f"[썸네일] QImage isNull: {image.isNull()}", LOG_DEBUG)
                                    if not image.isNull():
                                        pixmap = QPixmap.fromImage(image).scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                                        label.setPixmap(pixmap)
                                else:
                                    print(f"[썸네일] 이미지 응답 status_code 오류: {response.status_code}")
                                    if self.log_function:
                                        self.log_function(f"[썸네일] 이미지 응답 status_code 오류: {response.status_code}", LOG_WARNING)
                            except Exception as e:
                                print(f"[썸네일] 이미지 로드 예외: {e}")
                                if self.log_function:
                                    self.log_function(f"[썸네일] 이미지 로드 예외: {e}", LOG_ERROR)
                    else:
                        if self.log_function:
                            self.log_function("사진 로드가 비활성화되어 썸네일을 표시하지 않습니다.", LOG_INFO)
                    self.setCellWidget(row_idx, 1, label)
                    
                    # 2. ID
                    self.setItem(row_idx, 2, QTableWidgetItem(str(item.id)))

                    # 3. store_name (store_url 하이퍼링크)
                    store_name_item = QTableWidgetItem(item.store_name)
                    store_url = getattr(item, 'store_url', None)
                    if store_url:
                        store_name_item.setForeground(QBrush(QColor(0, 102, 204)))
                        store_name_item.setData(Qt.UserRole, store_url)
                    self.setItem(row_idx, 3, store_name_item)
                    
                    # 4. 동대문주소
                    self.setItem(row_idx, 4, QTableWidgetItem(item.store_ddm_address))
                    # 5. 퀄리티 | 품질코드
                    quality_code = getattr(item, 'quality_code', None)
                    quality_name = item.quality_name
                    quality_display = quality_name
                    if quality_code:
                        quality_display += f" | {quality_code}"
                    quality_name_item = QTableWidgetItem(quality_display)
                    quality_url = getattr(item, 'quality_url', None)
                    if quality_url:
                        quality_name_item.setForeground(QBrush(QColor(0, 102, 204)))
                        quality_name_item.setData(Qt.UserRole, quality_url)
                    self.setItem(row_idx, 5, quality_name_item)
                    # 6. 스와치픽업 (O/X, 컬러)
                    swatch_pickupable = getattr(item, 'swatch_pickupable', None)
                    swatch_item = QTableWidgetItem("O" if swatch_pickupable else "X")
                    if swatch_pickupable:
                        swatch_item.setForeground(QBrush(QColor(46, 204, 113)))  # 초록
                    else:
                        swatch_item.setForeground(QBrush(QColor(231, 76, 60)))  # 빨강
                    self.setItem(row_idx, 6, swatch_item)
                    # 7. 스와치보관
                    swatch_storage = getattr(item, 'swatch_storage', None)
                    if swatch_storage is None or swatch_storage == '':
                        swatch_storage_item = QTableWidgetItem("X")
                        swatch_storage_item.setForeground(QBrush(QColor(231, 76, 60)))  # 빨강
                    else:
                        swatch_storage_item = QTableWidgetItem(str(swatch_storage))
                    self.setItem(row_idx, 7, swatch_storage_item)
                    # 8. 컬러번호
                    self.setItem(row_idx, 8, QTableWidgetItem(str(item.color_number)))
                    # 9. 컬러코드
                    self.setItem(row_idx, 9, QTableWidgetItem(str(item.color_code or "")))
                    # 10. 수량
                    try:
                        qty = int(item.quantity)
                    except Exception:
                        qty = 0
                    quantity_item = QTableWidgetItem(f"{qty}")
                    quantity_item.setData(Qt.UserRole, qty)
                    self.setItem(row_idx, 10, quantity_item)
                    # 11. 발주번호 (purchase_url 하이퍼링크)
                    purchase_code_item = QTableWidgetItem(item.purchase_code)
                    purchase_url = getattr(item, 'purchase_url', None)
                    if purchase_url:
                        purchase_code_item.setForeground(QBrush(QColor(0, 102, 204)))
                        purchase_code_item.setData(Qt.UserRole, purchase_url)
                    self.setItem(row_idx, 11, purchase_code_item)
                    # 12. 주문코드 (order_url 하이퍼링크)
                    order_code_item = QTableWidgetItem(item.order_code if item.order_code else "")
                    order_url = getattr(item, 'order_url', None)
                    if order_url:
                        order_code_item.setForeground(QBrush(QColor(0, 102, 204)))
                        order_code_item.setData(Qt.UserRole, order_url)
                    self.setItem(row_idx, 12, order_code_item)
                    # 13. 출고일
                    pickup_date = item.pickup_at.strftime("%Y-%m-%d") if hasattr(item.pickup_at, 'strftime') else str(item.pickup_at)
                    self.setItem(row_idx, 13, QTableWidgetItem(pickup_date))
                    # 14. 최종출고일
                    last_pickup_date = item.last_pickup_at.strftime("%Y-%m-%d") if getattr(item, 'last_pickup_at', None) and hasattr(item.last_pickup_at, 'strftime') else (str(item.last_pickup_at) if getattr(item, 'last_pickup_at', None) else "")
                    self.setItem(row_idx, 14, QTableWidgetItem(last_pickup_date))
                    # 15. 배송방법
                    delivery_method = DELIVERY_METHODS.get(item.delivery_method, item.delivery_method)
                    self.setItem(row_idx, 15, QTableWidgetItem(delivery_method))
                    # 16. 택배사
                    logistics_company = LOGISTICS_COMPANIES.get(item.logistics_company, item.logistics_company) if item.logistics_company else ""
                    self.setItem(row_idx, 16, QTableWidgetItem(logistics_company))
                    # 17. 메시지상태 (색상 기존대로)
                    message_status_text = getattr(item, 'message_status', MessageStatus.PENDING.value) if hasattr(item, 'message_status') else MessageStatus.PENDING.value
                    message_status_item = QTableWidgetItem(message_status_text)
                    if message_status_text == MessageStatus.SENT.value:
                        message_status_item.setBackground(QColor(212, 237, 218))
                        message_status_item.setForeground(QColor(21, 87, 36))
                    elif message_status_text == MessageStatus.FAILED.value:
                        message_status_item.setBackground(QColor(248, 215, 218))
                        message_status_item.setForeground(QColor(114, 28, 36))
                    elif message_status_text == MessageStatus.SENDING.value:
                        message_status_item.setBackground(QColor(255, 243, 205))
                        message_status_item.setForeground(QColor(133, 100, 4))
                    elif message_status_text == MessageStatus.CANCELLED.value:
                        message_status_item.setBackground(QColor(233, 236, 239))
                        message_status_item.setForeground(QColor(73, 80, 87))
                    elif message_status_text == MessageStatus.RETRY_WAITING.value:
                        message_status_item.setBackground(QColor(217, 237, 247))
                        message_status_item.setForeground(QColor(12, 84, 96))
                    elif message_status_text == MessageStatus.PENDING.value:
                        message_status_item.setBackground(QColor(255, 255, 255))
                        message_status_item.setForeground(QColor(0, 0, 0))
                    self.setItem(row_idx, 17, message_status_item)
                    # 18. 처리시각
                    if hasattr(item, 'processed_at') and item.processed_at:
                        processed_at = item.processed_at.strftime("%Y-%m-%d %H:%M:%S")
                    else:
                        processed_at = ""
                    self.setItem(row_idx, 18, QTableWidgetItem(processed_at))
                except Exception as row_error:
                    for col in range(self.columnCount()):
                        self.setItem(row_idx, col, QTableWidgetItem(""))
        except Exception as e:
            print(f"테이블 업데이트 중 오류: {str(e)}")
            self.setRowCount(0)
    
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
                        # id, store_name, purchase_code 등 주요 필드는 기존대로 추가
                        id_item = self.item(row, 2)
                        store_item = self.item(row, 3)
                        purchase_item = self.item(row, 11)
                        if id_item and store_item and purchase_item:
                            item_data["id"] = int(id_item.text())
                            item_data["store_name"] = store_item.text()
                            item_data["purchase_code"] = purchase_item.text()
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
    
    def _on_photo_checkbox_changed(self, state):
        """사진 로드 체크박스 상태 변경"""
        self.load_photo = (state == Qt.Checked)
        # 현재 데이터로 테이블 업데이트
        if hasattr(self, '_current_data'):
            self.update_data(self._current_data)

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
                            message_status_item = QTableWidgetItem(message_status)
                            # 메시지 상태에 따른 색상 설정
                            if message_status == MessageStatus.SENT.value:
                                message_status_item.setBackground(QColor(212, 237, 218))  # 연한 초록색
                                message_status_item.setForeground(QColor(21, 87, 36))     # 진한 초록색
                            elif message_status == MessageStatus.FAILED.value:
                                message_status_item.setBackground(QColor(248, 215, 218))  # 연한 빨간색
                                message_status_item.setForeground(QColor(114, 28, 36))    # 진한 빨간색
                            elif message_status == MessageStatus.SENDING.value:
                                message_status_item.setBackground(QColor(255, 243, 205))  # 연한 노란색
                                message_status_item.setForeground(QColor(133, 100, 4))    # 진한 노란색
                            elif message_status == MessageStatus.CANCELLED.value:
                                message_status_item.setBackground(QColor(233, 236, 239))  # 연한 회색
                                message_status_item.setForeground(QColor(73, 80, 87))     # 진한 회색
                            elif message_status == MessageStatus.RETRY_WAITING.value:
                                message_status_item.setBackground(QColor(217, 237, 247))  # 연한 파란색
                                message_status_item.setForeground(QColor(12, 84, 96))     # 진한 파란색
                            elif message_status == MessageStatus.PENDING.value:
                                message_status_item.setBackground(QColor(255, 255, 255))  # 흰색
                                message_status_item.setForeground(QColor(0, 0, 0))        # 검정색
                            
                        # 인덱스 유효성 체크 후 setItem
                        if row < self.rowCount() and 17 < self.columnCount():
                            try:
                                self.setItem(row, 17, message_status_item)
                            except Exception as e:
                                print(f"setItem(row={row}, col=17) 예외: {e}")
                            
                        # 처리시각 업데이트 (컬럼 18)
                        if processed_at and row < self.rowCount() and 18 < self.columnCount():
                            try:
                                self.setItem(row, 18, QTableWidgetItem(processed_at))
                            except Exception as e:
                                print(f"setItem(row={row}, col=18) 예외: {e}")
                    except ValueError:
                        continue
        except Exception as e:
            print(f"상태 업데이트 중 오류: {str(e)}")

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

    def _on_pickup_date_filter_changed(self, idx):
        if hasattr(self, '_current_data'):
            self.update_data(self._current_data) 