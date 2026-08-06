from abc import ABC, abstractmethod
from typing import Optional
from playwright.sync_api import Page, Locator


class TableFinderStrategy(ABC):
    """
    테이블을 찾기 위한 전략 인터페이스
    """

    @abstractmethod
    def find_table(self, page: Page) -> Optional[Locator]:
        pass


class TitleSiblingTableFinder(TableFinderStrategy):
    """
    제목(font 태그) 바로 다음 형제 테이블을 찾는 전략
    """

    def find_table(self, page: Page) -> Optional[Locator]:
        try:
            table = page.locator(
                '//font[contains(text(), "공모후 유통가능") and contains(text(), "물량")]'
                "/ancestor::*[self::td or self::th or self::div or self::p][1]"
                "/following-sibling::table[1]"
            ).first
            if table.is_visible(timeout=1500):
                print("      [정보] 전략1 성공: 제목 다음 형제 테이블 발견")
                return table
        except Exception:
            pass
        return None


class TitleFollowingTableFinder(TableFinderStrategy):
    """
    제목(font 태그) 이후에 나오는 첫 번째 테이블을 찾는 전략 (더 유연함)
    """

    def find_table(self, page: Page) -> Optional[Locator]:
        try:
            table = page.locator(
                '//font[contains(text(), "공모후 유통가능") and contains(text(), "물량")]'
                "/following::table[1]"
            ).first
            if table.is_visible(timeout=1500):
                print("      [정보] 전략2 성공: 제목 이후 첫 테이블 발견")
                return table
        except Exception:
            pass
        return None


class HeaderContentTableFinder(TableFinderStrategy):
    """
    특정 헤더 텍스트(의무보호예수, 유통가능)를 포함하는 테이블을 찾는 전략
    """

    def find_table(self, page: Page) -> Optional[Locator]:
        try:
            table = page.locator(
                "//table["
                './/td[contains(normalize-space(text()), "의무보호예수")] and '
                './/td[contains(normalize-space(text()), "유통가능")]'
                "]"
            ).last
            if table.is_visible(timeout=1500):
                print("      [정보] 전략3 성공: 헤더 구조(의무보호예수+유통가능) 일치")
                return table
        except Exception:
            pass
        return None


class RowContentTableFinder(TableFinderStrategy):
    """
    특정 행 내용(합계, 보통주, 주식수)을 포함하는 테이블을 찾는 전략
    """

    def find_table(self, page: Page) -> Optional[Locator]:
        try:
            table = page.locator(
                "//table["
                './/td[contains(text(), "합계")] and '
                './/td[contains(text(), "보통주")] and '
                'count(.//td[contains(text(), "주식수")]) >= 2'
                "]"
            ).last
            if table.is_visible(timeout=1500):
                print("      [정보] 전략4 성공: 합계 행 패턴 일치")
                return table
        except Exception:
            pass
        return None
