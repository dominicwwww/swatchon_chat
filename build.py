import PyInstaller.__main__
import json
import os

def build():
    # 버전 정보 읽기
    with open('version.json', 'r') as f:
        version_info = json.load(f)
    
    # PyInstaller 옵션 설정
    options = [
        'main.py',  # 메인 스크립트
        '--name=SwatchonChat',  # 실행 파일 이름
        '--onefile',  # 단일 실행 파일로 생성
        '--noconsole',  # 콘솔 창 숨기기
        '--icon=resources/swatchon.ico',  # 아이콘 (있는 경우)
        '--add-data=version.json;.',  # 버전 정보 파일 포함
        '--add-data=config.json;.',  # 설정 파일 포함
        '--add-data=resources;resources',  # 리소스 폴더 포함
        '--version-file=version.txt',  # 버전 정보 파일
    ]
    
    # 버전 정보 파일 생성
    with open('version.txt', 'w') as f:
        f.write(f"""
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({version_info['version'].replace('.', ', ')}, 0),
    prodvers=({version_info['version'].replace('.', ', ')}, 0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        u'040904B0',
        [StringStruct(u'CompanyName', u'Your Company'),
         StringStruct(u'FileDescription', u'Swatchon Chat Application'),
         StringStruct(u'FileVersion', u'{version_info['version']}'),
         StringStruct(u'InternalName', u'SwatchonChat'),
         StringStruct(u'LegalCopyright', u'Copyright (c) 2024'),
         StringStruct(u'OriginalFilename', u'SwatchonChat.exe'),
         StringStruct(u'ProductName', u'Swatchon Chat'),
         StringStruct(u'ProductVersion', u'{version_info['version']}')])
    ]),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
""")
    
    # PyInstaller 실행
    PyInstaller.__main__.run(options)

if __name__ == '__main__':
    build() 