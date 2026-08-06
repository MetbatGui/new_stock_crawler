import os
import requests  # type: ignore
import logging
from typing import List, Dict, Any, Optional
from datetime import date, timedelta

from core.ports.enrichment_ports import TickerMapperPort, MarketDataProviderPort

logger = logging.getLogger("crawler")

class KrxNativeAdapter(TickerMapperPort, MarketDataProviderPort):
    """
    KRX 정보데이터시스템(data.krx.co.kr)에서 직접 데이터를 스크래핑하는 어댑터.
    """
    
    BASE_URL = "https://data.krx.co.kr"
    
    def __init__(self, mbr_id: Optional[str] = None, pw: Optional[str] = None):
        from config import config
        self.mbr_id = mbr_id or config.KRX_USERNAME
        self.pw = pw or config.KRX_PASSWORD
        self.session = requests.Session()
        self.is_logged_in = False
        self._ticker_cache: Dict[str, Dict[str, str]] = {}
        self._market_data_cache: Dict[str, Dict[str, Dict[str, Any]]] = {}
        
        self.otp_url = f"{self.BASE_URL}/comm/fileDn/GenerateOTP/generate.cmd"
        self.download_url = f"{self.BASE_URL}/comm/fileDn/download_excel/download.cmd"
        self.api_url = f"{self.BASE_URL}/comm/bldAttendant/getJsonData.cmd"

        # 기본 헤더 설정
        self._UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        self._REF = f"{self.BASE_URL}/contents/MDC/MDI/mdiLoader/index.cmd?menuId=MDC0201"
        self.session.headers.update({
            "User-Agent": self._UA,
            "Referer": self._REF,
            "X-Requested-With": "XMLHttpRequest"
        })

    def _login(self) -> bool:
        """KRX 정보데이터시스템 로그인 세션을 획득한다."""
        if not self.mbr_id or not self.pw:
            logger.error("[KRX] 로그인 계정 정보(KRX_USERNAME/PASSWORD)가 설정되지 않았습니다.")
            return False

        login_url = f"{self.BASE_URL}/contents/MDC/COMS/client/MDCCOMS001D1.cmd"
        payload = {"mbrId": self.mbr_id, "pw": self.pw}
        
        try:
            # 초기 페이지 접근으로 세션 초기화
            self.session.get(self._REF)
            
            resp = self.session.post(login_url, data=payload)
            data = resp.json()

            if data.get("_error_code") == "CD011": # 중복 로그인 처리
                payload["skipDup"] = "Y"
                resp = self.session.post(login_url, data=payload)
                data = resp.json()

            if data.get("_error_code") == "CD001":
                logger.info(f"[KRX] 로그인 성공: {self.mbr_id}")
                self.is_logged_in = True
                return True
            else:
                logger.error(f"[KRX] 로그인 실패: {data}")
                return False
        except Exception as e:
            logger.error(f"[KRX] 로그인 프로세스 중 오류 발생: {e}")
            return False

    def _fetch_all_markets(self, target_date_str: str) -> List[Dict[str, Any]]:
        """MDCSTAT01501 데이터를 조회합니다. (JSON 전용)"""
        if target_date_str in self._market_data_cache:
            return list(self._market_data_cache[target_date_str].values())

        if not self.is_logged_in:
            if not self._login():
                return []

        try:
            # 시세 조회용 페이로드
            payload = {
                'bld': 'dbms/MDC/STAT/standard/MDCSTAT01501',
                'locale': 'ko_KR',
                'mktId': 'ALL',
                'trdDd': target_date_str,
                'share': '1',
                'money': '1',
                'csvxls_isNo': 'false',
            }
            
            res = self.session.post(self.api_url, data=payload, timeout=15)
            if res.status_code != 200: 
                return []
            
            try:
                data = res.json()
            except Exception:
                return []
            
            items = data.get('OutBlock_1', []) or data.get('output', [])
            
            if items:
                dt_ticker, dt_market, dt_name = {}, {}, {}
                for row in items:
                    name, ticker = row.get('ISU_ABBRV', ''), row.get('ISU_SRT_CD', '')
                    if ticker:
                        dt_market[ticker] = row
                    if name:
                        dt_ticker[name] = ticker
                        dt_name[name] = row
                
                self._ticker_cache[target_date_str] = dt_ticker
                self._market_data_cache[target_date_str] = dt_market
                self._market_data_cache[f"{target_date_str}_by_name"] = dt_name
                logger.info(f"      [KRX] {target_date_str} 전종목 시세 캐싱 완료 ({len(items)}건)")
            return items
        except Exception:
            return []

    def get_ticker(self, stock_name: str) -> Optional[str]:
        # 당일 데이터부터 최근 7일간 시도 (영업일 고려)
        target_dates = []
        base_date = date.today()
        for i in range(7):
            target_dates.append((base_date - timedelta(days=i)).strftime("%Y%m%d"))
            
        t_map = {}
        for d_str in target_dates:
            if d_str not in self._ticker_cache:
                self._fetch_all_markets(d_str)
            
            t_map = self._ticker_cache.get(d_str, {})
            if t_map:
                break
        
        if stock_name in t_map: return t_map[stock_name]
        cln = stock_name.replace("(주)", "").strip()
        return t_map.get(cln)

    def get_ohlc(
        self, 
        ticker: Optional[str] = None, 
        name: Optional[str] = None, 
        target_date: date = None
    ) -> Optional[Dict[str, int]]:
        if target_date is None:
            return None
            
        d_str = target_date.strftime("%Y%m%d")
        if d_str not in self._market_data_cache:
            self._fetch_all_markets(d_str)
        
        # 1. 티커로 조회
        row = None
        if ticker:
            row = self._market_data_cache.get(d_str, {}).get(ticker)
        
        # 2. 이름으로 조회 시도
        if not row and name:
            name_map = self._market_data_cache.get(f"{d_str}_by_name", {})
            row = name_map.get(name)
            # (주) 제거 후 재검색
            if not row and "(주)" in name:
                cln = name.replace("(주)", "").strip()
                row = name_map.get(cln)
        
        if not row:
            return None

        try:
            def _p(v): return int(float(str(v).replace(',', '')))
            op, cl = _p(row.get('TDD_OPNPRC', '0')), _p(row.get('TDD_CLSPRC', '0'))
            if op == 0 and cl == 0: 
                return None
            return {
                "Open": op, 
                "High": _p(row.get('TDD_HGPRC', '0')), 
                "Low": _p(row.get('TDD_LWPRC', '0')), 
                "Close": cl
            }
        except Exception:
            return None
