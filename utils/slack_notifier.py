import os
import json
import requests
from dotenv import load_dotenv

load_dotenv(".env_vts")

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")

def send_slack_message(message: str, emoji: str = "📢"):
    """슬랙 채널로 텍스트 알림 전송"""
    if not SLACK_WEBHOOK_URL:
        print("❌ Slack Webhook URL이 설정되지 않았습니다.")
        return

    payload = {
        "text": f"{emoji} {message}"
    }

    try:
        res = requests.post(
            SLACK_WEBHOOK_URL,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"}
        )
        if res.status_code != 200:
            print(f"❌ Slack 전송 실패: {res.text}")
        else:
            print(f"✅ Slack 알림 전송 완료: {message}")
    except Exception as e:
        print(f"❌ Slack 전송 중 오류 발생: {e}")