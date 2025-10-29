import os
import json
import pandas as pd
import numpy as np
import time
from datetime import datetime
from utils.data_handler import get_daily_price
from utils.logger import log_info, log_warning

class PortfolioUpdater:
    """
    📆 종목 업데이트 + 백테스트 자동 수행 모듈
    1️⃣ 주간 수익률 기반 교체
    2️⃣ 백테스트로 검증 후 반영
    """

    def __init__(self, lookback_weeks=12, replace_threshold=-0.02, top_n=3, mode="vts"):
        """
        :param lookback_weeks: 백테스트 기간 (기본 12주)
        :param replace_threshold: 주간 수익률 기준 (이하 종목 교체)
        :param top_n: 교체 시 후보 중 상위 N개 선택
        :param mode: 모의투자(vts) or 실전(real)
        """
        self.mode = mode
        self.lookback_weeks = lookback_weeks
        self.replace_threshold = replace_threshold
        self.top_n = top_n

        base_dir = os.path.dirname(os.path.dirname(__file__))
        self.current_path = os.path.join(base_dir, "utils", "stocks", "current_stocks.json")
        self.candidates_path = os.path.join(base_dir, "utils", "stocks", "candidates_kospi200.csv")

        # 파일 로드
        self.current_stocks = self._load_current_stocks()
        self.candidate_df = self._load_candidates()

    # ================================================
    # 1️⃣ 파일 로드 및 저장
    # ================================================
    def _load_current_stocks(self):
        with open(self.current_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        stocks = data.get("stocks", [])
        log_info(f"📁 현재 종목 로드 완료 ({len(stocks)}개)")
        return stocks

    def _load_candidates(self):
        df = pd.read_csv(self.candidates_path, dtype={"code": str})
        log_info(f"📁 후보 종목 로드 완료 ({len(df)}개)")
        return df

    def _save_current_stocks(self, updated_list):
        with open(self.current_path, "w", encoding="utf-8") as f:
            json.dump({"stocks": updated_list}, f, indent=2, ensure_ascii=False)
        log_info(f"💾 current_stocks.json 업데이트 완료 (총 {len(updated_list)}개)")

    # ================================================
    # 2️⃣ 주간 수익률 계산
    # ================================================
    def _weekly_return(self, code):
        """최근 1주일 수익률 계산"""
        df = get_daily_price(code, self.mode, count=10)
        time.sleep(0.6)
        if df.empty or len(df) < 5:
            return None
        start_price = df["stck_clpr"].iloc[-5]
        end_price = df["stck_clpr"].iloc[-1]
        return (end_price - start_price) / start_price

    def evaluate_current_stocks(self):
        """현재 종목들의 최근 1주 수익률 계산"""
        weekly_returns = []
        log_info("📊 현재 포트폴리오 수익률 계산 시작")
        for code in self.current_stocks:
            try:
                ret = self._weekly_return(code)
                if ret is not None:
                    weekly_returns.append({"code": code, "weekly_return": ret})
                    log_info(f"{code}: 주간 수익률 {ret:.2%}")
                else:
                    log_warning(f"{code}: 데이터 부족으로 제외")
            except Exception as e:
                log_warning(f"{code}: 오류 발생 → {e}")
        df_returns = pd.DataFrame(weekly_returns)
        return df_returns

    # ================================================
    # 3️⃣ 교체 로직 (중복 방지 개선 버전)
    # ================================================
    def update_portfolio(self):
        """기준 이하 종목 교체"""
        df_returns = self.evaluate_current_stocks()
        losers = df_returns[df_returns["weekly_return"] <= self.replace_threshold]
        num_replace = len(losers)
        log_info(f"📉 기준 이하 종목 수: {num_replace}")

        if num_replace == 0:
            log_info("✅ 교체 불필요 (모든 종목 유지)")
            return self.current_stocks

        # ✅ 현재 보유 종목 제외한 후보만 평가
        exclude_list = set(self.current_stocks)
        candidate_pool = self.candidate_df[~self.candidate_df["code"].isin(exclude_list)]

        log_info(f"📈 후보 종목 수익률 계산 중... (보유 중 종목 제외 후 {len(candidate_pool)}개)")
        candidate_scores = []
        for code in candidate_pool["code"].head(100):  # 상위 100개만 평가
            try:
                ret = self._weekly_return(code)
                if ret is not None:
                    candidate_scores.append({"code": code, "weekly_return": ret})
                time.sleep(0.6)
            except Exception as e:
                log_warning(f"{code}: 후보 평가 중 오류 발생 → {e}")
                continue

        df_candidate = pd.DataFrame(candidate_scores)
        if df_candidate.empty:
            log_warning("⚠️ 후보 종목 수익률 계산 결과가 비어 있습니다. 교체 생략.")
            return self.current_stocks

        # ✅ 상위 n개 후보 선택 (교체할 개수만큼)
        df_candidate = df_candidate.sort_values("weekly_return", ascending=False)
        new_candidates = df_candidate["code"].head(num_replace).tolist()

        # ✅ 손실 종목 제거 후 신규 후보 교체
        updated_stocks = [code for code in self.current_stocks if code not in losers["code"].tolist()]
        updated_stocks.extend(new_candidates)

        # ✅ 정확히 10개 유지 (중복 제거 + 부족 시 보충)
        updated_stocks = list(dict.fromkeys(updated_stocks))
        if len(updated_stocks) < 10:
            extra_needed = 10 - len(updated_stocks)
            for code in df_candidate["code"]:
                if code not in updated_stocks:
                    updated_stocks.append(code)
                    if len(updated_stocks) == 10:
                        break

        updated_stocks = updated_stocks[:10]

        log_info(f"🔄 교체 완료 → {num_replace}개 종목 교체됨")
        log_info(f"📁 새로운 종목 리스트 (총 {len(updated_stocks)}개): {updated_stocks}")

        self._save_current_stocks(updated_stocks)
        return updated_stocks

    # ================================================
    # 4️⃣ 백테스트 로직 (단순 Buy & Hold)
    # ================================================
    def run_backtest(self, stock_list):
        """
        단순 Buy & Hold 백테스트
        - lookback_weeks 기간 동안의 수익률, 변동성, Sharpe 계산
        """
        log_info("🧮 백테스트 시작")
        portfolio_values = []

        for code in stock_list:
            df = get_daily_price(code, self.mode, count=self.lookback_weeks * 5)
            time.sleep(0.6)
            if df.empty or len(df) < 5:
                continue

            start = df["stck_clpr"].iloc[0]
            end = df["stck_clpr"].iloc[-1]
            ret = (end - start) / start
            portfolio_values.append(ret)

        if not portfolio_values:
            log_warning("⚠️ 백테스트 데이터 부족")
            return None

        avg_return = np.mean(portfolio_values)
        volatility = np.std(portfolio_values)
        sharpe = avg_return / volatility if volatility > 0 else 0

        log_info(f"📊 백테스트 결과 → 수익률={avg_return:.2%}, 변동성={volatility:.2%}, Sharpe={sharpe:.2f}")
        return {"return": avg_return, "volatility": volatility, "sharpe": sharpe}

    # ================================================
    # 5️⃣ 전체 실행 루프
    # ================================================
    def run(self):
        log_info("🚀 종목 업데이트 + 백테스트 루프 시작")
        max_iterations = 3

        for i in range(max_iterations):
            updated_list = self.update_portfolio()
            result = self.run_backtest(updated_list)

            if result and result["sharpe"] > 0.5 and result["return"] > 0.01:
                log_info("✅ 백테스트 통과 → 포트폴리오 확정")
                self._save_current_stocks(updated_list)
                break
            else:
                log_warning("❌ 백테스트 미달 → 후보 교체 후 재시도")
                time.sleep(3)
        else:
            log_warning("⚠️ 3회 시도 후에도 백테스트 통과 실패 → 마지막 포트폴리오 유지")

        log_info("✅ 주간 포트폴리오 업데이트 완료")
        return self._load_current_stocks()  # ✅ 여기가 핵심
