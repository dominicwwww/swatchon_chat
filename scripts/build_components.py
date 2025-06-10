import os
import json
import zipfile
import hashlib
from pathlib import Path
from typing import Dict, List

class ComponentBuilder:
    def __init__(self):
        self.components_dir = Path("components")
        self.build_dir = Path("build")
        self.components_file = self.components_dir / "components.json"
        
    def build_all(self) -> Dict[str, str]:
        """모든 구성 요소를 빌드하고 해시값을 반환합니다."""
        # 빌드 디렉토리 생성
        self.build_dir.mkdir(exist_ok=True)
        
        # components.json 읽기
        with open(self.components_file, 'r', encoding='utf-8') as f:
            components_data = json.load(f)
        
        # 각 구성 요소 빌드
        hashes = {}
        for component in components_data["components"]:
            component_name = component["name"]
            component_path = Path(component["path"])
            
            if not component_path.exists():
                print(f"경고: {component_path} 경로가 존재하지 않습니다.")
                continue
                
            # ZIP 파일 생성
            zip_path = self.build_dir / f"{component_name}.zip"
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # 디렉토리 내의 모든 파일 추가
                for root, _, files in os.walk(component_path):
                    for file in files:
                        file_path = Path(root) / file
                        arcname = file_path.relative_to(component_path)
                        zipf.write(file_path, arcname)
            
            # 해시값 계산
            with open(zip_path, 'rb') as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()
                hashes[component_name] = file_hash
                
            print(f"빌드 완료: {component_name} (해시: {file_hash})")
        
        return hashes
    
    def update_components_json(self, hashes: Dict[str, str]):
        """components.json 파일을 업데이트합니다."""
        with open(self.components_file, 'r', encoding='utf-8') as f:
            components_data = json.load(f)
        
        # 해시값 업데이트
        for component in components_data["components"]:
            component_name = component["name"]
            if component_name in hashes:
                component["hash"] = hashes[component_name]
        
        # 파일 저장
        with open(self.components_file, 'w', encoding='utf-8') as f:
            json.dump(components_data, f, ensure_ascii=False, indent=4)
        
        print("components.json 업데이트 완료")

def main():
    builder = ComponentBuilder()
    hashes = builder.build_all()
    builder.update_components_json(hashes)

if __name__ == "__main__":
    main() 