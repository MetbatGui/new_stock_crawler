"""
DataFrame 매퍼 구현
"""
from typing import List
import pandas as pd

from core.ports.data_ports import DataMapperPort
from core.domain.models import StockInfo


class DataFrameMapper(DataMapperPort):
    """
    StockInfo 리스트를 Pandas DataFrame으로 변환하는 어댑터
    """
    
    # 컬럼명 매핑 (영문 필드명 -> 한글 컬럼명)
    COLUMN_MAPPING = {
        "name": "종목명",
        "url": "URL",
        "market_segment": "시장구분",
        "sector": "업종",
        "revenue": "매출액(백만원)",
        "profit_pre_tax": "법인세비용차감전(백만원)",
        "net_profit": "순이익(백만원)",
        "capital": "자본금(백만원)",
        "total_shares": "총공모주식수",
        "par_value": "액면가",
        "desired_price_range": "희망공모가액",
        "confirmed_price": "확정공모가",
        "offering_amount": "공모금액(백만원)",
        "underwriter": "주간사",
        "listing_date": "상장일",
        "competition_rate": "기관경쟁률",
        "emp_shares": "우리사주조합",
        "inst_shares": "기관투자자",
        "retail_shares": "일반청약자",
        "tradable_shares_count": "유통가능물량(주)",
        "tradable_shares_percent": "유통가능물량(%)",
        # 시세 정보
        "open_price": "시가",
        "high_price": "고가",
        "low_price": "저가",
        "close_price": "종가",
        "growth_rate": "수익률(%)",
    }
    
    def to_dataframe(self, stocks: List[StockInfo]) -> pd.DataFrame:
        """StockInfo 리스트를 DataFrame으로 변환"""
        if not stocks:
            return pd.DataFrame(columns=self.COLUMN_MAPPING.values())
        
        # 객체를 딕셔너리로 변환
        data = [stock.__dict__ for stock in stocks]
        
        # DataFrame 생성
        df = pd.DataFrame(data)
        
        # 컬럼명 변경
        df = df.rename(columns=self.COLUMN_MAPPING)
        
        # 정의된 컬럼만 선택 (순서 보장)
        columns = list(self.COLUMN_MAPPING.values())
        
        # 없는 컬럼이 있을 경우를 대비해 intersection 사용
        existing_columns = [col for col in columns if col in df.columns]
        df = df[existing_columns]
        
        return df
