# DataPulse

매일 쌓이는 값을 한곳에 모아 보고, 필요한 순간에 질문할 수 있는 작은 데이터 노트입니다. 예시는 서울의 일별 기온이지만 `date`, `value`, `memo` 구조라면 운동 시간이나 매출처럼 다른 기록에도 그대로 쓸 수 있습니다.

기록은 Firestore에 두고, 질문을 보낼 때만 기간·평균·최고/최저·최근 흐름을 계산해 답변의 참고 정보로 보냅니다. 원본 전체를 매번 전달하지 않기 때문에 대화가 길어져도 필요한 맥락을 짧게 유지할 수 있습니다.

## 구성

| 구역 | 역할 |
| --- | --- |
| `backend/` | FastAPI API, Firestore 저장소, 요약 계산, OpenAI 호출 |
| `frontend/` | 채팅, 데이터 입력·삭제, 대화 목록을 제공하는 정적 화면 |
| `backend/scripts/seed_sample_data.py` | 2024년 일별 샘플 366개 생성 |
| `tools/naito_precheck.py` | 네이토 사전평가 결과를 JSON/Markdown으로 보관하는 도구 |

## 로컬 실행

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload
```

API 문서는 `http://127.0.0.1:8000/docs`에서 확인할 수 있습니다. 프론트는 별도 터미널에서 실행합니다.

```powershell
cd frontend
python -m http.server 5500
```

Firestore 연결 뒤 처음 한 번만 샘플 데이터를 넣습니다.

```powershell
python scripts/seed_sample_data.py
```

## 설정값

| Name | Description |
| --- | --- |
| `OPENAI_API_KEY` | 서버에서만 사용하는 OpenAI 키 |
| `FIREBASE_SERVICE_ACCOUNT_JSON` | Firebase 서비스 계정 JSON 전체 |
| `ALLOWED_ORIGINS` | 접속을 허용할 프론트 주소 목록 |
| `OPENAI_MODEL` | 생략하면 `gpt-4o-mini` |
| `API_BASE_URL` | 프론트가 호출할 API 주소 |

`.env`와 서비스 계정 파일은 커밋하지 않습니다. Firestore에는 `data`, `conversations` 두 컬렉션만 사용합니다.

## API 요약

| Method | Path | 설명 |
| --- | --- | --- |
| POST / GET | `/api/data` | 시계열 데이터 추가·목록 |
| PUT / DELETE | `/api/data/{id}` | 데이터 수정·삭제 |
| GET | `/api/data/summary` | 기간·통계·최근 추세 계산 |
| POST / GET | `/api/conversations` | 대화 저장·목록 |
| GET / DELETE | `/api/conversations/{id}` | 특정 대화 불러오기·삭제 |
| POST | `/api/chat` | 요약 컨텍스트를 주입한 AI 답변 및 자동 저장 |

## 답변이 만들어지는 과정

```text
Firestore data → summary service → system prompt → OpenAI → conversation 저장
```

모델이 개인 데이터를 미리 기억하는 방식은 아닙니다. 질문이 들어올 때 기간과 통계를 만들어 함께 전달하고, 답변과 질문은 다시 대화 기록에 저장합니다.

## 배포 메모

Render에서는 `backend`를 Root Directory로 잡고 `pip install -r requirements.txt`로 빌드합니다. 시작 명령은 `uvicorn app.main:app --host 0.0.0.0 --port $PORT`입니다. Vercel에는 `frontend`를 올린 뒤 `config.js`의 `API_BASE_URL`을 Render 주소로 바꿉니다.

Render 무료 인스턴스는 첫 요청이 느릴 수 있습니다. `/docs`가 열리는지 먼저 확인한 뒤 화면을 테스트하면 원인 구분이 쉽습니다.

## 사전 점검

M1-2 평가 대상과 재사용 가능한 CDP 자동화 도구, 실행 결과 기록 방식은 [네이토 사전평가 운영 기록](docs/NAITO_PRECHECK.md)에 정리했습니다.

## 추가 기능

- 최근 90개 기록을 SVG 선 그래프로 표시합니다.
- 평균뿐 아니라 중앙값, 값의 범위, 표준편차를 계산합니다. 표준편차는 기록이 평소 값에서 얼마나 흔들렸는지 보는 지표입니다.
- 데이터 관리 화면에서 CSV 파일을 내려받을 수 있습니다.
- 테마 버튼으로 밝은 화면과 어두운 화면을 전환합니다.
