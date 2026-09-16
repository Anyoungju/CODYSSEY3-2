"""FastAPI application for DataPulse AI."""
from __future__ import annotations
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from firebase_admin import firestore
from openai import OpenAI
from .config import allowed_origins
from .repository import create_data, delete_data, list_data, update_data, db, now
from .schemas import ChatInput, ConversationInput, DataInput
from .summary import build_summary

app = FastAPI(title="DataPulse AI API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=allowed_origins(), allow_credentials=False, allow_methods=["*"], allow_headers=["*"])


def normalized(payload: DataInput) -> dict:
    return {"date": payload.date.isoformat(), "value": payload.value, "memo": payload.memo.strip()}


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/api/data", status_code=201)
def post_data(payload: DataInput) -> dict:
    return create_data(normalized(payload))


@app.get("/api/data")
def get_data() -> list[dict]:
    return list_data()


@app.get("/api/data/summary")
def get_summary() -> dict:
    return build_summary(list_data())


@app.get("/api/data/statistics")
def get_statistics() -> dict:
    """Return extended figures used by the dashboard visualization."""
    return build_summary(list_data())


@app.put("/api/data/{item_id}")
def put_data(item_id: str, payload: DataInput) -> dict:
    result = update_data(item_id, normalized(payload))
    if not result:
        raise HTTPException(404, "데이터를 찾을 수 없습니다.")
    return result


@app.delete("/api/data/{item_id}", status_code=204)
def remove_data(item_id: str) -> None:
    if not delete_data(item_id):
        raise HTTPException(404, "데이터를 찾을 수 없습니다.")


@app.post("/api/conversations", status_code=201)
def save_conversation(payload: ConversationInput) -> dict:
    ref = db().collection("conversations").document()
    result = payload.model_dump() | {"created_at": now(), "updated_at": now()}
    ref.set(result)
    return {"id": ref.id, **result}


@app.get("/api/conversations")
def conversations() -> list[dict]:
    query = db().collection("conversations").order_by(
        "updated_at", direction=firestore.Query.DESCENDING
    )
    return [{"id": d.id, "title": d.to_dict().get("title", "새 대화"), "updated_at": d.to_dict().get("updated_at")} for d in query.stream()]


@app.get("/api/conversations/{conversation_id}")
def conversation(conversation_id: str) -> dict:
    doc = db().collection("conversations").document(conversation_id).get()
    if not doc.exists:
        raise HTTPException(404, "대화를 찾을 수 없습니다.")
    return {"id": doc.id, **doc.to_dict()}


@app.delete("/api/conversations/{conversation_id}", status_code=204)
def remove_conversation(conversation_id: str) -> None:
    ref = db().collection("conversations").document(conversation_id)
    if not ref.get().exists:
        raise HTTPException(404, "대화를 찾을 수 없습니다.")
    ref.delete()


@app.post("/api/chat")
def chat(payload: ChatInput) -> dict:
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise HTTPException(503, "OPENAI_API_KEY가 설정되지 않았습니다.")
    summary = build_summary(list_data())
    prompt = f"""당신은 사용자의 시계열 데이터를 이해하는 분석 비서입니다.\n[사용자 데이터 요약]\n{summary}\n\n반드시 위 데이터만 근거로 한국어로 간결하게 답하세요. 확인 불가한 내용은 추측하지 마세요."""
    try:
        response = OpenAI(api_key=key, timeout=20).chat.completions.create(model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"), max_tokens=350, messages=[{"role": "system", "content": prompt}, {"role": "user", "content": payload.message}])
        answer = response.choices[0].message.content or "답변을 생성하지 못했습니다."
    except Exception as error:
        raise HTTPException(502, "AI 응답을 생성하지 못했습니다.") from error
    messages = [{"role": "user", "content": payload.message, "created_at": now()}, {"role": "assistant", "content": answer, "created_at": now()}]
    ref = db().collection("conversations").document(payload.conversation_id) if payload.conversation_id else db().collection("conversations").document()
    existing = ref.get()
    old = existing.to_dict().get("messages", []) if existing.exists else []
    result = {"title": (old[0]["content"] if old else payload.message)[:40], "messages": old + messages, "updated_at": now()}
    if not existing.exists: result["created_at"] = now()
    ref.set(result, merge=True)
    return {"answer": answer, "conversation_id": ref.id, "summary": summary}
