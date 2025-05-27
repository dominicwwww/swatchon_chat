import platform
import re
import time

from src.utils.logger import get_logger
from src.utils.ui_utils import flush_events

logger = get_logger(__name__)

if platform.system() == "Windows":
    import win32clipboard
    import win32con
    import win32gui
    from win32com.client import Dispatch
else:
    # 더미 클래스/함수 정의 (윈도우가 아닐 때)
    win32con = type("win32con", (), {"WM_CLOSE": 0, "SW_RESTORE": 0, "WM_SETTEXT": 0})()
    win32gui = type(
        "win32gui",
        (),
        {
            "IsWindowVisible": staticmethod(lambda hwnd: False),
            "GetWindowText": staticmethod(lambda hwnd: ""),
            "EnumWindows": staticmethod(lambda cb, extra: None),
            "FindWindow": staticmethod(lambda a, b: 0),
            "SetForegroundWindow": staticmethod(lambda hwnd: None),
            "ShowWindow": staticmethod(lambda hwnd, flag: None),
            "FindWindowEx": staticmethod(lambda a, b, c, d: 0),
            "SendMessage": staticmethod(lambda hwnd, msg, w, l: None),
            "PostMessage": staticmethod(lambda hwnd, msg, w, l: None),
        },
    )
    win32clipboard = type(
        "win32clipboard",
        (),
        {
            "OpenClipboard": staticmethod(lambda: None),
            "EmptyClipboard": staticmethod(lambda: None),
            "SetClipboardText": staticmethod(lambda text: None),
            "CloseClipboard": staticmethod(lambda: None),
        },
    )
    Dispatch = lambda x: type("DummyShell", (), {"SendKeys": staticmethod(lambda keys: None)})()


