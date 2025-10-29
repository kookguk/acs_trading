import os, json, time
from utils.slack_notifier import send_slack_message
from utils.logger import log_info, log_error
from utils.data_handler import get_stock_name
from backtest.update_backtest import PortfolioUpdater


def main():
    send_slack_message("🧠 주간 종목 업데이트 및 백테스트 시작")
    log_info("🧠 주간 종목 업데이트 및 백테스트 시작")

    try:
        base_dir = os.path.dirname(os.path.dirname(__file__))
        current_path = os.path.join(base_dir, "utils", "stocks", "current_stocks.json")

        # ✅ 기존 보유 종목 불러오기
        with open(current_path, "r", encoding="utf-8") as f:
            old_stocks = json.load(f)["stocks"]

        old_named = [f"{s} ({get_stock_name(s)})" for s in old_stocks]
        send_slack_message(f"📁 기존 보유 종목: {old_named}")

        # ✅ 종목 업데이트 + 백테스트 실행
        updater = PortfolioUpdater(mode="vts")
        new_stocks, performance = updater.run(return_metrics=True)  # 🔹 run()이 지표 리턴하도록 수정 필요

        new_named = [f"{s} ({get_stock_name(s)})" for s in new_stocks]
        send_slack_message(f"📁 신규 보유 종목: {new_named}")

        # ✅ 백테스트 성과 전송
        if performance:
            send_slack_message(
                f"📊 백테스트 결과 요약:\n"
                f"- 📈 수익률: {performance['return']:.2f}%\n"
                f"- 📉 변동성: {performance['volatility']:.2f}%\n"
                f"- ⚙️ Sharpe: {performance['sharpe']:.2f}"
            )

        send_slack_message("🎯 ✅ **주간 백테스트 및 종목 업데이트 완료**")

    except Exception as e:
        send_slack_message(f"❌ 오류 발생: {str(e)}", "🚨")
        log_error(str(e))
        raise e


if __name__ == "__main__":
    main()