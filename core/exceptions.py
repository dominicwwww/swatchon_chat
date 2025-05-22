"""
사용자 정의 예외 모듈
"""

class SwatchonBaseException(Exception):
    """기본 예외 클래스"""
    pass

class ConfigException(SwatchonBaseException):
    """설정 관련 예외"""
    pass

class SheetException(SwatchonBaseException):
    """스프레드시트 관련 예외"""
    pass

class KakaoException(SwatchonBaseException):
    """카카오톡 관련 예외"""
    pass

class ScraperException(SwatchonBaseException):
    """스크래퍼 관련 예외"""
    pass

class TemplateException(SwatchonBaseException):
    """템플릿 관련 예외"""
    pass

class AuthenticationException(SwatchonBaseException):
    """인증 관련 예외"""
    pass

class UIException(SwatchonBaseException):
    """UI 관련 예외"""
    pass

class NetworkException(SwatchonBaseException):
    """네트워크 관련 예외"""
    pass

class DataException(SwatchonBaseException):
    """데이터 관련 예외"""
    pass

class ValidationException(SwatchonBaseException):
    """데이터 유효성 검증 관련 예외"""
    pass 