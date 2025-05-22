from datetime import datetime

import pandas as pd
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By

from services.base_scraper import BaseScraper
from src.utils.logger import get_logger
from src.utils.ui_utils import flush_events

logger = get_logger(__name__)


class ShipmentScraper(BaseScraper):
    def __init__(self, user_info=None, log_function=None):
        super().__init__(user_info)
        self.receive_url = self.config.get(
            "RECEIVE_URL", "https://admin.swatchon.me/purchase_products/receive_index"
        )
        self.log_function = log_function

    # 로그 출력 헬퍼 메서드 추가
    def log(self, message):
        """로거와 UI에 모두 로그 메시지 출력"""
        self.logger.debug(message)
        if self.log_function:
            self.log_function(message)
            flush_events()  # UI 즉시 업데이트

    def scrape_pending_shipments(self, filtered_url=None, log_function=None):
        """입고 대기 중인 출고 확인 데이터 스크래핑"""
        try:
            # 로그 함수가 제공되면 업데이트
            if log_function:
                self.log_function = log_function

            self.log("입고 대기 데이터 스크래핑 시작...")

            # 필터링된 URL이 제공되면 사용, 아니면 기본 URL 사용
            url_to_use = filtered_url if filtered_url else self.receive_url

            # 로그인 상태 확인 후 입고 페이지로 이동
            self.log("스와치온 관리자 페이지 로그인 확인 중...")
            if not self.check_login_and_navigate(url_to_use):
                self.log("로그인 실패. 스크래핑을 중단합니다.")
                return pd.DataFrame()

            # 현재 날짜 가져오기
            today = datetime.now().strftime("%Y/%m/%d")
            self.log(f"현재 날짜: {today}, 오늘 출고 예정인 데이터만 가져옵니다.")

            # 데이터 추출 함수 정의
            def extract_shipment_data(row):
                try:
                    # 발주출고예상일자 추출
                    pickup_date = row.find_element(By.CSS_SELECTOR, "td:nth-child(15)").text.strip()

                    # 발주출고예상일자가 오늘인 데이터만 추출
                    if pickup_date and pickup_date == today:
                        # 판매자 정보 미리 추출하여 로그에 표시
                        seller = row.find_element(By.CSS_SELECTOR, "td:nth-child(4)").text.strip()
                        item = row.find_element(By.CSS_SELECTOR, "td:nth-child(6)").text.strip()
                        order_number = row.find_element(
                            By.CSS_SELECTOR, "td:nth-child(12)"
                        ).text.strip()

                        self.log(f"데이터 추출 중: {seller} - {item} (발주번호: {order_number})")

                        # 각 컬럼의 데이터 추출
                        row_data = {
                            "사진": (
                                row.find_element(
                                    By.CSS_SELECTOR, "td:nth-child(1) img"
                                ).get_attribute("src")
                                if self._element_exists(row, "td:nth-child(1) img")
                                else ""
                            ),
                            "프린트": row.find_element(
                                By.CSS_SELECTOR, "td:nth-child(2)"
                            ).text.strip(),
                            "ID": row.find_element(By.CSS_SELECTOR, "td:nth-child(3)").text.strip(),
                            "ID_URL": self._get_link_url(row, "td:nth-child(3) a"),
                            "판매자": seller,
                            "판매자_URL": self._get_link_url(row, "td:nth-child(4) a"),
                            "판매자 동대문주소": row.find_element(
                                By.CSS_SELECTOR, "td:nth-child(5)"
                            ).text.strip(),
                            "아이템": item,
                            "아이템_URL": self._get_link_url(row, "td:nth-child(6) a"),
                            "스와치 보관함": row.find_element(
                                By.CSS_SELECTOR, "td:nth-child(7)"
                            ).text.strip(),
                            "컬러순서": row.find_element(
                                By.CSS_SELECTOR, "td:nth-child(8)"
                            ).text.strip(),
                            "컬러코드": row.find_element(
                                By.CSS_SELECTOR, "td:nth-child(9)"
                            ).text.strip(),
                            "판매방식": row.find_element(
                                By.CSS_SELECTOR, "td:nth-child(10)"
                            ).text.strip(),
                            "발주수량": row.find_element(
                                By.CSS_SELECTOR, "td:nth-child(11)"
                            ).text.strip(),
                            "발주번호": order_number,
                            "발주번호_URL": self._get_link_url(row, "td:nth-child(12) a"),
                            "주문번호": row.find_element(
                                By.CSS_SELECTOR, "td:nth-child(13)"
                            ).text.strip(),
                            "주문번호_URL": self._get_link_url(row, "td:nth-child(13) a"),
                            "최종출고일자": row.find_element(
                                By.CSS_SELECTOR, "td:nth-child(14)"
                            ).text.strip(),
                            "발주출고예상일자": pickup_date,
                            "발주배송수단": row.find_element(
                                By.CSS_SELECTOR, "td:nth-child(16)"
                            ).text.strip(),
                            "판매자발송수단": row.find_element(
                                By.CSS_SELECTOR, "td:nth-child(17)"
                            ).text.strip(),
                            "발주상태": row.find_element(
                                By.CSS_SELECTOR, "td:nth-child(18)"
                            ).text.strip(),
                        }

                        return row_data
                except NoSuchElementException as e:
                    self.log(f"행 데이터 추출 실패: {str(e)}")

                return None  # 조건에 맞지 않는 데이터는 None 반환

            # 페이지네이션 처리하며 데이터 스크래핑
            self.log("스크래핑 시작. 모든 페이지를 확인합니다...")
            shipment_data = self.paginate_and_scrape(extract_shipment_data)

            # DataFrame 생성
            df = pd.DataFrame(shipment_data)
            if not df.empty:
                df["메시지 상태"] = ""
                self.log(f"스크래핑 완료! 총 {len(df)}개 데이터 추출됨")

                # 판매자별 발주 데이터 요약 출력
                self._log_shipment_summary(df)
            else:
                self.log("스크래핑 완료했으나 출고 예정 데이터가 없습니다.")

            return df

        except Exception as e:
            self.log(f"입고 대기 데이터 스크래핑 중 예상치 못한 오류: {str(e)}")
            return pd.DataFrame()

    def _log_shipment_summary(self, df):
        """판매자별 출고 확인 필요 현황 요약 로깅"""
        self.log("\n=== 판매자별 출고 확인 필요 현황 ===")
        for seller in sorted(df["판매자"].unique()):
            seller_orders = df[df["판매자"] == seller]
            order_summary = [
                f"- 발주번호: {num} (출고예상일: {date})"
                for num, date in zip(seller_orders["발주번호"], seller_orders["발주출고예상일자"])
            ]

            self.log(
                f"""
■ {seller}
  - 출고 확인 필요 건수: {len(seller_orders)}건
  - 출고 목록:
    {chr(10).join(order_summary)}
"""
            )

        # 전체 요약
        self.log(
            f"""
=== 전체 요약 ===
- 총 출고 확인 필요 건수: {len(df)}건
- 판매자 수: {len(df['판매자'].unique())}개
"""
        )

    def _element_exists(self, parent, selector):
        """특정 셀렉터가 존재하는지 확인하는 헬퍼 메서드"""
        try:
            parent.find_element(By.CSS_SELECTOR, selector)
            return True
        except NoSuchElementException:
            return False

    def _get_link_url(self, parent, selector):
        """링크 URL을 가져오는 헬퍼 메서드"""
        try:
            link = parent.find_element(By.CSS_SELECTOR, selector)
            return link.get_attribute("href")
        except NoSuchElementException:
            return ""
