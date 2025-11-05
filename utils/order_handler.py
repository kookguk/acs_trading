import requests
from utils.logger import log_info, log_error


def get_tick_size(price: float) -> int:
    """KRX 호가단위 규칙 기반 tick size 계산"""
    if price < 1_000:
        return 1
    elif price < 5_000:
        return 5
    elif price < 10_000:
        return 10
    elif price < 50_000:
        return 50
    elif price < 100_000:
        return 100
    elif price < 500_000:
        return 500
    else:
        return 1000


def place_order(config, token, code, qty, price, side="BUY"):
    """
    지정가 주문 (KRX 호가단위 반영)
    side='BUY' → 현재가보다 1~2틱 위로
    side='SELL' → 현재가보다 1~2틱 아래로
    """

    try:
        # ✅ 모의투자용 tr_id
        tr_id = "VTTC0012U" if side == "BUY" else "VTTC0011U"

        # ✅ 실제 호가단위 계산
        tick = get_tick_size(price)

        # ✅ 지정가 보정
        if side == "BUY":
            order_price = price + (tick * 2)
        else:
            order_price = max(price - (tick * 2), tick)

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
            "ORD_DVSN": "00",  # 지정가
            "ORD_QTY": str(int(qty)),
            "ORD_UNPR": str(int(order_price)),
        }

        url = f"{config['BASE_URL']}/uapi/domestic-stock/v1/trading/order-cash"
        response = requests.post(url, headers=headers, json=payload)

        if response.status_code == 200:
            data = response.json()
            msg = data.get("msg1", "응답 메시지 없음")

            if data.get("rt_cd") == "0":
                log_info(f"✅ {side} 주문 성공: {code}, 수량={qty}주, 주문가={int(order_price):,}원")
                return {"success": True, "message": msg}
            else:
                log_error(f"⚠️ {side} 주문 실패: {code}, 사유={msg}")
                return {"success": False, "message": msg}
        else:
            msg = f"HTTP {response.status_code} 오류: {response.text}"
            log_error(f"❌ {side} 주문 실패 ({response.status_code}): {response.text}")
            return {"success": False, "message": msg}

    except Exception as e:
        msg = str(e)
        log_error(f"❌ {side} 주문 중 오류 발생: {msg}")
        return {"success": False, "message": msg}