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
            log_function(f"--- 메시지 내용 ---\n{message}\n-------------------")
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
                self.logger.error("카카오톡 창을 찾을 수 없습니다.")
                return False
            
            # 카카오톡 창 활성화
            win32gui.ShowWindow(hwndkakao, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwndkakao)
            
            # 검색창 찾기
            hwndkakao_edit1 = win32gui.FindWindowEx(hwndkakao, None, "Edit", None)
            hwndkakao_edit2 = win32gui.FindWindowEx(hwndkakao, hwndkakao_edit1, "Edit", None)
            hwndkakao_edit3 = win32gui.FindWindowEx(hwndkakao, hwndkakao_edit2, "Edit", None)
            
            # 검색창에 채팅방 이름 입력
            win32gui.SendMessage(hwndkakao_edit3, win32con.WM_SETTEXT, 0, chatroom_name)
            
            # Enter 키 전송
            self.shell.SendKeys("{ENTER}")
            
            # 채팅방이 열릴 때까지 대기
            time.sleep(1)
            
            # 채팅방 찾기 시도
            hwndMain = win32gui.FindWindow(None, chatroom_name)
            
            # 채팅방을 찾을 수 없는 경우
            if hwndMain == 0:
                self.logger.error(f"채팅방 '{chatroom_name}'을(를) 찾을 수 없습니다.")
                return False
            
            return True
        except Exception as e:
            self.logger.error(f"채팅방 열기 실패: {str(e)}")
            return False
    
    def close_chatroom(self, chatroom_name: str) -> bool:
        """
        채팅방 닫기
        
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
            
            # Alt+F4 키 전송하여 창 닫기
            win32gui.SetForegroundWindow(hwndMain)
            self.shell.SendKeys("%{F4}")
            
            return True
        except Exception as e:
            self.logger.error(f"채팅방 닫기 실패: {str(e)}")
            return False
    
    def _send_text_windows(self, chatroom_name: str, text: str) -> bool:
        """
        Windows 환경에서 텍스트 전송
        
        Args:
            chatroom_name: 채팅방 이름
            text: 전송할 텍스트
            
        Returns:
            bool: 성공 여부
        """
        try:
            # 채팅방 창 찾기
            hwndMain = win32gui.FindWindow(None, chatroom_name)
            
            # 채팅방 창 활성화
            win32gui.SetForegroundWindow(hwndMain)
            
            # 클립보드에 텍스트 복사
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardText(text)
            win32clipboard.CloseClipboard()
            
            # Ctrl+V로 붙여넣기
            self.shell.SendKeys("^v")
            
            # 잠시 대기
            time.sleep(0.5)
            
            # Enter 키로 전송
            self.shell.SendKeys("{ENTER}")
            
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
        
        # [SwatchOn] 판매자명 형태에서 판매자명 추출
        match = re.search(r'\[SwatchOn\]\s+([^\s]+)', first_line)
        if match:
            return match.group(1)
        
        # 일반적인 경우 첫 줄의 첫 단어 사용
        words = first_line.split()
        if words:
            return words[0]
        
        return "Unknown" 