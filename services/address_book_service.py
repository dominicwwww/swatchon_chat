"""
주소록 서비스 모듈 - 판매자명과 채팅방명 매핑
"""

from typing import Dict, Optional
from core.logger import get_logger
from core.config import ConfigManager
from core.constants import SpreadsheetConfigKey
from services.spreadsheet_service import SpreadsheetService


class AddressBookService:
    """주소록 서비스 - 판매자명을 채팅방명으로 변환"""
    
    def __init__(self):
        """초기화"""
        self.logger = get_logger(__name__)
        self.config = ConfigManager()
        self.spreadsheet_service = SpreadsheetService()
        self.address_book = {}  # {store_name: chat_room_name}
        self._load_address_book()
    
    def _load_address_book(self):
        """주소록 데이터 로드"""
        try:
            # 설정에서 스프레드시트 URL과 시트 이름 가져오기
            spreadsheet_url = self.config.get(SpreadsheetConfigKey.ADDRESS_BOOK_URL.value, "")
            sheet_name = self.config.get(SpreadsheetConfigKey.ADDRESS_BOOK_SHEET.value, "주소록")
            
            if not spreadsheet_url:
                self.logger.error("주소록 스프레드시트 URL이 설정되지 않았습니다.")
                return
            
            # 스프레드시트 데이터 가져오기
            data = self.spreadsheet_service.get_spreadsheet_data(
                spreadsheet_url, 
                sheet_name,
                "B:C"  # B열(판매자)과 C열(채팅방)만 가져오기
            )
            
            if not data or len(data) < 2:  # 헤더 + 최소 1개 데이터 행
                self.logger.warning("주소록 데이터가 충분하지 않습니다.")
                return
            
            # 헤더 확인
            headers = data[0]
            if len(headers) < 2 or headers[0] != "판매자" or headers[1] != "채팅방":
                self.logger.error("주소록 형식이 올바르지 않습니다. (필요: 판매자, 채팅방)")
                return
            
            # 데이터 매핑
            self.address_book = {}
            for row in data[1:]:  # 헤더 이후 행만 처리
                if len(row) >= 2 and row[0] and row[1]:  # 판매자와 채팅방이 모두 있는 경우만
                    self.address_book[row[0].strip()] = row[1].strip()
            
            self.logger.info(f"주소록 {len(self.address_book)}개 항목 로드 완료")
            
        except Exception as e:
            self.logger.error(f"주소록 데이터 로드 중 오류 발생: {str(e)}")
    
    def get_chat_room_name(self, store_name: str) -> Optional[str]:
        """
        판매자명으로 채팅방명 조회
        
        Args:
            store_name: 판매자명
            
        Returns:
            Optional[str]: 채팅방명 (없으면 None)
        """
        return self.address_book.get(store_name)
    
    def get_all_mappings(self) -> Dict[str, str]:
        """
        모든 매핑 정보 조회
        
        Returns:
            Dict[str, str]: {판매자명: 채팅방명} 매핑
        """
        return self.address_book.copy()
    
    def reload_address_book(self):
        """주소록 다시 로드"""
        self.logger.info("주소록을 다시 로드합니다.")
        self._load_address_book()
    
    def has_mapping(self, store_name: str) -> bool:
        """
        해당 판매자명에 대한 매핑이 있는지 확인
        
        Args:
            store_name: 판매자명
            
        Returns:
            bool: 매핑 존재 여부
        """
        return store_name.strip() in self.address_book 