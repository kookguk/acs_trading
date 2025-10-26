# scripts/generate_token.py
from utils.config import load_env, request_new_token

def main(mode="vts"):
    config = load_env(mode)
    token = request_new_token(config)
    print("✅ 신규 토큰 발급 및 저장 완료.")

if __name__ == "__main__":
    main("vts")