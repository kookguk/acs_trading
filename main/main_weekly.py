import os, json, time
from utils.slack_notifier import send_slack_message
from utils.logger import log_info, log_error
from utils.config import load_env, get_access_token
from utils.data_handler import get_stock_name
from utils.order_handler import place_order
from backtest.update_backtest import PortfolioUpdater
from risk.risk_module import RiskManager


def main():
    send_slack_message("🧠 주간 종목 업데이트 및 백테스트 시작 (모의투자)")
    log_info("🧠 주간 종목 업데이트 및 백테스트 시작")

    try:
        # ✅ 환경 설정 및 토큰 발급
        config = load_env(mode="vts")
        token = get_access_token(config)
        config["ACCESS_TOKEN"] = token
        risk_manager = RiskManager(config)

        base_dir = os.path.dirname(os.path.dirname(__file__))
        current_path = os.path.join(base_dir, "utils", "stocks", "current_stocks.json")

        # ✅ 기존 보유 종목 불러오기
        with open(current_path, "r", encoding="utf-8") as f:
            old_stocks = json.load(f)["stocks"]

        old_named = [f"{s} ({get_stock_name(s)})" for s in old_stocks]
        send_slack_message(f"📁 기존 보유 종목: {old_named}")

        # ✅ 종목 업데이트 + 백테스트 실행
        updater = PortfolioUpdater(mode="vts")
        new_stocks, performance = updater.run(return_metrics=True)
        new_named = [f"{s} ({get_stock_name(s)})" for s in new_stocks]
        send_slack_message(f"📁 신규 보유 종목: {new_named}")

        # ✅ 백테스트 결과 보고
        if performance:
            send_slack_message(
                f"📊 백테스트 결과 요약:\n"
                f"- 📈 수익률: {performance['return']*100:.2f}%\n"
                f"- 📉 변동성: {performance['volatility']*100:.2f}%\n"
                f"- ⚙️ Sharpe: {performance['sharpe']:.2f}"
            )

        # ✅ 현재 잔고 확인
        portfolio_value = risk_manager.portfolio_value
        cash_balance = risk_manager.cash_balance
        send_slack_message(f"💰 현재 평가금: {portfolio_value:,.0f}원 / 💵 예수금: {cash_balance:,.0f}원")

        # ✅ 기존 종목 전량 매도
        send_slack_message("📉 기존 종목 전량 매도 시작")
        for code in old_stocks:
            try:
                result = place_order(config, token, code, qty=1, price=risk_manager.get_current_price(code), side="SELL")
                msg = (
                    f"✅ 매도 성공: {code} ({get_stock_name(code)})"
                    if result["success"]
                    else f"⚠️ 매도 실패: {code} ({get_stock_name(code)}), 사유={result['message']}"
                )
                send_slack_message(msg)
                time.sleep(1)
            except Exception as e:
                send_slack_message(f"❌ 매도 중 오류 발생: {code} → {e}")

        time.sleep(3)
        send_slack_message("✅ 기존 종목 전량 매도 완료")

        # ✅ 새 포트폴리오로 매수 (잔고의 10%씩)
        invest_per_stock = portfolio_value * 0.10
        send_slack_message(f"📈 신규 종목 매수 시작 (종목당 {invest_per_stock:,.0f}원)")

        for code in new_stocks:
            try:
                current_price = risk_manager.get_current_price(code)
                qty = int(invest_per_stock // current_price)
                if qty == 0:
                    send_slack_message(f"⚠️ {code} ({get_stock_name(code)}) → 금액 부족으로 건너뜀")
                    continue

                result = place_order(config, token, code, qty=qty, price=current_price, side="BUY")
                msg = (
                    f"✅ 매수 성공: {code} ({get_stock_name(code)}), 수량={qty}주"
                    if result["success"]
                    else f"⚠️ 매수 실패: {code} ({get_stock_name(code)}), 사유={result['message']}"
                )
                send_slack_message(msg)
                time.sleep(1)
            except Exception as e:
                send_slack_message(f"❌ 매수 중 오류 발생: {code} → {e}")

        send_slack_message("🎯 ✅ 주간 백테스트 및 종목 교체 + 매수 완료")
        log_info("✅ 주간 종목 업데이트 및 매수 완료")

    except Exception as e:
        send_slack_message(f"❌ 오류 발생: {str(e)}", "🚨")
        log_error(str(e))
        raise e


if __name__ == "__main__":
    main()