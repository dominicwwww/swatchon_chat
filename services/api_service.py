"""
API 서비스 모듈 - API 호출 관련 기능
"""
import requests
from typing import Dict, Any, Optional, List
from datetime import datetime
from core.logger import get_logger
from core.constants import API_BASE_URL, API_HEADERS, API_ENDPOINTS
from core.schemas import PurchaseProductList

class ApiService:
    """API 서비스 클래스"""
    
    def __init__(self):
        """초기화"""
        self.logger = get_logger(__name__)
    
    def _make_request(self, endpoint: str, method: str = "GET", params: Optional[Dict[str, Any]] = None) -> Optional[Any]:
        """
        API 요청 수행
        
        Args:
            endpoint: API 엔드포인트
            method: HTTP 메서드
            params: 요청 파라미터
            
        Returns:
            Optional[Any]: API 응답 데이터 (실패 시 None)
        """
        try:
            url = f"{API_BASE_URL}{endpoint}"
            response = requests.request(method, url, headers=API_HEADERS, params=params)
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            self.logger.error(f"API 요청 실패: {str(e)}")
            return None
    
    def get_purchase_products(self) -> Optional[List[Dict[str, Any]]]:
        """
        구매 상품 목록 가져오기 (모든 페이지)
        
        Returns:
            Optional[List[Dict[str, Any]]]: 구매 상품 목록 (실패 시 None)
        """
        try:
            all_items = []
            page = 1
            
            while True:
                self.logger.info(f"API 페이지 {page} 요청 중...")
                
                # 페이지 파라미터와 함께 요청
                params = {"page": page}
                data = self._make_request(API_ENDPOINTS["purchase_products"], params=params)
                
                if not data:
                    self.logger.warning(f"페이지 {page}에서 데이터를 받지 못했습니다.")
                    break
                
                # 응답이 리스트인지 딕셔너리인지 확인
                if isinstance(data, list):
                    items = data
                elif isinstance(data, dict) and 'items' in data:
                    items = data['items']
                else:
                    items = data if data else []
                
                if not items:
                    self.logger.info(f"페이지 {page}에 더 이상 데이터가 없습니다.")
                    break
                
                all_items.extend(items)
                self.logger.info(f"페이지 {page}: {len(items)}개 항목 추가 (총 {len(all_items)}개)")
                
                # 25개 미만이면 마지막 페이지
                if len(items) < 25:
                    self.logger.info(f"마지막 페이지 {page} 처리 완료")
                    break
                
                page += 1
            
            self.logger.info(f"전체 {len(all_items)}개 항목 로드 완료")
            return all_items
            
        except Exception as e:
            self.logger.error(f"구매 상품 목록 가져오기 실패: {str(e)}")
            return None
    
    def get_shipment_requests(self) -> Optional[Dict[str, Any]]:
        """
        출고 요청 목록 가져오기
        
        Returns:
            Optional[Dict[str, Any]]: 출고 요청 목록 (실패 시 None)
        """
        return self._make_request(API_ENDPOINTS["shipment_requests"])
    
    def get_shipment_confirmations(self) -> Optional[Dict[str, Any]]:
        """
        출고 확인 목록 가져오기
        
        Returns:
            Optional[Dict[str, Any]]: 출고 확인 목록 (실패 시 None)
        """
        return self._make_request(API_ENDPOINTS["shipment_confirmations"])
    
    def get_pickup_requests(self) -> Optional[Dict[str, Any]]:
        """
        픽업 요청 목록 가져오기
        
        Returns:
            Optional[Dict[str, Any]]: 픽업 요청 목록 (실패 시 None)
        """
        return self._make_request(API_ENDPOINTS["pickup_requests"])
    
    def get_purchase_confirms(self) -> Optional[List[Dict[str, Any]]]:
        """
        FBO 발주 확인 목록 가져오기 (모든 페이지)
        
        Returns:
            Optional[List[Dict[str, Any]]]: 발주 확인 목록 (실패 시 None)
        """
        try:
            all_items = []
            page = 1
            
            while True:
                self.logger.info(f"발주 확인 API 페이지 {page} 요청 중...")
                
                # 페이지 파라미터와 함께 요청
                params = {"page": page}
                data = self._make_request(API_ENDPOINTS["purchase_confirms"], params=params)
                
                if not data:
                    self.logger.warning(f"페이지 {page}에서 데이터를 받지 못했습니다.")
                    break
                
                # 응답이 리스트인지 딕셔너리인지 확인
                if isinstance(data, list):
                    items = data
                elif isinstance(data, dict) and 'items' in data:
                    items = data['items']
                else:
                    items = data if data else []
                
                if not items:
                    self.logger.info(f"페이지 {page}에 더 이상 데이터가 없습니다.")
                    break
                
                all_items.extend(items)
                self.logger.info(f"페이지 {page}: {len(items)}개 항목 추가 (총 {len(all_items)}개)")
                
                # 25개 미만이면 마지막 페이지
                if len(items) < 25:
                    self.logger.info(f"마지막 페이지 {page} 처리 완료")
                    break
                
                page += 1
            
            self.logger.info(f"전체 {len(all_items)}개 발주 확인 항목 로드 완료")
            return all_items
            
        except Exception as e:
            self.logger.error(f"발주 확인 목록 가져오기 실패: {str(e)}")
            return None
    
    @staticmethod
    def get_purchase_products_old() -> Optional[PurchaseProductList]:
        """구매 상품 전체 목록 조회 (모든 페이지 반복)"""
        try:
            all_items = []
            page = 1
            while True:
                url = f"{API_BASE_URL}{API_ENDPOINTS['purchase_products']}?page={page}"
                response = requests.get(url, headers=API_HEADERS)
                response.raise_for_status()
                data = response.json()
                if not data:
                    break
                all_items.extend(data)
                if len(data) < 25:  # 마지막 페이지(25개 미만)면 종료
                    break
                page += 1
            return PurchaseProductList(
                items=all_items,
                total=len(all_items)
            )
        except Exception as e:
            print(f"API 호출 중 오류 발생: {str(e)}")
            return None
    
    @staticmethod
    def get_shipment_requests_old() -> Optional[Dict[str, Any]]:
        """출고 요청 목록 조회"""
        try:
            response = requests.get(
                f"{API_BASE_URL}{API_ENDPOINTS['shipment_requests']}",
                headers=API_HEADERS
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"API 호출 중 오류 발생: {str(e)}")
            return None
    
    @staticmethod
    def get_shipment_confirmations_old() -> Optional[Dict[str, Any]]:
        """출고 확인 목록 조회"""
        try:
            response = requests.get(
                f"{API_BASE_URL}{API_ENDPOINTS['shipment_confirmations']}",
                headers=API_HEADERS
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"API 호출 중 오류 발생: {str(e)}")
            return None 