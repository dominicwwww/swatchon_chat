"""
카카오톡 메시지 서비스 모듈
"""

import platform
import time
import re
from typing import Optional

import win32gui
import win32con
import win32clipboard
from win32com.client import Dispatch

from core.logger import get_logger
from core.exceptions import KakaoException
from core.types import LogFunction


class KakaoService:
    """카카오톡 메시지 서비스"""
    
    def __init__(self):
        """초기화"""
        self.logger = get_logger(__name__)
        self.shell = Dispatch("WScript.Shell") if platform.system() == "Windows" else None
    
    def send_message(self, message: str, log_function: Optional[LogFunction] = None) -> bool:
        """
        메시지 전송 (로그 함수를 통한 실시간 표시)
        
        Args:
            message: 전송할 메시지
            log_function: 로그 출력 함수 (None인 경우 logger.info 사용)
            
        Returns:
            bool: 전송 성공 여부
        """
        if log_function is None:
            log_function = self.logger.info

        # HTML 태그 처리
        message = self._clean_html_tags(message)

        # 메시지 본문에서 채팅방 이름 추출
        chatroom_name = self._extract_chatroom_name(message)
        
        # 윈도우에서 실제 메시지 전송
        if platform.system() == "Windows":
            # 채팅방 검색 및 열기
            if not self.open_chatroom(chatroom_name):
                log_function(f"채팅방 '{chatroom_name}' 을(를) 찾을 수 없습니다.")
                return False

            # 메시지 전송
            result = self._send_text_windows(chatroom_name, message)
            
            # 채팅방 닫기
            self.close_chatroom(chatroom_name)
            
            if result:
                log_function(f"메시지가 '{chatroom_name}' 에게 성공적으로 전송되었습니다.")
            else:
                log_function(f"메시지 전송 실패: '{chatroom_name}'")
            
            return result
        else:
            # macOS 등 Windows가 아닌 환경
            log_function(f"[개발 모드] '{chatroom_name}'에게 메시지를 전송합니다:")
            log_function(f"--- 메시지 내용 시작 ---")
            log_function(message)
            log_function(f"--- 메시지 내용 끝 ---")
            log_function(f"메시지 길이: {len(message)}자")
            return True  # 개발 모드에서는 성공으로 처리
    
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
            hwndkakao = win32gui.FindWindow(None, "카카오톡")
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
        """
        Windows 환경에서 텍스트 전송 (레퍼런스 코드 방식)
        
        Args:
            chatroom_name: 채팅방 이름
            text: 전송할 텍스트
            
        Returns:
            bool: 성공 여부
        """
        try:
            # HTML 태그가 있으면 일반 텍스트로 변환
            text = self._clean_html_tags(text)

            # 채팅방 창 찾기
            hwndMain = win32gui.FindWindow(None, chatroom_name)
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
                return False
            
            time.sleep(0.2)  # 대기 시간 조정

            # Ctrl+V로 붙여넣기
            self.shell.SendKeys("^v")
            time.sleep(0.2)  # 대기 시간 조정

            # Enter 키로 전송
            self.shell.SendKeys("{ENTER}")
            time.sleep(0.2)  # 대기 시간 조정

            return True
            
        except Exception as e:
            self.logger.error(f"텍스트 전송 실패: {str(e)}")
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
    
    def send_message_to_seller(self, seller_name: str, message: str, log_function: Optional[LogFunction] = None) -> bool:
        """
        판매자에게 메시지 전송 (판매자명 직접 지정)
        
        Args:
            seller_name: 판매자명
            message: 전송할 메시지
            log_function: 로그 출력 함수 (None인 경우 logger.info 사용)
            
        Returns:
            bool: 전송 성공 여부
        """
        if log_function is None:
            log_function = self.logger.info

        # HTML 태그 처리
        message = self._clean_html_tags(message)
        
        # 윈도우에서 실제 메시지 전송
        if platform.system() == "Windows":
            # 채팅방 검색 및 열기
            if not self.open_chatroom(seller_name):
                log_function(f"채팅방 '{seller_name}' 을(를) 찾을 수 없습니다.")
                return False

            # 메시지 전송
            result = self._send_text_windows(seller_name, message)
            
            # 채팅방 닫기
            self.close_chatroom(seller_name)
            
            if result:
                log_function(f"메시지가 '{seller_name}' 에게 성공적으로 전송되었습니다.")
            else:
                log_function(f"메시지 전송 실패: '{seller_name}'")
            
            return result
        else:
            # macOS 등 Windows가 아닌 환경
            log_function(f"[개발 모드] '{seller_name}'에게 메시지를 전송합니다:")
            log_function(f"--- 메시지 내용 시작 ---")
            log_function(message)
            log_function(f"--- 메시지 내용 끝 ---")
            log_function(f"메시지 길이: {len(message)}자")
            return True  # 개발 모드에서는 성공으로 처리 