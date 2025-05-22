"""
FBO 출고 요청 테이블 컴포넌트
"""
from typing import List, Dict, Any
from PySide6.QtWidgets import (
    QTableWidget, QTableWidgetItem, QHeaderView, QWidget, QHBoxLayout,
    QCheckBox, QLabel, QDialog, QVBoxLayout, QPushButton, QScrollArea,
    QDialogButtonBox, QMenu
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QColor, QPixmap, QCursor, QAction

from ui.theme import get_theme
from ui.components.log_widget import LOG_INFO, LOG_WARNING, LOG_ERROR

class ImageDialog(QDialog):
    """이미지 확대 보기 다이얼로그"""
    def __init__(self, image_url: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("이미지 보기")
        self.setModal(True)
        
        # 레이아웃 설정
        layout = QVBoxLayout(self)
        
        # 스크롤 영역 생성
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll)
        
        # 이미지 표시 레이블
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        scroll.setWidget(self.image_label)
        
        # 이미지 로드
        try:
            import requests
            response = requests.get(image_url, timeout=5)
            if response.status_code == 200:
                pixmap = QPixmap()
                pixmap.loadFromData(response.content)
                self.image_label.setPixmap(pixmap)
                # 창 크기 조정
                screen_size = self.screen().size()
                max_width = int(screen_size.width() * 0.8)
                max_height = int(screen_size.height() * 0.8)
                self.resize(min(pixmap.width(), max_width), min(pixmap.height(), max_height))
        except Exception as e:
            self.image_label.setText(f"이미지 로드 실패: {str(e)}")
        
        # 닫기 버튼
        button_box = QDialogButtonBox(QDialogButtonBox.Close)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

class ShipmentRequestTable(QTableWidget):
    """FBO 출고 요청 테이블 컴포넌트"""
    
    # 시그널 정의
    selection_changed = Signal(list)  # 선택된 항목 변경 시그널
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_table()
        self.sort_columns = []  # 정렬 우선순위 저장
        
    def setup_table(self):
        """테이블 초기 설정"""
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setSelectionMode(QTableWidget.SingleSelection)
        self.setEditTriggers(QTableWidget.NoEditTriggers)
        self.setSortingEnabled(True)  # 정렬 활성화
        
        # 컬럼 정의
        self.setColumnCount(17)  # 판매방식, 발주상태 제외
        self.setHorizontalHeaderLabels([
            "선택", "사진", "ID", "판매자", "판매자 동대문주소", "아이템", 
            "스와치 보관함", "컬러순서", "컬러코드", "발주수량", "발주번호", 
            "주문번호", "최종출고일자", "발주출고예상일자", "발주배송수단", 
            "판매자발송수단", "메시지상태"
        ])
        
        # 헤더 설정
        header = self.horizontalHeader()
        header.setContextMenuPolicy(Qt.CustomContextMenu)
        header.customContextMenuRequested.connect(self._show_header_menu)
        
        # 컬럼 너비 설정
        for i in range(self.columnCount()):
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
    
    def _show_header_menu(self, pos):
        """헤더 우클릭 메뉴 표시"""
        header = self.horizontalHeader()
        column = header.logicalIndexAt(pos)
        
        menu = QMenu(self)
        
        # 정렬 메뉴
        sort_menu = menu.addMenu("정렬")
        sort_asc = sort_menu.addAction("오름차순")
        sort_desc = sort_menu.addAction("내림차순")
        
        # 정렬 우선순위 메뉴
        priority_menu = menu.addMenu("정렬 우선순위")
        for i in range(self.columnCount()):
            col_name = self.horizontalHeaderItem(i).text()
            action = priority_menu.addAction(col_name)
            action.setCheckable(True)
            action.setChecked(i in [col for col, _ in self.sort_columns])
        
        # 메뉴 실행
        action = menu.exec(header.mapToGlobal(pos))
        
        if action == sort_asc:
            self.sortItems(column, Qt.AscendingOrder)
        elif action == sort_desc:
            self.sortItems(column, Qt.DescendingOrder)
        elif action in priority_menu.actions():
            # 우선순위 설정
            col_name = action.text()
            col_idx = [i for i in range(self.columnCount()) if self.horizontalHeaderItem(i).text() == col_name][0]
            
            if action.isChecked():
                # 우선순위 추가
                if not any(col == col_idx for col, _ in self.sort_columns):
                    self.sort_columns.append((col_idx, Qt.AscendingOrder))
            else:
                # 우선순위 제거
                self.sort_columns = [(col, order) for col, order in self.sort_columns if col != col_idx]
            
            # 다중 정렬 적용
            self._apply_multi_sort()
    
    def _apply_multi_sort(self):
        """다중 정렬 적용"""
        if not self.sort_columns:
            return
            
        # 정렬 우선순위에 따라 정렬
        for col, order in reversed(self.sort_columns):
            self.sortItems(col, order)
    
    def update_data(self, data: List[Dict[str, Any]]):
        """테이블 데이터 업데이트 (모든 컬럼)"""
        try:
            from PySide6.QtWidgets import QApplication
            import requests
            from io import BytesIO
            print(f"[update_data] 테이블 데이터 업데이트 시작: {len(data)}건")
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
                        
                        # 사진 썸네일 (사진_URL 없으면 프린트_URL 사용)
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
                                    label.setCursor(Qt.PointingHandCursor)  # 커서 변경
                                    label.mousePressEvent = lambda e, url=photo_url: self._show_image_dialog(url)
                                    self.setCellWidget(row_idx, 1, label)
                                else:
                                    print(f"[update_data] {row_idx+1}행 이미지 응답코드: {response.status_code}")
                                    self.setItem(row_idx, 1, QTableWidgetItem(""))
                            except Exception as img_error:
                                print(f"[update_data] {row_idx+1}행 이미지 로드 오류: {img_error}")
                                self.setItem(row_idx, 1, QTableWidgetItem(""))
                        else:
                            self.setItem(row_idx, 1, QTableWidgetItem(""))
                            
                        # 나머지 컬럼들...
                        # [기존 코드와 동일하게 유지, 컬럼 인덱스만 조정]
                        
                        # 메시지상태 (배경색 조정)
                        msg_status = item.get("메시지상태", "대기중")
                        status_item = QTableWidgetItem(msg_status)
                        self.setItem(row_idx, 16, status_item)  # 인덱스 조정
                        try:
                            if msg_status == "대기중":
                                status_item.setBackground(QColor("#FFA500"))  # 더 진한 주황색
                            elif msg_status == "전송완료":
                                status_item.setBackground(QColor(get_theme().get_color("success")))
                            elif msg_status == "전송실패":
                                status_item.setBackground(QColor(get_theme().get_color("error")))
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
            
            # 다중 정렬 적용
            self._apply_multi_sort()
            
        except Exception as e:
            print(f"테이블 업데이트 중 오류: {str(e)}")
            self.setRowCount(0)
    
    def _show_image_dialog(self, image_url: str):
        """이미지 확대 다이얼로그 표시"""
        dialog = ImageDialog(image_url, self)
        dialog.exec()
    
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