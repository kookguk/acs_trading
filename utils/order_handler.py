import requests
from utils.logger import log_info, log_error

def place_order(config, token, code, qty, side="BUY"):
    """
    한국투자증권 OpenAPI 시장가 주문 함수
    :param config: 환경 설정
    :param token: Access Token
    :param code: 종목 코드
    :param qty: 주문 수량
    :param side: "BUY" or "SELL"
    """
    try:
        tr_id = "VTTC0802U" if side == "BUY" else "VTTC0801U"  # 모의투자용 TR ID

        headers = {
            "authorization": f"Bearer {token}",
            "appkey": config["APP_KEY"],
            "appsecret": config["APP_SECRET"],
            "tr_id": tr_id,
            "content-type": "application/json"
        }

        payload = {
            "CANO": config["CANO"],
            "ACNT_PRDT_CD": config["ACNT_PRDT_CD"],
            "PDNO": code,
            "ORD_DVSN": "00", 
            "ORD_QTY": str(int(qty)),
            "ORD_UNPR": "0"   
        }

        url = f"{config['BASE_URL']}/uapi/domestic-stock/v1/trading/order-cash"
        response = requests.post(url, headers=headers, json=payload)

        if response.status_code == 200:
            data = response.json()
            log_info(f"✅ {side} 주문 성공: {code} ({qty}주)")
            return data
        else:
            log_error(f"❌ {side} 주문 실패: {code}, 응답: {response.text}")
            return None

    except Exception as e:
        log_error(f"❌ {side} 주문 중 오류 발생: {str(e)}")
        return None