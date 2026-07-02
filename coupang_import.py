# -*- coding: utf-8 -*-
"""
쿠팡 '주문목록' 페이지에서 복사한 텍스트를 파싱한다.

쿠팡은 로그인/크롤링을 막아두고 약관상 자동 수집도 제한하므로,
사용자가 주문목록 화면을 직접 복사해서 붙여넣으면 그 텍스트에서
상품명 / 가격 / 날짜 / 수량을 최대한 뽑아낸다(best-effort).
결과는 화면에서 확인·수정한 뒤 등록하므로 파싱이 조금 틀려도 안전하다.
"""
import re

_DATE_RE = re.compile(r"(20\d{2})[.\-/년\s]+(\d{1,2})[.\-/월\s]+(\d{1,2})")
_PRICE_RE = re.compile(r"([\d,]{2,})\s*원")
_QTY_RE = re.compile(r"(\d+)\s*개")

# 상품명이 아닌 UI/상태 문구(이 단어가 들어간 줄은 상품명 후보에서 제외)
_NOISE_KEYWORDS = [
    "배송완료", "배송중", "배송예정", "주문접수", "결제완료", "배송조회",
    "장바구니", "교환", "반품", "리뷰", "재구매", "주문 상세", "상세보기",
    "도착 보장", "도착보장", "무료배송", "취소", "환불", "쿠폰", "적립",
    "더보기", "판매자", "영수증", "송장", "주문번호", "총 결제", "결제금액",
    "옵션", "선택", "배송지", "카드", "간편결제", "포인트", "와우",
]


def _to_iso(m):
    y, mo, d = m.group(1), int(m.group(2)), int(m.group(3))
    return f"{y}-{mo:02d}-{d:02d}"


def _is_noise(line):
    return any(k in line for k in _NOISE_KEYWORDS)


def _is_date_line(line):
    m = _DATE_RE.search(line)
    # 날짜만 있거나 '배송완료' 등 상태와 함께 있는 짧은 줄
    return bool(m) and len(line) <= 30


def _is_price_line(line):
    m = _PRICE_RE.search(line)
    if not m:
        return False
    # 가격/수량 위주의 짧은 줄 (상품명 안의 '원' 오인 방지)
    non_price = _PRICE_RE.sub("", line)
    non_price = _QTY_RE.sub("", non_price).strip(" ·|,")
    return len(line) <= 30 and len(non_price) <= 4


def _looks_like_product(line):
    if len(line) < 5:
        return False
    if _is_noise(line) or _is_date_line(line) or _is_price_line(line):
        return False
    # 한글/영문 글자가 충분히 있어야 상품명으로 인정
    letters = re.findall(r"[가-힣a-zA-Z]", line)
    return len(letters) >= 4


def parse_orders(text: str) -> list:
    """붙여넣은 텍스트 → [{name, price, quantity, date}] 리스트."""
    items = []
    cur = None
    last_date = None

    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line:
            continue

        if _is_date_line(line):
            last_date = _to_iso(_DATE_RE.search(line))
            if cur and not cur["date"]:
                cur["date"] = last_date
            continue

        if _is_price_line(line):
            if cur:
                pm = _PRICE_RE.search(line)
                cur["price"] = int(pm.group(1).replace(",", ""))
                qm = _QTY_RE.search(line)
                if qm:
                    cur["quantity"] = int(qm.group(1))
            continue

        if _is_noise(line):
            continue

        if _looks_like_product(line):
            cur = {"name": line, "price": 0, "quantity": 1, "date": last_date}
            items.append(cur)

    # 같은 텍스트 안 중복 상품명 제거(첫 등장만 유지)
    seen, deduped = set(), []
    for it in items:
        if it["name"] in seen:
            continue
        seen.add(it["name"])
        deduped.append(it)
    return deduped


if __name__ == "__main__":
    sample = """
    2026.06.21 배송완료
    6월 22일(월) 도착 보장
    코멧 3겹 데코 앤 소프트 화장지 30m, 30롤
    14,900원 · 1개
    배송조회  |  교환, 반품 신청
    장바구니 담기

    2026.06.15 배송완료
    남성 슬림핏 옥스포드 셔츠 긴팔 네이비
    23,900원 · 2개
    리뷰 쓰기
    """
    for it in parse_orders(sample):
        print(it)
