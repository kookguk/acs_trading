import os, json, time
from utils.slack_notifier import send_slack_message
from utils.logger import log_info, log_error
from utils.data_handler import get_stock_name
from backtest.update_backtest import PortfolioUpdater

def main():
    send_slack_message("🧠 주간 종목 업데이트 및 백테스트 시작", "🧠")
    log_info("🧠 주간 종목 업데이트 및 백테스트 시작")

    try:
        base_dir = os.path.dirname(os.path.dirname(__file__))
        current_path = os.path.join(base_dir, "utils", "stocks", "current_stocks.json")

        with open(current_path, "r", encoding="utf-8") as f:
            old_stocks = json.load(f)["stocks"]

        old_named = [f"{s} ({get_stock_name(s)})" for s in old_stocks]
        send_slack_message(f"📁 기존 보유 종목: {old_named}")

        updater = PortfolioUpdater(mode="vts")
        new_stocks = updater.run()

        new_named = [f"{s} ({get_stock_name(s)})" for s in new_stocks]
        send_slack_message(f"📁 신규 보유 종목: {new_named}")

        # 비교
        replaced = [s for s in new_stocks if s not in old_stocks]
        retained = [s for s in new_stocks if s in old_stocks]
        removed = [s for s in old_stocks if s not in new_stocks]

        if replaced:
            send_slack_message(f"🔁 교체된 종목: {[f'{s} ({get_stock_name(s)})' for s in replaced]}")
        if removed:
            send_slack_message(f"❌ 제외된 종목: {[f'{s} ({get_stock_name(s)})' for s in removed]}")
        if retained:
            send_slack_message(f"✅ 유지 종목: {[f'{s} ({get_stock_name(s)})' for s in retained]}")

        send_slack_message("✅ 주간 백테스트 및 종목 업데이트 완료", "🎯")

    except Exception as e:
        send_slack_message(f"❌ 오류 발생: {str(e)}", "🚨")
        log_error(str(e))
        raise e

if __name__ == "__main__":
    main()