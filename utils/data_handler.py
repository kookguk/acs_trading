import json
import time
import requests
import pandas as pd
from datetime import datetime
from utils.config import load_env, get_access_token, make_headers
from utils.logger import log_info, log_warning

# ==============================
# 1. 단일 종목 현재가 조회
# ==============================
def get_price(code: str, mode="vts"):
    config = load_env(mode)
    token = get_access_token(config)
    headers = make_headers(config, token, "FHKST01010100")

    url = f"{config['BASE_URL']}/uapi/domestic-stock/v1/quotations/inquire-price"
    params = {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": code}

    res = requests.get(url, headers=headers, params=params)
    if res.status_code != 200:
        raise ConnectionError(f"❌ 시세 조회 실패: {res.text}")

    data = res.json().get("output", {})
    price = float(data.get("stck_prpr", 0))
    log_info(f"{code} 현재가: {price:,.0f}원")
    return price


# ==============================
# 2. 일봉 데이터 조회
# ==============================
def get_daily_price(code: str, mode="vts", count=30):
    config = load_env(mode)
    token = get_access_token(config)
    headers = make_headers(config, token, "FHKST01010400")

    url = f"{config['BASE_URL']}/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice"
    params = {
        "FID_COND_MRKT_DIV_CODE": "J",
        "FID_INPUT_ISCD": code,
        "FID_INPUT_DATE_1": datetime.now().strftime("%Y%m%d"),
        "FID_PERIOD_DIV_CODE": "D",
        "FID_ORG_ADJ_PRC": "0"
    }

    res = requests.get(url, headers=headers, params=params)
    if res.status_code != 200:
        raise ConnectionError(f"❌ 일봉 조회 실패: {res.text}")

    data = res.json().get("output", [])
    if not data:
        log_warning(f"{code}: 일봉 데이터가 비어있습니다.")
        return pd.DataFrame()

    df = pd.DataFrame(data)
    if "stck_clpr" not in df.columns:
        log_warning(f"{code}: 일봉 데이터 컬럼 누락")
        return pd.DataFrame()

    df["stck_clpr"] = df["stck_clpr"].astype(float)
    df["stck_bsop_date"] = pd.to_datetime(df["stck_bsop_date"])
    df = df.sort_values("stck_bsop_date")
    log_info(f"{code}: 일봉 데이터 {len(df)}건 수신")
    return df.tail(count)


# ==============================
# 3. 계좌 잔고 조회
# ==============================
def get_balance(mode="vts"):
    config = load_env(mode)
    token = get_access_token(config)
    headers = make_headers(config, token, "VTTC8434R" if mode == "vts" else "TTTC8434R")

    url = f"{config['BASE_URL']}/uapi/domestic-stock/v1/trading/inquire-balance"
    params = {
        "CANO": config["CANO"],
        "ACNT_PRDT_CD": config["ACNT_PRDT_CD"],
        "AFHR_FLPR_YN": "N",
        "OFL_YN": "",
        "INQR_DVSN": "02",
        "UNPR_DVSN": "01",
        "FUND_STTL_ICLD_YN": "N",
        "BFYM_CPRC_KND": "0",
        "NCCS_ATSC_CNCL_YN": "N"
    }

    res = requests.get(url, headers=headers, params=params)
    if res.status_code != 200:
        raise ConnectionError(f"❌ 잔고 조회 실패: {res.text}")

    balance = res.json().get("output1", [])
    df = pd.DataFrame(balance)
    log_info(f"현재 잔고 종목 수: {len(df)}개")
    return df