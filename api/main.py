from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests
import json
from typing import Dict, List
import os

app = FastAPI(title="Swatchon Chat Update Server")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GitHub 설정
GITHUB_REPO = os.getenv("GITHUB_REPO", "your-username/your-repo")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "your-token")
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}"

@app.get("/version")
async def get_version():
    """최신 버전 정보를 반환합니다."""
    try:
        headers = {"Authorization": f"token {GITHUB_TOKEN}"}
        response = requests.get(
            f"{GITHUB_API_URL}/releases/latest",
            headers=headers
        )
        if response.status_code == 200:
            return response.json()
        raise HTTPException(status_code=404, detail="버전 정보를 찾을 수 없습니다.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/components")
async def get_components():
    """구성 요소 목록을 반환합니다."""
    try:
        headers = {"Authorization": f"token {GITHUB_TOKEN}"}
        response = requests.get(
            f"{GITHUB_API_URL}/contents/components/components.json",
            headers=headers
        )
        if response.status_code == 200:
            content = response.json()["content"]
            import base64
            decoded = base64.b64decode(content).decode()
            return json.loads(decoded)
        raise HTTPException(status_code=404, detail="구성 요소 정보를 찾을 수 없습니다.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/components/{component_name}")
async def get_component(component_name: str):
    """특정 구성 요소의 다운로드 URL을 반환합니다."""
    try:
        components = await get_components()
        component = next((c for c in components["components"] if c["name"] == component_name), None)
        if not component:
            raise HTTPException(status_code=404, detail="구성 요소를 찾을 수 없습니다.")
        
        # GitHub Releases에서 해당 구성 요소의 다운로드 URL 찾기
        headers = {"Authorization": f"token {GITHUB_TOKEN}"}
        response = requests.get(
            f"{GITHUB_API_URL}/releases/latest",
            headers=headers
        )
        if response.status_code == 200:
            release = response.json()
            asset = next((a for a in release["assets"] if a["name"] == f"{component_name}.zip"), None)
            if asset:
                return {"download_url": asset["browser_download_url"]}
        raise HTTPException(status_code=404, detail="구성 요소 다운로드 URL을 찾을 수 없습니다.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 