import numpy as np
import pandas as pd
from utils.logger import log_info, log_warning
from utils.config import get_access_token, load_env
import requests


class RiskManager:
    """
    리스크 관리 모듈 (실제 계좌 잔고 기반)
    - 최대 종목 비중 제한
    - 손절 / 익절 한도 설정
    - 포트폴리오 지표 계산 (MDD, Sharpe, 변동성)
    """

    def __init__(self,
                 config: dict,
                 token: str,
                 max_weight_per_stock=0.1,
                 stop_loss=-0.1,
                 take_profit=0.1):
        self.config = config
        self.token = token
        self.max_weight = max_weight_per_stock
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.portfolio_value = self.get_portfolio_value()  # 🔹 실제 계좌 평가금액 기반

    # ==============================
    # 1️⃣ 계좌 평가금액 조회
    # ==============================
    def get_portfolio_value(self):
        """계좌 평가금액 조회"""
        url = f"{self.config['BASE_URL']}/uapi/domestic-stock/v1/trading/inquire-balance"
        headers = {
            "authorization": f"Bearer {self.token}",
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
            "CTX_AREA_NK100": "",
        }

        res = requests.get(url, headers=headers, params=params).json()
        total_eval_amt = 0
        try:
            output2 = res.get("output2", [])
            for item in output2:
                total_eval_amt += float(item.get("pchs_amt", 0))
            output1 = res.get("output1", [])
            if output1:
                total_eval_amt += float(output1[0].get("dnca_tot_amt", 0))
        except Exception:
            log_warning("⚠️ 계좌 평가금액 조회 실패 — 기본값 10,000,000원 사용")
            total_eval_amt = 10_000_000

        log_info(f"💰 계좌 평가금액: {total_eval_amt:,.0f}원")
        return total_eval_amt

    # ==============================
    # 2️⃣ 포트폴리오 리스크 계산
    # ==============================
    def calculate_metrics(self, price_df):
        """포트폴리오 리스크 지표 계산"""
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

        log_info(f"📊 리스크 계산 → MDD={mdd:.2%}, Vol={volatility:.2%}, Sharpe={sharpe:.2f}")
        return metrics

    # ==============================
    # 3️⃣ 종목별 리스크 필터
    # ==============================
    def apply_risk_filter(self, df_signals):
        """전략 결과에 리스크 조건 적용"""
        if df_signals.empty:
            log_warning("⚠️ 전략 결과가 비어 있어 리스크 필터를 적용할 수 없습니다.")
            return []

        filtered_stocks = []
        for _, row in df_signals.iterrows():
            code = row["code"]
            signal = row["signal"]
            momentum = row["momentum_score"]

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
        return filtered_stocks