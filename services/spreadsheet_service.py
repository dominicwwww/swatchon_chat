"""
스프레드시트 서비스 모듈 - Google Sheets API 연동
"""
import os
import json
from typing import List, Dict, Any, Optional, Union
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from core.config import ConfigManager
from core.constants import SpreadsheetConfigKey
from core.logger import get_logger

class SpreadsheetService:
    """Google Sheets API 연동 서비스 클래스"""
    
    # 필요한 API 스코프
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.config = ConfigManager()
        self.credentials = None
        self.service = None
        self._init_service()
    
    def _init_service(self):
        """Google Sheets API 서비스 초기화"""
        try:
            # 자격 증명 파일 경로 가져오기
            creds_path = self.config.get("google_credentials", "")
            if not creds_path:
                self.logger.error("Google API 자격 증명 파일 경로가 설정되지 않았습니다.")
                return
            
            # 절대 경로 변환
            if not os.path.isabs(creds_path):
                creds_path = os.path.join(os.getcwd(), creds_path)
            
            # 자격 증명 파일이 존재하는지 확인
            if not os.path.exists(creds_path):
                self.logger.error(f"Google API 자격 증명 파일을 찾을 수 없습니다: {creds_path}")
                return
            
            # 자격 증명 생성
            self.credentials = Credentials.from_service_account_file(
                creds_path, scopes=self.SCOPES
            )
            
            # API 서비스 생성
            self.service = build('sheets', 'v4', credentials=self.credentials)
            self.logger.info("Google Sheets API 서비스가 초기화되었습니다.")
            
        except Exception as e:
            self.logger.error(f"Google Sheets API 서비스 초기화 중 오류 발생: {str(e)}")
            self.service = None
    
    def get_spreadsheet_data(self, spreadsheet_key: str, sheet_name: str, 
                             range_name: Optional[str] = None) -> List[List[Any]]:
        """
        스프레드시트 데이터 가져오기
        
        Args:
            spreadsheet_key: 스프레드시트 ID 또는 URL
            sheet_name: 시트 이름
            range_name: 범위 (예: 'A1:G100'), None이면 전체 데이터
            
        Returns:
            List[List[Any]]: 스프레드시트 데이터 (2차원 배열)
        """
        if not self.service:
            self.logger.error("Google Sheets API 서비스가 초기화되지 않았습니다.")
            return []
        
        try:
            # URL에서 스프레드시트 ID 추출
            if '/' in spreadsheet_key:
                # URL에서 ID 추출 시도
                try:
                    spreadsheet_key = self._extract_spreadsheet_id(spreadsheet_key)
                except ValueError as e:
                    self.logger.error(f"스프레드시트 URL에서 ID를 추출할 수 없습니다: {str(e)}")
                    return []
            
            # 범위 설정
            if range_name:
                range_str = f"{sheet_name}!{range_name}"
            else:
                range_str = sheet_name
            
            # API 호출로 데이터 가져오기
            sheet = self.service.spreadsheets()
            result = sheet.values().get(
                spreadsheetId=spreadsheet_key,
                range=range_str
            ).execute()
            
            # 결과에서 값 추출
            values = result.get('values', [])
            
            if not values:
                self.logger.warning(f"스프레드시트에서 데이터를 찾을 수 없습니다: {spreadsheet_key}, 시트: {sheet_name}")
                return []
            
            return values
            
        except HttpError as error:
            self.logger.error(f"스프레드시트 데이터 가져오기 API 오류: {error}")
            return []
        except Exception as e:
            self.logger.error(f"스프레드시트 데이터 가져오기 중 오류 발생: {str(e)}")
            return []
    
    def _extract_spreadsheet_id(self, url: str) -> str:
        """
        URL에서 스프레드시트 ID 추출
        
        Args:
            url: 스프레드시트 URL
            
        Returns:
            str: 스프레드시트 ID
        """
        # URL 형식: https://docs.google.com/spreadsheets/d/{spreadsheetId}/edit
        if '/spreadsheets/d/' in url:
            # ID 추출
            start_idx = url.find('/spreadsheets/d/') + len('/spreadsheets/d/')
            end_idx = url.find('/', start_idx)
            if end_idx == -1:  # '/' 문자가 없는 경우
                end_idx = url.find('?', start_idx)  # '?' 문자로 끝나는지 확인
                
            if end_idx == -1:  # '?' 문자도 없는 경우
                return url[start_idx:]  # 나머지 전체 문자열 사용
            else:
                return url[start_idx:end_idx]
        else:
            raise ValueError(f"유효한 Google 스프레드시트 URL이 아닙니다: {url}")
    
    def get_fbo_shipment_request_data(self) -> List[Dict[str, Any]]:
        """
        FBO 출고 요청 데이터 가져오기
        
        Returns:
            List[Dict[str, Any]]: 출고 요청 데이터 목록
        """
        try:
            # 설정에서 스프레드시트 URL과 시트 이름 가져오기
            spreadsheet_url = self.config.get(SpreadsheetConfigKey.FBO_SHIPMENT_REQUEST_URL.value, "")
            sheet_name = self.config.get(SpreadsheetConfigKey.FBO_SHIPMENT_REQUEST_SHEET.value, "출고요청")
            
            if not spreadsheet_url:
                self.logger.error("FBO 출고 요청 스프레드시트 URL이 설정되지 않았습니다.")
                return []
            
            # 스프레드시트 데이터 가져오기
            data = self.get_spreadsheet_data(spreadsheet_url, sheet_name)
            
            if not data or len(data) < 2:  # 헤더 + 최소 1개 데이터 행
                self.logger.warning("FBO 출고 요청 데이터가 충분하지 않습니다.")
                return []
            
            # 헤더 추출
            headers = data[0]
            
            # 데이터 행을 딕셔너리 목록으로 변환
            result = []
            for row in data[1:]:  # 헤더 이후 행만 처리
                # 행의 길이가 헤더보다 짧으면 빈 값으로 채움
                if len(row) < len(headers):
                    row.extend([''] * (len(headers) - len(row)))
                
                # 딕셔너리 생성
                item = {}
                for i, header in enumerate(headers):
                    item[header] = row[i]
                
                # 필수 필드 변환 및 추가
                item.setdefault("선택", False)  # 선택 여부 초기값
                item.setdefault("상태", "대기중")  # 상태 초기값
                
                # 필수 필드 존재 여부 확인
                required_fields = ["판매자", "주문번호", "상품명", "수량", "주문일"]
                if all(field in item and item[field] for field in required_fields):
                    result.append(item)
                else:
                    missing = [field for field in required_fields if field not in item or not item[field]]
                    self.logger.warning(f"필수 필드가 누락된 행 무시: {missing}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"FBO 출고 요청 데이터 가져오기 중 오류 발생: {str(e)}")
            return [] 