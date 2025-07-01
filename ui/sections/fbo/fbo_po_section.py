"""
FBO 발주 확인 요청 섹션 - 발주 확인 요청 기능
"""
from typing import List, Dict, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, QComboBox, QMessageBox
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QColor

from core.types import LogType, OrderType, ShipmentStatus, FboOperationType
from core.constants import MESSAGE_STATUS_LABELS
from ui.sections.base_section import BaseSection
from ui.components.message_section_mixin import MessageSectionMixin
from ui.theme import get_theme
from ui.components.fbo_po_table import FboPoTable
from ui.components.log_widget import LOG_INFO, LOG_DEBUG, LOG_WARNING, LOG_ERROR, LOG_SUCCESS
from core.schemas import PurchaseConfirm
from ui.components.statistics_widget import StatisticsWidget
import traceback
from datetime import datetime

class FboPoApiThread(QThread):
    """FBO 발주 확인 API 로드 스레드 - 비동기 처리"""
    
    # 시그널 정의
    log_signal = Signal(str, str)  # (메시지, 로그타입)
    data_loaded = Signal(list, dict)    # 로드 완료된 데이터 (발주 데이터, 프로덕트 데이터)
    loading_finished = Signal()   # 로딩 종료
    loading_error = Signal(str)   # 로딩 오류
    
    def __init__(self):
        super().__init__()
        self.loaded_data = []
        self.loaded_products = {}
    
    def run(self):
        """API에서 FBO 발주 확인 데이터 로드"""
        try:
            self._log_to_signal("발주 확인 요청 데이터를 API에서 로드합니다...")
            
            # DataManager를 사용하여 API 데이터 로드
            from ui.components.data_manager import DataManager
            data_manager = DataManager(OrderType.FBO, log_function=self._log_to_signal)
            success = data_manager.load_purchase_confirms_from_api()
            
            if success:
                purchase_confirms = data_manager.get_all_data()
                self._log_to_signal(f"FBO 발주 확인 데이터 {len(purchase_confirms)}건을 API에서 로드했습니다.", LOG_SUCCESS)
                
                # 데이터를 저장 (flat 구조로)
                file_path = data_manager.save_purchase_confirms(purchase_confirms)
                if file_path:
                    self._log_to_signal(f"FBO 발주 확인 데이터를 저장했습니다: {file_path}", LOG_SUCCESS)
                
                # status가 'requested'인 항목만 필터링하여 직접 전달
                table_data = []
                for confirm in purchase_confirms:
                    if isinstance(confirm, PurchaseConfirm):
                        # status가 'requested'인 항목만 처리
                        if confirm.status != 'requested':
                            continue
                        
                        # flat 구조로 저장된 JSON을 다시 로드하여 테이블에 전달
                        # (DataManager에서 이미 flat 구조로 저장했으므로)
                        pass
                
                # 저장된 JSON 파일에서 직접 로드
                import json
                import os
                import glob
                from datetime import datetime

                # 최신 JSON 파일 찾기
                project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
                data_dir = os.path.join(project_root, 'data', 'api_cache')

                # 오늘 날짜 파일들 확인
                today = datetime.now().strftime('%y%m%d')
                json_files = glob.glob(os.path.join(data_dir, f'fbo_po_confirm_{today}-*.json'))

                if not json_files:
                    # 오늘 파일이 없으면 가장 최신 파일 찾기
                    json_files = glob.glob(os.path.join(data_dir, 'fbo_po_confirm_*.json'))

                if json_files:
                    # 가장 최신 파일 사용
                    latest_file = max(json_files, key=os.path.getmtime)

                    with open(latest_file, 'r', encoding='utf-8') as f:
                        flat_data = json.load(f)

                    # status가 'requested' 또는 '발주요청중'인 것만 필터
                    table_data = []
                    for row in flat_data:
                        if row.get('status') in ('requested', '발주요청중'):
                            table_data.append(row)

                    self.data_loaded.emit(table_data, {})
                else:
                    self._log_to_signal("발주 확인 데이터 파일을 찾을 수 없습니다.", LOG_WARNING)
                    self.data_loaded.emit([], {})
            else:
                self._log_to_signal("API에서 데이터를 받아오지 못했습니다.", LOG_ERROR)
                self.loading_error.emit("API 연결 실패")
                
        except Exception as e:
            error_msg = f"API 로드 중 오류: {str(e)}"
            self._log_to_signal(error_msg, LOG_ERROR)
            self.loading_error.emit(error_msg)
        finally:
            self.loading_finished.emit()
    
    def _log_to_signal(self, message, log_type=LOG_INFO):
        """로그 메시지를 시그널로 전송"""
        self.log_signal.emit(message, log_type)


