"""
템플릿 렌더러 모듈
"""

from typing import Dict, Any, List, Optional

from core.logger import get_logger
from core.types import MessageData, OrderType, FboOperationType, SboOperationType
from core.exceptions import TemplateException
from services.template.template_service import TemplateService


class TemplateRenderer:
    """템플릿 렌더러 클래스"""
    
    def __init__(self):
        """초기화"""
        self.logger = get_logger(__name__)
        self.template_service = TemplateService()
    
    def render_fbo_shipment_request(self, data: MessageData) -> Optional[str]:
        """
        FBO 출고 요청 메시지 렌더링
        
        Args:
            data: 메시지 데이터
            
        Returns:
            Optional[str]: 렌더링된 메시지 (실패 시 None)
        """
        try:
            return self.template_service.render_message(
                OrderType.FBO,
                FboOperationType.SHIPMENT_REQUEST,
                data
            )
        except Exception as e:
            self.logger.error(f"FBO 출고 요청 메시지 렌더링 실패: {str(e)}")
            return None
    
    def render_fbo_shipment_confirm(self, data: MessageData) -> Optional[str]:
        """
        FBO 출고 확인 메시지 렌더링
        
        Args:
            data: 메시지 데이터
            
        Returns:
            Optional[str]: 렌더링된 메시지 (실패 시 None)
        """
        try:
            return self.template_service.render_message(
                OrderType.FBO,
                FboOperationType.SHIPMENT_CONFIRM,
                data
            )
        except Exception as e:
            self.logger.error(f"FBO 출고 확인 메시지 렌더링 실패: {str(e)}")
            return None
    
    def render_fbo_po(self, data: MessageData) -> Optional[str]:
        """
        FBO 발주 확인 요청 메시지 렌더링
        
        Args:
            data: 메시지 데이터
            
        Returns:
            Optional[str]: 렌더링된 메시지 (실패 시 None)
        """
        try:
            return self.template_service.render_message(
                OrderType.FBO,
                FboOperationType.PO,
                data
            )
        except Exception as e:
            self.logger.error(f"FBO 발주 확인 요청 메시지 렌더링 실패: {str(e)}")
            return None
    
    def render_sbo_po(self, data: MessageData) -> Optional[str]:
        """
        SBO 스와치 발주 메시지 렌더링
        
        Args:
            data: 메시지 데이터
            
        Returns:
            Optional[str]: 렌더링된 메시지 (실패 시 None)
        """
        try:
            return self.template_service.render_message(
                OrderType.SBO,
                SboOperationType.PO,
                data
            )
        except Exception as e:
            self.logger.error(f"SBO 스와치 발주 메시지 렌더링 실패: {str(e)}")
            return None
    
    def render_sbo_pickup_request(self, data: MessageData) -> Optional[str]:
        """
        SBO 스와치 픽업 요청 메시지 렌더링
        
        Args:
            data: 메시지 데이터
            
        Returns:
            Optional[str]: 렌더링된 메시지 (실패 시 None)
        """
        try:
            return self.template_service.render_message(
                OrderType.SBO,
                SboOperationType.PICKUP_REQUEST,
                data
            )
        except Exception as e:
            self.logger.error(f"SBO 스와치 픽업 요청 메시지 렌더링 실패: {str(e)}")
            return None
    
    def get_required_variables(self, order_type: OrderType, 
                               operation_type: FboOperationType | SboOperationType) -> List[str]:
        """
        필수 변수 목록 반환
        
        Args:
            order_type: 주문 유형
            operation_type: 작업 유형
            
        Returns:
            List[str]: 필수 변수 목록
        """
        return self.template_service.get_template_variables(order_type, operation_type) 