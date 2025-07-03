"""
템플릿 서비스 모듈
"""

import os
import json
import sys
from datetime import datetime, timedelta
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
    
    def _parse_date_value(self, value):
        """날짜 값 파싱 ({today}, {today-1}, {today+1} 등)"""
        if not isinstance(value, str):
            return value
            
        value = value.strip()
        if not value.startswith("{") or not value.endswith("}"):
            return value
            
        # {today}, {today-N}, {today+N} 형식 파싱
        inner_value = value[1:-1]  # 중괄호 제거
        
        if inner_value == "today":
            return datetime.now().strftime('%Y-%m-%d')
        elif inner_value.startswith("today"):
            try:
                # today-1, today+2 등의 형식 처리
                if "+" in inner_value:
                    days_offset = int(inner_value.split("+")[1])
                    target_date = datetime.now() + timedelta(days=days_offset)
                elif "-" in inner_value:
                    days_offset = int(inner_value.split("-")[1])
                    target_date = datetime.now() - timedelta(days=days_offset)
                else:
                    return value  # 파싱 실패 시 원본 반환
                
                return target_date.strftime('%Y-%m-%d')
            except (ValueError, IndexError):
                return value
        
        return value
    
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
            
            # null 체크 연산자 처리
            if operator == "is_null":
                return field_value is None or field_value == "" or field_value == "null"
            elif operator == "is_not_null":
                return field_value is not None and field_value != "" and field_value != "null"
            
            # 날짜 값 파싱
            value = self._parse_date_value(value)
            
            # pickup_at이 datetime 또는 ISO 문자열이면 YYYY-MM-DD로 변환
            if field == "pickup_at":
                if isinstance(field_value, datetime):
                    field_value = field_value.strftime('%Y-%m-%d')
                elif isinstance(field_value, str) and "T" in field_value:
                    field_value = field_value.split("T")[0]
            
            # boolean 값 처리
            if isinstance(field_value, bool) or isinstance(value, bool):
                # 둘 중 하나가 boolean이면 둘 다 boolean으로 변환
                if isinstance(field_value, str):
                    fv = field_value.lower() == "true"
                else:
                    fv = bool(field_value)
                    
                if isinstance(value, str):
                    vv = value.lower() == "true"
                else:
                    vv = bool(value)
            else:
                # 숫자 비교 연산자일 때 int/float 변환 시도
                if operator in [">", ">=", "<", "<=", "==", "!="]:
                    try:
                        # 둘 다 숫자라면 변환
                        fv = float(field_value)
                        vv = float(value)
                    except (ValueError, TypeError):
                        fv = field_value
                        vv = value
                else:
                    fv = field_value
                    vv = value
            
            # 연산자에 따른 조건 확인
            if operator == "==":
                return fv == vv
            elif operator == "!=":
                return fv != vv
            elif operator == ">":
                return fv > vv
            elif operator == ">=":
                return fv >= vv
            elif operator == "<":
                return fv < vv
            elif operator == "<=":
                return fv <= vv
            elif operator == "in":
                return value in field_value
            elif operator == "not in":
                return value not in field_value
            elif operator == "contains" or operator == "not_contains":
                contains_result = str(value) in str(field_value)
                return contains_result if operator == "contains" else not contains_result
            return False
        except Exception as e:
            self.logger.error(f"조건 평가 중 오류: {str(e)}")
            return False

    def _evaluate_multi_field_condition(self, data: Dict[str, Any], fields: List[str], operators: Dict[str, str], values: Dict[str, Any]) -> bool:
        """
        다중 필드 조건 평가 (새로운 형식)
        
        Args:
            data: 변수 데이터
            fields: 필드명 리스트
            operators: 필드별 연산자 딕셔너리
            values: 필드별 값 딕셔너리
            
        Returns:
            bool: 조건 만족 여부
        """
        try:
            # 모든 필드가 데이터에 있는지 확인 (null 체크 제외)
            for field in fields:
                if field not in data:
                    operator = operators.get(field, "==")
                    if operator not in ["is_null", "is_not_null"]:
                        return False

            # 각 필드별로 조건 평가
            results = []
            for field in fields:
                operator = operators.get(field, "==")
                value = values.get(field, "")
                
                # 개별 조건 평가
                result = self._evaluate_condition(data, field, operator, value)
                results.append(result)
            
            # 모든 조건이 만족되어야 함 (AND 연산)
            return all(results)
                
        except Exception as e:
            self.logger.error(f"다중 필드 조건 평가 중 오류: {str(e)}")
            return False

    def render_message(self, order_type: OrderType, operation_type: Union[FboOperationType, SboOperationType], data: Dict[str, Any]) -> str:
        """
        메시지 렌더링 (템플릿 변수 치환 시 예외 방어)
        """
        try:
            # 주문 아이템들을 미리 파싱해서 저장 (조건부 템플릿에서 사용)
            self._current_order_items = []
            
            # 우선 items 필드 확인 (메시지 매니저에서 전달)
            if "items" in data and isinstance(data["items"], list):
                self._current_order_items = data["items"]
            else:
                # 기존 방식: order_details를 JSON으로 파싱 시도
                order_details_str = data.get("order_details", "")
                if order_details_str:
                    try:
                        # JSON 형태로 파싱 시도
                        if order_details_str.startswith('['):
                            self._current_order_items = json.loads(order_details_str)
                        else:
                            # JSON이 아닌 경우 빈 리스트로 설정
                            self._current_order_items = []
                    except json.JSONDecodeError:
                        self._current_order_items = []
            
            template = self.load_template(order_type, operation_type)
            if not template:
                return None
            content = template["content"]
            
            # 조건부 템플릿 적용
            if "conditions" in template:
                additional_contents = []  # 추가할 내용들을 모으기 위한 리스트
                
                for condition in template["conditions"]:
                    action_type = condition.get("action_type", "템플릿 내용 변경")
                    
                    # 조건 평가
                    condition_met = False
                    matching_items = []  # 조건을 만족하는 아이템들
                    
                    # 전체 주문 데이터에서 조건을 만족하는 아이템들 찾기
                    order_details_str = data.get("order_details", "")
                    if order_details_str and hasattr(self, '_current_order_items'):
                        # 현재 주문 아이템들에서 조건 체크
                        for item in self._current_order_items:
                            item_condition_met = False
                            
                            if "operators" in condition:
                                # 새로운 형식 (필드별 연산자)
                                fields = condition.get("fields", [])
                                operators = condition.get("operators", {})
                                values = condition.get("value", {})
                                item_condition_met = self._evaluate_multi_field_condition(item, fields, operators, values)
                            elif "fields" in condition:
                                # 기존 다중 필드 형식
                                fields = condition["fields"]
                                operator = condition.get("operator", "==")
                                value = condition.get("value", {})
                                item_condition_met = self._evaluate_multi_field_condition_old(item, fields, operator, value)
                            elif "field" in condition:
                                # 기존 단일 필드 형식
                                field = condition["field"]
                                operator = condition.get("operator", "==")
                                value = condition.get("value", "")
                                item_condition_met = self._evaluate_condition(item, field, operator, value)
                            
                            if item_condition_met:
                                matching_items.append(item)
                    
                    # 전체 조건 만족 여부 (기존 로직)
                    if "operators" in condition:
                        # 새로운 형식 (필드별 연산자)
                        fields = condition.get("fields", [])
                        operators = condition.get("operators", {})
                        values = condition.get("value", {})
                        condition_met = self._evaluate_multi_field_condition(data, fields, operators, values)
                    elif "fields" in condition:
                        # 기존 다중 필드 형식
                        fields = condition["fields"]
                        operator = condition.get("operator", "==")
                        value = condition.get("value", {})
                        condition_met = self._evaluate_multi_field_condition_old(data, fields, operator, value)
                    elif "field" in condition:
                        # 기존 단일 필드 형식
                        field = condition["field"]
                        operator = condition.get("operator", "==")
                        value = condition.get("value", "")
                        condition_met = self._evaluate_condition(data, field, operator, value)
                    
                    # 조건을 만족하는 아이템이 있거나 전체 조건이 만족되면
                    if matching_items or condition_met:
                        if action_type == "내용 변경":
                            # 내용 변경: 기존 템플릿을 완전히 새로운 내용으로 교체
                            new_content = condition.get("template", "")
                            if new_content:
                                content = new_content  # 기존 템플릿을 완전히 교체
                                # 내용 변경은 즉시 적용하고 추가 조건은 처리하지 않음
                                break
                        elif action_type == "템플릿 타입 변경":
                            # 기존 "템플릿 타입 변경" 호환성 유지 (완전히 다른 템플릿으로 전환)
                            target_operation = condition.get("target_operation", "shipment_request")
                            return {
                                "action": "change_template_type",
                                "target_operation": target_operation,
                                "data": data
                            }
                        elif action_type == "내용 추가" or action_type == "템플릿 내용 변경":
                            # 내용 추가 (기존 호환성을 위해 "템플릿 내용 변경"도 처리)
                            additional_content = condition.get("template", "")
                            if additional_content:
                                # 특별 변수 생성
                                special_vars = {}
                                
                                # swatch_no_stock 변수 생성
                                if matching_items:
                                    quality_names = []
                                    for item in matching_items:
                                        quality_name = item.get("quality_name", "")
                                        if quality_name and quality_name not in quality_names:
                                            quality_names.append(quality_name)
                                    
                                    if quality_names:
                                        special_vars["swatch_no_stock"] = "\n".join([f"{i+1}) {name}" for i, name in enumerate(quality_names)])
                                    else:
                                        special_vars["swatch_no_stock"] = ""
                                
                                # 특별 변수 치환
                                for var_name, var_value in special_vars.items():
                                    additional_content = additional_content.replace(f"{{{var_name}}}", str(var_value))
                                
                                # 추가할 내용들을 리스트에 모음 (즉시 적용하지 않음)
                                additional_contents.append(additional_content)
                
                # 모든 추가 내용을 기본 템플릿 뒤에 한번에 추가
                if additional_contents:
                    content = content + "\n\n" + "\n\n".join(additional_contents)
            
            # 변수 치환 (예외 방어)
            import re
            pattern = r'\{([a-zA-Z0-9_]+)\}'
            matches = re.findall(pattern, content)
            for var in matches:
                try:
                    value = data.get(var, "")
                    content = content.replace(f"{{{var}}}", str(value) if value is not None else "")
                except Exception as e:
                    self.logger.warning(f"템플릿 변수 치환 중 오류: {{{var}}} → '' (에러: {str(e)})")
                    content = content.replace(f"{{{var}}}", "")
            return content
        except Exception as e:
            self.logger.error(f"메시지 렌더링 중 오류: {str(e)}")
            return None

    def _evaluate_multi_field_condition_old(self, data: Dict[str, Any], fields: List[str], operator: str, value: Any) -> bool:
        """
        다중 필드 조건 평가 (기존 형식 호환)
        """
        try:
            # 모든 필드가 데이터에 있는지 확인
            if not all(field in data for field in fields):
                return False

            # 각 필드의 값을 가져와서 리스트로 만듦
            field_values = []
            for field in fields:
                field_value = data[field]
                # pickup_at이 datetime 또는 ISO 문자열이면 YYYY-MM-DD로 변환
                if field == "pickup_at":
                    if isinstance(field_value, datetime):
                        field_value = field_value.strftime('%Y-%m-%d')
                    elif isinstance(field_value, str) and "T" in field_value:
                        field_value = field_value.split("T")[0]
                field_values.append((field, field_value))

            # 날짜 값 파싱
            value = self._parse_date_value(value)

            # value가 딕셔너리인 경우 (필드별 다른 값)
            if isinstance(value, dict):
                results = []
                for field, field_value in field_values:
                    if field not in value:
                        continue
                    target_value = self._parse_date_value(value[field])
                    
                    # 숫자 비교 연산자일 때 int/float 변환 시도
                    if operator in [">", ">=", "<", "<=", "==", "!="]:
                        try:
                            fv = float(field_value)
                            tv = float(target_value)
                        except (ValueError, TypeError):
                            fv = field_value
                            tv = target_value
                    else:
                        fv = field_value
                        tv = target_value

                    # 연산자에 따른 조건 확인
                    if operator == "==":
                        results.append(fv == tv)
                    elif operator == "!=":
                        results.append(fv != tv)
                    elif operator == ">":
                        results.append(fv > tv)
                    elif operator == ">=":
                        results.append(fv >= tv)
                    elif operator == "<":
                        results.append(fv < tv)
                    elif operator == "<=":
                        results.append(fv <= tv)
                    elif operator == "in":
                        results.append(tv in fv)
                    elif operator == "not in":
                        results.append(tv not in fv)
                    elif operator == "contains":
                        results.append(str(tv) in str(fv))
                    elif operator == "not contains":
                        results.append(str(tv) not in str(fv))
                
                return all(results)
            
            # 단일 값과 비교하는 경우 (기존 로직)
            else:
                # 숫자 비교 연산자일 때 int/float 변환 시도
                if operator in [">", ">=", "<", "<=", "==", "!="]:
                    try:
                        field_values_nums = [float(v) for _, v in field_values]
                        vv = float(value)
                        # 연산자에 따른 조건 확인
                        if operator == "==":
                            return all(fv == vv for fv in field_values_nums)
                        elif operator == "!=":
                            return all(fv != vv for fv in field_values_nums)
                        elif operator == ">":
                            return all(fv > vv for fv in field_values_nums)
                        elif operator == ">=":
                            return all(fv >= vv for fv in field_values_nums)
                        elif operator == "<":
                            return all(fv < vv for fv in field_values_nums)
                        elif operator == "<=":
                            return all(fv <= vv for fv in field_values_nums)
                    except (ValueError, TypeError):
                        # 숫자 변환 실패 시 문자열로 비교
                        pass

                # 문자열 비교
                if operator == "==":
                    return all(fv == value for _, fv in field_values)
                elif operator == "!=":
                    return all(fv != value for _, fv in field_values)
                elif operator == ">":
                    return all(fv > value for _, fv in field_values)
                elif operator == ">=":
                    return all(fv >= value for _, fv in field_values)
                elif operator == "<":
                    return all(fv < value for _, fv in field_values)
                elif operator == "<=":
                    return all(fv <= value for _, fv in field_values)
                elif operator == "in":
                    return all(value in fv for _, fv in field_values)
                elif operator == "not in":
                    return all(value not in fv for _, fv in field_values)
                elif operator == "contains":
                    return all(str(value) in str(fv) for _, fv in field_values)
                elif operator == "not contains":
                    return all(str(value) not in str(fv) for _, fv in field_values)
                return False
                
        except Exception as e:
            self.logger.error(f"다중 필드 조건 평가 중 오류: {str(e)}")
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

        # 숫자 비교 연산자일 때 int/float 변환 시도
        if operator in [">", ">=", "<", "<=", "==", "!="]:
            try:
                # 둘 다 숫자라면 변환
                fv = float(field_value)
                vv = float(value)
            except (ValueError, TypeError):
                fv = field_value
                vv = value
        else:
            fv = field_value
            vv = value

        # 연산자별 비교
        if operator == "==":
            return fv == vv
        elif operator == "!=":
            return fv != vv
        elif operator == ">":
            return fv > vv
        elif operator == "<":
            return fv < vv
        elif operator == ">=":
            return fv >= vv
        elif operator == "<=":
            return fv <= vv
        else:
            return False 