class KakaoSenderClipboard:
    def __init__(self):
        self.background_mode = False
        self.shell = Dispatch("WScript.Shell")

    def set_background_mode(self, mode: bool):
        self.background_mode = mode

    def _clean_html_tags(self, text: str) -> str:
        """HTML 태그를 제거하고 링크를 일반 텍스트로 변환"""
        # <a href="URL">텍스트</a> 형식의 HTML 링크를 텍스트 URL로 변환
        a_tag_pattern = r'<a\s+href=["\'](.*?)["\'].*?>(.*?)</a>'
        text = re.sub(a_tag_pattern, r"\2 (\1)", text)

        # 나머지 HTML 태그 제거
        clean_text = re.sub(r"<.*?>", "", text)

        return clean_text

    def send_message(self, message: str, log_function=None):
        """메시지 전송 (로그 함수를 통한 실시간 표시)"""
        if log_function is None:
            log_function = logger.info

        # HTML 태그 처리
        message = self._clean_html_tags(message)

        # 메시지 본문에서 채팅방 이름 추출 (첫 줄에서 [] 안의 내용)
        first_line = message.split("\n")[0] if message else ""
        chatroom_name = ""
        extraction_method = ""

        if "[" in first_line and "]" in first_line:
            start_idx = first_line.find("[") + 1
            end_idx = first_line.find("]")
            if start_idx < end_idx:
                content = first_line[start_idx:end_idx]
                if "-" in content:
                    # [출고 요청-텍스월드] 형식에서 판매자 이름 추출
                    chatroom_name = content.split("-")[1].strip()
                    extraction_method = "출고요청-판매자 패턴"
                else:
                    # [05/21 투연텍스 출고 요청] 형식에서 판매자 이름 추출 시도
                    import re

                    seller_match = re.search(
                        r"(?:\d+/\d+\s+)?([^\d\s][^\s]+)(?:\s+출고\s+요청|\s+출고\s+확인)", content
                    )
                    if seller_match:
                        chatroom_name = seller_match.group(1).strip()
                        extraction_method = "날짜 판매자 출고요청 패턴"

        # 채팅방 이름이 추출되지 않았다면 두 번째 줄에서 추출 시도 (안녕하세요, XXX님 등의 패턴)
        if not chatroom_name and len(message.split("\n")) > 1:
            second_line = message.split("\n")[1]
            if "안녕하세요" in second_line and "님" in second_line:
                seller_match = re.search(r"안녕하세요[,!\s]+(.*?)님", second_line)
                if seller_match:
                    chatroom_name = seller_match.group(1).strip()
                    extraction_method = "안녕하세요 패턴"

        if not chatroom_name:
            error_msg = "메시지에서 채팅방 이름을 추출할 수 없습니다. 메시지 형식을 확인해주세요."
            log_function(f"❌ {error_msg}")
            log_function(f"첫 번째 줄: {first_line}")
            return False

        log_function(f"✅ 채팅방 이름 '{chatroom_name}' 추출 성공 (추출 방법: {extraction_method})")

        # 메시지 전송 과정을 실시간으로 표시
        log_function(f"📱 [{chatroom_name}] 채팅방으로 메시지 전송 시작...")
        flush_events()

        # 메시지 내용 표시
        message_lines = message.split("\n")
        log_function("📝 전송할 메시지 내용:")
        for line in message_lines:
            log_function(f"   {line}")
        flush_events()

        if platform.system() == "Windows":
            # 윈도우에서 실제 메시지 전송
            log_function(f"🔍 [{chatroom_name}] 채팅방 검색 중...")
            flush_events()

            if not self.open_chatroom_windows(chatroom_name):
                error_msg = f"[{chatroom_name}] 채팅방을 찾을 수 없습니다. 카카오톡에 해당 채팅방이 존재하는지 확인해주세요."
                log_function(f"❌ {error_msg}")
                flush_events()
                return False

            log_function(f"✅ [{chatroom_name}] 채팅방 열기 성공")
            flush_events()

            log_function("📋 메시지를 클립보드에 복사 중...")
            flush_events()

            result = self._send_text_windows(chatroom_name, message)

            if result:
                log_function(f"✅ [{chatroom_name}] 메시지 전송 완료")
            else:
                error_msg = f"[{chatroom_name}] 메시지 전송 실패 - 클립보드 복사 또는 붙여넣기 과정에서 오류가 발생했습니다."
                log_function(f"❌ {error_msg}")
                log_function(
                    "🔍 원인: 카카오톡 창을 활성화하지 못했거나, 클립보드 접근 권한이 없거나, 채팅방이 정확히 열리지 않았을 수 있습니다."
                )

            time.sleep(1)
            log_function(f"🚪 [{chatroom_name}] 채팅방 닫는 중...")
            self.close_chatroom(chatroom_name)
            log_function(f"✅ 메시지 전송 프로세스 완료")

            flush_events()
            return result
        else:
            # 맥에서는 실제 전송 대신 로그만 표시
            log_function(f"⚠️ 현재 MacOS에서는 실제 메시지 전송이 지원되지 않습니다.")
            log_function(f"🖥️ Windows에서 실행하면 실제 메시지가 전송됩니다.")
            log_function(f"✅ [{chatroom_name}] 메시지 전송 시뮬레이션 완료")
            flush_events()
            return True

    def send_text(self, chatroom_name: str, text: str) -> bool:
        # HTML 태그 처리
        text = self._clean_html_tags(text)

        if platform.system() == "Windows":
            logger.info(f"Sending message to chatroom: {chatroom_name}")

            # 먼저 채팅방 열기
            if not self.open_chatroom_windows(chatroom_name):
                logger.error(f"Failed to open chatroom: {chatroom_name}")
                return False

            # 메시지 전송
            result = self._send_text_windows(chatroom_name, text)
            if result:
                logger.info(f"Message sent successfully to {chatroom_name}")
            else:
                logger.error(f"Failed to send message to {chatroom_name}")

            time.sleep(1)  # 메시지 전송 후 잠시 대기
            self.close_chatroom(chatroom_name)
            return result
        else:
            logger.info(f"[Mock] Sending text to {chatroom_name}: {text}")
            return True

    def _send_text_windows(self, chatroom_name: str, text: str) -> bool:
        # HTML 태그가 있으면 일반 텍스트로 변환 (추가 처리)
        text = self._clean_html_tags(text)

        # 디버깅을 위한 로그 추가
        logger.info(f"Searching for chatroom with exact name: '{chatroom_name}'")

        # 현재 열려있는 모든 윈도우 핸들을 가져와서 확인
        def callback(hwnd, extra):
            if win32gui.IsWindowVisible(hwnd):
                window_text = win32gui.GetWindowText(hwnd)
                if window_text:
                    logger.info(f"Found window: '{window_text}'")

        win32gui.EnumWindows(callback, None)

        hwndMain = win32gui.FindWindow(None, chatroom_name)
        if hwndMain == 0:
            error_msg = f"채팅방을 찾을 수 없습니다: {chatroom_name}"
            logger.error(error_msg)
            if not self.background_mode:
                return False
            else:
                logger.info(f"Trying to open chatroom: {chatroom_name} in background mode")
                if not self.open_chatroom_windows(chatroom_name):
                    error_msg = f"백그라운드 모드에서 채팅방을 열 수 없습니다: {chatroom_name}"
                    logger.error(error_msg)
                    return False
                hwndMain = win32gui.FindWindow(None, chatroom_name)
                if hwndMain == 0:
                    error_msg = f"채팅방을 찾을 수 없습니다: {chatroom_name}"
                    logger.error(error_msg)
                    return False

        try:
            # 채팅방 윈도우를 활성화 (오류 무시 처리)
            try:
                win32gui.SetForegroundWindow(hwndMain)
            except Exception as e:
                logger.warning(f"채팅방 활성화 중 오류 발생 (무시됨): {str(e)}")
                # 오류가 발생해도 계속 진행

            time.sleep(0.2)  # 대기 시간 조정

            # 클립보드에 텍스트 복사
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardText(text)
            win32clipboard.CloseClipboard()
            time.sleep(0.2)  # 대기 시간 조정

            # Ctrl+V로 붙여넣기
            self.shell.SendKeys("^v")
            time.sleep(0.2)  # 대기 시간 조정

            # Enter 키로 전송
            self.shell.SendKeys("{ENTER}")
            time.sleep(0.2)  # 대기 시간 조정

            return True

        except Exception as e:
            error_msg = f"메시지 전송 중 오류 발생: {str(e)}"
            logger.error(error_msg)
            return False

    def close_chatroom(self, chatroom_name: str):
        if platform.system() == "Windows":
            hwndMain = win32gui.FindWindow(None, chatroom_name)
            if hwndMain != 0:
                win32gui.PostMessage(hwndMain, win32con.WM_CLOSE, 0, 0)
            logger.info(f"Closing chatroom: {chatroom_name}")

    def open_chatroom_windows(self, chatroom_name: str) -> bool:
        # 카카오톡 메인 창 찾기
        hwndkakao = win32gui.FindWindow(None, "카카오톡")
        if hwndkakao == 0:
            # "카카오톡" 대신 "KakaoTalk"로도 시도
            hwndkakao = win32gui.FindWindow(None, "KakaoTalk")
            if hwndkakao == 0:
                logger.error("카카오톡 창을 찾을 수 없습니다.")
                return False

        logger.info(f"카카오톡 창 찾음: {hwndkakao}")

        # 채팅방 검색 전에 카카오톡 창을 활성화 (오류 무시 처리)
        win32gui.ShowWindow(hwndkakao, win32con.SW_RESTORE)  # 최소화된 경우 복원
        try:
            win32gui.SetForegroundWindow(hwndkakao)
        except Exception as e:
            logger.warning(f"카카오톡 창 활성화 중 오류 발생 (무시됨): {str(e)}")
            # 오류가 발생해도 계속 진행

        time.sleep(0.5)  # 활성화 대기 시간 조정

        # 검색창 찾기
        hwndkakao_edit1 = win32gui.FindWindowEx(hwndkakao, None, "EVA_ChildWindow", None)
        hwndkakao_edit2_1 = win32gui.FindWindowEx(hwndkakao_edit1, None, "EVA_Window", None)
        hwndkakao_edit2_2 = win32gui.FindWindowEx(
            hwndkakao_edit1, hwndkakao_edit2_1, "EVA_Window", None
        )
        hwndkakao_edit3 = win32gui.FindWindowEx(hwndkakao_edit2_2, None, "Edit", None)

        if not hwndkakao_edit3:
            logger.error("카카오톡 검색창을 찾을 수 없습니다.")
            return False

        logger.info(f"검색창 찾음: {hwndkakao_edit3}")

        # 검색창에 채팅방 이름 입력
        win32gui.SendMessage(hwndkakao_edit3, win32con.WM_SETTEXT, 0, chatroom_name)
        time.sleep(0.5)  # 대기 시간 조정

        # Enter 키 전송 전에 검색창이 활성화되어 있는지 확인 (오류 무시 처리)
        try:
            win32gui.SetForegroundWindow(hwndkakao)
        except Exception as e:
            logger.warning(f"카카오톡 창 활성화 중 오류 발생 (무시됨): {str(e)}")
            # 오류가 발생해도 계속 진행

        time.sleep(0.3)  # 대기 시간 조정

        self.shell.SendKeys("{ENTER}")
        time.sleep(0.8)  # 채팅방이 열릴 때까지 대기 시간 조정

        # 채팅방 찾기 시도
        hwndMain = win32gui.FindWindow(None, chatroom_name)
        if hwndMain == 0:
            logger.error(f"채팅방을 찾을 수 없습니다: {chatroom_name}")
            return False

        logger.info(f"채팅방 찾음: {hwndMain}")
        return True
