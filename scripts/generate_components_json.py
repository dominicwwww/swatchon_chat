import json
import hashlib
import os
import sys

def file_hash(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        h.update(f.read())
    return h.hexdigest()

def make_url(filename):
    # 실제 릴리즈 URL로 교체 필요
    return f"https://github.com/dominicwwww/swatchon_chat/releases/latest/download/{filename}"

# 워크플로에서 버전 넘버를 인자로 전달받음
generated_version = sys.argv[1] if len(sys.argv) > 1 else "1.0.0"

components = []
for folder in ['core', 'ui', 'services']:
    zip_name = f"{folder}.zip"
    components.append({
        "name": folder,
        "version": generated_version,
        "url": make_url(zip_name),
        "hash": file_hash(zip_name)
    })

os.makedirs("components", exist_ok=True)
with open("components/components.json", "w", encoding="utf-8") as f:
    json.dump({"components": components}, f, ensure_ascii=False, indent=2) 