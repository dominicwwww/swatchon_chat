"""
메시지 빌더 모듈
"""

from typing import Dict, List, Any, Optional
from datetime import datetime

from core.logger import get_logger
from core.constants import DEFAULT_HEADER, DEFAULT_FOOTER
from services.template.template_service import TemplateService


class MessageBuilder:
    """메시지 빌더 클래스"""
    
    def __init__(self):
        """초기화"""
        self.logger = get_logger(__name__)
        self.template_service = TemplateService()
    
    def build_message(self, seller_name: str, items: List[Dict[str, Any]], 
                     order_type: str, operation_type: str,
                     header: Optional[str] = None, footer: Optional[str] = None) -> str:
        """
        조건부 템플릿을 지원하는 메시지 생성
        
        Args:
            seller_name: 판매자명
            items: 항목 목록
            order_type: 주문 유형
            operation_type: 작업 유형
            header: 메시지 헤더
            footer: 메시지 푸터
            
        Returns:
            str: 생성된 메시지
        """
        try:
            # 메시지 데이터 준비
            message_data = {
                "store_name": seller_name,
                "items": items,
                "pickup_at": items[0].get("pickup_at", "") if items else "",
                "total_orders": len(set(item.get("purchase_code", "") for item in items)),
                "total_products": len(items)
            }
            
            # 기본 API 필드 추가
            if items:
                for field_name in ["quality_name", "color_number", "color_code", "quantity", 
                                 "purchase_code", "delivery_method", "logistics_company"]:
                    if field_name not in message_data:
                        message_data[field_name] = items[0].get(field_name, "")
            
            # 조건부 템플릿 적용
            template = self.template_service.load_template(order_type, operation_type)
            if template and template.get("conditions"):
                for condition in template.get("conditions", []):
                    if self.template_service.evaluate_condition(message_data, condition):
                        message = condition.get("template", "")
                        if message:
                            import re
                            pattern = r'\{([a-zA-Z0-9_]+)\}'
                            matches = re.findall(pattern, message)
                            for var in matches:
                                try:
                                    value = message_data.get(var, "")
                                    message = message.replace(f"{{{var}}}", str(value) if value is not None else "")
                                except Exception as e:
                                    message = message.replace(f"{{{var}}}", "")
                            return message
            
            # 조건부 템플릿이 없거나 조건이 만족되지 않으면 기본 메시지 생성
            if operation_type == "shipment_request":
                return self.build_shipment_request_message(seller_name, items, header, footer)
            elif operation_type == "shipment_confirm":
                return self.build_shipment_confirm_message(seller_name, items, header, footer)
            elif operation_type == "po":
                return self.build_po_message(seller_name, items, header, footer)
            elif operation_type == "swatch_po":
                return self.build_swatch_po_message(seller_name, items, header, footer)
            elif operation_type == "pickup_request":
                pickup_date = items[0].get("pickup_at", "").split("T")[0] if items else datetime.now().strftime("%Y-%m-%d")
                pickup_time = "09:00"  # 기본값
                return self.build_pickup_request_message(seller_name, items, pickup_date, pickup_time, header, footer)
            
            return "지원하지 않는 작업 유형입니다."
            
        except Exception as e:
            self.logger.error(f"메시지 생성 중 오류: {str(e)}")
            return f"메시지 생성 중 오류가 발생했습니다: {str(e)}"
    
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