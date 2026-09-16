"""Firestore persistence boundary."""
from __future__ import annotations
import json
import os
from datetime import datetime, timezone
import firebase_admin
from firebase_admin import credentials, firestore


def db():
    """Initialize Firebase once from an environment-only credential."""
    if not firebase_admin._apps:
        raw = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
        if not raw:
            raise RuntimeError("FIREBASE_SERVICE_ACCOUNT_JSON is not configured.")
        firebase_admin.initialize_app(credentials.Certificate(json.loads(raw)))
    return firestore.client()


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def list_data() -> list[dict]:
    return [{"id": doc.id, **doc.to_dict()} for doc in db().collection("data").order_by("date").stream()]


def create_data(payload: dict) -> dict:
    ref = db().collection("data").document()
    result = {**payload, "created_at": now(), "updated_at": now()}
    ref.set(result)
    return {"id": ref.id, **result}


def update_data(item_id: str, payload: dict) -> dict | None:
    ref = db().collection("data").document(item_id)
    if not ref.get().exists:
        return None
    result = {**payload, "updated_at": now()}
    ref.update(result)
    return {"id": item_id, **ref.get().to_dict()}


def delete_data(item_id: str) -> bool:
    ref = db().collection("data").document(item_id)
    if not ref.get().exists:
        return False
    ref.delete(); return True
