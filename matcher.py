# -*- coding: utf-8 -*-
"""
유사도 엔진 (v2).

기본(항상 동작, 외부 의존성 없음):
  - 정규화: 브랜드/용량/색상/마케팅 문구 제거 → 핵심 단어만 남김
  - 동의어 사전: '와이셔츠=셔츠=남방' 같은 표현 차이 흡수
  - 여러 신호를 조합: 문자순서(오타/어순) + 2/3-gram + 단어겹침 + 포함관계

선택(설치돼 있으면 자동 사용): 한국어 문장 임베딩으로 '의미' 유사도까지 반영
  pip install sentence-transformers
  -> 'C타입 충전기' 와 '아이폰 라이트닝 케이블' 처럼 사전에 없는 관계도 잡아냄.
  설치돼 있지 않으면 조용히 무시하고 기본 엔진만 사용한다.
"""
import re
from difflib import SequenceMatcher

# --- 동의어 그룹: 한 그룹 안의 단어는 같은 물건으로 취급한다 -------------------
SYNONYM_GROUPS = [
    {"와이셔츠", "셔츠", "남방", "드레스셔츠", "정장셔츠"},
    {"티셔츠", "티", "반팔", "반팔티", "긴팔티", "면티"},
    {"바지", "슬랙스", "청바지", "면바지", "팬츠", "슬랙"},
    {"후드", "후드티", "후드집업", "맨투맨", "스웨트셔츠"},
    {"양말", "발목양말", "니삭스"},
    {"칫솔"}, {"치약"},
    {"휴지", "화장지", "두루마리휴지", "롤휴지", "각티슈"},
    {"물티슈", "물수건"},
    {"세제", "세탁세제", "빨래세제", "액체세제"},
    {"주방세제", "설거지세제"},
    {"샴푸"}, {"린스", "컨디셔너"},
    {"이어폰", "무선이어폰", "블루투스이어폰", "이어버드"},
    {"충전기", "충전케이블", "케이블", "usb케이블", "c타입케이블", "고속충전기", "라이트닝케이블"},
    {"보조배터리", "파워뱅크"},
    {"마우스", "무선마우스"},
    {"키보드", "기계식키보드"},
    {"텀블러", "보온병", "물통", "물병", "보틀"},
    {"우산", "장우산", "자동우산"},
    {"생수", "물", "먹는샘물"},
]

_WORD_TO_GROUP = {}
for _g in SYNONYM_GROUPS:
    _rep = sorted(_g)[0]
    for _w in _g:
        _WORD_TO_GROUP[_w.replace(" ", "")] = _rep
_GROUP_REPS = set(_WORD_TO_GROUP.values())

NOISE_WORDS = [
    "대용량", "리필", "세트", "묶음", "낱개", "정품", "무료배송", "당일발송",
    "행사", "특가", "증정", "본품", "구성", "신상", "인기", "베스트",
    "쿠팡", "로켓배송", "국내산", "사은품", "기획", "한정", "정품인증",
]
COLOR_WORDS = [
    "블랙", "화이트", "레드", "블루", "그레이", "그린", "네이비", "베이지",
    "핑크", "옐로우", "브라운", "카키", "검정", "흰색", "빨강", "파랑", "회색",
]
_UNIT_PATTERN = re.compile(
    r"\d+\s*(ml|l|g|kg|개입|매입|개|매|팩|롤|장|호|cm|mm|인치|p|구|겹|박스|세트|병|캔|포|입|수)",
    re.IGNORECASE,
)


