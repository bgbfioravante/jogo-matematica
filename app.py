import os
import random
import time
from flask import Flask, request, jsonify, session

app = Flask(__name__)
# Necessário pra sessão funcionar (pontuação/nome etc.)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")

MODES = {
    "add": "Soma",
    "sub": "Subtração",
    "mul": "Multiplicação",
    "div": "Divisão",
    "mix": "Misto",
}

DIFFICULTIES = {
    "easy": ("Fácil", 10),
    "medium": ("Médio", 30),
    "hard": ("Difícil", 100),
}


def _pick_operation(mode_key: str) -> str:
    if mode_key != "mix":
        return mode_key
    return random.choice(["add", "sub", "mul", "div"])


def _make_question(op: str, max_n: int):
    a = random.randint(1, max_n)
    b = random.randint(1, max_n)

    if op == "add":
        return {"text": f"{a} + {b}", "answer": a + b, "op": op}

    if op == "sub":
        x, y = max(a, b), min(a, b)
        return {"text": f"{x} - {y}", "answer": x - y, "op": op}

    if op == "mul":
        aa = random.randint(1, max(3, max_n // 2))
        bb = random.randint(1, max(3, max_n // 2))
        return {"text": f"{aa} × {bb}", "answer": aa * bb, "op": op}

    if op == "div":
        divisor = random.randint(1, max(2, max_n // 3))
        quociente = random.randint(1, max(2, max_n // 3))
        dividendo = divisor * quociente
        return {"text": f"{dividendo} ÷ {divisor}", "answer": quociente, "op": op}

    raise ValueError("Operação inválida")


def _calc_points(correct: bool, streak: int, elapsed_s: float) -> int:
    if not correct:
        return 0
    base = 10
    streak_bonus = min(streak, 10) * 2
    speed_bonus = max(0, 8 - int(elapsed_s))  # bônus simples por rapidez
    return base + streak_bonus + speed_bonus


def _ensure_state():
    session.setdefault("player_name", "")
    session.setdefault("mode", "mix")
    session.setdefault("difficulty", "easy")
    session.setdefault("score", 0)
    session.setdefault("streak", 0)
    session.setdefault("current_answer", None)
    session.setdefault("question_started_at", None)
    session.setdefault("question_text", "")


@app.get("/")
def home():
    return f"""
<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>MATE GAME (Web)</title>
  <style>
    body {{ font-family: Arial, sans-serif; background:#0b1220; color:#e9eefc; margin:0; }}
    .wrap {{ max-width: 920px; margin: 0 auto; padding: 24px; }}
    .card {{ background:#111a2e; border:1px solid #24314f; border-radius: 14px; padding: 18px; box-shadow: 0 10px 30px rgba(0,0,0,.25); }}
    h1 {{ margin:0 0 10px; font-size: 26px; }}
    .grid {{ display:grid; grid-template-columns: 1fr 1fr; gap: 14px; }}
    @media (max-width: 720px) {{ .grid {{ grid-template-columns: 1fr; }} }}
    label {{ display:block; font-size: 12px; opacity:.85; margin-bottom:6px; }}
    input, select, button {{
      width:100%; padding: 12px; border-radius: 10px;
      border:1px solid #2a3a61; background:#0b1220; color:#e9eefc;
      outline:none;
    }}
    button {{ cursor:pointer; background:#2f6cff; border:1px solid #2f6cff; font-weight:600; }}
    button.secondary {{ background:transparent; border:1px solid #2a3a61; }}
    .row {{ display:flex; gap: 10px; }}
    .row > * {{ flex: 1; }}
    .stats {{ display:flex; gap: 10px; flex-wrap: wrap; margin-top: 10px; }}
    .pill {{ padding: 8px 10px; border:1px solid #24314f; border-radius: 999px; background:#0b1220; font-size: 13px; }}
    .qbox {{ font-size: 44px; text-align:center; letter-spacing: 1px; margin: 16px 0; }}
    .msg {{ margin-top: 10px; min-height: 22px; }}
    .ok {{ color:#64ffb5; }}
    .bad {{ color:#ff6b6b; }}
    .muted {{ opacity:.8; font-size: 13px; }}
    .topbar {{ display:flex; justify-content: space-between; align-items:center; margin-bottom: 12px; }}
    a {{ color:#90b4ff; text-decoration:none; }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="topbar">
      <h1>🎮 MATE GAME (Web)</h1>
      <div class="muted">Seu jogo de terminal continua em <b>main.py</b></div>
    </div>

    <div class="grid">
      <div class="card">
        <div class="row">
          <div>
            <label>Nome do competidor</label>
            <input id="playerName" placeholder="Ex: Bruno" />
          </div>
        </div>

        <div class="row" style="margin-top:10px;">
          <div>
            <label>Modo</label>
            <select id="mode">
              <option value="add">Soma</option>
              <option value="sub">Subtração</option>
              <option value="mul">Multiplicação</option>
              <option value="div">Divisão</option>
              <option value="mix" selected>Misto</option>
            </select>
          </div>
          <div>
            <label>Dificuldade</label>
            <select id="difficulty">
              <option value="easy" selected>Fácil</option>
              <option value="medium">Médio</option>
              <option value="hard">Difícil</option>
            </select>
          </div>
        </div>

        <div class="row" style="margin-top:10px;">
          <button id="btnStart">Iniciar / Atualizar</button>
          <button id="btnReset" class="secondary">Reset</button>
        </div>

        <div class="stats">
          <div class="pill">Jogador: <b id="stPlayer">—</b></div>
          <div class="pill">Modo: <b id="stMode">—</b></div>
          <div class="pill">Dificuldade: <b id="stDiff">—</b></div>
          <div class="pill">Pontos: <b id="stScore">0</b></div>
          <div class="pill">Streak: <b id="stStreak">0</b></div>
        </div>

        <p class="muted" style="margin-top:12px;">
          Dica: quanto mais rápido você responde, mais bônus. Streak dá mais pontos.
        </p>
      </div>

      <div class="card">
        <div class="qbox" id="question">—</div>

        <label>Sua resposta</label>
        <div class="row">
          <input id="answer" placeholder="Digite um número" inputmode="numeric" />
          <button id="btnSend">Responder</button>
        </div>

        <div class="row" style="margin-top:10px;">
          <button id="btnNext" class="secondary">Próxima questão</button>
        </div>

        <div class="msg" id="msg"></div>
      </div>
    </div>

    <p class="muted" style="margin-top:14px;">
      Deploy no Render: se o site “dormir”, a primeira abertura pode demorar um pouco no plano free.
    </p>
  </div>

<script>
  const el = (id) => document.getElementById(id);

  function setMsg(text, kind) {{
    const m = el("msg");
    m.textContent = text || "";
    m.className = "msg " + (kind || "");
  }}

  async function api(path, body=null) {{
    const opt = body ? {{
      method: "POST",
      headers: {{ "Content-Type": "application/json" }},
      body: JSON.stringify(body)
    }} : {{ method: "GET" }};
    const res = await fetch(path, opt);
    return await res.json();
  }}

  function refreshUI(state) {{
    el("stPlayer").textContent = state.player_name || "—";
    el("stMode").textContent = state.mode_label || "—";
    el("stDiff").textContent = state.difficulty_label || "—";
    el("stScore").textContent = state.score ?? 0;
    el("stStreak").textContent = state.streak ?? 0;
    el("question").textContent = state.question_text || "—";
  }}

  async function loadState() {{
    const state = await api("/api/state");
    refreshUI(state);
  }}

  async function startOrUpdate() {{
    const name = el("playerName").value.trim();
    const mode = el("mode").value;
    const difficulty = el("difficulty").value;

    const state = await api("/api/start", {{ name, mode, difficulty }});
    refreshUI(state);
    setMsg("Pronto! Clique em “Próxima questão”.", "ok");
  }}

  async function nextQuestion() {{
    const state = await api("/api/question");
    refreshUI(state);
    el("answer").value = "";
    el("answer").focus();
    setMsg("", "");
  }}

  async function submitAnswer() {{
    const raw = el("answer").value.trim();
    if (!raw) {{
      setMsg("Digite uma resposta.", "bad");
      return;
    }}
    const n = Number(raw);
    if (!Number.isFinite(n)) {{
      setMsg("Resposta inválida (precisa ser número).", "bad");
      return;
    }}

    const result = await api("/api/answer", {{ answer: n }});
    refreshUI(result.state);

    if (result.correct) {{
      setMsg(`✅ Correto! +${{result.gained}} pontos (tempo: ${{result.elapsed_s}}s)`, "ok");
    }} else {{
      setMsg(`❌ Errado. Correto: ${{result.correct_answer}} (tempo: ${{result.elapsed_s}}s)`, "bad");
    }}
  }}

  async function resetGame() {{
    const state = await api("/api/reset", {{ }});
    refreshUI(state);
    setMsg("Resetado. Clique em “Próxima questão”.", "ok");
  }}

  el("btnStart").addEventListener("click", startOrUpdate);
  el("btnNext").addEventListener("click", nextQuestion);
  el("btnSend").addEventListener("click", submitAnswer);
  el("btnReset").addEventListener("click", resetGame);

  el("answer").addEventListener("keydown", (e) => {{
    if (e.key === "Enter") submitAnswer();
  }});

  loadState();
</script>

</body>
</html>
"""


@app.get("/api/state")
def api_state():
    _ensure_state()
    return jsonify({
        "player_name": session["player_name"],
        "mode": session["mode"],
        "mode_label": MODES.get(session["mode"], "—"),
        "difficulty": session["difficulty"],
        "difficulty_label": DIFFICULTIES.get(session["difficulty"], ("—", 0))[0],
        "score": session["score"],
        "streak": session["streak"],
        "question_text": session.get("question_text", ""),
    })


@app.post("/api/start")
def api_start():
    _ensure_state()
    data = request.get_json(silent=True) or {}

    name = (data.get("name") or "").strip()
    mode = (data.get("mode") or "mix").strip()
    difficulty = (data.get("difficulty") or "easy").strip()

    if mode not in MODES:
        mode = "mix"
    if difficulty not in DIFFICULTIES:
        difficulty = "easy"

    session["player_name"] = name[:30]
    session["mode"] = mode
    session["difficulty"] = difficulty

    return api_state()


@app.post("/api/reset")
def api_reset():
    session.clear()
    _ensure_state()
    return api_state()


@app.get("/api/question")
def api_question():
    _ensure_state()

    mode = session["mode"]
    diff = session["difficulty"]
    max_n = DIFFICULTIES[diff][1]

    op = _pick_operation(mode)
    q = _make_question(op, max_n)

    session["current_answer"] = q["answer"]
    session["question_text"] = q["text"]
    session["question_started_at"] = time.time()

    return api_state()


@app.post("/api/answer")
def api_answer():
    _ensure_state()
    data = request.get_json(silent=True) or {}

    if session.get("current_answer") is None:
        return jsonify({
            "error": "Nenhuma questão ativa. Clique em 'Próxima questão'.",
            "state": api_state().json
        }), 400

    started = session.get("question_started_at") or time.time()
    elapsed = max(0.0, time.time() - started)

    try:
        user_answer = int(data.get("answer"))
    except Exception:
        user_answer = None

    correct_answer = int(session["current_answer"])
    correct = (user_answer == correct_answer)

    if correct:
        session["streak"] += 1
        gained = _calc_points(True, session["streak"], elapsed)
        session["score"] += gained
    else:
        session["streak"] = 0
        gained = 0

    # trava a questão (precisa pedir próxima)
    session["current_answer"] = None
    session["question_started_at"] = None

    state = api_state().json
    return jsonify({
        "correct": correct,
        "gained": gained,
        "elapsed_s": f"{elapsed:.1f}",
        "correct_answer": correct_answer,
        "state": state
    })
