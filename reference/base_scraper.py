import time

import pandas as pd
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from src.utils.config_manager import ConfigManager
from src.utils.logger import get_logger
from src.utils.ui_utils import flush_events
from services.base_scraper import BaseScraper

logger = get_logger(__name__)


class BaseScraper:
    def __init__(self, user_info=None):
        self.driver = None
        self.logger = logger
        self.config = ConfigManager()
        self.update_user_info(user_info)
        self.login_url = self.config.get("LOGIN_URL")
        self.webdriver_path = self.config.get("WEBDRIVER_PATH", ChromeDriverManager().install())
        self.log_function = None

    def update_user_info(self, user_info):
        """유저 정보 업데이트"""
        if user_info:
            self.username = user_info.get("id")
            self.password = user_info.get("pw")
        else:
            self.username = self.config.get("SWATCHON_USERNAME")
            self.password = self.config.get("SWATCHON_PASSWORD")

    def log(self, message):
        """로거와 UI에 모두 로그 메시지 출력"""
        self.logger.debug(message)
        if hasattr(self, "log_function") and self.log_function:
            self.log_function(message)
            flush_events()  # UI 즉시 업데이트

    def setup_driver(self):
        """Selenium 드라이버 초기화"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.page_load_strategy = "eager"

        service = Service(self.webdriver_path)
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.driver.set_page_load_timeout(30)

    def login(self):
        """스와치온 관리자 페이지 로그인"""
        try:
            if not self.driver:
                self.log("드라이버 초기화 중...")
                self.setup_driver()
                self.log("드라이버 초기화 완료")

            self.log(f"로그인 페이지 접속 시도: {self.login_url}")
            self.driver.get(self.login_url)
            self.log(f"현재 URL: {self.driver.current_url}")

            self.log("로그인 폼 찾는 중...")
            username_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "user_email"))
            )
            password_input = self.driver.find_element(By.ID, "user_password")
            login_button = self.driver.find_element(By.NAME, "commit")
            self.log("로그인 폼 찾기 완료")

            self.log(f"로그인 시도 (username: {self.username})")
            username_input.send_keys(self.username)
            password_input.send_keys(self.password)
            login_button.click()

            self.log("로그인 후 페이지 로드 대기 중...")
            WebDriverWait(self.driver, 30).until(EC.url_contains("admin.swatchon.me"))
            self.log(f"로그인 성공. 현재 URL: {self.driver.current_url}")
            return True

        except Exception as e:
            self.log(f"로그인 실패: {str(e)}")
            return False

    def navigate_to_page(self, url):
        """특정 페이지로 이동"""
        try:
            self.log(f"페이지 이동 시도: {url}")
            self.driver.get(url)
            time.sleep(1)
            self.log(f"페이지 이동 완료. 현재 URL: {self.driver.current_url}")
            return True
        except Exception as e:
            self.log(f"페이지 이동 실패: {str(e)}")
            return False

    def check_login_and_navigate(self, target_url):
        """로그인 상태 확인 후 타겟 페이지로 이동"""
        # 로그인 체크 및 시도
        self.log("로그인 상태 확인 중...")
        if not self.driver or "admin.swatchon.me" not in self.driver.current_url:
            self.log("로그인 필요")
            if not self.login():
                self.log("로그인 실패")
                return False

        # 타겟 페이지로 이동
        return self.navigate_to_page(target_url)

    def paginate_and_scrape(self, extract_data_func):
        """페이지네이션 처리 및 데이터 스크래핑 공통 함수"""
        data = []
        page_num = 1

        while True:
            self.log(f"\n=== 페이지 {page_num} 스크래핑 시작 ===")
            try:
                # 테이블 찾기
                self.log("테이블 로드 대기 중...")
                table = WebDriverWait(self.driver, 8).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".table"))
                )

                # 행 데이터 찾기
                rows = table.find_elements(By.CSS_SELECTOR, "tbody tr")
                row_count = len(rows)
                self.log(f"페이지 {page_num}에서 {row_count}개 행 발견")

                if not rows:
                    self.log("더 이상 데이터가 없음")
                    break

                # 데이터 추출 (전달된 함수 활용)
                extracted_count = 0
                for i, row in enumerate(rows):
                    try:
                        row_data = extract_data_func(row)
                        if row_data:  # None이 아닌 경우에만 추가
                            data.append(row_data)
                            extracted_count += 1

                        # 진행 상황 업데이트 (10개 행마다 한 번)
                        if (i + 1) % 10 == 0 or i == len(rows) - 1:
                            self.log(f"페이지 {page_num} 진행 중: {i+1}/{len(rows)} 행 처리 완료")

                    except NoSuchElementException as e:
                        self.log(f"행 데이터 추출 실패: {str(e)}")
                        continue

                self.log(f"페이지 {page_num}에서 {extracted_count}개 데이터 추출 완료")

                # 다음 페이지로 이동
                try:
                    next_button = self.driver.find_element(
                        By.CSS_SELECTOR, 'nav .pagination a.page-link[rel="next"]'
                    )
                    if not next_button:
                        self.log("다음 페이지 버튼이 없음")
                        break

                    self.log("다음 페이지로 이동 중...")
                    current_url = self.driver.current_url
                    self.driver.execute_script("arguments[0].click();", next_button)
                    time.sleep(1)
                    new_url = self.driver.current_url
                    self.log(f"페이지 이동: {current_url} -> {new_url}")
                    page_num += 1
                except NoSuchElementException:
                    self.log("마지막 페이지 도달")
                    break

            except Exception as e:
                self.log(f"페이지 {page_num} 스크래핑 중 오류: {str(e)}")
                break

        self.log(f"\n=== 스크래핑 완료 ===\n총 {len(data)}개 데이터 수집")
        return data

    def close_driver(self):
        """드라이버 종료"""
        if self.driver:
            self.driver.quit()
            self.driver = None

    def __del__(self):
        """소멸자에서 드라이버 종료"""
        self.close_driver()