def normalize(text: str) -> str:
    t = (text or "").lower()
    t = re.sub(r"\[.*?\]|\(.*?\)|\{.*?\}", " ", t)
    t = _UNIT_PATTERN.sub(" ", t)
    t = re.sub(r"[^0-9a-z가-힣]", " ", t)
    for w in NOISE_WORDS + COLOR_WORDS:
        t = t.replace(w, " ")
    t = re.sub(r"\d+", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _canonical_tokens(norm_text: str) -> set:
    return {_WORD_TO_GROUP.get(tok, tok) for tok in norm_text.split()}


def _ngrams(s: str, n: int) -> set:
    s = s.replace(" ", "")
    if len(s) < n:
        return {s} if s else set()
    return {s[i:i + n] for i in range(len(s) - n + 1)}


def _jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


# -------------------------------------------------- 선택적 의미(임베딩) 유사도
_semantic_model = None
_semantic_tried = False


def _get_semantic_model():
    """sentence-transformers 가 설치돼 있으면 한국어 모델을 지연 로딩한다."""
    global _semantic_model, _semantic_tried
    if _semantic_tried:
        return _semantic_model
    _semantic_tried = True
    try:
        from sentence_transformers import SentenceTransformer
        _semantic_model = SentenceTransformer("jhgan/ko-sroberta-multitask")
    except Exception:
        _semantic_model = None  # 미설치/오프라인 → 기본 엔진만 사용
    return _semantic_model


def semantic_available() -> bool:
    return _get_semantic_model() is not None


def _semantic_similarity(a: str, b: str):
    model = _get_semantic_model()
    if model is None:
        return None
    try:
        import numpy as np
        ea, eb = model.encode([a, b])
        cos = float(np.dot(ea, eb) / (np.linalg.norm(ea) * np.linalg.norm(eb) + 1e-9))
        return (cos + 1.0) / 2.0  # -1..1 → 0..1
    except Exception:
        return None


# -------------------------------------------------- 최종 유사도
def _lexical_similarity(a: str, b: str) -> float:
    na, nb = normalize(a), normalize(b)
    if not na or not nb:
        return 0.0
    ta, tb = _canonical_tokens(na), _canonical_tokens(nb)

    seq = SequenceMatcher(None, na, nb).ratio()       # 문자 순서
    bg = _jaccard(_ngrams(na, 2), _ngrams(nb, 2))     # 2-gram
    tg = _jaccard(_ngrams(na, 3), _ngrams(nb, 3))     # 3-gram
    tok = _jaccard(ta, tb)                             # 단어(동의어 반영)
    score = max(seq, bg, tg, tok)

    inter = ta & tb
    if inter & _GROUP_REPS:  # 같은 '종류'의 물건(동의어 그룹 일치) → 신뢰도 높음
        cont = len(inter) / min(len(ta), len(tb))      # 포함 정도
        score = max(score, 0.85 + 0.10 * cont)         # 최대 0.95
    return min(1.0, round(score, 3))


def similarity(a: str, b: str) -> float:
    """두 제품명의 유사도 0.0~1.0. 의미 모델이 있으면 함께 반영한다."""
    score = _lexical_similarity(a, b)
    sem = _semantic_similarity(a, b)
    if sem is not None and sem >= 0.72:   # 확실히 높을 때만 반영(오탐 방지)
        score = max(score, round(sem, 3))
    return min(1.0, score)


# 경고 등급 임계값
STRONG_THRESHOLD = 0.85   # 사실상 동일 → 빨강
WARN_THRESHOLD = 0.60     # 유사 → 노랑


def level_of(score: float) -> str:
    if score >= STRONG_THRESHOLD:
        return "strong"
    if score >= WARN_THRESHOLD:
        return "warn"
    return "none"


def find_matches(query_name: str, items: list, category: str = "") -> list:
    results = []
    for it in items:
        score = similarity(query_name, it["name"])
        if category and it.get("category") and category == it["category"]:
            score = min(1.0, score + 0.10)   # 같은 카테고리 가산점
        if score >= WARN_THRESHOLD:
            enriched = dict(it)
            enriched["score"] = round(score, 3)
            enriched["level"] = level_of(score)
            results.append(enriched)
    results.sort(key=lambda x: x["score"], reverse=True)
    return results


if __name__ == "__main__":
    print("의미 모델 사용:", semantic_available())
    samples = [
        ("무지 화이트 와이셔츠 100수", "남성 정장 셔츠 네이비"),
        ("삼성 정품 C타입 고속충전기 2개입", "usb c타입 충전케이블"),
        ("크리넥스 3겹 두루마리 휴지 30롤", "화장지 대용량 롤휴지"),
        ("아이폰 라이트닝 케이블 1m", "C타입 고속 충전기"),
        ("나이키 운동화 270", "크리넥스 물티슈"),
    ]
    for a, b in samples:
        print(f"{similarity(a, b):.2f}  |  {a}  <->  {b}")
