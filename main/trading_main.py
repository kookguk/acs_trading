import os
import logging
from datetime import datetime
from dotenv import load_dotenv

from risk.risk_module import RiskManager
from utils.logger import setup_logger
from utils.config import get_access_token
from strategies.momentum_strategy import MomentumStrategy

def main():
    load_dotenv()

    setup_logger()
    logger = logging.getLogger(__name__)
    logger.info("🚀 메인 실행 시작 (모멘텀 전략)")

    try:
        # === 환경 변수 ===
        base_url = os.getenv("BASE_URL")
        app_key = os.getenv("APP_KEY")
        app_secret = os.getenv("APP_SECRET")
        cano = os.getenv("CANO")

        if not all([base_url, app_key, app_secret, cano]):
            raise EnvironmentError("환경변수(BASE_URL, APP_KEY, APP_SECRET, CANO)가 설정되지 않았습니다.")

        config = {
            "base_url": base_url,
            "app_key": app_key,
            "app_secret": app_secret,
            "cano": cano,
        }

        # === 토큰 발급 ===
        token = get_access_token(config)
        if not token:
            raise ValueError("ACCESS_TOKEN 발급 실패")

        logger.info("✅ 토큰 발급 성공")

        # === 리스크 매니저 ===
        risk_manager = RiskManager(config, token)

        # === 전략 실행 ===
        strategy = MomentumStrategy(config, token)
        results = strategy.run()

        # === 리스크 계산 ===
        if results and "returns" in results:
            metrics = risk_manager.calculate_risk_metrics(results["returns"])
            logger.info(f"리스크 메트릭: {metrics}")
        else:
            logger.warning("전략 결과에 수익률 데이터가 없음.")

    except Exception as e:
        logger.error(f"❌ 메인 실행 중 오류 발생: {e}")
        try:
            from risk.risk_module import RiskManager
            rm = RiskManager({}, "")
            rm.send_slack_alert(f"❌ 메인 실행 오류: {e}")
        except Exception:
            pass

    finally:
        logger.info("🏁 메인 실행 종료")

if __name__ == "__main__":
    main()
