# main/trading_main.py
import os, json, time, requests
from datetime import datetime
import pandas as pd

# -----------------------------
# 내부 모듈 임포트
# -----------------------------
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from utils.config import get_access_token
from utils.data_handler import get_price, get_balance
from utils.logger import log_info, log_warning, log_exceptions
from strategies.momentum_strategy import MomentumStrategy
from risk.risk_module import RiskManager
from backtest.update_backtest import PortfolioUpdater


# ================================
# 1️⃣ 주문 실행 함수
# ================================
def send_order(token, code, qty, side="buy", price=None, mode="vts"):
    """
    한국투자증권 매수/매도 주문 실행
    :param token: access token
    :param code: 종목코드
    :param qty: 수량
    :param side: 'buy' or 'sell'
    :param price: 지정가 (없으면 시장가)
    :param mode: 'vts' = 모의투자 / 'real' = 실전투자
    """
    BASE_URL = (
        "https://openapivts.koreainvestment.com:29443"
        if mode == "vts"
        else "https://openapi.koreainvestment.com:9443"
    )

    url = f"{BASE_URL}/uapi/domestic-stock/v1/trading/order-cash"
    headers = {
        "authorization": f"Bearer {token}",
        "appkey": os.getenv("APP_KEY"),
        "appsecret": os.getenv("APP_SECRET"),
        "tr_id": "VTTC0802U" if mode == "vts" else "TTTC0802U",
        "content-type": "application/json",
    }

    data = {
        "CANO": os.getenv("CANO"),
        "ACNT_PRDT_CD": os.getenv("ACNT_PRDT_CD"),
        "PDNO": code,
        "ORD_DVSN": "01",  # 시장가
        "ORD_QTY": str(qty),
        "ORD_UNPR": "0" if price is None else str(price),
    }

    res = requests.post(url, headers=headers, data=json.dumps(data))
    try:
        r = res.json()
    except:
        log_warning(f"❌ 주문 응답 오류: {res.text}")
        return None

    if r.get("rt_cd") == "0":
        log_info(f"✅ {side.upper()} 주문 성공 → {code} ({qty}주)")
    else:
        log_warning(f"❌ {side.upper()} 주문 실패: {r}")
    return r


# ================================
# 2️⃣ 실행 메인 루프
# ================================
@log_exceptions
def main():
    log_info("🚀 시스템 트레이딩 실행 시작 (모의투자 모드)")
    mode = "vts"  # 모의투자
    base_dir = os.path.dirname(os.path.dirname(__file__))
    current_path = os.path.join(base_dir, "utils", "stocks", "current_stocks.json")

    # -----------------------------
    # (1) 토큰 발급
    # -----------------------------
    token = get_access_token({"mode": mode})
    log_info("🔑 Access Token 발급 완료")

    # -----------------------------
    # (2) 주간 종목 업데이트 + 백테스트
    # -----------------------------
    updater = PortfolioUpdater(mode=mode)
    updater.run()

    # -----------------------------
    # (3) 현재 종목 로드
    # -----------------------------
    if not os.path.exists(current_path):
        log_warning("⚠️ current_stocks.json 파일이 없습니다. 초기화를 진행하세요.")
        return

    with open(current_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    stock_list = data.get("stocks", [])
    log_info(f"📁 현재 보유/대상 종목 ({len(stock_list)}개): {stock_list}")

    # -----------------------------
    # (4) 전략 실행 (모멘텀)
    # -----------------------------
    strategy = MomentumStrategy(lookback=20, threshold=0.02, mode=mode)
    df_signals = strategy.run()

    # -----------------------------
    # (5) 리스크 필터 적용
    # -----------------------------
    risk_manager = RiskManager(max_weight_per_stock=0.1, stop_loss=-0.1, take_profit=0.1)
    filtered_codes = risk_manager.apply_risk_filter(df_signals)
    log_info(f"✅ 리스크 필터 통과 종목 수: {len(filtered_codes)} / {len(stock_list)}")

    if not filtered_codes:
        log_warning("⚠️ 리스크 기준 통과 종목 없음 → 매매 중단")
        return

    # -----------------------------
    # (6) 잔고 조회
    # -----------------------------
    balance = get_balance()
    if balance is None:
        log_warning("⚠️ 잔고 조회 실패 → 매매 불가")
        return

    if isinstance(balance, pd.DataFrame):
        if balance.empty:
            log_info("💰 현재 계좌에 보유 종목이 없습니다.")
            current_holdings = []
        else:
            current_holdings = balance["pdno"].tolist() if "pdno" in balance.columns else []
    else:
        try:
            current_holdings = [b["pdno"] for b in balance.get("output1", []) if b.get("pdno")]
        except Exception as e:
            log_warning(f"⚠️ 잔고 파싱 실패: {e}")
            current_holdings = []

    log_info(f"🔹 현재 잔고 종목 수: {len(current_holdings)}개")

    # -----------------------------
    # (7) 투자 비율 계산
    # -----------------------------
    try:
        if isinstance(balance, dict):
            cash = int(balance["output2"][0]["dnca_tot_amt"].replace(",", ""))
        else:
            cash = 10000000  # 조회 실패 시 기본 1천만 원 가정
    except Exception:
        cash = 10000000

    invest_per_stock = cash * 0.1  # 10%씩 투자
    log_info(f"💰 총 잔고: {cash:,.0f}원 / 종목당 투자금: {invest_per_stock:,.0f}원")

    # -----------------------------
    # (8) 매도 (보유 중이지만 신호 미통과)
    # -----------------------------
    sell_targets = [code for code in current_holdings if code not in filtered_codes]
    for code in sell_targets:
        log_info(f"📉 매도 대상: {code}")
        send_order(token, code, qty="all", side="sell", mode=mode)
        time.sleep(1)

    # -----------------------------
    # (9) 매수 (신규 진입)
    # -----------------------------
    for code in filtered_codes:
        price = get_price(code)
        if not price:
            continue
        qty = max(1, int(invest_per_stock // price))
        log_info(f"📈 매수 대상: {code} ({qty}주)")
        send_order(token, code, qty=qty, side="buy", mode=mode)
        time.sleep(1)

    # -----------------------------
    # (10) 루프 마감
    # -----------------------------
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_info(f"✅ 매매 루프 완료 ({now})")
    log_info("-" * 60)


# ================================
# 3️⃣ 엔트리포인트
# ================================
if __name__ == "__main__":
    main()