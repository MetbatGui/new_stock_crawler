# 📈 IPO Stock Crawler

한국 주식 시장의 IPO(기업공개) 데이터를 수집하고 분석하는 도구입니다. 38커뮤니케이션 등의 사이트에서 IPO 일정을 크롤링하고, FinanceDataReader(FDR)를 통해 상장 후 시세 정보를 자동으로 보강합니다.

## ✨ 주요 기능

- **전체 크롤링 (`full`)**: 지정한 연도부터 현재까지의 모든 IPO 데이터를 수집합니다.
- **일일 업데이트 (`daily`)**: 매일 실행되어 새로운 상장 종목을 감지하고 추가합니다. (GitHub Actions 연동 최적화)
- **데이터 보강 (`enrich`)**: 이미 수집된 엑셀 파일에 최신 주가 정보(OHLC)와 수익률을 추가합니다.
- **자동 시세 연동**: 상장일 기준 시가/고가/저가/종가 및 공모가 대비 수익률을 자동으로 계산합니다.

## 🏗️ 아키텍처

이 프로젝트는 **Hexagonal Architecture (Ports and Adapters)** 패턴을 따릅니다.

- **Core**: 비즈니스 로직 (`CrawlerService`, `EnrichmentService`)
- **Ports**: 인터페이스 정의 (`src/core/ports`)
- **Adapters**: 외부 시스템 연동 (`src/infra/adapters`)
  - Web: Playwright (크롤링)
  - Data: FinanceDataReader (주가 정보)
  - Persistence: Parquet (진실의 공급원, 데이터 저장) 및 Excel (표현 계층, 렌더링 전용)

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
# 기본값으로 전체 연도 모두 수집 (Parquet 저장소 반영)
uv run crawler full

# 특정 연도부터 수집
uv run crawler full --start-year 2023
```

### 2. 일일 업데이트 (자동화용)

오늘 날짜에 상장하는 종목이 있는지 확인하고 Parquet 저장소에 추가합니다.

```bash
# 오늘 날짜 기준 실행
uv run crawler daily
```

### 3. 기존 데이터 보강

Parquet 파일에서 누락된 현재 주가 정보를 갱신합니다.

```bash
uv run crawler enrich
```

### 4. Excel 산출물 생성 (선택)

Parquet 데이터를 읽어 `output/신규상장종목.xlsx` 으로 내보냅니다.

```bash
# 전체 데이터 엑셀 렌더링
uv run crawler export-excel

# (선택) 특정 연도만 렌더링 & 구글 드라이브 업로드
uv run crawler export-excel --year 2026 --drive
```

### 도움말 확인

```bash
uv run crawler --help
```

## 🐳 Docker 실행

도커를 사용하면 환경 설정 없이 바로 실행할 수 있습니다.

1. **이미지 빌드**

   ```bash
   docker build -t stock-crawler .
   ```

2. **실행 (전체 크롤링)**

   ```bash
   # 엑셀 파일 저장을 위해 볼륨 마운트 필요
   docker run -v $(pwd)/reports:/app/reports stock-crawler full
   ```

3. **실행 (일일 업데이트)**

   ```bash
   docker run -v $(pwd)/reports:/app/reports stock-crawler daily
   ```

## 📊 데이터 구조

수집된 원본 데이터는 `output/parquet/{연도}.parquet` 구조로 저장 관리되며, 엑셀 렌더링 시 `output/신규상장종목.xlsx`에 저장됩니다.

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
