"""
Playwright Page 제공 어댑터
"""

from playwright.sync_api import Browser, Page, Playwright, sync_playwright
from core.ports.web_scraping_ports import PageProvider
from config import config


class PlaywrightPageProvider(PageProvider):
    """
    Playwright 브라우저 생명주기 관리

    원칙 준수:
    - 다른 어댑터를 모름 ✅
    - Page 객체 제공만 담당
    """

    def __init__(self, headless: bool = config.HEADLESS):
        self.headless = headless
        self.playwright: Playwright | None = None
        self.browser: Browser | None = None
        self.page: Page | None = None

    def setup(self) -> None:
        """Playwright 초기화"""
        try:
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(headless=self.headless)
            self.page = self.browser.new_page()
        except Exception as e:
            print(f"Playwright 브라우저 시작 중 오류 발생: {e}")
            print("   [팁] 'playwright install' 명령어를 실행했는지 확인하세요.")
            raise

    def get_page(self) -> Page:
        """Page 객체 반환"""
        if self.page is None:
            raise RuntimeError("setup()을 먼저 호출하세요")
        return self.page

    def cleanup(self) -> None:
        """리소스 정리"""
        if self.page:
            self.page.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
