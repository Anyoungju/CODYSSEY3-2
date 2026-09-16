# 네이토 사전평가 운영 기록

## 평가 대상

- 과정: AI 응용 학습 (AI Native Master)
- 학습 주제: AI 응용 (AI Integration)
- 미션: **AI Agent 개발: 나만의 AI 비서 구축 (M1-2)**
- 저장소: <https://github.com/Anyoungju/CODYSSEY3-2>
- 브랜치: `main`

## 1차 사전 점검 결과

2026-09-16에 평가 화면에서 과정·주제·M1-2를 선택했다. 다만 프로젝트 URL 선택 창에 등록된 URL이 없어 실제 네이토 평가 요청은 시작되지 않았다. 따라서 점수나 PASS/FAIL 결과는 아직 생성되지 않았으며, 이 문서는 사실과 다른 평가 결과를 기록하지 않는다.

### 확인된 차단 조건

`프로젝트 URL → URL 찾기` 목록이 비어 있었다. 코디세이에 GitHub 저장소 URL을 먼저 등록해야 네이토가 평가 대상을 선택할 수 있다.

### 다음 실행 전 준비

1. 코디세이 평가 요청 화면에서 GitHub URL 등록 절차를 완료한다.
2. 목록에서 `https://github.com/Anyoungju/CODYSSEY3-2`와 `main`을 선택한다.
3. 아래 자동화 명령으로 새 평가를 단 한 번 시작한다.

```powershell
python tools/naito_precheck.py `
  --repository-url https://github.com/Anyoungju/CODYSSEY3-2 `
  --branch main --start --timeout 300 `
  --output docs/naito/attempt-1.json
```

결과가 진행 중이면 `--start`를 반복하지 않는다. 다음 명령으로 같은 평가에 다시 연결한다.

```powershell
python tools/naito_precheck.py --wait --timeout 300 `
  --output docs/naito/attempt-1.json
```

## 재사용 가능한 자동화 도구

[`tools/naito_precheck.py`](../tools/naito_precheck.py)는 외부 패키지 없이 동작하는 독립형 CDP 도구다.

- `--repository-url`, `--branch`: 평가 대상 선택
- 기본 조회: 기존 결과를 소비 없이 JSON/Markdown으로 내보내기
- `--start`: 새 네이토 평가 시작 및 완료 대기
- `--wait`: 기존 진행 중 평가 재연결
- `--output`: 같은 이름의 `.json`과 `.md` 결과 생성

Chrome은 원격 디버깅을 루프백 `127.0.0.1:9222`로 열고 코디세이에 로그인된 상태여야 한다. 이 작업 공간에서는 상위 폴더의 `scripts\open_codyssey.cmd`로 인증 세션을 연다.

## 평가 결과 반영 기준

실제 결과가 생기면 `docs/naito/attempt-N.json`을 원본으로 보관하고, 이 문서에 아래 형식으로 반영한다.

| 평가 항목 | 네이토 근거/부족한 점 | 코드·문서 반영 위치 | 재평가 상태 |
| --- | --- | --- | --- |
| 예: CORS | 실제 결과에서 발췌 | `backend/app/main.py`, `README.md` | 대기 |

PASS 항목도 근거와 권고를 기록하되, 평가 결과에 없는 주장을 추가하지 않는다.
