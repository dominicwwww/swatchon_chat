"""
로깅 시스템 모듈
"""

import os
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

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

class TruncatingFormatter(logging.Formatter):
    """로그 메시지 길이를 제한하는 포매터"""
    
    def format(self, record):
        # 원본 메시지 저장
        original_msg = record.msg
        
        # 메시지가 너무 길면 잘라내기
        if len(str(record.msg)) > MAX_LOG_LENGTH:
            record.msg = str(record.msg)[:MAX_LOG_LENGTH] + "... (생략됨)"
        
        # 포맷팅
        result = super().format(record)
        
        # 원본 메시지 복원
        record.msg = original_msg
        
        return result

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
    logger = logging.getLogger(name)
    
    # 이미 핸들러가 추가된 경우 다시 추가하지 않음
    if logger.handlers:
        return logger
    
    # 로그 레벨 설정
    log_level = LOG_LEVELS.get(level, DEFAULT_LOG_LEVEL)
    logger.setLevel(log_level)
    
    # 콘솔 핸들러 추가
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_formatter = TruncatingFormatter(LOG_FORMAT, LOG_DATE_FORMAT)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # 파일 핸들러 추가
    file_handler = logging.FileHandler(_get_log_file(), encoding='utf-8')
    file_handler.setLevel(log_level)
    file_formatter = TruncatingFormatter(LOG_FORMAT, LOG_DATE_FORMAT)
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    return logger 