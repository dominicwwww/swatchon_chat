"""
메시지 섹션 믹스인 - 메시지 전송 기능이 있는 섹션들의 공통 기능 모듈화
"""
from typing import List, Dict, Any, Optional, Callable
from abc import ABC, abstractmethod
from PySide6.QtWidgets import QMessageBox, QPushButton
from PySide6.QtCore import QObject, Signal

from core.types import OrderType
from ui.components.message_manager import MessageManager
from ui.components.data_manager import DataManager
from ui.components.statistics_widget import StatisticsWidget
from ui.components.filter_widget import FilterWidget
from ui.components.log_widget import LOG_INFO, LOG_SUCCESS, LOG_WARNING, LOG_ERROR
from services.address_book_service import AddressBookService
from datetime import datetime
import traceback


class MessageSectionMixin:
    """
    메시지 전송 기능이 있는 섹션들의 공통 기능을 제공하는 Mixin
    
    포함 기능:
    - 통계 카드 UI
    - 새로고침, 주소록 새로고침, 미리보기, 전송, 긴급정지 버튼
    - 메시지 매니저, 데이터 매니저 통합
    - 공통 이벤트 핸들러
    """
    
    def setup_message_components(self, order_type: OrderType, operation_type, 
                                enable_preview_features: bool = True,
                                enable_emergency_stop: bool = True,
                                use_two_row_statistics: bool = False):
        """
        메시지 관련 컴포넌트 초기화
        
        Args:
            order_type: 주문 유형 (FBO, SBO)
            operation_type: 작업 유형
            enable_preview_features: 미리보기 기능 활성화 여부
            enable_emergency_stop: 긴급정지 기능 활성화 여부
            use_two_row_statistics: 통계 위젯 2행 레이아웃 사용 여부
        """
        # 필수 속성 확인
        if not hasattr(self, 'log'):
            raise AttributeError("MessageSectionMixin을 사용하려면 'log' 메서드가 필요합니다.")
        if not hasattr(self, 'add_header_button'):
            raise AttributeError("MessageSectionMixin을 사용하려면 'add_header_button' 메서드가 필요합니다.")
        
        # 컴포넌트 초기화
        self.data_manager = DataManager(
            order_type=order_type,
            log_function=self.log
        )
        
        self.message_manager = MessageManager(
            order_type=order_type,
            operation_type=operation_type,
            log_function=self.log
        )
        
        # StatisticsWidget이 이미 생성되어 있지 않은 경우에만 생성
        if not hasattr(self, 'statistics_widget'):
            self.statistics_widget = StatisticsWidget(use_two_rows=use_two_row_statistics)
        self.filter_widget = FilterWidget()
        
        # 헤더 버튼 추가
        self.refresh_button = self.add_header_button("새로고침", self._on_refresh_clicked)
        self.refresh_address_button = self.add_header_button("주소록 새로고침", self._on_refresh_address_clicked)
        
        if enable_preview_features:
            self.preview_button = self.add_header_button("📋 메시지 미리보기", self._on_preview_clicked)
            self.send_button = self.add_header_button("💌 메시지 전송", self._on_send_clicked)
            self.send_button.setEnabled(False)
        else:
            self.send_button = self.add_header_button("💌 메시지 전송", self._on_send_clicked, primary=True)
        
        if enable_emergency_stop:
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
            self.emergency_stop_button.setEnabled(False)
        
        # 상태 변수 초기화
        self._selected_items = []
        if enable_preview_features:
            self._preview_ready = False
        
        # 시그널 연결
        self._connect_message_signals()
    
    def _connect_message_signals(self):
        """메시지 관련 시그널 연결"""
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
    
    def _on_refresh_clicked(self):
        """새로고침 버튼 클릭 이벤트 (API 연동)"""
        self.log("데이터를 API에서 새로고침합니다.", LOG_INFO)
        success = self.data_manager.load_data_from_api()
        if not success:
            QMessageBox.warning(self, "API 오류", "API에서 데이터를 받아오지 못했습니다.")
    
    def _on_refresh_address_clicked(self):
        """주소록 새로고침 버튼 클릭 이벤트"""
        try:
            self.log("주소록을 새로고침합니다.", LOG_INFO)
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
                    self.log(f"  {store_name} -> {chat_room}", LOG_INFO)
                if len(mappings) > sample_count:
                    self.log(f"  ... 외 {len(mappings) - sample_count}개", LOG_INFO)
            else:
                self.log("주소록 데이터가 없습니다.", LOG_WARNING)
        except Exception as e:
            self.log(f"주소록 새로고침 중 오류: {str(e)}", LOG_ERROR)
            QMessageBox.critical(self, "오류", f"주소록 새로고침 중 오류가 발생했습니다:\n{str(e)}")
    
    def _on_preview_clicked(self):
        """미리보기 버튼 클릭 이벤트"""
        if not hasattr(self, '_preview_ready') or not self._preview_ready:
            # 미리보기 생성
            if not self._selected_items:
                QMessageBox.warning(self, "선택 오류", "선택된 항목이 없습니다.")
                return
            
            # 중복 전송 검증
            selected_items_dict = [self._convert_item_to_dict(item) for item in self._selected_items]
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
        else:
            # 사용자 정의 미리보기 출력 (서브클래스에서 구현)
            if hasattr(self, '_handle_preview_output'):
                self._handle_preview_output()
    
    def _on_send_clicked(self):
        """메시지 전송 버튼 클릭 이벤트"""
        if hasattr(self, 'preview_button') and not self.message_manager.get_preview_data():
            QMessageBox.warning(self, "전송 오류", "먼저 미리보기를 생성해주세요.")
            return
        
        # 미리보기 기능이 없는 경우 직접 전송
        if not hasattr(self, 'preview_button'):
            if not self._selected_items:
                QMessageBox.warning(self, "선택 오류", "선택된 항목이 없습니다.")
                return
            
            selected_items_dict = [self._convert_item_to_dict(item) for item in self._selected_items]
            self.message_manager.generate_message_preview(selected_items_dict)
        
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
                if hasattr(self, 'emergency_stop_button'):
                    self.emergency_stop_button.setEnabled(True)
                
                # 메시지 전송 시작 전 로그
                self.log("\n=== 메시지 전송 시작 ===", LOG_INFO)
                self.log(f"선택된 항목 수: {len(self._selected_items)}", LOG_INFO)
                self.log(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", LOG_INFO)
                self.log("=" * 50, LOG_INFO)
                
                # 메시지 전송
                self.message_manager.send_messages(
                    update_status_callback=self._update_item_status
                )
                
            except Exception as e:
                error_msg = f"메시지 전송 중 오류: {str(e)}\n{traceback.format_exc()}"
                self.log(error_msg, LOG_ERROR)
                QMessageBox.critical(self, "전송 오류", f"메시지 전송 중 오류가 발생했습니다:\n{str(e)}")
                self._reset_send_button_state()
    
    def _on_emergency_stop_clicked(self):
        """긴급 정지 버튼 클릭 이벤트"""
        if not hasattr(self, 'emergency_stop_button') or not self.message_manager.is_sending():
            return
        
        reply = QMessageBox.question(
            self, "긴급 정지 확인", 
            "정말로 메시지 전송을 중단하시겠습니까?\n\n현재 전송 중인 메시지는 완료되고, 남은 메시지들은 취소됩니다.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.message_manager.emergency_stop()
            self.emergency_stop_button.setEnabled(False)
    
    def _on_data_loaded(self, data):
        """데이터 로드 완료 이벤트 - 서브클래스에서 오버라이드"""
        pass
    
    def _on_data_filtered(self, filtered_data):
        """데이터 필터링 완료 이벤트 - 서브클래스에서 오버라이드"""
        pass
    
    def _on_error_occurred(self, error_message: str):
        """오류 발생 이벤트"""
        self.log(f"오류 발생: {error_message}", LOG_ERROR)
        QMessageBox.critical(self, "오류", error_message)
    
    def _on_message_preview_generated(self, preview_data):
        """메시지 미리보기 생성 완료 이벤트"""
        self.log("메시지 미리보기가 생성되었습니다.", LOG_SUCCESS)
        if hasattr(self, 'send_button'):
            self.send_button.setEnabled(True)
        if hasattr(self, 'preview_button'):
            self.preview_button.setText("📋 메시지 미리보기")
            self._preview_ready = True
            self.log("💡 '메시지 전송' 버튼을 클릭하여 실제 전송하거나, 다른 항목을 선택하여 새로운 미리보기를 생성하세요.", LOG_INFO)
        
        # 서브클래스에서 추가 처리 가능
        if hasattr(self, '_handle_preview_generated'):
            self._handle_preview_generated(preview_data)
    
    def _on_message_sent(self, result):
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
            
            # 통계 및 테이블 업데이트 (서브클래스에서 구현)
            if hasattr(self, '_update_all_statistics'):
                self._update_all_statistics()
            if hasattr(self, 'table') and hasattr(self.table, 'update_data'):
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
        """통계 카드 클릭 이벤트 - 서브클래스에서 구체적 구현"""
        pass
    
    def _reset_send_button_state(self):
        """전송 버튼 상태 초기화"""
        try:
            self.send_button.setEnabled(False)
            self.send_button.setText("💌 메시지 전송")
            if hasattr(self, 'emergency_stop_button'):
                self.emergency_stop_button.setEnabled(False)
            if hasattr(self, 'preview_button'):
                self.preview_button.setText("📋 메시지 미리보기")
                self._preview_ready = False
            self.message_manager.clear_preview_data()
        except Exception as e:
            error_msg = f"버튼 상태 초기화 중 오류: {str(e)}\n{traceback.format_exc()}"
            self.log(error_msg, LOG_ERROR)
            QMessageBox.critical(self, "오류", error_msg)
    
    def _update_item_status(self, item_ids: List[int], status: str, set_processed_time: bool = False):
        """항목 상태 업데이트 콜백 - 서브클래스에서 구현"""
        pass
    
    @abstractmethod
    def _convert_item_to_dict(self, item) -> Dict[str, Any]:
        """아이템을 딕셔너리로 변환 - 서브클래스에서 구현"""
        pass
    
    def setup_message_content_layout(self):
        """메시지 섹션 기본 레이아웃 설정"""
        if not hasattr(self, 'content_layout'):
            raise AttributeError("content_layout이 필요합니다.")
        
        # 필터 영역
        self.content_layout.addWidget(self.filter_widget)
        
        # 통계 위젯
        self.content_layout.addWidget(self.statistics_widget)
    
    def emergency_stop_all_sending(self):
        """모든 전송 중단 (섹션 비활성화 시 호출)"""
        if hasattr(self, 'message_manager') and self.message_manager.is_sending():
            self.message_manager.emergency_stop() 