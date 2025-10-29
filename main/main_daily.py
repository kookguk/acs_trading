import time
from utils.slack_notifier import send_slack_message
from utils.logger import log_info, log_error
from utils.config import load_env, get_access_token
from strategies.momentum_strategy import MomentumStrategy
from risk.risk_module import RiskManager
from backtest.update_backtest import PortfolioUpdater
from utils.data_handler import get_stock_name


def main():
    """
    매일 자동매매 실행 (토큰 발급 → 전략 → 리스크 → 종목 교체 → Slack 알림)
    """
    send_slack_message("🤖 🚀 일일 자동매매 시작 (모의투자)")
    log_info("🚀 일일 자동매매 시작")

    try:
        # 1️⃣ 환경 설정 로드
        config = load_env(mode="vts")
        token = get_access_token(config)
        config["ACCESS_TOKEN"] = token
        send_slack_message("✅ Access Token 발급 완료")

        # 2️⃣ 현재 보유 종목 로드
        updater = PortfolioUpdater(mode="vts")
        current_stocks = updater._load_current_stocks()
        current_named = [f"{s} ({get_stock_name(s)})" for s in current_stocks]
        send_slack_message(f"📁 현재 보유 종목: {current_named}")

        # 3️⃣ 모멘텀 전략 실행
        strategy = MomentumStrategy(mode="vts")
        df_signals = strategy.run()
        send_slack_message("📊 모멘텀 전략 완료")

        # 4️⃣ 계좌 평가금액 확인
        risk_manager = RiskManager(config)
        portfolio_value = risk_manager.portfolio_value
        send_slack_message(f"💰 계좌 평가금액: {portfolio_value:,.0f}원")

        # 5️⃣ 리스크 모듈 적용
        filtered_stocks = risk_manager.apply_risk_filter(df_signals)
        named_filtered = [f"{s} ({get_stock_name(s)})" for s in filtered_stocks]
        send_slack_message(f"📊 리스크 통과 종목: {named_filtered}")

        # ===========================
        # 🔹 종목 교체 및 current_stocks.json 갱신
        # ===========================
        sell_stocks = [s for s in current_stocks if s not in filtered_stocks]
        keep_stocks = filtered_stocks.copy()
        num_needed = 10 - len(keep_stocks)
        new_additions = []

        if num_needed > 0:
            candidate_pool = updater._load_candidates()
            exclude_list = set(current_stocks)
            candidate_pool = candidate_pool[~candidate_pool["code"].isin(exclude_list)]
            top_candidates = candidate_pool["code"].head(num_needed).tolist()
            new_additions.extend(top_candidates)
            keep_stocks.extend(new_additions)

        # ✅ 종목 파일 업데이트
        updater._save_current_stocks(keep_stocks)

        # ===========================
        # 🔹 Slack 알림
        # ===========================
        send_slack_message(f"📊 유지 종목: {[f'{s} ({get_stock_name(s)})' for s in filtered_stocks]}")
        send_slack_message(f"📈 신규 추가 종목: {[f'{s} ({get_stock_name(s)})' for s in new_additions]}")
        send_slack_message(f"📉 매도 종목: {[f'{s} ({get_stock_name(s)})' for s in sell_stocks]}")

        # 🔹 새로운 보유 종목 리스트 알림
        new_holdings_named = [f"{s} ({get_stock_name(s)})" for s in keep_stocks]
        send_slack_message(f"💾 새로운 보유 종목 리스트: {new_holdings_named}")

        send_slack_message("🎯 ✅ 일일 자동매매 종료")
        log_info("✅ 일일 자동매매 종료")

    except Exception as e:
        send_slack_message(f"❌ 오류 발생: {str(e)}", "🚨")
        log_error(f"❌ 오류 발생: {str(e)}")
        raise e


if __name__ == "__main__":
    main()