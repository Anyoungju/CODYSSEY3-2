# 네이토 사전평가 기록

## 평가 대상

- 과정: AI 응용 학습 (AI Native Master)
- 학습 주제: AI 응용 (AI Integration)
- 미션: **AI Agent 개발: 나만의 AI 비서 구축 (M1-2)**
- 저장소: <https://github.com/Anyoungju/CODYSSEY3-2>
- 브랜치: `main`

## 시도 1

2026-09-16에 `https://github.com/Anyoungju/CODYSSEY3-2`의 `main` 브랜치를 M1-2 평가 대상으로 저장하고 사전평가를 시작했다.

- 시도 1: GitHub 파일 20개와 평가 대상 15개 파일까지 확인한 뒤 `AI_PRE_EVAL_COPA_ERROR`로 종료됐다. 네이토 AI 호출 오류로 표시됐으며, 저장소 코드에 관한 피드백은 생성되지 않았다.
- 시도 2: 파일 목록 20개를 확인하고 18개 파일을 대상으로 마지막 분석 단계를 처리 중이다.

서비스 오류는 제품 코드의 결함으로 기록하지 않는다. 점수와 항목별 피드백이 표시될 때에만 그 근거를 코드 또는 문서 변경에 연결한다.

## 결과 확인과 재연결

새 시도는 한 번만 시작한다. 결과가 처리 중일 때는 아래 명령으로 같은 시도에 다시 연결한다.

```powershell
python tools/naito_precheck.py `
  --wait --timeout 300 `
  --output docs/naito/attempt-1.json
```

새 평가가 필요할 때만 `--repository-url`, `--branch`, `--start`를 함께 쓴다.

`tools/naito_precheck.py`는 외부 패키지 없이 동작하며, 기본 실행은 결과 조회만 한다. `--start`는 새 평가를 시작하고, `--wait`는 진행 중인 평가를 다시 붙잡는다. `--output`을 지정하면 JSON과 같은 이름의 Markdown 파일을 함께 만든다.

Chrome은 원격 디버깅을 루프백 `127.0.0.1:9222`로 열고 코디세이에 로그인된 상태여야 한다. 이 작업 공간에서는 상위 폴더의 `scripts\open_codyssey.cmd`로 인증 세션을 연다.

원본 결과는 `docs/naito/attempt-N.json`에 남기고, 수정한 내용만 이 문서에 짧게 적는다. PASS 항목도 참고할 만한 권고가 있을 때만 기록한다.
