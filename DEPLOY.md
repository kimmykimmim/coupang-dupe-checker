# 📱 아이폰에서 쓰기 — PythonAnywhere 무료 배포 가이드

이 앱을 클라우드(PythonAnywhere)에 올려서, **PC를 꺼도 아이폰에서 언제 어디서나** 접속하는 방법입니다.
PythonAnywhere를 고른 이유: 무료 + 신용카드 불필요 + **구매 기록(SQLite)이 사라지지 않고 유지**됨.

준비물: `coupang-dupe-checker.zip` (프로젝트 폴더에 만들어 둠, 이걸 업로드합니다)

---

## 1. 회원가입
1. https://www.pythonanywhere.com 접속 → **Pricing & signup** → **Create a Beginner account** (무료)
2. 가입 후 로그인. 아이디를 `USERNAME` 이라고 하면, 앱 주소는 `https://USERNAME.pythonanywhere.com` 이 됩니다.

## 2. 코드 업로드
1. 상단 **Files** 탭 클릭
2. 왼쪽 경로가 `/home/USERNAME/` 인 상태에서, 오른쪽 **Upload a file** 로 `coupang-dupe-checker.zip` 업로드
3. 상단 **Bash** 콘솔(**Consoles → Bash**)을 열고 아래 입력:
   ```bash
   cd ~
   unzip coupang-dupe-checker.zip
   cd coupang-dupe-checker
   ls        # app.py, templates, static 등이 보이면 성공
   ```

## 3. 가상환경 만들고 Flask 설치
같은 Bash 콘솔에서:
```bash
python3.10 -m venv ~/venv
source ~/venv/bin/activate
pip install Flask
```
(PythonAnywhere는 자체 서버를 쓰므로 gunicorn은 필요 없습니다. Flask만 설치하면 됩니다.)

## 4. 웹앱 연결
1. 상단 **Web** 탭 → **Add a new web app** → **Next**
2. 프레임워크 선택 화면에서 **Manual configuration** 선택 → **Python 3.10** → **Next**
3. 웹앱이 생성되면 설정 페이지에서 두 곳을 고칩니다.

   **(a) Virtualenv** 항목에 경로 입력:
   ```
   /home/USERNAME/venv
   ```

   **(b) WSGI configuration file** 링크를 클릭해 열고, 내용을 **전부 지우고** 아래로 교체
   (`USERNAME` 두 군데를 본인 아이디로 바꾸세요):
   ```python
   import sys
   path = "/home/USERNAME/coupang-dupe-checker"
   if path not in sys.path:
       sys.path.insert(0, path)
   from app import app as application
   ```
   저장(초록 **Save** 버튼).

## 5. 실행
1. **Web** 탭 맨 위 초록색 **Reload** 버튼 클릭
2. `https://USERNAME.pythonanywhere.com` 접속 → 앱이 뜨면 성공! 🎉

## 6. 아이폰 홈 화면에 앱처럼 추가
1. 아이폰 **사파리**로 `https://USERNAME.pythonanywhere.com` 열기
2. 하단 **공유 버튼(⬆️)** → **홈 화면에 추가**
3. 홈 화면에 "중복방지" 아이콘 생성 → 탭하면 주소창 없이 전체화면 앱처럼 실행됩니다.

---

## 자주 겪는 문제
- **화면이 안 뜸/에러**: Web 탭의 **Error log** 링크를 열어 마지막 줄 확인. 보통 WSGI 파일의 `USERNAME`/경로 오타입니다.
- **3개월마다 비활성화 안내 메일**: 무료 계정 정책. 로그인해서 Web 탭의 버튼 한 번 누르면 3개월 연장됩니다.
- **코드 수정 후 반영 안 됨**: 파일을 다시 업로드/수정한 뒤 반드시 Web 탭 **Reload** 를 눌러야 적용됩니다.
- **의미(AI) 유사도**: 무료 계정은 외부 다운로드가 제한돼 `sentence-transformers` 모델을 받지 못할 수 있습니다. 기본 유사도 엔진만으로도 잘 동작하니 그대로 쓰면 됩니다.

## 데이터 백업 (선택)
구매 기록은 서버의 `~/coupang-dupe-checker/purchases.db` 에 저장됩니다.
Files 탭에서 이 파일을 가끔 내려받아 두면 안전합니다.
