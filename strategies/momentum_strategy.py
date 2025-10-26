import os
import json
import pandas as pd
import time
from utils.data_handler import get_daily_price
from utils.logger import log_info, log_warning

class MomentumStrategy:
    """
    단기 모멘텀 기반 전략
    - 최근 N일 수익률을 기준으로 모멘텀 점수 계산
    - 기준 이상이면 매수, 기준 미만이면 매도 신호 발생
    """

    def __init__(self, lookback=20, threshold=0.02, mode="vts"):
        """
        :param lookback: 모멘텀 계산 기준 일수
        :param threshold: 매수 판단 기준 (20일 수익률 2% 이상이면 매수)
        :param mode: 'vts' (모의투자) or 'real' (실전)
        """
        self.lookback = lookback
        self.threshold = threshold
        self.mode = mode
        self.results = []
        
        # 경로 설정
        base_dir = os.path.dirname(os.path.dirname(__file__))
        self.current_stocks_path = os.path.join(base_dir, "utils", "stocks", "current_stocks.json")
        self.candidates_path = os.path.join(base_dir, "utils", "stocks", "candidates_kospi200.csv")

        # 종목 데이터 로드
        self.stock_list = self._load_current_stocks()
        self.candidate_df = self._load_candidates()

    # ==============================
    # 종목 파일 로드
    # ==============================
    def _load_current_stocks(self):
        """현재 투자 중인 10개 종목 로드"""
        with open(self.current_stocks_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        stock_list = data.get("stocks", [])
        log_info(f"📁 현재 종목 파일 로드 완료 (개수: {len(stock_list)})")
        return stock_list

    def _load_candidates(self):
        """KOSPI200 후보 파일 로드"""
        df = pd.read_csv(self.candidates_path, dtype={"code": str})
        log_info(f"📁 후보 종목 파일 로드 완료 (개수: {len(df)})")
        return df

    # ==============================
    # 모멘텀 계산 함수
    # ==============================
    def _calculate_momentum(self, df):
        """수익률 계산 (마지막 종가 대비 lookback일 전 종가)"""
        if len(df) < self.lookback:
            return None
        past_price = df["stck_clpr"].iloc[-self.lookback]
        current_price = df["stck_clpr"].iloc[-1]
        return (current_price - past_price) / past_price

    # ==============================
    # 전략 실행
    # ==============================
    def run(self):
        """모멘텀 전략 실행"""
        log_info(f"📊 모멘텀 전략 시작 (종목 수: {len(self.stock_list)})")

        for code in self.stock_list:
            try:
                df = get_daily_price(code, self.mode, count=self.lookback + 5)
                time.sleep(1.1)  # API 요청 간격 유지

                if df.empty:
                    log_warning(f"{code}: 데이터 부족으로 제외")
                    continue

                momentum_score = self._calculate_momentum(df)
                if momentum_score is None:
                    log_warning(f"{code}: 데이터 부족 (lookback={self.lookback})")
                    continue

                # 매매 신호 판단
                if momentum_score >= self.threshold:
                    signal = "BUY"
                elif momentum_score < 0:
                    signal = "SELL"
                else:
                    signal = "HOLD"

                self.results.append({
                    "code": code,
                    "momentum_score": round(momentum_score, 4),
                    "signal": signal
                })

                log_info(f"{code}: 모멘텀={momentum_score:.2%}, 신호={signal}")

            except Exception as e:
                log_warning(f"{code}: 분석 중 오류 발생 → {e}")

        log_info("✅ 모멘텀 전략 완료")
        return pd.DataFrame(self.results)