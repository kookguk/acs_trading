import requests
from utils.logger import log_info, log_error
import math


def get_tick_size(price: float) -> int:
    """KRX 실제 호가단위 규칙 기반"""
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
    elif price < 1_000_000:
        return 1_000
    else:
        return 2_000


def round_to_tick(price: float, tick: int, direction: str = "BUY") -> int:
    """가격을 tick 단위로 보정 (위 or 아래로 올림/내림)"""
    if direction == "BUY":
        return math.ceil(price / tick) * tick
    else:
        return math.floor(price / tick) * tick


def place_order(config, token, code, qty, price, side="BUY"):
    """
    지정가 주문 (KRX 호가단위 보정 포함)
    side='BUY' → 현재가보다 1틱 위로
    side='SELL' → 현재가보다 1틱 아래로
    """

    try:
        tr_id = "VTTC0012U" if side == "BUY" else "VTTC0011U"

        tick = get_tick_size(price)

        # 지정가 설정 (한 틱만 이동)
        if side == "BUY":
            order_price = price + tick
            order_price = round_to_tick(order_price, tick, "BUY")
        else:
            order_price = price - tick
            order_price = round_to_tick(order_price, tick, "SELL")

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
        data = response.json()

        # ✅ 응답 처리
        if response.status_code == 200:
            msg = data.get("msg1", "응답 메시지 없음")

            if data.get("rt_cd") == "0":
                log_info(f"✅ {side} 주문 성공: {code}, 수량={qty}주, 주문가={int(order_price):,}원")
                return {"success": True, "message": msg}
            else:
                log_error(f"⚠️ {side} 주문 실패: {code}, 사유={msg}")

                # ✅ 호가단위 오류 시 자동 재시도 (tick 보정 후)
                if "호가단위" in msg:
                    retry_price = round_to_tick(order_price, tick, side)
                    log_info(f"🔁 재시도: {side} {code}, 보정가={retry_price:,}원")
                    payload["ORD_UNPR"] = str(int(retry_price))
                    retry_res = requests.post(url, headers=headers, json=payload).json()
                    if retry_res.get("rt_cd") == "0":
                        log_info(f"✅ {side} 재주문 성공: {code}, {retry_price:,}원")
                        return {"success": True, "message": "재시도 성공"}
                    else:
                        return {"success": False, "message": retry_res.get("msg1", "재시도 실패")}
                return {"success": False, "message": msg}
        else:
            msg = f"HTTP {response.status_code} 오류: {response.text}"
            log_error(f"❌ {side} 주문 실패 ({response.status_code}): {response.text}")
            return {"success": False, "message": msg}

    except Exception as e:
        msg = str(e)
        log_error(f"❌ {side} 주문 중 오류 발생: {msg}")
        return {"success": False, "message": msg}