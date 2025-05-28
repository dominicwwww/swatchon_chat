"""
로그인 서비스 - base_scraper.py와 동일한 로그인 로직
"""
import time
from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from core.config import ConfigManager
from core.constants import ConfigKey
from services.base_chromedriver import BaseChromeDriver

class LoginService:
    def __init__(self, config=None, driver=None):
        self.config = config if config else ConfigManager()
        self.driver = driver
        self.chrome_driver = None
        
        # URL 설정
        self.login_url = self.config.get(ConfigKey.SWATCHON_ADMIN_URL.value)
        self.receive_url = self.config.get(ConfigKey.RECEIVE_SCRAPING_URL.value)
        
        # 로그인 정보
        self.username = self.config.get(ConfigKey.SWATCHON_USERNAME.value)
        self.password = self.config.get(ConfigKey.SWATCHON_PASSWORD.value)
        
        print("로그인 서비스 초기화 중...")
        print(f"로그인 URL 설정: {self.login_url}")
        print(f"입고 URL 설정: {self.receive_url}")
        print(f"로그인 정보 확인 - 사용자명: {self.username}, 비밀번호: {'******' if self.password else 'None'}")

    def check_login_and_navigate(self, target_url=None):
        """로그인 상태 확인 후 타겟 페이지로 이동"""
        if not target_url:
            target_url = self.receive_url
            
        if not target_url:
            print("타겟 URL이 없습니다. 설정에서 URL을 확인하세요.")
            return False
        
        login_needed = False
        
        # 드라이버가 없거나 로그인 상태가 아닌 경우
        if not self.driver:
            print("드라이버가 초기화되지 않았습니다. 로그인이 필요합니다.")
            login_needed = True
        elif "admin.swatchon.me" not in self.driver.current_url:
            print("SwatchOn 관리자 페이지에 있지 않습니다. 로그인이 필요합니다.")
            login_needed = True
            
        if login_needed:
            if not self.login():
                print("로그인 실패")
                return False
                
        # 페이지 이동
        return self.navigate_to_page(target_url)

    def navigate_to_page(self, url):
        """특정 페이지로 이동"""
        try:
            if not url:
                print("이동할 URL이 제공되지 않았습니다.")
                return False
                
            print(f"페이지 이동 시도: {url}")
            
            # 페이지 이동
            try:
                self.driver.get(url)
                time.sleep(2)  # 페이지 로드 대기
            except Exception as e:
                print(f"페이지 이동 중 오류: {str(e)}")
                return False
            
            # 현재 URL과 요청한 URL 비교
            current_url = self.driver.current_url
            
            # URL에 로그인 페이지가 포함되어 있으면 로그인 세션이 끊긴 것
            if "sign_in" in current_url:
                print("세션이 만료되었습니다. 다시 로그인해야 합니다.")
                if self.login():
                    print("재로그인 성공, 페이지 다시 이동 시도")
                    try:
                        self.driver.get(url)
                        time.sleep(2)
                    except Exception as e:
                        print(f"재로그인 후 페이지 이동 중 오류: {str(e)}")
                        return False
                else:
                    print("재로그인 실패")
                    return False
            
            print(f"페이지 이동 완료: {self.driver.current_url}")
            return True
        except Exception as e:
            print(f"페이지 이동 실패: {str(e)}")
            return False

    def login(self):
        """스와치온 관리자 페이지 로그인 - base_scraper.py와 동일한 로직"""
        try:
            print("로그인 시도 중...")
            print(f"로그인 정보 재확인 - 사용자명: {self.username}, 비밀번호 존재: {bool(self.password)}")
            
            if not self.driver:
                print("ChromeDriver 설정 중...")
                self.chrome_driver = BaseChromeDriver(headless=False)
                self.driver = self.chrome_driver.setup_driver()
                if not self.driver:
                    print("ChromeDriver 설정 실패")
                    return None
                print("ChromeDriver 설정 완료")
            
            # 로그인 페이지로 이동
            try:
                print(f"로그인 시도: {self.login_url}")
                print("브라우저에서 로그인 페이지로 이동 중...")
                self.driver.get(self.login_url)
                time.sleep(2)
            except Exception as url_error:
                print(f"로그인 중 오류 발생: {str(url_error)}")
                return None
            
            # 이미 관리자 페이지에 로그인되어 있는지 확인
            if "admin.swatchon.me" in self.driver.current_url and "/users/sign_in" not in self.driver.current_url:
                print("이미 로그인되어 있습니다.")
                return self.driver
            
            # 로그인 페이지로 리디렉션 필요한 경우 체크
            if "/users/sign_in" not in self.driver.current_url:
                try:
                    print("로그인 페이지 이동 중...")
                    login_link = self.driver.find_element(By.LINK_TEXT, "Login")
                    login_link.click()
                    time.sleep(2)
                except Exception as redirect_error:
                    print(f"로그인 페이지 리디렉션 중 오류: {str(redirect_error)}")
            
            # 로그인 폼 입력
            try:
                username_input = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.ID, "user_email"))
                )
                password_input = self.driver.find_element(By.ID, "user_password")
                login_button = self.driver.find_element(By.NAME, "commit")
                print("로그인 폼 찾기 완료")
            except Exception as form_error:
                print(f"로그인 폼 요소를 찾을 수 없음: {str(form_error)}")
                return None
            
            # 로그인 정보 확인
            if not self.username or not self.password:
                print("로그인 정보가 부족합니다.")
                return None
                
            # 로그인 시도
            try:
                print(f"로그인 시도 (username: {self.username})")
                username_input.clear()
                username_input.send_keys(self.username)
                password_input.clear()
                password_input.send_keys(self.password)
                login_button.click()
                time.sleep(3)  # 페이지 로드 대기
            except Exception as input_error:
                print(f"로그인 폼 입력 중 오류: {str(input_error)}")
                return None
            
            # 로그인 결과 확인
            print(f"현재 URL: {self.driver.current_url}")
            if "sign_in" in self.driver.current_url:
                print("로그인 실패: 로그인 페이지에 머물러 있습니다.")
                return None
                
            print(f"로그인 성공. 현재 URL: {self.driver.current_url}")
            return self.driver
            
        except Exception as e:
            print(f"로그인 중 오류 발생: {str(e)}")
            try:
                if self.chrome_driver:
                    self.chrome_driver.close_driver()
            except Exception:
                pass
            return None

    def quit(self):
        """드라이버 종료"""
        try:
            if self.chrome_driver:
                self.chrome_driver.close_driver()
                self.chrome_driver = None
            self.driver = None
            print("로그인 서비스 종료")
        except Exception as e:
            print(f"로그인 서비스 종료 중 오류: {str(e)}")

    def __del__(self):
        """소멸자에서 드라이버 종료"""
        try:
            self.quit()
        except Exception:
            pass 