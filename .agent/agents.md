# 프로젝트 설계 원칙 및 가이드라인

## 🎯 핵심 설계 원칙

이 프로젝트는 **Hexagonal Architecture (Ports and Adapters)** 기반의 서비스 중심 아키텍처를 따릅니다.

### 1. 어댑터 격리 원칙
**어댑터끼리는 서로를 절대 모른다**

- ✅ 각 어댑터는 독립적으로 구현됨
- ✅ 어댑터는 다른 어댑터를 직접 참조하거나 생성하지 않음
- ✅ 어댑터 간 통신은 서비스 계층을 통해서만 이루어짐
- ❌ `PlaywrightPageProvider`가 `CalendarScraperImpl`을 직접 생성하는 것은 금지

```python
# ❌ 잘못된 예시
class PlaywrightPageProvider:
    def __init__(self):
        self.calendar_scraper = CalendarScraperImpl()  # 다른 어댑터 직접 생성

# ✅ 올바른 예시
class PlaywrightPageProvider:
    def __init__(self):
        pass  # 다른 어댑터를 알지 못함
```

### 2. 순수 모델 원칙
**모델은 아무것도 모른다**

- ✅ 도메인 모델(`core/domain/models.py`)은 외부 라이브러리나 프레임워크에 의존하지 않음
- ✅ 모델은 순수한 데이터 구조와 비즈니스 규칙만 포함
- ❌ 모델에서 Playwright, Pandas 등 인프라 의존성 사용 금지

```python
# ✅ 올바른 도메인 모델
@dataclass
class StockInfo:
    name: str
    market_segment: str
    # 순수 데이터만 포함
```

### 3. 서비스 오케스트레이션 원칙
**서비스가 포트를 통해 어댑터들을 조율한다**

- ✅ 비즈니스 로직은 `core/services/`에 위치
- ✅ 서비스는 포트 인터페이스만 의존
- ✅ 서비스가 여러 어댑터를 조합하여 워크플로우 실행
- ❌ 어댑터에 비즈니스 로직을 넣지 않음

```python
# ✅ 올바른 서비스 구현
class CrawlerService:
    def __init__(
        self,
        calendar_scraper: CalendarScraperPort,  # 포트 인터페이스
        detail_scraper: DetailScraperPort,      # 구체적인 구현체 아님
    ):
        self.calendar_scraper = calendar_scraper
        self.detail_scraper = detail_scraper
```

### 4. 명시적 의존성 원칙
**생성자에서 필요한 것만 받는다**

- ✅ 모든 의존성은 생성자를 통해 주입
- ✅ 의존성은 명시적으로 선언
- ❌ 전역 변수나 싱글톤 사용 금지
- ❌ 생성자 내부에서 의존성을 직접 생성하지 않음

```python
# ✅ 올바른 의존성 주입
class CrawlerService:
    def __init__(self, logger: LoggerPort):
        self.logger = logger  # 외부에서 주입받음

# ❌ 잘못된 예시
class CrawlerService:
    def __init__(self):
        self.logger = ConsoleLogger()  # 내부에서 생성
```

### 5. 단순한 Main 원칙
**main.py는 객체 생성과 연결만 담당한다**

- ✅ `main.py`에서 모든 어댑터를 생성
- ✅ 생성된 어댑터를 서비스에 전달
- ✅ 서비스 실행 및 정리
- ❌ `main.py`에 비즈니스 로직을 넣지 않음

```python
# ✅ 올바른 main.py
def main():
    # 1. 어댑터 생성
    logger = ConsoleLogger()
    page_provider = PlaywrightPageProvider()
    
    # 2. 서비스 생성 및 의존성 주입
    service = CrawlerService(logger=logger, page_provider=page_provider)
    
    # 3. 실행
    service.run()
```

---

## 🏗️ 아키텍처 구조

```
src/
├── core/                           # 비즈니스 로직
│   ├── domain/                     # 도메인 모델
│   │   └── models.py               # 순수 데이터 모델
│   │
│   ├── ports/                      # 포트 인터페이스 (추상화)
│   │   ├── web_scraping_ports.py   # 웹 스크래핑 포트
│   │   ├── data_ports.py           # 데이터 처리 포트
│   │   └── utility_ports.py        # 유틸리티 포트
│   │
│   └── services/                   # 서비스 계층
│       └── crawler_service.py      # 크롤링 워크플로우
│
└── infra/                          # 인프라 구현
    └── adapters/                   # 어댑터 구현체
        ├── web/                    # 웹 관련
        │   ├── playwright_page_provider.py
        │   ├── calendar_scraper_impl.py
        │   └── detail_scraper_impl.py
        │
        ├── data/                   # 데이터 관련
        │   ├── dataframe_mapper.py
        │   └── excel_exporter.py
        │
        └── utils/                  # 유틸리티 관련
            ├── date_calculator.py
            └── console_logger.py
```

