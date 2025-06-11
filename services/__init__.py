"""
SwatchOn 카카오톡 자동화 프로젝트 - 서비스 패키지
"""

# 서비스 모듈 임포트
from services.spreadsheet_service import SpreadsheetService
from services.base_scraper import BaseScraper
from services.shipment_request_scraper import ShipmentRequestScraper

# 버전 정보
__version__ = "1.0.0"

# services 패키지 초기화 파일 (zip 배포용) 