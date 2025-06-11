import requests
import zipfile
import os
import hashlib

def download_file(url, dest):
    r = requests.get(url)
    with open(dest, 'wb') as f:
        f.write(r.content)

def file_hash(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        h.update(f.read())
    return h.hexdigest()

def update_components():
    # 1. 서버에서 components.json 다운로드
    r = requests.get('https://raw.githubusercontent.com/dominicwwww/swatchon_chat/main/components/components.json')
    server_components = r.json()['components']

    for comp in server_components:
        name = comp['name']
        url = comp['url']
        hash_val = comp['hash']
        local_zip = f'components/{name}.zip'
        need_update = True

        # 2. 로컬 파일이 있으면 해시 비교
        if os.path.exists(local_zip):
            if file_hash(local_zip) == hash_val:
                need_update = False

        # 3. 업데이트 필요하면 다운로드 및 교체
        if need_update:
            print(f"{name} 업데이트 중...")
            download_file(url, local_zip)
            # 압축 해제
            with zipfile.ZipFile(local_zip, 'r') as zip_ref:
                zip_ref.extractall(name)
            print(f"{name} 업데이트 완료!")

if __name__ == "__main__":
    update_components() 