"""
공통 상수 정의 모듈
"""
from enum import Enum

# 앱 정보
APP_NAME = "SwatchOn 카카오톡 자동화"
APP_VERSION = "1.0.0"
APP_AUTHOR = "SwatchOn"

# 파일 경로
DEFAULT_CONFIG_PATH = "config.json"
DEFAULT_TEMPLATES_PATH = "resources/default_templates.json"
USER_DATA_DIR = "SwatchOn"  # 사용자 문서 폴더 내 디렉토리명

# UI 관련 상수
UI_MAIN_WIDTH = 1000
UI_MAIN_HEIGHT = 700
UI_SIDEBAR_WIDTH_RATIO = 0.2  # 전체 너비의 20%
UI_LOG_HEIGHT_RATIO = 0.3  # 전체 높이의 30%

# 테이블 컬럼
SELLER_COLUMN_NAME = "판매자"
STATUS_COLUMN_NAME = "상태"
ORDER_NUMBER_COLUMN_NAME = "주문번호"

# 시간 관련
DEFAULT_TIMEOUT = 10  # 기본 타임아웃 (초)
DEFAULT_WAIT_TIME = 1  # 기본 대기 시간 (초)

# 로그 관련
MAX_LOG_LINES = 1000  # 최대 로그 라인 수
LOG_FORMAT = "[%(asctime)s] [%(levelname)s] [%(name)s] - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# 메시지 관련
DEFAULT_HEADER = "[SwatchOn]"
DEFAULT_FOOTER = "감사합니다.\nSwatchOn 팀 드림."

# API 필드명 상수
API_FIELDS = {
    "ID": "id",
    "IMAGE_URL": "image_url",
    "PRINT_URL": "print_url",
    "STORE_NAME": "store_name",
    "STORE_URL": "store_url",
    "STORE_ADDRESS": "store_address",
    "STORE_DDM_ADDRESS": "store_ddm_address",
    "QUALITY_CODE": "quality_code",
    "QUALITY_NAME": "quality_name",
    "QUALITY_URL": "quality_url",
    "SWATCH_PICKUPABLE": "swatch_pickupable",
    "SWATCH_STORAGE": "swatch_storage",
    "COLOR_NUMBER": "color_number",
    "COLOR_CODE": "color_code",
    "QUANTITY": "quantity",
    "ORDER_CODE": "order_code",
    "ORDER_URL": "order_url",
    "PURCHASE_CODE": "purchase_code",
    "PURCHASE_URL": "purchase_url",
    "LAST_PICKUP_AT": "last_pickup_at",
    "PICKUP_AT": "pickup_at",
    "DELIVERY_METHOD": "delivery_method",
    "LOGISTICS_COMPANY": "logistics_company",
    "STATUS": "status",
    "MESSAGE_STATUS": "message_status",
    "PRICE": "price",
    "UNIT_PRICE": "unit_price",
    "UNIT_PRICE_ORIGIN": "unit_price_origin",
    "ADDITIONAL_INFO": "additional_info",
    "CREATED_AT": "created_at",
    "UPDATED_AT": "updated_at"
}

# 주문 상세 정보 기본 형식
DEFAULT_ORDER_DETAILS_FORMAT = "[{quality_name}] | #{color_number} | {quantity}yd | {pickup_at} | {delivery_method}-{logistics_company}"

# 설정 키 이름 상수 - 일반 설정
class ConfigKey(Enum):
    # 일반 설정
    UI_THEME = "ui_theme"
    LOG_LEVEL = "log_level"
    SAVE_LOGS = "save_logs"
    LOGS_PATH = "logs_path"
    
    # 카카오톡 설정
    KAKAO_PATH = "kakao_path"
    AUTO_START_KAKAO = "auto_start_kakao"
    MESSAGE_DELAY = "message_delay"
    
    # API 설정
    GOOGLE_CREDENTIALS = "google_credentials"
    API_LIMIT = "api_limit"
    
    # 주소록 설정
    ADDRESS_BOOK_URL = "address_book_spreadsheet_url"
    ADDRESS_BOOK_SHEET = "address_book_sheet_name"
    
    # SwatchOn 관련
    SWATCHON_ADMIN_URL = "swatchon_admin_url"
    SWATCHON_USERNAME = "swatchon_username"
    SWATCHON_PASSWORD = "swatchon_password"
    
    # 스크래핑 URL 설정
    RECEIVE_SCRAPING_URL = "receive_scraping_url"
    
    # 기타 설정
    DEFAULT_WAIT_TIME = "default_wait_time"
    TEMPLATES_PATH = "templates_path"
    LAST_SECTION = "last_section"

