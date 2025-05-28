"""
관리비 정산 섹션 (레퍼런스 기반, 한 건씩 진행)
"""
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFrame, QTableWidget, QTableWidgetItem, QFileDialog
)
from PySide6.QtCore import Qt, QThread, Signal
from core.types import SectionType
# from reference.maintenance_fee_handler import MaintenanceFeeHandler  # 삭제
from services.maintenance_handler import MaintenanceHandler
from core.config import ConfigManager
from ui.sections.base_section import BaseSection
from ui.components.log_widget import LOG_INFO, LOG_WARNING, LOG_ERROR, LOG_SUCCESS
import os
import re
import json
from datetime import datetime
from bs4 import BeautifulSoup

class SettlementWorker(QThread):
    """정산서 작성 작업을 처리하는 워커 스레드"""
    finished = Signal(bool, str)  # (성공여부, 메시지)
    
    def __init__(self, maintenance_handler, data):
        super().__init__()
        self.maintenance_handler = maintenance_handler
        self.data = data
    
    def run(self):
        try:
            result = self.maintenance_handler.process_maintenance_fee([self.data])
            if result:
                self.finished.emit(True, "정산서 작성 성공!")
            else:
                self.finished.emit(False, "정산서 작성 실패")
        except Exception as e:
            self.finished.emit(False, f"오류: {str(e)}")

def extract_info(html_content):
    """
    관리비 명세서 HTML에서 정보 추출
    Args:
        html_content: HTML 문자열
    Returns:
        tuple: (호수, 납기내금액, 연도, 월)
    """
    try:
        soup = BeautifulSoup(html_content, "html.parser")

        # 연도, 월 추출
        year_month_div = soup.find("div", text=re.compile(r"\d{4}년\s+\d{1,2}월분"))
        if year_month_div:
            match = re.search(r"(\d{4})년\s+(\d{1,2})월분", year_month_div.text)
            if match:
                year = int(match.group(1))
                month = int(match.group(2))
            else:
                year, month = None, None

        # 호수 추출 (D동 1015호)
        unit_div = soup.find("div", string=lambda text: text and "동" in text and "호" in text)
        if unit_div:
            unit_number = unit_div.text.strip()
            print(f"호수 찾음: {unit_number}")

        # 납기내금액 추출 (254,580)
        total_amount = None
        total_div = soup.find("div", style=lambda s: s and "color:#f31414" in s)
        if total_div:
            strong = total_div.find("strong")
            if strong:
                total_amount = int(strong.text.strip().replace(",", ""))
                print(f"납기내금액 찾음: {total_amount}")

        if unit_number and total_amount and year and month:
            return unit_number, total_amount, year, month
        return None

    except Exception as e:
        print(f"HTML 처리 중 오류 발생: {str(e)}")
        return None

