# 📈 IPO Stock Crawler

한국 주식 시장의 IPO(기업공개) 데이터를 수집하고 분석하는 도구입니다. 38커뮤니케이션 등의 사이트에서 IPO 일정을 크롤링하고, FinanceDataReader(FDR)를 통해 상장 후 시세 정보를 자동으로 보강합니다.

## ✨ 주요 기능

- **전체 크롤링 (`full`)**: 지정한 연도부터 현재까지의 모든 IPO 데이터를 수집하고, 저장된 전체 연도를 대상으로 OHLC 가격 백필을 수행합니다.
- **일일 업데이트 (`daily`)**: 당일 + 향후 3일의 상장 예정 종목을 감지해 추가하고, 당해연도 OHLC 가격 백필을 수행합니다. (docker-compose의 `crawler-cron` 서비스가 평일 15:50 KST에 자동 실행)
- **데이터 보강 (`enrich`)**: SQLite 저장소에서 누락된 OHLC/수익률을 채웁니다. 이미 채워진 행과 상장일 15:50 컷오프 전인 행은 건너뛰므로 재실행해도 안전합니다.
- **자동 시세 연동**: 상장일 기준 시가/고가/저가/종가 및 공모가 대비 수익률을 자동으로 계산합니다.
- **Google Drive 동기화**: `--drive` 옵션으로 변경된 연도의 Excel을 먼저, `db/{연도}.db`를 그 다음에 업로드합니다.

## 🏗️ 아키텍처

이 프로젝트는 **Hexagonal Architecture (Ports and Adapters)** 패턴을 따릅니다.

- **Core**: 비즈니스 로직 (`CrawlerService`, `EnrichmentService`)
- **Ports**: 인터페이스 정의 (`src/core/ports`)
- **Adapters**: 외부 시스템 연동 (`src/infra/adapters`)
  - Web: Playwright (크롤링)
  - Data: KRX 정보데이터시스템 직접 조회 (주가 정보)
  - Persistence: SQLite (진실의 공급원, `db/{연도}.db`) 및 Excel (표현 계층, 렌더링 전용)

## 🚀 설치 방법

이 프로젝트는 [uv](https://github.com/astral-sh/uv)를 사용하여 의존성을 관리합니다.

1. **uv 설치** (없을 경우)

   ```bash
   pip install uv
   ```

2. **프로젝트 클론 및 의존성 설치**

   ```bash
   git clone <repository-url>
   cd new_stock_crawler
   uv sync
   ```

## 💻 사용 방법

모든 명령어는 `uv run crawler`를 통해 실행됩니다.

### 1. 전체 데이터 수집 (초기 실행)

```bash
# 기본값으로 전체 연도 모두 수집 (SQLite 저장소 db/{연도}.db 에 반영)
uv run crawler full

# 특정 연도부터 수집
uv run crawler full --start-year 2023

# 수집 후 변경된 연도의 Excel/DB를 Google Drive에도 업로드
uv run crawler full --drive
```

### 2. 일일 업데이트 (자동화용)

당일 + 향후 3일의 상장 예정 종목을 확인해 SQLite 저장소에 추가하고, 당해연도 가격을 백필합니다.

```bash
uv run crawler daily --drive
```

### 3. 기존 데이터 보강

SQLite 저장소에서 누락된 OHLC/수익률을 갱신합니다. 이미 채워진 데이터는 건너뛰므로 재실행해도 안전합니다.

```bash
uv run crawler enrich
```

### 4. Excel 산출물 생성 (선택)

SQLite 데이터를 읽어 연도별로 `output/신규상장종목({연도}년).xlsx`로 내보냅니다.

```bash
# 전체 연도 엑셀 렌더링
uv run crawler export-excel

# (선택) 특정 연도만 렌더링 & 구글 드라이브 업로드
uv run crawler export-excel --year 2026 --drive
```

### 도움말 확인

```bash
uv run crawler --help
```

## 🐳 Docker 실행

`docker-compose.yml`에 두 개의 서비스가 정의되어 있습니다: 1회성 실행용 `crawler`, 컨테이너 내장 cron으로
평일 15:50 KST에 `daily`를 자동 실행하는 `crawler-cron`.

1. **이미지 빌드**

   ```bash
   docker compose build
   ```

2. **1회성 실행** (`crawler` 서비스, `--rm`으로 실행 후 컨테이너 정리)

   ```bash
   docker compose run --rm crawler crawler full --drive
   docker compose run --rm crawler crawler daily --drive
   docker compose run --rm crawler crawler enrich
   ```

3. **상시 스케줄 실행** (`crawler-cron` 서비스, 백그라운드로 계속 실행)

   ```bash
   docker compose up -d crawler-cron
   ```

   스케줄은 `docker/crontab`에서 관리합니다(기본: 평일 15:50 KST). cron이 실행하는 작업은
   `docker/run-crawl.sh` → `uv run crawler daily --drive`입니다. cron 데몬 기동에 root 권한이
   필요해 이 서비스만 `user: root`로 오버라이드되어 있습니다(다른 명령은 전부 `nonroot`로 실행).

4. **필요한 볼륨/환경변수**: `output/`, `db/`, `secrets/`, `.env`를 호스트와 마운트합니다
   (자세한 내용은 `docker-compose.yml` 참고). Google Drive 연동을 쓰려면 `secrets/client_secret.json`과
   `uv run crawler auth`로 발급한 `secrets/token.json`이 필요합니다.

## 📊 데이터 구조

수집된 원본 데이터는 `db/{연도}.db`(SQLite, 테이블명 `stocks`, 종목명 단일 PK)로 저장 관리되며,
엑셀 렌더링 시 연도별로 `output/신규상장종목({연도}년).xlsx`에 저장됩니다.

- **시트**: 연도별로 시트가 분리됩니다 (예: `2024`, `2025`).
- **주요 유지 컬럼**:
  - 기업명, 상장일, 확정공모가
  - 기관경쟁률, 수급 정보
  - 시가, 고가, 저가, 종가 (당일 기준)
  - 수익률(%)

## 🧪 테스트

```bash
# 전체 테스트 실행
uv run pytest

# 커버리지 리포트 생성
uv run pytest --cov=src --cov-report=html
```
