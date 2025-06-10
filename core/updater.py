import os
import sys
import json
import requests
import subprocess
import hashlib
from pathlib import Path
from typing import Optional, Dict, List

class Updater:
    def __init__(self, current_version: str, update_url: str, github_token: Optional[str] = None):
        self.current_version = current_version
        self.update_url = update_url
        self.version_file = "version.json"
        self.components_dir = "components"
        self.github_token = github_token
        self.headers = {"Authorization": f"token {github_token}"} if github_token else {}
        
    def check_for_updates(self) -> Optional[Dict]:
        """서버에서 최신 버전 정보를 확인합니다."""
        try:
            response = requests.get(f"{self.update_url}/version", headers=self.headers)
            if response.status_code == 200:
                latest_info = response.json()
                if self._compare_versions(latest_info["tag_name"], self.current_version):
                    return latest_info
        except Exception as e:
            print(f"업데이트 확인 중 오류 발생: {e}")
        return None

    def check_component_updates(self) -> List[Dict]:
        """업데이트가 필요한 구성 요소들을 확인합니다."""
        try:
            response = requests.get(f"{self.update_url}/components", headers=self.headers)
            if response.status_code == 200:
                server_components = response.json()["components"]
                local_components = self._get_local_components()
                
                updates_needed = []
                for comp in server_components:
                    local_comp = next((c for c in local_components if c["name"] == comp["name"]), None)
                    if not local_comp or self._compare_versions(comp["version"], local_comp["version"]):
                        updates_needed.append(comp)
                return updates_needed
        except Exception as e:
            print(f"구성 요소 업데이트 확인 중 오류 발생: {e}")
        return []

    def download_component(self, component: Dict) -> bool:
        """특정 구성 요소를 다운로드합니다."""
        try:
            # GitHub Releases에서 직접 다운로드
            response = requests.get(component["download_url"], stream=True, headers=self.headers)
            if response.status_code == 200:
                # 임시 파일로 다운로드
                temp_path = f"{component['name']}.tmp"
                with open(temp_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                
                # 해시 검증
                if self._verify_hash(temp_path, component["hash"]):
                    # 실제 파일로 이동
                    final_path = os.path.join(self.components_dir, component["name"])
                    os.makedirs(os.path.dirname(final_path), exist_ok=True)
                    os.replace(temp_path, final_path)
                    return True
                else:
                    os.remove(temp_path)
                    print(f"해시 검증 실패: {component['name']}")
        except Exception as e:
            print(f"구성 요소 다운로드 중 오류 발생: {e}")
        return False

    def _get_local_components(self) -> List[Dict]:
        """로컬 구성 요소 정보를 가져옵니다."""
        components = []
        try:
            components_file = os.path.join(self.components_dir, "components.json")
            if os.path.exists(components_file):
                with open(components_file, 'r') as f:
                    components = json.load(f)["components"]
        except Exception as e:
            print(f"로컬 구성 요소 정보 읽기 실패: {e}")
        return components

    def _verify_hash(self, file_path: str, expected_hash: str) -> bool:
        """파일의 해시값을 검증합니다."""
        try:
            sha256_hash = hashlib.sha256()
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest() == expected_hash
        except Exception as e:
            print(f"해시 검증 중 오류 발생: {e}")
            return False

    def _compare_versions(self, version1: str, version2: str) -> bool:
        """버전을 비교하여 version1이 더 새로운지 확인합니다."""
        v1_parts = [int(x) for x in version1.split('.')]
        v2_parts = [int(x) for x in version2.split('.')]
        
        for i in range(max(len(v1_parts), len(v2_parts))):
            v1 = v1_parts[i] if i < len(v1_parts) else 0
            v2 = v2_parts[i] if i < len(v2_parts) else 0
            
            if v1 > v2:
                return True
            elif v1 < v2:
                return False
        return False 