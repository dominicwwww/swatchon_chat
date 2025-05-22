"""
FBO 출고 요청 스크래퍼 - 스와치온 관리자 페이지에서 출고 요청 데이터 스크래핑
"""
from datetime import datetime
import pandas as pd
import traceback
import time
import threading
import gc

from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException, StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from services.base_scraper import BaseScraper
from core.logger import get_logger
from ui.components.log_widget import LOG_INFO, LOG_DEBUG, LOG_WARNING, LOG_ERROR, LOG_SUCCESS

class ShipmentRequestScraper(BaseScraper):
    """FBO 출고 요청 스크래퍼 클래스"""
    
    def __init__(self, user_info=None, log_function=None):
        super().__init__(user_info)
        # 상속받은 shipment_request_url 사용 (현재는 receive_url과 동일)
        self.log_function = log_function
        # 스크래핑 제어를 위한 플래그
        self.is_cancellation_requested = False
        # 리소스 관리를 위한 변수들
        self._safety_timer = None
        self._resource_check_timer = None
    
    def _get_link_url(self, parent, selector):
        """링크 URL을 가져오는 헬퍼 메서드"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                link = parent.find_element(By.CSS_SELECTOR, selector)
                return link.get_attribute("href")
            except StaleElementReferenceException:
                if attempt < max_retries - 1:
                    time.sleep(0.5)  # 잠시 대기 후 재시도
                    continue
                return ""
            except NoSuchElementException:
                return ""
            except Exception as e:
                self.log(f"링크 URL 가져오기 실패: {str(e)}", LOG_WARNING)
                return ""
    
    def _element_exists(self, parent, selector):
        """특정 셀렉터가 존재하는지 확인하는 헬퍼 메서드"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                parent.find_element(By.CSS_SELECTOR, selector)
                return True
            except StaleElementReferenceException:
                if attempt < max_retries - 1:
                    time.sleep(0.5)  # 잠시 대기 후 재시도
                    continue
                return False
            except NoSuchElementException:
                return False
            except Exception:
                return False
    
    def _request_cancellation(self):
        """스크래핑 작업 취소 요청"""
        self.is_cancellation_requested = True
        self.log("스크래핑 취소 요청이 접수되었습니다. 진행 중인 작업을 안전하게 종료합니다.", LOG_WARNING)
        self.update_status("취소 요청 처리 중...", 0.0)

    def _check_system_resources(self):
        """시스템 리소스 주기적 확인 및 관리"""
        if self.is_cancellation_requested:
            return
            
        try:
            # 메모리 사용량 확인 및 가비지 컬렉션 유도
            gc.collect()
            
            # 30초마다 반복 호출
            self._resource_check_timer = threading.Timer(30, self._check_system_resources)
            self._resource_check_timer.daemon = True
            self._resource_check_timer.start()
        except Exception as e:
            self.log(f"리소스 체크 중 오류: {str(e)}", LOG_WARNING)
    
    def _stop_timers(self):
        """모든 타이머 정리"""
        # 안전 타이머 정리
        if hasattr(self, '_safety_timer') and self._safety_timer and self._safety_timer.is_alive():
            try:
                self._safety_timer.cancel()
            except Exception:
                pass
                
        # 리소스 체크 타이머 정리
        if hasattr(self, '_resource_check_timer') and self._resource_check_timer and self._resource_check_timer.is_alive():
            try:
                self._resource_check_timer.cancel()
            except Exception:
                pass
    
    def log(self, message, log_type=LOG_INFO):
        """로그 메시지 출력 (UI log_function 호출 제거, logger만 사용)"""
        self.logger.info(message)
    
    def scrape_shipment_requests(self, filtered_url=None, log_function=None):
        """출고 요청 데이터 스크래핑 - 입고페이지에서 '오늘' 출고 예정인 데이터 추출"""
        result_df = pd.DataFrame()  # 기본 반환값 설정
        
        # 취소 요청 플래그 초기화
        self.is_cancellation_requested = False
        
        # 리소스 체크 시작
        self._check_system_resources()
        
        try:
            # 로그 함수가 제공되면 업데이트
            if log_function:
                self.log_function = log_function
                
            # 안전 타이머 설정 - 작업이 너무 오래 걸리면 경고만 하고 종료하지 않음
            def safety_timeout():
                self.log("안전 시간 초과: 스크래핑 작업이 10분 이상 소요되고 있습니다.", LOG_WARNING)
                self.update_status("시간이 오래 걸리고 있습니다...", 0.5)
                # 앱 종료나 드라이버 종료는 하지 않음
            
            # 10분 타임아웃 설정
            self._safety_timer = threading.Timer(600, safety_timeout)
            self._safety_timer.daemon = True
            self._safety_timer.start()
                
            self.log("FBO 출고 요청 데이터 스크래핑 시작...", LOG_INFO)
            self.update_status("FBO 출고 요청 데이터 스크래핑 시작...", 0.0)
            
            # 현재 날짜 가져오기
            today = datetime.now().strftime("%Y-%m-%d")
            self.log(f"현재 날짜: {today}, 이 날짜로 출고 예정 데이터를 필터링합니다.", LOG_INFO)
            
            # 필터링된 URL이 제공되면 사용, 아니면 기본 URL에 날짜 필터 추가
            url_to_use = filtered_url
            if not url_to_use:
                # 기본 URL에 날짜 필터 파라미터 추가
                from urllib.parse import urlencode
                
                filter_params = {
                    "q[pickup_at_lteq]": today  # 오늘 날짜까지 필터링
                }
                
                # URL 파라미터 인코딩 및 URL 생성
                url_to_use = f"{self.receive_url}?{urlencode(filter_params)}"
            
            self.log(f"사용할 URL: {url_to_use}", LOG_INFO)
            
            # 취소 체크
            if self.is_cancellation_requested:
                self.log("사용자 요청으로 스크래핑 취소됨", LOG_WARNING)
                return result_df
            
            # 로그인 및 페이지 이동
            if not self.check_login_and_navigate(url_to_use):
                self.log("로그인 또는 페이지 이동 실패", LOG_ERROR)
                self.update_status("로그인 또는 페이지 이동 실패", 0.0)
                return result_df
            
            # 취소 체크
            if self.is_cancellation_requested:
                self.log("사용자 요청으로 스크래핑 취소됨", LOG_WARNING)
                return result_df
                
            # 현재 URL 체크
            current_url = self.driver.current_url
            self.update_status("페이지 확인 중...", 0.1)
            
            # 리디렉션 확인 및 처리
            if "receive_index" not in current_url:
                self.log(f"예상 페이지와 다른 URL에 있습니다: {current_url}", LOG_WARNING)
                
                # 수동 리디렉션 시도
                try:
                    receive_url = self.receive_url
                    self.log(f"입고 페이지로 수동 이동 시도: {receive_url}")
                    
                    if not self.navigate_to_page(receive_url):
                        self.log("페이지 이동 실패. 스크래핑을 중단합니다.", LOG_ERROR)
                        self.update_status("페이지 이동 실패", 0.0)
                        return result_df
                except Exception as e:
                    self.log(f"페이지 이동 중 오류: {str(e)}", LOG_ERROR)
                    self.update_status("페이지 이동 중 오류", 0.0)
                    return result_df
            
            # 스크래핑 실행
            scraped_data = self.paginate_and_scrape(self.extract_shipment_request_data)
            
            if not scraped_data:
                self.log("스크래핑된 데이터가 없습니다.", LOG_WARNING)
                return result_df
                
            # 데이터프레임 변환
            self.log(f"수집된 데이터를 데이터프레임으로 변환 중 (행 수: {len(scraped_data)})")
            result_df = pd.DataFrame(scraped_data)
            
            # 테이블 생성 로그 추가
            self.log("출고 요청 테이블 생성 시작", LOG_INFO)
            # (UI에서 테이블 갱신 콜백이 있다면 호출)
            if hasattr(self, 'table_update_callback') and callable(self.table_update_callback):
                self.table_update_callback(result_df)
            self.log("출고 요청 테이블 생성 완료", LOG_INFO)
                
            # 로그 출력
            if not result_df.empty:
                self._log_shipment_summary(result_df)
            
            return result_df
            
        except Exception as e:
            self.log(f"스크래핑 중 오류 발생: {str(e)}", LOG_ERROR)
            return result_df
            
        finally:
            # 리소스 정리
            self._stop_timers()
            
            # 가비지 컬렉션 실행
            gc.collect()
    
    def _log_shipment_summary(self, df):
        """판매자별 출고 요청 현황 요약 로깅"""
        self.log("\n=== 판매자별 출고 요청 현황 ===", LOG_INFO)
        for seller in sorted(df["판매자"].unique()):
            seller_orders = df[df["판매자"] == seller]
            order_summary = [
                f"- 발주번호: {num} (출고예정일: {date})"
                for num, date in zip(seller_orders["발주번호"], seller_orders["발주출고예상일자"])
            ]
            
            self.log(
                f"""
■ {seller}
  - 출고 요청 필요 건수: {len(seller_orders)}건
  - 발주 목록:
    {chr(10).join(order_summary)}
""", LOG_INFO)
        
        # 전체 요약
        self.log(
            f"""
=== 전체 요약 ===
- 총 출고 요청 필요 건수: {len(df)}건
- 판매자 수: {len(df["판매자"].unique())}개
""", LOG_SUCCESS) 

    def extract_shipment_request_data(self, row):
        """행에서 출고 요청 데이터 추출 (모든 컬럼)"""
        if self.is_cancellation_requested:
            return None
        try:
            # 사진 URL (썸네일)
            try:
                img_elem = row.find_element(By.CSS_SELECTOR, "td:nth-child(1) img")
                photo_url = img_elem.get_attribute("src")
            except Exception:
                photo_url = ""

            # 프린트
            try:
                print_text = row.find_element(By.CSS_SELECTOR, "td:nth-child(2)").text.strip()
            except Exception:
                print_text = ""

            # ID (링크)
            try:
                id_elem = row.find_element(By.CSS_SELECTOR, "td:nth-child(3) a")
                id_text = id_elem.text.strip()
                id_url = id_elem.get_attribute("href")
            except Exception:
                id_text = row.find_element(By.CSS_SELECTOR, "td:nth-child(3)").text.strip()
                id_url = ""

            # 판매자 (링크)
            try:
                seller_elem = row.find_element(By.CSS_SELECTOR, "td:nth-child(4) a")
                seller = seller_elem.text.strip()
                seller_url = seller_elem.get_attribute("href")
            except Exception:
                seller = row.find_element(By.CSS_SELECTOR, "td:nth-child(4)").text.strip()
                seller_url = ""

            # 판매자 동대문주소
            try:
                seller_addr = row.find_element(By.CSS_SELECTOR, "td:nth-child(5)").text.strip()
            except Exception:
                seller_addr = ""

            # 아이템 (링크)
            try:
                item_elem = row.find_element(By.CSS_SELECTOR, "td:nth-child(6) a")
                item = item_elem.text.strip()
                item_url = item_elem.get_attribute("href")
            except Exception:
                item = row.find_element(By.CSS_SELECTOR, "td:nth-child(6)").text.strip()
                item_url = ""

            # 스와치 보관함
            try:
                swatch_box = row.find_element(By.CSS_SELECTOR, "td:nth-child(7)").text.strip()
            except Exception:
                swatch_box = ""

            # 컬러순서
            try:
                color_order = row.find_element(By.CSS_SELECTOR, "td:nth-child(8)").text.strip()
            except Exception:
                color_order = ""

            # 컬러코드
            try:
                color_code = row.find_element(By.CSS_SELECTOR, "td:nth-child(9)").text.strip()
            except Exception:
                color_code = ""

            # 판매방식
            try:
                sale_type = row.find_element(By.CSS_SELECTOR, "td:nth-child(10)").text.strip()
            except Exception:
                sale_type = ""

            # 발주수량
            try:
                order_qty = row.find_element(By.CSS_SELECTOR, "td:nth-child(11)").text.strip()
            except Exception:
                order_qty = ""

            # 발주번호 (링크)
            try:
                order_num_elem = row.find_element(By.CSS_SELECTOR, "td:nth-child(12) a")
                order_num = order_num_elem.text.strip()
                order_num_url = order_num_elem.get_attribute("href")
            except Exception:
                order_num = row.find_element(By.CSS_SELECTOR, "td:nth-child(12)").text.strip()
                order_num_url = ""

            # 주문번호 (링크)
            try:
                order_id_elem = row.find_element(By.CSS_SELECTOR, "td:nth-child(13) a")
                order_id = order_id_elem.text.strip()
                order_id_url = order_id_elem.get_attribute("href")
            except Exception:
                order_id = row.find_element(By.CSS_SELECTOR, "td:nth-child(13)").text.strip()
                order_id_url = ""

            # 최종출고일자
            try:
                last_ship_date = row.find_element(By.CSS_SELECTOR, "td:nth-child(14)").text.strip()
            except Exception:
                last_ship_date = ""

            # 발주출고예상일자
            try:
                expected_ship_date = row.find_element(By.CSS_SELECTOR, "td:nth-child(15)").text.strip()
            except Exception:
                expected_ship_date = ""

            # 발주배송수단
            try:
                order_ship_method = row.find_element(By.CSS_SELECTOR, "td:nth-child(16)").text.strip()
            except Exception:
                order_ship_method = ""

            # 판매자발송수단
            try:
                seller_ship_method = row.find_element(By.CSS_SELECTOR, "td:nth-child(17)").text.strip()
            except Exception:
                seller_ship_method = ""

            # 발주상태
            try:
                order_status = row.find_element(By.CSS_SELECTOR, "td:nth-child(18)").text.strip()
            except Exception:
                order_status = ""

            return {
                "사진_URL": photo_url,
                "프린트": print_text,
                "ID": id_text,
                "ID_URL": id_url,
                "판매자": seller,
                "판매자_URL": seller_url,
                "판매자_동대문주소": seller_addr,
                "아이템": item,
                "아이템_URL": item_url,
                "스와치_보관함": swatch_box,
                "컬러순서": color_order,
                "컬러코드": color_code,
                "판매방식": sale_type,
                "발주수량": order_qty,
                "발주번호": order_num,
                "발주번호_URL": order_num_url,
                "주문번호": order_id,
                "주문번호_URL": order_id_url,
                "최종출고일자": last_ship_date,
                "발주출고예상일자": expected_ship_date,
                "발주배송수단": order_ship_method,
                "판매자발송수단": seller_ship_method,
                "발주상태": order_status,
                "선택": False,
                "메시지상태": "대기중"
            }
        except StaleElementReferenceException:
            self.log("행 요소가 변경되었습니다. 다음 항목으로 진행합니다.", LOG_WARNING)
        except NoSuchElementException as e:
            self.log(f"행 데이터 추출 실패: {str(e)}", LOG_WARNING)
        except Exception as e:
            self.log(f"행 데이터 처리 중 오류: {str(e)}", LOG_WARNING)
        return None 