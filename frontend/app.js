const api = window.APP_CONFIG.API_BASE_URL.replace(/\/$/, "");
const $ = (selector) => document.querySelector(selector);
let conversationId = null;
let currentData = [];

async function request(path, options = {}) {
  const response = await fetch(`${api}${path}`, {headers: {"Content-Type": "application/json"}, ...options});
  if (!response.ok) throw new Error((await response.json().catch(() => ({}))).detail || "요청 처리에 실패했습니다.");
  return response.status === 204 ? null : response.json();
}
function message(role, content) { const el = document.createElement("article"); el.className = role; el.textContent = content; $("#messages").append(el); el.scrollIntoView({behavior:"smooth", block:"end"}); }
function esc(value) { return String(value).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c])); }

async function loadSummary() {
  const data = await request("/api/data/statistics");
  const metrics = data.metrics || {};
  $("#summary").innerHTML = `<div><b>기간</b><span>${esc(data.period)}</span></div><div><b>데이터</b><span>${data.count}개</span></div><div><b>평균</b><span>${metrics.average ?? "-"}</span></div><div><b>변동성</b><span>${metrics.standard_deviation ?? "-"}</span></div><div><b>최근 추세</b><span>${esc(data.trend)}</span></div>`;
}

function renderChart(records) {
  const svg = $("#trend-chart");
  if (!records.length) { svg.innerHTML = `<text x="360" y="110" text-anchor="middle">표시할 데이터가 없습니다.</text>`; return; }
  const items = records.slice(-90);
  const values = items.map(item => Number(item.value));
  const low = Math.min(...values), high = Math.max(...values), spread = high - low || 1;
  const points = items.map((item, index) => `${36 + index * 648 / Math.max(items.length - 1, 1)},${184 - (Number(item.value) - low) * 148 / spread}`).join(" ");
  svg.innerHTML = `<line x1="36" y1="184" x2="684" y2="184" class="axis"/><line x1="36" y1="36" x2="36" y2="184" class="axis"/><polyline points="${points}" class="line"/><text x="36" y="208">${esc(items[0].date)}</text><text x="684" y="208" text-anchor="end">${esc(items.at(-1).date)}</text><text x="30" y="42" text-anchor="end">${high}</text><text x="30" y="184" text-anchor="end">${low}</text>`;
  $("#chart-caption").textContent = `${items.length}개 기록 · 최근 값 ${items.at(-1).value}`;
}

function downloadCsv() {
  const header = "date,value,memo";
  const escapeCell = value => `"${String(value ?? "").replaceAll('"', '""')}"`;
  const csv = [header, ...currentData.map(item => [item.date, item.value, item.memo].map(escapeCell).join(","))].join("\n");
  const url = URL.createObjectURL(new Blob(["\uFEFF", csv], {type: "text/csv;charset=utf-8"}));
  const link = Object.assign(document.createElement("a"), {href: url, download: "datapulse-records.csv"});
  link.click(); URL.revokeObjectURL(url);
}
async function loadData() {
  const data = await request("/api/data");
  currentData = data;
  renderChart(data);
  $("#data-list").innerHTML = data.length ? data.map(item => `<div class="row"><span>${item.date}</span><b>${item.value}</b><small>${esc(item.memo || "-")}</small><button data-delete="${item.id}">삭제</button></div>`).join("") : "<p>저장된 데이터가 없습니다.</p>";
  document.querySelectorAll("[data-delete]").forEach(button => button.onclick = async () => { if (!confirm("이 데이터를 삭제할까요?")) return; await request(`/api/data/${button.dataset.delete}`, {method:"DELETE"}); await Promise.all([loadData(), loadSummary()]); });
}
async function loadHistory() {
  const data = await request("/api/conversations");
  $("#history-list").innerHTML = data.length ? data.map(item => `<button class="history" data-id="${item.id}">${esc(item.title)}<small>${new Date(item.updated_at).toLocaleString()}</small></button>`).join("") : "<p>저장된 대화가 없습니다.</p>";
  document.querySelectorAll(".history").forEach(button => button.onclick = async () => { const chat = await request(`/api/conversations/${button.dataset.id}`); conversationId = chat.id; $("#messages").replaceChildren(); chat.messages.forEach(item => message(item.role, item.content)); document.querySelector('[data-tab="chat"]').click(); });
}
document.querySelectorAll("nav button").forEach(button => button.onclick = () => { document.querySelectorAll("nav button,.panel").forEach(el => el.classList.remove("active")); button.classList.add("active"); $(`#${button.dataset.tab}`).classList.add("active"); if (button.dataset.tab === "data") loadData(); if (button.dataset.tab === "history") loadHistory(); });
$("#theme").onclick = () => document.body.classList.toggle("dark");
$("#download").onclick = downloadCsv;
$("#data-form").onsubmit = async event => { event.preventDefault(); const button = event.target.querySelector("button"); button.disabled = true; try { await request("/api/data", {method:"POST", body:JSON.stringify({date:$("#date").value, value:Number($("#value").value), memo:$("#memo").value})}); event.target.reset(); await Promise.all([loadData(), loadSummary()]); } catch (error) { alert(error.message); } finally { button.disabled = false; } };
$("#chat-form").onsubmit = async event => { event.preventDefault(); const input = $("#question"), button = event.target.querySelector("button"), question = input.value.trim(); if (!question) return; message("user", question); input.value=""; button.disabled=true; const loading=document.createElement("article"); loading.className="assistant loading"; loading.textContent="저장된 데이터를 분석하고 있어요…"; $("#messages").append(loading); try { const result=await request("/api/chat", {method:"POST", body:JSON.stringify({message:question, conversation_id:conversationId})}); conversationId=result.conversation_id; loading.remove(); message("assistant", result.answer); loadHistory(); } catch(error) { loading.textContent=error.message; } finally { button.disabled=false; } };
Promise.all([loadSummary(), loadData(), loadHistory()]).catch(error => $("#summary").textContent = `연결 오류: ${error.message}`);
