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
from core.schemas import PurchaseProduct
from ui.components.log_widget import LOG_INFO, LOG_DEBUG, LOG_WARNING, LOG_ERROR, LOG_SUCCESS


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
        
        # 데이터 디렉토리 설정 - 루트의 data 디렉토리 사용
        if data_dir is None:
            # 프로젝트 루트의 data 디렉토리
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            self.data_dir = os.path.join(project_root, 'data', 'api_cache')
        else:
            self.data_dir = data_dir
        
        # 디렉토리가 없으면 생성
        os.makedirs(self.data_dir, exist_ok=True)
        
        self.log_function = log_function or print
        
        # 서비스 인스턴스
        self.api_service = ApiService()
        
        # 데이터 저장소
        self.all_data: List[PurchaseProduct] = []
        self.filtered_data: List[PurchaseProduct] = []
        
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
                # 캐시된 데이터를 로드하되, 메시지 상태는 유지
                return self._load_cached_data_with_status_preservation(cached_file)
            
            self.log(f"{self.order_type.value} 데이터를 API에서 새로고침합니다.", LOG_INFO)
            
            # API 호출
            items = self.api_service.get_purchase_products()
            if not items:
                self.log("API에서 데이터를 받아오지 못했습니다.", LOG_WARNING)
                return False
            
            self.log(f"API에서 총 {len(items)}건의 데이터를 가져왔습니다.", LOG_INFO)
            
            # 데이터 변환 및 오늘 날짜까지 필터링
            purchase_products = []
            today_date = date.today()
            
            for item in items:
                try:
                    product_data = self._map_api_response_to_product_data(item)
                    
                    # pickup_at이 오늘 날짜까지인 데이터만 필터링
                    pickup_date = product_data['pickup_at']
                    if isinstance(pickup_date, datetime):
                        pickup_date = pickup_date.date()
                    elif isinstance(pickup_date, str):
                        try:
                            pickup_date = datetime.strptime(pickup_date, '%Y-%m-%d').date()
                        except ValueError:
                            continue
                    
                    if pickup_date <= today_date:
                        product = PurchaseProduct(**product_data)
                        purchase_products.append(product)
                    
                except Exception as e:
                    self.log(f"데이터 변환 실패: {str(e)}", LOG_WARNING)
                    continue
            
            self.log(f"오늘 날짜까지의 데이터 {len(purchase_products)}건을 필터링했습니다.", LOG_INFO)
            
            # 기존 메시지 상태 보존
            purchase_products = self._preserve_existing_message_status(purchase_products)
            
            # 데이터 저장
            self.all_data = purchase_products
            self.filtered_data = self.all_data.copy()
            self.current_data_date = today
            
            # 오늘 날짜로 캐시 파일 저장
            self._save_today_cache_file()
            
            # 시그널 발생
            self.data_loaded.emit(self.all_data)
            
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
        """오늘 날짜로 캐시 파일 저장"""
        try:
            today = date.today().strftime('%y%m%d')
            timestamp = datetime.now().strftime('%H%M')
            filename = f'shipment_requests_{today}-{timestamp}.json'
            file_path = os.path.join(self.data_dir, filename)
            
            # 기존 오늘 날짜 파일들 삭제 (가장 최신만 유지)
            existing_files = glob.glob(os.path.join(self.data_dir, f'shipment_requests_{today}-*.json'))
            for old_file in existing_files:
                try:
                    os.remove(old_file)
                except:
                    pass
            
            # PurchaseProduct 객체를 딕셔너리로 변환
            data_dicts = []
            for item in self.all_data:
                item_dict = self._purchase_product_to_dict(item)
                data_dicts.append(item_dict)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data_dicts, f, ensure_ascii=False, indent=2)
            
            self.log(f"오늘 날짜 캐시 파일을 저장했습니다: {filename}", LOG_SUCCESS)
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
            self.all_data = purchase_products
            self.filtered_data = self.all_data.copy()
            self.current_data_date = date.today().strftime('%y%m%d')
            
            # 시그널 발생
            self.data_loaded.emit(self.all_data)
            
            self.log(f"캐시된 데이터를 로드했습니다: {len(purchase_products)}건", LOG_SUCCESS)
            return True
            
        except Exception as e:
            self.log(f"캐시 데이터 로드 중 오류: {str(e)}", LOG_ERROR)
            return False
    
    def _preserve_existing_message_status(self, new_data: List[PurchaseProduct]) -> List[PurchaseProduct]:
        """기존 데이터의 메시지 상태와 처리 시각을 새 데이터에 적용"""
        if not self.all_data:
            return new_data
        
        # 기존 데이터를 ID로 매핑
        existing_status_map = {}
        for item in self.all_data:
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
    
    def _map_api_response_to_product_data(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        API 응답을 PurchaseProduct 데이터로 매핑
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
            'delivery_method': item.get('delivery_method', self._map_delivery_method(item.get('발주배송수단', ''))),
            'logistics_company': item.get('logistics_company', self._map_logistics_company(item.get('판매자발송수단', ''))),
            'status': item.get('status', item.get('발주상태', ''))
        }
        
        # 숫자 필드 변환
        product_data['color_number'] = self._safe_int_convert(product_data['color_number'])
        product_data['quantity'] = self._safe_int_convert(product_data['quantity'])
        
        # 날짜 필드 처리
        product_data['pickup_at'] = self._safe_datetime_convert(product_data['pickup_at'])
        
        # 기본 상태 설정
        if not product_data['status']:
            product_data['status'] = ""
        
        # 메시지 상태 - 기존 값이 있으면 사용, 없으면 기본값
        existing_message_status = item.get('message_status', item.get('메시지상태', ''))
        if existing_message_status and existing_message_status != '대기중':
            product_data['message_status'] = existing_message_status
        else:
            product_data['message_status'] = ShipmentStatus.PENDING.value
        
        # 처리 시각 - 기존 값이 있으면 사용
        existing_processed_at = item.get('processed_at', item.get('처리시각', None))
        if existing_processed_at:
            product_data['processed_at'] = self._safe_datetime_convert(existing_processed_at)
        else:
            product_data['processed_at'] = None
        
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
    
    def _map_delivery_method(self, original_value: str) -> str:
        """배송방법 매핑"""
        if not original_value:
            return ""
        
        mapping = {
            "동대문퀵": "quick",
            "동대문 픽업": "quick",
            "판매자발송": "logistics",
            "판매자 발송": "logistics"
        }
        
        return mapping.get(original_value, original_value.lower())
    
    def _map_logistics_company(self, original_value: str) -> str:
        """물류회사 매핑"""
        if not original_value or original_value == "-":
            return None
        
        mapping = {
            "경기택배": "kk",
            "일신택배": "is", 
            "경동택배": "kd",
            "퀵서비스": "quick_truck"
        }
        
        return mapping.get(original_value, original_value.lower())
    
    def save_data(self, data: List[PurchaseProduct] = None) -> Optional[str]:
        """
        데이터를 JSON 파일로 저장 (현재 날짜 캐시 파일 업데이트)
        
        Args:
            data: 저장할 데이터 (None이면 self.all_data 사용)
            
        Returns:
            Optional[str]: 저장된 파일 경로
        """
        try:
            if data is None:
                data = self.all_data
            
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
            'processed_at': item.processed_at.isoformat() if item.processed_at and hasattr(item.processed_at, 'isoformat') else (str(item.processed_at) if item.processed_at else None)
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
            filtered_data = self.all_data.copy()
            
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
        if not self.all_data:
            return {
                'total': '0',
                'pending': '0',
                'sending': '0',
                'sent': '0',
                'failed': '0',
                'cancelled': '0'
            }
        stats = {
            'total': len(self.all_data),
            'pending': len([item for item in self.all_data if getattr(item, 'message_status', '대기중') in [ShipmentStatus.PENDING.value, "대기중", ""]]),
            'sending': len([item for item in self.all_data if getattr(item, 'message_status', '대기중') == ShipmentStatus.SENDING.value]),
            'sent': len([item for item in self.all_data if getattr(item, 'message_status', '대기중') == ShipmentStatus.SENT.value]),
            'failed': len([item for item in self.all_data if getattr(item, 'message_status', '대기중') == ShipmentStatus.FAILED.value]),
            'cancelled': len([item for item in self.all_data if getattr(item, 'message_status', '대기중') == ShipmentStatus.CANCELLED.value])
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
            
            # all_data에서 업데이트
            for item in self.all_data:
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
        return self.all_data
    
    def get_filtered_data(self) -> List[PurchaseProduct]:
        """필터링된 데이터 반환"""
        return self.filtered_data
    
    def clear_data(self):
        """데이터 초기화"""
        self.all_data = []
        self.filtered_data = []
        self.current_search_text = ""
        self.current_status_filter = "all" 