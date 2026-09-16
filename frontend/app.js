const api = window.APP_CONFIG.API_BASE_URL.replace(/\/$/, "");
const $ = (selector) => document.querySelector(selector);
let conversationId = null;

async function request(path, options = {}) {
  const response = await fetch(`${api}${path}`, {headers: {"Content-Type": "application/json"}, ...options});
  if (!response.ok) throw new Error((await response.json().catch(() => ({}))).detail || "요청 처리에 실패했습니다.");
  return response.status === 204 ? null : response.json();
}
function message(role, content) { const el = document.createElement("article"); el.className = role; el.textContent = content; $("#messages").append(el); el.scrollIntoView({behavior:"smooth", block:"end"}); }
function esc(value) { return String(value).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c])); }

async function loadSummary() {
  const data = await request("/api/data/summary");
  const metrics = data.metrics || {};
  $("#summary").innerHTML = `<div><b>기간</b><span>${esc(data.period)}</span></div><div><b>데이터</b><span>${data.count}개</span></div><div><b>평균</b><span>${metrics.average ?? "-"}</span></div><div><b>최근 추세</b><span>${esc(data.trend)}</span></div>`;
}
async function loadData() {
  const data = await request("/api/data");
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
$("#data-form").onsubmit = async event => { event.preventDefault(); const button = event.target.querySelector("button"); button.disabled = true; try { await request("/api/data", {method:"POST", body:JSON.stringify({date:$("#date").value, value:Number($("#value").value), memo:$("#memo").value})}); event.target.reset(); await Promise.all([loadData(), loadSummary()]); } catch (error) { alert(error.message); } finally { button.disabled = false; } };
$("#chat-form").onsubmit = async event => { event.preventDefault(); const input = $("#question"), button = event.target.querySelector("button"), question = input.value.trim(); if (!question) return; message("user", question); input.value=""; button.disabled=true; const loading=document.createElement("article"); loading.className="assistant loading"; loading.textContent="저장된 데이터를 분석하고 있어요…"; $("#messages").append(loading); try { const result=await request("/api/chat", {method:"POST", body:JSON.stringify({message:question, conversation_id:conversationId})}); conversationId=result.conversation_id; loading.remove(); message("assistant", result.answer); loadHistory(); } catch(error) { loading.textContent=error.message; } finally { button.disabled=false; } };
Promise.all([loadSummary(), loadData(), loadHistory()]).catch(error => $("#summary").textContent = `연결 오류: ${error.message}`);
