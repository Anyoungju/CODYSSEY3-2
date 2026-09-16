# DataPulse AI

Firestore에 저장한 시계열 데이터를 분석하고, 그 요약을 AI 시스템 프롬프트에 주입해 맞춤 답변을 제공하는 서비스입니다.

> 배포 URL은 Render/Vercel 배포가 끝난 뒤 이 문서에 기록합니다. Render 무료 인스턴스는 첫 요청에서 잠시 깨어나는 시간이 필요할 수 있습니다.

## 기술

- Backend: Python 3.10+, FastAPI, Pydantic, Firestore, OpenAI
- Frontend: Vanilla HTML/CSS/JavaScript
- Deploy: Render (API), Vercel (static frontend)

## 로컬 실행

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload
```

프론트는 `frontend`에서 정적 서버로 실행합니다. API 문서는 `http://127.0.0.1:8000/docs`입니다.

```powershell
cd frontend
python -m http.server 5500
```

Firestore 연결 뒤 최초 데이터는 다음 명령으로 채웁니다. 이 스크립트는 2024년 일별 기온 형태의 결정적 데이터 366개를 만듭니다.

```powershell
python scripts/seed_sample_data.py
```

## 환경 변수

| Name | Description |
| --- | --- |
| `OPENAI_API_KEY` | 서버 전용 OpenAI API key |
| `FIREBASE_SERVICE_ACCOUNT_JSON` | 서비스 계정 JSON 전체 문자열 |
| `ALLOWED_ORIGINS` | 쉼표로 구분한 프론트 출처 |
| `OPENAI_MODEL` | 기본값 `gpt-4o-mini` |
| `API_BASE_URL` | Vercel의 백엔드 URL |

키는 커밋하지 않습니다. Firestore는 `data`, `conversations` 컬렉션을 사용합니다.

## API

| Method | Path | Purpose |
| --- | --- | --- |
| POST / GET | `/api/data` | 시계열 데이터 추가·목록 |
| PUT / DELETE | `/api/data/{id}` | 데이터 수정·삭제 |
| GET | `/api/data/summary` | 기간·통계·최근 추세 계산 |
| POST / GET | `/api/conversations` | 대화 저장·목록 |
| GET / DELETE | `/api/conversations/{id}` | 특정 대화 불러오기·삭제 |
| POST | `/api/chat` | 요약 컨텍스트를 주입한 AI 답변 및 자동 저장 |

## 컨텍스트 주입 흐름

```text
Firestore data → summary service → system prompt → OpenAI → conversation 저장
```

AI 모델이 개인 데이터를 미리 학습하는 방식이 아닙니다. 요청 시점에 기간·통계·추세를 만든 뒤 시스템 프롬프트에 포함하므로, 키를 노출하지 않으면서 저장된 데이터 근거의 답변을 제공합니다.

## 배포

1. Render에서 `backend`를 Root Directory로 지정하고 Build Command는 `pip install -r requirements.txt`, Start Command는 `uvicorn app.main:app --host 0.0.0.0 --port $PORT`로 설정합니다.
2. Render 환경 변수에 `OPENAI_API_KEY`, `FIREBASE_SERVICE_ACCOUNT_JSON`, `OPENAI_MODEL`, `ALLOWED_ORIGINS`를 등록합니다.
3. Vercel에서 `frontend`를 배포하고 `config.js`의 `API_BASE_URL`을 Render URL로 바꿉니다. 운영에서는 해당 값을 Vercel 환경 변수로 빌드 시 주입하도록 설정합니다.
4. Render URL의 `/docs`에서 Swagger UI를 확인합니다. 무료 인스턴스는 최초 요청에서 잠시 지연될 수 있으므로 화면에 재시도 가능한 오류 문구를 제공합니다.
