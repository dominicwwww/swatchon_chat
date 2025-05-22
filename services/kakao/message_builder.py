"""
메시지 빌더 모듈
"""

from typing import Dict, List, Any, Optional

from core.logger import get_logger
from core.constants import DEFAULT_HEADER, DEFAULT_FOOTER


class MessageBuilder:
    """메시지 빌더 클래스"""
    
    def __init__(self):
        """초기화"""
        self.logger = get_logger(__name__)
    
    def build_shipment_request_message(self, seller_name: str, items: List[Dict[str, Any]],
                                      header: Optional[str] = None, footer: Optional[str] = None) -> str:
        """
        출고 요청 메시지 생성
        
        Args:
            seller_name: 판매자명
            items: 출고 항목 목록
            header: 메시지 헤더 (None인 경우 기본값 사용)
            footer: 메시지 푸터 (None인 경우 기본값 사용)
            
        Returns:
            str: 출고 요청 메시지
        """
        header = header or DEFAULT_HEADER
        footer = footer or DEFAULT_FOOTER
        
        # 주문번호별 그룹화
        order_groups = {}
        for item in items:
            order_number = item.get('order_number', '')
            if order_number not in order_groups:
                order_groups[order_number] = []
            order_groups[order_number].append(item)
        
        # 메시지 본문 생성
        message = f"{header} {seller_name}님 안녕하세요.\n\n"
        message += "다음 주문의 출고를 요청드립니다.\n\n"
        
        # 주문번호별 메시지 추가
        for order_number, order_items in order_groups.items():
            message += f"# 주문번호: {order_number}\n"
            
            for item in order_items:
                product_name = item.get('product_name', '상품명 없음')
                quantity = item.get('quantity', 0)
                message += f"- {product_name} ({quantity}개)\n"
            
            message += "\n"
        
        # 푸터 추가
        message += footer
        
        return message
    
    def build_shipment_confirm_message(self, seller_name: str, items: List[Dict[str, Any]],
                                       header: Optional[str] = None, footer: Optional[str] = None) -> str:
        """
        출고 확인 메시지 생성
        
        Args:
            seller_name: 판매자명
            items: 출고 항목 목록
            header: 메시지 헤더 (None인 경우 기본값 사용)
            footer: 메시지 푸터 (None인 경우 기본값 사용)
            
        Returns:
            str: 출고 확인 메시지
        """
        header = header or DEFAULT_HEADER
        footer = footer or DEFAULT_FOOTER
        
        # 메시지 본문 생성
        message = f"{header} {seller_name}님\n\n"
        message += "출고 확인되었습니다.\n\n"
        
        # 항목별 메시지 추가
        for item in items:
            order_number = item.get('order_number', '번호 없음')
            tracking_number = item.get('tracking_number', '송장번호 없음')
            message += f"- 주문번호: {order_number}\n"
            message += f"- 송장번호: {tracking_number}\n\n"
        
        # 푸터 추가
        message += footer
        
        return message
    
    def build_po_message(self, seller_name: str, items: List[Dict[str, Any]],
                        header: Optional[str] = None, footer: Optional[str] = None) -> str:
        """
        발주 확인 요청 메시지 생성
        
        Args:
            seller_name: 판매자명
            items: 발주 항목 목록
            header: 메시지 헤더 (None인 경우 기본값 사용)
            footer: 메시지 푸터 (None인 경우 기본값 사용)
            
        Returns:
            str: 발주 확인 요청 메시지
        """
        header = header or DEFAULT_HEADER
        footer = footer or DEFAULT_FOOTER
        
        # 메시지 본문 생성
        message = f"{header} {seller_name}님\n\n"
        message += "발주 확인 요청드립니다.\n\n"
        
        # 항목별 메시지 추가
        for item in items:
            po_number = item.get('po_number', '번호 없음')
            product_name = item.get('product_name', '상품명 없음')
            quantity = item.get('quantity', 0)
            message += f"- 발주번호: {po_number}\n"
            message += f"- 상품명: {product_name}\n"
            message += f"- 수량: {quantity}개\n\n"
        
        # 푸터 추가
        message += footer
        
        return message
    
    def build_swatch_po_message(self, seller_name: str, items: List[Dict[str, Any]],
                              header: Optional[str] = None, footer: Optional[str] = None) -> str:
        """
        스와치 발주 메시지 생성
        
        Args:
            seller_name: 판매자명
            items: 스와치 항목 목록
            header: 메시지 헤더 (None인 경우 기본값 사용)
            footer: 메시지 푸터 (None인 경우 기본값 사용)
            
        Returns:
            str: 스와치 발주 메시지
        """
        header = header or DEFAULT_HEADER
        footer = footer or DEFAULT_FOOTER
        
        # 메시지 본문 생성
        message = f"{header} {seller_name}님\n\n"
        message += "스와치 발주합니다.\n\n"
        
        # 항목별 메시지 추가
        for item in items:
            order_number = item.get('order_number', '번호 없음')
            swatch_name = item.get('swatch_name', '스와치명 없음')
            quantity = item.get('quantity', 0)
            message += f"- 주문번호: {order_number}\n"
            message += f"- 스와치명: {swatch_name}\n"
            message += f"- 수량: {quantity}개\n\n"
        
        # 푸터 추가
        message += footer
        
        return message
    
    def build_pickup_request_message(self, seller_name: str, items: List[Dict[str, Any]],
                                   pickup_date: str, pickup_time: str,
                                   header: Optional[str] = None, footer: Optional[str] = None) -> str:
        """
        픽업 요청 메시지 생성
        
        Args:
            seller_name: 판매자명
            items: 스와치 항목 목록
            pickup_date: 픽업 날짜
            pickup_time: 픽업 시간
            header: 메시지 헤더 (None인 경우 기본값 사용)
            footer: 메시지 푸터 (None인 경우 기본값 사용)
            
        Returns:
            str: 픽업 요청 메시지
        """
        header = header or DEFAULT_HEADER
        footer = footer or DEFAULT_FOOTER
        
        # 메시지 본문 생성
        message = f"{header} {seller_name}님\n\n"
        message += "스와치 픽업 요청드립니다.\n\n"
        
        # 픽업 정보 추가
        message += f"## 픽업 정보\n"
        message += f"- 픽업 날짜: {pickup_date}\n"
        message += f"- 픽업 시간: {pickup_time}\n\n"
        
        # 항목별 메시지 추가
        message += f"## 픽업 스와치 목록\n"
        for item in items:
            order_number = item.get('order_number', '번호 없음')
            swatch_name = item.get('swatch_name', '스와치명 없음')
            quantity = item.get('quantity', 0)
            message += f"- {swatch_name} ({quantity}개) [주문번호: {order_number}]\n"
        
        message += "\n"
        
        # 푸터 추가
        message += footer
        
        return message 