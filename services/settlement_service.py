from services.login_service import LoginService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import datetime
import os
import time

class SettlementService:
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.login_service = None
        self.driver = None

    def _ensure_logged_in(self):
        """로그인 상태 확인 및 필요시 로그인"""
        if self.driver is None:
            try:
                print("로그인 서비스 초기화 중...")
                self.login_service = LoginService(self.config_manager)
                print("로그인 시도 중...")
                self.driver = self.login_service.login()
                
                # 로그인 결과 확인
                if self.driver is None:
                    raise Exception("로그인 실패: 드라이버가 생성되지 않았습니다.")
                
                print("로그인 완료, 드라이버 준비됨")
                time.sleep(2)  # 로그인 완료 대기
                
            except Exception as e:
                print(f"로그인 중 오류 발생: {str(e)}")
                import traceback
                traceback.print_exc()
                
                # 정리 작업
                if self.login_service:
                    try:
                        self.login_service.quit()
                    except:
                        pass
                    self.login_service = None
                self.driver = None
                
                raise Exception(f"로그인 실패: {str(e)}")

    def create_settlement(self, data):
        try:
            print("정산서 생성 시작...")
            self._ensure_logged_in()
            
            # 드라이버 상태 재확인
            if self.driver is None:
                raise Exception("드라이버가 초기화되지 않았습니다.")
            
            # data: (file_path, unit_number, total_amount, supply_amount, vat_amount, year, month)
            admin_url = self.config_manager.get("swatchon_admin_url", "https://admin.swatchon.me")
            settlement_url = f"{admin_url}/settlements/new?owner_id=173&owner_type=SettlementOwner"
            
            print(f"정산서 페이지로 이동: {settlement_url}")
            self.driver.get(settlement_url)
            time.sleep(3)  # 페이지 로드 대기 시간 증가
            
            # 페이지가 완전히 로드될 때까지 대기
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.ID, "settlement_bank_account_id"))
                )
                print("페이지 로딩 완료 확인됨")
            except Exception as e:
                print(f"페이지 로딩 대기 중 오류: {e}")
                # 페이지 소스 일부 출력하여 디버깅
                print("현재 페이지 제목:", self.driver.title)
                print("현재 URL:", self.driver.current_url)

            print("계좌 선택 중...")
            # 계좌 선택 (첫 번째 실제 계좌 선택 - 빈 값이 아닌 첫 번째 옵션)
            self.driver.find_element(By.ID, "settlement_bank_account_id").click()
            self.driver.find_element(By.CSS_SELECTOR, "#settlement_bank_account_id option[value]:not([value=''])").click()
            time.sleep(1)  # 선택 완료 대기

            print("공급가액 및 세액 입력 중...")
            # 공급가, 세액 입력
            self.driver.find_element(By.ID, "settlement_supply_amount").clear()
            self.driver.find_element(By.ID, "settlement_supply_amount").send_keys(str(data[3]))
            self.driver.find_element(By.ID, "settlement_tax").clear()
            self.driver.find_element(By.ID, "settlement_tax").send_keys(str(data[4]))
            time.sleep(1)  # 입력 완료 대기

            print("메모 입력 중...")
            # 메모 입력
            today = datetime.datetime.now().strftime("%y%m%d")
            memo = f"{today} Dominic) {data[5]}년 {data[6]:02d}월 다산물류센터 관리비: {data[1]}"
            self.driver.find_element(By.ID, "settlement_additional_info").clear()
            self.driver.find_element(By.ID, "settlement_additional_info").send_keys(memo)
            time.sleep(1)  # 입력 완료 대기

            print("파일 첨부 중...")
            # 파일 첨부 - input[type='file'] 선택자 사용 (확인된 작동 선택자)
            file_path = os.path.abspath(data[0])
            
            try:
                # 작동하는 것으로 확인된 선택자 직접 사용
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']"))
                )
                file_input = self.driver.find_element(By.CSS_SELECTOR, "input[type='file']")
                print("파일 입력 요소 찾음")
                
                # 파일 업로드
                file_input.send_keys(file_path)
                print(f"파일 업로드 시작: {file_path}")
                time.sleep(3)  # 파일 업로드 대기
                
            except Exception as e:
                print(f"파일 첨부 중 오류: {str(e)}")
                raise Exception(f"파일 첨부 실패: {str(e)}")

            print("파일 업로드 완료 대기 중...")
            # S3 업로드 완료 대기 (프로그레스바가 사라질 때까지)
            WebDriverWait(self.driver, 30).until(
                lambda d: d.find_element(By.ID, "shared-progress").value_of_css_property("display") == "none"
            )
            time.sleep(1)  # 추가 대기

            print("정산서 생성 버튼 클릭...")
            # 생성 버튼 찾기
            submit_button = self.driver.find_element(By.NAME, "commit")
            
            # 버튼이 보이도록 스크롤
            self.driver.execute_script("arguments[0].scrollIntoView(true);", submit_button)
            time.sleep(1)  # 스크롤 완료 대기
            
            # JavaScript로 클릭 (더 안전한 방법)
            self.driver.execute_script("arguments[0].click();", submit_button)
            time.sleep(2)  # 제출 완료 대기

            print("정산서 생성 완료 확인 중...")
            # 성공 여부 확인 (예: 페이지 이동, 알림 등)
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".alert, .notice, .card"))
            )
            print("정산서 생성 성공!")
            return True

        except Exception as e:
            print(f"정산서 자동화 오류: {e}")
            import traceback
            traceback.print_exc()
            return False

    def quit(self):
        """서비스 종료 및 리소스 정리"""
        print("SettlementService 종료 중...")
        if self.login_service:
            self.login_service.quit()
            self.login_service = None
        self.driver = None
        print("SettlementService 종료 완료") 