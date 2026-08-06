#!/bin/sh
set -e
# krx-auto-crawling과 달리 이 프로젝트의 설정(config.py)은 pydantic-settings가
# /app/.env 파일을 직접 읽어들이므로(OS 환경변수 주입에 의존하지 않음), cron 잡이
# 별도로 환경변수를 상속받을 필요가 없다. 그래서 env 덤프 없이 바로 cron만 기동한다.
exec cron -f
