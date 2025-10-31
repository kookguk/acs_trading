import requests
from utils.logger import log_info, log_error


def place_order(config, token, code, qty, price, side="BUY"):
    """
    슬리피지 보정 지정가 주문 (현재가 ± 호가단위 1~2틱 보정)
    side='BUY' → 현재가보다 약간 위로 주문 (즉시 체결 유도)
    side='SELL' → 현재가보다 약간 아래로 주문 (즉시 체결 유도)

    ✅ 반환값:
        {"success": True/False, "message": str}
    """

    try:
        # 주문 구분 ID (모의투자)
        tr_id = "VTTC0802U" if side == "BUY" else "VTTC0801U"

        # 호가 단위 계산 (약 0.2%)
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

        # =============================
        # ✅ 응답 상태 코드 확인
        # =============================
        if response.status_code == 200:
            data = response.json()
            msg = data.get("msg1", "응답 메시지 없음")

            if data.get("rt_cd") == "0":  # ✅ 성공
                log_info(f"✅ {side} 주문 성공: {code}, 수량={qty}주, 주문가={int(order_price):,}원")
                return {"success": True, "message": msg}

            else:  # ⚠️ 실패 (사유 포함)
                log_error(f"⚠️ {side} 주문 실패: {code}, 사유={msg}")
                return {"success": False, "message": msg}

        else:  # ❌ HTTP 에러
            msg = f"HTTP {response.status_code} 오류: {response.text}"
            log_error(f"❌ {side} 주문 실패 ({response.status_code}): {response.text}")
            return {"success": False, "message": msg}

    except Exception as e:
        msg = str(e)
        log_error(f"❌ {side} 주문 중 오류 발생: {msg}")
        return {"success": False, "message": msg}