### 계층별 책임

| 계층 | 책임 | 의존 방향 |
|------|------|----------|
| `core/domain` | 도메인 모델 정의 | 아무것도 의존 안 함 |
| `core/ports` | 인터페이스 정의 | `domain` 모델만 의존 |
| `core/services` | 비즈니스 로직 | `ports`, `domain` 의존 |
| `infra/adapters` | 외부 기술 구현 | `ports` 구현, `domain` 사용 |

---

## 📝 코딩 규칙

### 1. 한글 사용
- **주석**: 모든 주석은 한글로 작성
- **문서화**: docstring도 한글 사용
- **변수명/함수명**: 영어 사용 (PEP 8 준수)

```python
def scrape_calendar(self, year: int) -> ScrapeReport:
    """캘린더에서 IPO 목록을 추출합니다.
    
    Args:
        year: 크롤링할 연도
        
    Returns:
        스크래핑 결과 리포트
    """
    # 월별 페이지 이동
    for month in range(1, 13):
        self._goto_month(year, month)
```

### 2. 타입 힌팅
- 모든 함수/메서드에 타입 힌트 필수
- Python 3.10+ 문법 사용 (`list[str]` 대신 `List[str]` 허용)

```python
from typing import List, Optional

def process_stocks(stocks: List[StockInfo]) -> Optional[pd.DataFrame]:
    pass
```

### 3. 에러 처리
- 명시적인 예외 처리
- 로깅은 서비스 계층에서 처리
- 어댑터는 예외를 전파하거나 `None` 반환

```python
# 어댑터
def scrape_single(self, name: str) -> Optional[StockInfo]:
    try:
        # 스크래핑 로직
        return stock_info
    except Exception:
        return None  # 로깅은 서비스 계층에서

# 서비스
def run(self):
    stock = self.scraper.scrape_single(name)
    if stock is None:
        self.logger.warning(f"{name} 스크래핑 실패")
```

---

## 🔄 개발 워크플로우

### 1. 새로운 기능 추가 시
1. **포트 정의**: `core/ports/`에 인터페이스 추가
2. **서비스 수정**: `core/services/`에서 포트 사용
3. **어댑터 구현**: `infra/adapters/`에서 포트 구현
4. **Main 연결**: `main.py`에서 객체 생성 및 연결

### 2. 기존 기능 수정 시
1. **포트 변경**: 인터페이스 수정 필요 여부 확인
2. **어댑터 수정**: 구현체만 수정 (다른 어댑터에 영향 없음)
3. **서비스 수정**: 비즈니스 로직 변경 필요 시

### 3. 테스트 작성
1. **단위 테스트**: 각 어댑터를 독립적으로 테스트
2. **통합 테스트**: 서비스 계층 테스트 (모킹 활용)
3. **E2E 테스트**: 전체 워크플로우 테스트

---

## 🚫 금지 사항

1. ❌ **어댑터 간 직접 의존성**
   - 어댑터가 다른 어댑터를 직접 import하거나 생성하지 말 것

2. ❌ **도메인 모델에 인프라 의존성**
   - `StockInfo`에 Playwright나 Pandas 타입 사용 금지

3. ❌ **서비스에 구현체 직접 참조**
   - 서비스는 포트 인터페이스만 의존

4. ❌ **전역 상태**
   - 싱글톤 패턴, 전역 변수 사용 금지

5. ❌ **비즈니스 로직을 어댑터에 포함**
   - 어댑터는 순수하게 기술적인 구현만

---

## ✅ 체크리스트

새로운 코드를 작성할 때 다음을 확인하세요:

- [ ] 어댑터가 다른 어댑터를 직접 참조하지 않는가?
- [ ] 모든 의존성이 생성자를 통해 주입되는가?
- [ ] 포트 인터페이스를 통해 의존하는가?
- [ ] 한글 주석이 작성되었는가?
- [ ] 타입 힌트가 모든 함수에 있는가?
- [ ] 비즈니스 로직이 서비스 계층에만 있는가?
- [ ] 도메인 모델이 순수한가?

---

## 📚 참고 자료

- **Hexagonal Architecture**: 포트와 어댑터 패턴
- **Clean Architecture**: 의존성 규칙
- **Dependency Injection**: 명시적 의존성 주입 (DI 컨테이너 없이)
- **SOLID 원칙**: 특히 SRP(단일 책임 원칙), DIP(의존성 역전 원칙)
