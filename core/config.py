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
    
    def __init__(self):
        """초기화 메서드 - 한 번만 호출되도록 함"""
        if ConfigManager._initialized:
            return
        
        self._config_path = None
        self.logger = get_logger(__name__)
        self._config = {}
        
        # 설정 파일 경로 결정
        self._determine_config_path()
        
        # 설정 파일 로드
        self._load_config()
        
        ConfigManager._initialized = True
    
    def _determine_config_path(self):
        """설정 파일 경로 결정 (한 번만 호출)"""
        try:
            # 현재 작업 디렉토리를 기준으로 설정 파일 경로 설정
            current_dir = os.getcwd()
            config_path = os.path.join(current_dir, DEFAULT_CONFIG_PATH)
            
            # 항상 현재 작업 디렉토리의 config.json 사용
            self._config_path = config_path
            print(f"설정 파일 경로 설정: {config_path}")
            
            # 설정 파일이 없으면 빈 파일 생성
            if not os.path.exists(config_path):
                with open(config_path, 'w', encoding='utf-8') as f:
                    f.write('{}')
                print(f"설정 파일이 없어 빈 파일 생성: {config_path}")
        except Exception as e:
            # 오류 발생 시 현재 디렉토리에 config.json 사용
            self.logger.error(f"설정 파일 경로 결정 중 오류: {str(e)}")
            self._config_path = "config.json"
            print(f"오류로 인해 현재 디렉토리의 설정 파일 사용: {self._config_path}")
    
    def _load_config(self):
        """설정 파일 로드"""
        try:
            # 설정 파일이 있으면 로드
            if os.path.exists(self._config_path):
                with open(self._config_path, 'r', encoding='utf-8') as f:
                    self._config = json.load(f)
            else:
                # 설정 파일이 없으면 기본 설정 파일 생성
                self._create_default_config()
        except Exception as e:
            self.logger.error(f"설정 파일 로드 실패: {str(e)}")
            self._config = {}
    
    def _create_default_config(self):
        """기본 설정 파일 생성"""
        try:
            # 실행 파일 경로의 기본 설정 파일 경로
            exe_dir = os.path.dirname(os.path.abspath(__file__))
            app_dir = os.path.dirname(os.path.dirname(exe_dir))
            default_config_path = os.path.join(app_dir, DEFAULT_CONFIG_PATH)
            
            # 기본 설정 파일이 있으면 로드
            if os.path.exists(default_config_path):
                with open(default_config_path, 'r', encoding='utf-8') as f:
                    self._config = json.load(f)
                
                # 설정 파일 저장
                self._save_config()
            else:
                # 기본 설정 파일이 없으면 빈 설정 사용
                self._config = {}
                
        except Exception as e:
            self.logger.error(f"기본 설정 파일 생성 실패: {str(e)}")
            self._config = {}
    
    def get(self, key: Union[str, ConfigKey, SpreadsheetConfigKey], default: Any = None) -> Any:
        """설정 값 가져오기"""
        if isinstance(key, (ConfigKey, SpreadsheetConfigKey)):
            key = key.value
        return self._config.get(key, default)
    
    def set(self, key: Union[str, ConfigKey, SpreadsheetConfigKey], value: Any) -> None:
        """설정 값 설정하기"""
        # 현재 저장 중이면 설정만 업데이트하고 저장은 하지 않음
        if ConfigManager._is_saving:
            print(f"이미 저장 중입니다. 설정만 업데이트: {key}")
            if isinstance(key, (ConfigKey, SpreadsheetConfigKey)):
                key = key.value
            self._config[key] = value
            return
            
        # 설정 값 변경
        if isinstance(key, (ConfigKey, SpreadsheetConfigKey)):
            key = key.value
        
        # 값이 실제로 변경되었는지 확인
        old_value = self._config.get(key)
        if old_value == value:
            print(f"설정 값이 변경되지 않았습니다: {key}={value}")
            return
            
        # 값 설정 및 저장
        self._config[key] = value
        self._save_config()
    
    def set_batch(self, settings: Dict[str, Any]) -> None:
        """여러 설정 값을 한 번에 설정하기"""
        if not settings:
            return
            
        # 설정 업데이트
        for key, value in settings.items():
            if isinstance(key, (ConfigKey, SpreadsheetConfigKey)):
                key = key.value
            self._config[key] = value
            
        # 한 번만 저장
        self._save_config()
    
    def _save_config(self) -> None:
        """설정 파일 저장"""
        # 이미 저장 중이면 중첩 호출 방지
        if ConfigManager._is_saving:
            print("이미 설정 저장 중입니다. 중첩 저장 요청 무시")
            return
            
        try:
            # 저장 중 플래그 설정
            ConfigManager._is_saving = True
            
            # 경로가 정해지지 않았으면 다시 결정
            if not self._config_path:
                self._determine_config_path()
                
            # 설정 파일 저장 경로 출력
            print(f"설정을 저장합니다: {self._config_path}")
            
            # 설정 파일 저장
            with open(self._config_path, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, ensure_ascii=False, indent=2)
                
            print(f"설정 저장 완료: {self._config_path}")
        except Exception as e:
            # 오류 상세 정보 출력
            print(f"설정 파일 저장 실패: {str(e)}")
            print(f"오류 유형: {type(e).__name__}")
            
            # 스택 트레이스 출력
            import traceback
            traceback.print_exc()
        finally:
            # 저장 중 플래그 해제
            ConfigManager._is_saving = False
    
    def get_all(self) -> Dict[str, Any]:
        """모든 설정 값 가져오기"""
        return self._config.copy() 