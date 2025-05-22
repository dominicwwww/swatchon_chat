"""
템플릿 서비스 모듈
"""

import os
import json
import sys
from datetime import datetime
from typing import Dict, Any, Optional, Union, List

from core.logger import get_logger
from core.exceptions import TemplateException
from core.types import OrderType, FboOperationType, SboOperationType
from core.constants import DEFAULT_TEMPLATES_PATH, USER_DATA_DIR


class TemplateService:
    """템플릿 서비스 클래스"""
    
    def __init__(self):
        """초기화"""
        self.logger = get_logger(__name__)
        self.templates = self._load_templates_file()
    
    def load_template(self, order_type: OrderType, operation_type: Union[FboOperationType, SboOperationType]) -> Optional[Dict[str, Any]]:
        """
        템플릿 로드
        
        Args:
            order_type: 주문 유형
            operation_type: 작업 유형
            
        Returns:
            Optional[Dict[str, Any]]: 템플릿 데이터 (없으면 None)
        """
        # 템플릿 파일에서 해당 유형의 템플릿 찾기
        order_type_str = order_type.value
        operation_type_str = operation_type.value
        
        if order_type_str in self.templates and operation_type_str in self.templates[order_type_str]:
            return self.templates[order_type_str][operation_type_str]
        
        self.logger.error(f"템플릿을 찾을 수 없습니다: {order_type_str}/{operation_type_str}")
        return None
    
    def render_message(self, order_type: OrderType, operation_type: Union[FboOperationType, SboOperationType], 
                       data: Dict[str, Any]) -> Optional[str]:
        """
        메시지 렌더링
        
        Args:
            order_type: 주문 유형
            operation_type: 작업 유형
            data: 변수 데이터
            
        Returns:
            Optional[str]: 렌더링된 메시지 (실패 시 None)
        """
        template = self.load_template(order_type, operation_type)
        if not template:
            return None
        
        try:
            # 템플릿 컨텐츠 가져오기
            content = template.get("content", "")
            
            # 변수 치환
            for var_name, var_value in data.items():
                placeholder = "{" + var_name + "}"
                content = content.replace(placeholder, str(var_value))
            
            # 공통 헤더/푸터 적용 (있을 경우)
            if "defaults" in self.templates:
                defaults = self.templates["defaults"]
                
                # 헤더 추가 (템플릿에 헤더가 포함되어 있지 않은 경우)
                if "header" in defaults and not content.startswith(defaults["header"]):
                    content = defaults["header"] + " " + content
                
                # 푸터 추가 (템플릿에 푸터가 포함되어 있지 않은 경우)
                if "footer" in defaults and not content.endswith(defaults["footer"]):
                    content = content + defaults["footer"]
            
            return content
        
        except Exception as e:
            self.logger.error(f"메시지 렌더링 실패: {str(e)}")
            return None
    
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
    
    def update_template(self, order_type: OrderType, operation_type: Union[FboOperationType, SboOperationType],
                      title: str, content: str, variables: Optional[List[str]] = None) -> bool:
        """
        템플릿 업데이트
        
        Args:
            order_type: 주문 유형
            operation_type: 작업 유형
            title: 템플릿 제목
            content: 템플릿 내용
            variables: 변수 목록 (None인 경우 자동 추출)
            
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
            "last_modified": datetime.now().isoformat()
        }
        
        # 템플릿 파일 저장
        return self._save_templates_file()
    
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
                return self._save_templates_file()
            
            return False
        
        except Exception as e:
            self.logger.error(f"기본 템플릿으로 초기화 실패: {str(e)}")
            return False
    
    def _load_templates_file(self) -> Dict[str, Any]:
        """
        템플릿 파일 로드
        
        Returns:
            Dict[str, Any]: 템플릿 데이터
        """
        try:
            # 사용자 템플릿 파일 위치
            templates_path = self._get_templates_path()
            
            # 템플릿 파일이 있으면 로드
            if os.path.exists(templates_path):
                with open(templates_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            
            # 템플릿 파일이 없으면 기본 템플릿 파일 복사
            return self._create_default_templates()
            
        except Exception as e:
            self.logger.error(f"템플릿 파일 로드 실패: {str(e)}")
            return self._create_empty_templates()
    
    def _get_templates_path(self) -> str:
        """
        템플릿 파일 경로 반환
        
        Returns:
            str: 템플릿 파일 경로
        """
        # 사용자 문서 폴더 내 템플릿 파일 경로
        home_dir = os.path.expanduser("~")
        docs_dir = os.path.join(home_dir, "Documents" if sys.platform == "win32" else "Documents")
        app_dir = os.path.join(docs_dir, USER_DATA_DIR)
        os.makedirs(app_dir, exist_ok=True)
        return os.path.join(app_dir, "templates.json")
    
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
    
    def _create_default_templates(self) -> Dict[str, Any]:
        """
        기본 템플릿 파일 생성
        
        Returns:
            Dict[str, Any]: 기본 템플릿 데이터
        """
        try:
            # 기본 템플릿 데이터 로드
            default_templates = self._load_default_templates()
            
            # 사용자 템플릿 파일 경로
            templates_path = self._get_templates_path()
            
            # 템플릿 파일 저장
            with open(templates_path, 'w', encoding='utf-8') as f:
                json.dump(default_templates, f, ensure_ascii=False, indent=2)
            
            return default_templates
        
        except Exception as e:
            self.logger.error(f"기본 템플릿 파일 생성 실패: {str(e)}")
            return self._create_empty_templates()
    
    def _save_templates_file(self) -> bool:
        """
        템플릿 파일 저장
        
        Returns:
            bool: 성공 여부
        """
        try:
            # 템플릿 파일 경로
            templates_path = self._get_templates_path()
            
            # 템플릿 파일 저장
            with open(templates_path, 'w', encoding='utf-8') as f:
                json.dump(self.templates, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            self.logger.error(f"템플릿 파일 저장 실패: {str(e)}")
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
                    "content": "[SwatchOn] {seller_name}님 안녕하세요.\n\n다음 주문의 출고를 요청드립니다.\n\n- 주문번호: {order_number}\n- 상품명: {product_name}\n- 수량: {quantity}개\n\n감사합니다.",
                    "variables": ["seller_name", "order_number", "product_name", "quantity"],
                    "last_modified": datetime.now().isoformat()
                },
                "shipment_confirm": {
                    "title": "FBO 출고 확인",
                    "content": "[SwatchOn] {seller_name}님\n\n출고 확인되었습니다.\n\n- 주문번호: {order_number}\n- 송장번호: {tracking_number}\n\n감사합니다.",
                    "variables": ["seller_name", "order_number", "tracking_number"],
                    "last_modified": datetime.now().isoformat()
                },
                "po": {
                    "title": "FBO 발주 확인 요청",
                    "content": "[SwatchOn] {seller_name}님\n\n발주 확인 요청드립니다.\n\n- 발주번호: {po_number}\n- 상품명: {product_name}\n- 수량: {quantity}개\n\n감사합니다.",
                    "variables": ["seller_name", "po_number", "product_name", "quantity"],
                    "last_modified": datetime.now().isoformat()
                }
            },
            "sbo": {
                "po": {
                    "title": "SBO 스와치 발주",
                    "content": "[SwatchOn] {seller_name}님\n\n스와치 발주합니다.\n\n- 주문번호: {order_number}\n- 스와치 정보: {swatch_details}\n\n감사합니다.",
                    "variables": ["seller_name", "order_number", "swatch_details"],
                    "last_modified": datetime.now().isoformat()
                },
                "pickup_request": {
                    "title": "SBO 스와치 픽업 요청",
                    "content": "[SwatchOn] {seller_name}님\n\n스와치 픽업 요청드립니다.\n\n- 주문번호: {order_number}\n- 픽업 날짜: {pickup_date}\n- 픽업 시간: {pickup_time}\n\n감사합니다.",
                    "variables": ["seller_name", "order_number", "pickup_date", "pickup_time"],
                    "last_modified": datetime.now().isoformat()
                }
            },
            "defaults": {
                "header": "[SwatchOn]",
                "footer": "\n\n감사합니다.\nSwatchOn 팀 드림."
            },
            "settings": {
                "version": "1.0",
                "last_modified": datetime.now().isoformat(),
                "created_by": "SwatchOn"
            }
        } 