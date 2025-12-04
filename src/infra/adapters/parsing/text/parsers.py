import re
from typing import Optional, Tuple

def parse_to_int(text: str, context: str = "") -> Optional[int]:
    """Parse text to integer, handling various formats."""
    if not text or text in ("N/A", "-"):
        return None
    
    try:
        text_no_parens = text.split("(")[0]
        cleaned = text_no_parens.replace(",", "").replace("주", "").replace("원", "").strip()
        
        for separator in ("~", ":"):
            if separator in cleaned:
                cleaned = cleaned.split(separator)[0].strip()
        
        if not cleaned or cleaned == "-":
            return None
        
        return int(float(cleaned))
    except (ValueError, Exception) as e:
        msg = f"      [경고] 정수 변환 실패: '{text}'"
        if context:
            msg += f" | 항목: {context}"
        print(msg)
        return None

def clean_stock_name(name_raw: str) -> str:
    """Clean stock name by removing unwanted patterns."""
    name_cleaned = re.sub(r"\(구\..*?\)", "", name_raw).strip()
    return name_cleaned.replace("(상장)", "").strip()

def is_spac_stock(name: str) -> bool:
    """Check if stock is a SPAC or REIT."""
    return "스팩" in name or "리츠" in name

def format_competition_rate(rate_str: str) -> str:
    """Format institutional competition rate."""
    try:
        rate_part = rate_str.split(":")[0].strip().replace(",", "")
        return f"{round(float(rate_part))}:1"
    except Exception:
        return rate_str

def extract_share_count(raw_value: str, default: str = "0") -> str:
    """Extract share count from raw string."""
    result = raw_value.split("주")[0].replace(",", "").strip()
    return result if result else default

def clean_tradable_values(count: str, percent: str) -> Tuple[str, str]:
    """Clean and validate tradable values."""
    if count in ("-", "", "　"):
        count = "N/A"
    if percent in ("-", "", "S"):
        percent = "N/A"
    
    # % 기호로 주식수/지분율 순서가 바뀌었는지 감지하고 교정
    if count.endswith("%") and not percent.endswith("%"):
        print("      [경고] 주식수와 지분율 순서가 바뀐 것으로 감지됨. 순서 교정.")
        count, percent = percent, count
    
    return count, percent