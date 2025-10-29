# main/main_daily.py
import time
from utils.slack_notifier import send_slack_message
from utils.logger import log_info, log_error
from utils.config import load_env, get_access_token
from strategies.momentum_strategy import MomentumStrategy
from risk.risk_module import RiskManager
from backtest.update_backtest import PortfolioUpdater
from utils.data_handler import get_stock_name, get_current_price
from utils.order_handler import place_order


def main():
    """
    매일 자동매매 실행 (토큰 발급 → 전략 → 리스크 → 교체 → 슬리피지 보정 지정가 주문)
    """
    send_slack_message("🤖 🚀 일일 자동매매 시작 (모의투자)")
    log_info("🚀 일일 자동매매 시작")

    try:
        # 1️⃣ 환경 설정 및 토큰
        config = load_env(mode="vts")
        token = get_access_token(config)
        config["ACCESS_TOKEN"] = token
        send_slack_message("✅ Access Token 발급 완료")

        # 2️⃣ 현재 보유 종목 로드
        updater = PortfolioUpdater(mode="vts")
        current_stocks = updater._load_current_stocks()
        current_named = [f"{s} ({get_stock_name(s)})" for s in current_stocks]
        send_slack_message(f"📁 현재 보유 종목: {current_named}")

        # 3️⃣ 모멘텀 전략 실행
        strategy = MomentumStrategy(mode="vts")
        df_signals = strategy.run()
        send_slack_message("📊 모멘텀 전략 완료")

        # 4️⃣ 리스크 및 계좌 평가금액
        risk_manager = RiskManager(config)
        portfolio_value = risk_manager.portfolio_value
        cash_balance = risk_manager.cash_balance
        send_slack_message(f"💰 계좌 평가금액: {portfolio_value:,.0f}원 / 예수금: {cash_balance:,.0f}원")

        # 5️⃣ 리스크 필터 적용
        filtered_stocks = risk_manager.apply_risk_filter(df_signals)

        # 6️⃣ 교체 로직
        sell_stocks = [s for s in current_stocks if s not in filtered_stocks]
        keep_stocks = filtered_stocks.copy()
        num_needed = 10 - len(keep_stocks)
        new_additions = []

        if num_needed > 0:
            candidate_pool = updater._load_candidates()
            exclude_list = set(current_stocks)
            candidate_pool = candidate_pool[~candidate_pool["code"].isin(exclude_list)]
            top_candidates = candidate_pool["code"].head(num_needed).tolist()
            new_additions.extend(top_candidates)
            keep_stocks.extend(new_additions)

        updater._save_current_stocks(keep_stocks)

        # ===========================
        # 🔹 슬리피지 보정 지정가 주문 실행
        # ===========================
        send_slack_message("📈 슬리피지 보정 지정가 주문 실행 시작")
        invest_per_stock = min(cash_balance / 10, 900000)

        # (1) 매도
        for code in sell_stocks:
            price = get_current_price(config, token, code)
            if not price:
                send_slack_message(f"⚠️ {code} 현재가 조회 실패 (매도)")
                continue
            result = place_order(config, token, code, qty=1, price=price, side="SELL")
            msg = f"📉 매도 주문: {code} ({get_stock_name(code)}), 지정가={price:,}원"
            send_slack_message(msg)
            time.sleep(0.3)

        # (2) 신규 매수
        for code in new_additions:
            price = get_current_price(config, token, code)
            if not price:
                send_slack_message(f"⚠️ {code} 현재가 조회 실패 (매수)")
                continue
            qty = max(int(invest_per_stock // price), 1)
            result = place_order(config, token, code, qty=qty, price=price, side="BUY")
            msg = f"📈 매수 주문: {code} ({get_stock_name(code)}), {qty}주 지정가={price:,}원"
            send_slack_message(msg)
            time.sleep(0.5)

        # (3) Slack 요약
        send_slack_message(f"📊 유지 종목: {[f'{s} ({get_stock_name(s)})' for s in filtered_stocks]}")
        send_slack_message(f"📉 매도 종목: {[f'{s} ({get_stock_name(s)})' for s in sell_stocks]}")
        send_slack_message(f"📈 신규 매수 종목: {[f'{s} ({get_stock_name(s)})' for s in new_additions]}")
        send_slack_message("🎯 ✅ 일일 자동매매 종료")

    except Exception as e:
        send_slack_message(f"❌ 오류 발생: {str(e)}", "🚨")
        log_error(f"❌ 오류 발생: {str(e)}")
        raise e


if __name__ == "__main__":
    main()
