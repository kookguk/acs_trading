import requests
import json
import numpy as np
import pandas as pd
from utils.logger import log_info, log_warning, log_error
from utils.slack_notifier import send_slack_message


class RiskManager:
    """
    리스크 관리 모듈 (실전/모의 자동매매용)
    - 계좌 평가금액 조회
    - 예수금 조회
    - 종목당 투자 비중 계산
    - 손절/익절 필터링
    - 포트폴리오 리스크 지표 계산
    """

    def __init__(self,
                 config,
                 max_weight_per_stock=0.1,
                 stop_loss=-0.1,
                 take_profit=0.1):
        """
        :param config: 환경 설정 정보 (ACCESS_TOKEN 포함)
        :param max_weight_per_stock: 종목당 최대 투자 비중 (기본 10%)
        :param stop_loss: 손절 기준 (예: -0.1 → -10%)
        :param take_profit: 익절 기준 (예: +0.1 → +10%)
        """
        self.config = config
        self.max_weight = max_weight_per_stock
        self.stop_loss = stop_loss
        self.take_profit = take_profit

        # 🔹 평가금액 + 예수금 조회
        self.portfolio_value, self.cash_balance = self.get_portfolio_value()

    # ============================================================
    # 1️⃣ 계좌 평가금액 + 예수금 조회
    # ============================================================
    def get_portfolio_value(self):
        """
        🔹 모의투자/실전 계좌의 총 평가금액 및 예수금 조회
        """
        headers = {
            "content-type": "application/json; charset=utf-8",
            "authorization": f"Bearer {self.config['ACCESS_TOKEN']}",
            "appkey": self.config["APP_KEY"],
            "appsecret": self.config["APP_SECRET"],
            "tr_id": "VTTC8434R" if "vts" in self.config["BASE_URL"] else "TTTC8434R",
        }

        params = {
            "CANO": self.config["CANO"],
            "ACNT_PRDT_CD": self.config["ACNT_PRDT_CD"],
            "AFHR_FLPR_YN": "N",
            "OFL_YN": "",
            "INQR_DVSN": "02",
            "UNPR_DVSN": "01",
            "FUND_STTL_ICLD_YN": "N",
            "FNCG_AMT_AUTO_RDPT_YN": "N",
            "PRCS_DVSN": "00",
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": ""
        }

        url = f"{self.config['BASE_URL']}/uapi/domestic-stock/v1/trading/inquire-balance"

        try:
            res = requests.get(url, headers=headers, params=params, timeout=10)
            data = res.json()
            log_info("DEBUG: 🔍 계좌 조회 결과 ↓")
            log_info(json.dumps(data, indent=2, ensure_ascii=False))

            total_value, cash_balance = 0, 0
            if "output2" in data and len(data["output2"]) > 0:
                total_value = float(data["output2"][0].get("tot_evlu_amt", 0))
                cash_balance = float(data["output2"][0].get("dnca_tot_amt", 0))

            if total_value == 0:
                log_warning("⚠️ 평가금액이 0원으로 반환됨 — .env 계좌번호 또는 API키 확인 필요")
                send_slack_message("⚠️ 평가금액이 0원으로 반환됨 — .env 설정 확인 필요")
            else:
                msg = f"💰 계좌 평가금액: {total_value:,.0f}원 / 예수금: {cash_balance:,.0f}원"
                log_info(msg)
                send_slack_message(msg)

            return total_value, cash_balance

        except Exception as e:
            log_error(f"❌ 평가금액 조회 실패: {e}")
            send_slack_message(f"❌ 평가금액 조회 실패: {e}")
            return 0.0, 0.0

    # ============================================================
    # 2️⃣ 리스크 지표 계산 (MDD, Vol, Sharpe)
    # ============================================================
    def calculate_metrics(self, price_df: pd.DataFrame):
        if price_df.empty:
            log_warning("⚠️ 가격 데이터가 비어 있습니다. 리스크 계산 불가.")
            return None

        returns = price_df.pct_change().dropna()
        cumulative = (1 + returns.mean(axis=1)).cumprod()
        rolling_max = cumulative.cummax()
        drawdown = (cumulative - rolling_max) / rolling_max

        mdd = drawdown.min()
        volatility = returns.std().mean() * np.sqrt(252)
        sharpe = (returns.mean().mean() / returns.std().mean()) * np.sqrt(252)

        metrics = {
            "MDD": round(float(mdd), 4),
            "Volatility": round(float(volatility), 4),
            "Sharpe": round(float(sharpe), 4)
        }

        log_info(f"📊 리스크 지표 계산 완료 → MDD={mdd:.2%}, Vol={volatility:.2%}, Sharpe={sharpe:.2f}")
        return metrics

    # ============================================================
    # 3️⃣ 리스크 필터 적용 (손절/익절/비중)
    # ============================================================
    def apply_risk_filter(self, df_signals):
        """
        전략 결과 DataFrame에 리스크 조건 적용
        :param df_signals: 모멘텀 전략 결과 DataFrame (code, momentum_score, signal)
        :return: 리스크 통과 종목 리스트
        """
        if df_signals.empty:
            log_warning("⚠️ 전략 결과가 비어 있어 리스크 필터 적용 불가")
            return []

        filtered_stocks = []

        for _, row in df_signals.iterrows():
            code = row["code"]
            momentum = row["momentum_score"]

            # 손절 / 익절 조건
            if momentum <= self.stop_loss:
                log_warning(f"{code}: 손절 기준 초과 ({momentum:.2%}) → 제외")
                continue
            if momentum >= self.take_profit:
                log_info(f"{code}: 익절 기준 도달 ({momentum:.2%}) → 매도 고려")
                continue

            invest_amount = self.portfolio_value * self.max_weight
            log_info(f"{code}: 리스크 통과 (최대 투자금 {invest_amount:,.0f}원)")
            filtered_stocks.append(code)

        log_info(f"✅ 리스크 통과 종목: {filtered_stocks}")
        send_slack_message(f"🧮 리스크 통과 종목: {filtered_stocks}")

        return filtered_stocks