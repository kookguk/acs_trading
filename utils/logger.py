import os
import logging
from datetime import datetime

# ===============================
# 1. 로그 디렉토리 자동 생성
# ===============================
LOG_DIR = os.path.join(os.getcwd(), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# ===============================
# 2. 로그 파일 경로 설정 (날짜별)
# ===============================
today = datetime.now().strftime("%Y-%m-%d")
LOG_FILE = os.path.join(LOG_DIR, f"{today}.log")

# ===============================
# 3. 로거 기본 설정
# ===============================
logger = logging.getLogger("trading_logger")
logger.setLevel(logging.DEBUG)  # DEBUG 이상 모든 로그 기록

# ===============================
# 4. 파일 핸들러 (파일 기록용)
# ===============================
file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
file_handler.setLevel(logging.INFO)
file_format = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
file_handler.setFormatter(file_format)

# ===============================
# 5. 콘솔 핸들러 (터미널 출력용)
# ===============================
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_format = logging.Formatter("🔹 %(message)s")
console_handler.setFormatter(console_format)

# ===============================
# 6. 핸들러 중복 추가 방지
# ===============================
if not logger.handlers:
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

# ===============================
# 7. 로깅 함수 래퍼 (직접 사용 시 간결하게)
# ===============================
def log_info(msg):
    logger.info(msg)

def log_warning(msg):
    logger.warning(msg)

def log_error(msg):
    logger.error(msg)

def log_debug(msg):
    logger.debug(msg)

# ===============================
# 8. 예외 자동 로깅용 데코레이터
# ===============================
def log_exceptions(func):
    """함수 실행 시 발생한 예외 자동 기록"""
    from functools import wraps
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.exception(f"❌ {func.__name__}() 실행 중 오류 발생: {e}")
            raise
    return wrapper