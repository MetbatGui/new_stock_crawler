#!/bin/sh
set -e
set -a
. /app/docker/cron.env
set +a

cd /app
crawler daily --drive
