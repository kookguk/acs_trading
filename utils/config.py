import os
import json
import requests
from dotenv import load_dotenv
from datetime import datetime, timedelta

TOKEN_FILE = "token_cache.json"

def load_env(mode="vts"):
    env_file = ".env_vts" if mode == "vts" else ".env_real"
    load_dotenv(env_file)
    config = {
        "APP_KEY": os.getenv("APP_KEY"),
        "APP_SECRET": os.getenv("APP_SECRET"),
        "CANO": os.getenv("CANO"),
        "ACNT_PRDT_CD": os.getenv("ACNT_PRDT_CD"),
        "BASE_URL": os.getenv("BASE_URL"),
    }
    return config


def save_token(token, expires_in=86400):
    expires_at = datetime.now() + timedelta(seconds=expires_in)
    data = {
        "access_token": token,
        "expires_at": expires_at.strftime("%Y-%m-%d %H:%M:%S")
    }
    with open(TOKEN_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"💾 토큰 저장 완료 (만료: {data['expires_at']})")


def load_token():
    """token_cache.json에서 토큰 불러오기 (없거나 만료 시 예외 발생)"""
    if not os.path.exists(TOKEN_FILE):
        raise FileNotFoundError("❌ token_cache.json 파일이 없습니다.")
    with open(TOKEN_FILE, "r") as f:
        data = json.load(f)
    expires_at = datetime.strptime(data["expires_at"], "%Y-%m-%d %H:%M:%S")
    if expires_at < datetime.now():
        raise ValueError("❌ 토큰이 만료되었습니다.")
    return data["access_token"]


def request_new_token(config):
    """API로 새로운 토큰 발급"""
    url = f"{config['BASE_URL']}/oauth2/tokenP"
    headers = {"content-type": "application/json"}
    data = {
        "grant_type": "client_credentials",
        "appkey": config["APP_KEY"],
        "appsecret": config["APP_SECRET"]
    }
    res = requests.post(url, headers=headers, data=json.dumps(data))
    if res.status_code != 200:
        raise ConnectionError(f"❌ 토큰 발급 실패: {res.text}")
    token = res.json().get("access_token")
    expires_in = res.json().get("expires_in", 86400)
    save_token(token, expires_in)
    return token


def get_access_token(config: dict, use_cache=True):
    """Access Token 불러오기 (만료 시 자동 갱신)"""
    if not use_cache:
        return request_new_token(config)
    try:
        token = load_token()
        return token
    except Exception as e:
        print(f"⚠️ {e} → 새 토큰 발급 중...")
        return request_new_token(config)


def make_headers(config: dict, token: str, tr_id: str):
    """API 요청용 공통 헤더 생성"""
    headers = {
        "authorization": f"Bearer {token}",
        "appkey": config["APP_KEY"],
        "appsecret": config["APP_SECRET"],
        "tr_id": tr_id
    }
    return headers