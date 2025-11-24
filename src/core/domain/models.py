# src/domain/models.py
from dataclasses import dataclass
from typing import List, Tuple, Optional 

# -----------------------------------------------------------------
# ▼ [수정] 요청하신 10개 필드의 타입을 int | None 으로 변경
# -----------------------------------------------------------------
@dataclass(frozen=True)
class StockInfo:
    """
    1차, 2차 크롤링을 통해 수집한 모든 세부 정보를 담는 데이터 클래스
    """
    
    # 1차 수집 정보 (식별자)
    name: str                       # 종목명
    url: str                        # 세부 정보 페이지 URL

    # 2차 수집: 기업개요 (Table 1)
    market_segment: str             # 시장구분 (str)
    sector: str                     # 업종 (str)
    revenue: int | None             # 매출액 (int)
    profit_pre_tax: int | None      # 법인세차감전이익 (int)
    net_profit: int | None          # 순이익 (int)
    capital: int | None             # 자본금 (int)

    # 2차 수집: 공모정보 (Table 2)
    total_shares: int | None        # 총공모주식수 (int)
    par_value: int | None           # 액면가 (int)
    desired_price_range: str        # 희망공모가액 (str)
    confirmed_price: int | None     # 확정공모가 (int)
    offering_amount: int | None     # 공모금액 (int)
    underwriter: str                # 주간사 (str)

    # 2차 수집: 공모청약일정 (Table 3)
    listing_date: str               # 상장일 (str)
    competition_rate: str           # 기관경쟁률 (str)
    emp_shares: int                 # 우리사주조합 (str) - 요청 목록에 없으므로 str 유지
    inst_shares: int | None         # 기관투자자 (int)
    retail_shares: int | None       # 일반청약자 (int)

    # 2차 수집: 주주현황 (Table 4)
    tradable_shares_count: str      # 유통가능물량 (str) - 요청 목록에 없으므로 str 유지
    tradable_shares_percent: str    # 유통가능물량지분율 (str) - 요청 목록에 없으므로 str 유지


# -----------------------------------------------------------------
# ▼ [변경 없음] ScrapeReport는 1차 수집 결과(작업 목록)를 담음
# -----------------------------------------------------------------
@dataclass(frozen=True)
class ScrapeReport:
    """
    1차 크롤링 결과를 요약하는 리포트
    """
    final_stock_count: int      
    spack_filtered_count: int   
    results: List[Tuple[str, str]] # (종목명, href)