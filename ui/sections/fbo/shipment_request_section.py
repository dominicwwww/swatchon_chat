"""
FBO 출고 요청 섹션 - 컴포넌트 기반 리팩토링 버전
"""
from typing import List, Dict, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFrame, QMessageBox, QApplication
)
from PySide6.QtCore import Qt, Signal, QTimer, QMarginsF
from PySide6.QtGui import QFont
import os
import sys
import traceback
from datetime import datetime, timedelta

from core.types import OrderType, FboOperationType, ShipmentStatus, MessageStatus
from ui.sections.base_section import BaseSection
from ui.theme import get_theme
from ui.components.log_widget import LOG_INFO, LOG_DEBUG, LOG_WARNING, LOG_ERROR, LOG_SUCCESS
from ui.components.shipment_request_table import ShipmentRequestTable
from ui.components.message_manager import MessageManager
from ui.components.data_manager import DataManager
from ui.components.statistics_widget import StatisticsWidget
from ui.components.filter_widget import FilterWidget
from core.schemas import PurchaseProduct


class ShipmentRequestSection(BaseSection):
    """
    FBO 출고 요청 섹션 - 컴포넌트 기반 리팩토링 버전
    
    기존 1100줄의 방대한 코드를 재사용 가능한 컴포넌트로 분리하여 모듈화
    """
    
    def __init__(self, parent=None):
        super().__init__("FBO 출고 요청", parent)
        
        # 컴포넌트 초기화
        self.setup_components()
        
        # 헤더 버튼 추가
        self.refresh_button = self.add_header_button("새로고침", self._on_refresh_clicked)
        self.refresh_address_button = self.add_header_button("주소록 새로고침", self._on_refresh_address_clicked)
        self.preview_button = self.add_header_button("📋 메시지 미리보기", self._on_preview_clicked, primary=True)
        self.message_log_button = self.add_header_button("📄 메시지 로그 출력", self._on_message_log_clicked)
        self.send_button = self.add_header_button("💌 메시지 전송", self._on_send_clicked)
        self.emergency_stop_button = self.add_header_button("🛑 긴급 정지", self._on_emergency_stop_clicked)
        
        # 긴급 정지 버튼 스타일 설정
        self.emergency_stop_button.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                font-weight: bold;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
            QPushButton:pressed {
                background-color: #bd2130;
            }
            QPushButton:disabled {
                background-color: #6c757d;
                color: #adb5bd;
            }
        """)
        
        # 초기 버튼 상태 설정
        self.send_button.setEnabled(False)
        self.message_log_button.setEnabled(False)
        self.emergency_stop_button.setEnabled(False)
        
        # UI 설정
        self.setup_content()
        
        # 선택된 항목 추적
        self._selected_items: List[PurchaseProduct] = []
        self._preview_ready = False  # 미리보기 상태 플래그
    
    def setup_components(self):
        """컴포넌트 초기화 및 연결"""
        # 데이터 매니저 (루트 data 디렉토리 자동 사용)
        self.data_manager = DataManager(
            order_type=OrderType.FBO,
            log_function=self.log
        )
        
        # 메시지 매니저
        self.message_manager = MessageManager(
            order_type=OrderType.FBO,
            operation_type=FboOperationType.SHIPMENT_REQUEST,
            log_function=self.log
        )
        
        # 통계 위젯
        self.statistics_widget = StatisticsWidget()
        
        # 필터 위젯
        self.filter_widget = FilterWidget()
        
        # 시그널 연결
        self.connect_signals()
    
    def connect_signals(self):
        """컴포넌트 간 시그널 연결"""
        # 데이터 매니저 시그널
        self.data_manager.data_loaded.connect(self._on_data_loaded)
        self.data_manager.data_filtered.connect(self._on_data_filtered)
        self.data_manager.error_occurred.connect(self._on_error_occurred)
        
        # 메시지 매니저 시그널
        self.message_manager.message_preview_generated.connect(self._on_message_preview_generated)
        self.message_manager.message_sent.connect(self._on_message_sent)
        
        # 필터 위젯 시그널
        self.filter_widget.search_changed.connect(self._on_search_changed)
        self.filter_widget.filter_changed.connect(self._on_filter_changed)
        
        # 통계 위젯 시그널
        self.statistics_widget.card_clicked.connect(self._on_statistics_card_clicked)
    
    def setup_content(self):
        """콘텐츠 설정"""
        # 필터 영역
        self.content_layout.addWidget(self.filter_widget)
        
        # 테이블 위젯
        self.table = ShipmentRequestTable(log_function=self.log)
        self.table.selection_changed.connect(self._on_table_selection_changed)
        self.content_layout.addWidget(self.table.main_widget)
        
        # 통계 위젯
        self.content_layout.addWidget(self.statistics_widget)
        
        # 추가 통계 카드들 생성
        self._setup_additional_statistics()
        
        # 통계 정보 레이블
        self.stats_label = QLabel("총 0건")
        self.content_layout.addWidget(self.stats_label)
    
    def _setup_additional_statistics(self):
        """추가 통계 카드들 설정"""
        # FBO 출고 요청에 특화된 추가 통계 카드들
        self.statistics_widget.add_custom_card("product_count", "프로덕트 수", "info", 0)
        self.statistics_widget.add_custom_card("store_count", "판매자 수", "primary", 0)
        self.statistics_widget.add_custom_card("total_quantity", "총 수량", "success", 0)
        self.statistics_widget.add_custom_card("quick_pickup", "동대문 픽업", "warning", 0)
        self.statistics_widget.add_custom_card("logistics", "판매자 발송", "info", 0)
    
    def _on_data_loaded(self, data: List[PurchaseProduct]):
        """데이터 로드 완료 이벤트"""
        self.log(f"총 {len(data)}건의 데이터가 로드되었습니다.", LOG_SUCCESS)
        
        # 테이블 업데이트
        self.table.update_data(data)
        
        # 통계 업데이트
        self._update_all_statistics()
    
    def _on_data_filtered(self, filtered_data: List[PurchaseProduct]):
        """데이터 필터링 완료 이벤트"""
        self.log(f"필터링 결과: {len(filtered_data)}건", LOG_INFO)
        
        # 테이블 업데이트
        self.table.update_data(filtered_data)
        
        # 통계 업데이트
        self._update_all_statistics()
    
    def _on_error_occurred(self, error_message: str):
        """오류 발생 이벤트"""
        self.log(f"오류 발생: {error_message}", LOG_ERROR)
        QMessageBox.critical(self, "오류", error_message)
    
    def _on_message_preview_generated(self, preview_data: Dict[str, Any]):
        """메시지 미리보기 생성 완료 이벤트"""
        self.log("메시지 미리보기가 생성되었습니다.", LOG_SUCCESS)
        self.send_button.setEnabled(True)
        self.message_log_button.setEnabled(True)
        self.preview_button.setText("📋 메시지 미리보기")
        self.log("💡 '메시지 전송' 버튼을 클릭하여 실제 전송하거나, 다른 항목을 선택하여 새로운 미리보기를 생성하세요.", LOG_INFO)
        
        # quantity가 50 이상인 아이템 필터링
        large_quantity_items = [
            item for item in self._selected_items
            if isinstance(item.quantity, (int, float)) and item.quantity >= 50
        ]
        
        # 전체 프로덕트 정보 추가
        total_product_count = len(self._selected_items)
        total_unique_qualities = len(set(item.quality_code for item in self._selected_items if item.quality_code))
        
        if large_quantity_items:
            # swatch_storage 기준으로 정렬
            sorted_items = sorted(large_quantity_items, key=lambda x: str(x.swatch_storage or ""))
            
            # 보관함이 있는 항목만 카운트
            storage_items = [item for item in large_quantity_items if item.swatch_storage]
            large_product_count = len(storage_items)
            large_unique_qualities = len(set(item.quality_code for item in storage_items if item.quality_code))
            
            # pickup_at이 가장 빠른 날짜의 형식으로 헤더 생성 (하루 더하기)
            if sorted_items:
                from datetime import timedelta
                # 원본 날짜 (실제 프로덕트 출고일)
                original_pickup = sorted_items[0].pickup_at
                pickup_date_str = original_pickup.strftime('%Y-%m-%d')
                
                # 표시용 날짜 (하루 더하기)
                display_pickup = original_pickup + timedelta(days=1)
                header_date = display_pickup.strftime('%m/%d')
                
                admin_url = f"https://admin.swatchon.me/purchase_products/receive_index?q%5Bpickup_at_gteq%5D={pickup_date_str}&q%5Bpickup_at_lteq%5D={pickup_date_str}"
                
                self.log(f"\n:clipboard: {admin_url}", LOG_INFO)
                self.log(f"[{header_date} 전체 입고 예정: {total_product_count} PD / {total_unique_qualities} QL]", LOG_INFO)
                self.log(f"[{header_date} 50yd 이상 입고 예정: {large_product_count} PD / {large_unique_qualities} QL]", LOG_INFO)
                self.log("", LOG_INFO)  # 빈 줄
                self.log("스와치 보관함 (스와치 제공 여부) - QL (컬러 순서) - 발주번호 - 주문번호 - 판매자 - 수량", LOG_INFO)
                self.log("", LOG_INFO)  # 빈 줄
            
            # 50야드 이상 항목은 모두 표시
            for idx, item in enumerate(sorted_items, 1):
                # swatch_storage 표시
                storage_display = str(item.swatch_storage) if item.swatch_storage else "None"
                if not item.swatch_storage:
                    pickupable = "O" if item.swatch_pickupable else "X"
                    storage_display += f" ({pickupable})"
                
                # quality_code와 color_number 표시
                quality_with_color = f"{item.quality_code or 'N/A'}"
                if item.color_number:
                    quality_with_color += f" ({item.color_number})"
                
                log_message = (
                    f"{idx}) {storage_display} - "
                    f"{quality_with_color} - "
                    f"{item.purchase_code} - "
                    f"{item.order_code or 'N/A'} - "
                    f"{item.store_name} - "
                    f"{item.quantity}yd"
                )
                self.log(log_message, LOG_INFO)
            
            # 고유한 quality_code 개수 계산 (보관함 있는 항목 기준)
            self.log(f"\n컬러 검수를 위해 총 {large_unique_qualities} QL의 스와치를 준비해주시기 바랍니다~!", LOG_INFO)
            
            # 판매자별 메시지 미리보기는 3개만 표시
            store_messages = preview_data.get("store_messages", [])
            if store_messages:
                self.log("\n=== 메시지 미리보기 (3개 판매자) ===", LOG_INFO)
                import random
                sample_stores = random.sample(store_messages, min(3, len(store_messages)))
                
                for store_msg in sample_stores:
                    self.log(f"\n--- [{store_msg['store_name']}] → [{store_msg['store_name']}] ---", LOG_INFO)
                    self.log(f"[출고 요청-{store_msg['store_name']}]", LOG_INFO)
                    self.log(store_msg["message"], LOG_INFO)
                
                if len(store_messages) > 3:
                    self.log(f"\n... 외 {len(store_messages) - 3}개 판매자 메시지 생략됨", LOG_INFO)
                
                self.log("\n=== 미리보기 완료 ===", LOG_INFO)
        else:
            # 50야드 이상이 없어도 전체 정보는 표시
            if self._selected_items:
                from datetime import timedelta
                # 원본 날짜 (실제 프로덕트 출고일)
                original_pickup = self._selected_items[0].pickup_at
                pickup_date_str = original_pickup.strftime('%Y-%m-%d')
                
                # 표시용 날짜 (하루 더하기)
                display_pickup = original_pickup + timedelta(days=1)
                header_date = display_pickup.strftime('%m/%d')
                
                admin_url = f"https://admin.swatchon.me/purchase_products/receive_index?q%5Bpickup_at_gteq%5D={pickup_date_str}&q%5Bpickup_at_lteq%5D={pickup_date_str}"
                
                self.log(f"\n:clipboard: {admin_url}", LOG_INFO)
                self.log(f"[{header_date} 전체 입고 예정: {total_product_count} PD / {total_unique_qualities} QL]", LOG_INFO)
                self.log("[50yd 이상 PD 없음]", LOG_INFO)
    
    def _on_message_sent(self, result: Dict[str, Any]):
        """메시지 전송 완료 이벤트"""
        try:
            success_count = result.get('success_count', 0)
            fail_count = result.get('fail_count', 0)
            cancelled_count = result.get('cancelled_count', 0)
            emergency_stop = result.get('emergency_stop', False)
            
            # 전송 결과 로그
            self.log("\n=== 메시지 전송 결과 ===", LOG_INFO)
            self.log(f"종료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", LOG_INFO)
            
            if emergency_stop:
                self.log(f"긴급 정지로 전송 중단: 성공 {success_count}건, 실패 {fail_count}건, 취소 {cancelled_count}건", LOG_WARNING)
                QMessageBox.information(self, "전송 중단", 
                    f"긴급 정지로 인해 전송이 중단되었습니다.\n성공: {success_count}건, 실패: {fail_count}건, 취소: {cancelled_count}건")
            else:
                self.log(f"메시지 전송 완료: 성공 {success_count}건, 실패 {fail_count}건", LOG_SUCCESS)
                QMessageBox.information(self, "전송 완료", 
                    f"메시지 전송이 완료되었습니다.\n성공: {success_count}건, 실패: {fail_count}건")
            
            # 통계 및 테이블 업데이트
            self._update_all_statistics()
            self.table.update_data(self.data_manager.get_filtered_data())
            
            # 버튼 상태 초기화
            self._reset_send_button_state()
            
        except Exception as e:
            error_msg = f"전송 완료 처리 중 오류 발생: {str(e)}\n{traceback.format_exc()}"
            self.log(error_msg, LOG_ERROR)
            QMessageBox.critical(self, "오류", error_msg)
            self._reset_send_button_state()
    
    def _on_search_changed(self, search_text: str):
        """검색어 변경 이벤트"""
        status_filter = self.filter_widget.get_status_filter()
        self.data_manager.apply_filters(search_text, status_filter)
    
    def _on_filter_changed(self, filter_type: str, value: str):
        """필터 변경 이벤트"""
        if filter_type == 'status':
            search_text = self.filter_widget.get_search_text()
            self.data_manager.apply_filters(search_text, value)
    
    def _on_statistics_card_clicked(self, card_key: str):
        """통계 카드 클릭 이벤트"""
        # 해당 상태로 필터 설정
        if card_key == 'total':
            self.filter_widget.set_status_filter('all')
            self._on_filter_changed('status', 'all')
        elif card_key in ['pending', 'sending', 'sent', 'failed', 'cancelled']:
            status_map = {
                'pending': ShipmentStatus.PENDING.value,
                'sending': ShipmentStatus.SENDING.value,
                'sent': ShipmentStatus.SENT.value,
                'failed': ShipmentStatus.FAILED.value,
                'cancelled': ShipmentStatus.CANCELLED.value
            }
            if card_key in status_map:
                self.filter_widget.set_status_filter(status_map[card_key])
                self._on_filter_changed('status', status_map[card_key])
        
        self.log(f"'{card_key}' 상태로 필터가 적용되었습니다.", LOG_INFO)
    
    def _on_table_selection_changed(self, selected_items):
        """테이블 선택 변경 이벤트"""
        # 선택된 항목 ID 목록
        selected_ids = [item['id'] for item in selected_items]
        
        # 데이터 매니저에서 선택된 항목의 전체 데이터 가져오기
        complete_selected_items = [
            item for item in self.data_manager.get_filtered_data()
            if item.id in selected_ids
        ]
        
        # 완전한 데이터로 선택된 항목 저장
        self._selected_items = complete_selected_items
        
        # 버튼 상태 업데이트
        has_selection = len(complete_selected_items) > 0
        self.preview_button.setEnabled(has_selection)
        
        if has_selection:
            if len(complete_selected_items) == self.table.rowCount():
                self.log(f"전체 {len(complete_selected_items)}개 항목이 선택되었습니다.", LOG_INFO)
            else:
                self.log(f"{len(complete_selected_items)}개 항목이 선택되었습니다.", LOG_INFO)
            
            # 미리보기 상태 초기화
            self.send_button.setEnabled(False)
            self.message_log_button.setEnabled(False)
            self.preview_button.setText("📋 메시지 미리보기")
            self.message_manager.clear_preview_data()
        else:
            self.log("선택된 항목이 없습니다.", LOG_INFO)
            self.send_button.setEnabled(False)
            self.message_log_button.setEnabled(False)
            self.preview_button.setText("📋 메시지 미리보기")
    
    def _on_refresh_clicked(self):
        """새로고침 버튼 클릭 이벤트 (API 연동)"""
        self.log("출고 요청 데이터를 API에서 새로고침합니다.", LOG_INFO)
        success = self.data_manager.load_data_from_api()
        if not success:
            QMessageBox.warning(self, "API 오류", "API에서 데이터를 받아오지 못했습니다.")
    
    def _on_refresh_address_clicked(self):
        """주소록 새로고침 버튼 클릭 이벤트"""
        try:
            self.log("주소록을 새로고침합니다.", LOG_INFO)
            from services.address_book_service import AddressBookService
            
            address_book_service = AddressBookService()
            address_book_service.reload_address_book()
            
            # 로드된 매핑 정보 표시
            mappings = address_book_service.get_all_mappings()
            if mappings:
                self.log(f"주소록 새로고침 완료: {len(mappings)}개 매핑 로드됨", LOG_SUCCESS)
                # 처음 몇 개 매핑 예시 표시
                sample_count = min(3, len(mappings))
                sample_items = list(mappings.items())[:sample_count]
                for store_name, chat_room in sample_items:
                    self.log(f"  {store_name} -> {chat_room}", LOG_DEBUG)
                if len(mappings) > sample_count:
                    self.log(f"  ... 외 {len(mappings) - sample_count}개", LOG_DEBUG)
            else:
                self.log("주소록 데이터가 없습니다.", LOG_WARNING)
            
        except Exception as e:
            self.log(f"주소록 새로고침 중 오류: {str(e)}", LOG_ERROR)
            QMessageBox.critical(self, "오류", f"주소록 새로고침 중 오류가 발생했습니다:\n{str(e)}")
    
    def _on_preview_clicked(self):
        """미리보기/출력 버튼 클릭 이벤트"""
        if not self._preview_ready:
            # 1. 메시지 미리보기 클릭 시: 로그 출력, 레이블 변경
            if not self._selected_items:
                QMessageBox.warning(self, "선택 오류", "선택된 항목이 없습니다.")
                return
            
            # 중복 전송 검증
            selected_items_dict = [self._purchase_product_to_dict(item) for item in self._selected_items]
            duplicate_check = self.message_manager.check_duplicate_sending(
                selected_items_dict,
                self.data_manager.get_all_data()
            )
            
            if duplicate_check.get('has_duplicates', False):
                duplicates = duplicate_check.get('duplicates', {})
                duplicate_info = []
                for seller_name, info in duplicates.items():
                    duplicate_info.append(f"• {seller_name}: 이미 전송된 {info['sent_count']}건, 대기 중 {info['pending_count']}건")
                
                message = "다음 판매자들에게 이미 전송된 메시지가 있습니다:\n\n" + "\n".join(duplicate_info) + "\n\n계속 진행하시겠습니까?"
                
                reply = QMessageBox.question(
                    self, "중복 전송 확인", message,
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                )
                
                if reply != QMessageBox.Yes:
                    return
            
            # 메시지 미리보기 생성
            self.message_manager.generate_message_preview(selected_items_dict)
            self.log("메시지 미리보기가 생성되었습니다.", LOG_SUCCESS)
            self.log("💡 '스와치 보관함 출력' 버튼을 클릭하면 인쇄 미리보기가 열립니다.", LOG_INFO)
            self._preview_ready = True
            self.preview_button.setText("스와치 보관함 출력")
        else:
            # 2. 스와치 보관함 출력 클릭 시: 인쇄 미리보기 창
            from PySide6.QtPrintSupport import QPrinter, QPrintPreviewDialog
            from PySide6.QtGui import QTextDocument
            from PySide6.QtCore import QMarginsF
            printer = QPrinter()
            printer.setPageMargins(QMarginsF(0, 0, 0, 0))
            preview = QPrintPreviewDialog(printer, self)
            large_quantity_items = [
                item for item in self._selected_items
                if isinstance(item.quantity, (int, float)) and item.quantity >= 50
            ]
            if large_quantity_items:
                sorted_items = sorted(large_quantity_items, key=lambda x: str(x.swatch_storage or ""))
                # 보관함이 있는 항목만 카운트
                storage_items = [item for item in large_quantity_items if item.swatch_storage]
                product_count = len(storage_items)
                unique_qualities = len(set(item.quality_code for item in storage_items if item.quality_code))
                html = []
                if sorted_items:
                    from datetime import timedelta
                    first_pickup = sorted_items[0].pickup_at + timedelta(days=1)
                    header_date = first_pickup.strftime('%m/%d')
                    html.append(f"<h2 style='color:#000;'>[{header_date}] 50yd 이상 입고 예정: {product_count} PD / {unique_qualities} QL</h2>")
                    html.append("<p style='color:#000;'>스와치 보관함 (스와치 제공 여부) - QL (컬러 순서) - 발주번호 - 판매자 - 수량</p>")
                    html.append("<br>")
                for idx, item in enumerate(sorted_items, 1):
                    storage_display = str(item.swatch_storage) if item.swatch_storage else "None"
                    if not item.swatch_storage:
                        pickupable = "O" if item.swatch_pickupable else "X"
                        storage_display += f" ({pickupable})"
                    quality_with_color = f"{item.quality_code or 'N/A'}"
                    if item.color_number:
                        quality_with_color += f" ({item.color_number})"
                    html.append(
                        f"<span style='color:#000;'>{idx}) {storage_display} - "
                        f"{quality_with_color} - "
                        f"{item.purchase_code} - "
                        f"{item.store_name} - "
                        f"{item.quantity}yd</span>"
                    )
                document = QTextDocument()
                document.setHtml("<br>".join(html))
                preview.paintRequested.connect(document.print_)
                preview.exec()
                self.log("스와치 보관함 미리보기/인쇄가 완료되었습니다.", LOG_SUCCESS)
            self._preview_ready = False
            self.preview_button.setText("📋 메시지 미리보기")
    
    def _on_send_clicked(self):
        """메시지 전송 버튼 클릭 이벤트"""
        if not self.message_manager.get_preview_data():
            QMessageBox.warning(self, "전송 오류", "먼저 미리보기를 생성해주세요.")
            return
        
        reply = QMessageBox.question(
            self, "전송 확인", 
            f"선택된 {len(self._selected_items)}개 항목의 메시지를 전송하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                # 버튼 상태 변경
                self.send_button.setEnabled(False)
                self.send_button.setText("전송 중...")
                self.emergency_stop_button.setEnabled(True)
                
                # 메시지 전송 시작 전 로그 초기화
                self.log("\n=== 메시지 전송 시작 ===", LOG_INFO)
                self.log(f"선택된 항목 수: {len(self._selected_items)}", LOG_INFO)
                self.log(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", LOG_INFO)
                self.log("=" * 50, LOG_INFO)
                
                # 메시지 전송
                try:
                    # 메시지 전송 시도
                    self.message_manager.send_messages(
                        update_status_callback=self._update_item_status
                    )
                except Exception as send_error:
                    import traceback
                    error_msg = f"메시지 전송 중 예외 발생:\n{str(send_error)}\n{traceback.format_exc()}"
                    print(error_msg)  # 터미널에 전체 스택트레이스 출력
                    self.log(error_msg, LOG_ERROR)
                    
                    # 현재 남은 판매자 정보 로깅
                    preview_data = self.message_manager.get_preview_data()
                    if preview_data:
                        remaining_sellers = list(preview_data.keys())
                        if remaining_sellers:
                            self.log("\n전송 실패 시점의 남은 판매자 목록:", LOG_ERROR)
                            for seller in remaining_sellers:
                                self.log(f"- {seller}", LOG_ERROR)
                    
                    # 사용자에게 상세한 오류 메시지 표시
                    QMessageBox.critical(
                        self, 
                        "전송 오류", 
                        f"메시지 전송 중 오류가 발생했습니다:\n\n"
                        f"오류 내용: {str(send_error)}\n\n"
                        f"자세한 내용은 로그를 확인해주세요."
                    )
                    self._reset_send_button_state()
                    return
                
            except Exception as e:
                import traceback
                error_msg = f"메시지 전송 처리 중 예외 발생:\n{str(e)}\n{traceback.format_exc()}"
                print(error_msg)  # 터미널에 전체 스택트레이스 출력
                self.log(error_msg, LOG_ERROR)
                
                # 현재 남은 판매자 정보 로깅
                preview_data = self.message_manager.get_preview_data()
                if preview_data:
                    remaining_sellers = list(preview_data.keys())
                    if remaining_sellers:
                        self.log("\n처리 중 예외 발생 시점의 남은 판매자 목록:", LOG_ERROR)
                        for seller in remaining_sellers:
                            self.log(f"- {seller}", LOG_ERROR)
                
                QMessageBox.critical(
                    self, 
                    "전송 오류", 
                    f"메시지 전송 처리 중 오류가 발생했습니다:\n\n"
                    f"오류 내용: {str(e)}\n\n"
                    f"자세한 내용은 로그를 확인해주세요."
                )
                self._reset_send_button_state()
                return
    
    def _on_emergency_stop_clicked(self):
        """긴급 정지 버튼 클릭 이벤트"""
        if not self.message_manager.is_sending():
            return
        
        reply = QMessageBox.question(
            self, "긴급 정지 확인", 
            "정말로 메시지 전송을 중단하시겠습니까?\n\n현재 전송 중인 메시지는 완료되고, 남은 메시지들은 취소됩니다.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.message_manager.emergency_stop()
            self.emergency_stop_button.setEnabled(False)
    
    def _on_message_log_clicked(self):
        """메시지 로그 출력 버튼 클릭 이벤트"""
        if not self.message_manager.get_preview_data():
            QMessageBox.warning(self, "로그 출력 오류", "먼저 미리보기를 생성해주세요.")
            return
        
        # 로그에 카카오톡 메시지 출력
        self._log_kakao_messages()
    
    def _log_kakao_messages(self):
        """로그에 카카오톡 메시지 출력"""
        preview_data = self.message_manager.get_preview_data()
        
        # 실제 데이터 구조 확인
        self.log(f"Preview data keys: {list(preview_data.keys()) if preview_data else 'None'}", LOG_DEBUG)
        
        if not preview_data:
            self.log("미리보기 데이터가 없습니다.", LOG_WARNING)
            return
        
        # 다양한 키 형태 확인
        store_messages = None
        if 'store_messages' in preview_data:
            store_messages = preview_data['store_messages']
        elif 'messages' in preview_data:
            store_messages = preview_data['messages']
        else:
            # 미리보기 데이터가 직접 판매자별 메시지일 수도 있음
            store_messages = []
            for key, value in preview_data.items():
                if isinstance(value, dict) and 'message' in value:
                    store_messages.append({
                        'store_name': key,
                        'message': value['message']
                    })
                elif isinstance(value, str):
                    # 키가 판매자명이고 값이 메시지인 경우
                    store_messages.append({
                        'store_name': key,
                        'message': value
                    })
        
        if not store_messages:
            self.log("전송할 메시지가 없습니다.", LOG_WARNING)
            self.log(f"사용 가능한 데이터: {preview_data}", LOG_DEBUG)
            return
        
        self.log("\n" + "=" * 60, LOG_INFO)
        self.log("📱 카카오톡 메시지 로그", LOG_INFO)
        self.log("=" * 60, LOG_INFO)
        self.log(f"총 {len(store_messages)}개 판매자에게 전송될 메시지\n", LOG_INFO)
        
        for i, store_msg in enumerate(store_messages, 1):
            store_name = store_msg.get('store_name', f'판매자{i}')
            message = store_msg.get('message', '메시지 없음')
            
            self.log(f"[{i}/{len(store_messages)}] 📤 {store_name}", LOG_INFO)
            self.log("-" * 40, LOG_INFO)
            self.log(f"제목: [출고 요청-{store_name}]", LOG_INFO)
            self.log("메시지 내용:", LOG_INFO)
            self.log("┌" + "─" * 50 + "┐", LOG_INFO)
            
            # 메시지 내용을 줄별로 출력
            message_lines = message.strip().split('\n')
            for line in message_lines:
                if line.strip():
                    # 전체 메시지를 모두 표시
                    self.log(f"│ {line.strip()}", LOG_INFO)
                else:
                    self.log("│", LOG_INFO)
            
            self.log("└" + "─" * 50 + "┘", LOG_INFO)
            self.log("", LOG_INFO)  # 빈 줄
        
        self.log("=" * 60, LOG_INFO)
        self.log("📱 카카오톡 메시지 로그 완료", LOG_SUCCESS)
    
    def _update_item_status(self, item_ids: List[int], status: str, set_processed_time: bool = False):
        """항목 상태 업데이트 콜백"""
        try:
            # 데이터 매니저를 통해 상태 업데이트
            self.data_manager.update_item_status(item_ids, status, set_processed_time)
            
            # 테이블 업데이트
            processed_at_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S') if set_processed_time else None
            self.table.update_status(item_ids, status, processed_at_str)
            
            # 통계 실시간 갱신
            self._update_all_statistics()
            
            # UI 업데이트를 위한 이벤트 처리
            QApplication.processEvents()
        except Exception as e:
            error_msg = f"상태 업데이트 중 오류: {str(e)}\n{traceback.format_exc()}"
            self.log(error_msg, LOG_ERROR)
            QMessageBox.critical(self, "상태 업데이트 오류", error_msg)
    
    def _purchase_product_to_dict(self, item: PurchaseProduct) -> Dict[str, Any]:
        """PurchaseProduct 객체를 딕셔너리로 변환"""
        return {
            'id': item.id,
            'image_url': getattr(item, 'image_url', None),
            'print_url': getattr(item, 'print_url', None),
            'store_name': item.store_name,
            'store_url': getattr(item, 'store_url', None),
            'store_address': item.store_address,
            'store_ddm_address': item.store_ddm_address,
            'quality_code': getattr(item, 'quality_code', None),
            'quality_name': item.quality_name,
            'quality_url': getattr(item, 'quality_url', None),
            'swatch_pickupable': getattr(item, 'swatch_pickupable', None),
            'swatch_storage': getattr(item, 'swatch_storage', None),
            'color_number': item.color_number,
            'color_code': item.color_code,
            'quantity': item.quantity,
            'order_code': getattr(item, 'order_code', None),
            'order_url': getattr(item, 'order_url', None),
            'purchase_code': item.purchase_code,
            'purchase_url': getattr(item, 'purchase_url', None),
            'last_pickup_at': item.last_pickup_at.isoformat() if getattr(item, 'last_pickup_at', None) and hasattr(item.last_pickup_at, 'isoformat') else (str(item.last_pickup_at) if getattr(item, 'last_pickup_at', None) else None),
            'pickup_at': item.pickup_at.isoformat() if hasattr(item.pickup_at, 'isoformat') else str(item.pickup_at),
            'delivery_method': item.delivery_method,
            'logistics_company': item.logistics_company,
            'status': item.status,
            'message_status': getattr(item, 'message_status', '대기중'),
            'processed_at': item.processed_at.isoformat() if item.processed_at and hasattr(item.processed_at, 'isoformat') else (str(item.processed_at) if item.processed_at else None)
        }
    
    def _update_all_statistics(self):
        """모든 통계 정보 업데이트"""
        # 기본 메시지 상태 통계
        stats = self.data_manager.get_statistics()
        self.statistics_widget.update_statistics(stats)
        
        # 추가 통계 계산
        all_data = self.data_manager.get_all_data()
        filtered_data = self.data_manager.get_filtered_data()
        
        if filtered_data:
            # 프로덕트 수
            product_count = len(filtered_data)
            self.statistics_widget.update_single_statistic("product_count", product_count)
            
            # 판매자 수
            store_count = len(set(item.store_name for item in filtered_data))
            self.statistics_widget.update_single_statistic("store_count", store_count)
            
            # 총 수량
            total_quantity = sum(int(item.quantity) if not isinstance(item.quantity, int) and str(item.quantity).isdigit() else item.quantity for item in filtered_data)
            self.statistics_widget.update_single_statistic("total_quantity", total_quantity)
            
            # 동대문 픽업
            quick_pickup_count = len([item for item in filtered_data if item.delivery_method == "quick"])
            self.statistics_widget.update_single_statistic("quick_pickup", quick_pickup_count)
            
            # 판매자 발송
            logistics_count = len([item for item in filtered_data if item.delivery_method == "logistics"])
            self.statistics_widget.update_single_statistic("logistics", logistics_count)
        
        # 통계 레이블 업데이트
        if all_data:
            pending_count = stats.get('pending', 0)
            sending_count = stats.get('sending', 0)
            sent_count = stats.get('sent', 0)
            failed_count = stats.get('failed', 0)
            cancelled_count = stats.get('cancelled', 0)
            
            self.stats_label.setText(
                f"전체 {len(all_data)}건 / 대기중 {pending_count}건 / 전송중 {sending_count}건 / "
                f"전송완료 {sent_count}건 / 실패 {failed_count}건 / 취소 {cancelled_count}건 / "
                f"필터링 {len(filtered_data)}건"
            )
        else:
            self.stats_label.setText("총 0건")
    
    def _reset_send_button_state(self):
        """전송 버튼 상태 초기화"""
        try:
            self.send_button.setEnabled(False)
            self.message_log_button.setEnabled(False)
            self.send_button.setText("💌 메시지 전송")
            self.emergency_stop_button.setEnabled(False)
            self.preview_button.setText("📋 메시지 미리보기")
            self.message_manager.clear_preview_data()
        except Exception as e:
            error_msg = f"버튼 상태 초기화 중 오류: {str(e)}\n{traceback.format_exc()}"
            self.log(error_msg, LOG_ERROR)
            QMessageBox.critical(self, "오류", error_msg)
    
    def on_section_activated(self):
        """섹션이 활성화될 때 호출"""
        self.log("FBO 출고 요청 섹션이 활성화되었습니다.", LOG_INFO)
        
        # 데이터가 없는 경우에만 안내 메시지 표시
        if not self.data_manager.get_all_data():
            self.log("'새로고침' 버튼을 클릭하여 출고 요청 데이터를 가져오세요.", LOG_INFO)
    
    def on_section_deactivated(self):
        """섹션이 비활성화될 때 호출"""
        # 전송 중인 경우 중단
        if self.message_manager.is_sending():
            self.message_manager.emergency_stop() 