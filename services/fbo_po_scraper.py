"""
FBO 발주 확인 스크래퍼 - 발주 확인 데이터 스크래핑 전용
"""
from typing import List, Dict, Any
from services.base_scraper import BaseScraper
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, WebDriverException, StaleElementReferenceException
from ui.components.log_widget import LOG_INFO, LOG_ERROR, LOG_WARNING, LOG_SUCCESS, LOG_DEBUG
from core.config import ConfigManager
import time
from selenium.common.exceptions import TimeoutException

class FboPoScraper(BaseScraper):
    """
    FBO 발주 확인 데이터 스크래퍼
    """
    def __init__(self, user_info=None):
        super().__init__(user_info)
        config = ConfigManager()
        self.po_url = config.get("fbo_po_url")
        self.max_retries = 3  # 최대 재시도 횟수

    def _is_browser_alive(self) -> bool:
        """브라우저가 살아있는지 확인"""
        try:
            if not self.driver:
                return False
            self.driver.current_url
            return True
        except WebDriverException:
            return False
        except Exception:
            return False

    def _ensure_browser_ready(self) -> bool:
        """브라우저가 준비되어 있는지 확인하고 필요시 재연결"""
        if not self._is_browser_alive():
            self.log("브라우저 세션이 끊어졌습니다. 재연결을 시도합니다.", LOG_WARNING)
            try:
                if self.driver:
                    self.driver.quit()
            except:
                pass
            self.driver = None
            return self.check_login_and_navigate(self.po_url)
        return True

    def scrape_po_list(self) -> List[Dict[str, Any]]:
        """
        FBO 발주 확인 데이터 스크래핑
        Returns: List[Dict[str, Any]]
        """
        self.log("FBO 발주 확인 데이터 스크래핑 시작", LOG_INFO)
        if not self.check_login_and_navigate(self.po_url):
            self.log("발주 확인 페이지 이동 실패", LOG_ERROR)
            return []
        
        def extract_data(row):
            try:
                cols = row.find_elements(By.TAG_NAME, "td")
                if len(cols) < 13:  # 13개 컬럼 확인
                    return None
                
                # 각 컬럼의 텍스트 추출 (badge 안의 텍스트 포함)
                def get_text_content(col):
                    # badge가 있으면 badge 안의 텍스트, 없으면 일반 텍스트
                    badge = col.find_elements(By.CLASS_NAME, "badge")
                    if badge:
                        return badge[0].text.strip()
                    return col.text.strip()
                
                # URL 추출 함수
                def get_link_text(col):
                    link = col.find_elements(By.TAG_NAME, "a")
                    if link:
                        return link[0].text.strip()
                    return col.text.strip()
                
                # 가격에서 숫자만 추출
                def extract_price(price_text):
                    import re
                    # "KRW 52,800" -> "52800"
                    numbers = re.findall(r'[\d,]+', price_text)
                    if numbers:
                        return numbers[0].replace(',', '')
                    return "0"
                
                return {
                    "purchase_code": get_link_text(cols[0]),           # 발주번호 (링크 텍스트)
                    "purchase_type": get_text_content(cols[1]),        # 발주거래타입 (badge)
                    "created_at": cols[2].text.strip(),               # 생성시각
                    "order_code": get_link_text(cols[3]),             # 주문 (링크 텍스트)
                    "seller": get_link_text(cols[4]),                 # 판매자 (링크 텍스트)
                    "in_charge": cols[5].text.strip(),                # 발주담당자
                    "quantity": cols[6].text.strip(),                 # 발주수량
                    "price": extract_price(cols[7].text.strip()),     # 공급가액 (숫자만)
                    "price_changeable": get_text_content(cols[8]),    # 단가변경여부 (badge)
                    "delay_allowable": get_text_content(cols[9]),     # 지연허용여부 (badge)
                    "status": get_text_content(cols[10]),             # 상태 (badge)
                    "payment_status": get_text_content(cols[11]),     # 정산상태 (badge)
                    "internal_memo": cols[12].text.strip()           # 내부메모
                }
            except Exception as e:
                self.log(f"행 데이터 추출 오류: {str(e)}", LOG_ERROR)
                return None
        
        data = self.paginate_and_scrape(extract_data)
        self.log(f"FBO 발주 확인 데이터 스크래핑 완료: {len(data)}건", LOG_INFO)
        return data

    def scrape_purchase_products(self, purchase_code: str) -> List[Dict[str, Any]]:
        """
        특정 발주번호의 발주프로덕트 목록 스크래핑
        
        Args:
            purchase_code: 발주번호 (예: "1A1C3")
            
        Returns:
            List[Dict[str, Any]]: 발주프로덕트 목록
        """
        try:
            self.log(f"발주번호 {purchase_code}의 프로덕트 목록 스크래핑 시작", LOG_INFO)
            
            # 브라우저 준비 상태 확인
            if not self._ensure_browser_ready():
                self.log("브라우저 초기화 실패", LOG_ERROR)
                return []
            
            # 현재 URL 저장 (복귀용)
            original_url = self.driver.current_url
            
            # 발주번호 링크 찾기 및 클릭
            retry_count = 0
            products = []
            
            while retry_count < self.max_retries:
                try:
                    # 브라우저 상태 재확인
                    if not self._is_browser_alive():
                        if not self._ensure_browser_ready():
                            break
                    
                    # 여러 방법으로 발주번호 링크 찾기
                    purchase_link = None
                    
                    # 방법 1: 정확한 텍스트 매칭
                    purchase_links = self.driver.find_elements(By.XPATH, f"//a[normalize-space(text())='{purchase_code}']")
                    if purchase_links:
                        purchase_link = purchase_links[0]
                        self.log(f"방법 1로 발주번호 {purchase_code} 링크 발견", LOG_DEBUG)
                    
                    # 방법 2: 텍스트 포함 검색
                    if not purchase_link:
                        purchase_links = self.driver.find_elements(By.XPATH, f"//a[contains(text(), '{purchase_code}')]")
                        if purchase_links:
                            # 정확히 일치하는 링크 찾기
                            for link in purchase_links:
                                if link.text.strip() == purchase_code:
                                    purchase_link = link
                                    self.log(f"방법 2로 발주번호 {purchase_code} 링크 발견", LOG_DEBUG)
                                    break
                    
                    # 방법 3: CSS 선택자로 테이블 내 첫 번째 컬럼의 링크들 확인
                    if not purchase_link:
                        table_links = self.driver.find_elements(By.CSS_SELECTOR, "table.table tbody tr td:first-child a")
                        for link in table_links:
                            if link.text.strip() == purchase_code:
                                purchase_link = link
                                self.log(f"방법 3으로 발주번호 {purchase_code} 링크 발견", LOG_DEBUG)
                                break
                    
                    if not purchase_link:
                        if retry_count == 0:
                            # 첫 번째 시도에서 실패 시 페이지 새로고침
                            self.log(f"발주번호 {purchase_code} 링크를 찾을 수 없습니다. 페이지를 새로고침합니다.", LOG_WARNING)
                            self.driver.refresh()
                            WebDriverWait(self.driver, 10).until(
                                EC.presence_of_element_located((By.CLASS_NAME, "table"))
                            )
                            time.sleep(1.0)  # 페이지 안정화 대기
                            retry_count += 1
                            continue
                        else:
                            self.log(f"발주번호 {purchase_code}의 링크를 찾을 수 없습니다.", LOG_ERROR)
                            break
                    
                    # 링크 클릭
                    products = self._click_and_scrape_products(purchase_link, purchase_code, original_url)
                    break  # 성공 시 반복 종료
                    
                except Exception as e:
                    retry_count += 1
                    self.log(f"발주번호 {purchase_code} 스크래핑 시도 {retry_count} 실패: {str(e)}", LOG_WARNING)
                    if retry_count < self.max_retries:
                        time.sleep(2.0)  # 재시도 전 대기
                        # 브라우저 상태 복구 시도
                        try:
                            if original_url and self.driver.current_url != original_url:
                                self.driver.get(original_url)
                                WebDriverWait(self.driver, 5).until(
                                    EC.presence_of_element_located((By.CLASS_NAME, "table"))
                                )
                        except:
                            self._ensure_browser_ready()
                    else:
                        self.log(f"발주번호 {purchase_code} 최대 재시도 횟수 초과", LOG_ERROR)
                        break
            
            return products
            
        except Exception as e:
            self.log(f"발주프로덕트 스크래핑 중 오류: {str(e)}", LOG_ERROR)
            return []
        finally:
            # 원래 페이지로 복귀
            self._return_to_original_page(original_url if 'original_url' in locals() else None)

    def _click_and_scrape_products(self, purchase_link, purchase_code: str, original_url: str) -> List[Dict[str, Any]]:
        """발주번호 링크 클릭 후 프로덕트 데이터 스크래핑"""
        try:
            # 링크 클릭 전 브라우저 상태 확인
            if not self._ensure_browser_ready():
                self.log("브라우저 상태 확인 실패", LOG_ERROR)
                return []
            
            # 링크 클릭 전 URL 저장
            self.log(f"발주번호 {purchase_code} 링크를 클릭합니다.", LOG_INFO)
            
            # 링크의 href 속성 확인
            href = purchase_link.get_attribute("href")
            self.log(f"클릭할 링크 URL: {href}", LOG_DEBUG)
            
            # 여러 방법으로 클릭 시도
            click_success = False
            
            # 방법 1: 일반 클릭
            try:
                purchase_link.click()
                click_success = True
                self.log("일반 클릭 성공", LOG_DEBUG)
            except (StaleElementReferenceException, WebDriverException) as e:
                self.log(f"일반 클릭 실패: {str(e)}", LOG_DEBUG)
            
            # 방법 2: JavaScript 클릭
            if not click_success:
                try:
                    self.driver.execute_script("arguments[0].click();", purchase_link)
                    click_success = True
                    self.log("JavaScript 클릭 성공", LOG_DEBUG)
                except Exception as e:
                    self.log(f"JavaScript 클릭 실패: {str(e)}", LOG_DEBUG)
            
            # 방법 3: 직접 URL 이동
            if not click_success and href:
                try:
                    self.driver.get(href)
                    click_success = True
                    self.log("직접 URL 이동 성공", LOG_DEBUG)
                except Exception as e:
                    self.log(f"직접 URL 이동 실패: {str(e)}", LOG_DEBUG)
            
            if not click_success:
                self.log(f"발주번호 {purchase_code} 링크 클릭에 모든 방법이 실패했습니다.", LOG_ERROR)
                return []
            
            # 페이지 이동 확인 및 로드 대기
            return self._wait_and_extract_products(purchase_code, original_url)
            
        except Exception as e:
            self.log(f"링크 클릭 및 프로덕트 스크래핑 중 오류: {str(e)}", LOG_ERROR)
            return []

    def _wait_and_extract_products(self, purchase_code: str, original_url: str) -> List[Dict[str, Any]]:
        """페이지 로드 대기 후 프로덕트 데이터 추출"""
        try:
            # URL 변경 확인 (최대 5초 대기)
            url_changed = False
            for i in range(10):  # 0.5초씩 10번 = 5초
                if self.driver.current_url != original_url:
                    url_changed = True
                    self.log(f"페이지 이동 확인됨: {self.driver.current_url}", LOG_DEBUG)
                    break
                time.sleep(0.5)
            
            if not url_changed:
                self.log(f"페이지 이동이 확인되지 않았습니다. 현재 URL: {self.driver.current_url}", LOG_WARNING)
            
            # 페이지 완전 로드 대기
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # 추가로 테이블 로드 대기
            time.sleep(1.0)
            
            # 현재 페이지가 발주 상세 페이지인지 확인
            page_title = self.driver.title
            current_url = self.driver.current_url
            self.log(f"이동된 페이지 - 제목: {page_title}, URL: {current_url}", LOG_DEBUG)
            
            # 발주 상세 페이지 여부 확인 (URL에 purchase_code가 포함되어 있는지 등)
            if purchase_code not in current_url and "purchase" not in current_url.lower():
                self.log(f"올바른 발주 상세 페이지가 아닐 수 있습니다.", LOG_WARNING)
            
            return self._extract_products_from_table(purchase_code)
            
        except TimeoutException:
            self.log(f"발주번호 {purchase_code} 상세 페이지 로드 시간 초과", LOG_ERROR)
            return []
        except Exception as e:
            self.log(f"페이지 로드 및 데이터 추출 중 오류: {str(e)}", LOG_ERROR)
            return []

    def _extract_products_from_table(self, purchase_code: str) -> List[Dict[str, Any]]:
        """테이블에서 프로덕트 데이터 추출"""
        try:
            # 발주프로덕트 테이블 찾기
            product_table = None
            tables = self.driver.find_elements(By.TAG_NAME, "table")
            
            self.log(f"페이지에서 {len(tables)}개의 테이블을 발견했습니다.", LOG_DEBUG)
            
            for i, table in enumerate(tables):
                try:
                    # 테이블에 데이터가 있는지 확인
                    tbody = table.find_element(By.TAG_NAME, "tbody")
                    rows = tbody.find_elements(By.TAG_NAME, "tr")
                    
                    if len(rows) == 0:
                        self.log(f"테이블 {i+1}: 데이터 행이 없음", LOG_DEBUG)
                        continue
                    
                    # 첫 번째 행의 컬럼 수 확인
                    first_row_cols = rows[0].find_elements(By.TAG_NAME, "td")
                    self.log(f"테이블 {i+1}: {len(first_row_cols)}개 컬럼, {len(rows)}개 행", LOG_DEBUG)
                    
                    # 헤더 확인
                    try:
                        thead = table.find_element(By.TAG_NAME, "thead")
                        headers = thead.find_elements(By.TAG_NAME, "th")
                        header_texts = [th.text.strip() for th in headers]
                        self.log(f"테이블 {i+1} 헤더: {header_texts[:8]}...", LOG_DEBUG)
                        
                        # 프로덕트 테이블 특징: 많은 컬럼 수 (15개 이상), 특정 헤더 포함
                        if (len(header_texts) >= 10 and 
                            (any(h in ["사진", "ID", "판매방식", "퀄리티", "컬러", "프로덕트"] for h in header_texts) or
                             len(first_row_cols) >= 15)):  # 컬럼 수로도 판단
                            product_table = table
                            self.log(f"발주프로덕트 테이블을 찾았습니다. (테이블 {i+1})", LOG_INFO)
                            break
                    except NoSuchElementException:
                        # 헤더가 없는 테이블인 경우 컬럼 수로만 판단
                        if len(first_row_cols) >= 15:  # 프로덕트 테이블은 컬럼이 많음
                            product_table = table
                            self.log(f"헤더 없는 프로덕트 테이블을 찾았습니다. (테이블 {i+1})", LOG_INFO)
                            break
                        
                except Exception as e:
                    self.log(f"테이블 {i+1} 확인 중 오류: {str(e)}", LOG_DEBUG)
                    continue
            
            if not product_table:
                self.log(f"발주번호 {purchase_code}의 프로덕트 테이블을 찾을 수 없습니다.", LOG_ERROR)
                self.log(f"현재 페이지 제목: {self.driver.title}", LOG_DEBUG)
                
                # 페이지 내용 일부 확인 (디버깅용)
                try:
                    page_text = self.driver.find_element(By.TAG_NAME, "body").text[:500]
                    self.log(f"페이지 내용 일부: {page_text}...", LOG_DEBUG)
                except:
                    pass
                
                return []
            
            # 테이블에서 데이터 추출
            products = []
            tbody = product_table.find_element(By.TAG_NAME, "tbody")
            rows = tbody.find_elements(By.TAG_NAME, "tr")
            
            self.log(f"발주프로덕트 테이블에서 {len(rows)}개의 행을 발견했습니다.", LOG_INFO)
            
            for row_idx, row in enumerate(rows):
                try:
                    cols = row.find_elements(By.TAG_NAME, "td")
                    if len(cols) < 10:  # 최소 컬럼 수 확인 (15->10으로 완화)
                        self.log(f"행 {row_idx+1}: 컬럼 수 부족 ({len(cols)}개)", LOG_DEBUG)
                        continue
                    
                    # 이미지 URL 추출
                    try:
                        img_element = cols[0].find_element(By.TAG_NAME, "img")
                        image_url = img_element.get_attribute("src")
                    except:
                        image_url = ""
                    
                    # ID 추출 (링크에서)
                    try:
                        id_link = cols[1].find_element(By.TAG_NAME, "a")
                        product_id = id_link.text.strip()
                    except:
                        product_id = cols[1].text.strip()
                    
                    # badge 텍스트 추출 함수
                    def get_badge_text(col):
                        try:
                            badge = col.find_element(By.CLASS_NAME, "badge")
                            return badge.text.strip()
                        except:
                            return col.text.strip()
                    
                    # 링크 텍스트 추출 함수
                    def get_link_text(col):
                        try:
                            link = col.find_element(By.TAG_NAME, "a")
                            return link.text.strip()
                        except:
                            return col.text.strip()
                    
                    # 가격에서 콤마 제거
                    def clean_price(price_text):
                        return price_text.replace(',', '').strip()
                    
                    # 안전한 텍스트 추출 함수
                    def safe_text(col_index):
                        try:
                            return cols[col_index].text.strip() if len(cols) > col_index else ""
                        except:
                            return ""
                    
                    product_data = {
                        "purchase_code": purchase_code,  # 부모 발주번호
                        "product_id": product_id,
                        "image_url": image_url,
                        "sale_type": get_badge_text(cols[2]) if len(cols) > 2 else "",        # 판매방식
                        "quality_name": get_link_text(cols[3]) if len(cols) > 3 else "",     # 퀄리티
                        "color_number": safe_text(4),       # 컬러순서
                        "color_code": safe_text(5),         # 컬러코드
                        "color_name": safe_text(6),         # 컬러
                        "product_code": get_link_text(cols[7]) if len(cols) > 7 else "",     # 프로덕트
                        "quantity": safe_text(8),           # 발주수량
                        "total_price": clean_price(safe_text(9)),   # 발주금액(공급가)
                        "unit_price": clean_price(safe_text(10)),  # 단가
                        "original_unit_price": clean_price(safe_text(11)),  # 최초단가
                        "price_changeable": get_badge_text(cols[12]) if len(cols) > 12 else "",       # 단가변경여부
                        "expected_delivery_days": safe_text(13),    # 예상납기(일)
                        "status": get_badge_text(cols[14]) if len(cols) > 14 else "",                 # 발주상태
                        "delivery_method": safe_text(15),           # 발주배송수단
                        "seller_delivery_method": safe_text(16),    # 판매자발송수단
                        "expected_shipping_date": safe_text(17),    # 발주출고예상일자
                        "labdip_expected_shipping_date": safe_text(18),  # 랩딥발주출고예상일자
                        "failure_info": safe_text(19)  # 발주실패정보
                    }
                    
                    products.append(product_data)
                    
                except Exception as e:
                    self.log(f"프로덕트 행 {row_idx+1} 데이터 추출 오류: {str(e)}", LOG_WARNING)
                    continue
            
            self.log(f"발주번호 {purchase_code}의 프로덕트 {len(products)}건 스크래핑 완료", LOG_SUCCESS)
            return products
            
        except Exception as e:
            self.log(f"테이블에서 데이터 추출 중 오류: {str(e)}", LOG_ERROR)
            return []

    def _return_to_original_page(self, original_url: str = None):
        """원래 페이지로 복귀"""
        try:
            if self.driver and hasattr(self, 'driver'):
                # 브라우저가 여전히 활성 상태인지 확인
                try:
                    self.driver.current_url  # 브라우저 연결 상태 확인
                    
                    # 뒤로가기로 원래 페이지로 복귀
                    self.driver.back()
                    
                    # 페이지 로드 대기
                    WebDriverWait(self.driver, 8).until(
                        EC.presence_of_element_located((By.CLASS_NAME, "table"))
                    )
                    time.sleep(0.5)  # 추가 안정화 대기
                    
                except Exception as browser_check_error:
                    # 브라우저 연결이 끊어진 경우 재연결 시도
                    self.log(f"브라우저 연결 끊어짐 감지, 재연결 시도: {str(browser_check_error)}", LOG_WARNING)
                    if not self.check_login_and_navigate(self.po_url):
                        self.log("브라우저 재연결 실패", LOG_ERROR)
                    
        except Exception as e:
            self.log(f"원래 페이지로 복귀 중 오류: {str(e)}", LOG_WARNING)
            # 복귀 실패 시 원래 페이지로 직접 이동
            try:
                if self.driver and original_url:
                    self.driver.get(original_url)
                    WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.CLASS_NAME, "table"))
                    )
            except:
                pass 