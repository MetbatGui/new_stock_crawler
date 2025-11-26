# src/domain/models.py
from dataclasses import dataclass
from typing import List, Tuple, Optional 

@dataclass(frozen=True)
class StockInfo:
    """
    1차, 2차 크롤링을 통해 수집한 모든 세부 정보를 담는 데이터 클래스
    """
    
    # 1차 수집 정보 (식별자)
    name: str                       # 종목명
    url: str                        # 세부 정보 페이지 URL

    # 2차 수집: 기업개요 (Table 1)
    market_segment: str             # 시장구분
    sector: str                     # 업종
    revenue: int | None             # 매출액
    profit_pre_tax: int | None      # 법인세차감전이익
    net_profit: int | None          # 순이익
    capital: int | None             # 자본금

    # 2차 수집: 공모정보 (Table 2)
    total_shares: int | None        # 총공모주식수
    par_value: int | None           # 액면가
    desired_price_range: str        # 희망공모가액
    confirmed_price: int | None     # 확정공모가
    offering_amount: int | None     # 공모금액
    underwriter: str                # 주간사

    # 2차 수집: 공모청약일정 (Table 3)
    listing_date: str               # 상장일
    competition_rate: str           # 기관경쟁률
    emp_shares: int                 # 우리사주조합
    inst_shares: int | None         # 기관투자자
    retail_shares: int | None       # 일반청약자

    # 2차 수집: 주주현황 (Table 4)
    tradable_shares_count: str      # 유통가능물량
    tradable_shares_percent: str    # 유통가능물량지분율
    
    # 시세 정보 (Enrichment - FDR)
    open_price: int | None = None       # 시가 (상장일 기준)
    high_price: int | None = None       # 고가 (상장일 기준)
    low_price: int | None = None        # 저가 (상장일 기준)
    close_price: int | None = None      # 종가 (상장일 기준)
    growth_rate: float | None = None    # 수익률 (%) = (종가/공모가-1)*100


@dataclass(frozen=True)
class ScrapeReport:
    """
    1차 크롤링 결과를 요약하는 리포트
    """
    final_stock_count: int      
    spack_filtered_count: int   
    results: List[Tuple[str, str]] # (종목명, href)