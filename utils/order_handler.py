# utils/order_handler.py
import requests
from utils.logger import log_info, log_error

def place_order(config, token, code, qty, price, side="BUY"):
    """
    슬리피지 보정 지정가 주문 (현재가 ± 호가단위 1~2틱 보정)
    side='BUY' → 현재가보다 약간 위로 주문 (즉시 체결 유도)
    side='SELL' → 현재가보다 약간 아래로 주문 (즉시 체결 유도)
    """
    try:
        tr_id = "VTTC0802U" if side == "BUY" else "VTTC0801U"

        # 호가 단위 계산 (단순 근사: 현재가 * 0.002 → 약 0.2%)
        tick = max(int(price * 0.002), 10)

        # 지정가 보정
        if side == "BUY":
            order_price = price + (tick * 2)  # 매수는 2틱 위로
        else:
            order_price = max(price - (tick * 2), 10)  # 매도는 2틱 아래로

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
            "ORD_DVSN": "01",  # ✅ 지정가
            "ORD_QTY": str(int(qty)),
            "ORD_UNPR": str(int(order_price)),
        }

        url = f"{config['BASE_URL']}/uapi/domestic-stock/v1/trading/order-cash"
        response = requests.post(url, headers=headers, json=payload)

        if response.status_code == 200:
            data = response.json()
            if data.get("rt_cd") == "0":
                msg = f"✅ {side} 주문 성공: {code}, 수량={qty}주, 주문가={int(order_price):,}원"
                log_info(msg)
                return True
            else:
                msg = f"⚠️ {side} 주문 실패: {code}, 사유={data.get('msg1')}"
                log_error(msg)
                return False
        else:
            log_error(f"❌ {side} 주문 실패 ({response.status_code}): {response.text}")
            return False

    except Exception as e:
        log_error(f"❌ {side} 주문 중 오류 발생: {str(e)}")
        return False