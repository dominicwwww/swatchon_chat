"""
카카오톡 메시지 서비스 모듈
"""

import platform
import time
import re
from typing import Optional, Callable

import win32gui
import win32con
import win32clipboard
from win32com.client import Dispatch
from selenium.webdriver.common.keys import Keys
import sys
import multiprocessing
import faulthandler

from core.logger import get_logger
from core.exceptions import KakaoException
from core.types import LogFunction


class KakaoService:
    """카카오톡 메시지 서비스"""
    
    def __init__(self):
        """초기화"""
        self.logger = get_logger(__name__)
        self.shell = Dispatch("WScript.Shell") if platform.system() == "Windows" else None
    
    def send_message(self, chat_room_name: str, message: str) -> bool:
        """카카오톡 메시지 전송"""
        try:
            # 전송 시작 로깅
            self.logger.info(f"\n=== 카카오톡 메시지 전송 시작 ===")
            self.logger.info(f"채팅방: {chat_room_name}")
            self.logger.info(f"메시지 길이: {len(message)}")
            
            # 채팅방 열기
            self.logger.info("채팅방 열기 시도...")
            if not self.open_chatroom(chat_room_name):
                self.logger.error("채팅방을 열 수 없습니다.")
                return False
            
            # 메시지 전송
            self.logger.info("메시지 전송 시도...")
            if not self._send_text_windows(message):
                self.logger.error("메시지 전송에 실패했습니다.")
                return False
            
            # 채팅방 닫기
            self.logger.info("채팅방 닫기 시도...")
            try:
                self.close_chatroom()
            except Exception as e:
                self.logger.error(f"채팅방 닫기 실패: {str(e)}")
                # 채팅방 닫기 실패는 전체 실패로 처리하지 않음
                pass
            
            self.logger.info("=== 메시지 전송 완료 ===\n")
            return True
            
        except Exception as e:
            # 전체 프로세스 중 발생한 예외 로깅
            error_msg = f"카카오톡 메시지 전송 중 오류 발생: {str(e)}"
            self.logger.error(error_msg)
            self.logger.error(f"스택 트레이스:\n{traceback.format_exc()}")
            
            # 채팅방이 열려있는 경우 닫기 시도
            try:
                self.close_chatroom()
            except:
                pass
            
            return False
    
    def open_chatroom(self, chatroom_name: str) -> bool:
        """
        채팅방 열기
        
        Args:
            chatroom_name: 채팅방 이름
            
        Returns:
            bool: 성공 여부
        """
        # Windows 환경에서만 실행
        if platform.system() != "Windows":
            return True  # 개발 모드에서는 성공으로 처리
        
        try:
            # 카카오톡 메인 창 찾기
            try:
                hwndkakao = win32gui.FindWindow(None, "카카오톡")
            except Exception as e:
                self.logger.error(f"카카오톡 창 핸들 검색 중 치명적 오류: {str(e)}")
                with open("crash.log", "a", encoding="utf-8") as f:
                    f.write(f"[open_chatroom] 카카오톡 창 핸들 검색 중 치명적 오류: {str(e)}\n")
                return False
            if not hwndkakao:
                # "카카오톡" 대신 "KakaoTalk"로도 시도
                hwndkakao = win32gui.FindWindow(None, "KakaoTalk")
                if not hwndkakao:
                    self.logger.error("카카오톡 창을 찾을 수 없습니다.")
                    return False
            
            self.logger.info(f"카카오톡 창 찾음: {hwndkakao}")
            
            # 카카오톡 창 활성화
            win32gui.ShowWindow(hwndkakao, win32con.SW_RESTORE)
            try:
                win32gui.SetForegroundWindow(hwndkakao)
            except Exception as e:
                self.logger.warning(f"카카오톡 창 활성화 중 오류 발생 (무시됨): {str(e)}")
            
            time.sleep(0.5)  # 창 활성화 대기
            
            # 검색창 찾기 (레퍼런스 코드 방식)
            hwndkakao_edit1 = win32gui.FindWindowEx(hwndkakao, None, "EVA_ChildWindow", None)
            hwndkakao_edit2_1 = win32gui.FindWindowEx(hwndkakao_edit1, None, "EVA_Window", None)
            hwndkakao_edit2_2 = win32gui.FindWindowEx(
                hwndkakao_edit1, hwndkakao_edit2_1, "EVA_Window", None
            )
            hwndkakao_edit3 = win32gui.FindWindowEx(hwndkakao_edit2_2, None, "Edit", None)

            if not hwndkakao_edit3:
                self.logger.error("카카오톡 검색창을 찾을 수 없습니다.")
                return False

            self.logger.info(f"검색창 찾음: {hwndkakao_edit3}")

            # 검색창에 채팅방 이름 입력
            win32gui.SendMessage(hwndkakao_edit3, win32con.WM_SETTEXT, 0, chatroom_name)
            time.sleep(0.5)

            # Enter 키 전송 전에 검색창이 활성화되어 있는지 확인
            try:
                win32gui.SetForegroundWindow(hwndkakao)
            except Exception as e:
                self.logger.warning(f"카카오톡 창 활성화 중 오류 발생 (무시됨): {str(e)}")

            time.sleep(0.3)

            # Enter 키로 검색 실행
            self.shell.SendKeys("{ENTER}")
            time.sleep(0.8)  # 채팅방이 열릴 때까지 대기
            
            # 채팅방이 열렸는지 확인
            hwndMain = win32gui.FindWindow(None, chatroom_name)
            if hwndMain == 0:
                self.logger.error(f"채팅방 '{chatroom_name}'을(를) 찾을 수 없습니다.")
                return False
            
            self.logger.info(f"채팅방 찾음: {hwndMain}")
            
            # 채팅방 창 활성화
            try:
                win32gui.SetForegroundWindow(hwndMain)
            except Exception as e:
                self.logger.warning(f"채팅방 창 활성화 중 오류 발생 (무시됨): {str(e)}")
            
            time.sleep(0.5)
            
            return True
            
        except Exception as e:
            self.logger.error(f"채팅방 열기 실패: {str(e)}")
            return False
    
    def close_chatroom(self, chatroom_name: str) -> bool:
        """
        채팅방 닫기 (레퍼런스 코드 방식 사용)
        
        Args:
            chatroom_name: 채팅방 이름
            
        Returns:
            bool: 성공 여부
        """
        # Windows 환경에서만 실행
        if platform.system() != "Windows":
            return True  # 개발 모드에서는 성공으로 처리
        
        try:
            # 채팅방 창 찾기
            hwndMain = win32gui.FindWindow(None, chatroom_name)
            
            if hwndMain != 0:
                # WM_CLOSE 메시지로 채팅방만 닫기 (Alt+F4 대신)
                win32gui.PostMessage(hwndMain, win32con.WM_CLOSE, 0, 0)
                self.logger.info(f"채팅방 닫기: {chatroom_name}")
            else:
                self.logger.warning(f"닫을 채팅방을 찾을 수 없음: {chatroom_name}")
            
            return True
        except Exception as e:
            self.logger.error(f"채팅방 닫기 실패: {str(e)}")
            return False
    
    def _send_text_windows(self, chatroom_name: str, text: str) -> bool:
        try:
            # HTML 태그가 있으면 일반 텍스트로 변환
            try:
                text = self._clean_html_tags(text)
            except Exception as e:
                self.logger.error(f"HTML 태그 제거 실패: {str(e)}")
                return False

            # 채팅방 창 찾기
            try:
                hwndMain = win32gui.FindWindow(None, chatroom_name)
            except Exception as e:
                self.logger.error(f"채팅방 핸들 검색 중 치명적 오류: {str(e)}")
                with open("crash.log", "a", encoding="utf-8") as f:
                    f.write(f"[_send_text_windows] 채팅방 핸들 검색 중 치명적 오류: {str(e)}\n")
                return False
            if hwndMain == 0:
                self.logger.error(f"채팅방 '{chatroom_name}' 창을 찾을 수 없습니다.")
                return False

            # 채팅방 윈도우를 활성화 (오류 무시 처리)
            try:
                win32gui.SetForegroundWindow(hwndMain)
            except Exception as e:
                self.logger.warning(f"채팅방 활성화 중 오류 발생 (무시됨): {str(e)}")
                # 오류가 발생해도 계속 진행

            time.sleep(0.2)  # 대기 시간 조정

            # 클립보드에 텍스트 복사
            try:
                win32clipboard.OpenClipboard()
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardText(text)
                win32clipboard.CloseClipboard()
            except Exception as e:
                self.logger.error(f"클립보드 복사 실패: {str(e)}")
                with open("crash.log", "a", encoding="utf-8") as f:
                    f.write(f"[_send_text_windows] 클립보드 복사 실패: {str(e)}\n")
                return False

            time.sleep(0.2)  # 대기 시간 조정

            # Ctrl+V로 붙여넣기
            try:
                self.shell.SendKeys("^v")
            except Exception as e:
                self.logger.error(f"SendKeys(^v) 실패: {str(e)}")
                with open("crash.log", "a", encoding="utf-8") as f:
                    f.write(f"[_send_text_windows] SendKeys(^v) 실패: {str(e)}\n")
                return False
            time.sleep(0.2)  # 대기 시간 조정

            # Enter 키로 전송
            try:
                self.shell.SendKeys("{ENTER}")
            except Exception as e:
                self.logger.error(f"SendKeys(ENTER) 실패: {str(e)}")
                with open("crash.log", "a", encoding="utf-8") as f:
                    f.write(f"[_send_text_windows] SendKeys(ENTER) 실패: {str(e)}\n")
                return False
            time.sleep(0.2)  # 대기 시간 조정

            return True

        except Exception as e:
            self.logger.error(f"텍스트 전송 실패: {str(e)}")
            with open("crash.log", "a", encoding="utf-8") as f:
                f.write(f"[_send_text_windows] 텍스트 전송 실패: {str(e)}\n")
            return False
    
    def _clean_html_tags(self, text: str) -> str:
        """
        HTML 태그 제거
        
        Args:
            text: 원본 텍스트
            
        Returns:
            str: HTML 태그가 제거된 텍스트
        """
        return re.sub(r'<.*?>', '', text)
    
    def _extract_chatroom_name(self, message: str) -> str:
        """
        메시지 본문에서 채팅방 이름 추출
        
        Args:
            message: 메시지 본문
            
        Returns:
            str: 채팅방 이름 (추출 실패 시 첫 줄)
        """
        # 첫 줄에서 채팅방 이름 추출 시도
        lines = message.split('\n')
        first_line = lines[0] if lines else ""
        
        # [출고 요청-판매자명] 형태에서 판매자명 추출
        match = re.search(r'\[출고 요청-([^\]]+)\]', first_line)
        if match:
            return match.group(1)
        
        # [SwatchOn] 판매자명 형태에서 판매자명 추출
        match = re.search(r'\[SwatchOn\]\s+([^\s]+)', first_line)
        if match:
            return match.group(1)
        
        # 일반적인 경우 첫 줄의 첫 단어 사용
        words = first_line.split()
        if words:
            return words[0]
        
        return "Unknown"
    
    def send_message_to_seller(self, chat_room_name: str, message: str, log_function: Optional[Callable] = None) -> bool:
        """
        판매자에게 메시지 전송
        
        Args:
            chat_room_name: 채팅방 이름
            message: 전송할 메시지
            log_function: 로그 출력 함수
            
        Returns:
            bool: 전송 성공 여부
        """
        try:
            message = self._clean_html_tags(message)
            if platform.system() == "Windows":
                try:
                    if not self.open_chatroom(chat_room_name):
                        error_msg = f"채팅방 '{chat_room_name}' 을(를) 찾을 수 없습니다."
                        print(error_msg)
                        if log_function:
                            for line in error_msg.splitlines():
                                if line.strip():
                                    log_function(line, "error")
                        return False
                    result = self._send_text_windows(chat_room_name, message)
                    try:
                        self.close_chatroom(chat_room_name)
                    except Exception as close_error:
                        import traceback
                        error_msg = f"채팅방 닫기 실패:\n{str(close_error)}\n{traceback.format_exc()}"
                        print(error_msg)
                        if log_function:
                            for line in error_msg.splitlines():
                                if line.strip():
                                    log_function(line, "error")
                    if result:
                        if log_function:
                            for line in f"메시지가 '{chat_room_name}' 에게 성공적으로 전송되었습니다.".splitlines():
                                if line.strip():
                                    log_function(line, "success")
                    else:
                        error_msg = f"메시지 전송 실패: '{chat_room_name}'"
                        print(error_msg)
                        if log_function:
                            for line in error_msg.splitlines():
                                if line.strip():
                                    log_function(line, "error")
                    return result
                except Exception as e:
                    import traceback
                    error_msg = f"메시지 전송 중 오류 발생:\n{str(e)}\n{traceback.format_exc()}"
                    print(error_msg)
                    if log_function:
                        for line in error_msg.splitlines():
                            if line.strip():
                                log_function(line, "error")
                    return False
            else:
                if log_function:
                    for line in f"[개발 모드] '{chat_room_name}'에게 메시지를 전송합니다:".splitlines():
                        if line.strip():
                            log_function(line, "info")
                    for line in "--- 메시지 내용 시작 ---".splitlines():
                        if line.strip():
                            log_function(line, "info")
                    for line in message.splitlines():
                        if line.strip():
                            log_function(line, "info")
                    for line in "--- 메시지 내용 끝 ---".splitlines():
                        if line.strip():
                            log_function(line, "info")
                    for line in f"메시지 길이: {len(message)}자".splitlines():
                        if line.strip():
                            log_function(line, "info")
                return True
        except Exception as e:
            import traceback
            error_msg = f"카카오톡 메시지 전송 중 치명적 오류:\n{str(e)}\n{traceback.format_exc()}"
            print(error_msg)
            if log_function:
                for line in error_msg.splitlines():
                    if line.strip():
                        log_function(line, "error")
            return False 

def send_message_in_subprocess(chat_room_name, message, timeout=15):
    ctx = multiprocessing.get_context('spawn')
    result_queue = ctx.Queue()

    def target(q, chat_room_name, message):
        faulthandler.enable(open("subprocess_crash.log", "a"))
        from services.kakao.kakao_service import KakaoService
        service = KakaoService()
        try:
            res = service.send_message(chat_room_name, message)
            q.put(res)
        except Exception as e:
            q.put(False)

    p = ctx.Process(target=target, args=(result_queue, chat_room_name, message))
    p.start()
    p.join(timeout)
    if p.is_alive():
        p.terminate()
        return False  # timeout/crash
    try:
        return result_queue.get_nowait()
    except Exception:
        return False 