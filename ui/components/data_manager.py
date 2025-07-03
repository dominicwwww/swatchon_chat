"""
데이터 관리자 컴포넌트 - 재사용 가능한 API 연동 및 데이터 관리 기능 (날짜별 캐시 지원)
"""
from typing import List, Dict, Any, Optional, Callable, Union
from datetime import datetime, date
from PySide6.QtCore import QObject, Signal, QTimer
from PySide6.QtWidgets import QMessageBox
import json
import os
import glob

from core.types import OrderType, FboOperationType, SboOperationType, ShipmentStatus
from services.api_service import ApiService
from core.schemas import (
    PurchaseProduct, PurchaseProductList, MessageStatus, 
    PurchaseConfirm, PurchaseConfirmList
)
from ui.components.log_widget import LOG_INFO, LOG_DEBUG, LOG_WARNING, LOG_ERROR, LOG_SUCCESS
from core.constants import MESSAGE_STATUS_LABELS


class DataManager(QObject):
    """
    데이터 관리자 - 여러 섹션에서 재사용 가능한 데이터 관리 기능
    
    기능:
    - API 데이터 로드 및 날짜별 캐시
    - 파일 저장/로드
    - 데이터 변환 및 매핑
    - 필터링 및 검색
    - 메시지 상태 기록 및 관리
    """
    
    # 시그널 정의
    data_loaded = Signal(list)  # 데이터 로드 완료
    data_filtered = Signal(list)  # 데이터 필터링 완료
    error_occurred = Signal(str)  # 오류 발생
    
    def __init__(self, order_type: OrderType, data_dir: str = None, log_function: Optional[Callable] = None):
        """
        초기화
        
        Args:
            order_type: 주문 유형 (FBO, SBO)
            data_dir: 데이터 디렉토리 경로 (None이면 루트 data 디렉토리 사용)
            log_function: 로그 함수
        """
        super().__init__()
        self.order_type = order_type
        self.log_function = log_function
        
        # 데이터 저장소
        self.data: List[PurchaseProduct] = []
        self.filtered_data: List[PurchaseProduct] = []
        self.purchase_products_data: Dict[str, List[Dict[str, Any]]] = {}
        
        # 파일 경로 설정
        if data_dir is None:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            data_dir = os.path.join(project_root, 'data', 'api_cache')
        
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)
        
        # 파일명 프리픽스 설정
        if order_type == OrderType.FBO:
            self.file_prefix = "fbo_products"
        elif order_type == OrderType.SBO:
            self.file_prefix = "sbo_products"
        else:
            self.file_prefix = "products"  # 기본값
        
        # 서비스 인스턴스
        self.api_service = ApiService()
        
        # 필터 상태
        self.current_search_text = ""
        self.current_status_filter = "all"
        
        # 현재 로드된 데이터의 날짜
        self.current_data_date: Optional[str] = None
    
    def log(self, message: str, level: str = LOG_INFO):
        """로그 출력"""
        if self.log_function:
            self.log_function(message, level)
    
    def load_data_from_api(self) -> bool:
        """
        API에서 데이터 로드 (날짜별 캐시 지원)
        
        Returns:
            bool: 성공 여부
        """
        try:
            today = date.today().strftime('%y%m%d')
            
            # 오늘 날짜의 캐시 파일이 있는지 확인
            cached_file = self._get_today_cache_file()
            if cached_file and os.path.exists(cached_file):
                self.log(f"오늘 날짜 ({today})의 캐시 파일을 발견했습니다: {os.path.basename(cached_file)}", LOG_INFO)
                # 기존 캐시 파일이 있는 경우, API 데이터와 비교 병합
                if not self._load_and_merge_with_api(cached_file):
                    # API 병합 실패 시 캐시만 로드
                    return self._load_cached_data_with_status_preservation(cached_file)
                return True
            
            self.log(f"{self.order_type.value} 데이터를 API에서 새로고침합니다.", LOG_INFO)
            
            # API 호출
            items = self.api_service.get_purchase_products()
            if not items:
                self.log("API에서 데이터를 받아오지 못했습니다.", LOG_WARNING)
                return False
            
            self.log(f"API에서 총 {len(items)}건의 데이터를 가져왔습니다.", LOG_INFO)
            
            # 데이터 변환 및 필터링
            purchase_products = []
            
            for item in items:
                try:
                    product_data = self._map_api_response_to_product_data(item)
                    
                    # status가 'confirmed' 또는 'delivery_requested'인 항목만 처리
                    if product_data.get('status') not in ['confirmed', 'delivery_requested']:
                        continue
                    
                    product = PurchaseProduct(**product_data)
                    purchase_products.append(product)
                    
                except Exception as e:
                    self.log(f"데이터 변환 실패: {str(e)}", LOG_WARNING)
                    continue
            
            self.log(f"confirmed/delivery_requested 상태의 데이터 {len(purchase_products)}건을 필터링했습니다.", LOG_INFO)
            
            # 기존 데이터와 병합 (새로운 방식)
            merged_data, stats = self.merge_data_with_existing(purchase_products)
            
            # 로그 출력
            if stats['new_count'] > 0 or stats['updated_count'] > 0 or stats['deleted_count'] > 0:
                self.log(f"데이터 업데이트 - 신규: {stats['new_count']}건, 변경: {stats['updated_count']}건, 유지: {stats['unchanged_count']}건, 삭제: {stats['deleted_count']}건", LOG_SUCCESS)
            else:
                self.log(f"변경사항 없음 - 총 {stats['total_count']}건", LOG_INFO)
            
            # 데이터 저장
            self.data = merged_data
            self.filtered_data = self.data.copy()
            self.current_data_date = today
            
            # 오늘 날짜로 캐시 파일 저장
            self._save_today_cache_file()
            
            # 시그널 발생
            self.data_loaded.emit(self.data)
            
            return True
            
        except Exception as e:
            self.log(f"API 데이터 로드 중 오류: {str(e)}", LOG_ERROR)
            self.error_occurred.emit(str(e))
            return False
    
    def _get_today_cache_file(self) -> Optional[str]:
        """오늘 날짜의 캐시 파일 경로 반환"""
        today = date.today().strftime('%y%m%d')
        pattern = os.path.join(self.data_dir, f'shipment_requests_{today}-*.json')
        files = glob.glob(pattern)
        return files[0] if files else None
    
    def _save_today_cache_file(self) -> Optional[str]:
        """오늘 날짜로 캐시 파일 저장 (기존 파일 업데이트 방식)"""
        try:
            today = date.today().strftime('%y%m%d')
            
            # 기존 오늘 날짜 파일이 있는지 확인
            existing_files = glob.glob(os.path.join(self.data_dir, f'shipment_requests_{today}-*.json'))
            
            if existing_files:
                # 기존 파일이 있으면 가장 오래된 파일을 업데이트 (최초 파일 유지)
                file_path = min(existing_files, key=os.path.getctime)
                self.log(f"기존 캐시 파일을 업데이트합니다: {os.path.basename(file_path)}", LOG_INFO)
            else:
                # 기존 파일이 없으면 새로 생성
                timestamp = datetime.now().strftime('%H%M')
                filename = f'shipment_requests_{today}-{timestamp}.json'
                file_path = os.path.join(self.data_dir, filename)
                self.log(f"새 캐시 파일을 생성합니다: {filename}", LOG_INFO)
            
            # PurchaseProduct 객체를 딕셔너리로 변환
            data_dicts = []
            for item in self.data:
                item_dict = self._purchase_product_to_dict(item)
                data_dicts.append(item_dict)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data_dicts, f, ensure_ascii=False, indent=2)
            
            self.log(f"캐시 파일 저장 완료: {os.path.basename(file_path)}", LOG_SUCCESS)
            return file_path
            
        except Exception as e:
            self.log(f"캐시 파일 저장 중 오류: {str(e)}", LOG_ERROR)
            return None
    
    def _load_cached_data_with_status_preservation(self, file_path: str) -> bool:
        """캐시된 데이터를 로드하면서 기존 메시지 상태 보존"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 딕셔너리 데이터를 PurchaseProduct 객체로 변환
            purchase_products = []
            for item_data in data:
                try:
                    # status가 'confirmed' 또는 'delivery_requested'인 항목만 처리
                    if item_data.get('status') not in ['confirmed', 'delivery_requested']:
                        continue
                    
                    # 날짜 필드 처리
                    if isinstance(item_data.get('pickup_at'), str):
                        item_data['pickup_at'] = self._safe_datetime_convert(item_data['pickup_at'])
                    
                    # 처리 시각 필드 처리
                    if item_data.get('processed_at') and isinstance(item_data['processed_at'], str):
                        item_data['processed_at'] = self._safe_datetime_convert(item_data['processed_at'])
                    
                    # 기본 상태 설정
                    if 'status' not in item_data or not item_data['status']:
                        item_data['status'] = ""
                    
                    # 메시지 상태 기본값 설정 (캐시된 값이 있으면 그대로 사용)
                    if 'message_status' not in item_data:
                        item_data['message_status'] = ShipmentStatus.PENDING.value
                    
                    product = PurchaseProduct(**item_data)
                    purchase_products.append(product)
                    
                except Exception as e:
                    self.log(f"캐시 데이터 변환 실패: {str(e)}", LOG_WARNING)
                    continue
            
            # 데이터 저장
            self.data = purchase_products
            self.filtered_data = self.data.copy()
            self.current_data_date = date.today().strftime('%y%m%d')
            
            # 시그널 발생
            self.data_loaded.emit(self.data)
            
            self.log(f"캐시된 데이터를 로드했습니다: {len(purchase_products)}건", LOG_SUCCESS)
            return True
            
        except Exception as e:
            self.log(f"캐시 데이터 로드 중 오류: {str(e)}", LOG_ERROR)
            return False
    
    def _preserve_existing_message_status(self, new_data: List[PurchaseProduct]) -> List[PurchaseProduct]:
        """기존 데이터의 메시지 상태와 처리 시각을 새 데이터에 적용"""
        if not self.data:
            return new_data
        
        # 기존 데이터를 ID로 매핑
        existing_status_map = {}
        for item in self.data:
            existing_status_map[item.id] = {
                'message_status': getattr(item, 'message_status', ShipmentStatus.PENDING.value),
                'processed_at': getattr(item, 'processed_at', None)
            }
        
        # 새 데이터에 기존 상태 적용
        preserved_count = 0
        for item in new_data:
            if item.id in existing_status_map:
                existing_info = existing_status_map[item.id]
                item.message_status = existing_info['message_status']
                item.processed_at = existing_info['processed_at']
                preserved_count += 1
        
        if preserved_count > 0:
            self.log(f"{preserved_count}개 항목의 메시지 상태를 보존했습니다.", LOG_INFO)
        
        return new_data
    
    def merge_data_with_existing(self, new_data: List[PurchaseProduct]) -> tuple[List[PurchaseProduct], dict]:
        """
        새 데이터와 기존 데이터를 병합하고 변경 통계 반환
        중요: message_status와 processed_at은 항상 기존 값 보존
        
        Args:
            new_data: 새로 가져온 데이터
            
        Returns:
            tuple: (병합된 데이터, 통계 정보)
        """
        if not self.data:
            # 기존 데이터가 없으면 모두 새 데이터 (신규 항목에는 기본 메시지 상태 설정)
            for item in new_data:
                item.message_status = ShipmentStatus.PENDING.value
                item.processed_at = None
            return new_data, {
                'new_count': len(new_data),
                'updated_count': 0,
                'unchanged_count': 0,
                'deleted_count': 0,
                'total_count': len(new_data)
            }
        
        # 기존 데이터를 ID로 매핑
        existing_map = {item.id: item for item in self.data}
        new_data_ids = {item.id for item in new_data}
        
        updated_count = 0
        new_count = 0
        unchanged_count = 0
        deleted_count = 0
        merged_data = []
        
        # 새 데이터 처리
        for new_item in new_data:
            if new_item.id in existing_map:
                existing_item = existing_map[new_item.id]
                
                # 메시지 상태와 처리 시각을 기존 값으로 보존 (항상 보존)
                new_item.message_status = getattr(existing_item, 'message_status', ShipmentStatus.PENDING.value)
                new_item.processed_at = getattr(existing_item, 'processed_at', None)
                
                # 데이터 변경 여부 확인 (메시지 상태 제외)
                if self._has_purchase_product_changed(existing_item, new_item):
                    merged_data.append(new_item)
                    updated_count += 1
                    self.log(f"ID {new_item.id}: 데이터 변경됨, 메시지 상태 '{new_item.message_status}' 보존", LOG_DEBUG)
                else:
                    # 변경되지 않았지만 메시지 상태는 이미 보존됨
                    merged_data.append(new_item)
                    unchanged_count += 1
            else:
                # 새로운 항목 - 기본 메시지 상태 설정
                new_item.message_status = ShipmentStatus.PENDING.value
                new_item.processed_at = None
                merged_data.append(new_item)
                new_count += 1
                self.log(f"ID {new_item.id}: 신규 항목, 메시지 상태 '대기중'으로 설정", LOG_DEBUG)
        
        # API에서 삭제된 항목 감지
        deleted_count = len([item_id for item_id in existing_map.keys() if item_id not in new_data_ids])
        
        if deleted_count > 0:
            self.log(f"API에서 삭제된 항목 {deleted_count}개가 감지되어 로컬 데이터에서 제거됩니다.", LOG_INFO)
        
        stats = {
            'new_count': new_count,
            'updated_count': updated_count,
            'unchanged_count': unchanged_count,
            'deleted_count': deleted_count,
            'total_count': len(merged_data)
        }
        
        return merged_data, stats
    
    def _has_purchase_product_changed(self, existing: PurchaseProduct, new: PurchaseProduct) -> bool:
        """두 PurchaseProduct 객체가 변경되었는지 비교 (메시지 상태 제외)"""
        # 비교할 중요한 필드들
        compare_fields = [
            'store_name', 'store_address', 'store_ddm_address', 'quality_name',
            'color_code', 'quantity', 'purchase_code', 'pickup_at', 
            'delivery_method', 'logistics_company', 'status',
            # 새로 추가된 필드들
            'additional_info', 'price', 'unit_price', 'unit_price_origin'
        ]
        
        for field in compare_fields:
            existing_val = getattr(existing, field, None)
            new_val = getattr(new, field, None)
            
            # 날짜 필드는 문자열로 변환해서 비교
            if field == 'pickup_at':
                if hasattr(existing_val, 'date') and hasattr(new_val, 'date'):
                    existing_val = existing_val.date()
                    new_val = new_val.date()
                elif isinstance(existing_val, str) and isinstance(new_val, str):
                    pass  # 문자열이면 그대로 비교
            
            if existing_val != new_val:
                return True
        
        return False
    
    def _map_api_response_to_product_data(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        API 응답을 PurchaseProduct 데이터로 매핑
        주의: message_status와 processed_at은 여기서 설정하지 않음 (기존 값 보존을 위해)
        """
        product_data = {
            'id': self._safe_int_convert(item.get('ID', item.get('id', 0))),
            'image_url': item.get('image_url'),
            'print_url': item.get('print_url'),
            'store_name': item.get('store_name', item.get('판매자', '')),
            'store_url': item.get('store_url'),
            'store_address': item.get('store_address', ''),
            'store_ddm_address': item.get('store_ddm_address', item.get('판매자_동대문주소', '')),
            'quality_code': item.get('quality_code'),
            'quality_name': item.get('quality_name', item.get('아이템', '')),
            'quality_url': item.get('quality_url'),
            'swatch_pickupable': item.get('swatch_pickupable'),
            'swatch_storage': item.get('swatch_storage'),
            'color_number': item.get('color_number', item.get('컬러순서', 0)),
            'color_code': item.get('color_code', item.get('컬러코드', '')),
            'quantity': item.get('quantity', item.get('발주수량', 0)),
            'order_code': item.get('order_code'),
            'order_url': item.get('order_url'),
            'purchase_code': item.get('purchase_code', item.get('발주번호', '')),
            'purchase_url': item.get('purchase_url'),
            'last_pickup_at': self._safe_datetime_convert(item.get('last_pickup_at')) if item.get('last_pickup_at') else None,
            'pickup_at': item.get('pickup_at', item.get('최종출고일자', datetime.now().isoformat())),
            'delivery_method': self._map_delivery_method(item.get('delivery_method', item.get('발주배송수단', ''))),
            'logistics_company': item.get('logistics_company', self._map_logistics_company(item.get('판매자발송수단', ''))),
            'status': item.get('status', item.get('발주상태', '')),
            # 새로 추가된 필드들
            'price': item.get('price'),
            'unit_price': item.get('unit_price'),
            'unit_price_origin': item.get('unit_price_origin'),
            'additional_info': item.get('additional_info'),
            'created_at': self._safe_datetime_convert(item.get('created_at')) if item.get('created_at') else None,
            'updated_at': self._safe_datetime_convert(item.get('updated_at')) if item.get('updated_at') else None
        }
        
        # 숫자 필드 변환
        product_data['color_number'] = self._safe_int_convert(product_data['color_number'])
        product_data['quantity'] = self._safe_int_convert(product_data['quantity'])
        
        # 날짜 필드 처리
        product_data['pickup_at'] = self._safe_datetime_convert(product_data['pickup_at'])
        
        # 기본 상태 설정
        if not product_data['status']:
            product_data['status'] = ""
        
        # message_status와 processed_at은 여기서 설정하지 않음
        # merge_data_with_existing에서 기존 값 보존 또는 신규 항목에 대해서만 기본값 설정
        
        return product_data
    
    def _safe_int_convert(self, value: Any) -> int:
        """안전한 정수 변환"""
        if isinstance(value, str):
            try:
                return int(value)
            except ValueError:
                return 0
        return value if isinstance(value, int) else 0
    
    def _safe_datetime_convert(self, value: Any) -> datetime:
        """안전한 datetime 변환"""
        if isinstance(value, str):
            try:
                # YYYY/MM/DD 형식 처리
                if '/' in value:
                    value = value.replace('/', '-')
                # ISO 형식 처리
                if 'T' in value:
                    return datetime.fromisoformat(value.replace('Z', '+00:00'))
                else:
                    # YYYY-MM-DD 형식
                    return datetime.strptime(value, '%Y-%m-%d')
            except Exception:
                return datetime.now()
        return value if isinstance(value, datetime) else datetime.now()
    
    def _map_delivery_method(self, original_value: str) -> Optional[str]:
        """배송방법 매핑"""
        if not original_value or original_value in [None, "None", ""]:
            return None  # None 값은 그대로 반환
        
        mapping = {
            "동대문퀵": "quick",
            "동대문 픽업": "quick",
            "판매자발송": "logistics",
            "판매자 발송": "logistics",
            "quick": "quick",
            "logistics": "logistics"
        }
        
        return mapping.get(original_value, original_value.lower() if isinstance(original_value, str) else None)
    
    def _map_logistics_company(self, original_value: str) -> Optional[str]:
        """물류회사 매핑"""
        if not original_value or original_value in [None, "None", "", "-"]:
            return None
        
        mapping = {
            "경기택배": "kk",
            "일신택배": "is", 
            "경동택배": "kd",
            "퀵서비스": "quick_truck"
        }
        
        return mapping.get(original_value, original_value.lower() if isinstance(original_value, str) else None)
    
    def save_data(self, data: List[PurchaseProduct] = None) -> Optional[str]:
        """
        데이터를 JSON 파일로 저장 (현재 날짜 캐시 파일 업데이트)
        
        Args:
            data: 저장할 데이터 (None이면 self.data 사용)
            
        Returns:
            Optional[str]: 저장된 파일 경로
        """
        try:
            if data is None:
                data = self.data
            
            # 현재 날짜 캐시 파일 업데이트
            return self._save_today_cache_file()
            
        except Exception as e:
            self.log(f"데이터 저장 중 오류: {str(e)}", LOG_ERROR)
            return None
    
    def _purchase_product_to_dict(self, item: PurchaseProduct) -> Dict[str, Any]:
        """PurchaseProduct 객체를 딕셔너리로 변환"""
        return {
            'id': item.id,
            'image_url': getattr(item, 'image_url', None),
            'print_url': getattr(item, 'print_url', None),
            'store_name': item.store_name,
            'store_url': getattr(item, 'store_url', None),
            'store_address': item.store_address,
            'store_ddm_address': item.store_ddm_address,
            'quality_code': getattr(item, 'quality_code', None),
            'quality_name': item.quality_name,
            'quality_url': getattr(item, 'quality_url', None),
            'swatch_pickupable': getattr(item, 'swatch_pickupable', None),
            'swatch_storage': getattr(item, 'swatch_storage', None),
            'color_number': item.color_number,
            'color_code': item.color_code,
            'quantity': item.quantity,
            'order_code': getattr(item, 'order_code', None),
            'order_url': getattr(item, 'order_url', None),
            'purchase_code': item.purchase_code,
            'purchase_url': getattr(item, 'purchase_url', None),
            'last_pickup_at': item.last_pickup_at.isoformat() if getattr(item, 'last_pickup_at', None) and hasattr(item.last_pickup_at, 'isoformat') else (str(item.last_pickup_at) if getattr(item, 'last_pickup_at', None) else None),
            'pickup_at': item.pickup_at.isoformat() if hasattr(item.pickup_at, 'isoformat') else str(item.pickup_at),
            'delivery_method': item.delivery_method,
            'logistics_company': item.logistics_company,
            'status': item.status,
            'message_status': getattr(item, 'message_status', '대기중'),
            'processed_at': item.processed_at.isoformat() if item.processed_at and hasattr(item.processed_at, 'isoformat') else (str(item.processed_at) if item.processed_at else None),
            # 새로 추가된 필드들
            'price': getattr(item, 'price', None),
            'unit_price': getattr(item, 'unit_price', None),
            'unit_price_origin': getattr(item, 'unit_price_origin', None),
            'additional_info': getattr(item, 'additional_info', None),
            'created_at': item.created_at.isoformat() if getattr(item, 'created_at', None) and hasattr(item.created_at, 'isoformat') else (str(item.created_at) if getattr(item, 'created_at', None) else None),
            'updated_at': item.updated_at.isoformat() if getattr(item, 'updated_at', None) and hasattr(item.updated_at, 'isoformat') else (str(item.updated_at) if getattr(item, 'updated_at', None) else None)
        }
    
    def apply_filters(self, search_text: str = "", status_filter: str = "all") -> List[PurchaseProduct]:
        """
        검색어와 필터를 적용하여 데이터 필터링
        
        Args:
            search_text: 검색어
            status_filter: 상태 필터
            
        Returns:
            List[PurchaseProduct]: 필터링된 데이터
        """
        try:
            self.current_search_text = search_text
            self.current_status_filter = status_filter
            
            # 전체 데이터에서 시작
            filtered_data = self.data.copy()
            
            # 검색어 필터 적용
            if search_text:
                search_text_lower = search_text.lower()
                filtered_data = [
                    item for item in filtered_data 
                    if (search_text_lower in item.store_name.lower() or 
                        search_text_lower in item.purchase_code.lower())
                ]
            
            # 상태 필터 적용
            if status_filter != "all":
                if status_filter == ShipmentStatus.PENDING.value:
                    # 대기중: 메시지 상태가 대기중인 항목들
                    filtered_data = [
                        item for item in filtered_data 
                        if getattr(item, 'message_status', '대기중') in [ShipmentStatus.PENDING.value, "대기중", ""]
                    ]
                else:
                    # 특정 메시지 상태 항목만
                    filtered_data = [
                        item for item in filtered_data 
                        if getattr(item, 'message_status', '대기중') == status_filter
                    ]
            
            self.filtered_data = filtered_data
            
            # 시그널 발생
            self.data_filtered.emit(self.filtered_data)
            
            return self.filtered_data
            
        except Exception as e:
            self.log(f"데이터 필터링 중 오류: {str(e)}", LOG_ERROR)
            return []
    
    def get_statistics(self) -> Dict[str, str]:
        """
        데이터 통계 정보 반환 (숫자에 3자리마다 콤마)
        Returns:
            Dict[str, str]: 통계 정보 (문자열)
        """
        if not self.data:
            return {
                'total': '0',
                'pending': '0',
                'sending': '0',
                'sent': '0',
                'failed': '0',
                'cancelled': '0'
            }
        stats = {
            'total': len(self.data),
            'pending': len([item for item in self.data if getattr(item, 'message_status', '대기중') in [ShipmentStatus.PENDING.value, "대기중", ""]]),
            'sending': len([item for item in self.data if getattr(item, 'message_status', '대기중') == ShipmentStatus.SENDING.value]),
            'sent': len([item for item in self.data if getattr(item, 'message_status', '대기중') == ShipmentStatus.SENT.value]),
            'failed': len([item for item in self.data if getattr(item, 'message_status', '대기중') == ShipmentStatus.FAILED.value]),
            'cancelled': len([item for item in self.data if getattr(item, 'message_status', '대기중') == ShipmentStatus.CANCELLED.value])
        }
        # 3자리 콤마 포맷
        return {k: f"{v:,}" for k, v in stats.items()}
    
    def update_item_status(self, item_ids: List[int], status: str, set_processed_time: bool = False):
        """
        항목들의 메시지 상태 업데이트 및 캐시 파일 자동 저장
        
        Args:
            item_ids: 업데이트할 항목 ID 목록
            status: 새로운 상태
            set_processed_time: 처리 시각 설정 여부
        """
        try:
            updated_count = 0
            current_time = datetime.now() if set_processed_time else None
            
            # data에서 업데이트
            for item in self.data:
                if item.id in item_ids:
                    item.message_status = status
                    if set_processed_time:
                        item.processed_at = current_time
                    updated_count += 1
            
            # filtered_data에서도 업데이트
            for item in self.filtered_data:
                if item.id in item_ids:
                    item.message_status = status
                    if set_processed_time:
                        item.processed_at = current_time
            
            status_msg = f"{updated_count}개 항목의 메시지 상태가 '{status}'로 업데이트되었습니다."
            if set_processed_time:
                status_msg += f" (처리시각: {current_time.strftime('%Y-%m-%d %H:%M:%S')})"
            
            self.log(status_msg, LOG_SUCCESS)
            
            # 캐시 파일 자동 업데이트
            if updated_count > 0:
                self._save_today_cache_file()
            
        except Exception as e:
            self.log(f"메시지 상태 업데이트 중 오류: {str(e)}", LOG_ERROR)
    
    def get_all_data(self) -> List[PurchaseProduct]:
        """전체 데이터 반환"""
        return self.data
    
    def get_filtered_data(self) -> List[PurchaseProduct]:
        """필터링된 데이터 반환"""
        return self.filtered_data
    
    def clear_data(self):
        """데이터 초기화"""
        self.data = []
        self.filtered_data = []
        self.current_search_text = ""
        self.current_status_filter = "all" 
    
    def _load_and_merge_with_api(self, cached_file: str) -> bool:
        """캐시된 데이터를 로드하고 API 데이터와 병합"""
        try:
            # 먼저 캐시된 데이터 로드 (기존 상태 유지)
            if not self._load_cached_data_with_status_preservation(cached_file):
                return False
            
            self.log("API에서 최신 데이터를 가져와 기존 데이터와 비교합니다...", LOG_INFO)
            
            # API 호출
            items = self.api_service.get_purchase_products()
            if not items:
                self.log("API 호출 실패, 캐시된 데이터만 사용합니다.", LOG_WARNING)
                return True  # 캐시된 데이터라도 성공
            
            # 새 데이터 변환
            new_purchase_products = []
            
            for item in items:
                try:
                    product_data = self._map_api_response_to_product_data(item)
                    
                    # status가 'confirmed' 또는 'delivery_requested'인 항목만 처리
                    if product_data.get('status') not in ['confirmed', 'delivery_requested']:
                        continue
                    
                    product = PurchaseProduct(**product_data)
                    new_purchase_products.append(product)
                    
                except Exception as e:
                    self.log(f"데이터 변환 실패: {str(e)}", LOG_WARNING)
                    continue
            
            # 기존 캐시 데이터와 새 API 데이터 병합
            merged_data, stats = self.merge_data_with_existing(new_purchase_products)
            
            # 변경사항이 있는 경우에만 업데이트
            if stats['new_count'] > 0 or stats['updated_count'] > 0 or stats['deleted_count'] > 0:
                self.log(f"데이터 업데이트 - 신규: {stats['new_count']}건, 변경: {stats['updated_count']}건, 유지: {stats['unchanged_count']}건, 삭제: {stats['deleted_count']}건", LOG_SUCCESS)
                
                # 데이터 저장
                self.data = merged_data
                self.filtered_data = self.data.copy()
                
                # 캐시 파일 다시 저장
                self._save_today_cache_file()
                
                # 시그널 발생
                self.data_loaded.emit(self.data)
            else:
                self.log(f"변경사항 없음 - 총 {stats['total_count']}건", LOG_INFO)
            
            return True
            
        except Exception as e:
            self.log(f"데이터 병합 중 오류: {str(e)}", LOG_ERROR)
            return False 
    
    def save_purchase_products(self, purchase_code: str, products: List[Dict[str, Any]]) -> bool:
        """
        발주프로덕트 데이터를 저장 (기존 파일 업데이트 방식)
        
        Args:
            purchase_code: 발주번호
            products: 프로덕트 목록
            
        Returns:
            bool: 저장 성공 여부
        """
        try:
            # 메모리에 저장
            self.purchase_products_data[purchase_code] = products
            
            # 파일로도 저장 (발주번호별 개별 파일)
            today = date.today().strftime('%y%m%d')
            
            # 기존 해당 발주번호 파일이 있는지 확인
            existing_files = glob.glob(os.path.join(self.data_dir, f'{self.file_prefix}_{purchase_code}_*.json'))
            
            if existing_files:
                # 기존 파일이 있으면 가장 오래된 파일을 업데이트 (최초 파일 유지)
                file_path = min(existing_files, key=os.path.getctime)
                self.log(f"기존 {self.file_prefix} 번호 {purchase_code} 파일을 업데이트합니다: {os.path.basename(file_path)}", LOG_INFO)
            else:
                # 기존 파일이 없으면 새로 생성
                timestamp = datetime.now().strftime('%H%M')
                filename = f'{self.file_prefix}_{purchase_code}_{today}-{timestamp}.json'
                file_path = os.path.join(self.data_dir, filename)
                self.log(f"새 {self.file_prefix} 번호 {purchase_code} 파일을 생성합니다: {filename}", LOG_INFO)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(products, f, ensure_ascii=False, indent=2)
            
            self.log(f"{self.file_prefix} 번호 {purchase_code}의 프로덕트 데이터를 저장했습니다: {os.path.basename(file_path)}", LOG_SUCCESS)
            return True
            
        except Exception as e:
            self.log(f"{self.file_prefix} 번호 {purchase_code}의 프로덕트 데이터 저장 중 오류: {str(e)}", LOG_ERROR)
            return False
    
    def load_purchase_products(self, purchase_code: str) -> List[Dict[str, Any]]:
        """
        발주프로덕트 데이터를 로드
        
        Args:
            purchase_code: 발주번호
            
        Returns:
            List[Dict[str, Any]]: 프로덕트 목록
        """
        try:
            # 메모리에서 먼저 확인
            if purchase_code in self.purchase_products_data:
                return self.purchase_products_data[purchase_code]
            
            # 파일에서 로드
            pattern = os.path.join(self.data_dir, f'{self.file_prefix}_{purchase_code}_*.json')
            files = glob.glob(pattern)
            
            if files:
                # 가장 최신 파일 사용
                latest_file = max(files, key=os.path.getmtime)
                
                with open(latest_file, 'r', encoding='utf-8') as f:
                    products = json.load(f)
                
                # 메모리에 캐시
                self.purchase_products_data[purchase_code] = products
                
                self.log(f"{self.file_prefix} 번호 {purchase_code}의 프로덕트 데이터를 로드했습니다: {len(products)}건", LOG_INFO)
                return products
            
            # 데이터가 없으면 빈 리스트 반환
            return []
            
        except Exception as e:
            self.log(f"{self.file_prefix} 번호 {purchase_code}의 프로덕트 데이터 로드 중 오류: {str(e)}", LOG_ERROR)
            return []
    
    def get_all_purchase_products(self) -> Dict[str, List[Dict[str, Any]]]:
        """모든 발주프로덕트 데이터 반환"""
        return self.purchase_products_data
    
    def clear_purchase_products(self, purchase_code: str = None):
        """발주프로덕트 데이터 삭제
        
        Args:
            purchase_code: 특정 발주번호 (None이면 전체 삭제)
        """
        if purchase_code:
            if purchase_code in self.purchase_products_data:
                del self.purchase_products_data[purchase_code]
        else:
            self.purchase_products_data.clear()

    # FBO 발주 확인용 메서드들
    def load_purchase_confirms_from_api(self) -> bool:
        """FBO 발주 확인 데이터를 API에서 로드 (기존 메시지 상태 보존)"""
        try:
            # 먼저 기존 캐시된 데이터 로드 시도
            today = date.today().strftime('%y%m%d')
            cached_file_pattern = os.path.join(self.data_dir, f'fbo_po_confirm_{today}-*.json')
            cached_files = glob.glob(cached_file_pattern)
            
            existing_data_map = {}
            if cached_files:
                # 기존 캐시된 데이터를 ID로 매핑
                try:
                    cached_file = cached_files[0]  # 가장 첫 번째 파일 사용
                    with open(cached_file, 'r', encoding='utf-8') as f:
                        cached_data = json.load(f)
                    
                    for item in cached_data:
                        item_id = item.get('id')
                        if item_id:
                            existing_data_map[item_id] = {
                                'message_status': item.get('message_status', '대기중'),
                                'processed_at': item.get('processed_at')
                            }
                    
                    self.log(f"기존 FBO 발주 확인 캐시 데이터 {len(existing_data_map)}건을 로드했습니다.", LOG_INFO)
                except Exception as e:
                    self.log(f"기존 캐시 데이터 로드 실패: {str(e)}", LOG_WARNING)
            
            # API에서 새 데이터 가져오기
            api_service = ApiService()
            response = api_service.get_purchase_confirms()
            
            if response:
                purchase_confirms = []
                preserved_count = 0
                new_count = 0
                
                for item in response:
                    # status가 'requested'인 항목만 처리
                    if item.get('status') != 'requested':
                        continue
                    
                    # 기존 메시지 상태 보존
                    item_id = item.get('id')
                    if item_id in existing_data_map:
                        existing_info = existing_data_map[item_id]
                        item['message_status'] = existing_info['message_status']
                        item['processed_at'] = existing_info['processed_at']
                        preserved_count += 1
                    else:
                        # 새로운 항목은 기본값 설정
                        item['message_status'] = MessageStatus.PENDING.value
                        item['processed_at'] = None
                        new_count += 1
                    
                    purchase_confirm = PurchaseConfirm(
                        purchase_code=item.get("purchase_code", ""),
                        purchase_type=item.get("purchase_type", ""),
                        created_at=item.get("created_at", ""),
                        order_code=item.get("order_code", ""),
                        seller=item.get("store_name", ""),
                        in_charge=item.get("in_charge", ""),
                        quantity=str(item.get("quantity", "")),
                        price=str(item.get("price", "")),
                        price_changeable=item.get("price_changeable", ""),
                        delay_allowable=item.get("delay_allowable", ""),
                        status="requested",
                        payment_status=item.get("payment_status", ""),
                        internal_memo=item.get("internal_memo", ""),
                        message_status=item.get("message_status", MessageStatus.PENDING.value),
                        # processed_at은 기존 캐시된 값만 사용 (API에서 새로 설정하지 않음)
                        processed_at=self._safe_datetime_convert(item.get("processed_at")) if item.get("processed_at") else None
                    )
                    
                    # 같은 purchase_code를 가진 아이템들을 프로덕트로 그룹화
                    purchase_confirm.products = [
                        PurchaseProduct(**self._map_api_response_to_product_data(item))
                    ]
                    
                    purchase_confirms.append(purchase_confirm)
                
                # purchase_code별로 그룹화하여 중복 제거 및 프로덕트 병합
                grouped_confirms = {}
                for confirm in purchase_confirms:
                    if confirm.purchase_code in grouped_confirms:
                        # 기존 데이터에 프로덕트 추가
                        grouped_confirms[confirm.purchase_code].products.extend(confirm.products)
                    else:
                        grouped_confirms[confirm.purchase_code] = confirm
                
                self.data = list(grouped_confirms.values())
                self.filtered_data = self.data.copy()
                
                # 상태 보존 통계 출력
                if preserved_count > 0:
                    self.log(f"메시지 상태 보존: {preserved_count}건, 신규: {new_count}건", LOG_SUCCESS)
                else:
                    self.log(f"모든 항목이 신규: {new_count}건", LOG_INFO)
                
                self.log(f"{self.file_prefix} 발주 확인 데이터 {len(self.data)}건을 API에서 로드했습니다.", LOG_SUCCESS)
                self.data_loaded.emit(self.data)
                
                # 업데이트된 데이터를 캐시에 저장
                self.save_purchase_confirms()
                
                return True
            else:
                self.log("API에서 FBO 발주 확인 데이터를 가져올 수 없습니다.", LOG_ERROR)
                return False
                
        except Exception as e:
            self.log(f"{self.file_prefix} 발주 확인 API 로드 중 오류: {str(e)}", LOG_ERROR)
            self.error_occurred.emit(str(e))
            return False

    def _map_api_to_purchase_confirm(self, item: Dict[str, Any]) -> PurchaseConfirm:
        """API 응답을 PurchaseConfirm 객체로 매핑"""
        return PurchaseConfirm(
            purchase_code=item.get("purchase_code", ""),
            purchase_type=item.get("purchase_type", ""),
            created_at=item.get("created_at", ""),
            order_code=item.get("order_code", ""),
            seller=item.get("store_name", ""),
            in_charge=item.get("in_charge", ""),
            quantity=str(item.get("quantity", "")),
            price=str(item.get("price", "")),
            price_changeable=item.get("price_changeable", ""),
            delay_allowable=item.get("delay_allowable", ""),
            status=item.get("status", ""),
            payment_status=item.get("payment_status", ""),
            internal_memo=item.get("internal_memo", ""),
            message_status=item.get("message_status", MessageStatus.PENDING.value),
            # processed_at은 기존 캐시된 값만 사용 (API에서 새로 설정하지 않음)
            processed_at=self._safe_datetime_convert(item.get("processed_at")) if item.get("processed_at") else None
        )

    def save_purchase_confirms(self, data: List[PurchaseConfirm] = None) -> Optional[str]:
        """발주 확인 데이터를 flat product 구조로 파일로 저장"""
        try:
            if data is None:
                data = self.data

            # flat product 구조로 변환
            flat_products = []
            for confirm in data:
                for product in confirm.products:
                    row = {
                        "id": product.id,
                        "image_url": getattr(product, 'image_url', None),
                        "print_url": getattr(product, 'print_url', None),
                        "store_name": product.store_name,
                        "store_url": getattr(product, 'store_url', None),
                        "store_address": product.store_address,
                        "store_ddm_address": product.store_ddm_address,
                        "quality_code": getattr(product, 'quality_code', None),
                        "quality_name": product.quality_name,
                        "quality_url": getattr(product, 'quality_url', None),
                        "swatch_pickupable": getattr(product, 'swatch_pickupable', None),
                        "swatch_storage": getattr(product, 'swatch_storage', None),
                        "color_number": product.color_number,
                        "color_code": product.color_code,
                        "quantity": product.quantity,
                        "order_code": getattr(product, 'order_code', None),
                        "order_url": getattr(product, 'order_url', None),
                        "purchase_code": confirm.purchase_code,
                        "purchase_url": getattr(product, 'purchase_url', None),
                        "last_pickup_at": product.last_pickup_at,
                        "pickup_at": product.pickup_at,
                        "delivery_method": product.delivery_method,
                        "logistics_company": product.logistics_company,
                        "status": confirm.status,
                        "message_status": self._map_message_status_to_korean(confirm.message_status),
                        "processed_at": confirm.processed_at.isoformat() if confirm.processed_at and hasattr(confirm.processed_at, 'isoformat') else (str(confirm.processed_at) if confirm.processed_at else None),
                        "price": getattr(product, 'price', None),
                        "unit_price": getattr(product, 'unit_price', None),
                        "unit_price_origin": getattr(product, 'unit_price_origin', None),
                        "additional_info": getattr(product, 'additional_info', None),
                        "created_at": getattr(product, 'created_at', None),
                        "updated_at": getattr(product, 'updated_at', None),
                    }
                    flat_products.append(row)

            file_path = self._save_today_cache_file_custom("fbo_po_confirm", flat_products)
            if file_path:
                self.log(f"FBO 발주 확인 flat product 데이터를 저장했습니다: {file_path}", LOG_SUCCESS)
                return file_path
            else:
                self.log("FBO 발주 확인 flat product 데이터 저장 실패", LOG_ERROR)
                return None

        except Exception as e:
            self.log(f"FBO 발주 확인 flat product 데이터 저장 중 오류: {str(e)}", LOG_ERROR)
            return None

    def _save_today_cache_file_custom(self, prefix: str, data: List[Dict]) -> Optional[str]:
        """커스텀 프리픽스로 오늘 날짜 캐시 파일 저장 (기존 파일 업데이트 방식)"""
        try:
            from datetime import datetime
            import json
            
            today = datetime.now().strftime('%y%m%d')
            
            # 기존 오늘 날짜 파일이 있는지 확인
            existing_files = glob.glob(os.path.join(self.data_dir, f'{prefix}_{today}-*.json'))
            
            if existing_files:
                # 기존 파일이 있으면 가장 오래된 파일을 업데이트 (최초 파일 유지)
                file_path = min(existing_files, key=os.path.getctime)
                self.log(f"기존 {prefix} 파일을 업데이트합니다: {os.path.basename(file_path)}", LOG_INFO)
            else:
                # 기존 파일이 없으면 새로 생성
                timestamp = datetime.now().strftime('%H%M')
                filename = f'{prefix}_{today}-{timestamp}.json'
                file_path = os.path.join(self.data_dir, filename)
                self.log(f"새 {prefix} 파일을 생성합니다: {filename}", LOG_INFO)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
            
            return file_path
        except Exception as e:
            self.log(f"파일 저장 중 오류: {str(e)}", LOG_ERROR)
            return None

    def _map_message_status_to_korean(self, status: str) -> str:
        """메시지 상태를 한글로 매핑"""
        return MESSAGE_STATUS_LABELS.get(status, status) 