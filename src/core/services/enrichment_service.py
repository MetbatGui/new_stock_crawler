from datetime import datetime, time
from typing import Dict, Set
import pandas as pd
from core.ports.enrichment_ports import StockEnricherPort
from core.ports.utility_ports import LoggerPort
from core.ports.repository_ports import RepositoryPort

# 상장일 장마감(15:30) 후 KRX 시세 확정을 기다리는 버퍼
ENRICH_CUTOFF_TIME = time(15, 50)


class EnrichmentService:
    """
    수집된 데이터에 추가 정보(시세, 성장률)를 보강하는 서비스

    보강 결과는 RepositoryPort(SQLite)에 upsert됩니다.
    이미 채워진 행과 아직 상장일 컷오프 전인 행은 건너뛰므로 재실행이 안전(idempotent)합니다.
    """

    def __init__(
        self,
        stock_enricher: StockEnricherPort,
        repository: RepositoryPort,
        logger: LoggerPort,
    ):
        self.stock_enricher = stock_enricher
        self.repository = repository
        self.logger = logger

    def enrich_data(self, yearly_data: Dict[int, pd.DataFrame]) -> Set[int]:
        """
        데이터 보강 및 저장소에 upsert

        Args:
            yearly_data: {연도: DataFrame} 로드된 기존 데이터

        Returns:
            실제로 1건 이상 갱신되어 저장까지 이어진 연도 집합
        """
        self.logger.info("=" * 60)
        self.logger.info("📈 데이터 보강 작업 시작 (OHLC, 성장률)")

        total_enriched = 0
        changed_years: Set[int] = set()

        for year, df in yearly_data.items():
            if df.empty:
                continue

            df = df.copy()
            year_changed = False
            self.logger.info(f"[{year}년] 데이터 보강 중... ({len(df)}건)")

            new_cols = ["시가", "고가", "저가", "종가", "수익률(%)"]
            for col in new_cols:
                if col not in df.columns:
                    df[col] = None

            for index, row in df.iterrows():
                try:
                    stock_name = row.get("종목명") or row.get("name")
                    listing_date_val = row.get("상장일") or row.get("listing_date")
                    confirmed_price_val = row.get("확정공모가") or row.get(
                        "confirmed_price"
                    )

                    if pd.isna(stock_name) or not stock_name:
                        self.logger.info("    - [SKIP] 종목명 찾을 수 없음")
                        continue

                    if pd.notna(row.get("종가")):
                        continue  # 이미 보강된 행 — 재조회하지 않음

                    if not self._is_past_cutoff(listing_date_val):
                        continue  # 상장일 15:50 컷오프 전 — 아직 시세 미확정

                    market_data = self.stock_enricher.get_market_data(
                        stock_name, listing_date_val, confirmed_price_val
                    )

                    if market_data["종가"]:
                        df.at[index, "시가"] = market_data["시가"]
                        df.at[index, "고가"] = market_data["고가"]
                        df.at[index, "저가"] = market_data["저가"]
                        df.at[index, "종가"] = market_data["종가"]
                        year_changed = True

                        if market_data["수익률(%)"] is not None:
                            df.at[index, "수익률(%)"] = market_data["수익률(%)"]
                            total_enriched += 1

                except Exception as e:
                    self.logger.error(
                        f"    - [ERROR] {row.get('종목명', 'Unknown')} 처리 중 오류: {e}"
                    )

            # 실제로 갱신된 연도만 SQLite upsert
            if year_changed:
                self.repository.save(year, df)
                changed_years.add(year)

        self.logger.info(f"✅ 데이터 보강 완료 (총 {total_enriched}건 시세 추가됨)")
        self.logger.info("=" * 60)
        return changed_years

    def _is_past_cutoff(self, listing_date_val) -> bool:
        """상장일 15:50 컷오프가 지났는지 확인 (장마감 후 시세 확정 대기 버퍼)"""
        if not listing_date_val or listing_date_val == "N/A":
            return False
        try:
            listing_date_str = str(listing_date_val).replace(".", "-")
            listing_date = pd.to_datetime(listing_date_str).date()
        except Exception:
            return False
        return datetime.combine(listing_date, ENRICH_CUTOFF_TIME) <= datetime.now()
