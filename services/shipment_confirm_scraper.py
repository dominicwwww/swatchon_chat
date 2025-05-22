"""
FBO 출고 확인 스크래퍼 - 스와치온 관리자 페이지에서 출고 확인 데이터 스크래핑
"""
from datetime import datetime
import pandas as pd
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By

from services.base_scraper import BaseScraper
from core.logger import get_logger
from ui.components.log_widget import LOG_INFO, LOG_DEBUG, LOG_WARNING, LOG_ERROR, LOG_SUCCESS

class ShipmentConfirmScraper(BaseScraper):
    """FBO 출고 확인 스크래퍼 클래스"""
    
    def __init__(self, user_info=None, log_function=None):
        super().__init__(user_info)
        # 상속받은 receive_url 사용
        self.log_function = log_function
    
    def scrape_shipment_confirms(self, filtered_url=None, log_function=None):
        """출고 확인 데이터 스크래핑 - 입고 대기 중인 출고 확인 데이터"""
        try:
            # 로그 함수가 제공되면 업데이트
            if log_function:
                self.log_function = log_function
                
            self.log("FBO 출고 확인 데이터 스크래핑 시작...", LOG_INFO)
            
            # 필터링된 URL이 제공되면 사용, 아니면 기본 URL 사용
            url_to_use = filtered_url if filtered_url else self.receive_url
            
            # 로그인 상태 확인 후 입고 페이지로 이동
            self.log("스와치온 관리자 페이지 로그인 확인 중...")
            if not self.check_login_and_navigate(url_to_use):
                self.log("로그인 실패. 스크래핑을 중단합니다.", LOG_ERROR)
                return pd.DataFrame()
            
            # 현재 날짜 가져오기
            today = datetime.now().strftime("%Y/%m/%d")
            self.log(f"현재 날짜: {today}", LOG_INFO)
            
            # 데이터 추출 함수 정의
            def extract_shipment_confirm_data(row):
                try:
                    # 발주상태 확인 - 여기서는 이미 출고된 상품만 확인
                    status = row.find_element(By.CSS_SELECTOR, "td:nth-child(18)").text.strip()
                    
                    # 발주상태가 '출고', '배송중' 등인 경우에만 처리
                    if "출고" in status or "배송중" in status or "배송" in status:
                        # 판매자 정보 미리 추출하여 로그에 표시
                        seller = row.find_element(By.CSS_SELECTOR, "td:nth-child(4)").text.strip()
                        item = row.find_element(By.CSS_SELECTOR, "td:nth-child(6)").text.strip()
                        order_number = row.find_element(By.CSS_SELECTOR, "td:nth-child(12)").text.strip()
                        
                        self.log(f"데이터 추출 중: {seller} - {item} (발주번호: {order_number})", LOG_INFO)
                        
                        # 각 컬럼의 데이터 추출
                        row_data = {
                            "판매자": seller,
                            "판매자_URL": self._get_link_url(row, "td:nth-child(4) a"),
                            "상품명": item,
                            "상품명_URL": self._get_link_url(row, "td:nth-child(6) a"),
                            "수량": row.find_element(By.CSS_SELECTOR, "td:nth-child(11)").text.strip(),
                            "발주번호": order_number,
                            "발주번호_URL": self._get_link_url(row, "td:nth-child(12) a"),
                            "주문번호": row.find_element(By.CSS_SELECTOR, "td:nth-child(13)").text.strip(),
                            "주문번호_URL": self._get_link_url(row, "td:nth-child(13) a"),
                            "출고일자": row.find_element(By.CSS_SELECTOR, "td:nth-child(14)").text.strip(),
                            "발주출고예상일자": row.find_element(By.CSS_SELECTOR, "td:nth-child(15)").text.strip(),
                            "배송수단": row.find_element(By.CSS_SELECTOR, "td:nth-child(16)").text.strip(),
                            "발주상태": status,
                            "선택": False,  # 체크박스 상태 초기값
                            "메시지상태": "대기중"  # 메시지 전송 상태 초기값
                        }
                        
                        return row_data
                
                except NoSuchElementException as e:
                    self.log(f"행 데이터 추출 실패: {str(e)}", LOG_WARNING)
                
                return None  # 조건에 맞지 않는 데이터는 None 반환
            
            # 페이지네이션 처리하며 데이터 스크래핑
            self.log("스크래핑 시작. 모든 페이지를 확인합니다...")
            shipment_data = self.paginate_and_scrape(extract_shipment_confirm_data)
            
            # DataFrame 생성
            df = pd.DataFrame(shipment_data)
            if not df.empty:
                self.log(f"스크래핑 완료! 총 {len(df)}개 데이터 추출됨", LOG_SUCCESS)
                
                # 판매자별 발주 데이터 요약 출력
                self._log_shipment_summary(df)
            else:
                self.log("스크래핑 완료했으나 출고된 데이터가 없습니다.", LOG_WARNING)
            
            return df
            
        except Exception as e:
            self.log(f"출고 확인 데이터 스크래핑 중 예상치 못한 오류: {str(e)}", LOG_ERROR)
            return pd.DataFrame()
    
    def _log_shipment_summary(self, df):
        """판매자별 출고 확인 현황 요약 로깅"""
        self.log("\n=== 판매자별 출고 확인 현황 ===", LOG_INFO)
        for seller in sorted(df["판매자"].unique()):
            seller_orders = df[df["판매자"] == seller]
            order_summary = [
                f"- 발주번호: {num} (출고일: {date})"
                for num, date in zip(seller_orders["발주번호"], seller_orders["출고일자"])
            ]
            
            self.log(
                f"""
■ {seller}
  - 출고 확인 필요 건수: {len(seller_orders)}건
  - 출고 목록:
    {chr(10).join(order_summary)}
""", LOG_INFO)
        
        # 전체 요약
        self.log(
            f"""
=== 전체 요약 ===
- 총 출고 확인 필요 건수: {len(df)}건
- 판매자 수: {len(df["판매자"].unique())}개
""", LOG_SUCCESS) 