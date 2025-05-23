"""
FBO 출고 요청 섹션 - 출고 요청 기능
"""
from typing import List, Dict, Any
import threading
import pandas as pd
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFrame, QComboBox, QLineEdit, QMessageBox, QProgressDialog, QApplication
)
from PySide6.QtCore import Qt, Signal, QSize, QTimer
from PySide6.QtGui import QFont, QColor
import json
import os
from datetime import datetime
import glob

from core.types import LogType
from ui.sections.base_section import BaseSection
from ui.theme import get_theme
from services.shipment_request_scraper import ShipmentRequestScraper
from ui.components.log_widget import LOG_INFO, LOG_DEBUG, LOG_WARNING, LOG_ERROR, LOG_SUCCESS
from ui.components.shipment_request_table import ShipmentRequestTable

class ShipmentRequestSection(BaseSection):
    """
    FBO 출고 요청 섹션 - 출고 요청 관련 기능
    """
    
    def __init__(self, parent=None):
        super().__init__("FBO 출고 요청", parent)
        
        # 데이터 저장 경로 설정
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data')
        os.makedirs(self.data_dir, exist_ok=True)
        
        # 스크래퍼는 실제 사용할 때 초기화 - 미리 하지 않음
        self.scraper = None
        
        # 데이터 저장 변수
        self.all_data = []
        self.filtered_data = []
        self.df = pd.DataFrame()
        
        # 헤더 버튼 추가
        self.refresh_button = self.add_header_button("새로고침", self._on_refresh_clicked)
        self.load_saved_button = self.add_header_button("저장 데이터 불러오기", self._on_load_saved_clicked)
        self.send_button = self.add_header_button("메시지 전송", self._on_send_clicked, primary=True)
        
        # 콘텐츠 설정
        self.setup_content()
    
    def setup_content(self):
        """콘텐츠 설정"""
        # 필터 영역
        filter_widget = QWidget()
        filter_layout = QHBoxLayout(filter_widget)
        filter_layout.setContentsMargins(0, 0, 0, 0)
        
        # 검색창
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("판매자, 발주번호 검색...")
        self.search_input.textChanged.connect(self._on_search_changed)
        
        # 상태 필터
        self.status_filter = QComboBox()
        self.status_filter.addItem("모든 상태", "all")
        self.status_filter.addItem("대기중", "pending")
        self.status_filter.addItem("전송완료", "sent")
        self.status_filter.addItem("전송실패", "failed")
        self.status_filter.currentIndexChanged.connect(self._on_filter_changed)
        
        # 필터 레이아웃에 추가
        filter_layout.addWidget(QLabel("검색:"))
        filter_layout.addWidget(self.search_input)
        filter_layout.addWidget(QLabel("상태:"))
        filter_layout.addWidget(self.status_filter)
        filter_layout.addStretch()
        
        self.content_layout.addWidget(filter_widget)
        
        # 테이블 위젯
        self.table = ShipmentRequestTable()
        self.table.selection_changed.connect(self._on_table_selection_changed)
        self.content_layout.addWidget(self.table.main_widget)
        
        # 통계 정보
        stats_widget = QWidget()
        stats_layout = QHBoxLayout(stats_widget)
        stats_layout.setContentsMargins(0, 8, 0, 0)
        
        self.stats_label = QLabel("총 0건")
        stats_layout.addWidget(self.stats_label)
        stats_layout.addStretch()
        
        # 선택 버튼들
        self.select_all_button = QPushButton("모두 선택")
        self.select_all_button.clicked.connect(self._on_select_all_clicked)
        
        self.deselect_all_button = QPushButton("모두 해제")
        self.deselect_all_button.clicked.connect(self._on_deselect_all_clicked)
        
        stats_layout.addWidget(self.select_all_button)
        stats_layout.addWidget(self.deselect_all_button)
        
        self.content_layout.addWidget(stats_widget)
    
    def _on_table_selection_changed(self, selected_items):
        """테이블 선택 변경 이벤트"""
        # 선택된 항목에 따라 원본 데이터 업데이트
        for item in self.all_data:
            item["선택"] = False
            for selected in selected_items:
                if (item.get("판매자") == selected["판매자"] and 
                    item.get("발주번호") == selected["발주번호"]):
                    item["선택"] = True
                    break
    
    def apply_filters(self):
        """검색어와 상태 필터 적용 (확장 컬럼 반영)"""
        try:
            search_text = self.search_input.text().lower()
            status_filter = self.status_filter.currentData()
            if not hasattr(self, 'all_data') or not self.all_data:
                self.log("필터링할 데이터가 없습니다.", LOG_WARNING)
                self.stats_label.setText("총 0건")
                return

            filtered = []
            for item in self.all_data:
                # 상태 필터
                msg_status = item.get("메시지상태", "대기중")
                if status_filter != "all":
                    if status_filter == "pending" and msg_status != "대기중":
                        continue
                    if status_filter == "sent" and msg_status != "전송완료":
                        continue
                    if status_filter == "failed" and msg_status != "전송실패":
                        continue
                # 검색어 필터
                if search_text:
                    search_fields = ["판매자", "발주번호", "아이템", "ID", "주문번호"]
                    if not any(search_text in str(item.get(field, "")).lower() for field in search_fields):
                        continue
                filtered.append(item)
            self.filtered_data = filtered
            self.stats_label.setText(f"총 {len(self.filtered_data)}건")
        except Exception as e:
            self.log(f"필터 적용 중 오류: {str(e)}", LOG_ERROR)
            self.filtered_data = self.all_data.copy()
            self.stats_label.setText(f"총 {len(self.filtered_data)}건 (필터링 오류)")
    
    def update_table(self):
        print("[ShipmentRequestSection] update_table 진입")
        try:
            print(f"[ShipmentRequestSection] filtered_data 개수: {len(self.filtered_data)}")
            self.table.update_data(self.filtered_data)
            print("[ShipmentRequestSection] update_data 호출 완료")
        except Exception as e:
            print(f"[ShipmentRequestSection] 테이블 업데이트 중 예외: {e}")
    
    def _on_select_all_clicked(self):
        """모두 선택 버튼 클릭 이벤트"""
        self.table.select_all()
    
    def _on_deselect_all_clicked(self):
        """모두 해제 버튼 클릭 이벤트"""
        self.table.deselect_all()
    
    def _on_search_changed(self, text):
        """검색어 변경 이벤트"""
        self.apply_filters()
        self.update_table()
    
    def _on_filter_changed(self, index):
        """필터 변경 이벤트"""
        self.apply_filters()
        self.update_table()
    
    def _on_refresh_clicked(self):
        """새로고침 버튼 클릭 이벤트"""
        try:
            self.log("출고 요청 데이터를 새로고침합니다.", LOG_INFO)
            
            # 이미 스크래핑 중인지 확인
            if hasattr(self, 'scraping_completed') and not self.scraping_completed:
                self.log("이미 데이터를 가져오는 중입니다.", LOG_WARNING)
                try:
                    QMessageBox.information(self, "처리 중", "데이터를 가져오는 중입니다. 잠시만 기다려주세요.")
                except Exception:
                    pass
                return
            
            # 확인 메시지
            try:
                reply = QMessageBox.question(
                    self, 
                    "데이터 새로고침", 
                    "스와치온 관리자 페이지에서 출고 요청 데이터를 가져오시겠습니까?\n\n이 작업은 시간이 다소 소요될 수 있습니다.",
                    QMessageBox.Yes | QMessageBox.No, 
                    QMessageBox.No
                )
                
                if reply == QMessageBox.Yes:
                    self.load_data_from_scraper()
            except Exception as dialog_error:
                self.log(f"대화상자 표시 중 오류: {str(dialog_error)}", LOG_ERROR)
                # 오류가 발생해도 진행 시도
                self.load_data_from_scraper()
        except Exception as e:
            self.log(f"새로고침 버튼 처리 중 예상치 못한 오류: {str(e)}", LOG_ERROR)
            import traceback
            self.log(f"상세 오류: {traceback.format_exc()}", LOG_ERROR)
    
    def _on_send_clicked(self):
        """메시지 전송 버튼 클릭 이벤트"""
        # 선택된 항목 찾기
        selected_items = [item for item in self.all_data if item.get("선택", False)]
        
        if not selected_items:
            self.log("선택된 항목이 없습니다.", LOG_WARNING)
            return
        
        # 확인 메시지
        reply = QMessageBox.question(
            self, 
            "메시지 전송 확인", 
            f"{len(selected_items)}건의 출고 요청 메시지를 전송하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No, 
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.log(f"{len(selected_items)}건의 출고 요청 메시지를 전송합니다.", LOG_INFO)
            
            # TODO: 실제로 메시지 전송 구현
            # 임시로 전송 완료로 상태 변경
            for item in selected_items:
                item["메시지상태"] = "전송완료"
            
            # 테이블 업데이트
            self.apply_filters()
            self.update_table()
            
            self.log("메시지 전송이 완료되었습니다.", LOG_SUCCESS)
    
    def on_section_activated(self):
        """섹션이 활성화될 때 호출"""
        self.log("FBO 출고 요청 섹션이 활성화되었습니다.", LOG_INFO)
        
        # 데이터가 없는 경우에만 안내 메시지 표시
        if not self.all_data:
            self.log("'새로고침' 버튼을 클릭하여 출고 요청 데이터를 가져오세요.", LOG_INFO)
    
    def on_section_deactivated(self):
        """섹션이 비활성화될 때 호출"""
        pass

    def load_saved_data(self, file_path=None):
        """가장 최근에 생성된 shipment_requests_*.json 파일 또는 지정된 파일을 로드"""
        try:
            if file_path is None:
                pattern = os.path.join(self.data_dir, 'shipment_requests_*.json')
                file_list = glob.glob(pattern)
                if not file_list:
                    self.log("로드할 데이터 파일이 없습니다.", LOG_WARNING)
                    return False
                latest_file = max(file_list, key=os.path.getmtime)
            else:
                latest_file = file_path

            self.log(f"데이터 파일을 로드합니다: {os.path.basename(latest_file)}", LOG_INFO)
            with open(latest_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            print("[ShipmentRequestSection] update_ui 진입")
            self.all_data = data
            self.filtered_data = data.copy()
            self.apply_filters()
            print("[ShipmentRequestSection] apply_filters 호출 완료")
            self.update_table()
            print("[ShipmentRequestSection] update_table 호출 완료")
            return True
        except Exception as e:
            self.log(f"저장된 데이터 로드 중 오류: {str(e)}", LOG_ERROR)
            return False

    def save_data(self, data):
        """데이터를 JSON 파일로 저장하고 파일명을 반환"""
        try:
            timestamp = datetime.now().strftime('%y%m%d-%H%M')
            data_file = os.path.join(self.data_dir, f'shipment_requests_{timestamp}.json')
            with open(data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.log(f"데이터를 파일로 저장했습니다: {data_file}", LOG_INFO)
            return data_file
        except Exception as e:
            self.log(f"데이터 저장 중 오류: {str(e)}", LOG_ERROR)
            return None

    def load_data_from_scraper(self):
        """스크래퍼를 사용하여 데이터 로드"""
        try:
            self.is_scraping_in_progress = True
            progress = QProgressDialog("데이터를 가져오는 중...", "취소", 0, 100, self)
            progress.setWindowTitle("출고 요청 데이터 로드")
            progress.setWindowModality(Qt.NonModal)
            cancel_button = QPushButton("취소")
            progress.setCancelButton(cancel_button)
            self.is_scraping_canceled = False
            progress.canceled.connect(self._on_scraping_canceled)
            progress.setValue(0)
            progress.setMinimumDuration(0)
            progress.show()
            self.scraping_status = "초기화 중..."
            self.scraping_progress = 0
            status_timer = QTimer(self)
            def update_progress_status():
                try:
                    if not hasattr(self, 'is_scraping_in_progress') or not self.is_scraping_in_progress:
                        try:
                            status_timer.stop()
                            if progress and progress.isVisible():
                                QTimer.singleShot(0, progress.close)
                        except Exception:
                            pass
                        return
                    progress.setLabelText(f"데이터를 가져오는 중...\n\n{self.scraping_status}")
                    progress.setValue(self.scraping_progress)
                    QApplication.processEvents()
                except Exception as e:
                    self.log(f"진행 상태 업데이트 오류: {str(e)}", LOG_WARNING)
            status_timer.timeout.connect(update_progress_status)
            status_timer.start(500)
            import sys
            original_excepthook = sys.excepthook
            def global_exception_handler(exctype, value, traceback_obj):
                try:
                    self.log(f"치명적 오류 발생: {exctype.__name__}: {value}", LOG_ERROR)
                    self.scraping_status = f"심각한 오류: {exctype.__name__}: {value}"
                    self.scraping_progress = 0
                    self.scraping_result = {
                        'success': False,
                        'data': [],
                        'message': f"심각한 오류: {exctype.__name__}: {value}"
                    }
                    self.scraping_completed = True
                    self.is_scraping_in_progress = False
                    if hasattr(self, 'scraper') and self.scraper:
                        try:
                            self.scraper.close_driver()
                        except Exception:
                            pass
                    QApplication.processEvents()
                    QTimer.singleShot(0, lambda: QMessageBox.critical(self, "심각한 오류", f"예상치 못한 오류가 발생했습니다.\n\n{exctype.__name__}: {value}"))
                except Exception as handler_error:
                    original_excepthook(exctype, value, traceback_obj)
            sys.excepthook = global_exception_handler
            def update_ui_from_file(saved_file):
                try:
                    self.log(f"저장된 데이터 파일을 로드합니다: {os.path.basename(saved_file)}", LOG_INFO)
                    with open(saved_file, 'r', encoding='utf-8') as f:
                        self.all_data = json.load(f)
                        self.filtered_data = self.all_data.copy()
                    self.log(f"데이터 로드 완료: {len(self.all_data)}건", LOG_SUCCESS)
                    self.apply_filters()
                    self.update_table()
                except Exception as e:
                    self.log(f"UI 업데이트 중 오류: {str(e)}", LOG_ERROR)
                    QTimer.singleShot(0, lambda: QMessageBox.critical(self, "오류", f"데이터 로드 중 오류: {str(e)}"))
            def scrape_thread():
                try:
                    self.scraping_result = None
                    try:
                        self.scraping_status = "스크래퍼 초기화 중..."
                        self.scraping_progress = 5
                        if not self.scraper:
                            self.log("스크래퍼 초기화 중...", LOG_INFO)
                            self.scraper = ShipmentRequestScraper(log_function=self.log)
                        else:
                            self.log("기존 스크래퍼 사용 중...", LOG_INFO)
                            if hasattr(self.scraper, 'driver') and self.scraper.driver:
                                try:
                                    self.scraper.close_driver()
                                    self.log("기존 드라이버 정리 완료", LOG_INFO)
                                except Exception as e:
                                    self.log(f"드라이버 정리 실패: {str(e)}", LOG_WARNING)
                        self.scraping_progress = 10
                    except Exception as init_error:
                        self.log(f"스크래퍼 초기화 중 오류: {str(init_error)}", LOG_ERROR)
                        self.scraping_status = f"초기화 오류: {str(init_error)}"
                        self.scraping_result = {
                            'success': False,
                            'data': [],
                            'message': f"스크래퍼 초기화 실패: {str(init_error)}"
                        }
                        self.scraping_completed = True
                        self.is_scraping_in_progress = False
                        return False
                    if self.is_scraping_canceled:
                        self.log("사용자에 의해 스크래핑이 취소되었습니다.", LOG_WARNING)
                        self.scraping_status = "사용자에 의해 취소됨"
                        self.scraping_result = {
                            'success': False,
                            'data': [],
                            'message': "사용자에 의해 취소되었습니다."
                        }
                        self.scraping_completed = True
                        self.is_scraping_in_progress = False
                        return False
                    try:
                        self.scraping_status = "로그인 및 페이지 이동 중..."
                        self.scraping_progress = 15
                        self.log("스크래핑 시작", LOG_INFO)
                        def scraper_status_callback(status, progress_value=None):
                            self.scraping_status = status
                            if progress_value is not None:
                                adjusted_progress = 15 + int(progress_value * 0.75)
                                self.scraping_progress = min(90, adjusted_progress)
                        self.scraper.set_status_callback(scraper_status_callback)
                        df = None
                        try:
                            df = self.scraper.scrape_shipment_requests()
                            print(f"[scrape_thread] 스크래핑 결과 데이터프레임: {len(df) if df is not None else 'None'} 행")
                        except Exception as scrape_specific_error:
                            self.log(f"스크래핑 함수 호출 중 특정 오류: {str(scrape_specific_error)}", LOG_ERROR)
                            import traceback
                            self.log(f"스택 추적: {traceback.format_exc()}", LOG_ERROR)
                            raise
                        if self.is_scraping_canceled:
                            self.log("데이터 처리 중 사용자에 의해 취소되었습니다.", LOG_WARNING)
                            self.scraping_status = "사용자에 의해 취소됨"
                            self.scraping_result = {
                                'success': False,
                                'data': [],
                                'message': "사용자에 의해 취소되었습니다."
                            }
                            self.scraping_completed = True
                            self.is_scraping_in_progress = False
                            return False
                        self.scraping_status = "스크래핑 완료, 데이터 처리 중..."
                        self.scraping_progress = 95
                        self.log("스크래핑 작업 완료", LOG_INFO)
                        if df is not None and not df.empty:
                            try:
                                records = df.to_dict('records')
                                print(f"[scrape_thread] 데이터프레임을 딕셔너리로 변환: {len(records)}개 레코드")
                                saved_file = self.save_data(records)
                                if saved_file:
                                    self.scraping_result = {
                                        'success': True,
                                        'data': records,
                                        'message': f"총 {len(df)}개 데이터 로드 완료",
                                        'saved_file': saved_file
                                    }
                                    self.scraping_progress = 100
                                    QTimer.singleShot(0, lambda: update_ui_from_file(saved_file))
                                else:
                                    self.scraping_result = {
                                        'success': False,
                                        'data': [],
                                        'message': "데이터 저장 실패"
                                    }
                            except Exception as df_error:
                                self.log(f"데이터프레임 변환 오류: {str(df_error)}", LOG_ERROR)
                                print(f"[scrape_thread] 데이터프레임 변환 오류: {df_error}")
                                self.scraping_result = {
                                    'success': False,
                                    'data': [],
                                    'message': f"데이터 변환 실패: {str(df_error)}"
                                }
                                return False
                        else:
                            self.scraping_status = "데이터가 없습니다."
                            self.scraping_result = {
                                'success': False,
                                'data': [],
                                'message': "스크래핑된 데이터가 없습니다."
                            }
                            self.log("스크래핑된 데이터가 없습니다.", LOG_WARNING)
                            self.scraping_progress = 100
                            return False
                    except Exception as scrape_error:
                        self.scraping_status = f"스크래핑 오류: {str(scrape_error)}"
                        self.log(f"스크래핑 중 오류 발생: {str(scrape_error)}", LOG_ERROR)
                        import traceback
                        self.log(f"상세 오류: {traceback.format_exc()}", LOG_ERROR)
                        try:
                            if hasattr(self.scraper, 'driver') and self.scraper.driver:
                                self.scraper.close_driver()
                                self.log("오류 후 드라이버 정리 완료", LOG_INFO)
                        except Exception as close_error:
                            self.log(f"드라이버 정리 실패: {str(close_error)}", LOG_WARNING)
                        self.scraping_result = {
                            'success': False,
                            'data': [],
                            'message': f"스크래핑 오류: {str(scrape_error)}"
                        }
                        return False
                except Exception as e:
                    self.scraping_status = f"예상치 못한 오류: {str(e)}"
                    self.log(f"스크래핑 스레드 실행 중 예외 발생: {str(e)}", LOG_ERROR)
                    import traceback
                    self.log(f"상세 오류: {traceback.format_exc()}", LOG_ERROR)
                    self.scraping_result = {
                        'success': False,
                        'data': [],
                        'message': f"심각한 오류 발생: {str(e)}"
                    }
                    return False
                finally:
                    try:
                        self.scraping_completed = True
                        self.is_scraping_in_progress = False
                    except Exception:
                        pass
            self.scraping_completed = False
            self.scraping_result = None
            try:
                thread = threading.Thread(target=scrape_thread)
                thread.daemon = True
                thread.start()
                timer = QTimer(self)
                def check_thread_completion():
                    try:
                        if not hasattr(self, 'is_scraping_in_progress') or not self.is_scraping_in_progress:
                            QTimer.singleShot(0, lambda: (
                                timer.stop(),
                                status_timer.stop(),
                                progress.close() if progress and progress.isVisible() else None
                            ))
                            return
                        if hasattr(self, 'scraping_completed') and self.scraping_completed:
                            QTimer.singleShot(0, lambda: (
                                timer.stop(),
                                status_timer.stop(),
                                progress.close() if progress and progress.isVisible() else None
                            ))
                            try:
                                if (hasattr(self, 'scraping_result') and self.scraping_result and 
                                   self.scraping_result.get('success', False)):
                                    self.log(self.scraping_result['message'], LOG_SUCCESS)
                                else:
                                    try:
                                        error_msg = self.scraping_result.get('message', "스크래핑 실패") if self.scraping_result else "스크래핑 실패"
                                        self.log(error_msg, LOG_ERROR)
                                        QTimer.singleShot(0, lambda: QMessageBox.warning(self, "스크래핑 실패", error_msg))
                                    except Exception as msg_error:
                                        self.log(f"오류 메시지 표시 실패: {str(msg_error)}", LOG_ERROR)
                            except Exception as final_error:
                                self.log(f"최종 처리 중 오류: {str(final_error)}", LOG_ERROR)
                    except Exception as timer_error:
                        self.log(f"타이머 처리 중 오류: {str(timer_error)}", LOG_ERROR)
                        QTimer.singleShot(0, lambda: (
                            timer.stop(),
                            status_timer.stop(),
                            progress.close() if progress and progress.isVisible() else None
                        ))
                        self.is_scraping_in_progress = False
                timer.timeout.connect(check_thread_completion)
                timer.start(200)
            except Exception as thread_error:
                self.log(f"스레드 생성 실패: {str(thread_error)}", LOG_ERROR)
                try:
                    QTimer.singleShot(0, progress.close)
                    status_timer.stop()
                except Exception:
                    pass
                self.is_scraping_in_progress = False
                QTimer.singleShot(0, lambda: QMessageBox.critical(self, "오류", f"스크래핑 시작 실패: {str(thread_error)}"))
        except Exception as e:
            self.log(f"데이터 로드 함수 실행 중 예상치 못한 오류: {str(e)}", LOG_ERROR)
            import traceback
            self.log(f"상세 오류: {traceback.format_exc()}", LOG_ERROR)
            self.is_scraping_in_progress = False
            try:
                QTimer.singleShot(0, lambda: QMessageBox.critical(self, "심각한 오류", f"데이터 로드 중 시스템 오류 발생: {str(e)}"))
            except Exception:
                pass
        try:
            for _ in range(10):
                QApplication.processEvents()
        except Exception:
            pass

    def _on_scraping_canceled(self):
        """스크래핑 취소 처리"""
        if not getattr(self, 'is_scraping_in_progress', False):
            return  # 이미 종료된 경우 중복 처리 방지
        try:
            self.is_scraping_canceled = True
            self.log("스크래핑 취소 요청됨", LOG_WARNING)
            # 드라이버 정리 시도
            if hasattr(self, 'scraper') and self.scraper:
                try:
                    self.scraper.close_driver()
                    self.log("취소로 인한 드라이버 정리 완료", LOG_INFO)
                except Exception as e:
                    self.log(f"취소 시 드라이버 정리 실패: {str(e)}", LOG_WARNING)
        except Exception as e:
            self.log(f"스크래핑 취소 처리 중 오류: {str(e)}", LOG_ERROR) 

    def _on_load_saved_clicked(self):
        """저장된 최신 JSON 데이터를 불러와 테이블에 표시"""
        try:
            self.log("저장된 최신 출고 요청 데이터를 불러옵니다.", LOG_INFO)
            result = self.load_saved_data()
            if result:
                QTimer.singleShot(0, lambda: QMessageBox.information(self, "불러오기 완료", "저장된 데이터를 성공적으로 불러왔습니다."))
            else:
                QTimer.singleShot(0, lambda: QMessageBox.warning(self, "불러오기 실패", "불러올 데이터 파일이 없습니다."))
        except Exception as e:
            self.log(f"저장 데이터 불러오기 중 오류: {str(e)}", LOG_ERROR)
            QTimer.singleShot(0, lambda: QMessageBox.critical(self, "오류", f"저장 데이터 불러오기 중 오류: {str(e)}")) 