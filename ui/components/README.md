# SwatchOn 재사용 가능한 UI 컴포넌트

SwatchOn 채팅 애플리케이션의 FBO 출고 요청 기능을 모듈화하여 재사용 가능한 컴포넌트들을 생성했습니다. 이 컴포넌트들은 다른 기능들(스와치 발주, 발주 확인 요청 등)에서도 활용할 수 있습니다.

## 생성된 컴포넌트 목록

### 1. MessageManager (`message_manager.py`)
- **기능**: 메시지 생성, 미리보기, 전송, 중복 검증
- **재사용성**: 모든 주문 유형 및 작업 유형에서 사용 가능

#### 사용법
```python
from ui.components.message_manager import MessageManager
from core.types import OrderType, FboOperationType

# FBO 출고 요청용 메시지 매니저
message_manager = MessageManager(
    order_type=OrderType.FBO,
    operation_type=FboOperationType.SHIPMENT_REQUEST,
    log_function=self.log
)

# 메시지 미리보기 생성
selected_items = [...]  # 선택된 항목들 (딕셔너리 형태)
message_manager.generate_message_preview(selected_items)

# 메시지 전송
message_manager.send_messages(update_status_callback=self._update_status)
```

#### 다른 용도로 활용
```python
# FBO 발주 확인 요청
po_message_manager = MessageManager(
    OrderType.FBO, 
    FboOperationType.PO, 
    self.log
)

# SBO 스와치 발주
sbo_message_manager = MessageManager(
    OrderType.SBO, 
    SboOperationType.PO, 
    self.log
)
```

### 2. DataManager (`data_manager.py`)
- **기능**: API 연동, 데이터 로드/저장, 필터링, 상태 관리
- **재사용성**: 모든 주문 유형에서 사용 가능

#### 사용법
```python
from ui.components.data_manager import DataManager
from core.types import OrderType

# FBO용 데이터 매니저
data_manager = DataManager(
    order_type=OrderType.FBO,
    data_dir="ui/data",
    log_function=self.log
)

# API에서 데이터 로드
data_manager.load_data_from_api()

# 필터 적용
filtered_data = data_manager.apply_filters(
    search_text="판매자A",
    status_filter="pending"
)

# 상태 업데이트
data_manager.update_item_status([1, 2, 3], "sent", True)
```

### 3. StatisticsWidget (`statistics_widget.py`)
- **기능**: 상태별 통계 카드 표시, 클릭 이벤트
- **재사용성**: 모든 섹션에서 동일한 통계 UI 제공

#### 사용법
```python
from ui.components.statistics_widget import StatisticsWidget

# 통계 위젯 생성
stats_widget = StatisticsWidget()

# 통계 업데이트
stats = {
    'total': 100,
    'pending': 50,
    'sent': 30,
    'failed': 20
}
stats_widget.update_statistics(stats)

# 카드 클릭 이벤트 연결
stats_widget.card_clicked.connect(self._on_card_clicked)
```

#### 사용자 정의 카드 추가
```python
# 사용자 정의 통계 카드 추가
stats_widget.add_custom_card("urgent", "긴급", "error", 5)
```

### 4. FilterWidget (`filter_widget.py`)
- **기능**: 검색, 상태 필터, 사용자 정의 필터
- **재사용성**: 모든 섹션에서 동일한 필터링 UI 제공

#### 사용법
```python
from ui.components.filter_widget import FilterWidget

# 필터 위젯 생성
filter_widget = FilterWidget()

# 시그널 연결
filter_widget.search_changed.connect(self._on_search_changed)
filter_widget.filter_changed.connect(self._on_filter_changed)

# 사용자 정의 필터 추가
filter_widget.add_combo_filter(
    "delivery_method", 
    "배송방법", 
    [("모든 방법", "all"), ("동대문퀵", "quick"), ("판매자발송", "logistics")]
)
```

## 활용 예시

### FBO 발주 확인 요청 섹션에서 활용
```python
class PoSection(BaseSection):
    def __init__(self, parent=None):
        super().__init__("FBO 발주 확인 요청", parent)
        
        # 컴포넌트 재사용
        self.data_manager = DataManager(OrderType.FBO, "ui/data", self.log)
        self.message_manager = MessageManager(
            OrderType.FBO, 
            FboOperationType.PO, 
            self.log
        )
        self.statistics_widget = StatisticsWidget()
        self.filter_widget = FilterWidget()
```

### SBO 스와치 발주 섹션에서 활용
```python
class SboPoSection(BaseSection):
    def __init__(self, parent=None):
        super().__init__("SBO 스와치 발주", parent)
        
        # 컴포넌트 재사용 (주문 유형만 변경)
        self.data_manager = DataManager(OrderType.SBO, "ui/data", self.log)
        self.message_manager = MessageManager(
            OrderType.SBO, 
            SboOperationType.PO, 
            self.log
        )
        self.statistics_widget = StatisticsWidget()
        self.filter_widget = FilterWidget()
```

## 리팩토링 효과

### 기존 문제점
- `shipment_request_section.py`: 1100줄 이상의 방대한 코드
- 메시지 처리, 데이터 관리, UI 로직이 모두 한 파일에 집중
- 코드 중복 및 재사용의 어려움

### 리팩토링 후
- **코드 라인 수 감소**: 1100줄 → 약 300줄 (70% 감소)
- **모듈화**: 기능별로 독립된 컴포넌트 분리
- **재사용성**: 다른 섹션에서 동일한 컴포넌트 활용 가능
- **유지보수성**: 개별 컴포넌트 단위로 수정 가능
- **테스트 용이성**: 각 컴포넌트를 독립적으로 테스트 가능

## 주요 설계 원칙

### 1. 범용성
- `OrderType`과 `operation_type` 파라미터를 통해 다양한 용도로 활용
- 기존 서비스(`TemplateService`, `KakaoService` 등) 재활용

### 2. 시그널 기반 통신
- Qt의 시그널/슬롯 메커니즘을 활용한 느슨한 결합
- 컴포넌트 간 독립성 보장

### 3. 콜백 기반 확장성
- 섹션별 고유 로직은 콜백 함수로 분리
- 컴포넌트의 범용성 유지

### 4. 상태 관리 분리
- 데이터 상태는 `DataManager`에서 중앙 관리
- UI 상태와 데이터 상태의 명확한 분리

## 향후 확장 가능성

1. **추가 컴포넌트**: 테이블 위젯, 진행률 표시 위젯 등
2. **설정 관리**: 컴포넌트별 설정 저장/로드 기능
3. **애니메이션**: 상태 변경 시 부드러운 전환 효과
4. **플러그인 시스템**: 사용자 정의 컴포넌트 추가 가능
5. **테마 시스템**: 다양한 색상 테마 지원

이러한 컴포넌트 기반 설계를 통해 SwatchOn 애플리케이션의 확장성과 유지보수성을 크게 향상시킬 수 있습니다. 