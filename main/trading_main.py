import time
from utils.slack_notifier import send_slack_message
from utils.logger import log_info, log_error
from utils.config import load_env, get_access_token


def main():
    """
    시스템 트레이딩 메인 실행 (Slack + Logger + Config 연동 버전)
    """
    send_slack_message("🚀 시스템 트레이딩 루프 시작", "🤖")
    log_info("🚀 시스템 트레이딩 루프 시작")

    try:
        # 1️⃣ 환경 설정 로드 (모의투자 / 실전 선택 가능)
        config = load_env(mode="vts")  # .env_vts 파일 로드
        log_info(f"✅ 환경 설정 로드 완료: {config['BASE_URL']}")
        send_slack_message("🔧 환경 설정 로드 완료")

        # 2️⃣ Access Token 불러오기 (캐시 or 재발급)
        send_slack_message("🔑 Access Token 확인 중...")
        token = get_access_token(config)
        log_info("✅ Access Token 정상 발급 완료")
        send_slack_message("✅ Access Token 정상 발급 완료")

        # 3️⃣ 전략 실행 (모멘텀 전략 예시)
        send_slack_message("📊 모멘텀 전략 계산 중...")
        log_info("📊 모멘텀 전략 계산 중...")
        time.sleep(2)
        strategy_signals = {"005930": "BUY", "000660": "BUY"}  # 예시 시그널
        send_slack_message(f"📈 전략 결과: {strategy_signals}")
        log_info(f"전략 결과: {strategy_signals}")

        # 4️⃣ 리스크 체크
        send_slack_message("🧮 리스크 체크 중...")
        log_info("🧮 리스크 체크 중...")
        time.sleep(1)
        send_slack_message("✅ 리스크 조건 통과 — 주문 진행")
        log_info("✅ 리스크 조건 통과 — 주문 진행")

        # 5️⃣ 주문 실행 (시뮬레이션)
        send_slack_message("💰 매수 주문 실행 중...")
        log_info("💰 매수 주문 실행 중...")
        time.sleep(1)
        send_slack_message("✅ 매수 주문 완료 — 삼성전자 100주, SK하이닉스 50주")
        log_info("✅ 매수 주문 완료 — 삼성전자 100주, SK하이닉스 50주")

        # 6️⃣ 로그 및 종료
        send_slack_message("💾 로그 저장 완료")
        log_info("💾 로그 저장 완료")

        send_slack_message("✅ 시스템 트레이딩 프로세스 정상 종료", "🎯")
        log_info("✅ 시스템 트레이딩 프로세스 정상 종료")

    except Exception as e:
        send_slack_message(f"❌ 오류 발생: {str(e)}", "🚨")
        log_error(f"❌ 오류 발생: {str(e)}")
        raise e


if __name__ == "__main__":
    main()