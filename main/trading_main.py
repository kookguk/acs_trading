import time
from utils.slack_notifier import send_slack_message
from utils.logger import log_info, log_error
from utils.config import load_env, get_access_token
from strategies.momentum_strategy import MomentumStrategy
from risk.risk_module import RiskManager
from backtest.update_backtest import PortfolioUpdater


def main():
    """
    시스템 트레이딩 메인 실행 (Slack + Logger + Config + 실전 리스크 반영)
    """
    send_slack_message("🚀 시스템 트레이딩 시작 (모의투자)", "🤖")
    log_info("🚀 시스템 트레이딩 시작")

    try:
        # 1️⃣ 환경 설정 로드 (모의투자)
        config = load_env(mode="vts")
        log_info(f"✅ 환경 설정 로드 완료: {config['BASE_URL']}")
        send_slack_message("🔧 환경 설정 로드 완료")

        # 2️⃣ Access Token 불러오기
        send_slack_message("🔑 Access Token 발급 중...")
        token = get_access_token(config)
        config["ACCESS_TOKEN"] = token  # ✅ RiskManager와 연동을 위해 config에 추가
        log_info("✅ Access Token 정상 발급 완료")
        send_slack_message("✅ Access Token 정상 발급 완료")

        # 3️⃣ 종목 업데이트 + 백테스트
        updater = PortfolioUpdater(mode="vts")
        updater.run()  # 자동 교체 및 백테스트
        send_slack_message("✅ 주간 포트폴리오 업데이트 완료")

        # 4️⃣ 모멘텀 전략 실행
        strategy = MomentumStrategy(mode="vts")
        df_signals = strategy.run()
        send_slack_message("📊 모멘텀 전략 완료")

        # 5️⃣ 리스크 모듈 적용
        risk_manager = RiskManager(config)
        filtered_stocks = risk_manager.apply_risk_filter(df_signals)

        send_slack_message(f"🧮 리스크 통과 종목: {filtered_stocks}")
        log_info(f"🧮 리스크 통과 종목: {filtered_stocks}")

        # 6️⃣ (선택) 매수/매도 실행 로직 (이후 확장 가능)
        if not filtered_stocks:
            send_slack_message("⚠️ 리스크 통과 종목 없음 — 매매 생략")
        else:
            log_info(f"💰 투자 가능 종목: {filtered_stocks}")

        # 7️⃣ 로그 및 종료
        send_slack_message("✅ 시스템 트레이딩 프로세스 정상 종료", "🎯")
        log_info("✅ 시스템 트레이딩 프로세스 정상 종료")

    except Exception as e:
        send_slack_message(f"❌ 오류 발생: {str(e)}", "🚨")
        log_error(f"❌ 오류 발생: {str(e)}")
        raise e


if __name__ == "__main__":
    main()
