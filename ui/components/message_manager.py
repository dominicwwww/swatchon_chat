"""
메시지 관리자 컴포넌트 - 재사용 가능한 메시지 처리 기능
"""
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
from PySide6.QtWidgets import QMessageBox
from PySide6.QtCore import QObject, Signal, QThread
import time
import traceback
import re

from core.types import OrderType, FboOperationType, SboOperationType, ShipmentStatus, MessageStatus
from services.template.template_service import TemplateService
from services.kakao.kakao_service import KakaoService
from services.address_book_service import AddressBookService
from core.constants import DELIVERY_METHODS, LOGISTICS_COMPANIES, API_FIELDS
from ui.components.log_widget import LOG_INFO, LOG_DEBUG, LOG_WARNING, LOG_ERROR, LOG_SUCCESS


class MessageSenderThread(QThread):
    """메시지 전송을 위한 워커 스레드"""
    finished = Signal(dict)  # 전송 완료 시그널
    
    def __init__(self, message_manager, update_status_callback):
        super().__init__()
        self.message_manager = message_manager
        self.update_status_callback = update_status_callback
    
    def run(self):
        """스레드 실행"""
        try:
            result = self.message_manager._send_messages_internal(self.update_status_callback)
            self.finished.emit(result)
        except Exception as e:
            print("\n=== QThread에서 예외 발생 ===")
            print("타입:", type(e))
            print("값:", e)
            traceback.print_exc()
            print("===========================\n")
            self.finished.emit({
                'success': False, 
                'error': str(e),
                'traceback': traceback.format_exc()
            })

