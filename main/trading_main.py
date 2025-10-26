import time
from utils.slack_notifier import send_slack_message


def main():
    """
    시스템 트레이딩 메인 실행 테스트
    (Slack 알림, 전략 흐름, 에러 핸들링 포함)
    """
    send_slack_message("🚀 시스템 트레이딩 테스트 시작", "🤖")

    try:
        # 1️⃣ 초기화
        send_slack_message("🔑 Access Token 확인 중...")
        time.sleep(1)
        send_slack_message("✅ Access Token 정상 발급 완료")

        # 2️⃣ 전략 실행 (모멘텀 전략 예시)
        send_slack_message("📊 모멘텀 전략 계산 중...")
        time.sleep(2)
        send_slack_message("📈 매수 신호 감지: 삼성전자(005930), SK하이닉스(000660)")

        # 3️⃣ 주문 실행
        send_slack_message("💰 매수 주문 실행 중...")
        time.sleep(1)
        send_slack_message("✅ 매수 주문 완료 — 삼성전자 100주, SK하이닉스 50주")

        # 4️⃣ 로그 및 종료
        send_slack_message("💾 로그 저장 완료")
        send_slack_message("✅ 시스템 트레이딩 프로세스 정상 종료", "🎯")

    except Exception as e:
        send_slack_message(f"❌ 오류 발생: {str(e)}", "🚨")
        raise e


if __name__ == "__main__":
    main()