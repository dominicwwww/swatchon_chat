from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, 
                             QLabel, QProgressBar, QPushButton, QTextEdit)
from PySide6.QtCore import Qt, Signal, QThread
from core.updater import Updater
import json

class UpdateWorker(QThread):
    progress = Signal(int)
    status = Signal(str)
    finished = Signal(bool)
    
    def __init__(self, updater: Updater, components: list):
        super().__init__()
        self.updater = updater
        self.components = components
        
    def run(self):
        try:
            total = len(self.components)
            for i, component in enumerate(self.components):
                self.status.emit(f"{component['name']} 업데이트 중...")
                if self.updater.download_component(component):
                    self.progress.emit(int((i + 1) / total * 100))
                else:
                    self.status.emit(f"{component['name']} 업데이트 실패")
                    self.finished.emit(False)
                    return
            self.status.emit("업데이트 완료")
            self.finished.emit(True)
        except Exception as e:
            self.status.emit(f"오류 발생: {str(e)}")
            self.finished.emit(False)

class UpdateDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("업데이트")
        self.setMinimumWidth(400)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # 상태 표시
        self.status_label = QLabel("업데이트 확인 중...")
        layout.addWidget(self.status_label)
        
        # 진행 상태
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        layout.addWidget(self.progress_bar)
        
        # 업데이트 내용
        self.changes_text = QTextEdit()
        self.changes_text.setReadOnly(True)
        self.changes_text.setMaximumHeight(150)
        layout.addWidget(self.changes_text)
        
        # 버튼
        button_layout = QHBoxLayout()
        self.update_button = QPushButton("업데이트")
        self.update_button.clicked.connect(self.start_update)
        self.cancel_button = QPushButton("취소")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.update_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
    def check_updates(self, updater: Updater):
        """업데이트 확인"""
        self.updater = updater
        try:
            # 버전 정보 확인
            latest_info = updater.check_for_updates()
            if latest_info:
                self.status_label.setText(f"새로운 버전 {latest_info['tag_name']}이(가) 있습니다.")
                self.changes_text.setText(latest_info.get('body', '업데이트 내용이 없습니다.'))
                self.update_button.setEnabled(True)
            else:
                self.status_label.setText("이미 최신 버전입니다.")
                self.update_button.setEnabled(False)
        except Exception as e:
            self.status_label.setText(f"업데이트 확인 중 오류 발생: {str(e)}")
            self.update_button.setEnabled(False)
            
    def start_update(self):
        """업데이트 시작"""
        try:
            components = self.updater.check_component_updates()
            if not components:
                self.status_label.setText("업데이트할 구성 요소가 없습니다.")
                return
                
            self.update_button.setEnabled(False)
            self.cancel_button.setEnabled(False)
            
            # 업데이트 작업 시작
            self.worker = UpdateWorker(self.updater, components)
            self.worker.progress.connect(self.progress_bar.setValue)
            self.worker.status.connect(self.status_label.setText)
            self.worker.finished.connect(self.update_finished)
            self.worker.start()
            
        except Exception as e:
            self.status_label.setText(f"업데이트 시작 중 오류 발생: {str(e)}")
            self.update_button.setEnabled(True)
            self.cancel_button.setEnabled(True)
            
    def update_finished(self, success: bool):
        """업데이트 완료 처리"""
        self.update_button.setEnabled(True)
        self.cancel_button.setEnabled(True)
        if success:
            self.accept()
        else:
            self.status_label.setText("업데이트 실패") 