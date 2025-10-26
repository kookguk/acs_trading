import os
import time
import pandas as pd
from datetime import datetime
from utils.config import load_env, get_access_token
from utils.logger import log_info, log_error
from utils.slack_notifier import send_slack_message
from strategies.momentum_strategy import MomentumStrategy
from risk.risk_module import RiskManager
from backtest.update_backtest import PortfolioUpdater
from utils.data_handler import get_daily_price
import json, requests


def place_order(config, token, code, qty, side):
    """매수/매도 주문"""
    url = f"{config['BASE_URL']}/uapi/domestic-stock/v1/trading/order-cash"
    tr_id = "VTTC0802U" if "vts" in config["BASE_URL"] else ("TTTC0802U" if side == "BUY" else "TTTC0801U")
    headers = {
        "authorization": f"Bearer {token}",
        "appkey": config["APP_KEY"],
        "appsecret": config["APP_SECRET"],
        "tr_id": tr_id,
        "content-type": "application/json",
    }
    data = {
        "CANO": config["CANO"],
        "ACNT_PRDT_CD": config["ACNT_PRDT_CD"],
        "PDNO": code,
        "ORD_DVSN": "01",
        "ORD_QTY": str(qty),
        "ORD_UNPR": "0",
    }
    res = requests.post(url, headers=headers, data=json.dumps(data))
    return res.json()


def main():
    send_slack_message("🚀 시스템 트레이딩 시작 (모의투자)", "🤖")
    log_info("🚀 시스템 트레이딩 시작")

    try:
        # 1️⃣ 환경 로드 및 토큰 발급
        config = load_env(mode="vts")
        token = get_access_token(config)
        send_slack_message("🔑 Access Token 발급 완료")

        # 2️⃣ 포트폴리오 업데이트 + 백테스트 (일요일 자동 실행)
        if datetime.now().weekday() == 6:  # 일요일
            updater = PortfolioUpdater(mode="vts")
            updater.run()

        # 3️⃣ 모멘텀 전략 실행
        strategy = MomentumStrategy(mode="vts")
        df_signals = strategy.run()
        send_slack_message("📊 모멘텀 전략 완료")

        # 4️⃣ 리스크 모듈 적용 (실제 계좌금액 기반)
        risk_manager = RiskManager(config, token)
        filtered_stocks = risk_manager.apply_risk_filter(df_signals)
        send_slack_message(f"🧮 리스크 통과 종목: {filtered_stocks}")

        # 5️⃣ 매매 실행
        per_stock_invest = risk_manager.portfolio_value * 0.1
        for code in filtered_stocks:
            df = get_daily_price(code, mode="vts", count=1)
            if df.empty:
                continue
            price = df["stck_clpr"].iloc[-1]
            qty = max(int(per_stock_invest // price), 1)
            result = place_order(config, token, code, qty, "BUY")
            send_slack_message(f"🟢 {code} 매수 {qty}주 — {result.get('msg1', '응답 없음')}")
            log_info(f"{code} 매수 완료 ({qty}주)")

            time.sleep(1.0)

        send_slack_message("✅ 모든 거래 완료 — 트레이딩 종료")
        log_info("✅ 모든 거래 완료 — 트레이딩 종료")

    except Exception as e:
        send_slack_message(f"❌ 오류 발생: {str(e)}", "🚨")
        log_error(f"❌ 오류 발생: {str(e)}")
        raise e


if __name__ == "__main__":
    main()