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


# CI가 build -> deploy -> release를 독립 호출할 수 있도록 이름을 표준화함
# (handoff_guide.md §2.1 참고)
docker-build:
    docker-compose build

# 컨테이너 내장 cron 서비스를 백그라운드로 기동. 재빌드는 하지 않음 - docker-build를
# 먼저 실행할 것.
docker-deploy:
    docker-compose up -d crawler-cron

# 현재 브랜치가 main/master일 때만 origin push - ship은 "안정화된 main 배포"가 목적이라
# feature 브랜치에서 실수로 배포/릴리즈되는 걸 막는다.
push-main:
    $branch = git rev-parse --abbrev-ref HEAD; if ($branch -ne 'main' -and $branch -ne 'master') { Write-Error "Refusing to push: current branch is '$branch', not main/master"; exit 1 }; git push origin $branch

# push-main -> docker-build -> docker-deploy -> release를 순서대로 한 번에 실행
ship: push-main docker-build docker-deploy release

# Docker execution
docker-full year="2020":
    docker-compose run --rm crawler crawler full --start-year {{year}} --drive

docker-daily date="":
    docker-compose run --rm crawler crawler daily {{ if date != "" { "--date " + date } else { "" } }} --drive

docker-enrich:
    docker-compose run --rm crawler crawler enrich --drive

auth:
    uv run crawler auth

healthcheck:
    uv run crawler healthcheck

docker-healthcheck:
    docker-compose run --rm crawler crawler healthcheck

docker-auth:
    docker-compose run --rm crawler crawler auth

# Local execution (using uv) - Default
full year="2020":
    uv run crawler full --start-year {{year}} --drive

daily date="":
    uv run crawler daily {{ if date != "" { "--date " + date } else { "" } }} --drive

enrich:
    uv run crawler enrich --drive

setup-release:
    git checkout master
    git remote add employers-new-stock https://github.com/guruta71/new-stock-crawler.git

# Release to employers-new-stock
# Usage: just release
release:
    git checkout -B release master
    git push -u employers-new-stock release:main
    git checkout master
