import time
from utils.slack_notifier import send_slack_message
from utils.logger import log_info, log_error
from utils.config import load_env, get_access_token
from strategies.momentum_strategy import MomentumStrategy
from risk.risk_module import RiskManager


def main():
    """일일 자동매매 실행"""
    send_slack_message("🚀 일일 자동매매 시작 (모의투자)", "🤖")
    log_info("🚀 일일 자동매매 시작")

    try:
        # 1️⃣ 환경 설정 + 토큰 발급
        config = load_env(mode="vts")
        token = get_access_token(config)
        config["ACCESS_TOKEN"] = token
        log_info("✅ Access Token 발급 완료")

        # 2️⃣ 전략 실행
        strategy = MomentumStrategy(mode="vts")
        df_signals = strategy.run()
        send_slack_message("📊 모멘텀 전략 완료")

        # 3️⃣ 리스크 평가
        risk_manager = RiskManager(config)
        filtered_stocks = risk_manager.apply_risk_filter(df_signals)
        log_info(f"🧮 리스크 통과 종목: {filtered_stocks}")
        send_slack_message(f"🧮 리스크 통과 종목: {filtered_stocks}")

        # 4️⃣ 주문 실행 (샘플)
        if not filtered_stocks:
            log_info("⚠️ 리스크 통과 종목 없음 — 매매 생략")
            send_slack_message("⚠️ 리스크 통과 종목 없음 — 매매 생략")
        else:
            log_info(f"💰 투자 가능 종목: {filtered_stocks}")
            send_slack_message(f"💰 매매 예정 종목: {filtered_stocks}")

        send_slack_message("✅ 일일 자동매매 종료", "🎯")
        log_info("✅ 일일 자동매매 종료")

    except Exception as e:
        send_slack_message(f"❌ 오류 발생: {e}", "🚨")
        log_error(f"❌ 오류 발생: {e}")
        raise e


if __name__ == "__main__":
    main()