class MessageManager(QObject):
    """
    메시지 관리자 - 여러 섹션에서 재사용 가능한 메시지 처리 기능
    
    기능:
    - 메시지 미리보기 생성
    - 메시지 전송
    - 중복 전송 검증
    - 상태 업데이트
    """
    
    # 시그널 정의
    message_preview_generated = Signal(dict)  # 미리보기 생성 완료 시그널
    message_sent = Signal(dict)  # 메시지 전송 완료 시그널
    status_updated = Signal(list, str, str)  # 상태 업데이트 시그널 (item_ids, status, processed_at)
    
    def __init__(self, order_type: OrderType, operation_type, log_function: Optional[Callable] = None):
        """
        초기화
        
        Args:
            order_type: 주문 유형 (FBO, SBO)
            operation_type: 작업 유형 (출고요청, 발주확인 등)
            log_function: 로그 함수
        """
        super().__init__()
        self.order_type = order_type
        self.operation_type = operation_type
        self.log_function = log_function or print
        
        # 서비스 인스턴스 생성
        self.template_service = TemplateService()
        self.kakao_service = KakaoService()
        self.address_book_service = AddressBookService()
        
        # 상태 관리
        self._message_preview_data = None
        self._is_sending = False
        self._emergency_stop = False
    
    def log(self, message: str, level: str = LOG_INFO):
        """로그 출력"""
        if self.log_function:
            for line in str(message).splitlines():
                if line.strip():
                    self.log_function(f"[LOG] {line}", level)
    
    def check_duplicate_sending(self, selected_items: List[Dict[str, Any]], 
                              all_data: List[Any]) -> Dict[str, Any]:
        """
        중복 전송 검증
        
        Args:
            selected_items: 선택된 항목들
            all_data: 전체 데이터
            
        Returns:
            Dict[str, Any]: 중복 검증 결과
        """
        try:
            # 선택된 항목들을 판매자별로 그룹핑
            seller_groups = {}
            for item in selected_items:
                seller_name = item.get("store_name", "알 수 없음")
                if seller_name not in seller_groups:
                    seller_groups[seller_name] = []
                seller_groups[seller_name].append(item)
            
            duplicates = {}
            has_duplicates = False
            
            # 각 판매자별로 이미 전송된 항목이 있는지 확인
            for seller_name in seller_groups.keys():
                # 해당 판매자의 모든 항목 조회
                seller_all_items = [item for item in all_data if item.store_name == seller_name]
                
                # 메시지 전송완료된 항목과 대기중인 항목 분류
                sent_items = [item for item in seller_all_items if getattr(item, 'message_status', '대기중') == MessageStatus.SENT.value]
                pending_items = [item for item in seller_all_items if getattr(item, 'message_status', '대기중') in [MessageStatus.PENDING.value, "대기중", ""]]
                
                # 이미 전송된 항목이 있는 경우
                if sent_items:
                    has_duplicates = True
                    duplicates[seller_name] = {
                        'sent_count': len(sent_items),
                        'pending_count': len(pending_items)
                    }
            
            return {
                'has_duplicates': has_duplicates,
                'duplicates': duplicates
            }
            
        except Exception as e:
            self.log(f"중복 전송 검증 중 오류: {str(e)}", LOG_ERROR)
            return {'has_duplicates': False, 'duplicates': {}}
    
    def format_order_details(self, items: List[Dict[str, Any]]) -> str:
        """
        주문 상세 정보 포맷팅
        
        Args:
            items: 주문 항목들
            
        Returns:
            str: 포맷팅된 주문 상세 정보
        """
        try:
            # 템플릿 로드
            template = self.template_service.load_template(self.order_type, self.operation_type)
            
            if not template:
                self.log(f"{self.order_type.value}/{self.operation_type.value} 템플릿을 찾을 수 없습니다.", LOG_ERROR)
                return "템플릿을 찾을 수 없습니다."
            
            order_details_format = template.get("order_details_format", "[{quality_name}] | #{color_number} | {quantity}yd | {pickup_at} | {delivery_method}-{logistics_company}")
            
            # 주문번호별로 그룹핑
            order_groups = {}
            for item in items:
                order_number = item.get("purchase_code", "")
                if order_number not in order_groups:
                    order_groups[order_number] = []
                order_groups[order_number].append(item)

            # 주문별 order_details 생성
            order_details_blocks = []
            for order_idx, (order_number, products) in enumerate(order_groups.items(), 1):
                # id와 purchase_code 기준 중복 제거된 상품 리스트 생성
                unique_products = []
                seen_identifiers = set()
                for data in products:
                    # id와 purchase_code 조합으로 고유성 확인
                    product_id = data.get("id", "")
                    purchase_code = data.get("purchase_code", "")
                    identifier = f"{product_id}_{purchase_code}"
                    
                    if identifier in seen_identifiers:
                        continue
                    seen_identifiers.add(identifier)
                    unique_products.append(data)
                    
                order_details_lines = []
                for prod_idx, data in enumerate(unique_products, 1):
                    # 데이터 복사 및 추가 정보 설정
                    processed_data = data.copy()
                    processed_data["order_index"] = order_idx
                    processed_data["total_orders"] = len(order_groups)
                    processed_data["product_index"] = prod_idx
                    processed_data["total_products"] = len(unique_products)
                    
                    # delivery_method와 logistics_company 치환
                    delivery_method = processed_data.get("delivery_method", "")
                    logistics_company = processed_data.get("logistics_company", "")
                    
                    # None 값을 문자열로 변환
                    if delivery_method is None:
                        delivery_method = "None"
                    if logistics_company is None:
                        logistics_company = "None"
                    
                    # pickup_at 날짜 형식 변환 (YYYY-MM-DDTHH:MM:SS+TZ -> YYYY-MM-DD)
                    pickup_at = processed_data.get("pickup_at", "")
                    if pickup_at and "T" in pickup_at:
                        pickup_at = pickup_at.split("T")[0]  # T 앞부분만 추출
                        processed_data["pickup_at"] = pickup_at
                    
                    processed_data["delivery_method"] = DELIVERY_METHODS.get(delivery_method, delivery_method)
                    processed_data["logistics_company"] = LOGISTICS_COMPANIES.get(logistics_company, logistics_company)
                    
                    # 템플릿 변수 치환
                    order_details_line = order_details_format
                    # API_FIELDS 매핑을 포함한 모든 변수 처리
                    all_variables = {**processed_data, **{k: processed_data.get(k, '') for k in API_FIELDS.values()}}
                    
                    for k, v in all_variables.items():
                        placeholder = f"{{{k}}}"
                        if placeholder in order_details_line:
                            order_details_line = order_details_line.replace(placeholder, str(v))
                    
                    order_details_lines.append(order_details_line)
                    
                # 주문별 블록 생성 (주문번호 + created_at + 상품 목록)
                if order_details_lines:
                    # created_at 정보를 발주번호 옆에 추가
                    created_at = unique_products[0].get("created_at", "") if unique_products else ""
                    if created_at:
                        # created_at 날짜 포맷팅 (YYYY-MM-DDTHH:MM:SS+TZ -> YYYY-MM-DD HH:MM)
                        if "T" in created_at:
                            date_part, time_part = created_at.split("T")
                            time_part = time_part.split("+")[0].split("Z")[0]  # 타임존 제거
                            if ":" in time_part:
                                hour_min = ":".join(time_part.split(":")[:2])  # HH:MM만 추출
                                created_at_formatted = f"{date_part} {hour_min}"
                            else:
                                created_at_formatted = date_part
                        else:
                            # T가 없는 경우 그대로 사용하되 길이 제한
                            created_at_formatted = created_at[:16] if len(created_at) >= 16 else created_at
                        
                        order_header = f"{order_idx}. {order_number} ({created_at_formatted} 주문)"
                    else:
                        order_header = f"{order_idx}. {order_number}"
                    
                    block = order_header + "\n" + "\n".join([f"    {prod_idx}) {line}" for prod_idx, line in enumerate(order_details_lines, 1)])
                else:
                    # 상품이 없는 경우에도 주문번호는 표시
                    block = f"{order_idx}. {order_number}\n    (상품 정보 없음)"
                
                order_details_blocks.append(block)

            final_result = "\n".join(order_details_blocks)
            return final_result
            
        except Exception as e:
            self.log(f"주문 상세 정보 포맷팅 실패: {str(e)}", LOG_ERROR)
            return f"주문 상세 정보 포맷팅 실패: {str(e)}"
    
    def clean_seller_name(self, name):
        if not name:
            return "알 수 없음"
        name = name.strip()
        name = re.sub(r'\s+', ' ', name)
        # 필요시 특수문자 제거(괄호, 한글, 영문, 숫자, 공백만 허용)
        # name = re.sub(r'[^\w\s가-힣()]', '', name)
        return name
    
    def generate_message_preview(self, selected_items: List[Dict[str, Any]]) -> bool:
        """
        메시지 미리보기 생성
        
        Args:
            selected_items: 선택된 항목들
            
        Returns:
            bool: 성공 여부
        """
        try:
            self.log(f"선택된 {len(selected_items)}개 항목으로 메시지 미리보기를 생성합니다.", LOG_INFO)
            
            # 판매자별로 그룹핑 (store_name strip 적용)
            seller_groups = {}
            for item in selected_items:
                seller_name = self.clean_seller_name(item.get("store_name", "알 수 없음"))
                if seller_name not in seller_groups:
                    seller_groups[seller_name] = []
                seller_groups[seller_name].append(item)
            
            # 미리보기용으로 3개의 판매자만 선택
            import random
            preview_sellers = random.sample(list(seller_groups.items()), min(3, len(seller_groups)))
            
            self.log(f"=== 메시지 미리보기 ({len(preview_sellers)}명의 판매자) ===", LOG_INFO)
            
            # 미리보기 데이터 저장 (모든 판매자 데이터 저장)
            self._message_preview_data = {}
            
            # 각 판매자별로 메시지 생성
            for seller_name, seller_items in seller_groups.items():
                try:
                    # seller_items를 깊은 복사로 분리
                    seller_items_copy = [dict(item) for item in seller_items]
                    # 주문 상세 정보 포맷팅
                    order_details = self.format_order_details(seller_items_copy)
                
                    # 메시지 데이터 준비
                    message_data = {
                        "store_name": seller_name,
                        "order_details": order_details,
                        "pickup_at": seller_items_copy[0].get("pickup_at", ""),
                        "total_orders": len(set(item.get("purchase_code", "") for item in seller_items_copy)),
                        "total_products": len(seller_items_copy),
                        "items": seller_items_copy  # 개별 아이템 리스트 추가
                    }
                    
                    # 기본 API 필드 추가
                    for field_key, field_name in API_FIELDS.items():
                        if field_name not in message_data:
                            message_data[field_name] = seller_items_copy[0].get(field_name, "")
                    
                    # quantity를 int로 변환
                    if "quantity" in message_data:
                        try:
                            message_data["quantity"] = int(float(message_data["quantity"]))
                        except (ValueError, TypeError):
                            pass
                    
                    # 조건부 템플릿 적용
                    template = self.template_service.load_template(self.order_type, self.operation_type)
                    message = None
                    if template and template.get("conditions"):
                        for condition in template.get("conditions", []):
                            if self.template_service.evaluate_condition(message_data, condition):
                                # 조건이 만족되면 해당 템플릿 사용
                                message = condition.get("template", "")
                                if message:
                                    # 템플릿 변수 치환
                                    for k, v in message_data.items():
                                        message = message.replace(f"{{{k}}}", str(v) if v is not None else "")
                                    break
                    if not message:
                        # 조건이 만족되지 않거나 조건부 템플릿이 없으면 기본 템플릿 사용
                        message = self.template_service.render_message(
                            self.order_type,
                            self.operation_type,
                            message_data
                        )
                
                    if message:
                        # 주소록에서 실제 채팅방 이름 조회 (strip 적용)
                        chat_room_name = self.address_book_service.get_chat_room_name(seller_name)
                        
                        if not chat_room_name:
                            self.log(f"⚠️ [경고] '{seller_name}'의 채팅방을 주소록에서 찾을 수 없습니다.", LOG_WARNING)
                            continue
                        
                        # 미리보기 데이터에 저장 (seller_items_copy로 저장)
                        self._message_preview_data[seller_name] = {
                            'message': message,
                            'chat_room_name': chat_room_name,
                            'items': seller_items_copy
                        }
                        
                        # 미리보기용으로 선택된 판매자만 로그 출력
                        if (seller_name, seller_items) in preview_sellers:
                            self.log(f"--- [{seller_name}] → [{chat_room_name}] ---", LOG_INFO)
                            self.log(f"{message}", LOG_INFO)
                        
                    else:
                        self.log(f"{seller_name} 판매자용 메시지 생성에 실패했습니다.", LOG_ERROR)
                        
                except Exception as e:
                    self.log(f"{seller_name} 판매자 메시지 처리 중 오류: {str(e)}", LOG_ERROR)
                    continue
            
            if self._message_preview_data:
                self.log("=== 미리보기 완료 ===", LOG_SUCCESS)
                self.message_preview_generated.emit(self._message_preview_data)
                return True
            else:
                self.log("생성된 메시지가 없습니다.", LOG_WARNING)
                return False
            
        except Exception as e:
            self.log(f"메시지 미리보기 생성 중 오류: {str(e)}", LOG_ERROR)
            return False
    
    def send_messages(self, update_status_callback: Optional[Callable] = None) -> None:
        """
        실제 메시지 전송 (비동기)
        
        Args:
            update_status_callback: 상태 업데이트 콜백 함수
        """
        if not self._message_preview_data:
            self.log("전송할 메시지 데이터가 없습니다. 먼저 미리보기를 생성해주세요.", LOG_WARNING)
            return
        
        try:
            self._is_sending = True
            self._emergency_stop = False
            
            # 워커 스레드 생성 및 시작
            self.sender_thread = MessageSenderThread(self, update_status_callback)
            self.sender_thread.finished.connect(self._on_send_finished)
            self.sender_thread.start()
            
        except Exception as e:
            self.log(f"메시지 전송 시작 중 오류: {str(e)}", LOG_ERROR)
            self._is_sending = False
    
    def _on_send_finished(self, result: Dict[str, Any]):
        """전송 완료 처리"""
        self._is_sending = False
        self.message_sent.emit(result)
    
    def _send_messages_internal(self, update_status_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        실제 메시지 전송 로직 (내부용)
        
        Args:
            update_status_callback: 상태 업데이트 콜백 함수
            
        Returns:
            Dict[str, Any]: 전송 결과
        """
        try:
            self.log(f"=== 메시지 전송 시작 ({len(self._message_preview_data)}명의 판매자) ===", LOG_INFO)
            
            # 전체 판매자 목록 로그
            self.log("\n전체 전송 예정 판매자 목록:", LOG_INFO)
            for idx, seller in enumerate(self._message_preview_data.keys(), 1):
                self.log(f"{idx}. {seller}", LOG_INFO)
            
            success_count = 0
            fail_count = 0
            sent_item_ids = []  # 전송 성공한 항목들의 ID 저장
            cancelled_item_ids = []
            
            # 판매자 목록을 리스트로 변환
            sellers = list(self._message_preview_data.keys())
            
            for idx, seller_name in enumerate(sellers):
                data = self._message_preview_data[seller_name]
                
                # 긴급 정지 확인
                if self._emergency_stop:
                    self.log("⚠️ 긴급 정지가 요청되었습니다. 전송을 중단합니다.", LOG_WARNING)
                    # 남은 항목들을 취소 상태로 설정
                    for remaining_seller, remaining_data in self._message_preview_data.items():
                        if remaining_seller not in sellers[:idx]:
                            for item in remaining_data['items']:
                                item_id = item.get('id')
                                if item_id:
                                    cancelled_item_ids.append(item_id)
                    break

                try:
                    chat_room_name = data.get('chat_room_name')
                    message = data.get('message')
                    seller_items = data.get('items', [])

                    # === 현재 판매자 정보 로그 ===
                    self.log(f"\n[전송 예정] 판매자: {seller_name}", LOG_INFO)
                    self.log(f"채팅방 이름: {chat_room_name if chat_room_name else 'N/A'}", LOG_INFO)
                    self.log(f"메시지 길이: {len(message) if message else 0}자", LOG_INFO)
                    self.log(f"전송할 항목 수: {len(seller_items)}개", LOG_INFO)
                    
                    # === 다음 판매자 정보 미리 로그 ===
                    if idx + 1 < len(sellers):
                        next_seller = sellers[idx + 1]
                        next_data = self._message_preview_data[next_seller]
                        self.log(f"\n다음 전송 예정 판매자: {next_seller}", LOG_INFO)
                        self.log(f"채팅방 이름: {next_data.get('chat_room_name', 'N/A')}", LOG_INFO)
                        self.log(f"메시지 길이: {len(next_data.get('message', ''))}자", LOG_INFO)
                        self.log(f"전송할 항목 수: {len(next_data.get('items', []))}개", LOG_INFO)
                    # === END ===

                    if not chat_room_name:
                        self.log(f"⚠️ [경고] '{seller_name}'의 채팅방을 주소록에서 찾을 수 없습니다. 해당 판매자는 건너뜁니다.", LOG_WARNING)
                        fail_count += 1
                        failed_item_ids = [item.get('id') for item in seller_items if item.get('id')]
                        if update_status_callback:
                            try:
                                update_status_callback(failed_item_ids, MessageStatus.FAILED.value)
                            except Exception as callback_error:
                                print(f"상태 업데이트 콜백 오류: {str(callback_error)}")
                                self.log(f"상태 업데이트 콜백 오류: {str(callback_error)}", LOG_ERROR)
                        continue
                    if not message:
                        self.log(f"⚠️ [경고] '{seller_name}'의 메시지 내용이 없습니다. 해당 판매자는 건너뜁니다.", LOG_WARNING)
                        fail_count += 1
                        failed_item_ids = [item.get('id') for item in seller_items if item.get('id')]
                        if update_status_callback:
                            try:
                                update_status_callback(failed_item_ids, MessageStatus.FAILED.value)
                            except Exception as callback_error:
                                print(f"상태 업데이트 콜백 오류: {str(callback_error)}")
                                self.log(f"상태 업데이트 콜백 오류: {str(callback_error)}", LOG_ERROR)
                        continue
                    if not seller_items:
                        self.log(f"⚠️ [경고] '{seller_name}'의 전송할 항목이 없습니다. 해당 판매자는 건너뜁니다.", LOG_WARNING)
                        fail_count += 1
                        continue

                    # 해당 판매자의 항목들을 "전송중" 상태로 업데이트
                    seller_item_ids = [item.get('id') for item in seller_items if item.get('id')]
                    if update_status_callback:
                        try:
                            update_status_callback(seller_item_ids, MessageStatus.SENDING.value)
                        except Exception as callback_error:
                            print(f"상태 업데이트 콜백 오류: {str(callback_error)}")
                            self.log(f"상태 업데이트 콜백 오류: {str(callback_error)}", LOG_ERROR)

                    self.log(f"[{seller_name}] → [{chat_room_name}] 메시지 전송 중...", LOG_INFO)
                    
                    try:
                        # 카카오톡으로 실제 메시지 전송
                        success = self.kakao_service.send_message_to_seller(chat_room_name, message, log_function=self.log)
                    except Exception as send_exc:
                        error_msg = f"카카오톡 메시지 전송 중 예외 발생:\n{str(send_exc)}\n{traceback.format_exc()}"
                        print(error_msg)  # 터미널에 전체 스택트레이스 출력
                        self.log(error_msg, LOG_ERROR)
                        fail_count += 1
                        failed_item_ids = [item.get('id') for item in seller_items if item.get('id')]
                        if update_status_callback:
                            try:
                                update_status_callback(failed_item_ids, MessageStatus.FAILED.value)
                            except Exception as callback_error:
                                print(f"상태 업데이트 콜백 오류: {str(callback_error)}")
                                self.log(f"상태 업데이트 콜백 오류: {str(callback_error)}", LOG_ERROR)
                        continue  # 예외 발생 시에도 다음 판매자 계속 진행
                    else:
                        if success:
                            success_count += 1
                            for item in seller_items:
                                item_id = item.get('id')
                                if item_id:
                                    sent_item_ids.append(item_id)
                            if update_status_callback:
                                try:
                                    update_status_callback(seller_item_ids, MessageStatus.SENT.value, True)
                                except Exception as callback_error:
                                    print(f"상태 업데이트 콜백 오류: {str(callback_error)}")
                                    self.log(f"상태 업데이트 콜백 오류: {str(callback_error)}", LOG_ERROR)
                        else:
                            self.log(f"❌ {seller_name}({chat_room_name}) 메시지 전송 실패", LOG_ERROR)
                            fail_count += 1
                            failed_item_ids = [item.get('id') for item in seller_items if item.get('id')]
                            if update_status_callback:
                                try:
                                    update_status_callback(failed_item_ids, MessageStatus.FAILED.value)
                                except Exception as callback_error:
                                    print(f"상태 업데이트 콜백 오류: {str(callback_error)}")
                                    self.log(f"상태 업데이트 콜백 오류: {str(callback_error)}", LOG_ERROR)

                except Exception as e:
                    error_msg = f"❌ {seller_name} 메시지 전송 실패(예외):\n{str(e)}\n{traceback.format_exc()}"
                    print(error_msg)  # 터미널에 전체 스택트레이스 출력
                    self.log(error_msg, LOG_ERROR)
                    fail_count += 1
                    if 'seller_items' in locals():
                        failed_item_ids = [item.get('id') for item in seller_items if item.get('id')]
                        if update_status_callback:
                            try:
                                update_status_callback(failed_item_ids, MessageStatus.FAILED.value)
                            except Exception as callback_error:
                                print(f"상태 업데이트 콜백 오류: {str(callback_error)}")
                                self.log(f"상태 업데이트 콜백 오류: {str(callback_error)}", LOG_ERROR)
                    continue  # 예외 발생 시에도 다음 판매자 계속 진행

            # 취소된 항목들의 상태를 "취소됨"으로 업데이트
            if cancelled_item_ids and update_status_callback:
                try:
                    update_status_callback(cancelled_item_ids, MessageStatus.CANCELLED.value)
                except Exception as callback_error:
                    print(f"상태 업데이트 콜백 오류: {str(callback_error)}")
                    self.log(f"상태 업데이트 콜백 오류: {str(callback_error)}", LOG_ERROR)

            # 전송 결과 요약
            self.log(f"=== 전송 완료 ===", LOG_INFO)
            if self._emergency_stop:
                self.log(f"성공: {success_count}건, 실패: {fail_count}건, 취소: {len(cancelled_item_ids)}건", LOG_INFO)
            else:
                self.log(f"성공: {success_count}건, 실패: {fail_count}건", LOG_INFO)

            return {
                'success': True,
                'success_count': success_count,
                'fail_count': fail_count,
                'cancelled_count': len(cancelled_item_ids),
                'sent_item_ids': sent_item_ids,
                'emergency_stop': self._emergency_stop
            }

        except Exception as e:
            error_msg = f"메시지 전송 중 치명적 오류:\n{str(e)}\n{traceback.format_exc()}"
            print(error_msg)  # 터미널에 전체 스택트레이스 출력
            self.log(error_msg, LOG_ERROR)
            # 예외 발생 시에도 실패로 결과 반환
            return {'success': False, 'error': str(e)}
    
    def emergency_stop(self):
        """긴급 정지 요청"""
        if self._is_sending:
            self._emergency_stop = True
            self.log("🛑 긴급 정지가 요청되었습니다.", LOG_WARNING)
    
    def get_preview_data(self) -> Optional[Dict[str, Any]]:
        """미리보기 데이터 반환"""
        return self._message_preview_data
    
    def clear_preview_data(self):
        """미리보기 데이터 초기화"""
        self._message_preview_data = None
    
    def is_sending(self) -> bool:
        """전송 중 여부 확인"""
        return self._is_sending 