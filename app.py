# -*- coding: utf-8 -*-
"""쿠팡 중복구매 방지기 - Flask 웹앱."""
import os
import socket

from flask import Flask, render_template, request, redirect, url_for, jsonify

import db
import matcher
import coupang_import

app = Flask(__name__)


@app.route("/")
def index():
    return render_template(
        "index.html",
        purchases=db.list_purchases(),
        categories=db.list_categories(),
        semantic=matcher.semantic_available(),
    )


@app.route("/api/check", methods=["POST"])
def api_check():
    """구매 전 확인: 사려는 물건과 비슷한 기존 구매를 찾아 반환한다."""
    data = request.get_json(force=True)
    name = (data.get("name") or "").strip()
    category = (data.get("category") or "").strip()
    if not name:
        return jsonify({"ok": False, "error": "제품명을 입력하세요."}), 400
    matches = matcher.find_matches(name, db.list_purchases(), category)
    top = matches[0]["level"] if matches else "none"
    return jsonify({"ok": True, "query": name, "verdict": top, "matches": matches})


@app.route("/add", methods=["POST"])
def add():
    f = request.form
    if (f.get("name") or "").strip():
        db.add_purchase(
            name=f.get("name"),
            category=f.get("category", "기타"),   # 새 값이면 db 계층이 자동 등록
            price=f.get("price", 0),
            purchase_date=f.get("purchase_date") or None,
            url=f.get("url", ""),
            memo=f.get("memo", ""),
        )
    return redirect(url_for("index"))


@app.route("/delete/<int:item_id>", methods=["POST"])
def delete(item_id):
    db.delete_purchase(item_id)
    return redirect(url_for("index"))


# ---------------------------------------------------------------- 카테고리 관리
@app.route("/category/add", methods=["POST"])
def category_add():
    db.add_category(request.form.get("name", ""))
    return redirect(url_for("index"))


@app.route("/category/delete", methods=["POST"])
def category_delete():
    db.delete_category(request.form.get("name", ""))
    return redirect(url_for("index"))


# ---------------------------------------------------------------- 쿠팡 가져오기
@app.route("/import", methods=["POST"])
def import_parse():
    """붙여넣은 주문목록 텍스트를 파싱해 미리보기 화면을 보여준다."""
    text = request.form.get("raw", "")
    items = coupang_import.parse_orders(text)
    for it in items:                       # 이미 목록에 있는 상품명 표시
        it["dup"] = db.name_exists(it["name"])
    return render_template(
        "import_preview.html",
        items=items,
        categories=db.list_categories(),
    )


@app.route("/import/confirm", methods=["POST"])
def import_confirm():
    """미리보기에서 체크한 항목만 실제로 등록한다."""
    f = request.form
    added = 0
    for idx in f.getlist("include"):       # 체크된 행의 인덱스들
        name = f.get(f"name_{idx}", "").strip()
        if not name:
            continue
        db.add_purchase(
            name=name,
            category=f.get(f"category_{idx}", "기타"),
            price=f.get(f"price_{idx}", 0),
            purchase_date=f.get(f"date_{idx}") or None,
            memo="쿠팡 주문내역에서 가져옴",
        )
        added += 1
    return redirect(url_for("index"))


def _lan_ip():
    """같은 와이파이의 다른 기기(아이폰)가 접속할 PC의 로컬 IP를 찾는다."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except OSError:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


# gunicorn 등 외부 WSGI 서버(클라우드 배포)에서 실행할 때를 위해 미리 초기화
db.init_db()
db.seed_if_empty()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("\n  이 PC에서:              http://127.0.0.1:%d" % port)
    print("  같은 와이파이 아이폰에서:  http://%s:%d\n" % (_lan_ip(), port))
    # host="0.0.0.0" → 같은 네트워크의 다른 기기에서도 접속 가능
    app.run(host="0.0.0.0", port=port, debug=False)
