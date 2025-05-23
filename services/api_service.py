"""
API 서비스 모듈 - API 호출 관련 기능
"""
import requests
from typing import Dict, Any, Optional
from datetime import datetime

from core.constants import API_BASE_URL, API_HEADERS, API_ENDPOINTS
from core.schemas import PurchaseProductList

class ApiService:
    """API 서비스 클래스"""
    
    @staticmethod
    def get_purchase_products() -> Optional[PurchaseProductList]:
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
    def get_shipment_requests() -> Optional[Dict[str, Any]]:
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
    def get_shipment_confirmations() -> Optional[Dict[str, Any]]:
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