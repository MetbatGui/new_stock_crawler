from typing import Dict
import pandas as pd
from core.ports.enrichment_ports import TickerMapperPort, MarketDataProviderPort
from core.ports.utility_ports import LoggerPort
from core.ports.data_ports import DataExporterPort

class EnrichmentService:
    """
    수집된 데이터에 추가 정보(시세, 성장률)를 보강하는 서비스
    """
    def __init__(
        self,
        ticker_mapper: TickerMapperPort,
        market_data_provider: MarketDataProviderPort,
        data_exporter: DataExporterPort,
        logger: LoggerPort
    ):
        self.ticker_mapper = ticker_mapper
        self.market_data_provider = market_data_provider
        self.data_exporter = data_exporter
        self.logger = logger

    def enrich_data(self, yearly_data: Dict[int, pd.DataFrame]) -> None:
        """
        데이터 보강 및 재저장
        """
        self.logger.info("=" * 60)
        self.logger.info("📈 데이터 보강 작업 시작 (OHLC, 성장률)")
        
        enriched_data = {}
        total_enriched = 0
        
        for year, df in yearly_data.items():
            if df.empty:
                continue
                
            self.logger.info(f"[{year}년] 데이터 보강 중... ({len(df)}건)")
            
            # 새로운 컬럼 초기화 (Ticker는 저장하지 않음)
            new_cols = ['시가', '고가', '저가', '종가', '수익률']
            for col in new_cols:
                if col not in df.columns:
                    df[col] = None
            
            for index, row in df.iterrows():
                try:
                    # 1. Ticker 조회 (저장하지 않고 로직 내에서만 사용)
                    # DataFrameMapper에서 'name' -> '종목명'으로 변환됨
                    stock_name = row.get('종목명')
                    if not stock_name:
                         # 혹시 'name'으로 남아있을 경우 대비
                         stock_name = row.get('name')
                    
                    if not stock_name:
                        self.logger.info(f"    - [SKIP] 종목명 찾을 수 없음")
                        continue

                    ticker = self.ticker_mapper.get_ticker(stock_name)
                    if not ticker:
                        self.logger.info(f"    - [SKIP] Ticker 찾을 수 없음: {stock_name}")
                        continue
                    
                    # 2. OHLC 조회 (상장일 기준)
                    # DataFrameMapper에서 'listing_date' -> '상장일'로 변환됨
                    listing_date_val = row.get('상장일')
                    if not listing_date_val:
                        listing_date_val = row.get('listing_date')

                    if pd.isna(listing_date_val) or listing_date_val == "N/A":
                        self.logger.info(f"    - [SKIP] 상장일 정보 없음: {stock_name}")
                        continue
                        
                    # 날짜 형식 변환 (YYYY.MM.DD -> datetime)
                    try:
                        listing_date_str = str(listing_date_val).replace(".", "-")
                        listing_date = pd.to_datetime(listing_date_str).date()
                    except Exception as e:
                        self.logger.info(f"    - [SKIP] 날짜 변환 실패: {stock_name} ({listing_date_val}) - {e}")
                        continue
                    
                    ohlc = self.market_data_provider.get_ohlc(ticker, listing_date)
                    
                    if ohlc:
                        df.at[index, '시가'] = ohlc['Open']
                        df.at[index, '고가'] = ohlc['High']
                        df.at[index, '저가'] = ohlc['Low']
                        df.at[index, '종가'] = ohlc['Close']
                        
                        # 3. 성장률 계산 (종가 / 공모가 - 1) * 100
                        # DataFrameMapper에서 'confirmed_price' -> '확정공모가'로 변환됨
                        confirmed_price_val = row.get('확정공모가')
                        if not confirmed_price_val:
                            confirmed_price_val = row.get('confirmed_price')

                        if pd.notna(confirmed_price_val) and confirmed_price_val != "":
                            try:
                                confirmed_price = float(str(confirmed_price_val).replace(",", ""))
                                if confirmed_price > 0:
                                    growth_rate = (ohlc['Close'] - confirmed_price) / confirmed_price * 100
                                    df.at[index, '수익률'] = round(growth_rate, 2)
                                    total_enriched += 1
                                    self.logger.info(f"    - [OK] {stock_name} ({ticker}): 수익률 {round(growth_rate, 2)}%")
                            except ValueError:
                                self.logger.info(f"    - [WARN] 공모가 변환 실패: {stock_name} ({confirmed_price_val})")
                    else:
                        self.logger.info(f"    - [SKIP] OHLC 데이터 없음: {stock_name} ({ticker}, {listing_date})")

                except Exception as e:
                    self.logger.error(f"    - [ERROR] {row.get('종목명', 'Unknown')} 처리 중 오류: {e}")
                    pass
            
            enriched_data[year] = df
            
        # 저장
        if enriched_data:
            self.data_exporter.export(enriched_data)
            self.logger.info(f"✅ 데이터 보강 완료 (총 {total_enriched}건 시세 추가됨)")
            self.logger.info("=" * 60)
