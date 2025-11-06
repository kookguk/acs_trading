import os, json, time, requests
from utils.slack_notifier import send_slack_message
from utils.logger import log_info, log_error
from utils.config import load_env, get_access_token
from utils.data_handler import get_stock_name
from utils.order_handler import place_order
from backtest.update_backtest import PortfolioUpdater


def main():
    send_slack_message("🧠 주간 종목 업데이트 및 백테스트 시작 (모의투자)")
    log_info("🧠 주간 종목 업데이트 및 백테스트 시작")

    try:
        # ✅ 환경 설정 및 토큰 발급
        config = load_env(mode="vts")
        token = get_access_token(config)
        config["ACCESS_TOKEN"] = token

        base_dir = os.path.dirname(os.path.dirname(__file__))
        current_path = os.path.join(base_dir, "utils", "stocks", "current_stocks.json")

        # ✅ 기존 보유 종목 불러오기
        with open(current_path, "r", encoding="utf-8") as f:
            old_stocks = json.load(f)["stocks"]

        old_named = [f"{s} ({get_stock_name(s)})" for s in old_stocks]
        send_slack_message(f"📁 기존 보유 종목: {old_named}")

        # ✅ 백테스트 실행 및 교체 종목 결정
        updater = PortfolioUpdater(mode="vts")
        new_stocks, performance = updater.run(return_metrics=True)
        new_named = [f"{s} ({get_stock_name(s)})" for s in new_stocks]
        send_slack_message(f"📁 신규 포트폴리오: {new_named}")

        # ✅ 교체 대상 계산
        sell_targets = [s for s in old_stocks if s not in new_stocks]
        buy_targets = [s for s in new_stocks if s not in old_stocks]

        send_slack_message(
            f"📊 교체 대상 요약\n"
            f"- 매도 대상: {[f'{s} ({get_stock_name(s)})' for s in sell_targets]}\n"
            f"- 신규 매수 대상: {[f'{s} ({get_stock_name(s)})' for s in buy_targets]}"
        )

        # ✅ 백테스트 성과 보고
        if performance:
            send_slack_message(
                f"📈 백테스트 결과\n"
                f"- 수익률: {performance['return']*100:.2f}%\n"
                f"- 변동성: {performance['volatility']*100:.2f}%\n"
                f"- Sharpe: {performance['sharpe']:.2f}"
            )

        # ✅ 현재 잔고 조회 (보유 종목 수량 포함)
        headers = {
            "authorization": f"Bearer {token}",
            "appkey": config["APP_KEY"],
            "appsecret": config["APP_SECRET"],
            "tr_id": "VTTC8434R",
            "content-type": "application/json",
        }
        url = f"{config['BASE_URL']}/uapi/domestic-stock/v1/trading/inquire-balance"
        params = {
            "CANO": config["CANO"],
            "ACNT_PRDT_CD": config["ACNT_PRDT_CD"],
            "AFHR_FLPR_YN": "N",
            "OFL_YN": "",
            "INQR_DVSN": "02",
            "UNPR_DVSN": "01",
            "FUND_STTL_ICLD_YN": "N",
            "FNCG_AMT_AUTO_RDPT_YN": "N",
            "PRCS_DVSN": "01",
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": "",
        }
        res = requests.get(url, headers=headers, params=params).json()

        holdings = res.get("output1", [])
        portfolio_value = float(res["output2"][0]["tot_evlu_amt"])
        send_slack_message(f"💰 현재 총 평가금: {portfolio_value:,.0f}원")

        # 보유 종목 딕셔너리로 변환
        holding_dict = {
            h["pdno"]: int(float(h["hldg_qty"]))
            for h in holdings if int(float(h["hldg_qty"])) > 0
        }

        # ✅ 교체 대상 전량 매도
        if sell_targets:
            send_slack_message("📉 교체 대상 전량 매도 시작")
            for code in sell_targets:
                if code not in holding_dict:
                    send_slack_message(f"⚠️ {code} ({get_stock_name(code)}) → 보유 수량 없음, 건너뜀")
                    continue

                qty = holding_dict[code]  # 실제 보유 수량
                try:
                    price_url = f"{config['BASE_URL']}/uapi/domestic-stock/v1/quotations/inquire-price"
                    price_params = {"fid_cond_mrkt_div_code": "J", "fid_input_iscd": code}
                    price_headers = {
                        "authorization": f"Bearer {token}",
                        "appkey": config["APP_KEY"],
                        "appsecret": config["APP_SECRET"],
                        "tr_id": "FHKST01010100",
                        "content-type": "application/json",
                    }
                    res_p = requests.get(price_url, headers=price_headers, params=price_params)
                    price = float(res_p.json()["output"]["stck_prpr"])

                    result = place_order(config, token, code, qty=qty, price=price, side="SELL")
                    msg = (
                        f"✅ 매도 성공: {code} ({get_stock_name(code)}), {qty}주 @ {price:,.0f}"
                        if result["success"]
                        else f"⚠️ 매도 실패: {code}, 사유={result['message']}"
                    )
                    send_slack_message(msg)
                    time.sleep(1)
                except Exception as e:
                    send_slack_message(f"❌ 매도 중 오류 발생: {code} → {e}")
            send_slack_message("✅ 매도 완료")

        # ✅ 신규 종목 매수 (잔고의 10%씩)
        if buy_targets:
            invest_per_stock = portfolio_value * 0.10
            send_slack_message(f"📈 신규 종목 매수 시작 (종목당 약 {invest_per_stock:,.0f}원)")

            for code in buy_targets:
                try:
                    price_url = f"{config['BASE_URL']}/uapi/domestic-stock/v1/quotations/inquire-price"
                    price_params = {"fid_cond_mrkt_div_code": "J", "fid_input_iscd": code}
                    price_headers = {
                        "authorization": f"Bearer {token}",
                        "appkey": config["APP_KEY"],
                        "appsecret": config["APP_SECRET"],
                        "tr_id": "FHKST01010100",
                        "content-type": "application/json",
                    }
                    res_p = requests.get(price_url, headers=price_headers, params=price_params)
                    price = float(res_p.json()["output"]["stck_prpr"])

                    qty = int(invest_per_stock // price)
                    if qty <= 0:
                        send_slack_message(f"⚠️ {code} ({get_stock_name(code)}) → 금액 부족으로 건너뜀")
                        continue

                    result = place_order(config, token, code, qty=qty, price=price, side="BUY")
                    msg = (
                        f"✅ 매수 성공: {code} ({get_stock_name(code)}), 수량={qty}주, 가격={price:,.0f}"
                        if result["success"]
                        else f"⚠️ 매수 실패: {code}, 사유={result['message']}"
                    )
                    send_slack_message(msg)
                    time.sleep(1)
                except Exception as e:
                    send_slack_message(f"❌ 매수 중 오류 발생: {code} → {e}")
            send_slack_message("✅ 신규 종목 매수 완료")

        send_slack_message("🎯 ✅ 주간 포트폴리오 교체 및 매매 완료")
        log_info("✅ 주간 포트폴리오 교체 + 매매 완료")

    except Exception as e:
        send_slack_message(f"❌ 오류 발생: {str(e)}")
        log_error(str(e))
        raise e


if __name__ == "__main__":
    main()