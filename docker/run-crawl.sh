#!/bin/sh
set -e
cd /app
/app/.venv/bin/crawler daily --drive
