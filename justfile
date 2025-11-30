set shell := ["powershell.exe", "-c"]

default:
    @just --list

# 초기 설정 (Initialize)
init:
    @echo "🚀 초기 설정을 시작합니다..."
    @if not exist .env ( copy .env.example .env ) else ( echo "ℹ️  .env 파일이 이미 존재합니다." )
    @if not exist secrets ( mkdir secrets ) else ( echo "ℹ️  secrets 폴더가 이미 존재합니다." )
    uv sync
    @echo "✅ 설정 완료! secrets/client_secret.json 파일을 넣고 'just auth'를 실행하세요."


build:
    docker-compose build

full year="2020":
    docker-compose run --rm crawler crawler full --start-year {{year}} --drive

daily date="":
    docker-compose run --rm crawler crawler daily {{ if date != "" { "--date " + date } else { "" } }} --drive

enrich:
    docker-compose run --rm crawler crawler enrich --drive

auth:
    docker-compose run --rm crawler crawler auth

# Local execution (using uv)
local-full year="2020":
    uv run crawler full --start-year {{year}} --drive

local-daily date="":
    uv run crawler daily {{ if date != "" { "--date " + date } else { "" } }} --drive

local-enrich:
    uv run crawler enrich --drive

local-auth:
    uv run crawler auth
