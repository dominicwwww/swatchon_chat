import os
import sys
import json
from pathlib import Path

# 프로젝트 루트 디렉토리를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from core.updater import Updater
from ui.update_dialog import UpdateDialog
from PySide6.QtWidgets import QApplication

def test_local_update():
    """로컬 업데이트 테스트"""
    print("로컬 업데이트 테스트 시작...")
    
    # 테스트용 버전 정보
    current_version = "1.0.0"
    update_url = "https://your-vercel-deployment-url.vercel.app"  # 실제 배포된 Vercel 서버 URL
    
    # Updater 인스턴스 생성
    updater = Updater(current_version, update_url)
    
    # 업데이트 확인
    latest_info = updater.check_for_updates()
    if latest_info:
        print(f"새로운 버전 발견: {latest_info['tag_name']}")
        print(f"업데이트 내용: {latest_info.get('body', '내용 없음')}")
        
        # 구성 요소 업데이트 확인
        components = updater.check_component_updates()
        if components:
            print("\n업데이트가 필요한 구성 요소:")
            for comp in components:
                print(f"- {comp['name']} (버전: {comp['version']})")
            
            # 업데이트 다운로드 테스트
            for comp in components:
                print(f"\n{comp['name']} 다운로드 중...")
                if updater.download_component(comp):
                    print(f"{comp['name']} 다운로드 성공")
                else:
                    print(f"{comp['name']} 다운로드 실패")
        else:
            print("업데이트가 필요한 구성 요소가 없습니다.")
    else:
        print("이미 최신 버전입니다.")

def test_ui_update():
    """UI 업데이트 테스트"""
    app = QApplication(sys.argv)
    
    # 테스트용 버전 정보
    current_version = "1.0.0"
    update_url = "https://your-vercel-deployment-url.vercel.app"  # 실제 배포된 Vercel 서버 URL
    
    # Updater 인스턴스 생성
    updater = Updater(current_version, update_url)
    
    # 업데이트 다이얼로그 생성
    dialog = UpdateDialog()
    dialog.check_updates(updater)
    dialog.show()
    
    return app.exec()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--ui":
        sys.exit(test_ui_update())
    else:
        test_local_update() 