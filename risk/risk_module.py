import numpy as np
import pandas as pd
from utils.logger import log_info, log_warning

class RiskManager:
    """
    리스크 관리 모듈
    - 최대 종목 비중 제한
    - 손절 / 익절 한도 설정
    - 포트폴리오 지표 계산 (MDD, Sharpe, 변동성)
    """

    def __init__(self,
                 max_weight_per_stock=0.1,
                 stop_loss=-0.1,
                 take_profit=0.1,
                 portfolio_value=10000000):
        """
        :param max_weight_per_stock: 종목당 최대 투자 비중 (기본 10%)
        :param stop_loss: 손절 기준 (예: -0.1 → -10%)
        :param take_profit: 익절 기준 (예: +0.1 → +10%)
        :param portfolio_value: 포트폴리오 전체 금액 (기본 1천만 원)
        """
        self.max_weight = max_weight_per_stock
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.portfolio_value = portfolio_value

    # ==============================
    # 1️⃣ 포트폴리오 리스크 계산
    # ==============================
    def calculate_metrics(self, price_df):
        """
        포트폴리오의 기본 리스크 지표 계산
        :param price_df: 종목별 일별 종가 DataFrame (index=날짜, columns=종목코드)
        """
        if price_df.empty:
            log_warning("⚠️ 가격 데이터가 비어 있습니다. 리스크 계산 불가.")
            return None

        # 일별 수익률
        returns = price_df.pct_change().dropna()

        # MDD (최대 낙폭)
        cumulative = (1 + returns.mean(axis=1)).cumprod()
        rolling_max = cumulative.cummax()
        drawdown = (cumulative - rolling_max) / rolling_max
        mdd = drawdown.min()

        # 변동성 (연율화)
        volatility = returns.std().mean() * np.sqrt(252)

        # Sharpe 비율 (무위험 수익률 0 가정)
        sharpe = (returns.mean().mean() / returns.std().mean()) * np.sqrt(252)

        metrics = {
            "MDD": round(float(mdd), 4),
            "Volatility": round(float(volatility), 4),
            "Sharpe": round(float(sharpe), 4)
        }

        log_info(f"📊 포트폴리오 리스크 계산 완료 → MDD={mdd:.2%}, Vol={volatility:.2%}, Sharpe={sharpe:.2f}")
        return metrics

    # ==============================
    # 2️⃣ 종목별 리스크 필터
    # ==============================
    def apply_risk_filter(self, df_signals):
        """
        전략 결과 DataFrame에 리스크 조건을 적용해 필터링
        :param df_signals: 모멘텀 전략 결과 DataFrame (code, momentum_score, signal)
        :return: 리스크 통과 종목 리스트
        """
        if df_signals.empty:
            log_warning("⚠️ 전략 결과가 비어 있어 리스크 필터를 적용할 수 없습니다.")
            return []

        filtered_stocks = []

        for _, row in df_signals.iterrows():
            code = row["code"]
            signal = row["signal"]
            momentum = row["momentum_score"]

            # 손절 / 익절 조건
            if momentum <= self.stop_loss:
                log_warning(f"{code}: 손절 기준 초과 ({momentum:.2%}) → 제외")
                continue
            if momentum >= self.take_profit:
                log_info(f"{code}: 익절 기준 도달 ({momentum:.2%}) → 매도 고려")
                continue

            # 비중 제한 조건
            invest_amount = self.portfolio_value * self.max_weight
            log_info(f"{code}: 리스크 통과 (최대 투자금 {invest_amount:,.0f}원)")
            filtered_stocks.append(code)

        log_info(f"✅ 리스크 필터 통과 종목 수: {len(filtered_stocks)} / {len(df_signals)}")
        return filtered_stocks