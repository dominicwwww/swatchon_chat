"""
주소록 서비스 모듈 - 판매자명과 채팅방명 매핑
"""

from typing import Dict, Optional
from core.logger import get_logger
from core.config import ConfigManager
from services.spreadsheet_service import SpreadsheetService


class AddressBookService:
    """주소록 서비스 - 판매자명을 채팅방명으로 변환"""
    
    def __init__(self):
        """초기화"""
        self.logger = get_logger(__name__)
        self.config = ConfigManager()
        self.spreadsheet_service = SpreadsheetService()
        self._address_cache = {}  # 캐시
        self._load_address_book()
    
    def _load_address_book(self):
        """주소록 데이터 로드"""
        try:
            # 설정에서 주소록 스프레드시트 정보 가져오기
            spreadsheet_url = self.config.get("address_book_spreadsheet_url", "")
            sheet_name = self.config.get("address_book_sheet_name", "주소록")
            
            if not spreadsheet_url:
                self.logger.warning("주소록 스프레드시트 URL이 설정되지 않았습니다.")
                return
            
            # 스프레드시트 데이터 가져오기
            data = self.spreadsheet_service.get_spreadsheet_data(spreadsheet_url, sheet_name)
            
            if not data or len(data) < 2:  # 헤더 + 최소 1개 데이터 행
                self.logger.warning("주소록 데이터가 충분하지 않습니다.")
                return
            
            # 데이터 파싱 (B컬럼: 판매자, C컬럼: 채팅방)
            self._address_cache = {}
            for row in data[1:]:  # 헤더 제외
                if len(row) >= 3:  # A, B, C 컬럼이 있는지 확인
                    store_name = row[1].strip() if len(row) > 1 else ""  # B컬럼 (판매자)
                    chat_room = row[2].strip() if len(row) > 2 else ""   # C컬럼 (채팅방)
                    
                    if store_name and chat_room:
                        self._address_cache[store_name] = chat_room
            
            self.logger.info(f"주소록 로드 완료: {len(self._address_cache)}개 항목")
            
        except Exception as e:
            self.logger.error(f"주소록 로드 실패: {str(e)}")
            self._address_cache = {}
    
    def get_chat_room_name(self, store_name: str) -> str:
        """
        판매자명으로 채팅방명 조회
        
        Args:
            store_name: 판매자명
            
        Returns:
            str: 채팅방명 (찾지 못하면 원본 판매자명 반환)
        """
        if not store_name:
            return store_name
        
        # 캐시에서 찾기
        chat_room = self._address_cache.get(store_name.strip())
        
        if chat_room:
            self.logger.debug(f"주소록에서 찾음: {store_name} -> {chat_room}")
            return chat_room
        else:
            self.logger.warning(f"주소록에서 찾을 수 없음: {store_name}")
            return store_name  # 찾지 못하면 원본 반환
    
    def reload_address_book(self):
        """주소록 다시 로드"""
        self.logger.info("주소록을 다시 로드합니다.")
        self._load_address_book()
    
    def get_all_mappings(self) -> Dict[str, str]:
        """
        모든 매핑 정보 반환
        
        Returns:
            Dict[str, str]: 판매자명 -> 채팅방명 매핑
        """
        return self._address_cache.copy()
    
    def has_mapping(self, store_name: str) -> bool:
        """
        해당 판매자명에 대한 매핑이 있는지 확인
        
        Args:
            store_name: 판매자명
            
        Returns:
            bool: 매핑 존재 여부
        """
        return store_name.strip() in self._address_cache 