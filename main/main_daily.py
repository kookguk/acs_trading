import time
import requests
from utils.slack_notifier import send_slack_message
from utils.logger import log_info, log_error
from utils.config import load_env, get_access_token
from strategies.momentum_strategy import MomentumStrategy
from risk.risk_module import RiskManager
from backtest.update_backtest import PortfolioUpdater
from utils.data_handler import get_stock_name
from utils.order_handler import place_order


def get_current_price(config, token, code):
    """현재가 조회 함수"""
    try:
        url = f"{config['BASE_URL']}/uapi/domestic-stock/v1/quotations/inquire-price"
        headers = {
            "authorization": f"Bearer {token}",
            "appkey": config["APP_KEY"],
            "appsecret": config["APP_SECRET"],
            "tr_id": "FHKST01010100",
            "content-type": "application/json"
        }
        params = {"fid_cond_mrkt_div_code": "J", "fid_input_iscd": code}
        res = requests.get(url, headers=headers, params=params)
        data = res.json()
        price = float(data["output"]["stck_prpr"])
        return price
    except Exception as e:
        log_error(f"❌ 현재가 조회 실패: {code} → {e}")
        send_slack_message(f"⚠️ 현재가 조회 실패: {code} → {e}")
        return None


def main():
    send_slack_message("🤖 🚀 일일 자동매매 시작 (모의투자)")
    log_info("🚀 일일 자동매매 시작")

    try:
        # 1️⃣ 환경 설정 및 토큰 발급
        config = load_env(mode="vts")
        token = get_access_token(config)

        # ✅ 토큰을 config에 추가
        config["ACCESS_TOKEN"] = token
        send_slack_message("✅ Access Token 발급 완료")

        # 2️⃣ 계좌 정보 및 현재 잔고
        risk_manager = RiskManager(config)
        portfolio_value = risk_manager.portfolio_value
        cash_balance = risk_manager.cash_balance
        send_slack_message(f"💰 현재 잔고: {portfolio_value:,.0f}원 / 💵 예수금: {cash_balance:,.0f}원")
        send_slack_message(f"📈 현재 수익률: {risk_manager.current_return:.2%}")

        # 3️⃣ 현재 보유 종목 불러오기
        updater = PortfolioUpdater(mode="vts")
        current_stocks = updater._load_current_stocks()
        current_named = [f"{s} ({get_stock_name(s)})" for s in current_stocks]
        send_slack_message(f"📁 현재 보유 종목: {current_named}")

        # 4️⃣ 모멘텀 전략 실행
        strategy = MomentumStrategy(mode="vts")
        df_signals = strategy.run()
        send_slack_message("📊 모멘텀 전략 실행 완료")

        # 5️⃣ 리스크 필터 적용
        filtered_stocks = risk_manager.apply_risk_filter(df_signals)
        filtered_named = [f"{s} ({get_stock_name(s)})" for s in filtered_stocks]

        # 6️⃣ 유지/매도/신규 매수 종목 계산
        sell_stocks = [s for s in current_stocks if s not in filtered_stocks]
        keep_stocks = filtered_stocks.copy()
        num_needed = 10 - len(keep_stocks)

        candidate_pool = updater._load_candidates()
        exclude_list = set(current_stocks)
        candidate_pool = candidate_pool[~candidate_pool["code"].isin(exclude_list)]
        new_additions = candidate_pool["code"].head(num_needed).tolist() if num_needed > 0 else []
        keep_stocks.extend(new_additions)

        send_slack_message(
            f"📊 전략 실행 결과:\n"
            f"- 리스크 통과: {filtered_named}\n"
            f"- 유지 종목: {[f'{s} ({get_stock_name(s)})' for s in filtered_stocks]}\n"
            f"- 매도 종목: {[f'{s} ({get_stock_name(s)})' for s in sell_stocks]}\n"
            f"- 신규 매수 종목: {[f'{s} ({get_stock_name(s)})' for s in new_additions]}"
        )

        # 7️⃣ 주문 실행 (성공/실패/사유까지 Slack 전송)
        send_slack_message("📈 슬리피지 보정 지정가 주문 실행 시작")

        def execute_order_list(order_list, side):
            for s in order_list:
                price = get_current_price(config, token, s)
                if not price:
                    msg = f"⚠️ {side} 주문 실패: {s} ({get_stock_name(s)}) → 현재가 조회 실패"
                    log_error(msg)
                    send_slack_message(msg)
                    continue

                try:
                    result = place_order(config, token, s, qty=1, price=price, side=side)

                    # ✅ place_order()의 반환값 기반으로 처리
                    if isinstance(result, dict):
                        if result.get("success", False):
                            msg = f"✅ {side} 주문 성공: {s} ({get_stock_name(s)}), 수량=1주, 주문가={price:,.0f}원"
                            log_info(msg)
                            send_slack_message(msg)
                        else:
                            reason = result.get("message", "알 수 없는 오류")
                            msg = f"⚠️ {side} 주문 실패: {s} ({get_stock_name(s)}), 사유={reason}"
                            log_error(msg)
                            send_slack_message(msg)
                    else:
                        # place_order()가 단순 bool 반환하는 경우
                        if result:
                            msg = f"✅ {side} 주문 성공: {s} ({get_stock_name(s)}), 주문가={price:,.0f}원"
                            log_info(msg)
                            send_slack_message(msg)
                        else:
                            msg = f"⚠️ {side} 주문 실패: {s} ({get_stock_name(s)})"
                            log_error(msg)
                            send_slack_message(msg)

                except Exception as e:
                    msg = f"❌ {side} 주문 중 예외 발생: {s} ({get_stock_name(s)}) → {e}"
                    log_error(msg)
                    send_slack_message(msg)

                time.sleep(1)  # 주문 간 간격

        # 실제 주문 실행
        execute_order_list(sell_stocks, "SELL")
        execute_order_list(new_additions, "BUY")

        # 8️⃣ 주문 후 잔고 갱신
        risk_manager.refresh_portfolio()
        send_slack_message(f"💰 주문 후 잔고: {risk_manager.portfolio_value:,.0f}원 / 💵 예수금: {risk_manager.cash_balance:,.0f}원")
        send_slack_message(f"📈 주문 후 수익률: {risk_manager.current_return:.2%}")

        # 9️⃣ 새로운 보유 종목 저장 및 알림
        updater._save_current_stocks(keep_stocks)
        new_holdings_named = [f"{s} ({get_stock_name(s)})" for s in keep_stocks]
        send_slack_message(f"💾 새로운 보유 종목: {new_holdings_named}")

        send_slack_message("🎯 ✅ 일일 자동매매 종료")
        log_info("✅ 일일 자동매매 종료")

    except Exception as e:
        send_slack_message(f"❌ 오류 발생: {str(e)}")
        log_error(f"❌ 오류 발생: {str(e)}")
        raise e


if __name__ == "__main__":
    main()