class FboPoSection(BaseSection, MessageSectionMixin):
    """
    FBO 발주 확인 요청 섹션 - 발주 확인 요청 관련 기능
    MessageSectionMixin을 사용하여 공통 기능 활용
    """
    def __init__(self, parent=None):
        super().__init__("FBO 발주 확인", parent)
        
        # 공통 메시지 컴포넌트 설정 (미리보기 기능 활성화)
        self.setup_message_components(
            order_type=OrderType.FBO,
            operation_type=FboOperationType.PO,
            enable_preview_features=True,  # 미리보기 기능 활성화
            enable_emergency_stop=True
        )
        
        # 기존 통계 위젯 교체 - 2행 레이아웃 사용
        self.statistics_widget = StatisticsWidget(use_two_rows=True)
        
        # API 스레드 초기화
        self.api_thread = None
        
        # 프로덕트 데이터 저장소
        self.products_data = {}
        
        # 스크래핑 스레드 초기화
        self.scraping_thread = FboPoApiThread()
        self.scraping_thread.log_signal.connect(self._on_scraping_log)
        self.scraping_thread.data_loaded.connect(self._on_data_loaded)
        self.scraping_thread.loading_finished.connect(self._on_loading_finished)
        self.scraping_thread.loading_error.connect(self._on_loading_error)
        
        # 프로덕트 데이터 저장소 (JSON에서 로드)
        self.all_products_data = {}
        
        self.setup_content()
    
    def setup_content(self):
        # 필터 위젯만 먼저 추가
        self.content_layout.addWidget(self.filter_widget)
        
        # 테이블
        self.table = FboPoTable(log_function=self.log)
        
        # 프로덕트 표시 요청 시그널 연결 - JSON에서 로드하도록 변경
        self.table.product_show_requested.connect(self._on_product_show_requested)
        
        # selection_label을 테이블 상단에 추가
        table_top_widget = QWidget()
        table_top_layout = QHBoxLayout(table_top_widget)
        table_top_layout.setContentsMargins(0, 0, 0, 8)
        table_top_layout.addWidget(self.table.selection_label)
        table_top_layout.addStretch()
        self.content_layout.addWidget(table_top_widget)
        self.content_layout.addWidget(self.table)
        
        # 통계 위젯을 테이블 아래에 추가
        self.content_layout.addWidget(self.statistics_widget)
        
        # 시그널 연결
        self.table.selection_changed.connect(self._on_table_selection_changed)
        
        # 통계/선택 버튼 영역
        stats_widget = QWidget()
        stats_layout = QHBoxLayout(stats_widget)
        stats_layout.setContentsMargins(0, 8, 0, 0)
        self.stats_label = QLabel("총 0건")
        stats_layout.addWidget(self.stats_label)
        stats_layout.addStretch()
        self.select_all_button = QPushButton("모두 선택")
        self.select_all_button.clicked.connect(self.table.select_all)
        self.deselect_all_button = QPushButton("모두 해제")
        self.deselect_all_button.clicked.connect(self.table.clear_selection)
        stats_layout.addWidget(self.select_all_button)
        stats_layout.addWidget(self.deselect_all_button)
        self.content_layout.addWidget(stats_widget)
        
        # 추가 통계 카드 설정
        self._setup_additional_statistics()
        
        # 데이터 로드
        self._load_existing_data()
    
    def _setup_additional_statistics(self):
        """FBO 발주 확인에 특화된 통계 카드들 설정 - 2행에 배치"""
        self.statistics_widget.add_custom_card("purchase_count", "발주 건수", "info", 0, row=2)
        self.statistics_widget.add_custom_card("store_count", "판매자 수", "primary", 0, row=2)
        self.statistics_widget.add_custom_card("bulk_orders", "벌크 주문", "success", 0, row=2)
        self.statistics_widget.add_custom_card("sample_orders", "샘플 주문", "warning", 0, row=2)
        self.statistics_widget.add_custom_card("total_quantity", "총 수량", "secondary", 0, row=2)
        self.statistics_widget.add_custom_card("avg_quantity", "평균 수량", "secondary", 0, row=2)
        self.statistics_widget.add_custom_card("swatch_pickup_no", "스와치픽업 X", "error", 0, row=2)
    
    def _load_existing_data(self):
        """기존 JSON 데이터 로드 (flat product 구조)"""
        try:
            import json
            import os
            import glob
            from datetime import datetime

            # 최신 JSON 파일 찾기
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            data_dir = os.path.join(project_root, 'data', 'api_cache')

            # 오늘 날짜 파일들 확인
            today = datetime.now().strftime('%y%m%d')
            json_files = glob.glob(os.path.join(data_dir, f'fbo_po_confirm_{today}-*.json'))

            if not json_files:
                # 오늘 파일이 없으면 가장 최신 파일 찾기
                json_files = glob.glob(os.path.join(data_dir, 'fbo_po_confirm_*.json'))

            if json_files:
                # 가장 최신 파일 사용
                latest_file = max(json_files, key=os.path.getmtime)

                with open(latest_file, 'r', encoding='utf-8') as f:
                    flat_data = json.load(f)

                # status가 'requested' 또는 '발주요청중'인 것만 필터
                table_data = []
                for row in flat_data:
                    if row.get('status') in ('requested', '발주요청중'):
                        # message_status 한글 매핑 적용
                        row['message_status'] = self._map_message_status_to_korean(row.get('message_status', '대기중'))
                        table_data.append(row)

                self.table.update_data(table_data)
                self.stats_label.setText(f"총 {len(table_data)}건")
                self._update_all_statistics(table_data)
                self.log(f"발주 확인 flat 데이터 {len(table_data)}건을 로드했습니다. ({os.path.basename(latest_file)})", LOG_SUCCESS)
            else:
                self.log("발주 확인 데이터 파일을 찾을 수 없습니다. 새로고침을 눌러 데이터를 스크래핑하세요.", LOG_WARNING)
        except Exception as e:
            self.log(f"발주 확인 데이터 로드 중 오류: {str(e)}", LOG_ERROR)

    # MessageSectionMixin 오버라이드 메서드들
    def _on_refresh_clicked(self):
        """새로고침 버튼 클릭 - 비동기 스크래핑 시작 (발주+프로덕트 함께)"""
        if self.scraping_thread.isRunning():
            self.log("이미 스크래핑이 진행 중입니다.", LogType.WARNING.value)
            return
        
        # 버튼 비활성화
        self.refresh_button.setEnabled(False)
        self.refresh_button.setText("스크래핑 중...")
        
        # 스크래핑 스레드 시작
        self.scraping_thread.start()

    def _on_data_loaded(self, table_data, products_data):
        """API 데이터 로드 완료 처리"""
        try:
            self.log(f"테이블 데이터 {len(table_data)}건 수신", LOG_INFO)
            self.log(f"프로덕트 데이터 {len(products_data)}건 수신", LOG_INFO)
            
            # 프로덕트 데이터 저장
            self.products_data = products_data
            
            # 테이블 업데이트 - 데이터가 있는지 확인
            if table_data:
                # message_status 한글 매핑 적용
                for row in table_data:
                    row['message_status'] = self._map_message_status_to_korean(row.get('message_status', '대기중'))
                
                self.table.update_data(table_data)
                self.stats_label.setText(f"총 {len(table_data)}건")
                self._update_all_statistics(table_data)
                self.log(f"테이블 업데이트 완료: {len(table_data)}건", LOG_SUCCESS)
            else:
                self.log("로드된 테이블 데이터가 없습니다", LOG_WARNING)
                self.table.clear_table()
                self.stats_label.setText("총 0건")
                self._update_all_statistics([])
            
            # 통계 업데이트
            self.log(f"발주 확인 데이터 {len(table_data)}건, 프로덕트 데이터 {len(products_data)}건을 로드했습니다.", LOG_SUCCESS)
            
        except Exception as e:
            self.log(f"데이터 로드 처리 중 오류: {str(e)}", LOG_ERROR)

    def _update_all_statistics(self, data: List[Dict] = None):
        """모든 통계 정보 업데이트"""
        if data is None:
            return
        
        try:
            # 기본 통계
            total_count = len(data)
            store_names = set(row.get('store_name', '') for row in data)
            total_quantity = sum(int(row.get('quantity', 0)) for row in data if row.get('quantity'))
            # 평균 수량 계산 (소수점 1자리)
            avg_quantity = round(total_quantity / total_count, 1) if total_count > 0 else 0
            # 스와치픽업 불가능한 항목 카운트 (N 또는 빈 값, false)
            swatch_pickup_no_count = sum(1 for row in data if row.get('swatch_pickupable') in ('N', '', None, False))
            
            # 주문코드 접두어별 분류
            bulk_orders = sum(1 for row in data if str(row.get('order_code', '')).startswith('FB-'))
            sample_orders = sum(1 for row in data if str(row.get('order_code', '')).startswith('SP-'))
            
            # 통계 카드 업데이트 - 올바른 메서드명 사용
            self.statistics_widget.update_single_statistic("purchase_count", total_count)
            self.statistics_widget.update_single_statistic("store_count", len(store_names))
            self.statistics_widget.update_single_statistic("bulk_orders", bulk_orders)
            self.statistics_widget.update_single_statistic("sample_orders", sample_orders)
            self.statistics_widget.update_single_statistic("total_quantity", total_quantity)
            self.statistics_widget.update_single_statistic("avg_quantity", avg_quantity)
            self.statistics_widget.update_single_statistic("swatch_pickup_no", swatch_pickup_no_count)
            
            # 상태별 통계
            status_stats = {}
            for row in data:
                status = row.get('message_status', '대기중')
                status_stats[status] = status_stats.get(status, 0) + 1
            
            # 기본 상태 카드 업데이트 - 올바른 메서드명 사용
            pending_count = status_stats.get('대기중', 0)
            sent_count = status_stats.get('전송완료', 0)
            failed_count = status_stats.get('전송실패', 0)
            
            self.statistics_widget.update_single_statistic("pending", pending_count)
            self.statistics_widget.update_single_statistic("sent", sent_count)
            self.statistics_widget.update_single_statistic("failed", failed_count)
            self.statistics_widget.update_single_statistic("total", total_count)
            
        except Exception as e:
            self.log(f"통계 업데이트 중 오류: {str(e)}", LOG_ERROR)

    def _convert_item_to_dict(self, item) -> Dict[str, Any]:
        """아이템을 딕셔너리로 변환 (MessageSectionMixin 인터페이스 구현)"""
        if isinstance(item, dict):
            return item
        else:
            # 다른 타입의 경우 적절히 변환
            return {"id": getattr(item, 'id', ''), "store_name": getattr(item, 'store_name', '')}

    def _update_item_status(self, item_ids: List[int], status: str, set_processed_time: bool = False):
        """항목 상태 업데이트 콜백"""
        # 처리시각 설정
        processed_at_str = None
        if set_processed_time:
            from datetime import datetime
            processed_at_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 테이블에서 해당 항목들의 상태 업데이트
        for item_id in item_ids:
            self.table.update_item_status(str(item_id), status, processed_at_str)
        
        # 통계 재계산
        current_data = self.table.get_all_data()
        self._update_all_statistics(current_data)

    def _on_product_show_requested(self, purchase_code: str):
        # flat 구조에서는 별도 product 표시 기능이 필요 없음 (구현 생략)
        pass

    def _on_scraping_log(self, message, log_type):
        """스크래핑 스레드에서 온 로그 메시지 처리"""
        self.log(message, log_type)

    def _on_loading_finished(self):
        """스크래핑 완료 후 UI 복원"""
        self.refresh_button.setEnabled(True)
        self.refresh_button.setText("새로고침")

    def _on_loading_error(self, error_message):
        """스크래핑 오류 처리"""
        self.log(error_message, LogType.ERROR.value)
    
    def _on_table_selection_changed(self, selected_items):
        """테이블 선택 변경 이벤트"""
        self._selected_items = selected_items
        
        # 버튼 상태 업데이트
        has_selection = len(selected_items) > 0
        
        if hasattr(self, 'preview_button'):
            self.preview_button.setEnabled(has_selection)
        
        if has_selection:
            self.log(f"{len(selected_items)}개 항목이 선택되었습니다.", LOG_INFO)
            
            # 미리보기 상태 초기화
            self.send_button.setEnabled(False)
            if hasattr(self, 'preview_button'):
                self.preview_button.setText("📋 메시지 미리보기")
            if hasattr(self, 'message_manager'):
                self.message_manager.clear_preview_data()
            self._preview_ready = False
        else:
            self.log("선택된 항목이 없습니다.", LOG_INFO)
            self.send_button.setEnabled(False)
            if hasattr(self, 'preview_button'):
                self.preview_button.setText("📋 메시지 미리보기")
    
    def on_section_activated(self):
        self.log("FBO 발주 확인 요청 섹션이 활성화되었습니다.", LogType.INFO.value)
    
    def on_section_deactivated(self):
        # 스크래핑 스레드 중단
        if self.scraping_thread.isRunning():
            self.scraping_thread.quit()
            self.scraping_thread.wait(3000)  # 3초 대기 
        
        # 메시지 전송 중단
        self.emergency_stop_all_sending()

    def _map_message_status_to_korean(self, status: str) -> str:
        """메시지 상태를 한글로 매핑"""
        return MESSAGE_STATUS_LABELS.get(status, status)

    def _on_message_sent(self, result):
        """메시지 전송 완료 이벤트 - FBO 발주 확인 섹션 전용 구현"""
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
            
            # 통계 업데이트 (현재 테이블 데이터 기준)
            current_data = self.table.get_all_data()
            self._update_all_statistics(current_data)
            
            # 테이블 데이터는 초기화하지 않고 현재 상태 유지
            # (상태 업데이트는 _update_item_status 콜백에서 이미 처리됨)
            
            # 버튼 상태 초기화
            self._reset_send_button_state()
            
        except Exception as e:
            error_msg = f"전송 완료 처리 중 오류 발생: {str(e)}\n{traceback.format_exc()}"
            self.log(error_msg, LOG_ERROR)
            QMessageBox.critical(self, "오류", error_msg)
            self._reset_send_button_state() 