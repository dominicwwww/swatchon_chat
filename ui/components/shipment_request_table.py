"""
FBO 출고 요청 테이블 컴포넌트
"""
from typing import List, Dict, Any
from PySide6.QtWidgets import (
    QTableWidget, QTableWidgetItem, QHeaderView, QWidget, QHBoxLayout,
    QCheckBox, QLabel, QVBoxLayout, QComboBox, QPushButton, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPixmap

from ui.theme import get_theme
from ui.components.log_widget import LOG_INFO, LOG_WARNING, LOG_ERROR

class ShipmentRequestTable(QTableWidget):
    """FBO 출고 요청 테이블 컴포넌트"""
    
    # 시그널 정의
    selection_changed = Signal(list)  # 선택된 항목 변경 시그널
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.load_photo = False  # 사진 로드 여부 (기본값: 비활성화)
        self.sort_priority = ["판매자", "발주수량", "발주배송수단"]  # 기본 정렬 우선순위
        
        # 메인 레이아웃 설정
        self.main_widget = QWidget()
        self.main_layout = QVBoxLayout(self.main_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        self._init_ui()
        self.setup_table()
        
        # 테이블을 메인 레이아웃에 추가
        self.main_layout.addWidget(self)
        
    def _init_ui(self):
        """상단 UI 초기화"""
        self.top_widget = QWidget()
        self.top_layout = QHBoxLayout(self.top_widget)
        self.top_layout.setContentsMargins(0, 0, 0, 8)  # 하단 여백 추가
        
        # 사진 로드 체크박스
        self.photo_checkbox = QCheckBox("사진 로드")
        self.photo_checkbox.setChecked(False)  # 초기값: 비활성화
        self.photo_checkbox.stateChanged.connect(self._on_photo_checkbox_changed)
        self.top_layout.addWidget(self.photo_checkbox)
        
        # 정렬 구분선
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setFrameShadow(QFrame.Sunken)
        self.top_layout.addWidget(separator)
        
        # 다중 정렬 콤보박스
        self.sort_combos = []
        sort_labels = ["1순위", "2순위", "3순위"]
        sort_options = [
            "판매자", "발주수량", "발주번호", "주문번호", 
            "최종출고일자", "발주출고예상일자", "발주배송수단", "판매자발송수단"
        ]
        
        for i, label in enumerate(sort_labels):
            # 레이블 추가
            label_widget = QLabel(label)
            self.top_layout.addWidget(label_widget)
            
            # 콤보박스 추가
            combo = QComboBox()
            combo.addItem("선택 안함", None)  # 기본값
            for option in sort_options:
                combo.addItem(option, option)  # 표시 텍스트와 데이터를 동일하게 설정
            combo.setCurrentIndex(0)  # 기본값 선택
            combo.currentIndexChanged.connect(self._on_sort_combo_changed)
            self.top_layout.addWidget(combo)
            self.sort_combos.append(combo)
            
        # 정렬 버튼
        self.sort_button = QPushButton("정렬")
        self.sort_button.clicked.connect(self._on_sort_button_clicked)
        print("정렬 버튼 클릭 이벤트 연결됨")
        self.top_layout.addWidget(self.sort_button)
        
        # 레이아웃 정렬
        self.top_layout.addStretch()
        
        # 상단 위젯을 메인 레이아웃에 추가
        self.main_layout.addWidget(self.top_widget)
        
    def _on_photo_checkbox_changed(self, state):
        """사진 로드 체크박스 상태 변경"""
        self.load_photo = (state == Qt.Checked)
        # 현재 데이터로 테이블 업데이트
        if hasattr(self, '_current_data'):
            self.update_data(self._current_data)
            
    def _on_sort_combo_changed(self):
        """정렬 콤보박스 변경 이벤트"""
        # 중복 선택 방지
        selected_values = []
        for combo in self.sort_combos:
            current_value = combo.currentData()
            print(f"콤보박스 값 변경: {current_value}")  # 디버깅 로그
            if current_value and current_value in selected_values:
                # 이전에 선택된 값이면 선택 해제
                combo.setCurrentIndex(0)
            elif current_value:
                selected_values.append(current_value)
                
    def _on_sort_button_clicked(self):
        """정렬 버튼 클릭 이벤트"""
        print("정렬 버튼 클릭됨")
        
        if not hasattr(self, '_current_data'):
            print("정렬할 데이터가 없습니다.")
            return
            
        # 선택된 정렬 기준 수집
        sort_criteria = []
        for i, combo in enumerate(self.sort_combos):
            value = combo.currentData()
            print(f"콤보박스 {i+1} 현재 값: {value}")
            if value:
                sort_criteria.append(value)
                print(f"{i+1}순위 정렬 기준: {value}")
                
        if not sort_criteria:
            print("선택된 정렬 기준이 없습니다.")
            return
            
        print(f"정렬 시작: {len(self._current_data)}개 데이터")
        
        # 데이터 정렬
        sorted_data = self._current_data.copy()
        
        # 다중 정렬을 위한 키 함수
        def get_sort_key(item):
            key_values = []
            for criterion in sort_criteria:
                value = item.get(criterion, "")
                # 날짜 형식 처리
                if criterion == "발주출고예상일자" or criterion == "최종출고일자":
                    try:
                        # 날짜 형식이 "YYYY-MM-DD"인 경우
                        from datetime import datetime
                        value = datetime.strptime(str(value), "%Y-%m-%d")
                    except:
                        value = str(value)
                # 발주수량 숫자 처리
                elif criterion == "발주수량":
                    try:
                        value = int(str(value).replace(',', ''))  # 쉼표 제거 후 정수 변환
                    except:
                        value = 0  # 변환 실패 시 0으로 처리
                else:
                    value = str(value)
                key_values.append(value)
            return tuple(key_values)
            
        # 정렬 실행
        sorted_data.sort(key=get_sort_key)
        print("정렬 완료")
            
        # 정렬된 데이터로 테이블 업데이트
        self._current_data = sorted_data
        self.update_data(sorted_data)
        
        # 정렬 완료 메시지
        sort_message = " → ".join(sort_criteria)
        print(f"정렬 완료: {sort_message}")
        
    def setup_table(self):
        """테이블 초기 설정"""
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setSelectionMode(QTableWidget.SingleSelection)
        self.setEditTriggers(QTableWidget.NoEditTriggers)
        self.setSortingEnabled(True)  # 헤더 클릭 정렬 활성화
        
        # 컬럼 정의
        self.setColumnCount(19)
        self.setHorizontalHeaderLabels([
            "", "사진", "ID", "판매자", "판매자 동대문주소", "아이템", "스와치 보관함", 
            "컬러순서", "컬러코드", "판매방식", "발주수량", "발주번호", "주문번호", 
            "최종출고일자", "발주출고예상일자", "발주배송수단", "판매자발송수단", 
            "발주상태", "메시지상태"
        ])
        
        # 컬럼 너비 설정
        header = self.horizontalHeader()
        for i in range(19):
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
            
        # 특정 컬럼 숨김
        self.setColumnHidden(9, True)   # 판매방식
        self.setColumnHidden(17, True)  # 발주상태
        
        # 정렬 가능한 컬럼 설정 (선택과 사진 컬럼 제외)
        self.sortable_columns = {
            2: "ID", 3: "판매자", 5: "아이템", 11: "발주번호", 
            12: "주문번호", 14: "발주출고예상일자"
        }
        
        # 헤더 클릭 이벤트 연결
        self.horizontalHeader().sectionClicked.connect(self._on_header_clicked)
        
        # 선택 컬럼 헤더에 체크박스 추가
        self.header_checkbox = QCheckBox()
        self.header_checkbox.stateChanged.connect(self._on_header_checkbox_changed)
        
        # 헤더 아이템 생성 및 체크박스 설정
        header_item = QTableWidgetItem()
        header_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
        header_item.setCheckState(Qt.Unchecked)
        self.setHorizontalHeaderItem(0, header_item)
        
        # 헤더 아이템 클릭 이벤트 처리
        self.horizontalHeader().sectionClicked.connect(self._on_header_section_clicked)
        
    def _on_header_section_clicked(self, column):
        """헤더 섹션 클릭 처리"""
        if column == 0:  # 선택 컬럼
            header_item = self.horizontalHeaderItem(0)
            if header_item:
                # 현재 상태의 반대로 변경
                new_state = Qt.Unchecked if header_item.checkState() == Qt.Checked else Qt.Checked
                header_item.setCheckState(new_state)
                # 모든 행의 체크박스 상태 변경
                for row in range(self.rowCount()):
                    checkbox = self.cellWidget(row, 0).findChild(QCheckBox)
                    if checkbox:
                        checkbox.setChecked(new_state == Qt.Checked)
                        
    def _on_header_checkbox_changed(self, state):
        """헤더 체크박스 상태 변경 처리"""
        for row in range(self.rowCount()):
            checkbox = self.cellWidget(row, 0).findChild(QCheckBox)
            if checkbox:
                checkbox.setChecked(state == Qt.Checked)
                
    def _on_header_clicked(self, column):
        """헤더 클릭 시 정렬 처리"""
        # 선택(0)과 사진(1) 컬럼은 정렬 제외
        if column in [0, 1] or column not in self.sortable_columns:
            return
            
        # 현재 정렬 방향 확인
        current_order = self.horizontalHeader().sortIndicatorOrder()
        new_order = Qt.DescendingOrder if current_order == Qt.AscendingOrder else Qt.AscendingOrder
        
        # 데이터 정렬
        self.sortItems(column, new_order)
        
        # 정렬 방향 표시
        self.horizontalHeader().setSortIndicator(column, new_order)
        
    def sortItems(self, column, order):
        """컬럼별 정렬 처리 (발주수량은 숫자 기준)"""
        if not hasattr(self, '_current_data'):
            return
        # 발주수량 컬럼(10번)만 숫자 기준 정렬
        if column == 10:
            reverse = (order == Qt.DescendingOrder)
            self._current_data.sort(
                key=lambda x: x.get("발주수량", 0),
                reverse=reverse
            )
            self.update_data(self._current_data)
        else:
            super().sortItems(column, order)
        
    def update_data(self, data: List[Dict[str, Any]]):
        """테이블 데이터 업데이트 (모든 컬럼)"""
        try:
            from PySide6.QtWidgets import QApplication
            import requests
            from io import BytesIO
            print(f"[update_data] 테이블 데이터 업데이트 시작: {len(data)}건")
            
            # 발주수량을 숫자로 변환
            for item in data:
                try:
                    quantity = item.get("발주수량", "")
                    if quantity:
                        quantity = int(str(quantity).replace(',', ''))
                        item["발주수량"] = quantity
                except:
                    item["발주수량"] = 0
            
            # 현재 데이터 저장
            self._current_data = data
            
            # 데이터 타입 확인을 위한 디버깅 로그
            if data:
                sample_item = data[0]
                print(f"[update_data] 발주수량 데이터 타입: {type(sample_item.get('발주수량'))}")
                print(f"[update_data] 발주수량 값: {sample_item.get('발주수량')}")
            
            self.setRowCount(0)
            if not data:
                print("[update_data] 데이터 없음")
                return
                
            total_rows = len(data)
            self.setRowCount(total_rows)
            batch_size = 50
            
            for batch_start in range(0, total_rows, batch_size):
                batch_end = min(batch_start + batch_size, total_rows)
                for row_idx in range(batch_start, batch_end):
                    try:
                        item = data[row_idx]
                        print(f"[update_data] {row_idx+1}/{total_rows}행 처리 시작")
                        
                        # 체크박스
                        checkbox = QCheckBox()
                        if item.get("선택", False):
                            checkbox.setChecked(True)
                        checkbox.stateChanged.connect(
                            lambda state, r=row_idx: self._on_checkbox_changed(state, r)
                        )
                        self.setCellWidget(row_idx, 0, self._create_checkbox_widget(checkbox))
                        
                        # 사진 썸네일 (사진 로드 체크박스 상태에 따라)
                        if self.load_photo:
                            photo_url = item.get("사진_URL", "")
                            if not photo_url:
                                photo_url = item.get("프린트_URL", "")
                            if photo_url:
                                try:
                                    print(f"[update_data] {row_idx+1}행 이미지 요청: {photo_url}")
                                    response = requests.get(photo_url, timeout=5)
                                    if response.status_code == 200:
                                        image = QPixmap()
                                        image.loadFromData(response.content)
                                        thumbnail = image.scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                                        label = QLabel()
                                        label.setPixmap(thumbnail)
                                        label.setAlignment(Qt.AlignCenter)
                                        self.setCellWidget(row_idx, 1, label)
                                    else:
                                        print(f"[update_data] {row_idx+1}행 이미지 응답코드: {response.status_code}")
                                        self.setItem(row_idx, 1, QTableWidgetItem(""))
                                except Exception as img_error:
                                    print(f"[update_data] {row_idx+1}행 이미지 로드 오류: {img_error}")
                                    self.setItem(row_idx, 1, QTableWidgetItem(""))
                            else:
                                self.setItem(row_idx, 1, QTableWidgetItem(""))
                        else:
                            self.setItem(row_idx, 1, QTableWidgetItem(""))
                            
                        # ID (링크)
                        id_text = item.get("ID", "")
                        id_url = item.get("ID_URL", "")
                        id_label = QLabel()
                        if id_url:
                            id_label.setText(f'<a href="{id_url}">{id_text}</a>')
                            id_label.setTextFormat(Qt.RichText)
                            id_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
                            id_label.setOpenExternalLinks(True)
                        else:
                            id_label.setText(id_text)
                        self.setCellWidget(row_idx, 2, id_label)
                        # 판매자 (링크)
                        seller = item.get("판매자", "")
                        seller_url = item.get("판매자_URL", "")
                        seller_label = QLabel()
                        if seller_url:
                            seller_label.setText(f'<a href="{seller_url}">{seller}</a>')
                            seller_label.setTextFormat(Qt.RichText)
                            seller_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
                            seller_label.setOpenExternalLinks(True)
                        else:
                            seller_label.setText(seller)
                        self.setCellWidget(row_idx, 3, seller_label)
                        # 판매자 동대문주소
                        self.setItem(row_idx, 4, QTableWidgetItem(str(item.get("판매자_동대문주소", ""))))
                        # 아이템 (링크)
                        item_name = item.get("아이템", "")
                        item_url = item.get("아이템_URL", "")
                        item_label = QLabel()
                        if item_url:
                            item_label.setText(f'<a href="{item_url}">{item_name}</a>')
                            item_label.setTextFormat(Qt.RichText)
                            item_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
                            item_label.setOpenExternalLinks(True)
                        else:
                            item_label.setText(item_name)
                        self.setCellWidget(row_idx, 5, item_label)
                        # 스와치 보관함
                        self.setItem(row_idx, 6, QTableWidgetItem(str(item.get("스와치_보관함", ""))))
                        # 컬러순서
                        self.setItem(row_idx, 7, QTableWidgetItem(str(item.get("컬러순서", ""))))
                        # 컬러코드
                        self.setItem(row_idx, 8, QTableWidgetItem(str(item.get("컬러코드", ""))))
                        # 발주수량
                        quantity = item.get("발주수량", 0)
                        item_widget = QTableWidgetItem(str(quantity))
                        item_widget.setData(Qt.UserRole, quantity)
                        self.setItem(row_idx, 10, item_widget)
                        # 발주번호 (링크)
                        order_num = item.get("발주번호", "")
                        order_url = item.get("발주번호_URL", "")
                        order_label = QLabel()
                        if order_url:
                            order_label.setText(f'<a href="{order_url}">{order_num}</a>')
                            order_label.setTextFormat(Qt.RichText)
                            order_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
                            order_label.setOpenExternalLinks(True)
                        else:
                            order_label.setText(order_num)
                        self.setCellWidget(row_idx, 11, order_label)
                        # 주문번호 (링크)
                        order_num2 = item.get("주문번호", "")
                        order_url2 = item.get("주문번호_URL", "")
                        order_label2 = QLabel()
                        if order_url2:
                            order_label2.setText(f'<a href="{order_url2}">{order_num2}</a>')
                            order_label2.setTextFormat(Qt.RichText)
                            order_label2.setTextInteractionFlags(Qt.TextBrowserInteraction)
                            order_label2.setOpenExternalLinks(True)
                        else:
                            order_label2.setText(order_num2)
                        self.setCellWidget(row_idx, 12, order_label2)
                        # 최종출고일자
                        self.setItem(row_idx, 13, QTableWidgetItem(str(item.get("최종출고일자", ""))))
                        # 발주출고예상일자
                        self.setItem(row_idx, 14, QTableWidgetItem(str(item.get("발주출고예상일자", ""))))
                        # 발주배송수단
                        self.setItem(row_idx, 15, QTableWidgetItem(str(item.get("발주배송수단", ""))))
                        # 판매자발송수단
                        self.setItem(row_idx, 16, QTableWidgetItem(str(item.get("판매자발송수단", ""))))
                        # 발주상태
                        self.setItem(row_idx, 17, QTableWidgetItem(str(item.get("발주상태", ""))))
                        # 메시지상태
                        msg_status = item.get("메시지상태", "대기중")
                        status_item = QTableWidgetItem(msg_status)
                        self.setItem(row_idx, 18, status_item)
                        try:
                            if msg_status == "대기중":
                                status_item.setBackground(QColor("#FF8C00"))  # 주황색
                                status_item.setForeground(QColor("#000000"))  # 텍스트 검정
                            elif msg_status == "전송완료":
                                status_item.setBackground(QColor("#4CAF50"))  # 초록색
                                status_item.setForeground(QColor("#FFFFFF"))  # 텍스트 흰색
                            elif msg_status == "전송실패":
                                status_item.setBackground(QColor("#F44336"))  # 빨간색
                                status_item.setForeground(QColor("#FFFFFF"))  # 텍스트 흰색
                        except Exception as color_error:
                            print(f"[update_data] {row_idx+1}행 상태 색상 오류: {str(color_error)}")
                            
                        print(f"[update_data] {row_idx+1}/{total_rows}행 처리 완료")
                    except Exception as row_error:
                        print(f"[update_data] {row_idx+1}행 처리 중 오류: {str(row_error)}")
                        for col in range(self.columnCount()):
                            self.setItem(row_idx, col, QTableWidgetItem(""))
                QApplication.processEvents()
            QApplication.processEvents()
            print(f"[update_data] {batch_end}/{total_rows}행까지 처리 완료")
        except Exception as e:
            print(f"테이블 업데이트 중 오류: {str(e)}")
            self.setRowCount(0)
            
    def sort_data(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """다중 정렬 수행"""
        def get_sort_key(item):
            return tuple(item.get(key, "") for key in self.sort_priority)
            
        return sorted(data, key=get_sort_key)
        
    def _on_checkbox_changed(self, state: int, row: int):
        """체크박스 상태 변경 이벤트"""
        selected_items = []
        for row in range(self.rowCount()):
            checkbox = self.cellWidget(row, 0).findChild(QCheckBox)
            if checkbox and checkbox.isChecked():
                # 안전하게 QLabel 추출
                seller_label = self.cellWidget(row, 3)
                order_label = self.cellWidget(row, 11)
                seller_text = ""
                order_text = ""
                if seller_label:
                    label = seller_label.findChild(QLabel)
                    if label:
                        seller_text = label.text()
                if order_label:
                    label = order_label.findChild(QLabel)
                    if label:
                        order_text = label.text()
                selected_items.append({
                    "판매자": seller_text,
                    "발주번호": order_text
                })
        self.selection_changed.emit(selected_items)
    
    def _create_checkbox_widget(self, checkbox):
        """체크박스를 위한 위젯 생성"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignCenter)
        layout.addWidget(checkbox)
        return widget
    
    def select_all(self):
        """모든 항목 선택"""
        for row in range(self.rowCount()):
            checkbox = self.cellWidget(row, 0).findChild(QCheckBox)
            if checkbox:
                checkbox.setChecked(True)
    
    def deselect_all(self):
        """모든 항목 선택 해제"""
        for row in range(self.rowCount()):
            checkbox = self.cellWidget(row, 0).findChild(QCheckBox)
            if checkbox:
                checkbox.setChecked(False) 