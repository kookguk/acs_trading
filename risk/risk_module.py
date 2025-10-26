import os
import requests
import logging
import numpy as np
import pandas as pd
from datetime import datetime

class RiskManager:
    def __init__(self, config, token):
        self.config = config
        self.token = token
        self.logger = logging.getLogger(__name__)
        self.slack_url = os.getenv("SLACK_WEBHOOK_URL")

        # 초기 포트폴리오 평가금액 계산
        self.portfolio_value = self.get_portfolio_value()
        self.logger.info(f"💰 초기 포트폴리오 평가금액: {self.portfolio_value:,.0f}원")

    def get_portfolio_value(self):
        """
        API를 통해 현재 계좌 평가금액 조회 (토큰 필요)
        """
        try:
            url = f"{self.config['base_url']}/uapi/domestic-stock/v1/trading/inquire-balance"
            headers = {
                "authorization": f"Bearer {self.token}",
                "appkey": self.config['app_key'],
                "appsecret": self.config['app_secret'],
                "tr_id": "TTTC8434R",
            }
            params = {"CANO": self.config['cano'], "ACNT_PRDT_CD": "01"}

            resp = requests.get(url, headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json()

            balance = float(data["output2"][0]["tot_evlu_amt"])
            return balance

        except Exception as e:
            self.logger.error(f"⚠️ 계좌 평가금액 조회 실패: {e}")
            self.send_slack_alert(f"⚠️ 계좌 평가금액 조회 실패: {e}")
            return 0.0

    def calculate_risk_metrics(self, returns: pd.Series):
        """
        수익률 시리즈 기반으로 리스크 지표 계산
        """
        try:
            avg_return = np.mean(returns)
            vol = np.std(returns)
            sharpe = avg_return / vol if vol != 0 else 0
            mdd = self.calculate_mdd(returns)
            var_95 = np.percentile(returns, 5)

            metrics = {
                "평균수익률": avg_return,
                "변동성": vol,
                "샤프비율": sharpe,
                "MDD": mdd,
                "VaR(95%)": var_95
            }
            self.logger.info(f"📊 리스크 지표 계산 완료: {metrics}")
            return metrics

        except Exception as e:
            self.logger.error(f"리스크 지표 계산 오류: {e}")
            self.send_slack_alert(f"리스크 지표 계산 오류: {e}")
            return {}

    def calculate_mdd(self, returns: pd.Series):
        """
        최대 낙폭 (MDD) 계산
        """
        cum_ret = (1 + returns).cumprod()
        peak = cum_ret.cummax()
        drawdown = (cum_ret - peak) / peak
        mdd = drawdown.min()
        return mdd

    def send_slack_alert(self, message: str):
        """
        슬랙 알림 전송 (예외 안전)
        """
        if not self.slack_url:
            self.logger.warning("Slack Webhook URL이 설정되지 않음.")
            return

        try:
            payload = {"text": f"[Risk Manager] {message}"}
            requests.post(self.slack_url, json=payload)
        except Exception as e:
            self.logger.warning(f"Slack 알림 실패: {e}")
