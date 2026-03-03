"""
루트 conftest.py — pytest가 src 디렉터리를 패키지 경로로 인식하도록 보장
"""
import sys
from pathlib import Path

# 이미 pyproject.toml의 pythonpath = ["src"]로 설정되어 있으나,
# 일부 환경에서 namespace 패키지 인식 문제가 발생할 수 있어 명시적으로 추가
_src = str(Path(__file__).parent / "src")
if _src not in sys.path:
    sys.path.insert(0, _src)
