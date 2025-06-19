"""
FBO 발주 확인 요청 섹션 - 발주 확인 요청 기능
"""
from typing import List, Dict, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, QComboBox
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QColor

from core.types import LogType, OrderType
from ui.sections.base_section import BaseSection
from ui.theme import get_theme
from ui.components.fbo_po_table import FboPoTable
from ui.components.log_widget import LOG_INFO, LOG_DEBUG, LOG_WARNING, LOG_ERROR, LOG_SUCCESS
from ui.components.data_manager import DataManager

class FboPoScrapingThread(QThread):
    """FBO 발주 확인 스크래핑 스레드 - 비동기 처리"""
    
    # 시그널 정의
    log_signal = Signal(str, str)  # (메시지, 로그타입)
    data_scraped = Signal(list, dict)    # 스크래핑 완료된 데이터 (발주 데이터, 프로덕트 데이터)
    scraping_finished = Signal()   # 스크래핑 종료
    scraping_error = Signal(str)   # 스크래핑 오류
    
    def __init__(self):
        super().__init__()
        self.scraped_data = []
        self.scraped_products = {}
    
    def run(self):
        """스크래핑 실행 (별도 스레드에서) - 발주와 프로덕트 함께"""
        try:
            self.log_signal.emit("발주 확인 요청 데이터 스크래핑을 시작합니다...", LOG_INFO)
            
            from services.fbo_po_scraper import FboPoScraper
            import json, os, glob
            from datetime import datetime
            
            # 기존 오늘 날짜 파일 확인
            today = datetime.now().strftime('%y%m%d')
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            data_dir = os.path.join(project_root, 'data', 'api_cache')
            os.makedirs(data_dir, exist_ok=True)
            
            # 오늘 날짜의 기존 파일 찾기
            existing_files = glob.glob(os.path.join(data_dir, f'fbo_po_{today}-*.json'))
            existing_data = {}
            existing_file_path = None
            
            if existing_files:
                # 가장 최신 파일 사용
                existing_file_path = max(existing_files, key=os.path.getmtime)
                try:
                    with open(existing_file_path, 'r', encoding='utf-8') as f:
                        existing_list = json.load(f)
                        # purchase_code를 키로 하는 딕셔너리로 변환
                        for item in existing_list:
                            purchase_code = item.get('purchase_code')
                            if purchase_code:
                                existing_data[purchase_code] = item
                    self.log_signal.emit(f"기존 데이터 로드: {len(existing_data)}건 ({os.path.basename(existing_file_path)})", LOG_INFO)
                except Exception as e:
                    self.log_signal.emit(f"기존 데이터 로드 실패: {str(e)}", LOG_WARNING)
            
            # 발주 목록 스크래핑
            scraper = FboPoScraper()
            new_data = scraper.scrape_po_list()
            
            if new_data:
                # 데이터 비교 및 업데이트
                updated_count = 0
                new_count = 0
                unchanged_count = 0
                merged_data = existing_data.copy()  # 기존 데이터로 시작
                
                for new_item in new_data:
                    purchase_code = new_item.get('purchase_code')
                    if not purchase_code:
                        continue
                    
                    if purchase_code in existing_data:
                        # 기존 데이터와 비교
                        existing_item = existing_data[purchase_code]
                        if self._has_data_changed(existing_item, new_item):
                            merged_data[purchase_code] = new_item
                            updated_count += 1
                        else:
                            unchanged_count += 1
                    else:
                        # 새로운 데이터
                        merged_data[purchase_code] = new_item
                        new_count += 1
                
                # 딕셔너리를 리스트로 변환
                final_data = list(merged_data.values())
                
                # 모든 발주번호의 프로덕트 스크래핑
                self.log_signal.emit("발주프로덕트 데이터 스크래핑을 시작합니다...", LOG_INFO)
                all_products = {}
                success_count = 0
                failed_count = 0
                
                for idx, purchase_data in enumerate(final_data):
                    purchase_code = purchase_data.get('purchase_code')
                    if purchase_code:
                        try:
                            self.log_signal.emit(f"진행 상황: {idx+1}/{len(final_data)} - 발주번호 {purchase_code}의 프로덕트 스크래핑 중...", LOG_DEBUG)
                            products = scraper.scrape_purchase_products(purchase_code)
                            if products:
                                all_products[purchase_code] = products
                                success_count += 1
                                self.log_signal.emit(f"발주번호 {purchase_code}: {len(products)}건 완료", LOG_DEBUG)
                            else:
                                failed_count += 1
                                self.log_signal.emit(f"발주번호 {purchase_code}: 프로덕트 없음 또는 스크래핑 실패", LOG_DEBUG)
                        except Exception as e:
                            failed_count += 1
                            self.log_signal.emit(f"발주번호 {purchase_code} 프로덕트 스크래핑 오류: {str(e)}", LOG_WARNING)
                            continue
                        
                        # 너무 많은 요청으로 인한 차단 방지를 위해 잠시 대기
                        if idx % 10 == 9:  # 10개마다 대기
                            import time
                            time.sleep(1.0)
                
                # 발주 데이터에 프로덕트 데이터 포함
                for purchase_data in final_data:
                    purchase_code = purchase_data.get('purchase_code')
                    if purchase_code in all_products:
                        purchase_data['products'] = all_products[purchase_code]
                    else:
                        purchase_data['products'] = []
                
                # 파일 저장 (새로운 타임스탬프로)
                timestamp = datetime.now().strftime('%H%M')
                filename = f'fbo_po_{today}-{timestamp}.json'
                file_path = os.path.join(data_dir, filename)
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(final_data, f, ensure_ascii=False, indent=2)
                
                # 기존 파일 삭제 (최신 파일만 유지)
                if existing_file_path and existing_file_path != file_path:
                    try:
                        os.remove(existing_file_path)
                        self.log_signal.emit(f"기존 파일 삭제: {os.path.basename(existing_file_path)}", LOG_DEBUG)
                    except:
                        pass
                
                # 업데이트 결과 로그
                total_products = sum(len(p) for p in all_products.values())
                self.log_signal.emit(f"데이터 업데이트 완료 - 신규: {new_count}건, 변경: {updated_count}건, 유지: {unchanged_count}건", LOG_SUCCESS)
                self.log_signal.emit(f"프로덕트 스크래핑 완료 - 성공: {success_count}건, 실패: {failed_count}건, 총 프로덕트: {total_products}건", LOG_SUCCESS)
                self.log_signal.emit(f"파일 저장: {file_path}", LOG_SUCCESS)
                
                # 테이블용 데이터 변환
                table_data = []
                for row in final_data:
                    # 가격 포맷팅 (숫자를 KRW 형태로)
                    price = row.get("price", "0")
                    if price and price.isdigit():
                        formatted_price = f"KRW {int(price):,}"
                    else:
                        formatted_price = price or "-"
                    
                    table_data.append({
                        "발주번호": row.get("purchase_code", ""),
                        "거래타입": row.get("purchase_type", ""),
                        "생성시각": row.get("created_at", ""),
                        "주문": row.get("order_code", ""),
                        "판매자": row.get("seller", ""),
                        "발주담당자": row.get("in_charge", ""),
                        "발주수량": row.get("quantity", ""),
                        "공급가액": formatted_price,
                        "단가변경여부": row.get("price_changeable", ""),
                        "지연허용여부": row.get("delay_allowable", ""),
                        "상태": row.get("status", ""),
                        "정산상태": row.get("payment_status", ""),
                        "내부메모": row.get("internal_memo", "")
                    })
                
                self.scraped_data = table_data
                self.scraped_products = all_products
                self.data_scraped.emit(table_data, all_products)
                self.log_signal.emit(f"총 {len(table_data)}건의 발주데이터, {total_products}건의 프로덕트데이터 표시", LOG_SUCCESS)
            else:
                self.scraping_error.emit("데이터 스크래핑 실패")
                
        except Exception as e:
            self.scraping_error.emit(f"스크래핑 중 오류: {str(e)}")
        finally:
            self.scraping_finished.emit()
    
    def _has_data_changed(self, existing_item: dict, new_item: dict) -> bool:
        """두 데이터 항목이 변경되었는지 비교"""
        # 중요한 필드들만 비교 (타임스탬프 등 무시)
        compare_fields = [
            'purchase_type', 'order_code', 'seller', 'in_charge', 'quantity', 
            'price', 'price_changeable', 'delay_allowable', 'status', 
            'payment_status', 'internal_memo'
        ]
        
        for field in compare_fields:
            if existing_item.get(field) != new_item.get(field):
                return True
        return False

