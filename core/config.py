"""
설정 관리 시스템 모듈
"""

import os
import json
import sys
from typing import Dict, Any, Optional, Union

from core.constants import DEFAULT_CONFIG_PATH, USER_DATA_DIR, ConfigKey, SpreadsheetConfigKey
from core.logger import get_logger

class ConfigManager:
    """설정 관리 클래스"""
    
    _instance = None
    _initialized = False
    _is_saving = False  # 저장 중 플래그
    
    def __new__(cls):
        """싱글톤 패턴 구현"""
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self, config_path: str = None):
        """
        초기화
        
        Args:
            config_path: 설정 파일 경로 (None인 경우 기본 경로 사용)
        """
        if ConfigManager._initialized:
            return
        
        self.logger = get_logger(__name__)
        
        # 설정 파일 경로 설정
        if config_path is None:
            exe_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config_path = os.path.join(exe_dir, 'config.json')
        
        self.config_path = config_path
        self.logger.info(f"설정 파일 경로 설정: {self.config_path}")
        
        # 설정 데이터 로드
        self.config = self._load_config()
        
        ConfigManager._initialized = True
    
    def _load_config(self) -> Dict[str, Any]:
        """
        설정 파일 로드
        
        Returns:
            Dict[str, Any]: 설정 데이터
        """
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            self.logger.error(f"설정 파일 로드 실패: {str(e)}")
            return {}
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        설정 값 가져오기
        
        Args:
            key: 설정 키
            default: 기본값
            
        Returns:
            Any: 설정 값
        """
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """
        설정 값 설정
        
        Args:
            key: 설정 키
            value: 설정 값
        """
        if self.config.get(key) != value:
            self.config[key] = value
            self.logger.info(f"설정 값이 변경되었습니다: {key}={value}")
        else:
            self.logger.debug(f"설정 값이 변경되지 않았습니다: {key}={value}")
    
    def save(self) -> bool:
        """
        설정 파일 저장
        
        Returns:
            bool: 성공 여부
        """
        try:
            # 설정 파일 디렉토리 생성
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            
            # 설정 파일 저장
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            
            self.logger.info("설정 파일 저장 완료")
            return True
            
        except Exception as e:
            self.logger.error(f"설정 파일 저장 실패: {str(e)}")
            return False
    
    def set_batch(self, settings: Dict[str, Any]) -> None:
        """여러 설정 값을 한 번에 설정하기"""
        if not settings:
            return
            
        # 설정 업데이트
        for key, value in settings.items():
            if isinstance(key, (ConfigKey, SpreadsheetConfigKey)):
                key = key.value
            self.config[key] = value
            
        # 한 번만 저장
        self.save()
    
    def get_all(self) -> Dict[str, Any]:
        """모든 설정 값 가져오기"""
        return self.config.copy() 

    def get_login_url(self) -> str:
        base = self.get("swatchon_admin_url", "https://admin.swatchon.me")
        return f"{base}/users/sign_in"

    def get_receive_url(self) -> str:
        return self.get("receive_scraping_url") or f"{self.get('swatchon_admin_url', 'https://admin.swatchon.me')}/purchase_products/receive_index" 