"""Run, resume, and export Codyssey Naito pre-evaluations via loopback CDP.

The script is self-contained and uses only the Python standard library. Chrome
must already be running with remote debugging bound to loopback and the user
must already be authenticated to Codyssey.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import secrets
import socket
import struct
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from urllib.request import urlopen


DEFAULT_PORT = 9222
DEFAULT_EVALUATION_URL = (
    "https://usr.codyssey.kr/daejeon/ev/request/evalutionRequestWrite"
)
AUTHENTICATED_HOST = "usr.codyssey.kr"


def read_json(url: str) -> Any:
    """Read JSON from a loopback CDP endpoint."""
    with urlopen(url, timeout=5) as response:
        return json.load(response)


class CDPClient:
    """Minimal WebSocket client for a loopback Chrome DevTools endpoint."""

    def __init__(self, websocket_url: str, timeout: float = 30) -> None:
        parsed = urlsplit(websocket_url)
        if parsed.scheme != "ws" or parsed.hostname not in {
            "127.0.0.1",
            "localhost",
        }:
            raise ValueError("CDP WebSocket must use an unencrypted loopback URL")
        self._host = parsed.hostname
        self._port = parsed.port or 80
        self._path = parsed.path
        self._socket = socket.create_connection(
            (self._host, self._port),
            timeout=timeout,
        )
        self._socket.settimeout(timeout)
        self._next_id = 0
        self._handshake()

    def _handshake(self) -> None:
        key = base64.b64encode(secrets.token_bytes(16)).decode("ascii")
        request = (
            f"GET {self._path} HTTP/1.1\r\n"
            f"Host: {self._host}:{self._port}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n"
        )
        self._socket.sendall(request.encode("ascii"))
        response = bytearray()
        while b"\r\n\r\n" not in response:
            response.extend(self._socket.recv(4096))
        header_text = response.decode("latin-1")
        if not header_text.startswith("HTTP/1.1 101"):
            raise ConnectionError("Chrome rejected the CDP WebSocket handshake")
        expected = base64.b64encode(
            hashlib.sha1(
                (
                    key
                    + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
                ).encode("ascii")
            ).digest()
        ).decode("ascii")
        if f"Sec-WebSocket-Accept: {expected}".lower() not in header_text.lower():
            raise ConnectionError("Chrome returned an invalid WebSocket handshake")

    def _read_exact(self, size: int) -> bytes:
        data = bytearray()
        while len(data) < size:
            chunk = self._socket.recv(size - len(data))
            if not chunk:
                raise ConnectionError("CDP WebSocket closed unexpectedly")
            data.extend(chunk)
        return bytes(data)

    def _send_frame(self, payload: bytes, opcode: int = 1) -> None:
        mask = secrets.token_bytes(4)
        length = len(payload)
        header = bytearray([0x80 | opcode])
        if length < 126:
            header.append(0x80 | length)
        elif length <= 0xFFFF:
            header.append(0x80 | 126)
            header.extend(struct.pack("!H", length))
        else:
            header.append(0x80 | 127)
            header.extend(struct.pack("!Q", length))
        header.extend(mask)
        masked = bytes(
            value ^ mask[index % 4] for index, value in enumerate(payload)
        )
        self._socket.sendall(header + masked)

    def _receive_message(self) -> str:
        fragments = bytearray()
        message_opcode: int | None = None
        while True:
            first, second = self._read_exact(2)
            final = bool(first & 0x80)
            opcode = first & 0x0F
            masked = bool(second & 0x80)
            length = second & 0x7F
            if length == 126:
                length = struct.unpack("!H", self._read_exact(2))[0]
            elif length == 127:
                length = struct.unpack("!Q", self._read_exact(8))[0]
            mask = self._read_exact(4) if masked else b""
            payload = self._read_exact(length)
            if masked:
                payload = bytes(
                    value ^ mask[index % 4]
                    for index, value in enumerate(payload)
                )
            if opcode == 0x8:
                raise ConnectionError("Chrome closed the CDP WebSocket")
            if opcode == 0x9:
                self._send_frame(payload, opcode=0xA)
                continue
            if opcode == 0xA:
                continue
            if opcode in {0x1, 0x2}:
                message_opcode = opcode
                fragments = bytearray(payload)
            elif opcode == 0x0:
                fragments.extend(payload)
            else:
                continue
            if final and message_opcode is not None:
                if message_opcode != 0x1:
                    raise ValueError("Unexpected binary CDP message")
                return fragments.decode("utf-8")

    def call(
        self,
        method: str,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """Send one CDP command and wait for the matching response."""
        self._next_id += 1
        command_id = self._next_id
        self._send_frame(
            json.dumps(
                {
                    "id": command_id,
                    "method": method,
                    "params": params or {},
                },
                separators=(",", ":"),
            ).encode("utf-8")
        )
        while True:
            message = json.loads(self._receive_message())
            if message.get("id") != command_id:
                continue
            if "error" in message:
                reason = message["error"].get("message", "CDP command failed")
                raise RuntimeError(reason)
            return message.get("result")

    def evaluate(self, expression: str) -> Any:
        """Evaluate JavaScript and return a JSON-serializable value."""
        response = self.call(
            "Runtime.evaluate",
            {
                "expression": expression,
                "returnByValue": True,
                "awaitPromise": True,
            },
        )
        if response.get("exceptionDetails"):
            raise RuntimeError("JavaScript evaluation failed")
        return response["result"].get("value")

    def close(self) -> None:
        """Close the WebSocket connection."""
        try:
            self._send_frame(b"", opcode=0x8)
        finally:
            self._socket.close()


def is_authenticated_tab(tab: dict[str, Any]) -> bool:
    """Return whether a CDP target is an authenticated Codyssey page."""
    parsed = urlsplit(tab.get("url", ""))
    return (
        tab.get("type") == "page"
        and parsed.scheme == "https"
        and parsed.hostname == AUTHENTICATED_HOST
    )


def find_target(port: int, evaluation_url: str) -> dict[str, Any]:
    """Find a Codyssey tab, preferring the configured evaluation page."""
    tabs = read_json(f"http://127.0.0.1:{port}/json/list")
    authenticated = [tab for tab in tabs if is_authenticated_tab(tab)]
    if not authenticated:
        raise RuntimeError(
            "No authenticated Codyssey CDP tab. Open the project Chrome first."
        )
    return next(
        (
            tab
            for tab in authenticated
            if tab.get("url", "").startswith(evaluation_url)
        ),
        authenticated[0],
    )


def wait_ready(client: CDPClient, timeout: float = 20) -> None:
    """Wait until the active document has finished loading."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if client.evaluate("document.readyState === 'complete'"):
            return
        time.sleep(0.25)
    raise TimeoutError("Codyssey evaluation page did not finish loading")


