#!/bin/sh
set -e
# docker-compose env_file(.env)로 주입된 환경변수는 cron이 띄우는 잡 프로세스에는
# 상속되지 않으므로, 파일로 저장해뒀다가 run-crawl.sh에서 직접 로드한다.
printenv | grep -Ev '^(HOME|PWD|SHLVL|_)=' > /app/docker/cron.env
exec cron -f
