"""
SwatchOn Partner Hub 애플리케이션 메인 진입점
"""
import sys
import atexit
import os
import signal
import psutil
import traceback
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

def global_excepthook(exctype, value, tb):
    """전역 예외 핸들러"""
    print("\n=== 전역 예외 발생 ===")
    print("타입:", exctype)
    print("값:", value)
    traceback.print_exception(exctype, value, tb)
    print("===================\n")
    
    # 예외 발생 시에도 앱이 종료되지 않도록
    if QApplication.instance():
        QApplication.instance().processEvents()

# 전역 예외 핸들러 등록
sys.excepthook = global_excepthook

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
    try:
        # 설정 파일 경로 로깅
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
        print(f"설정 파일 경로 설정: {config_path}")
        
        # QApplication 인스턴스 생성
        app = QApplication(sys.argv)
        app.setApplicationName("SwatchOn Partner Hub")
        app.setOrganizationName("SwatchOn")
        
        # 마지막 윈도우가 닫혀도 앱이 종료되지 않도록 설정
        app.setQuitOnLastWindowClosed(False)
        
        # 프로세스 정리 함수 등록 (Qt 종료 신호와 연결)
        app.aboutToQuit.connect(cleanup_chrome_processes)
        
        # 테마 초기화
        theme = get_theme()
        app.setPalette(theme.create_palette())
        app.setStyleSheet(theme.get_stylesheet())
        
        # 메인 윈도우 생성 및 표시
        window = MainWindow()
        window.show()
        
        # 주기적으로 이벤트 루프 체크 (앱이 멈추지 않도록)
        def check_app_state():
            if not QApplication.instance():
                print("\n=== QApplication 인스턴스가 없음 ===")
                print("앱이 비정상적으로 종료되었을 수 있습니다.")
                print("=" * 50)
                return
            QTimer.singleShot(1000, check_app_state)  # 1초마다 체크
        
        # 앱 상태 체크 시작
        QTimer.singleShot(1000, check_app_state)
        
        # 애플리케이션 이벤트 루프 실행
        return app.exec()
    except Exception as e:
        print("\n=== 메인 함수에서 예외 발생 ===")
        print("타입:", type(e))
        print("값:", e)
        traceback.print_exc()
        print("=============================\n")
        return 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print("\n=== 메인 진입점에서 예외 발생 ===")
        print("타입:", type(e))
        print("값:", e)
        traceback.print_exc()
        print("================================\n")
        sys.exit(1) 