def open_evaluation_page(client: CDPClient, evaluation_url: str) -> None:
    """Navigate the authenticated target to the evaluation page."""
    current = client.evaluate("location.href")
    if current == evaluation_url:
        return
    client.call("Page.enable")
    client.call("Page.navigate", {"url": evaluation_url})
    wait_ready(client)
    time.sleep(1)


def configure_submission(
    client: CDPClient,
    repository_url: str | None,
    branch: str | None,
) -> None:
    """Select a registered repository and its branch in the evaluation form."""
    if repository_url is None and branch is None:
        return
    payload = json.dumps(
        {"repository_url": repository_url, "branch": branch},
        ensure_ascii=False,
    )
    result = client.evaluate(
        f"""
        (async () => {{
          const values = {payload};
          const pause = (ms) => new Promise(resolve => setTimeout(resolve, ms));
          const repositoryInput = document.querySelector('#srccdUrlAddr');
          const branchInput = document.querySelector('#brnchNm');
          if (!repositoryInput || !branchInput) return {{form: false}};
          if (values.repository_url && repositoryInput.value !== values.repository_url) {{
            document.querySelector('#gitAddrBtn')?.click();
            await pause(600);
            const radios = [...document.querySelectorAll('input[type=radio]')];
            const match = radios.find(radio =>
              (radio.closest('li, label, div')?.innerText || '')
                .includes(values.repository_url)
            );
            if (!match) return {{form: true, repository: false}};
            match.click();
            const confirm = [...document.querySelectorAll('button')].find(button =>
              (button.textContent || '').trim() === '확인'
            );
            if (!confirm) return {{form: true, repository: false}};
            confirm.click();
            await pause(400);
          }}
          const repositoryMatches = !values.repository_url ||
            repositoryInput.value === values.repository_url;
          const branchMatches = !values.branch || branchInput.value === values.branch;
          return {{
            form: true,
            repository: repositoryMatches,
            branch: branchMatches
          }};
        }})()
        """
    )
    failed = [name for name, succeeded in result.items() if not succeeded]
    if failed:
        raise RuntimeError(f"Evaluation fields were not found: {failed}")


