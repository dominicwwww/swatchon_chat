"""
Pydantic 스키마 모듈
"""

from datetime import date, datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from core.types import MessageStatus, OrderType
from enum import Enum


class ShipmentItem(BaseModel):
    """출고 항목 스키마"""
    order_number: str = Field(..., description="주문 번호")
    product_name: str = Field(..., description="상품명")
    quantity: int = Field(..., description="수량", gt=0)
    seller_name: str = Field(..., description="판매자명")
    order_date: date = Field(..., description="주문일")
    shipment_date: Optional[date] = Field(None, description="출고일")
    status: str = Field("대기중", description="상태")
    
    @validator('order_number')
    def order_number_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('주문 번호는 비어있을 수 없습니다')
        return v
    
    @validator('seller_name')
    def seller_name_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('판매자명은 비어있을 수 없습니다')
        return v


class ShipmentRequestData(BaseModel):
    """출고 요청 데이터 스키마"""
    items: List[ShipmentItem] = Field(default_factory=list)
    request_date: date = Field(default_factory=date.today)
    is_processed: bool = Field(False, description="처리 여부")
    
    class Config:
        """Pydantic 설정"""
        validate_assignment = True  # 속성 할당 시 유효성 검증
        extra = "forbid"  # 추가 필드 금지


class ShipmentConfirmData(BaseModel):
    """출고 확인 데이터 스키마"""
    items: List[ShipmentItem] = Field(default_factory=list)
    confirm_date: date = Field(default_factory=date.today)
    is_processed: bool = Field(False, description="처리 여부")
    
    class Config:
        """Pydantic 설정"""
        validate_assignment = True
        extra = "forbid"


class PoItem(BaseModel):
    """발주 항목 스키마"""
    po_number: str = Field(..., description="발주 번호")
    product_name: str = Field(..., description="상품명")
    quantity: int = Field(..., description="수량", gt=0)
    seller_name: str = Field(..., description="판매자명")
    po_date: date = Field(..., description="발주일")
    status: str = Field("대기중", description="상태")


class PoData(BaseModel):
    """발주 데이터 스키마"""
    items: List[PoItem] = Field(default_factory=list)
    request_date: date = Field(default_factory=date.today)
    is_processed: bool = Field(False, description="처리 여부")


class SwatchItem(BaseModel):
    """스와치 항목 스키마"""
    order_number: str = Field(..., description="주문 번호")
    swatch_name: str = Field(..., description="스와치명")
    quantity: int = Field(..., description="수량", gt=0)
    seller_name: str = Field(..., description="판매자명")
    order_date: date = Field(..., description="주문일")
    status: str = Field("대기중", description="상태")


class PickupRequestData(BaseModel):
    """픽업 요청 데이터 스키마"""
    items: List[SwatchItem] = Field(default_factory=list)
    pickup_date: date = Field(..., description="픽업 날짜")
    pickup_time: str = Field(..., description="픽업 시간")
    request_date: date = Field(default_factory=date.today)
    is_processed: bool = Field(False, description="처리 여부")


class MessageTemplate(BaseModel):
    """메시지 템플릿 스키마"""
    title: str = Field(..., description="템플릿 제목")
    content: str = Field(..., description="템플릿 내용")
    variables: List[str] = Field(default_factory=list, description="변수 목록")
    last_modified: datetime = Field(default_factory=datetime.now, description="마지막 수정일")


class TemplateCollection(BaseModel):
    """템플릿 모음 스키마"""
    fbo: Dict[str, MessageTemplate] = Field(default_factory=dict)
    sbo: Dict[str, MessageTemplate] = Field(default_factory=dict)
    defaults: Dict[str, str] = Field(default_factory=dict)
    settings: Dict[str, Any] = Field(default_factory=dict)


class PurchaseProduct(BaseModel):
    """구매 상품 스키마"""
    id: int = Field(..., description="상품 ID")
    image_url: Optional[str] = Field(None, description="상품 이미지 URL")
    print_url: Optional[str] = Field(None, description="프린트 이미지 URL")
    store_name: str = Field(..., description="스토어명")
    store_url: Optional[str] = Field(None, description="스토어 상세 URL")
    store_address: str = Field("", description="스토어 주소")
    store_ddm_address: str = Field("", description="동대문 주소")
    quality_code: Optional[str] = Field(None, description="품질 코드")
    quality_name: str = Field(..., description="품질명")
    quality_url: Optional[str] = Field(None, description="품질 상세 URL")
    swatch_pickupable: Optional[bool] = Field(None, description="스와치 픽업 가능 여부")
    swatch_storage: Optional[str] = Field(None, description="스와치 보관 위치")
    color_number: int = Field(..., description="컬러 번호")
    color_code: Optional[str] = Field(None, description="컬러 코드")
    quantity: int = Field(..., description="수량")
    order_code: Optional[str] = Field(None, description="주문 코드")
    order_url: Optional[str] = Field(None, description="주문 상세 URL")
    purchase_code: str = Field(..., description="구매 코드")
    purchase_url: Optional[str] = Field(None, description="구매 상세 URL")
    last_pickup_at: Optional[datetime] = Field(None, description="최종 픽업 일시")
    pickup_at: datetime = Field(..., description="픽업 일시")
    delivery_method: Optional[str] = Field(None, description="배송 방법")
    logistics_company: Optional[str] = Field(None, description="물류 회사")
    status: str = Field("", description="발주 상태")  # 예: requested(발주요청중), confirmed(발주확정), cancelled(발주취소)
    message_status: str = Field(MessageStatus.PENDING.value, description="메시지 전송 상태")
    processed_at: Optional[datetime] = Field(None, description="처리 시각")
    price: Optional[str] = Field(None, description="총 가격")
    unit_price: Optional[str] = Field(None, description="단가")
    unit_price_origin: Optional[str] = Field(None, description="원본 단가")
    additional_info: Optional[str] = Field(None, description="추가 정보")
    created_at: Optional[datetime] = Field(None, description="생성 시각")
    updated_at: Optional[datetime] = Field(None, description="수정 시각")

    class Config:
        """Pydantic 설정"""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class PurchaseProductList(BaseModel):
    """구매 상품 목록 스키마"""
    items: List[PurchaseProduct] = Field(default_factory=list)
    total: int = Field(0, description="전체 개수")


class PurchaseConfirm(BaseModel):
    """발주 확인 스키마 - API 응답 데이터 매핑용"""
    purchase_code: str = Field(..., description="발주번호")
    purchase_type: str = Field("", description="발주 거래타입")
    created_at: str = Field("", description="생성시각")
    order_code: str = Field("", description="주문번호")
    seller: str = Field("", description="판매자")
    in_charge: str = Field("", description="발주담당자")
    quantity: str = Field("", description="발주수량")
    price: str = Field("", description="공급가액")
    price_changeable: str = Field("", description="단가변경여부")
    delay_allowable: str = Field("", description="지연허용여부")
    status: str = Field("", description="상태")
    payment_status: str = Field("", description="정산상태")
    internal_memo: str = Field("", description="내부메모")
    message_status: str = Field(MessageStatus.PENDING.value, description="메시지 전송 상태")
    processed_at: Optional[datetime] = Field(None, description="처리 시각")
    
    # 확장용 프로덕트 데이터
    products: List[PurchaseProduct] = Field(default_factory=list, description="발주 프로덕트 목록")
    
    class Config:
        """Pydantic 설정"""
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None,
        }


class PurchaseConfirmList(BaseModel):
    """발주 확인 목록 스키마"""
    items: List[PurchaseConfirm] = Field(default_factory=list)
    total: int = Field(0, description="전체 개수") 