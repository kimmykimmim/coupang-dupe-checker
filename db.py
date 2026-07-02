# -*- coding: utf-8 -*-
"""SQLite 데이터 계층. 앱 첫 실행 시 purchases.db 를 자동 생성한다."""
import os
import sqlite3
from datetime import date

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "purchases.db")

DEFAULT_CATEGORIES = ["의류", "생활용품", "식품", "전자기기", "화장품/미용", "주방", "문구", "기타"]


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS purchases (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                name          TEXT    NOT NULL,
                category      TEXT    DEFAULT '기타',
                price         INTEGER DEFAULT 0,
                purchase_date TEXT,
                url           TEXT    DEFAULT '',
                memo          TEXT    DEFAULT '',
                created_at    TEXT    DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS categories (
                id   INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
            """
        )
    _seed_default_categories()
    _backfill_categories_from_purchases()


# ---------------------------------------------------------------- 카테고리
def list_categories():
    with get_conn() as conn:
        rows = conn.execute("SELECT name FROM categories ORDER BY id").fetchall()
    return [r["name"] for r in rows]


def add_category(name):
    name = (name or "").strip()
    if not name:
        return False
    with get_conn() as conn:
        conn.execute("INSERT OR IGNORE INTO categories (name) VALUES (?)", (name,))
    return True


def delete_category(name):
    """카테고리 목록에서만 제거한다(기존 구매 기록의 카테고리는 그대로 둔다)."""
    with get_conn() as conn:
        conn.execute("DELETE FROM categories WHERE name = ?", (name,))


def _seed_default_categories():
    if list_categories():
        return
    for c in DEFAULT_CATEGORIES:
        add_category(c)


def _backfill_categories_from_purchases():
    """구매 기록에는 있는데 카테고리 목록엔 없는 값을 목록에 채워 넣는다."""
    with get_conn() as conn:
        used = conn.execute(
            "SELECT DISTINCT category FROM purchases WHERE category IS NOT NULL AND category <> ''"
        ).fetchall()
    for r in used:
        add_category(r["category"])


# ---------------------------------------------------------------- 구매 기록
def list_purchases():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM purchases ORDER BY purchase_date DESC, id DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def add_purchase(name, category="기타", price=0, purchase_date=None, url="", memo=""):
    name = (name or "").strip()
    if not name:
        return None
    category = (category or "기타").strip() or "기타"
    add_category(category)  # 새 카테고리면 목록에 자동 등록
    if not purchase_date:
        purchase_date = date.today().isoformat()
    try:
        price = int(price) if str(price).strip() else 0
    except (TypeError, ValueError):
        price = 0
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO purchases (name, category, price, purchase_date, url, memo)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (name, category, price, purchase_date, url.strip(), memo.strip()),
        )
        return cur.lastrowid


def delete_purchase(item_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM purchases WHERE id = ?", (item_id,))


def name_exists(name):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM purchases WHERE name = ? LIMIT 1", (name.strip(),)
        ).fetchone()
    return row is not None


def seed_if_empty():
    """처음 실행하면 감이 오도록 예시 데이터 몇 개를 넣는다."""
    if list_purchases():
        return
    samples = [
        ("무지 화이트 와이셔츠 100수", "의류", 29000, "2026-03-11"),
        ("삼성 정품 C타입 고속충전기", "전자기기", 15900, "2026-04-02"),
        ("크리넥스 3겹 두루마리 휴지 30롤", "생활용품", 18900, "2026-05-20"),
        ("나이키 운동화 270", "의류", 89000, "2026-01-15"),
    ]
    for name, cat, price, d in samples:
        add_purchase(name, cat, price, d)