def open_dialog(client: CDPClient) -> None:
    """Open the Naito dialog without starting a new attempt."""
    if client.evaluate("!!document.querySelector('[role=dialog]')"):
        return
    clicked = client.evaluate(
        """
        (() => {
          const button = [...document.querySelectorAll('button')]
            .find((item) =>
              (item.textContent || '').includes('네이토 사전평가')
            );
          if (!button) return false;
          button.click();
          return true;
        })()
        """
    )
    if not clicked:
        raise RuntimeError("Naito pre-evaluation button was not found")
    time.sleep(1)


def refresh_dialog(client: CDPClient) -> None:
    """Close and reopen the dialog to fetch server-side updates."""
    client.evaluate(
        """
        document.querySelector(
          '.ai-preeval-btn-close, .modal-close-btn'
        )?.click(); true
        """
    )
    time.sleep(0.5)
    open_dialog(client)


def snapshot(client: CDPClient) -> dict[str, Any]:
    """Extract the visible Naito result and repository metadata."""
    return client.evaluate(
        """
        (() => {
          const dialog = document.querySelector('[role=dialog]');
          const panel = dialog?.querySelector('.ai-pre-eval-result-panel');
          const tabs = dialog
            ? [...dialog.querySelectorAll(
                '.ai-pre-evaluation-tab-header button'
              )].map((item) => (item.textContent || '').trim())
            : [];
          const items = panel
            ? [...panel.querySelectorAll('li')]
                .map((item) => (item.innerText || '').trim())
            : [];
          return {
            repository_url:
              document.querySelector('#srccdUrlAddr')?.value || '',
            branch: document.querySelector('#brnchNm')?.value || '',
            dialog_text: dialog?.innerText || '',
            tabs,
            summary: panel
              ? (panel.innerText || '').split('항목별 평가')[0].trim()
              : '',
            items
          };
        })()
        """
    )


