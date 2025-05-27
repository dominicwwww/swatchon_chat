"""
SwatchOn Partner Hub 애플리케이션 메인 진입점
"""
import sys
import atexit
import os
import signal
import psutil
from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow
from ui.theme import get_theme
from core.config import ConfigManager
from core.logger import get_logger

logger = get_logger(__name__)

def cleanup_chrome_processes():
    """애플리케이션 종료 시에만 실행됨 - Chrome/ChromeDriver 프로세스 정리"""
    try:
        logger.info("애플리케이션 종료 시에 실행되는 정리 작업입니다.")
        # 크롬 프로세스 검색 및 종료
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                # 프로세스 이름에 'chrome' 또는 'chromedriver'가 포함된 경우
                if proc.info['name'] and any(x in proc.info['name'].lower() for x in ['chrome', 'chromedriver']):
                    try:
                        # 이 정리 작업은 애플리케이션이 완전히 종료될 때만 실행됨
                        proc.terminate()
                        logger.info(f"브라우저 프로세스 정리: {proc.pid} ({proc.name()})")
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
                
    except Exception as e:
        logger.error(f"프로세스 정리 중 오류: {str(e)}")

# 애플리케이션 종료 시에만 프로세스 정리 함수 등록
atexit.register(cleanup_chrome_processes)

def main():
    """애플리케이션 메인 함수"""
    # 설정 파일 경로 로깅
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
    print(f"설정 파일 경로 설정: {config_path}")
    
    # QApplication 인스턴스 생성
    app = QApplication(sys.argv)
    app.setApplicationName("SwatchOn Partner Hub")
    app.setOrganizationName("SwatchOn")
    
    # 프로세스 정리 함수 등록 (Qt 종료 신호와 연결)
    app.aboutToQuit.connect(cleanup_chrome_processes)
    
    # 테마 초기화
    theme = get_theme()
    app.setPalette(theme.create_palette())
    app.setStyleSheet(theme.get_stylesheet())
    
    # 메인 윈도우 생성 및 표시
    window = MainWindow()
    window.show()
    
    # 애플리케이션 이벤트 루프 실행
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 