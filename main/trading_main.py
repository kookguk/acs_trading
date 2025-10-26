import time
from utils.slack_notifier import send_slack_message
from utils.config import get_access_token
from utils.logger import setup_logger

logger = setup_logger()

def main():
    """
    시스템 트레이딩 메인 실행 (Slack + 기본 흐름 통합)
    """
    send_slack_message("🚀 시스템 트레이딩 루프 시작", "🤖")
    logger.info("🚀 시스템 트레이딩 루프 시작")

    try:
        # 1️⃣ 토큰 확인
        send_slack_message("🔑 Access Token 확인 중...")
        token = get_access_token()
        logger.info("✅ Access Token 정상 발급 완료")
        send_slack_message("✅ Access Token 정상 발급 완료")

        # 2️⃣ 전략 실행 (모멘텀 예시)
        send_slack_message("📊 모멘텀 전략 계산 중...")
        logger.info("📊 모멘텀 전략 계산 중...")
        time.sleep(2)
        strategy_signals = {"005930": "BUY", "000660": "BUY"}
        send_slack_message(f"📈 전략 결과: {strategy_signals}")
        logger.info(f"전략 결과: {strategy_signals}")

        # 3️⃣ 리스크 체크 (예시)
        send_slack_message("🧮 리스크 체크 중...")
        logger.info("🧮 리스크 체크 중...")
        time.sleep(1)
        send_slack_message("✅ 리스크 조건 통과 — 주문 진행")
        logger.info("리스크 조건 통과")

        # 4️⃣ 주문 실행
        send_slack_message("💰 매수 주문 실행 중...")
        logger.info("💰 매수 주문 실행 중...")
        time.sleep(1)
        send_slack_message("✅ 매수 주문 완료 — 삼성전자 100주, SK하이닉스 50주")
        logger.info("매수 주문 완료 — 삼성전자 100주, SK하이닉스 50주")

        # 5️⃣ 로그 및 종료
        send_slack_message("💾 로그 저장 완료")
        logger.info("💾 로그 저장 완료")
        send_slack_message("✅ 시스템 트레이딩 프로세스 정상 종료", "🎯")
        logger.info("✅ 시스템 트레이딩 프로세스 정상 종료")

    except Exception as e:
        send_slack_message(f"❌ 오류 발생: {str(e)}", "🚨")
        logger.error(f"❌ 오류 발생: {str(e)}", exc_info=True)
        raise e


if __name__ == "__main__":
    main()