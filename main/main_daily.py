import time
from utils.slack_notifier import send_slack_message
from utils.logger import log_info, log_error
from utils.config import load_env, get_access_token
from utils.data_handler import get_stock_name
from strategies.momentum_strategy import MomentumStrategy
from risk.risk_module import RiskManager
from backtest.update_backtest import PortfolioUpdater
import json
import os

def main():
    send_slack_message("🚀 일일 자동매매 시작 (모의투자)", "🤖")
    log_info("🚀 일일 자동매매 시작")

    try:
        # === 환경 설정 & 토큰 ===
        config = load_env(mode="vts")
        token = get_access_token(config)
        config["ACCESS_TOKEN"] = token
        send_slack_message("✅ Access Token 발급 완료")

        # === 현재 보유 종목 ===
        base_dir = os.path.dirname(os.path.dirname(__file__))
        with open(os.path.join(base_dir, "utils", "stocks", "current_stocks.json"), "r", encoding="utf-8") as f:
            current_stocks = json.load(f)["stocks"]

        stock_names = [f"{code} ({get_stock_name(code)})" for code in current_stocks]
        send_slack_message(f"📁 현재 보유 종목: {stock_names}")

        # === 전략 실행 ===
        strategy = MomentumStrategy(mode="vts")
        df_signals = strategy.run()
        send_slack_message("📊 모멘텀 전략 완료")

        # === 리스크 모듈 ===
        risk_manager = RiskManager(config)
        filtered_stocks = risk_manager.apply_risk_filter(df_signals)
        filtered_named = [f"{code} ({get_stock_name(code)})" for code in filtered_stocks]

        send_slack_message(f"🧮 리스크 통과 종목: {filtered_named}")

        # === 매매 분류 ===
        buy_stocks = [s for s in filtered_stocks if s not in current_stocks]
        sell_stocks = [s for s in current_stocks if s not in filtered_stocks]
        hold_stocks = [s for s in filtered_stocks if s in current_stocks]

        send_slack_message(f"💰 유지 종목: {[f'{s} ({get_stock_name(s)})' for s in hold_stocks]}")
        send_slack_message(f"📈 매수 종목: {[f'{s} ({get_stock_name(s)})' for s in buy_stocks]}")
        send_slack_message(f"📉 매도 종목: {[f'{s} ({get_stock_name(s)})' for s in sell_stocks]}")

        send_slack_message("✅ 일일 자동매매 종료", "🎯")

    except Exception as e:
        send_slack_message(f"❌ 오류 발생: {str(e)}", "🚨")
        log_error(str(e))
        raise e

if __name__ == "__main__":
    main()