# 스프레드시트 설정 키
class SpreadsheetConfigKey(Enum):
    # Google API 설정
    GOOGLE_CREDENTIALS = "google_credentials"
    
    # 주소록 관련
    ADDRESS_BOOK_URL = "address_book_spreadsheet_url"
    ADDRESS_BOOK_SHEET = "address_book_sheet_name"
    
    # FBO (Fabric Bulk Order) 관련
    FBO_SHIPMENT_REQUEST_URL = "fbo_shipment_request_spreadsheet_url"
    FBO_SHIPMENT_REQUEST_SHEET = "fbo_shipment_request_sheet_name"
    
    FBO_SHIPMENT_CONFIRM_URL = "fbo_shipment_confirm_spreadsheet_url"
    FBO_SHIPMENT_CONFIRM_SHEET = "fbo_shipment_confirm_sheet_name"
    
    FBO_PO_SHEET = "fbo_po_sheet_name"
    
    # 입고 관련
    FBO_RECEIVE_URL = "fbo_receive_spreadsheet_url"
    FBO_RECEIVE_SHEET = "fbo_receive_sheet_name"
    
    # SBO (Swatch Box Order) 관련
    SBO_PO_URL = "sbo_po_spreadsheet_url"
    SBO_PO_SHEET = "sbo_po_sheet_name"
    
    SBO_PICKUP_REQUEST_URL = "sbo_pickup_request_spreadsheet_url"
    SBO_PICKUP_REQUEST_SHEET = "sbo_pickup_request_sheet_name"

# 설정 매핑: SectionType과 SpreadsheetConfigKey 매핑
SECTION_SPREADSHEET_MAPPING = {
    "fbo_shipment_request": {
        "name": "FBO 출고 요청",
        "url_key": SpreadsheetConfigKey.FBO_SHIPMENT_REQUEST_URL.value,
        "sheet_key": SpreadsheetConfigKey.FBO_SHIPMENT_REQUEST_SHEET.value
    },
    "fbo_shipment_confirm": {
        "name": "FBO 출고 확인",
        "url_key": SpreadsheetConfigKey.FBO_SHIPMENT_CONFIRM_URL.value,
        "sheet_key": SpreadsheetConfigKey.FBO_SHIPMENT_CONFIRM_SHEET.value
    },
    "fbo_po": {
        "name": "FBO 발주 확인",
        "url_key": SpreadsheetConfigKey.FBO_PO_SHEET.value,
        "sheet_key": SpreadsheetConfigKey.FBO_PO_SHEET.value
    },
    "fbo_receive": {
        "name": "FBO 입고 확인",
        "url_key": SpreadsheetConfigKey.FBO_RECEIVE_URL.value,
        "sheet_key": SpreadsheetConfigKey.FBO_RECEIVE_SHEET.value
    },
    "sbo_po": {
        "name": "SBO 스와치 발주",
        "url_key": SpreadsheetConfigKey.SBO_PO_URL.value,
        "sheet_key": SpreadsheetConfigKey.SBO_PO_SHEET.value
    },
    "sbo_pickup_request": {
        "name": "SBO 픽업 요청",
        "url_key": SpreadsheetConfigKey.SBO_PICKUP_REQUEST_URL.value,
        "sheet_key": SpreadsheetConfigKey.SBO_PICKUP_REQUEST_SHEET.value
    }
}

# RemixIcon 사이드바 아이콘 경로 매핑
SECTION_ICON_PATHS = {
    "dashboard": "assets/icons/dashboard-line.svg",
    "fbo_shipment_request": "assets/icons/truck-line.svg",
    "fbo_shipment_confirm": "assets/icons/check-line.svg",
    "fbo_po": "assets/icons/file-list-2-line.svg",
    "sbo_po": "assets/icons/price-tag-3-line.svg",
    "sbo_pickup_request": "assets/icons/box-3-line.svg",
    "template": "assets/icons/layout-2-line.svg",
    "settings": "assets/icons/settings-3-line.svg",
}

