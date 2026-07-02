# -*- coding: utf-8 -*-
"""
SQLite 데이터 계층.

모든 데이터는 owner 로 구분한다.
- 개인용 실행(기본): owner = 'me' 하나만 사용 → 기존과 동일하게 동작.
- 데모 모드(DEMO=1): 방문자(브라우저)마다 owner 가 달라 서로 데이터가 섞이지 않는다.
"""
import os
import sqlite3
from datetime import date

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "purchases.db")
DEFAULT_OWNER = "me"
DEFAULT_CATEGORIES = ["의류", "생활용품", "식품", "전자기기", "화장품/미용", "주방", "문구", "기타"]


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _has_column(conn, table, col):
    return col in [r["name"] for r in conn.execute(f"PRAGMA table_info({table})")]


def _table_exists(conn, table):
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    return row is not None


def init_db():
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS purchases (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                owner         TEXT    NOT NULL DEFAULT 'me',
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
                id    INTEGER PRIMARY KEY AUTOINCREMENT,
                owner TEXT NOT NULL DEFAULT 'me',
                name  TEXT NOT NULL,
                UNIQUE(owner, name)
            )
            """
        )
        # --- 기존 DB(owner 없던 버전) 자동 마이그레이션 ---
        if not _has_column(conn, "purchases", "owner"):
            conn.execute("ALTER TABLE purchases ADD COLUMN owner TEXT NOT NULL DEFAULT 'me'")
        if _table_exists(conn, "categories") and not _has_column(conn, "categories", "owner"):
            conn.execute(
                """CREATE TABLE categories_new (
                       id INTEGER PRIMARY KEY AUTOINCREMENT,
                       owner TEXT NOT NULL DEFAULT 'me',
                       name TEXT NOT NULL, UNIQUE(owner, name))"""
            )
            conn.execute("INSERT INTO categories_new (owner, name) SELECT 'me', name FROM categories")
            conn.execute("DROP TABLE categories")
            conn.execute("ALTER TABLE categories_new RENAME TO categories")


# ---------------------------------------------------------------- 카테고리
def list_categories(owner=DEFAULT_OWNER):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT name FROM categories WHERE owner = ? ORDER BY id", (owner,)
        ).fetchall()
    return [r["name"] for r in rows]


def add_category(owner, name):
    name = (name or "").strip()
    if not name:
        return False
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO categories (owner, name) VALUES (?, ?)", (owner, name)
        )
    return True


def delete_category(owner, name):
    with get_conn() as conn:
        conn.execute("DELETE FROM categories WHERE owner = ? AND name = ?", (owner, name))


# ---------------------------------------------------------------- 구매 기록
def list_purchases(owner=DEFAULT_OWNER):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM purchases WHERE owner = ? ORDER BY purchase_date DESC, id DESC",
            (owner,),
        ).fetchall()
    return [dict(r) for r in rows]


def add_purchase(owner, name, category="기타", price=0, purchase_date=None, url="", memo=""):
    name = (name or "").strip()
    if not name:
        return None
    category = (category or "기타").strip() or "기타"
    add_category(owner, category)  # 새 카테고리면 자동 등록
    if not purchase_date:
        purchase_date = date.today().isoformat()
    try:
        price = int(price) if str(price).strip() else 0
    except (TypeError, ValueError):
        price = 0
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO purchases (owner, name, category, price, purchase_date, url, memo)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (owner, name, category, price, purchase_date, url.strip(), memo.strip()),
        )
        return cur.lastrowid


def delete_purchase(owner, item_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM purchases WHERE id = ? AND owner = ?", (item_id, owner))


def name_exists(owner, name):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM purchases WHERE owner = ? AND name = ? LIMIT 1",
            (owner, name.strip()),
        ).fetchone()
    return row is not None


# ---------------------------------------------------------------- 시딩
def seed_categories(owner):
    if not list_categories(owner):
        for c in DEFAULT_CATEGORIES:
            add_category(owner, c)


def seed_samples(owner):
    """해당 owner 에게 예시 구매가 하나도 없으면 4건 넣는다."""
    if list_purchases(owner):
        return
    samples = [
        ("무지 화이트 와이셔츠 100수", "의류", 29000, "2026-03-11"),
        ("삼성 정품 C타입 고속충전기", "전자기기", 15900, "2026-04-02"),
        ("크리넥스 3겹 두루마리 휴지 30롤", "생활용품", 18900, "2026-05-20"),
        ("나이키 운동화 270", "의류", 89000, "2026-01-15"),
    ]
    for name, cat, price, d in samples:
        add_purchase(owner, name, cat, price, d)


def seed_owner(owner):
    """카테고리·예시 구매를 (없을 때만) 채운다. 여러 번 불러도 안전."""
    seed_categories(owner)
    seed_samples(owner)