class MaintenanceFeeSection(BaseSection):
    """관리비 정산 섹션 (파일 임포트, 테이블, 자동화, 한 건씩 진행)"""
    def __init__(self, parent=None):
        super().__init__("관리비 정산", parent)
        # self.fee_handler = MaintenanceFeeHandler()  # 삭제
        self.config_manager = ConfigManager()
        self.maintenance_handler = MaintenanceHandler(self.config_manager)
        self.files_data = []  # (file_path, unit_number, total_amount, supply_amount, vat_amount, year, month)
        self.current_index = 0  # 현재 진행 중인 인덱스
        self.worker = None  # 워커 스레드
        
        # JSON 데이터 저장 경로 설정
        self.data_dir = os.path.join('data', 'maintenance_fee')
        os.makedirs(self.data_dir, exist_ok=True)
        
        self._init_ui()

    def on_section_activated(self):
        """섹션이 활성화될 때 호출되는 메서드"""
        self.log("관리비 정산 섹션이 활성화되었습니다.", LOG_INFO)
        # 필요한 초기화 작업이 있다면 여기에 추가

    def _init_ui(self):
        # 상단: 파일 선택 버튼
        top_layout = QHBoxLayout()
        self.file_button = QPushButton("정산서(HTML) 파일 선택")
        self.file_button.clicked.connect(self.select_files)
        top_layout.addWidget(self.file_button)
        top_layout.addStretch()
        self.content_layout.addLayout(top_layout)

        # 테이블
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["파일명", "호수", "공급가액", "부가세", "합계", "연월", "상태"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.content_layout.addWidget(self.table)

        # 정산서 작성 버튼
        btn_layout = QHBoxLayout()
        self.process_button = QPushButton("정산서 작성 (다음)")
        self.process_button.clicked.connect(self.process_next_maintenance)
        btn_layout.addStretch()
        btn_layout.addWidget(self.process_button)
        self.content_layout.addLayout(btn_layout)

    def select_files(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "관리비 정산서(HTML) 선택", "", "HTML Files (*.html *.htm)"
        )
        if not file_paths:
            return
        
        self.files_data.clear()
        self.table.setRowCount(0)
        self.current_index = 0
        
        # JSON 데이터 구조 초기화
        maintenance_data = {
            "created_at": datetime.now().isoformat(),
            "total_count": len(file_paths),
            "processed_count": 0,
            "items": []
        }
        
        for file_path in file_paths:
            try:
                file_name = os.path.basename(file_path)
                with open(file_path, "r", encoding="utf-8") as f:
                    html_content = f.read()
                
                result = extract_info(html_content)
                if not result:
                    self.log(f"[오류] {file_name}: 데이터 추출 실패", LOG_ERROR)
                    continue
                
                unit_number, total_amount, year, month = result
                supply_amount = int(total_amount / 1.1) if total_amount else 0
                vat_amount = total_amount - supply_amount if total_amount else 0
                
                # 파일 데이터 저장
                file_data = (file_path, unit_number, total_amount, supply_amount, vat_amount, year, month)
                self.files_data.append(file_data)
                
                # JSON 아이템 데이터 생성
                item_data = {
                    "id": len(maintenance_data["items"]) + 1,
                    "file_path": file_path,
                    "file_name": file_name,
                    "unit_number": unit_number,
                    "total_amount": total_amount,
                    "supply_amount": supply_amount,
                    "vat_amount": vat_amount,
                    "year": year,
                    "month": month,
                    "status": "대기중",
                    "created_at": datetime.now().isoformat(),
                    "processed_at": None,
                    "error_message": None
                }
                maintenance_data["items"].append(item_data)
                
                # 테이블에 행 추가
                row = self.table.rowCount()
                self.table.insertRow(row)
                self.table.setItem(row, 0, QTableWidgetItem(file_name))
                self.table.setItem(row, 1, QTableWidgetItem(str(unit_number)))
                self.table.setItem(row, 2, QTableWidgetItem(f"{supply_amount:,}"))
                self.table.setItem(row, 3, QTableWidgetItem(f"{vat_amount:,}"))
                self.table.setItem(row, 4, QTableWidgetItem(f"{total_amount:,}"))
                self.table.setItem(row, 5, QTableWidgetItem(f"{year}-{month:02d}"))
                self.table.setItem(row, 6, QTableWidgetItem("대기중"))
                
            except Exception as e:
                self.log(f"[오류] {file_name}: {str(e)}", LOG_ERROR)
        
        # JSON 파일 저장
        if maintenance_data["items"]:
            self._save_maintenance_data(maintenance_data)
            self.log(f"{len(maintenance_data['items'])}개의 관리비 정산 데이터를 로드했습니다.", LOG_SUCCESS)

    def _save_maintenance_data(self, data):
        """관리비 데이터를 JSON 파일로 저장"""
        try:
            # 첫 번째 항목의 연월 정보 사용
            if data["items"]:
                first_item = data["items"][0]
                year_month = f"{first_item['year']:02d}{first_item['month']:02d}"
            else:
                year_month = "0000"
            
            today = datetime.now().strftime("%y%m%d")
            filename = f"maintenance_fee_{year_month}_{today}.json"
            file_path = os.path.join(self.data_dir, filename)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            self.current_json_file = file_path
            self.log(f"관리비 데이터를 저장했습니다: {filename}", LOG_INFO)
            
        except Exception as e:
            self.log(f"JSON 파일 저장 중 오류: {str(e)}", LOG_ERROR)

    def _update_item_status(self, index, status, error_message=None):
        """JSON 파일의 특정 항목 상태 업데이트"""
        try:
            if not hasattr(self, 'current_json_file') or not os.path.exists(self.current_json_file):
                return
            
            # JSON 파일 읽기
            with open(self.current_json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 해당 항목 상태 업데이트
            if 0 <= index < len(data["items"]):
                data["items"][index]["status"] = status
                data["items"][index]["processed_at"] = datetime.now().isoformat()
                if error_message:
                    data["items"][index]["error_message"] = error_message
                
                # 처리 완료 카운트 업데이트
                if status in ["성공", "실패"]:
                    data["processed_count"] = len([item for item in data["items"] if item["status"] in ["성공", "실패"]])
            
            # JSON 파일 저장
            with open(self.current_json_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            self.log(f"상태 업데이트 중 오류: {str(e)}", LOG_ERROR)

    def process_next_maintenance(self):
        if not self.files_data:
            self.log("[오류] 파일을 먼저 선택하세요.", LOG_ERROR)
            return
        if self.current_index >= len(self.files_data):
            self.log("모든 정산서 작성이 완료되었습니다.", LOG_SUCCESS)
            return
        
        # 이미 진행 중인 작업이 있다면 중단
        if self.worker and self.worker.isRunning():
            self.log("이미 진행 중인 작업이 있습니다.", LOG_WARNING)
            return
        
        data = self.files_data[self.current_index]
        file_name = os.path.basename(data[0])
        unit_number = data[1]
        
        # 상태를 "진행중"으로 업데이트
        self._update_item_status(self.current_index, "진행중")
        
        self.log(f"[{self.current_index+1}/{len(self.files_data)}] {file_name} ({unit_number}) 정산서 작성 시작...", LOG_INFO)
        self.table.setItem(self.current_index, 6, QTableWidgetItem("진행중"))
        
        # 워커 스레드 생성 및 시작
        self.worker = SettlementWorker(self.maintenance_handler, data)
        self.worker.finished.connect(self._on_settlement_finished)
        self.worker.start()
        
        # 버튼 비활성화
        self.process_button.setEnabled(False)
        self.process_button.setText("처리 중...")
    
    def _on_settlement_finished(self, success, message):
        """정산서 작성 완료 처리"""
        status = "성공" if success else "실패"
        error_message = None if success else message
        
        # JSON 상태 업데이트
        self._update_item_status(self.current_index, status, error_message)
        
        # 테이블 상태 업데이트
        self.table.setItem(self.current_index, 6, QTableWidgetItem(status))
        
        file_name = os.path.basename(self.files_data[self.current_index][0])
        unit_number = self.files_data[self.current_index][1]
        log_type = LOG_SUCCESS if success else LOG_ERROR
        self.log(f"[{self.current_index+1}/{len(self.files_data)}] {file_name} ({unit_number}) {message}", log_type)
        
        self.current_index += 1
        if self.current_index >= len(self.files_data):
            self.log("모든 정산서 작성이 완료되었습니다.", LOG_SUCCESS)
            # 모든 작업 완료 후 브라우저 정리
            self.maintenance_handler.cleanup()
        
        # 버튼 상태 복구
        self.process_button.setEnabled(True)
        self.process_button.setText("정산서 작성 (다음)")
        
        # 워커 정리
        self.worker.deleteLater()
        self.worker = None 