# API 관련 상수
API_BASE_URL = "https://admin.swatchon.me/api"
# API 키는 환경변수나 설정파일에서 로드하도록 변경 권장
API_KEY = "CkhbWmgJV51nxuTsiKiHmel8QUuoHnxUtjSQ812FxEexVfen"

# API 엔드포인트
API_ENDPOINTS = {
    "purchase_products": "/purchase_products",
    "shipment_requests": "/shipment_requests",
    "shipment_confirmations": "/shipment_confirmations",
    "pickup_requests": "/pickup_requests",
    "purchase_confirms": "/purchase_products"
}

# API 헤더
API_HEADERS = {
    "X-Api-Key": API_KEY,
    "Content-Type": "application/json"
}

# 배송 방법 매핑
DELIVERY_METHODS = {
   "quick": "동대문 픽업",
   "logistics": "판매자 발송"
}

# 물류 회사 매핑
LOGISTICS_COMPANIES = {
    "kk": "경기택배",
    "is": "일신택배",
    "kd": "경동택배",
    "quick_truck": "퀵서비스",
    "None": "3 p.m.",  # 동대문 픽업의 경우
    "null": "3 p.m."   # null 값도 3 p.m.으로 처리
}

# 테이블 컬럼명 매핑
TABLE_COLUMN_NAMES = {
    "id": "ID",
    "image_url": "이미지",
    "print_url": "프린트",
    "store_name": "판매자",
    "store_url": "판매자URL",
    "store_address": "판매자주소",
    "store_ddm_address": "동대문주소",
    "quality_name": "QL",
    "quality_url": "QLURL",
    "quality_code": "QL코드",
    "swatch_pickupable": "스와치픽업",
    "swatch_storage": "스와치보관함",
    "color_number": "컬러순서",
    "color_code": "컬러코드",
    "quantity": "수량(yd)",
    "order_code": "주문코드",
    "order_url": "주문URL",
    "purchase_code": "발주번호",
    "purchase_url": "발주URL",
    "last_pickup_at": "최종출고일",
    "pickup_at": "출고일",
    "delivery_method": "배송방법",
    "logistics_company": "택배사",
    "status": "발주상태",
    "message_status": "메시지상태",
    "processed_at": "처리시각",
    "price": "총가격",
    "unit_price": "단가",
    "unit_price_origin": "원본단가",
    "additional_info": "메모",
    "created_at": "생성시각",
    "updated_at": "수정시각"
}

# 메시지 상태 한글 매핑
MESSAGE_STATUS_LABELS = {
    "pending": "대기중",
    "requested": "발주요청중",
    "sending": "전송중",
    "sent": "전송완료",
    "failed": "실패",
    "cancelled": "취소됨",
    "retry": "재시도"
}

# 테이블 공통 표시 설정
TABLE_DISPLAY_CONFIG = {
    # O/X 표시 설정
    "BOOLEAN_TRUE_TEXT": "O",
    "BOOLEAN_FALSE_TEXT": "✗",
    "EMPTY_TEXT": "✗",
    
    # 색상 설정 (테마 색상 키)
    "BOOLEAN_TRUE_COLOR": "success",  # 초록색
    "BOOLEAN_FALSE_COLOR": "error",   # 빨간색
    "EMPTY_COLOR": "error",           # 빨간색
    
    # 빈 값으로 처리할 조건들
    "EMPTY_VALUES": [None, "", "null", "NULL"],
    "FALSE_VALUES": [False, "false", "False", "FALSE", 0, "0"]
}

# 스와치픽업 관련 설정
SWATCH_PICKUP_CONFIG = {
    "TRUE_DISPLAY": TABLE_DISPLAY_CONFIG["BOOLEAN_TRUE_TEXT"],
    "FALSE_DISPLAY": TABLE_DISPLAY_CONFIG["BOOLEAN_FALSE_TEXT"],
    "NULL_DISPLAY": TABLE_DISPLAY_CONFIG["EMPTY_TEXT"],
    "TRUE_COLOR": TABLE_DISPLAY_CONFIG["BOOLEAN_TRUE_COLOR"],
    "FALSE_COLOR": TABLE_DISPLAY_CONFIG["BOOLEAN_FALSE_COLOR"],
    "NULL_COLOR": TABLE_DISPLAY_CONFIG["EMPTY_COLOR"]
} 