"""
ChromeDriver 기본 클래스 - base_scraper.py와 동일한 설정 (헤드리스 제외)
"""
import time
import os
import atexit
import requests
import zipfile
import io
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

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

class BaseChromeDriver:
    def __init__(self, headless=False):
        self.driver = None
        self.headless = headless
        self.webdriver_path = self._get_chromedriver_path()

    def _get_chrome_version(self):
        """설치된 Chrome 버전 확인"""
        try:
            import subprocess
            import re
            
            # Windows에서 Chrome 버전 확인
            result = subprocess.run([
                'reg', 'query', 'HKEY_CURRENT_USER\\Software\\Google\\Chrome\\BLBeacon', 
                '/v', 'version'
            ], capture_output=True, text=True, shell=True)
            
            if result.returncode == 0:
                version_match = re.search(r'version\s+REG_SZ\s+(\d+\.\d+\.\d+\.\d+)', result.stdout)
                if version_match:
                    version = version_match.group(1)
                    print(f"Chrome 버전 확인: {version}")
                    return version
            
            # 대안 방법: Chrome 실행 파일에서 버전 확인
            chrome_paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
            ]
            
            for chrome_path in chrome_paths:
                if os.path.exists(chrome_path):
                    result = subprocess.run([chrome_path, '--version'], capture_output=True, text=True)
                    if result.returncode == 0:
                        version_match = re.search(r'(\d+\.\d+\.\d+\.\d+)', result.stdout)
                        if version_match:
                            version = version_match.group(1)
                            print(f"Chrome 버전 확인 (실행파일): {version}")
                            return version
            
        except Exception as e:
            print(f"Chrome 버전 확인 실패: {str(e)}")
        
        return None

    def _download_chromedriver_from_chrome_for_testing(self, version):
        """Chrome for Testing API에서 ChromeDriver 다운로드"""
        try:
            # 메이저 버전만 추출 (예: 137.0.7151.93 -> 137)
            major_version = version.split('.')[0]
            
            # Chrome for Testing API에서 사용 가능한 버전 확인
            api_url = "https://googlechromelabs.github.io/chrome-for-testing/known-good-versions-with-downloads.json"
            response = requests.get(api_url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # 호환되는 ChromeDriver 버전 찾기
                compatible_version = None
                for version_info in reversed(data['versions']):  # 최신 버전부터 확인
                    if version_info['version'].startswith(major_version + '.'):
                        downloads = version_info.get('downloads', {})
                        chromedriver_downloads = downloads.get('chromedriver', [])
                        
                        # Windows 64bit 버전 찾기
                        for download in chromedriver_downloads:
                            if download['platform'] == 'win64':
                                compatible_version = version_info['version']
                                download_url = download['url']
                                break
                        
                        if compatible_version:
                            break
                
                if compatible_version and download_url:
                    print(f"호환 ChromeDriver 버전 찾음: {compatible_version}")
                    print(f"다운로드 URL: {download_url}")
                    
                    # ChromeDriver 다운로드
                    response = requests.get(download_url, timeout=30)
                    if response.status_code == 200:
                        # ZIP 파일 압축 해제
                        with zipfile.ZipFile(io.BytesIO(response.content)) as zip_file:
                            # chromedriver.exe 파일 추출
                            chromedriver_path = os.path.join(os.getcwd(), "chromedriver.exe")
                            
                            # ZIP 내부 구조 확인
                            for file_info in zip_file.filelist:
                                if file_info.filename.endswith('chromedriver.exe'):
                                    with zip_file.open(file_info) as source, open(chromedriver_path, 'wb') as target:
                                        target.write(source.read())
                                    print(f"ChromeDriver 다운로드 완료: {chromedriver_path}")
                                    return chromedriver_path
                            
                            print("ZIP 파일에서 chromedriver.exe를 찾을 수 없습니다.")
                    else:
                        print(f"ChromeDriver 다운로드 실패: HTTP {response.status_code}")
                else:
                    print(f"Chrome {major_version} 버전과 호환되는 ChromeDriver를 찾을 수 없습니다.")
            else:
                print(f"Chrome for Testing API 접근 실패: HTTP {response.status_code}")
                
        except Exception as e:
            print(f"Chrome for Testing에서 ChromeDriver 다운로드 실패: {str(e)}")
        
        return None

    def _get_chromedriver_path(self):
        """ChromeDriver 경로 확인 - 여러 방법으로 시도"""
        # 1. 기존 chromedriver.exe가 있는지 확인
        local_driver = os.path.join(os.getcwd(), "chromedriver.exe")
        if os.path.exists(local_driver):
            print(f"기존 ChromeDriver 사용: {local_driver}")
            return local_driver
        
        # 2. Chrome 버전 확인 후 Chrome for Testing에서 다운로드
        chrome_version = self._get_chrome_version()
        if chrome_version:
            print(f"Chrome 버전 {chrome_version}과 호환되는 ChromeDriver 다운로드 시도...")
            driver_path = self._download_chromedriver_from_chrome_for_testing(chrome_version)
            if driver_path:
                return driver_path
        
        # 3. webdriver_manager로 설치 시도
        try:
            print("webdriver_manager로 ChromeDriver 설치 시도...")
            path = ChromeDriverManager().install()
            print(f"ChromeDriver 설치 성공: {path}")
            return path
        except Exception as e:
            print(f"webdriver_manager 설치 실패: {str(e)}")
        
        # 4. 환경변수에서 찾기
        env_path = os.environ.get("CHROMEDRIVER_PATH")
        if env_path and os.path.exists(env_path):
            print(f"환경변수에서 ChromeDriver 찾음: {env_path}")
            return env_path
        
        # 5. 시스템 PATH에서 찾기
        import shutil
        system_driver = shutil.which("chromedriver")
        if system_driver:
            print(f"시스템 PATH에서 ChromeDriver 찾음: {system_driver}")
            return system_driver
        
        # 6. 마지막 시도: 강제로 특정 버전 설치
        try:
            print("호환 가능한 ChromeDriver 버전으로 강제 설치 시도...")
            from webdriver_manager.chrome import ChromeDriverManager
            path = ChromeDriverManager(version="114.0.5735.90").install()
            print(f"호환 버전 ChromeDriver 설치 성공: {path}")
            return path
        except Exception as e:
            print(f"호환 버전 설치도 실패: {str(e)}")
        
        raise Exception("ChromeDriver를 설치할 수 없습니다. Chrome 브라우저가 설치되어 있는지 확인하세요.")

    def setup_driver(self):
        """Selenium 드라이버 초기화 - base_scraper.py와 동일한 설정"""
        try:
            chrome_options = Options()
            
            # 헤드리스 모드 설정 (선택적)
            if self.headless:
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
            
            print(f"ChromeDriver 경로: {self.webdriver_path}")
            service = Service(self.webdriver_path)
            
            # 드라이버 생성
            print("ChromeDriver 생성 중...")
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            print("ChromeDriver 생성 성공")
            
            # 타임아웃 설정
            self.driver.set_page_load_timeout(60)
            self.driver.set_script_timeout(30)
            
            # 활성 드라이버 목록에 추가
            global _active_drivers
            _active_drivers.append(self.driver)
            
            return self.driver
            
        except Exception as e:
            print(f"드라이버 초기화 실패: {str(e)}")
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
                self.driver = None
            return None

    def close_driver(self):
        """드라이버 종료"""
        if self.driver:
            try:
                # 활성 드라이버 목록에서 제거
                global _active_drivers
                if self.driver in _active_drivers:
                    _active_drivers.remove(self.driver)
                
                # 드라이버 종료
                self.driver.quit()
                print("웹 드라이버 종료")
                self.driver = None
            except Exception as e:
                print(f"드라이버 종료 중 오류: {str(e)}")
                self.driver = None

    def __del__(self):
        """소멸자에서 드라이버 종료"""
        try:
            self.close_driver()
        except Exception:
            pass 