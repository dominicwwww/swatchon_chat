"""
FBO 출고 요청 섹션 - 컴포넌트 기반 리팩토링 버전
"""
from typing import List, Dict, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFrame, QMessageBox, QApplication
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont
import os
from datetime import datetime

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
        self.emergency_stop_button.setEnabled(False)
        
        # UI 설정
        self.setup_content()
        
        # 선택된 항목 추적
        self._selected_items: List[PurchaseProduct] = []
    
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
        self.table = ShipmentRequestTable()
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
        self.preview_button.setText("📋 미리보기 완료")
        self.log("💡 '메시지 전송' 버튼을 클릭하여 실제 전송하거나, 다른 항목을 선택하여 새로운 미리보기를 생성하세요.", LOG_INFO)
    
    def _on_message_sent(self, result: Dict[str, Any]):
        """메시지 전송 완료 이벤트"""
        success_count = result.get('success_count', 0)
        fail_count = result.get('fail_count', 0)
        cancelled_count = result.get('cancelled_count', 0)
        emergency_stop = result.get('emergency_stop', False)
        
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
        # 선택된 항목의 ID를 기반으로 완전한 데이터 찾기
        complete_selected_items = []
        
        for selected_item in selected_items:
            # 선택된 항목의 ID 가져오기
            selected_id = selected_item.get('id')
            
            if selected_id:
                # filtered_data에서 해당 ID의 완전한 PurchaseProduct 객체 찾기
                for complete_item in self.data_manager.get_filtered_data():
                    if complete_item.id == selected_id:
                        complete_selected_items.append(complete_item)
                        break
        
        # 완전한 데이터로 선택된 항목 저장
        self._selected_items = complete_selected_items
        
        # 버튼 상태 업데이트
        has_selection = len(complete_selected_items) > 0
        self.preview_button.setEnabled(has_selection)
        
        if has_selection:
            # 전체 선택인 경우 (테이블의 모든 행이 선택된 경우)
            if len(complete_selected_items) == self.table.rowCount():
                self.log(f"전체 {len(complete_selected_items)}개 항목이 선택되었습니다.", LOG_INFO)
            else:
                self.log(f"{len(complete_selected_items)}개 항목이 선택되었습니다.", LOG_INFO)
            
            # 미리보기 상태 초기화
            self.send_button.setEnabled(False)
            self.preview_button.setText("📋 메시지 미리보기")
            self.message_manager.clear_preview_data()
        else:
            self.log("선택된 항목이 없습니다.", LOG_INFO)
            self.send_button.setEnabled(False)
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
        """미리보기 버튼 클릭 이벤트"""
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
            # 버튼 상태 변경
            self.send_button.setEnabled(False)
            self.send_button.setText("전송 중...")
            self.emergency_stop_button.setEnabled(True)
            
            # 메시지 전송
            self.message_manager.send_messages(
                update_status_callback=self._update_item_status
            )
    
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
    
    def _update_item_status(self, item_ids: List[int], status: str, set_processed_time: bool = False):
        """항목 상태 업데이트 콜백"""
        # 데이터 매니저를 통해 상태 업데이트
        self.data_manager.update_item_status(item_ids, status, set_processed_time)
        
        # 테이블 업데이트
        processed_at_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S') if set_processed_time else None
        self.table.update_status(item_ids, status, processed_at_str)
    
    def _purchase_product_to_dict(self, item: PurchaseProduct) -> Dict[str, Any]:
        """PurchaseProduct 객체를 딕셔너리로 변환"""
        return {
            'id': item.id,
            'store_name': item.store_name,
            'store_address': item.store_address,
            'store_ddm_address': item.store_ddm_address,
            'quality_name': item.quality_name,
            'color_number': item.color_number,
            'color_code': item.color_code,
            'quantity': item.quantity,
            'purchase_code': item.purchase_code,
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
            total_quantity = sum(item.quantity for item in filtered_data)
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
        self.send_button.setEnabled(False)
        self.send_button.setText("💌 메시지 전송")
        self.emergency_stop_button.setEnabled(False)
        self.preview_button.setText("📋 메시지 미리보기")
        self.message_manager.clear_preview_data()
    
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