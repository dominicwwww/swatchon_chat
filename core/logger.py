"""
로깅 시스템 모듈
"""

import os
import logging
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict

from core.constants import LOG_FORMAT, LOG_DATE_FORMAT, USER_DATA_DIR

# 로그 레벨 매핑
LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL
}

# 기본 로그 레벨
DEFAULT_LOG_LEVEL = logging.INFO

# 로그 최대 길이 제한
MAX_LOG_LENGTH = 1000

# 로거 인스턴스 캐시
_logger_cache: Dict[str, logging.Logger] = {}
_logger_lock = threading.Lock()

class TruncatingFormatter(logging.Formatter):
    """로그 메시지 길이를 제한하는 포매터"""
    
    def format(self, record):
        try:
            # 원본 메시지 저장
            original_msg = record.msg
            
            # 여러 줄 메시지 처리: 빈 줄/공백만 있는 줄은 무시
            lines = str(record.msg).splitlines()
            filtered_lines = [line for line in lines if line.strip()]
            record.msg = "\n".join(filtered_lines)
            
            # 메시지가 너무 길면 잘라내기
            if len(str(record.msg)) > MAX_LOG_LENGTH:
                record.msg = str(record.msg)[:MAX_LOG_LENGTH] + "... (생략됨)"
            
            result = super().format(record)
            record.msg = original_msg
            return result
        except Exception as e:
            # 포매팅 실패 시 기본 포맷 사용
            return f"로그 포매팅 오류: {str(e)}"

class DailyRotatingFileHandler(logging.FileHandler):
    """일별 로그 파일 핸들러"""
    
    def __init__(self, filename, mode='a', encoding='utf-8'):
        super().__init__(filename, mode, encoding)
        self._last_date = datetime.now().date()
        self._lock = threading.Lock()
    
    def emit(self, record):
        try:
            current_date = datetime.now().date()
            with self._lock:
                if current_date != self._last_date:
                    self.close()
                    # 새로운 파일 핸들러 생성
                    new_filename = self._get_new_filename(current_date)
                    self._file = open(new_filename, self.mode, encoding=self.encoding)
                    self._last_date = current_date
            super().emit(record)
        except Exception as e:
            print(f"로그 파일 핸들러 오류: {str(e)}")
    
    def _get_new_filename(self, date):
        """새로운 로그 파일 이름 생성"""
        log_dir = _get_log_dir()
        return os.path.join(log_dir, f"swatchon_{date.strftime('%Y-%m-%d')}.log")

def _get_log_dir() -> str:
    """로그 디렉토리 경로 반환"""
    home_dir = os.path.expanduser("~")
    doc_dir = os.path.join(home_dir, "Documents" if sys.platform == "win32" else "Documents")
    app_dir = os.path.join(doc_dir, USER_DATA_DIR)
    log_dir = os.path.join(app_dir, "logs")
    
    # 로그 디렉토리가 없으면 생성
    os.makedirs(log_dir, exist_ok=True)
    
    return log_dir

def _get_log_file() -> str:
    """현재 날짜의 로그 파일 경로 반환"""
    log_dir = _get_log_dir()
    today = datetime.now().strftime("%Y-%m-%d")
    return os.path.join(log_dir, f"swatchon_{today}.log")

def get_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    """
    로거 인스턴스 반환
    
    Args:
        name: 로거 이름
        level: 로그 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        
    Returns:
        logging.Logger: 로거 인스턴스
    """
    # 캐시된 로거 반환
    if name in _logger_cache:
        return _logger_cache[name]
    
    with _logger_lock:
        # 이중 체크 (race condition 방지)
        if name in _logger_cache:
            return _logger_cache[name]
        
        logger = logging.getLogger(name)
        
        # 이미 핸들러가 추가된 경우 다시 추가하지 않음
        if logger.handlers:
            _logger_cache[name] = logger
            return logger
        
        # 로그 레벨 설정
        log_level = LOG_LEVELS.get(level, DEFAULT_LOG_LEVEL)
        logger.setLevel(log_level)
        
        try:
            # 콘솔 핸들러 추가
            console_handler = logging.StreamHandler()
            console_handler.setLevel(log_level)
            console_formatter = TruncatingFormatter(LOG_FORMAT, LOG_DATE_FORMAT)
            console_handler.setFormatter(console_formatter)
            logger.addHandler(console_handler)
            
            # 파일 핸들러 추가 (일별 로테이션)
            file_handler = DailyRotatingFileHandler(_get_log_file(), encoding='utf-8')
            file_handler.setLevel(log_level)
            file_formatter = TruncatingFormatter(LOG_FORMAT, LOG_DATE_FORMAT)
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
            
            # 캐시에 저장
            _logger_cache[name] = logger
            
        except Exception as e:
            print(f"로거 초기화 중 오류 발생: {str(e)}")
            # 최소한의 콘솔 로깅은 유지
            if not logger.handlers:
                console_handler = logging.StreamHandler()
                console_handler.setFormatter(logging.Formatter('%(message)s'))
                logger.addHandler(console_handler)
        
        return logger 