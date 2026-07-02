# -*- coding: utf-8 -*-
"""쿠팡 중복구매 방지기 - Flask 웹앱."""
import os
import socket
import secrets

from flask import Flask, render_template, request, redirect, url_for, jsonify, session

import db
import matcher
import coupang_import

app = Flask(__name__)
# 데모 모드: DEMO=1 이면 방문자(브라우저)마다 데이터를 분리한다(공개 배포용).
DEMO_MODE = os.environ.get("DEMO", "").lower() in ("1", "true", "yes", "on")
app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(16)


def current_owner():
    """지금 요청의 데이터 소유자. 개인용은 'me', 데모는 브라우저별 세션 id."""
    if not DEMO_MODE:
        return db.DEFAULT_OWNER
    sid = session.get("sid")
    if not sid:
        sid = secrets.token_hex(8)
        session["sid"] = sid
    return sid


@app.before_request
def _ensure_demo_seed():
    # 데모 모드에서는 방문자마다 처음 들어올 때 예시 데이터를 채워준다.
    if DEMO_MODE and request.endpoint != "static":
        db.seed_owner(current_owner())


@app.route("/")
def index():
    owner = current_owner()
    return render_template(
        "index.html",
        purchases=db.list_purchases(owner),
        categories=db.list_categories(owner),
        semantic=matcher.semantic_available(),
        demo=DEMO_MODE,
    )


@app.route("/api/check", methods=["POST"])
def api_check():
    data = request.get_json(force=True)
    name = (data.get("name") or "").strip()
    category = (data.get("category") or "").strip()
    if not name:
        return jsonify({"ok": False, "error": "제품명을 입력하세요."}), 400
    matches = matcher.find_matches(name, db.list_purchases(current_owner()), category)
    top = matches[0]["level"] if matches else "none"
    return jsonify({"ok": True, "query": name, "verdict": top, "matches": matches})


@app.route("/add", methods=["POST"])
def add():
    f = request.form
    if (f.get("name") or "").strip():
        db.add_purchase(
            current_owner(),
            name=f.get("name"),
            category=f.get("category", "기타"),
            price=f.get("price", 0),
            purchase_date=f.get("purchase_date") or None,
            url=f.get("url", ""),
            memo=f.get("memo", ""),
        )
    return redirect(url_for("index"))


@app.route("/delete/<int:item_id>", methods=["POST"])
def delete(item_id):
    db.delete_purchase(current_owner(), item_id)
    return redirect(url_for("index"))


# ---------------------------------------------------------------- 카테고리 관리
@app.route("/category/add", methods=["POST"])
def category_add():
    db.add_category(current_owner(), request.form.get("name", ""))
    return redirect(url_for("index"))


@app.route("/category/delete", methods=["POST"])
def category_delete():
    db.delete_category(current_owner(), request.form.get("name", ""))
    return redirect(url_for("index"))


# ---------------------------------------------------------------- 쿠팡 가져오기
@app.route("/import", methods=["POST"])
def import_parse():
    owner = current_owner()
    items = coupang_import.parse_orders(request.form.get("raw", ""))
    for it in items:
        it["dup"] = db.name_exists(owner, it["name"])
    return render_template(
        "import_preview.html",
        items=items,
        categories=db.list_categories(owner),
    )


@app.route("/import/confirm", methods=["POST"])
def import_confirm():
    owner = current_owner()
    f = request.form
    for idx in f.getlist("include"):
        name = f.get(f"name_{idx}", "").strip()
        if not name:
            continue
        db.add_purchase(
            owner,
            name=name,
            category=f.get(f"category_{idx}", "기타"),
            price=f.get(f"price_{idx}", 0),
            purchase_date=f.get(f"date_{idx}") or None,
            memo="쿠팡 주문내역에서 가져옴",
        )
    return redirect(url_for("index"))


def _lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except OSError:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


# 외부 WSGI 서버(클라우드 배포)에서 import 될 때를 위해 미리 초기화
db.init_db()
if not DEMO_MODE:
    db.seed_owner(db.DEFAULT_OWNER)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("\n  이 PC에서:              http://127.0.0.1:%d" % port)
    print("  같은 와이파이 아이폰에서:  http://%s:%d" % (_lan_ip(), port))
    print("  데모 모드:", "ON (방문자별 분리)" if DEMO_MODE else "OFF (개인용)", "\n")
    app.run(host="0.0.0.0", port=port, debug=False)
