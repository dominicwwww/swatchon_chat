"""
템플릿 서비스 모듈
"""

import os
import json
import sys
from datetime import datetime
from typing import Dict, Any, Optional, Union, List, Callable

from core.logger import get_logger
from core.exceptions import TemplateException
from core.types import OrderType, FboOperationType, SboOperationType
from core.constants import (
    DEFAULT_TEMPLATES_PATH, USER_DATA_DIR, DELIVERY_METHODS, 
    LOGISTICS_COMPANIES, DEFAULT_ORDER_DETAILS_FORMAT, API_FIELDS
)
from core.config import ConfigManager
from services.api_service import ApiService


class TemplateService:
    """템플릿 서비스 클래스"""
    
    def __init__(self):
        """초기화"""
        self.logger = get_logger(__name__)
        self.config_manager = ConfigManager()
        self.templates = self._load_templates()
        self.api_service = ApiService()
        
        # 템플릿 타입별 API 매핑
        self.api_mapping = {
            (OrderType.FBO.value, FboOperationType.SHIPMENT_REQUEST.value): self.api_service.get_purchase_products,
            (OrderType.FBO.value, FboOperationType.SHIPMENT_CONFIRM.value): self.api_service.get_shipment_confirmations,
            (OrderType.FBO.value, FboOperationType.PO.value): self.api_service.get_purchase_products,
            (OrderType.SBO.value, SboOperationType.PO.value): self.api_service.get_purchase_products,
            (OrderType.SBO.value, SboOperationType.PICKUP_REQUEST.value): self.api_service.get_pickup_requests
        }
    
    def _load_templates(self) -> Dict[str, Any]:
        """
        템플릿 로드
        
        Returns:
            Dict[str, Any]: 템플릿 데이터
        """
        try:
            # config.json에서 템플릿 데이터 로드
            templates = self.config_manager.get("default_templates", {})
            
            # 기본 템플릿이 없으면 빈 템플릿 생성
            if not templates:
                templates = self._create_empty_templates()
                # config.json에 기본 템플릿 저장
                self.config_manager.set("default_templates", templates)
                self.config_manager.save()
            
            return templates
            
        except Exception as e:
            self.logger.error(f"템플릿 로드 실패: {str(e)}")
            return self._create_empty_templates()
    
    def _save_templates(self) -> bool:
        """
        템플릿 저장
        
        Returns:
            bool: 성공 여부
        """
        try:
            # config.json에 템플릿 저장
            self.config_manager.set("default_templates", self.templates)
            return self.config_manager.save()
            
        except Exception as e:
            self.logger.error(f"템플릿 저장 실패: {str(e)}")
            return False
    
    def _create_empty_templates(self) -> Dict[str, Any]:
        """
        빈 템플릿 생성
        
        Returns:
            Dict[str, Any]: 빈 템플릿 데이터
        """
        return {
            "fbo": {
                "shipment_request": {
                    "title": "FBO 출고 요청",
                    "content": "[출고 요청-{store_name}]\n안녕하세요!\n오늘 출고 예정인 주문 알려드립니다.\n\n\n{order_details}\n\n출고 불가 시 반드시 출고일 변경 부탁드립니다.\n[주문]>[출고예정] 링크:\nhttps://partners.swatchon.com/purchases/products/need-sent?page=1",
                    "variables": ["store_name", "order_details"],
                    "conditions": [],
                    "order_details_format": "[{quality_name}] | #{color_number} | {quantity}yd | {pickup_at} | {delivery_method}-{logistics_company}",
                    "last_modified": datetime.now().isoformat()
                }
            },
            "sbo": {},
            "settings": {
                "version": "1.0",
                "last_modified": datetime.now().isoformat(),
                "created_by": "SwatchOn"
            }
        }
    
    def load_template(self, order_type: OrderType, operation_type: Union[FboOperationType, SboOperationType]) -> Optional[Dict[str, Any]]:
        """
        템플릿 로드
        
        Args:
            order_type: 주문 유형
            operation_type: 작업 유형
            
        Returns:
            Optional[Dict[str, Any]]: 템플릿 데이터 (없으면 None)
        """
        # 템플릿에서 해당 유형의 템플릿 찾기
        order_type_str = order_type.value
        operation_type_str = operation_type.value
        
        if order_type_str in self.templates and operation_type_str in self.templates[order_type_str]:
            return self.templates[order_type_str][operation_type_str]
        
        self.logger.error(f"템플릿을 찾을 수 없습니다: {order_type_str}/{operation_type_str}")
        return None
    
    def update_template(self, order_type: OrderType, operation_type: Union[FboOperationType, SboOperationType],
                      title: str, content: str, variables: Optional[List[str]] = None,
                      conditions: Optional[List[Dict[str, Any]]] = None,
                      order_details_format: Optional[str] = None) -> bool:
        """
        템플릿 업데이트
        
        Args:
            order_type: 주문 유형
            operation_type: 작업 유형
            title: 템플릿 제목
            content: 템플릿 내용
            variables: 변수 목록 (None인 경우 자동 추출)
            conditions: 조건부 템플릿 목록
            order_details_format: 주문 상세 정보 형식
            
        Returns:
            bool: 성공 여부
        """
        order_type_str = order_type.value
        operation_type_str = operation_type.value
        
        # 주문 유형이 없으면 생성
        if order_type_str not in self.templates:
            self.templates[order_type_str] = {}
        
        # 변수 추출 (제공되지 않은 경우)
        if variables is None:
            variables = self._extract_variables(content)
        
        # 템플릿 업데이트
        self.templates[order_type_str][operation_type_str] = {
            "title": title,
            "content": content,
            "variables": variables,
            "conditions": conditions or [],
            "order_details_format": order_details_format or DEFAULT_ORDER_DETAILS_FORMAT,
            "last_modified": datetime.now().isoformat()
        }
        
        # 템플릿 저장
        return self._save_templates()
    
    def _extract_variables(self, content: str) -> List[str]:
        """
        템플릿 내용에서 변수 추출
        
        Args:
            content: 템플릿 내용
            
        Returns:
            List[str]: 변수 목록
        """
        import re
        
        # {변수명} 패턴 추출
        pattern = r'\{([a-zA-Z0-9_]+)\}'
        matches = re.findall(pattern, content)
        
        # 중복 제거
        return list(set(matches))
    
    def render_message(self, order_type: OrderType, operation_type: Union[FboOperationType, SboOperationType], data: Dict[str, Any]) -> str:
        """메시지 렌더링"""
        try:
            # 템플릿 로드
            template = self.load_template(order_type, operation_type)
            if not template:
                return None
            content = template["content"]
            
            # 조건부 템플릿 적용
            if "conditions" in template:
                for condition in template["conditions"]:
                    field = condition["field"]
                    operator = condition["operator"]
                    value = condition["value"]
                    condition_content = condition.get("template", "")
                    if self._evaluate_condition(data, field, operator, value):
                        content = condition_content
                        break
            
            # 모든 변수를 문자열로 변환하여 치환
            for key, value in data.items():
                placeholder = f"{{{key}}}"
                if placeholder in content:
                    content = content.replace(placeholder, str(value))
            
            return content
            
        except Exception as e:
            self.logger.error(f"메시지 렌더링 중 오류: {str(e)}")
            return None
    
    def _format_order_details(self, data: Dict[str, Any]) -> List[str]:
        """
        주문 상세 정보 포맷팅
        
        Args:
            data: 주문 데이터
            
        Returns:
            List[str]: 포맷팅된 주문 상세 정보 목록
        """
        try:
            details = []
            
            # 판매자 정보
            if "store_name" in data:
                details.append(f"판매자: {data['store_name']}")
            
            # 주문 번호
            if "purchase_code" in data:
                details.append(f"주문번호: {data['purchase_code']}")
            
            # 상품 정보
            if "quality_name" in data:
                details.append(f"퀄리티: {data['quality_name']}")
            
            if "color_name" in data or "color_code" in data:
                color_name = data.get("color_name", "")
                color_code = data.get("color_code", "")
                if color_name and color_code:
                    details.append(f"컬러: {color_name} ({color_code})")
                elif color_name:
                    details.append(f"컬러: {color_name}")
                elif color_code:
                    details.append(f"컬러: {color_code}")
            
            if "quantity" in data:
                details.append(f"수량: {data['quantity']}yd")
            
            # 배송 정보
            if "delivery_method" in data:
                delivery_method = data["delivery_method"]
                if delivery_method == "quick":
                    details.append("배송방법: 동대문 픽업")
                elif delivery_method == "logistics":
                    details.append("배송방법: 판매자 발송")
            
            if "logistics_company" in data:
                company = data["logistics_company"]
                if company in LOGISTICS_COMPANIES:
                    details.append(f"택배사: {LOGISTICS_COMPANIES[company]}")
            
            # 출고일
            if "pickup_at" in data:
                pickup_date = data["pickup_at"].split("T")[0] if "T" in data["pickup_at"] else data["pickup_at"]
                details.append(f"출고일: {pickup_date}")
            
            return details
            
        except Exception as e:
            self.logger.error(f"주문 상세 정보 포맷팅 실패: {str(e)}")
            return ["주문 상세 정보를 가져올 수 없습니다."]
    
    def _evaluate_condition(self, data: Dict[str, Any], field: str, operator: str, value: Any) -> bool:
        """
        조건 평가
        
        Args:
            data: 변수 데이터
            field: 필드명
            operator: 연산자
            value: 비교값
            
        Returns:
            bool: 조건 만족 여부
        """
        try:
            if field not in data:
                return False
            field_value = data[field]
            # {today} 지원
            if isinstance(value, str) and value.strip() == "{today}":
                value = datetime.now().strftime('%Y-%m-%d')
            # pickup_at이 datetime 또는 ISO 문자열이면 YYYY-MM-DD로 변환
            if field == "pickup_at":
                if isinstance(field_value, datetime):
                    field_value = field_value.strftime('%Y-%m-%d')
                elif isinstance(field_value, str) and "T" in field_value:
                    field_value = field_value.split("T")[0]
            # 연산자에 따른 조건 확인
            if operator == "==":
                return field_value == value
            elif operator == "!=":
                return field_value != value
            elif operator == ">":
                return field_value > value
            elif operator == ">=":
                return field_value >= value
            elif operator == "<":
                return field_value < value
            elif operator == "<=":
                return field_value <= value
            elif operator == "in":
                return value in field_value
            elif operator == "not in":
                return value not in field_value
            elif operator == "contains":
                return str(value) in str(field_value)
            elif operator == "not contains":
                return str(value) not in str(field_value)
            return False
        except Exception as e:
            self.logger.error(f"조건 평가 중 오류: {str(e)}")
            return False
    
    def get_template_variables(self, order_type: OrderType, 
                               operation_type: Union[FboOperationType, SboOperationType]) -> List[str]:
        """
        템플릿 변수 목록 가져오기
        
        Args:
            order_type: 주문 유형
            operation_type: 작업 유형
            
        Returns:
            List[str]: 변수 목록
        """
        template = self.load_template(order_type, operation_type)
        if not template:
            return []
        
        return template.get("variables", [])
    
    def reset_to_default_template(self, order_type: OrderType, 
                                operation_type: Union[FboOperationType, SboOperationType]) -> bool:
        """
        기본 템플릿으로 초기화
        
        Args:
            order_type: 주문 유형
            operation_type: 작업 유형
            
        Returns:
            bool: 성공 여부
        """
        try:
            # 기본 템플릿 파일 로드
            default_templates = self._load_default_templates()
            if not default_templates:
                return False
            
            order_type_str = order_type.value
            operation_type_str = operation_type.value
            
            # 기본 템플릿에서 해당 유형 템플릿 찾기
            if order_type_str in default_templates and operation_type_str in default_templates[order_type_str]:
                default_template = default_templates[order_type_str][operation_type_str]
                
                # 현재 템플릿 업데이트
                if order_type_str not in self.templates:
                    self.templates[order_type_str] = {}
                
                self.templates[order_type_str][operation_type_str] = default_template
                
                # 템플릿 파일 저장
                return self._save_templates()
            
            return False
        
        except Exception as e:
            self.logger.error(f"기본 템플릿으로 초기화 실패: {str(e)}")
            return False
    
    def _load_default_templates(self) -> Dict[str, Any]:
        """
        기본 템플릿 파일 로드
        
        Returns:
            Dict[str, Any]: 기본 템플릿 데이터
        """
        try:
            # 기본 템플릿 파일 경로
            exe_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            default_templates_path = os.path.join(exe_dir, DEFAULT_TEMPLATES_PATH)
            
            # 기본 템플릿 파일 로드
            if os.path.exists(default_templates_path):
                with open(default_templates_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            
            return self._create_empty_templates()
        
        except Exception as e:
            self.logger.error(f"기본 템플릿 파일 로드 실패: {str(e)}")
            return self._create_empty_templates()
    
    def get_api_data(self, order_type: str, operation_type: str) -> Optional[Any]:
        """
        템플릿 타입에 맞는 API 데이터 가져오기
        
        Args:
            order_type: 주문 유형
            operation_type: 작업 유형
        
        Returns:
            Optional[Any]: API 데이터 (실패 시 None)
        """
        try:
            api_func = self.api_mapping.get((order_type, operation_type))
            if not api_func:
                self.logger.error(f"API 매핑을 찾을 수 없습니다: {order_type}/{operation_type}")
                return None
                
            return api_func()
            
        except Exception as e:
            self.logger.error(f"API 데이터 가져오기 실패: {str(e)}")
            return None

    def evaluate_condition(self, data: dict, condition: dict) -> bool:
        """
        조건부 템플릿의 조건을 평가합니다.
        Args:
            data: 메시지 데이터(dict)
            condition: {"field": ..., "operator": ..., "value": ...}
        Returns:
            bool: 조건 만족 여부
        """
        from datetime import datetime
        field = condition.get("field")
        operator = condition.get("operator")
        value = condition.get("value")

        # {today} 지원
        if isinstance(value, str) and value.strip() == "{today}":
            value = datetime.now().strftime('%Y-%m-%d')
        if field == "pickup_at":
            field_value = data.get(field, "")
            if isinstance(field_value, str) and "T" in field_value:
                field_value = field_value.split("T")[0]
        else:
            field_value = data.get(field, "")

        # 숫자 비교 연산자 처리
        def try_cast(val):
            try:
                return float(val)
            except (ValueError, TypeError):
                return val

        if operator in (">", "<", ">=", "<="):
            left = try_cast(field_value)
            right = try_cast(value)
            # 둘 다 숫자면 숫자 비교
            if isinstance(left, (int, float)) and isinstance(right, (int, float)):
                if operator == ">":
                    return left > right
                elif operator == "<":
                    return left < right
                elif operator == ">=":
                    return left >= right
                elif operator == "<=":
                    return left <= right
            else:
                # 둘 중 하나라도 숫자가 아니면 문자열 비교 fallback
                left = str(field_value)
                right = str(value)
                if operator == ">":
                    return left > right
                elif operator == "<":
                    return left < right
                elif operator == ">=":
                    return left >= right
                elif operator == "<=":
                    return left <= right
        # 나머지 연산자
        if operator == "==":
            return field_value == value
        elif operator == "!=":
            return field_value != value
        elif operator == "in":
            return value in field_value
        elif operator == "not in":
            return value not in field_value
        elif operator == "contains":
            return str(value) in str(field_value)
        elif operator == "not contains":
            return str(value) not in str(field_value)
        return False 