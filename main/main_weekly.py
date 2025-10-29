from utils.slack_notifier import send_slack_message
from utils.logger import log_info, log_error
from utils.config import load_env, get_access_token
from backtest.update_backtest import PortfolioUpdater


def main():
    """주간 종목 업데이트 + 백테스트"""
    send_slack_message("📅 주간 종목 업데이트 및 백테스트 시작", "🧠")
    log_info("📅 주간 종목 업데이트 및 백테스트 시작")

    try:
        config = load_env(mode="vts")
        token = get_access_token(config)
        config["ACCESS_TOKEN"] = token
        log_info("✅ Access Token 발급 완료")

        updater = PortfolioUpdater(mode="vts")
        updater.run()

        send_slack_message("✅ 주간 백테스트 및 종목 업데이트 완료", "🎯")
        log_info("✅ 주간 백테스트 및 종목 업데이트 완료")

    except Exception as e:
        send_slack_message(f"❌ 오류 발생: {e}", "🚨")
        log_error(f"❌ 오류 발생: {e}")
        raise e


if __name__ == "__main__":
    main()