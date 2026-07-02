# 📱 라이브 데모 배포 — PythonAnywhere 무료 가이드

이 앱을 클라우드(PythonAnywhere)에 올려서, PC를 꺼도 **아이폰·아무나** 웹에서 접속하게 만드는 방법입니다.
PythonAnywhere를 고른 이유: 무료 + 카드 불필요 + **데이터(SQLite)가 유지**됨.

> 💡 공개용이면 **데모 모드(DEMO=1)** 로 켜세요. 방문자(브라우저)마다 데이터가 분리되어
> 서로의 구매 목록이 섞이거나 삭제되지 않습니다. (4단계에서 설정)

---

## 1. 회원가입
1. https://www.pythonanywhere.com → **Pricing & signup** → **Create a Beginner account** (무료)
2. 로그인. 아이디가 `USERNAME` 이면 주소는 `https://USERNAME.pythonanywhere.com` 입니다.

## 2. 코드 내려받기 (git clone)
상단 **Consoles → Bash** 콘솔을 열고:
```bash
cd ~
git clone https://github.com/kimmykimmim/coupang-dupe-checker.git
cd coupang-dupe-checker
ls        # app.py, templates, static 등이 보이면 성공
```
> 나중에 코드를 고쳤을 땐 이 폴더에서 `git pull` 하고 Web 탭에서 **Reload** 만 누르면 됩니다.

## 3. 가상환경 만들고 Flask 설치
```bash
python3.10 -m venv ~/venv
source ~/venv/bin/activate
pip install Flask
```
(PythonAnywhere는 자체 서버를 쓰므로 gunicorn은 필요 없습니다.)

## 4. 웹앱 연결
1. 상단 **Web** 탭 → **Add a new web app** → **Next**
2. **Manual configuration** → **Python 3.10** → **Next**
3. 설정 페이지에서 두 곳을 고칩니다.

   **(a) Virtualenv** 에 입력:
   ```
   /home/USERNAME/venv
   ```

   **(b) WSGI configuration file** 링크를 열어 내용을 **전부 지우고** 아래로 교체
   (`USERNAME` 을 본인 아이디로, `SECRET_KEY` 는 아무 긴 랜덤 문자열로 바꾸세요):
   ```python
   import os
   import sys

   os.environ["DEMO"] = "1"                       # 공개 데모: 방문자별 데이터 분리
   os.environ["SECRET_KEY"] = "바꾸세요-길고-랜덤한-문자열-abc123"

   path = "/home/USERNAME/coupang-dupe-checker"
   if path not in sys.path:
       sys.path.insert(0, path)

   from app import app as application
   ```
   초록 **Save**.
   > 본인 혼자만 쓸 거면 `os.environ["DEMO"] = "1"` 줄을 지우면 됩니다(모든 데이터를 한 곳에 계속 저장).

## 5. 실행
1. **Web** 탭 맨 위 초록 **Reload** 클릭
2. `https://USERNAME.pythonanywhere.com` 접속 → 앱이 뜨면 성공! 🎉
   상단에 노란 "🧪 체험판(데모)" 배너가 보이면 데모 모드가 켜진 것입니다.

## 6. 아이폰 홈 화면에 앱처럼 추가
1. 아이폰 **사파리**로 주소 열기
2. 하단 **공유(⬆️)** → **홈 화면에 추가**
3. "중복방지" 아이콘 생성 → 주소창 없이 전체화면 앱처럼 실행.

---

## 자주 겪는 문제
- **에러/안 뜸**: Web 탭의 **Error log** 마지막 줄 확인. 보통 WSGI의 `USERNAME`/경로 오타.
- **3개월마다 비활성화 메일**: 무료 정책. 로그인해 Web 탭 버튼 한 번이면 3개월 연장.
- **코드 수정 반영 안 됨**: `git pull` 후 Web 탭 **Reload** 필수.
- **의미(AI) 유사도**: 무료 계정은 외부 다운로드 제한으로 모델을 못 받을 수 있음. 기본 엔진만으로 잘 동작하니 그대로 두면 됩니다.

## 데모 vs 개인용 정리
| | DEMO=1 (공개) | DEMO 없음 (개인) |
|---|---|---|
| 데이터 | 방문자(브라우저)별 분리, 예시데이터 자동 | 전부 한 곳에 영구 저장 |
| 용도 | 인스타/포트폴리오에서 아무나 체험 | 나만 실제로 쓰기 |
