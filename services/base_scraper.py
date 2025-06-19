"""
스크래핑 서비스 기본 클래스 - 웹 스크래핑 공통 기능
"""
import time
import os
import traceback
import threading
import atexit
import re

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from core.config import ConfigManager
from core.logger import get_logger
from core.constants import ConfigKey, SpreadsheetConfigKey
from ui.components.log_widget import LOG_INFO, LOG_DEBUG, LOG_WARNING, LOG_ERROR, LOG_SUCCESS

# 전역 드라이버 레지스트리 - 프로세스 종료 시 정리하기 위함
_active_drivers = []

# 종료 시 모든 드라이버 정리
def _cleanup_all_drivers():
    """종료 시 열려있는 모든 드라이버 정리"""
    global _active_drivers
    for driver in _active_drivers[:]:
        try:
            if driver:
                driver.quit()
        except Exception:
            pass
    _active_drivers = []

# 프로세스 종료 시 드라이버 정리 함수 등록
atexit.register(_cleanup_all_drivers)

class BaseScraper:
    """기본 스크래퍼 클래스"""
    
    def __init__(self, user_info=None):
        self.driver = None
        self.logger = get_logger(__name__)
        self.config = ConfigManager()
        self.update_user_info(user_info)
        
        # 모든 URL은 설정에서만 가져옴
        self.login_url = self.config.get(ConfigKey.SWATCHON_ADMIN_URL.value)
        self.receive_url = self.config.get(ConfigKey.RECEIVE_SCRAPING_URL.value)
        
        # 다른 모든 URL 변수도 receive_url로 통일
        self.shipment_request_url = self.receive_url
        self.shipment_confirm_url = self.receive_url
        
        # 최신 webdriver-manager 4.0.2 사용
        self.webdriver_path = ChromeDriverManager().install()
        self.log_function = None
        
        # 상태 업데이트 콜백 초기화
        self.status_callback = None
        self.current_page = 0
        self.total_pages = 0  # 예상 페이지 수 (알 수 없는 경우 0)
        
        # 종료 시 자동 정리를 위한 감시 타이머
        self._watchdog_timer = None
        self._last_activity = time.time()
        self._is_active = False
    
    def set_status_callback(self, callback_function):
        """상태 업데이트 콜백 함수 설정
        
        Args:
            callback_function: 콜백 함수. 매개변수로 (상태 메시지, 진행률)을 받음
        """
        self.status_callback = callback_function
    
    def update_status(self, status_message, progress_value=None):
        """상태 업데이트 및 콜백 호출
        
        Args:
            status_message (str): 현재 상태 메시지
            progress_value (float, optional): 진행률 (0.0 ~ 1.0)
        """
        # 활동 시간 업데이트
        self._last_activity = time.time()
        
        if self.status_callback is not None:
            try:
                self.status_callback(status_message, progress_value)
            except Exception as e:
                self.log(f"상태 업데이트 콜백 호출 중 오류: {str(e)}", LOG_WARNING)
    
    def update_user_info(self, user_info):
        """유저 정보 업데이트"""
        if user_info:
            self.username = user_info.get("username")
            self.password = user_info.get("password")
        else:
            self.username = self.config.get(ConfigKey.SWATCHON_USERNAME.value)
            self.password = self.config.get(ConfigKey.SWATCHON_PASSWORD.value)
    
    def log(self, message, log_type=LOG_INFO):
        """로그 메시지 출력"""
        self.logger.info(message)
        if hasattr(self, "log_function") and self.log_function:
            try:
                self.log_function(message, log_type)
            except Exception as e:
                # 로그 함수 호출 실패 시 기본 로거에만 기록
                self.logger.warning(f"로그 함수 호출 실패: {str(e)}")
    
    def _start_watchdog(self):
        """감시 타이머 시작 - 일정 시간 활동이 없으면 경고만 표시"""
        if self._watchdog_timer:
            try:
                self._watchdog_timer.cancel()
            except Exception:
                pass
            
        self._is_active = True
        self._last_activity = time.time()
        
        def watchdog_check():
            if not self._is_active:
                return
                
            current_time = time.time()
            idle_time = current_time - self._last_activity
            
            # 5분(300초) 이상 활동이 없으면 경고만 표시
            if idle_time > 300:
                self.log("감시 타이머: 장시간 활동 없음, 작업이 멈춘 것 같습니다.", LOG_WARNING)
                # 드라이버는 종료하지 않음
                
            # 다음 감시 타이머 설정 (30초 후)
            if self._is_active:
                self._watchdog_timer = threading.Timer(30, watchdog_check)
                self._watchdog_timer.daemon = True
                self._watchdog_timer.start()
                
        # 첫 감시 타이머 시작
        self._watchdog_timer = threading.Timer(30, watchdog_check)
        self._watchdog_timer.daemon = True
        self._watchdog_timer.start()
    
    def _stop_watchdog(self):
        """감시 타이머 중지"""
        self._is_active = False
        if self._watchdog_timer:
            try:
                self._watchdog_timer.cancel()
            except Exception:
                pass
            self._watchdog_timer = None
    
    def setup_driver(self):
        """Selenium 드라이버 초기화"""
        try:
            chrome_options = Options()
            
            # 헤드리스 모드 설정
            chrome_options.add_argument("--headless=new")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-software-rasterizer")
            
            # 웹 드라이버 세션 기본 옵션
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--disable-notifications")
            
            # 대기 시간 관련 설정
            chrome_options.page_load_strategy = "normal"
            
            # 사용자 에이전트 설정
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36")
            
            service = Service(self.webdriver_path)
            
            # 드라이버 생성
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # 타임아웃 설정
            self.driver.set_page_load_timeout(60)
            self.driver.set_script_timeout(30)
            
            # 활성 드라이버 목록에 추가
            global _active_drivers
            _active_drivers.append(self.driver)
            
            # 감시 타이머 시작
            self._start_watchdog()
            
            return True
        except Exception as e:
            self.log(f"드라이버 초기화 실패: {str(e)}", LOG_ERROR)
            return False
    
    def login(self):
        """스와치온 관리자 페이지 로그인"""
        try:
            if not self.driver:
                self.log("드라이버 초기화 중...")
                if not self.setup_driver():
                    self.log("드라이버 초기화 실패", LOG_ERROR)
                    return False
                self.log("드라이버 초기화 완료")
            
            # 로그인 페이지로 이동
            try:
                self.log(f"로그인 페이지 접속 시도: {self.login_url}")
                self.driver.get(self.login_url)
                time.sleep(2)
            except Exception as url_error:
                self.log(f"로그인 페이지 접속 실패: {str(url_error)}", LOG_ERROR)
                return False
            
            # 이미 관리자 페이지에 로그인되어 있는지 확인
            if "admin.swatchon.me" in self.driver.current_url and "/users/sign_in" not in self.driver.current_url:
                self.log("이미 로그인되어 있습니다.")
                return True
            
            # 로그인 페이지로 리디렉션 필요한 경우 체크
            if "/users/sign_in" not in self.driver.current_url:
                try:
                    self.log("로그인 페이지 이동 중...")
                    login_link = self.driver.find_element(By.LINK_TEXT, "Login")
                    login_link.click()
                    time.sleep(2)
                except Exception as redirect_error:
                    self.log(f"로그인 페이지 리디렉션 중 오류: {str(redirect_error)}", LOG_WARNING)
            
            # 로그인 폼 입력
            try:
                username_input = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.ID, "user_email"))
                )
                password_input = self.driver.find_element(By.ID, "user_password")
                login_button = self.driver.find_element(By.NAME, "commit")
                self.log("로그인 폼 찾기 완료")
            except Exception as form_error:
                self.log(f"로그인 폼 요소를 찾을 수 없음: {str(form_error)}", LOG_ERROR)
                return False
            
            # 로그인 정보 확인
            if not self.username or not self.password:
                self.log("로그인 정보가 부족합니다.", LOG_ERROR)
                return False
                
            # 로그인 시도
            try:
                self.log(f"로그인 시도 (username: {self.username})")
                username_input.clear()
                username_input.send_keys(self.username)
                password_input.clear()
                password_input.send_keys(self.password)
                login_button.click()
                time.sleep(3)  # 페이지 로드 대기
            except Exception as input_error:
                self.log(f"로그인 폼 입력 중 오류: {str(input_error)}", LOG_ERROR)
                return False
            
            # 로그인 결과 확인
            if "sign_in" in self.driver.current_url:
                self.log("로그인 실패: 로그인 페이지에 머물러 있습니다.", LOG_ERROR)
                return False
                
            self.log(f"로그인 성공. 현재 URL: {self.driver.current_url}")
            return True
            
        except Exception as e:
            self.log(f"로그인 실패: {str(e)}", LOG_ERROR)
            try:
                if self.driver:
                    self.close_driver()
            except Exception:
                pass
            return False
    
    def navigate_to_page(self, url):
        """특정 페이지로 이동"""
        try:
            if not url:
                self.log("이동할 URL이 제공되지 않았습니다.", LOG_ERROR)
                return False
                
            self.log(f"페이지 이동 시도: {url}")
            
            # 현재 URL 로깅
            before_url = self.driver.current_url
            
            # 페이지 이동
            try:
                self.driver.get(url)
                time.sleep(2)  # 페이지 로드 대기
            except Exception as e:
                self.log(f"페이지 이동 중 오류: {str(e)}", LOG_ERROR)
                return False
            
            # 현재 URL과 요청한 URL 비교
            current_url = self.driver.current_url
            
            # URL에 로그인 페이지가 포함되어 있으면 로그인 세션이 끊긴 것
            if "sign_in" in current_url:
                self.log("세션이 만료되었습니다. 다시 로그인해야 합니다.", LOG_WARNING)
                if self.login():
                    self.log("재로그인 성공, 페이지 다시 이동 시도")
                    try:
                        self.driver.get(url)
                        time.sleep(2)
                    except Exception as e:
                        self.log(f"재로그인 후 페이지 이동 중 오류: {str(e)}", LOG_ERROR)
                        return False
                else:
                    self.log("재로그인 실패", LOG_ERROR)
                    return False
            
            self.log(f"페이지 이동 완료: {self.driver.current_url}")
            return True
        except Exception as e:
            self.log(f"페이지 이동 실패: {str(e)}", LOG_ERROR)
            return False
    
    def check_login_and_navigate(self, target_url):
        """로그인 상태 확인 후 타겟 페이지로 이동"""
        if not target_url:
            self.log("타겟 URL이 없습니다. 설정에서 URL을 확인하세요.", LOG_ERROR)
            return False
        
        login_needed = False
        
        # 드라이버가 없거나 로그인 상태가 아닌 경우
        if not self.driver:
            self.log("드라이버가 초기화되지 않았습니다. 로그인이 필요합니다.")
            login_needed = True
        elif "admin.swatchon.me" not in self.driver.current_url:
            self.log("SwatchOn 관리자 페이지에 있지 않습니다. 로그인이 필요합니다.")
            login_needed = True
            
        if login_needed:
            if not self.login():
                self.log("로그인 실패", LOG_ERROR)
                return False
                
        # 페이지 이동
        return self.navigate_to_page(target_url)
    
    def paginate_and_scrape(self, extract_data_func):
        """페이지네이션 처리 및 데이터 스크래핑 공통 함수"""
        data = []
        page_num = 1
        
        while True:
            self.log(f"\n=== 페이지 {page_num} 스크래핑 시작 ===")
            
            # 현재 페이지 업데이트
            self.current_page = page_num
            self.update_status(f"페이지 {page_num} 스크래핑 중...", 
                             0.1 + (0.8 * ((page_num - 1) / max(20, page_num * 2))))
            
            try:
                # 스크린샷 캡처 (디버깅용)
                try:
                    screenshot_path = f"page_{page_num}_before.png"
                    self.driver.save_screenshot(screenshot_path)
                    self.log(f"페이지 {page_num} 스크래핑 전 스크린샷 저장됨", LOG_DEBUG)
                except Exception:
                    pass
                
                # 테이블 찾기 - 타임아웃 증가 및 페이지 로드 확인 강화
                self.log("테이블 로드 대기 중...")
                try:
                    # 테이블을 찾기 전에 페이지가 완전히 로드될 때까지 대기 (타임아웃 증가)
                    self.log("페이지 완전 로드 대기 중...")
                    WebDriverWait(self.driver, 20).until(
                        lambda driver: driver.execute_script("return document.readyState") == "complete"
                    )
                    self.log(f"페이지 완전히 로드됨. 현재 URL: {self.driver.current_url}")
                    
                    # 페이지 로드 후 잠시 대기 추가 (JS 초기화 등을 위한 시간)
                    time.sleep(2)
                    
                    self.log("테이블 요소 탐색 중...")
                    table = WebDriverWait(self.driver, 25).until(  # 타임아웃 증가
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".table"))
                    )
                    self.log("테이블을 찾았습니다.")
                except Exception as e:
                    self.log(f"테이블을 찾지 못했습니다: {str(e)}", LOG_ERROR)
                    self.log("페이지 소스 확인 중...")
                    
                    # 페이지가 로그인 페이지로 리디렉션 되었는지 확인
                    if "sign_in" in self.driver.current_url:
                        self.log("로그인 세션이 만료되었습니다. 재로그인 시도 중...", LOG_WARNING)
                        if self.login():
                            self.log("재로그인 성공. 페이지 다시 로드 중...")
                            self.navigate_to_page(self.driver.current_url)
                            continue
                        else:
                            self.log("재로그인 실패", LOG_ERROR)
                            break
                    
                    # 테이블을 찾을 수 없는 경우 디버깅을 위한 스크린샷 저장
                    try:
                        screenshot_path = f"error_no_table_page_{page_num}.png"
                        self.driver.save_screenshot(screenshot_path)
                        self.log(f"테이블 없음 오류 스크린샷 저장됨: {screenshot_path}", LOG_ERROR)
                    except Exception:
                        pass
                    
                    # 페이지 소스의 일부를 로그에 출력
                    try:
                        self.log(f"페이지 소스 일부: {self.driver.page_source[:500]}...", LOG_DEBUG)
                    except Exception:
                        pass
                    
                    # 이 시점에서 테이블을 찾을 수 없으면 종료
                    break
                
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
                        self.log(f"행 데이터 추출 실패: {str(e)}", LOG_WARNING)
                        continue
                    except Exception as e:
                        self.log(f"행 처리 중 예상치 못한 오류: {str(e)}", LOG_ERROR)
                        continue
                
                self.log(f"페이지 {page_num}에서 {extracted_count}개 데이터 추출 완료", LOG_SUCCESS)
                
                # 페이지 전환 전 상태 업데이트
                self.update_status(f"페이지 {page_num} 완료, 다음 페이지 확인 중...", 
                                 0.1 + (0.8 * (page_num / max(20, page_num * 2))))
                
                # 다음 페이지로 이동
                try:
                    try:
                        next_button = self.driver.find_element(
                            By.CSS_SELECTOR, 'nav .pagination a.page-link[rel="next"]'
                        )
                        
                        if not next_button:
                            self.log("다음 페이지 버튼이 없음 - 마지막 페이지에 도달")
                            break
                    except NoSuchElementException:
                        self.log("다음 페이지 버튼을 찾을 수 없음 (마지막 페이지일 수 있음)")
                        break
                    
                    self.log("다음 페이지로 이동 중...")
                    current_url = self.driver.current_url
                    
                    # JavaScript 클릭이 실패할 경우를 대비하여 href 속성을 백업
                    next_page_url = next_button.get_attribute("href")
                    
                    # 클릭으로 이동 시도
                    try:
                        self.driver.execute_script("arguments[0].click();", next_button)
                        time.sleep(5)  # 페이지 로드 대기 시간 증가
                    except Exception as click_err:
                        self.log(f"다음 버튼 클릭 실패: {str(click_err)}", LOG_WARNING)
                        # href 속성으로 이동 시도
                        if next_page_url:
                            self.log(f"대안으로 href를 사용하여 이동 시도: {next_page_url}", LOG_INFO)
                            self.driver.get(next_page_url)
                            time.sleep(5)  # 페이지 로드 대기 시간 증가
                    
                    # 현재 URL 확인
                    new_url = self.driver.current_url
                    
                    # URL이 변경되지 않았으면 문제가 있는 것
                    if current_url == new_url:
                        self.log("URL이 변경되지 않았습니다. 페이지 이동에 문제가 있을 수 있습니다.", LOG_WARNING)
                        
                        # 직접 URL에서 page 파라미터를 수정해서 이동 시도
                        if "page=" in current_url:
                            # 정규식으로 페이지 번호 추출 및 수정
                            import re
                            try:
                                page_match = re.search(r'page=(\d+)', current_url)
                                if page_match:
                                    current_page = int(page_match.group(1))
                                    next_page_url = re.sub(r'page=\d+', f'page={current_page+1}', current_url)
                                    self.log(f"정규식으로 수정된 URL로 이동 시도: {next_page_url}", LOG_INFO)
                                    self.driver.get(next_page_url)
                                    time.sleep(5)  # 페이지 로드 대기 시간 증가
                                    new_url = self.driver.current_url
                            except Exception as re_err:
                                self.log(f"정규식 처리 중 오류: {str(re_err)}", LOG_WARNING)
                                # 원래 방식으로 폴백
                                try:
                                    current_page = int(current_url.split("page=")[1].split("&")[0])
                                    next_page_url = current_url.replace(f"page={current_page}", f"page={current_page+1}")
                                    self.log(f"수정된 URL로 이동 시도: {next_page_url}", LOG_INFO)
                                    self.driver.get(next_page_url)
                                    time.sleep(5)  # 페이지 로드 대기 시간 증가
                                    new_url = self.driver.current_url
                                except Exception as split_err:
                                    self.log(f"URL 파싱 오류: {str(split_err)}", LOG_ERROR)
                        else:
                            # page 파라미터가 없으면 추가
                            try:
                                if "?" in current_url:
                                    next_page_url = f"{current_url}&page=2"
                                else:
                                    next_page_url = f"{current_url}?page=2"
                                
                                self.log(f"페이지 파라미터 추가하여 이동 시도: {next_page_url}", LOG_INFO)
                                self.driver.get(next_page_url)
                                time.sleep(5)  # 페이지 로드 대기 시간 증가
                                new_url = self.driver.current_url
                            except Exception as url_err:
                                self.log(f"URL 수정 오류: {str(url_err)}", LOG_ERROR)
                        
                        # 여전히 URL이 변경되지 않았으면 마지막 페이지로 간주하고 종료
                        if current_url == new_url:
                            self.log("페이지 이동 실패 - 마지막 페이지로 간주하고 종료", LOG_WARNING)
                            break
                    
                    self.log(f"페이지 이동: {current_url} -> {new_url}")
                    page_num += 1
                except NoSuchElementException:
                    self.log("마지막 페이지 도달")
                    self.update_status("마지막 페이지 완료", 0.9)
                    break
                except Exception as e:
                    self.log(f"페이지 이동 중 오류: {str(e)}", LOG_ERROR)
                    import traceback
                    self.log(f"상세 오류: {traceback.format_exc()}", LOG_ERROR)
                    self.update_status(f"페이지 {page_num} 처리 중 오류 발생", None)
                    break
                
            except Exception as e:
                self.log(f"페이지 {page_num} 스크래핑 중 오류: {str(e)}", LOG_ERROR)
                import traceback
                self.log(f"상세 오류: {traceback.format_exc()}", LOG_ERROR)
                self.update_status(f"페이지 {page_num} 처리 중 오류 발생", None)
                break
        
        self.log(f"\n=== 스크래핑 완료 ===\n총 {len(data)}개 데이터 수집", LOG_SUCCESS)
        self.update_status(f"스크래핑 완료 (총 {len(data)}개 데이터)", 1.0)
        return data
    
    def close_driver(self):
        """드라이버 종료"""
        if self.driver:
            try:
                # 활성 드라이버 목록에서 제거
                global _active_drivers
                if self.driver in _active_drivers:
                    _active_drivers.remove(self.driver)
                
                # 감시 타이머 중지
                self._stop_watchdog()
                
                # 드라이버 종료
                self.driver.quit()
                self.log("웹 드라이버 종료")
                self.driver = None
            except Exception as e:
                self.log(f"드라이버 종료 중 오류: {str(e)}", LOG_WARNING)
                # 프로세스 강제 종료는 제거하고 None 처리만 수행
                self.driver = None
    
    def __del__(self):
        """소멸자에서 드라이버 종료"""
        try:
            # 감시 타이머 중지
            self._stop_watchdog()
            
            # 드라이버 종료
            self.close_driver()
        except Exception:
            pass

    # 스크래퍼 객체가 gc에 의해 수집되더라도 드라이버 종료를 보장하는 추가 안전장치
    def __exit__(self, exc_type, exc_val, exc_tb):
        """컨텍스트 매니저 종료 시 호출"""
        try:
            # 종료 원인 로깅
            if exc_type:
                self.log(f"컨텍스트 종료 원인: {exc_type.__name__}: {exc_val}", LOG_WARNING)
            
            # 감시 타이머 중지
            self._stop_watchdog()
            
            # 드라이버 종료
            self.close_driver()
        except Exception:
            pass
        
    def __enter__(self):
        """컨텍스트 매니저 시작 시 호출"""
        # 감시 타이머 시작
        if self.driver:
            self._start_watchdog()
        return self

    def _get_link_url(self, parent, selector):
        """링크 URL을 가져오는 헬퍼 메서드"""
        try:
            link = parent.find_element(By.CSS_SELECTOR, selector)
            return link.get_attribute("href")
        except NoSuchElementException:
            return ""
    
    def _element_exists(self, parent, selector):
        """특정 셀렉터가 존재하는지 확인하는 헬퍼 메서드"""
        try:
            parent.find_element(By.CSS_SELECTOR, selector)
            return True
        except NoSuchElementException:
            return False 