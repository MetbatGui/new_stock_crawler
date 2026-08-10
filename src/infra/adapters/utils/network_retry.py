"""
네트워크 계층 재시도 공용 데코레이터
"""

import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# 일시적 네트워크 오류(타임아웃/연결 끊김 등)에 한해서만 재시도. HTTP 응답은
# 받았지만 상태코드가 비정상이거나 JSON 파싱이 실패하는 경우는 각 호출부가
# 이미 정상적으로 처리하므로 재시도 대상이 아니다.
network_retry = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    retry=retry_if_exception_type(requests.exceptions.RequestException),
    reraise=True,
)
