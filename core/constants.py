"""
공통 상수 정의 모듈
"""
from enum import Enum, auto

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
    # FBO (Fabric Bulk Order) 관련
    FBO_SHIPMENT_REQUEST_URL = "fbo_shipment_request_spreadsheet_url"
    FBO_SHIPMENT_REQUEST_SHEET = "fbo_shipment_request_sheet_name"
    
    FBO_SHIPMENT_CONFIRM_URL = "fbo_shipment_confirm_spreadsheet_url"
    FBO_SHIPMENT_CONFIRM_SHEET = "fbo_shipment_confirm_sheet_name"
    
    FBO_PO_URL = "fbo_po_spreadsheet_url"
    FBO_PO_SHEET = "fbo_po_sheet_name"
    
    # 입고 관련
    FBO_RECEIVE_URL = "fbo_receive_spreadsheet_url"
    FBO_RECEIVE_SHEET = "fbo_receive_sheet_name"
    
    # SBO (Swatch Box Order) 관련
    SBO_PO_URL = "sbo_po_spreadsheet_url"
    SBO_PO_SHEET = "sbo_po_sheet_name"
    
    SBO_PICKUP_REQUEST_URL = "sbo_pickup_request_spreadsheet_url"
    SBO_PICKUP_REQUEST_SHEET = "sbo_pickup_request_sheet_name"

# 로그 레벨
class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"

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
        "url_key": SpreadsheetConfigKey.FBO_PO_URL.value,
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
API_KEY = "CkhbWmgJV51nxuTsiKiHmel8QUuoHnxUtjSQ812FxEexVfen"

# API 엔드포인트
API_ENDPOINTS = {
    "purchase_products": "/purchase_products",
    "shipment_requests": "/shipment_requests",
    "shipment_confirmations": "/shipment_confirmations"
}

# API 헤더
API_HEADERS = {
    "X-Api-Key": API_KEY,
    "Content-Type": "application/json"
} 