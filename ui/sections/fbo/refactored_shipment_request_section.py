"""
FBO 출고 요청 섹션 - 리팩토링된 버전 (컴포넌트 활용)
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

from core.types import OrderType, FboOperationType, ShipmentStatus
from ui.sections.base_section import BaseSection
from ui.theme import get_theme
from ui.components.log_widget import LOG_INFO, LOG_DEBUG, LOG_WARNING, LOG_ERROR, LOG_SUCCESS
from ui.components.shipment_request_table import ShipmentRequestTable
from ui.components.message_manager import MessageManager
from ui.components.data_manager import DataManager
from ui.components.statistics_widget import StatisticsWidget
from ui.components.filter_widget import FilterWidget
from core.schemas import PurchaseProduct


class RefactoredShipmentRequestSection(BaseSection):
    """
    FBO 출고 요청 섹션 - 리팩토링된 버전
    
    기존 1100줄의 코드를 재사용 가능한 컴포넌트로 분리하여 모듈화
    """
    
    def __init__(self, parent=None):
        super().__init__("FBO 출고 요청 (리팩토링됨)", parent)
        
        # 데이터 디렉토리 설정
        self.data_dir = "ui/data"
        os.makedirs(self.data_dir, exist_ok=True)
        
        # 컴포넌트 초기화
        self.setup_components()
        
        # 헤더 버튼 추가
        self.refresh_button = self.add_header_button("새로고침", self._on_refresh_clicked)
        self.load_saved_button = self.add_header_button("저장된 데이터", self._on_load_saved_clicked)
        self.preview_button = self.add_header_button("미리보기", self._on_preview_clicked)
        self.send_button = self.add_header_button("메시지 전송", self._on_send_clicked, primary=True)
        self.emergency_stop_button = self.add_header_button("긴급 정지", self._on_emergency_stop_clicked)
        self.emergency_stop_button.setEnabled(False)
        
        # UI 설정
        self.setup_content()
        
        # 선택된 항목 추적
        self._selected_items: List[PurchaseProduct] = []
    
    def setup_components(self):
        """컴포넌트 초기화 및 연결"""
        # 데이터 매니저
        self.data_manager = DataManager(
            order_type=OrderType.FBO,
            data_dir=self.data_dir,
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
    
    def _on_data_loaded(self, data: List[PurchaseProduct]):
        """데이터 로드 완료 이벤트"""
        self.log(f"총 {len(data)}건의 데이터가 로드되었습니다.", LOG_SUCCESS)
        
        # 테이블 업데이트
        self.table.update_data(data)
        
        # 통계 업데이트
        stats = self.data_manager.get_statistics()
        self.statistics_widget.update_statistics(stats)
    
    def _on_data_filtered(self, filtered_data: List[PurchaseProduct]):
        """데이터 필터링 완료 이벤트"""
        self.log(f"필터링 결과: {len(filtered_data)}건", LOG_INFO)
        
        # 테이블 업데이트
        self.table.update_data(filtered_data)
    
    def _on_error_occurred(self, error_message: str):
        """오류 발생 이벤트"""
        self.log(f"오류 발생: {error_message}", LOG_ERROR)
        QMessageBox.critical(self, "오류", error_message)
    
    def _on_message_preview_generated(self, preview_data: Dict[str, Any]):
        """메시지 미리보기 생성 완료 이벤트"""
        self.log("메시지 미리보기가 생성되었습니다.", LOG_SUCCESS)
        self.send_button.setEnabled(True)
        self.preview_button.setText("미리보기 완료")
    
    def _on_message_sent(self, result: Dict[str, Any]):
        """메시지 전송 완료 이벤트"""
        success_count = result.get('success_count', 0)
        fail_count = result.get('fail_count', 0)
        
        self.log(f"메시지 전송 완료: 성공 {success_count}건, 실패 {fail_count}건", LOG_SUCCESS)
        
        # 통계 업데이트
        stats = self.data_manager.get_statistics()
        self.statistics_widget.update_statistics(stats)
        
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
    
    def _on_table_selection_changed(self, selected_items: List[PurchaseProduct]):
        """테이블 선택 변경 이벤트"""
        self._selected_items = selected_items
        
        # 버튼 상태 업데이트
        has_selection = len(selected_items) > 0
        self.preview_button.setEnabled(has_selection)
        
        if has_selection:
            self.log(f"{len(selected_items)}개 항목이 선택되었습니다.", LOG_INFO)
            # 미리보기 상태 초기화
            self.send_button.setEnabled(False)
            self.preview_button.setText("미리보기")
            self.message_manager.clear_preview_data()
        else:
            self.send_button.setEnabled(False)
            self.preview_button.setText("미리보기")
    
    def _on_refresh_clicked(self):
        """새로고침 버튼 클릭 이벤트"""
        success = self.data_manager.load_data_from_api()
        if not success:
            QMessageBox.warning(self, "API 오류", "API에서 데이터를 받아오지 못했습니다.")
    
    def _on_load_saved_clicked(self):
        """저장된 데이터 불러오기 버튼 클릭 이벤트"""
        success = self.data_manager.load_saved_data()
        if success:
            QTimer.singleShot(0, lambda: QMessageBox.information(
                self, "불러오기 완료", "저장된 데이터를 성공적으로 불러왔습니다."
            ))
        else:
            QTimer.singleShot(0, lambda: QMessageBox.warning(
                self, "불러오기 실패", "불러올 데이터 파일이 없습니다."
            ))
    
    def _on_preview_clicked(self):
        """미리보기 버튼 클릭 이벤트"""
        if not self._selected_items:
            QMessageBox.warning(self, "선택 오류", "선택된 항목이 없습니다.")
            return
        
        # 중복 전송 검증
        duplicate_check = self.message_manager.check_duplicate_sending(
            [self._purchase_product_to_dict(item) for item in self._selected_items],
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
        selected_items_dict = [self._purchase_product_to_dict(item) for item in self._selected_items]
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
        
        # 통계 업데이트
        stats = self.data_manager.get_statistics()
        self.statistics_widget.update_statistics(stats)
    
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
    
    def _reset_send_button_state(self):
        """전송 버튼 상태 초기화"""
        self.send_button.setEnabled(False)
        self.send_button.setText("메시지 전송")
        self.emergency_stop_button.setEnabled(False)
        self.preview_button.setText("미리보기")
        self.message_manager.clear_preview_data()
    
    def on_section_activated(self):
        """섹션이 활성화될 때 호출"""
        self.log("FBO 출고 요청 섹션 (리팩토링됨)이 활성화되었습니다.", LOG_INFO)
        
        # 데이터가 없는 경우에만 안내 메시지 표시
        if not self.data_manager.get_all_data():
            self.log("'새로고침' 버튼을 클릭하여 출고 요청 데이터를 가져오세요.", LOG_INFO)
    
    def on_section_deactivated(self):
        """섹션이 비활성화될 때 호출"""
        # 전송 중인 경우 중단
        if self.message_manager.is_sending():
            self.message_manager.emergency_stop() 