class FboPoSection(BaseSection):
    """
    FBO 발주 확인 요청 섹션 - 발주 확인 요청 관련 기능
    """
    def __init__(self, parent=None):
        super().__init__("FBO 발주 확인 요청", parent)
        self.refresh_button = self.add_header_button("새로고침", self._on_refresh_clicked)
        self.send_button = self.add_header_button("메시지 전송", self._on_send_clicked, primary=True)
        
        # 데이터 매니저 초기화
        self.data_manager = DataManager(OrderType.FBO, log_function=self.log)
        
        # 스크래핑 스레드 초기화
        self.scraping_thread = FboPoScrapingThread()
        self.scraping_thread.log_signal.connect(self._on_scraping_log)
        self.scraping_thread.data_scraped.connect(self._on_data_scraped)
        self.scraping_thread.scraping_finished.connect(self._on_scraping_finished)
        self.scraping_thread.scraping_error.connect(self._on_scraping_error)
        
        # 프로덕트 데이터 저장소 (JSON에서 로드)
        self.all_products_data = {}
        
        self.setup_content()
    
    def setup_content(self):
        # 상단 필터/검색 영역
        filter_widget = QWidget()
        filter_layout = QHBoxLayout(filter_widget)
        filter_layout.setContentsMargins(0, 0, 0, 0)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("판매자, 발주번호 검색...")
        self.search_input.textChanged.connect(self._on_search_changed)
        self.status_filter = QComboBox()
        self.status_filter.addItem("모든 상태", "all")
        self.status_filter.addItem("대기중", "pending")
        self.status_filter.addItem("전송완료", "sent")
        self.status_filter.addItem("전송실패", "failed")
        self.status_filter.currentIndexChanged.connect(self._on_filter_changed)
        filter_layout.addWidget(QLabel("검색:"))
        filter_layout.addWidget(self.search_input)
        filter_layout.addWidget(QLabel("상태:"))
        filter_layout.addWidget(self.status_filter)
        filter_layout.addStretch()
        self.content_layout.addWidget(filter_widget)
        
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
        
        # 데이터 로드
        self._load_existing_data()
    
    def _load_existing_data(self):
        """기존 JSON 데이터 로드"""
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
            json_files = glob.glob(os.path.join(data_dir, f'fbo_po_{today}-*.json'))
            
            if not json_files:
                # 오늘 파일이 없으면 가장 최신 파일 찾기
                json_files = glob.glob(os.path.join(data_dir, 'fbo_po_*.json'))
            
            if json_files:
                # 가장 최신 파일 사용
                latest_file = max(json_files, key=os.path.getmtime)
                
                with open(latest_file, 'r', encoding='utf-8') as f:
                    raw_data = json.load(f)
                
                # 데이터 변환 및 프로덕트 데이터 분리
                table_data = []
                for item in raw_data:
                    # 프로덕트 데이터 저장
                    purchase_code = item.get("purchase_code", "")
                    if purchase_code and 'products' in item:
                        self.all_products_data[purchase_code] = item['products']
                    
                    table_data.append({
                        "발주번호": purchase_code,
                        "거래타입": item.get("purchase_type", ""),
                        "생성시각": item.get("created_at", ""),
                        "주문": item.get("order_code", ""),
                        "판매자": item.get("seller", ""),
                        "발주담당자": item.get("in_charge", ""),
                        "발주수량": item.get("quantity", ""),
                        "공급가액": f"KRW {int(item.get('price', 0)):,}" if item.get('price', '').isdigit() else item.get('price', ''),
                        "단가변경여부": item.get("price_changeable", ""),
                        "지연허용여부": item.get("delay_allowable", ""),
                        "상태": item.get("status", ""),
                        "정산상태": item.get("payment_status", ""),
                        "내부메모": item.get("internal_memo", "")
                    })
                
                self.table.update_data(table_data)
                self.stats_label.setText(f"총 {len(table_data)}건")
                
                total_products = sum(len(products) for products in self.all_products_data.values())
                self.log(f"발주 확인 데이터 {len(table_data)}건, 프로덕트 데이터 {total_products}건을 로드했습니다. ({os.path.basename(latest_file)})", LOG_SUCCESS)
                
            else:
                self.log("발주 확인 데이터 파일을 찾을 수 없습니다. 새로고침을 눌러 데이터를 스크래핑하세요.", LOG_WARNING)
                
        except Exception as e:
            self.log(f"발주 확인 데이터 로드 중 오류: {str(e)}", LOG_ERROR)

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

    def _on_product_show_requested(self, purchase_code: str):
        """프로덕트 표시 요청 처리 - JSON 데이터에서 로드"""
        try:
            if purchase_code in self.all_products_data:
                products = self.all_products_data[purchase_code]
                if products:
                    # 테이블에 프로덕트 데이터 추가
                    self.table.add_products_to_purchase(purchase_code, products)
                    self.log(f"발주번호 {purchase_code}의 프로덕트 {len(products)}건을 표시했습니다.", LOG_SUCCESS)
                else:
                    self.log(f"발주번호 {purchase_code}에 프로덕트 데이터가 없습니다.", LOG_INFO)
            else:
                self.log(f"발주번호 {purchase_code}의 프로덕트 데이터를 찾을 수 없습니다. 새로고침을 눌러 데이터를 업데이트하세요.", LOG_WARNING)
                
        except Exception as e:
            self.log(f"프로덕트 데이터 로드 중 오류: {str(e)}", LOG_ERROR)

    def _on_scraping_log(self, message, log_type):
        """스크래핑 스레드에서 온 로그 메시지 처리"""
        self.log(message, log_type)

    def _on_data_scraped(self, table_data, products_data):
        """스크래핑된 데이터를 테이블에 업데이트"""
        self.table.update_data(table_data)
        self.stats_label.setText(f"총 {len(table_data)}건")
        
        # 프로덕트 데이터 저장
        self.all_products_data = products_data
        
        total_products = sum(len(products) for products in products_data.values())
        self.log(f"발주 확인 데이터 {len(table_data)}건, 프로덕트 데이터 {total_products}건을 로드했습니다.", LOG_SUCCESS)

    def _on_scraping_finished(self):
        """스크래핑 완료 후 UI 복원"""
        self.refresh_button.setEnabled(True)
        self.refresh_button.setText("새로고침")

    def _on_scraping_error(self, error_message):
        """스크래핑 오류 처리"""
        self.log(error_message, LogType.ERROR.value)
    
    def _on_send_clicked(self):
        selected = self.table.get_selected_rows()
        if not selected:
            self.log("선택된 항목이 없습니다.", LogType.WARNING.value)
            return
        self.log(f"{len(selected)}건의 발주 확인 요청 메시지를 전송합니다.", LogType.INFO.value)
        # TODO: 실제 메시지 전송 구현
    
    def _on_search_changed(self, text):
        self.log(f"검색어: {text}", LogType.DEBUG.value)
        # TODO: 검색 기능 구현
    
    def _on_filter_changed(self, index):
        filter_value = self.status_filter.itemData(index)
        self.log(f"상태 필터: {filter_value}", LogType.DEBUG.value)
        # TODO: 필터링 기능 구현
    
    def _on_table_selection_changed(self, selected_items):
        # 필요시 추가 동작 구현 가능
        pass
    
    def on_section_activated(self):
        self.log("FBO 발주 확인 요청 섹션이 활성화되었습니다.", LogType.INFO.value)
    
    def on_section_deactivated(self):
        # 스크래핑 스레드 중단
        if self.scraping_thread.isRunning():
            self.scraping_thread.quit()
            self.scraping_thread.wait(3000)  # 3초 대기 