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
    - 주간 수익률 기반 교체
    - 교체 종목 수에 따라 백테스트 시도 횟수 조정
    """

    def __init__(self, lookback_weeks=12, replace_threshold=-0.02, mode="vts"):
        self.mode = mode
        self.lookback_weeks = lookback_weeks
        self.replace_threshold = replace_threshold

        base_dir = os.path.dirname(os.path.dirname(__file__))
        self.current_path = os.path.join(base_dir, "utils", "stocks", "current_stocks.json")
        self.candidates_path = os.path.join(base_dir, "utils", "stocks", "candidates_kospi200.csv")

        self.current_stocks = self._load_current_stocks()
        self.candidate_df = self._load_candidates()

    # =====================================================
    # 1️⃣ 파일 로드 및 저장
    # =====================================================
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

    # =====================================================
    # 2️⃣ 주간 수익률 계산
    # =====================================================
    def _weekly_return(self, code):
        """최근 1주일 수익률 계산"""
        df = get_daily_price(code, self.mode, count=10)
        time.sleep(0.5)
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
        return pd.DataFrame(weekly_returns)

    # =====================================================
    # 3️⃣ 교체 로직 (offset별 다른 후보로 교체)
    # =====================================================
    def update_portfolio(self, offset=0):
        """기준 이하 종목 교체 (offset에 따라 다른 후보 사용)"""
        df_returns = self.evaluate_current_stocks()
        losers = df_returns[df_returns["weekly_return"] <= self.replace_threshold]
        num_replace = len(losers)
        log_info(f"📉 기준 이하 종목 수: {num_replace}")

        # 모든 종목이 기준 이상일 경우 유지
        if num_replace == 0:
            log_info("✅ 교체 불필요 (모든 종목 유지)")
            return self.current_stocks, 0

        # ================================
        # 후보군에서 보유 종목 제외 후 평가
        # ================================
        exclude_list = set(self.current_stocks)
        candidate_pool = self.candidate_df[~self.candidate_df["code"].isin(exclude_list)]
        log_info(f"📈 후보 종목 수익률 계산 중... (보유 종목 제외 후 {len(candidate_pool)}개)")

        candidate_scores = []
        for code in candidate_pool["code"]:
            try:
                ret = self._weekly_return(code)
                if ret is not None:
                    candidate_scores.append({"code": code, "weekly_return": ret})
                time.sleep(0.3)
            except Exception as e:
                log_warning(f"{code}: 후보 평가 중 오류 발생 → {e}")

        df_candidate = pd.DataFrame(candidate_scores)
        if df_candidate.empty:
            log_warning("⚠️ 후보 종목 수익률 계산 결과가 비어 있음 — 교체 생략")
            return self.current_stocks, num_replace

        # ================================
        # 상위 후보 정렬 및 offset 기반 선택
        # ================================
        df_candidate = df_candidate.sort_values("weekly_return", ascending=False).reset_index(drop=True)
        start_idx = offset * num_replace
        end_idx = start_idx + num_replace
        new_candidates = df_candidate["code"].iloc[start_idx:end_idx].tolist()

        log_info(f"🔁 {offset+1}번째 시도 교체 대상: {losers['code'].tolist()}")
        log_info(f"🔁 {offset+1}번째 시도 신규 후보: {new_candidates}")

        # ================================
        # 교체 실행 (중복 방지)
        # ================================
        updated_stocks = [c for c in self.current_stocks if c not in losers["code"].tolist()]
        updated_stocks.extend(new_candidates)
        updated_stocks = list(dict.fromkeys(updated_stocks))[:10]

        log_info(f"📁 새로운 종목 리스트 (총 {len(updated_stocks)}개): {updated_stocks}")
        return updated_stocks, num_replace

    # =====================================================
    # 4️⃣ 백테스트 로직 (단순 Buy & Hold)
    # =====================================================
    def run_backtest(self, stock_list):
        """단순 Buy & Hold 백테스트"""
        log_info("🧮 백테스트 시작")
        portfolio_values = []

        for code in stock_list:
            df = get_daily_price(code, self.mode, count=self.lookback_weeks * 5)
            time.sleep(0.5)
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
        return {"return": avg_return, "volatility": volatility, "sharpe": sharpe}

    # =====================================================
    # 5️⃣ 전체 실행 루프 (교체 종목 수에 따른 반복 횟수)
    # =====================================================
    def run(self, return_metrics=False):
        """전체 실행 루프 — 백테스트 기준 통과 시까지 반복"""
        log_info("🚀 종목 업데이트 + 백테스트 루프 시작")

        # 첫 번째 교체 실행 (교체 종목 수 파악)
        updated_list, num_replace = self.update_portfolio(offset=0)

        # 교체 수에 따른 시도 횟수 결정
        if num_replace <= 3:
            max_iterations = 3
        elif num_replace <= 5:
            max_iterations = 2
        else:
            max_iterations = 1

        log_info(f"🧩 교체 종목 {num_replace}개 → 최대 {max_iterations}회 백테스트 시도 예정")

        best_metrics = None
        best_stocks = updated_list
        best_sharpe = -np.inf

        for i in range(max_iterations):
            # offset에 따라 새로운 후보 세트 사용
            trial_stocks, _ = self.update_portfolio(offset=i)
            result = self.run_backtest(trial_stocks)

            if not result:
                log_warning(f"⚠️ {i+1}번째 시도: 백테스트 데이터 없음 → 다음 후보로 이동")
                continue

            sharpe, ret = result["sharpe"], result["return"]

            if sharpe > best_sharpe:
                best_sharpe = sharpe
                best_metrics = result
                best_stocks = trial_stocks

            if sharpe > 1.0 and ret > 0.01:
                log_info(
                    f"✅ 백테스트 통과 (시도 {i+1}) → 포트폴리오 확정\n"
                    f"📊 결과: 수익률={ret*100:.2f}%, 변동성={result['volatility']*100:.2f}%, Sharpe={sharpe:.2f}"
                )
                self._save_current_stocks(trial_stocks)
                break
            else:
                log_warning(
                    f"❌ 백테스트 미달 (시도 {i+1}) → Sharpe={sharpe:.2f}, Return={ret*100:.2f}% → 다음 후보 재시도"
                )
                time.sleep(3)
        else:
            log_warning("⚠️ 모든 시도 실패 → Sharpe 최고 조합으로 확정")
            self._save_current_stocks(best_stocks)

        log_info("✅ 주간 포트폴리오 업데이트 완료")

        if return_metrics:
            return self._load_current_stocks(), best_metrics
        else:
            return self._load_current_stocks()