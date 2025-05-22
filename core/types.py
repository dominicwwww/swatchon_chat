from enum import Enum, auto
from typing import Callable, Dict, List, Optional, Any, Union, TypedDict

# 로그 함수 타입
LogFunction = Callable[[str], None]

# 주문 유형 열거형
class OrderType(Enum):
    FBO = "fbo"  # Fabric Bulk Order
    SBO = "sbo"  # Swatch Box Order

# FBO 작업 유형 열거형
class FboOperationType(Enum):
    SHIPMENT_REQUEST = "shipment_request"  # 출고 요청
    SHIPMENT_CONFIRM = "shipment_confirm"  # 출고 확인
    PO = "po"                              # 발주 확인 요청

# SBO 작업 유형 열거형
class SboOperationType(Enum):
    PO = "po"                     # 스와치 발주
    PICKUP_REQUEST = "pickup_request"  # 스와치 픽업 요청

# 메시지 상태 열거형
class MessageStatus(Enum):
    PENDING = "대기중"
    SENT = "전송완료"
    FAILED = "전송실패"

# UI 섹션 유형
class SectionType(Enum):
    FBO_SHIPMENT_REQUEST = "fbo_shipment_request"
    FBO_SHIPMENT_CONFIRM = "fbo_shipment_confirm"
    FBO_PO = "fbo_po"
    SBO_PO = "sbo_po"
    SBO_PICKUP_REQUEST = "sbo_pickup_request"
    SETTINGS = "settings"
    TEMPLATE = "template"
    DASHBOARD = "dashboard"  # 대시보드 섹션 추가

# UI 테마 모드
class ThemeMode(Enum):
    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"  # 시스템 설정 따름

# 로그 타입
class LogType(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"
    DEBUG = "debug"

# 사이드바 아이템 타입
class SidebarItemType(Enum):
    SECTION = "section"  # 섹션 (FBO, SBO 등)
    CATEGORY = "category"  # 카테고리 구분선
    SPACER = "spacer"  # 여백

# 데이터 타입
ShipmentData = Dict[str, Any]
SheetRow = Dict[str, Any]
SellerList = List[str]

# 상세 타입 정의
class MessageData(TypedDict):
    """메시지 데이터 타입"""
    seller_name: str
    items: List[Dict[str, Any]]
    total_count: int
    message_type: str

# UI 컴포넌트 스타일 타입
class StyleData(TypedDict, total=False):
    """스타일 데이터 타입"""
    color: str
    background_color: str
    border: str
    padding: str
    margin: str
    font_family: str
    font_size: str
    font_weight: str 