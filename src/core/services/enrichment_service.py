from typing import Dict
import pandas as pd
from core.services.stock_price_enricher import StockPriceEnricher
from core.ports.utility_ports import LoggerPort
from core.ports.data_ports import DataExporterPort

class EnrichmentService:
    """
    수집된 데이터에 추가 정보(시세, 성장률)를 보강하는 서비스
    """
    def __init__(
        self,
        stock_enricher: StockPriceEnricher,
        data_exporter: DataExporterPort,
        logger: LoggerPort
    ):
        self.stock_enricher = stock_enricher
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
            
            # 새로운 컬럼 초기화
            new_cols = ['시가', '고가', '저가', '종가', '수익률']
            for col in new_cols:
                if col not in df.columns:
                    df[col] = None
            
            for index, row in df.iterrows():
                try:
                    # 1. 필수 정보 추출
                    stock_name = row.get('종목명') or row.get('name')
                    listing_date_val = row.get('상장일') or row.get('listing_date')
                    confirmed_price_val = row.get('확정공모가') or row.get('confirmed_price')
                    
                    if not stock_name:
                        self.logger.info(f"    - [SKIP] 종목명 찾을 수 없음")
                        continue

                    # 2. 데이터 보강 (StockPriceEnricher 위임)
                    market_data = self.stock_enricher.get_market_data(
                        stock_name, listing_date_val, confirmed_price_val
                    )
                    
                    # 3. 결과 반영
                    if market_data['종가']:
                        df.at[index, '시가'] = market_data['시가']
                        df.at[index, '고가'] = market_data['고가']
                        df.at[index, '저가'] = market_data['저가']
                        df.at[index, '종가'] = market_data['종가']
                        
                        if market_data['수익률'] is not None:
                            df.at[index, '수익률'] = market_data['수익률']
                            total_enriched += 1
                            
                except Exception as e:
                    self.logger.error(f"    - [ERROR] {row.get('종목명', 'Unknown')} 처리 중 오류: {e}")
                    pass
            
            enriched_data[year] = df
            
        # 저장
        if enriched_data:
            self.data_exporter.export(enriched_data)
            self.logger.info(f"✅ 데이터 보강 완료 (총 {total_enriched}건 시세 추가됨)")
            self.logger.info("=" * 60)
