#!/bin/sh
set -e
cd /app
# cron 잡 자체는 root로 도는데(crontab 주석 참고 - /proc/1/fd/1 리다이렉션 때문),
# 실제 크롤링/스크래핑/Drive 업로드는 su로 nonroot로 낮춰서 실행한다. 리다이렉션은
# 부모(root) 셸이 이미 열어놓은 fd를 su의 자식 프로세스가 그대로 물려받으므로
# (open 시점에만 권한 체크) nonroot로 내려도 로그는 정상적으로 계속 써진다.
#
# cron은 Dockerfile의 ENV(PLAYWRIGHT_BROWSERS_PATH 포함)를 잡 프로세스에 물려주지
# 않는다(cron이 잡마다 최소 환경만 새로 구성) - Playwright가 브라우저를 못 찾고
# nonroot 기본 경로(~/.cache/ms-playwright)를 뒤지다 실패하므로 명시적으로 지정.
exec su -s /bin/sh -c 'PLAYWRIGHT_BROWSERS_PATH=/ms-playwright /app/.venv/bin/crawler daily --drive' nonroot