def parse_item_text(text: str) -> dict[str, Any]:
    """Convert one Korean result card into stable structured fields."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    status = lines[0] if lines and lines[0] in {"PASS", "FAIL"} else "UNKNOWN"
    number_match = re.search(r"#(\d+)", text)
    labels = {
        "근거": "evidence",
        "잘한 점": "strength",
        "부족한 점": "gap",
        "보완": "action",
    }
    fields: dict[str, str] = {}
    current: str | None = None
    values: list[str] = []
    for line in lines[2:]:
        if line in labels:
            if current:
                fields[current] = "\n".join(values)
            current = labels[line]
            values = []
        elif current:
            values.append(line)
    if current:
        fields[current] = "\n".join(values)
    return {
        "number": int(number_match.group(1)) if number_match else None,
        "status": status,
        **fields,
    }


def structured_result(raw: dict[str, Any]) -> dict[str, Any]:
    """Build a stable result object from a browser snapshot."""
    score = re.search(r"(\d+)%", raw.get("summary", ""))
    passed = re.search(r"\((\d+)\s*/\s*(\d+)", raw.get("summary", ""))
    items = []
    for position, item_text in enumerate(raw.get("items", []), start=1):
        item = parse_item_text(item_text)
        if item["number"] is None:
            item["number"] = position
        items.append(item)
    return {
        "repository_url": raw.get("repository_url"),
        "branch": raw.get("branch"),
        "score_percent": int(score.group(1)) if score else None,
        "passed": int(passed.group(1)) if passed else None,
        "total": int(passed.group(2)) if passed else None,
        "summary": raw.get("summary", ""),
        "items": items,
        "tabs": raw.get("tabs", []),
    }


def start_attempt(client: CDPClient) -> int:
    """Start a new attempt and return the prior result-tab count."""
    before = len(snapshot(client).get("tabs", []))
    clicked = client.evaluate(
        """
        (() => {
          const button = document.querySelector(
            '.ai-preeval-empty__start-btn, .ai-preeval-btn-primary'
          );
          if (!button || button.disabled) return false;
          button.click();
          return true;
        })()
        """
    )
    if not clicked:
        raise RuntimeError("No enabled Naito start button or no attempts remain")
    return before


def wait_for_attempt(
    client: CDPClient,
    previous_tabs: int,
    timeout: float,
    poll_interval: float,
) -> dict[str, Any]:
    """Wait for a new completed result while periodically refreshing."""
    deadline = time.monotonic() + timeout
    next_refresh = time.monotonic() + 30
    while time.monotonic() < deadline:
        raw = snapshot(client)
        tabs = raw.get("tabs", [])
        dialog_text = raw.get("dialog_text", "")
        running = "진행 중" in dialog_text or "평가 중" in dialog_text
        if len(tabs) > previous_tabs and raw.get("items") and not running:
            return raw
        if time.monotonic() >= next_refresh:
            refresh_dialog(client)
            next_refresh = time.monotonic() + 30
        time.sleep(poll_interval)
    raise TimeoutError(
        "Naito result wait timed out; use --wait later to reconnect"
    )


def to_markdown(result: dict[str, Any]) -> str:
    """Render a compact Markdown evaluation record."""
    lines = [
        "# 네이토 사전평가 결과",
        "",
        f"- 저장소: {result.get('repository_url') or '-'}",
        f"- 브랜치: `{result.get('branch') or '-'}`",
        (
            f"- 점수: **{result.get('score_percent')}% "
            f"({result.get('passed')}/{result.get('total')})**"
        ),
        "",
        "## 항목별 결과",
        "",
    ]
    for item in result.get("items", []):
        lines.extend(
            [
                f"### #{item.get('number')} — {item.get('status')}",
                "",
                f"- 근거: {item.get('evidence', '-')}",
                f"- 잘한 점: {item.get('strength', '-')}",
                f"- 부족한 점: {item.get('gap', '-')}",
                f"- 보완: {item.get('action', '-')}",
                "",
            ]
        )
    return "\n".join(lines)


def save_result(result: dict[str, Any], output: Path) -> None:
    """Save JSON and a sibling Markdown report."""
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    output.with_suffix(".md").write_text(
        to_markdown(result),
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument(
        "--evaluation-url",
        default=DEFAULT_EVALUATION_URL,
    )
    parser.add_argument("--repository-url")
    parser.add_argument("--branch")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--start", action="store_true")
    mode.add_argument("--wait", action="store_true")
    parser.add_argument("--timeout", type=float, default=300)
    parser.add_argument("--poll", type=float, default=5)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    """Inspect, start, or resume a Naito pre-evaluation."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args()
    target = find_target(args.port, args.evaluation_url)
    client = CDPClient(target["webSocketDebuggerUrl"])
    try:
        open_evaluation_page(client, args.evaluation_url)
        configure_submission(client, args.repository_url, args.branch)
        open_dialog(client)
        if args.start:
            prior_tabs = start_attempt(client)
            raw = wait_for_attempt(
                client,
                prior_tabs,
                args.timeout,
                args.poll,
            )
        elif args.wait:
            current = snapshot(client)
            if not any("⏳" in tab for tab in current.get("tabs", [])):
                raise RuntimeError("No running Naito attempt was found")
            prior_tabs = max(0, len(current.get("tabs", [])) - 1)
            raw = wait_for_attempt(
                client,
                prior_tabs,
                args.timeout,
                args.poll,
            )
        else:
            raw = snapshot(client)
        result = structured_result(raw)
    finally:
        client.close()
    if args.output:
        save_result(result, args.output)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("score_percent") is not None else 2


if __name__ == "__main__":
    raise SystemExit(main())
