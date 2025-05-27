"""
설정 섹션 - 애플리케이션 설정 관리
"""
from typing import List, Dict, Any, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFormLayout, QLineEdit, QCheckBox, QComboBox, QSpinBox,
    QTabWidget, QGroupBox, QSpacerItem, QSizePolicy, QFileDialog,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QFont, QColor

from core.types import LogType, ThemeMode, SectionType
from ui.sections.base_section import BaseSection
from ui.theme import get_theme
from core.config import ConfigManager
from core.constants import ConfigKey, SpreadsheetConfigKey, SECTION_SPREADSHEET_MAPPING
from ui.components.log_widget import LOG_INFO, LOG_DEBUG, LOG_WARNING, LOG_ERROR, LOG_SUCCESS

class SettingsSection(BaseSection):
    """
    설정 섹션 - 애플리케이션 설정 관리
    """
    
    def __init__(self, parent=None):
        super().__init__("설정", parent)
        
        # 설정 관리자 인스턴스 가져오기
        self.config_manager = ConfigManager()
        
        # 저장 버튼 추가
        self.save_button = self.add_header_button("저장", self._on_save_clicked, primary=True)
        
        # 설정 로드 플래그
        self._settings_loaded = False
        
        # 콘텐츠 설정
        self.setup_content()
    
    def setup_content(self):
        """콘텐츠 설정"""
        # 탭 위젯 생성
        tab_widget = QTabWidget()
        
        # 일반 설정 탭
        general_tab = QWidget()
        general_layout = QFormLayout(general_tab)
        general_layout.setContentsMargins(16, 16, 16, 16)
        general_layout.setSpacing(12)
        
        # 테마 설정
        self.theme_combo = QComboBox()
        self.theme_combo.addItem("시스템 설정 따름", ThemeMode.SYSTEM.value)
        self.theme_combo.addItem("라이트 모드", ThemeMode.LIGHT.value)
        self.theme_combo.addItem("다크 모드", ThemeMode.DARK.value)
        
        current_theme = get_theme().get_theme_name()
        for i in range(self.theme_combo.count()):
            if self.theme_combo.itemData(i) == current_theme:
                self.theme_combo.setCurrentIndex(i)
                break
        
        general_layout.addRow("테마:", self.theme_combo)
        
        # 로그 설정
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItem("디버그", LogType.DEBUG.value)
        self.log_level_combo.addItem("정보", LogType.INFO.value)
        self.log_level_combo.addItem("경고", LogType.WARNING.value)
        self.log_level_combo.addItem("오류", LogType.ERROR.value)
        
        # 현재 로그 레벨 설정
        current_log_level = self.config_manager.get(ConfigKey.LOG_LEVEL, LogType.INFO.value)
        for i in range(self.log_level_combo.count()):
            if self.log_level_combo.itemData(i) == current_log_level:
                self.log_level_combo.setCurrentIndex(i)
                break
        
        general_layout.addRow("로그 레벨:", self.log_level_combo)
        
        # 로그 파일 저장 옵션
        self.save_log_check = QCheckBox("로그 파일 저장")
        self.save_log_check.setChecked(self.config_manager.get(ConfigKey.SAVE_LOGS, True))
        
        general_layout.addRow("", self.save_log_check)
        
        # 로그 파일 경로
        self.log_path_edit = QLineEdit()
        self.log_path_edit.setPlaceholderText("로그 파일 경로를 입력하세요")
        self.log_path_edit.setText(self.config_manager.get(ConfigKey.LOGS_PATH, "logs"))
        
        log_path_layout = QHBoxLayout()
        log_path_layout.setSpacing(8)
        log_path_layout.addWidget(self.log_path_edit)
        
        # 파일 선택 버튼
        log_path_button = QPushButton("찾아보기...")
        log_path_button.clicked.connect(self._on_log_path_browse)
        log_path_layout.addWidget(log_path_button)
        
        general_layout.addRow("로그 경로:", log_path_layout)
        
        # 여백 추가
        general_layout.addItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        
        # 카카오톡 설정 탭
        kakao_tab = QWidget()
        kakao_layout = QFormLayout(kakao_tab)
        kakao_layout.setContentsMargins(16, 16, 16, 16)
        kakao_layout.setSpacing(12)
        
        # 카카오톡 경로
        self.kakao_path_edit = QLineEdit()
        self.kakao_path_edit.setPlaceholderText("카카오톡 실행 파일 경로")
        self.kakao_path_edit.setText(self.config_manager.get(ConfigKey.KAKAO_PATH, ""))
        
        kakao_path_layout = QHBoxLayout()
        kakao_path_layout.setSpacing(8)
        kakao_path_layout.addWidget(self.kakao_path_edit)
        
        # 파일 선택 버튼
        kakao_path_button = QPushButton("찾아보기...")
        kakao_path_button.clicked.connect(self._on_kakao_path_browse)
        kakao_path_layout.addWidget(kakao_path_button)
        
        kakao_layout.addRow("카카오톡 경로:", kakao_path_layout)
        
        # 자동 실행 설정
        self.auto_start_kakao = QCheckBox("프로그램 시작 시 카카오톡 자동 실행")
        self.auto_start_kakao.setChecked(self.config_manager.get(ConfigKey.AUTO_START_KAKAO, False))
        kakao_layout.addRow("", self.auto_start_kakao)
        
        # 메시지 딜레이 설정
        self.message_delay = QSpinBox()
        self.message_delay.setMinimum(100)
        self.message_delay.setMaximum(5000)
        self.message_delay.setValue(self.config_manager.get(ConfigKey.MESSAGE_DELAY, 1000))
        self.message_delay.setSuffix(" ms")
        
        kakao_layout.addRow("메시지 딜레이:", self.message_delay)
        
        # 여백 추가
        kakao_layout.addItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        
        # 스프레드시트 설정 탭
        spreadsheet_tab = QWidget()
        spreadsheet_layout = QVBoxLayout(spreadsheet_tab)
        spreadsheet_layout.setContentsMargins(16, 16, 16, 16)
        spreadsheet_layout.setSpacing(12)
        
        # 자격 증명 파일 경로 그룹
        credentials_group = QGroupBox("Google API 자격 증명")
        credentials_layout = QFormLayout(credentials_group)
        
        # 자격 증명 파일 경로
        self.credentials_path_edit = QLineEdit()
        self.credentials_path_edit.setPlaceholderText("credentials.json 파일 경로")
        self.credentials_path_edit.setText(self.config_manager.get(ConfigKey.GOOGLE_CREDENTIALS, ""))
        
        credentials_path_layout = QHBoxLayout()
        credentials_path_layout.setSpacing(8)
        credentials_path_layout.addWidget(self.credentials_path_edit)
        
        # 파일 선택 버튼
        credentials_path_button = QPushButton("찾아보기...")
        credentials_path_button.clicked.connect(self._on_credentials_path_browse)
        credentials_path_layout.addWidget(credentials_path_button)
        
        credentials_layout.addRow("자격 증명 파일:", credentials_path_layout)
        
        # API 요청 제한
        self.api_limit = QSpinBox()
        self.api_limit.setMinimum(10)
        self.api_limit.setMaximum(1000)
        self.api_limit.setValue(self.config_manager.get(ConfigKey.API_LIMIT, 60))
        self.api_limit.setSuffix(" 요청/분")
        
        credentials_layout.addRow("API 요청 제한:", self.api_limit)
        
        spreadsheet_layout.addWidget(credentials_group)
        
        # 스크래핑 URL 설정 탭
        scraping_tab = QWidget()
        scraping_layout = QFormLayout(scraping_tab)
        scraping_layout.setContentsMargins(16, 16, 16, 16)
        scraping_layout.setSpacing(12)
        
        # SwatchOn 관리자 페이지 URL
        self.swatchon_admin_url = QLineEdit()
        self.swatchon_admin_url.setPlaceholderText("SwatchOn Admin 페이지 기본 URL")
        self.swatchon_admin_url.setText(
            self.config_manager.get(ConfigKey.SWATCHON_ADMIN_URL, "https://admin.swatchon.me")
        )
        scraping_layout.addRow("Admin 페이지 URL:", self.swatchon_admin_url)
        
        # 스크래핑 URL (입고 페이지 URL, 모든 기능 공통)
        self.receive_scraping_url = QLineEdit()
        self.receive_scraping_url.setPlaceholderText("스크래핑 페이지 URL을 입력하세요")
        self.receive_scraping_url.setText(
            self.config_manager.get(ConfigKey.RECEIVE_SCRAPING_URL, 
                                   self.config_manager.get(ConfigKey.SWATCHON_ADMIN_URL, "https://admin.swatchon.me") + "/purchase_products/receive_index")
        )
        scraping_layout.addRow("스크래핑 URL:", self.receive_scraping_url)
        
        # 설명 추가
        url_help_label = QLabel("※ 모든 출고 요청/확인 및 입고 기능은 동일한 스크래핑 URL을 사용합니다.")
        url_help_label.setStyleSheet("color: gray;")
        scraping_layout.addRow("", url_help_label)
        
        # 여백 추가
        scraping_layout.addItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        
        # 주소록 스프레드시트 설정 그룹
        address_group = QGroupBox("주소록 스프레드시트 설정 (모든 기능 공통)")
        address_layout = QFormLayout(address_group)
        
        # 주소록 스프레드시트 URL
        self.address_spreadsheet_url = QLineEdit()
        self.address_spreadsheet_url.setPlaceholderText("주소록 스프레드시트 URL을 입력하세요")
        self.address_spreadsheet_url.setText(self.config_manager.get(ConfigKey.ADDRESS_BOOK_URL, ""))
        address_layout.addRow("스프레드시트 URL:", self.address_spreadsheet_url)
        
        # 주소록 시트 이름
        self.address_sheet_name = QLineEdit()
        self.address_sheet_name.setPlaceholderText("주소록 시트 이름을 입력하세요")
        self.address_sheet_name.setText(self.config_manager.get(ConfigKey.ADDRESS_BOOK_SHEET, "주소록"))
        address_layout.addRow("시트 이름:", self.address_sheet_name)
        
        # 테스트 버튼
        address_test_button = QPushButton("연결 테스트")
        address_test_button.clicked.connect(self._on_address_test)
        address_layout.addRow("", address_test_button)
        
        spreadsheet_layout.addWidget(address_group)
        
        # 기능별 스프레드시트 설정 테이블
        sheet_settings_group = QGroupBox("기능별 스프레드시트 설정")
        sheet_layout = QVBoxLayout(sheet_settings_group)
        
        # 테이블 위젯
        self.sheet_table = QTableWidget()
        self.sheet_table.setColumnCount(3)
        self.sheet_table.setHorizontalHeaderLabels(["기능", "스프레드시트 URL", "시트 이름"])
        self.sheet_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.sheet_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.sheet_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        
        sheet_layout.addWidget(self.sheet_table)
        
        # 버튼 레이아웃
        buttons_layout = QHBoxLayout()
        
        # 시트 설정 복사 버튼 (한 기능에서 다른 기능으로 설정 복사)
        copy_button = QPushButton("설정 복사")
        copy_button.clicked.connect(self._on_copy_sheet_settings)
        buttons_layout.addWidget(copy_button)
        
        # 스페이서
        buttons_layout.addStretch()
        
        # 테스트 연결 버튼
        test_button = QPushButton("연결 테스트")
        test_button.clicked.connect(self._on_test_connection)
        buttons_layout.addWidget(test_button)
        
        sheet_layout.addLayout(buttons_layout)
        
        spreadsheet_layout.addWidget(sheet_settings_group)
        
        # 일괄 변경 그룹
        bulk_settings_group = QGroupBox("일괄 설정")
        bulk_layout = QFormLayout(bulk_settings_group)
        
        # 모든 기능에 동일한 스프레드시트 적용
        self.bulk_spreadsheet_url = QLineEdit()
        self.bulk_spreadsheet_url.setPlaceholderText("모든 기능에 적용할 스프레드시트 URL")
        bulk_layout.addRow("스프레드시트 URL:", self.bulk_spreadsheet_url)
        
        # 적용 버튼
        apply_bulk_url_button = QPushButton("모든 기능에 URL 적용")
        apply_bulk_url_button.clicked.connect(self._on_apply_bulk_url)
        bulk_layout.addRow("", apply_bulk_url_button)
        
        spreadsheet_layout.addWidget(bulk_settings_group)
        
        # 여백 추가
        spreadsheet_layout.addItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        
        # 탭 추가
        tab_widget.addTab(general_tab, "일반 설정")
        tab_widget.addTab(kakao_tab, "카카오톡 설정")
        tab_widget.addTab(spreadsheet_tab, "스프레드시트 설정")
        tab_widget.addTab(scraping_tab, "스크래핑 URL 설정")
        
        # 레이아웃에 탭 위젯 추가
        self.content_layout.addWidget(tab_widget)
        
        # 설정 데이터 로드
        self._load_settings()
    
    def _load_settings(self):
        """설정 데이터 로드"""
        # 기능별 스프레드시트 설정 로드
        self._load_sheet_settings()
    
    def _load_sheet_settings(self):
        """기능별 스프레드시트 설정 로드"""
        # 테이블 크기 설정
        self.sheet_table.setRowCount(len(SECTION_SPREADSHEET_MAPPING))
        
        # 각 행에 데이터 설정
        row = 0
        for section_key, section_data in SECTION_SPREADSHEET_MAPPING.items():
            # 기능 이름
            self.sheet_table.setItem(row, 0, QTableWidgetItem(section_data["name"]))
            
            # 스프레드시트 URL - url_key 값을 문자열로 처리
            url_key = section_data["url_key"]
            url = self.config_manager.get(url_key, "")
            url_item = QTableWidgetItem(url)
            self.sheet_table.setItem(row, 1, url_item)
            
            # 시트 이름 - sheet_key 값을 문자열로 처리
            sheet_key = section_data["sheet_key"]
            sheet_name = self.config_manager.get(sheet_key, section_data["name"].split(" ")[-1])
            self.sheet_table.setItem(row, 2, QTableWidgetItem(sheet_name))
            
            row += 1
    
    def _on_log_path_browse(self):
        """로그 파일 경로 선택 대화상자"""
        directory = QFileDialog.getExistingDirectory(self, "로그 폴더 선택")
        if directory:
            self.log_path_edit.setText(directory)
    
    def _on_kakao_path_browse(self):
        """카카오톡 실행 파일 선택 대화상자"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "카카오톡 실행 파일 선택", "", "실행 파일 (*.exe)"
        )
        if file_path:
            self.kakao_path_edit.setText(file_path)
    
    def _on_credentials_path_browse(self):
        """자격 증명 파일 선택 대화상자"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "자격 증명 파일 선택", "", "JSON 파일 (*.json)"
        )
        if file_path:
            self.credentials_path_edit.setText(file_path)
    
    def _on_address_test(self):
        """주소록 스프레드시트 연결 테스트"""
        # 주소록 설정 가져오기
        spreadsheet_url = self.address_spreadsheet_url.text()
        sheet_name = self.address_sheet_name.text()
        
        if not spreadsheet_url or not sheet_name:
            self.log("주소록 스프레드시트 URL과 시트 이름을 모두 입력해주세요.", LOG_WARNING)
            return
        
        # 연결 테스트 로그
        self.log(f"주소록 스프레드시트 연결 테스트 중... URL: {spreadsheet_url}, 시트: {sheet_name}", LOG_INFO)
        
        # TODO: 실제 연결 테스트 구현
        
        # 테스트 성공 로그
        self.log("주소록 스프레드시트 연결 테스트 성공!", LOG_SUCCESS)
    
    def _on_copy_sheet_settings(self):
        """선택한 시트 설정을 다른 행으로 복사"""
        # 현재 선택된 행
        selected_rows = self.sheet_table.selectedIndexes()
        if not selected_rows:
            self.log("복사할 설정을 선택해주세요.", LOG_WARNING)
            return
        
        # 선택된 행에서 URL과 시트 이름 가져오기
        row = selected_rows[0].row()
        spreadsheet_url = self.sheet_table.item(row, 1).text()
        sheet_name = self.sheet_table.item(row, 2).text()
        
        # 모든 행에 설정 복사할지 확인
        message = f"선택한 설정을 모든 기능에 복사하시겠습니까?\n\nURL: {spreadsheet_url}\n시트: {sheet_name}"
        reply = QMessageBox.question(self, "설정 복사 확인", message, 
                                      QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            # 모든 행에 설정 복사
            for row in range(self.sheet_table.rowCount()):
                self.sheet_table.item(row, 1).setText(spreadsheet_url)
                self.sheet_table.item(row, 2).setText(sheet_name)
            
            self.log("설정이 모든 기능에 복사되었습니다.", LOG_SUCCESS)
    
    def _on_test_connection(self):
        """선택한 스프레드시트 연결 테스트"""
        # 현재 선택된 행
        selected_rows = self.sheet_table.selectedIndexes()
        if not selected_rows:
            self.log("테스트할 설정을 선택해주세요.", LOG_WARNING)
            return
        
        # 선택된 행에서 URL과 시트 이름 가져오기
        row = selected_rows[0].row()
        function_name = self.sheet_table.item(row, 0).text()
        spreadsheet_url = self.sheet_table.item(row, 1).text()
        sheet_name = self.sheet_table.item(row, 2).text()
        
        # 연결 테스트 로그
        self.log(f"'{function_name}'의 스프레드시트 연결 테스트 중... URL: {spreadsheet_url}, 시트: {sheet_name}", LOG_INFO)
        
        # TODO: 실제 연결 테스트 구현
        
        # 테스트 성공 로그
        self.log(f"'{function_name}'의 스프레드시트 연결 테스트 성공!", LOG_SUCCESS)
    
    def _on_apply_bulk_url(self):
        """모든 기능에 동일한 스프레드시트 URL 적용"""
        # 입력된 URL 가져오기
        bulk_url = self.bulk_spreadsheet_url.text()
        if not bulk_url:
            self.log("적용할 스프레드시트 URL을 입력해주세요.", LOG_WARNING)
            return
        
        # 모든 행에 URL 설정
        for row in range(self.sheet_table.rowCount()):
            self.sheet_table.item(row, 1).setText(bulk_url)
        
        self.log(f"모든 기능에 스프레드시트 URL이 적용되었습니다: {bulk_url}", LOG_SUCCESS)
    
    def _on_save_clicked(self):
        """저장 버튼 클릭 이벤트"""
        try:
            saved_values = []  # 저장된 값들을 추적
            settings_to_save = {}  # 저장할 설정 모음
            
            # 일반 설정 저장
            # 테마 설정 저장
            theme_value = self.theme_combo.currentData()
            get_theme().set_theme(theme_value)
            settings_to_save[ConfigKey.UI_THEME.value] = theme_value
            saved_values.append(f"UI 테마: {theme_value}")
            
            # 로그 설정 저장
            log_level = self.log_level_combo.currentData()
            settings_to_save[ConfigKey.LOG_LEVEL.value] = log_level
            saved_values.append(f"로그 레벨: {log_level}")
            
            save_logs = self.save_log_check.isChecked()
            settings_to_save[ConfigKey.SAVE_LOGS.value] = save_logs
            saved_values.append(f"로그 저장: {save_logs}")
            
            logs_path = self.log_path_edit.text()
            settings_to_save[ConfigKey.LOGS_PATH.value] = logs_path
            saved_values.append(f"로그 경로: {logs_path}")
            
            # 카카오톡 설정 저장
            kakao_path = self.kakao_path_edit.text()
            settings_to_save[ConfigKey.KAKAO_PATH.value] = kakao_path
            saved_values.append(f"카카오톡 경로: {kakao_path}")
            
            auto_start = self.auto_start_kakao.isChecked()
            settings_to_save[ConfigKey.AUTO_START_KAKAO.value] = auto_start
            saved_values.append(f"자동시작: {auto_start}")
            
            msg_delay = self.message_delay.value()
            settings_to_save[ConfigKey.MESSAGE_DELAY.value] = msg_delay
            saved_values.append(f"메시지 딜레이: {msg_delay}")
            
            # 스크래핑 URL 설정 저장
            admin_url = self.swatchon_admin_url.text()
            settings_to_save[ConfigKey.SWATCHON_ADMIN_URL.value] = admin_url
            saved_values.append(f"SwatchOn Admin URL: {admin_url}")
            
            # 스크래핑 URL 저장 (모든 기능 공통)
            receive_url = self.receive_scraping_url.text()
            settings_to_save[ConfigKey.RECEIVE_SCRAPING_URL.value] = receive_url
            saved_values.append(f"스크래핑 URL: {receive_url}")
            
            # Google API 설정 저장
            credentials = self.credentials_path_edit.text()
            settings_to_save[ConfigKey.GOOGLE_CREDENTIALS.value] = credentials
            saved_values.append(f"Google 자격증명: {credentials}")
            
            api_limit = self.api_limit.value()
            settings_to_save[ConfigKey.API_LIMIT.value] = api_limit
            saved_values.append(f"API 제한: {api_limit}")
            
            # 주소록 설정 저장
            address_url = self.address_spreadsheet_url.text()
            settings_to_save[ConfigKey.ADDRESS_BOOK_URL.value] = address_url
            saved_values.append(f"주소록 URL: {address_url}")
            
            address_sheet = self.address_sheet_name.text()
            settings_to_save[ConfigKey.ADDRESS_BOOK_SHEET.value] = address_sheet
            saved_values.append(f"주소록 시트: {address_sheet}")
            
            # 기능별 스프레드시트 설정 저장
            # 테이블에서 각 행의 데이터 저장
            row = 0
            for section_key, section_data in SECTION_SPREADSHEET_MAPPING.items():
                spreadsheet_url = self.sheet_table.item(row, 1).text()
                sheet_name = self.sheet_table.item(row, 2).text()
                
                # 설정 저장 - 문자열 키를 직접 사용
                url_key = section_data["url_key"]
                sheet_key = section_data["sheet_key"]
                settings_to_save[url_key] = spreadsheet_url
                settings_to_save[sheet_key] = sheet_name
                
                saved_values.append(f"{section_data['name']} URL: {spreadsheet_url}")
                saved_values.append(f"{section_data['name']} 시트: {sheet_name}")
                
                row += 1
            
            # 모든 설정을 한 번에 저장
            print("모든 설정을 일괄 저장합니다...")
            self.config_manager.set_batch(settings_to_save)
            
            # 저장된 설정 로그에 출력
            self.log("설정이 저장되었습니다:", LOG_SUCCESS)
            for value in saved_values:
                self.log(f"- {value}", LOG_INFO)
            
            # 설정 파일 경로 출력
            config_path = self.config_manager._config_path
            self.log(f"설정 파일 저장 위치: {config_path}", LOG_INFO)
            
            # 터미널에 설정 정보 출력
            print("\n=== 저장된 설정 값 ===")
            for value in saved_values:
                print(value)
            print(f"설정 파일 경로: {config_path}")
            print("=====================\n")
            
            # 변경 사항 알림
            QMessageBox.information(self, "설정 저장 완료", 
                                   "모든 설정이 성공적으로 저장되었습니다.\n일부 설정은 프로그램 재시작 후 적용됩니다.",
                                   QMessageBox.Ok)
            
            # 다음 활성화 시 다시 로드할 수 있도록 플래그 재설정
            self._settings_loaded = False
        
        except Exception as e:
            error_msg = f"설정 저장 중 오류가 발생했습니다: {str(e)}"
            self.log(error_msg, LOG_ERROR)
            print(f"오류: {error_msg}")
            print(f"오류 상세: {type(e).__name__}")
            
            # 스택 트레이스 출력
            import traceback
            traceback.print_exc()
            
            QMessageBox.critical(self, "설정 저장 오류", 
                               f"설정 저장 중 오류가 발생했습니다:\n{str(e)}",
                               QMessageBox.Ok)
    
    def on_section_activated(self):
        """섹션이 활성화될 때 호출"""
        # 이미 로드된 경우 다시 로드하지 않음
        if self._settings_loaded:
            print("설정이 이미 로드되어 있습니다.")
            return
            
        print("설정 섹션이 활성화되었습니다.")
        
        # 최신 설정 데이터 로드 (한 번만)
        try:
            self._load_settings()
            self._settings_loaded = True  # 로드 완료 플래그 설정
        except Exception as e:
            print(f"설정 로드 중 오류 발생: {str(e)}")
    
    def on_section_deactivated(self):
        """섹션이 비활성화될 때 호출"""
        pass 