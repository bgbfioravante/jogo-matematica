from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import random
import time
import math

app = FastAPI(title="Jogo Matemática — Turbo Edition")

# =========================
# UTILIDADES
# =========================

def clamp(x, a, b):
    return max(a, min(b, x))

def now_ms():
    return int(time.time() * 1000)

def shuffle4(arr):
    random.shuffle(arr)
    return arr[:4]

def ensure_options(correct, options):
    opts = []
    for o in options:
        if o not in opts:
            opts.append(o)
    if correct not in opts:
        opts.append(correct)
    # garantir 4 opções
    step = 1
    while len(opts) < 4:
        fake = correct + random.choice([-1, 1]) * step
        if fake not in opts:
            opts.append(fake)
        step += 1
    random.shuffle(opts)
    return opts[:4]

# =========================
# MODELOS (requests)
# =========================

class NextQRequest(BaseModel):
    mode: str
    level: int = 1
    tier: int = 1
    rating: float = 0.50   # dificuldade adaptativa (0.0 a 1.0)
    combo: int = 0
    streak: int = 0

class AnswerRequest(BaseModel):
    mode: str
    level: int
    tier: int
    rating: float
    combo: int
    streak: int
    qid: str
    chosen: int
    correct: int
    start_ms: int
    end_ms: int

# =========================
# GERADORES DE QUESTÕES
# =========================

def gen_arithmetic(level, rating):
    # range cresce com level e rating
    base = 10 + level * 2
    spread = int(base + rating * 25)

    op_pool = ["+", "-"]
    if level >= 3:
        op_pool += ["*"]
    if level >= 6:
        op_pool += ["/"]

    op = random.choice(op_pool)

    if op == "+":
        a = random.randint(1, spread)
        b = random.randint(1, spread)
        correct = a + b
        text = f"{a} + {b} = ?"

    elif op == "-":
        a = random.randint(1, spread)
        b = random.randint(1, spread)
        if b > a:
            a, b = b, a
        correct = a - b
        text = f"{a} - {b} = ?"

    elif op == "*":
        a = random.randint(2, max(4, int(3 + level/2)))
        b = random.randint(2, max(4, int(4 + rating * 10)))
        correct = a * b
        text = f"{a} × {b} = ?"

    else:  # "/"
        b = random.randint(2, max(4, int(4 + rating * 10)))
        correct = random.randint(2, max(6, int(5 + level/2)))
        a = b * correct
        text = f"{a} ÷ {b} = ?"

    # opções plausíveis
    options = [
        correct,
        correct + random.randint(1, 5),
        correct - random.randint(1, 5),
        correct + random.randint(6, 15)
    ]
    options = ensure_options(correct, options)
    return text, options, correct

def gen_logic(level, rating):
    # Sequências / padrões
    kind = random.choice(["seq", "oddone", "grid"])
    diff = level + int(rating * 10)

    if kind == "seq":
        step = random.choice([1, 2, 3, 4, 5, 6])
        start = random.randint(1, 10 + diff)
        length = 4
        seq = [start + i * step for i in range(length)]
        missing_i = random.randint(1, length-1)
        correct = seq[missing_i]
        seq[missing_i] = "?"
        text = "Complete a sequência: " + "  ".join(map(str, seq))
        options = [correct, correct + step, correct - step, correct + step * 2]
        options = ensure_options(correct, options)
        return text, options, correct

    if kind == "oddone":
        # 3 seguem regra, 1 é intruso
        base = random.randint(2, 10 + diff)
        rule = random.choice(["square", "double", "prime-ish"])
        if rule == "square":
            arr = [base**2, (base+1)**2, (base+2)**2]
            intr = random.randint(10, 200)
        elif rule == "double":
            arr = [base, base*2, base*4]
            intr = random.randint(10, 200)
        else:
            # "quase primos" + intruso
            arr = [2, 3, 5]
            intr = random.choice([4, 6, 8, 9, 10, 12])

        all4 = arr + [intr]
        random.shuffle(all4)
        correct = intr
        text = "Qual é o intruso (não segue o padrão)?"
        options = all4
        options = ensure_options(correct, options)
        return text, options, correct

    # grid: raciocínio rápido
    a = random.randint(2, 10 + diff)
    b = random.randint(2, 10 + diff)
    c = random.randint(2, 10 + diff)
    # regra: (a+b)*c
    correct = (a + b) * c
    text = f"Raciocínio: ({a} + {b}) × {c} = ?"
    options = [correct, correct + c, correct - c, correct + (a+b)]
    options = ensure_options(correct, options)
    return text, options, correct

def gen_trap(level, rating):
    # Armadilhas (ordem das operações, negativos, inversões)
    diff = level + int(rating * 10)
    trap_type = random.choice(["priority", "negative", "reverse"])

    if trap_type == "priority":
        a = random.randint(2, 9 + diff)
        b = random.randint(2, 9 + diff)
        c = random.randint(2, 9 + diff)
        # a + b*c (armadilha: (a+b)*c)
        correct = a + b * c
        wrong1 = (a + b) * c
        wrong2 = a * b + c
        wrong3 = a + b + c
        text = f"Armadilha ⚠️: {a} + {b} × {c} = ?"
        options = [correct, wrong1, wrong2, wrong3]
        options = ensure_options(correct, options)
        return text, options, correct

    if trap_type == "negative":
        a = random.randint(1, 10 + diff)
        b = random.randint(1, 10 + diff)
        correct = -a + b
        text = f"Armadilha ⚠️: (-{a}) + {b} = ?"
        options = [correct, -(a+b), b-a, a-b]
        options = ensure_options(correct, options)
        return text, options, correct

    # reverse
    x = random.randint(10, 50 + diff * 2)
    y = random.randint(2, 9 + diff)
    correct = x - y
    # armadilha: troca
    text = f"Armadilha ⚠️: {x} - {y} = ?"
    options = [correct, y - x, x + y, x - (y + 1)]
    options = ensure_options(correct, options)
    return text, options, correct

def gen_memory(level, rating):
    # Memória: mostra sequência e depois pergunta (fazemos em 2 etapas no front)
    diff = level + int(rating * 10)
    length = clamp(3 + level // 2 + int(rating * 3), 3, 10)
    seq = [random.randint(0, 9) for _ in range(length)]
    # Pergunta: qual era o dígito na posição k?
    k = random.randint(1, length)
    correct = seq[k-1]
    text = f"Memória 🧠: memorize a sequência (vai sumir!)"
    payload = {
        "sequence": seq,
        "ask": f"Qual era o número na posição {k}?",
        "k": k
    }
    options = [correct, (correct+1)%10, (correct+2)%10, (correct+3)%10]
    options = ensure_options(correct, options)
    return text, options, correct, payload

def make_question(mode, level, tier, rating):
    qid = f"{mode}:{level}:{tier}:{random.randint(100000,999999)}"
    if mode == "speed":
        text, options, correct = gen_arithmetic(level, rating)
        meta = {"hint": "⚡ Velocidade dá bônus."}
        return qid, text, options, correct, meta

    if mode == "logica":
        text, options, correct = gen_logic(level, rating)
        meta = {"hint": "🧩 Padrões e lógica."}
        return qid, text, options, correct, meta

    if mode == "armadilha":
        text, options, correct = gen_trap(level, rating)
        meta = {"hint": "🪤 Cuidado com pegadinhas."}
        return qid, text, options, correct, meta

    # memoria
    text, options, correct, payload = gen_memory(level, rating)
    meta = {"hint": "🧠 Memorize rápido!", "memory": payload}
    return qid, text, options, correct, meta

# =========================
# ADAPTATIVO + PONTUAÇÃO
# =========================

def compute_time_bonus(mode, ms):
    # quanto mais rápido, melhor (cap)
    if mode == "speed":
        if ms <= 1200: return 60
        if ms <= 2000: return 35
        if ms <= 3000: return 15
        return 0
    if mode == "memoria":
        if ms <= 2500: return 25
        return 0
    return 0

def compute_base_points(mode, level, tier, rating):
    base = 40 + (level * 6) + (tier * 4) + int(rating * 30)
    if mode == "armadilha":
        base += 10
    if mode == "logica":
        base += 8
    if mode == "memoria":
        base += 6
    return base

def update_rating(rating, correct, ms, mode):
    # rating sobe se acerta rápido, desce se erra
    r = rating
    if correct:
        gain = 0.04
        if mode == "speed" and ms <= 1800:
            gain += 0.03
        if mode == "logica":
            gain += 0.02
        r += gain
    else:
        r -= 0.06
    return clamp(r, 0.05, 0.98)

def level_progress(level, tier, correct, streak):
    # sobe de tier mais rápido com streak
    new_level = level
    new_tier = tier
    if correct:
        if streak % 3 == 0:
            new_tier += 1
        if new_tier >= 5:
            new_level += 1
            new_tier = 1
    else:
        # penaliza um pouco mas sem frustração
        if new_tier > 1:
            new_tier -= 1
    return new_level, new_tier

# =========================
# API
# =========================

@app.post("/api/next")
def api_next(req: NextQRequest):
    mode = req.mode.strip().lower()
    if mode not in ["speed", "logica", "armadilha", "memoria"]:
        return JSONResponse({"error": "Modo inválido"}, status_code=400)

    level = max(1, int(req.level))
    tier = clamp(int(req.tier), 1, 5)
    rating = clamp(float(req.rating), 0.05, 0.98)

    qid, text, options, correct, meta = make_question(mode, level, tier, rating)

    return {
        "qid": qid,
        "mode": mode,
        "level": level,
        "tier": tier,
        "rating": rating,
        "text": text,
        "options": options,
        "correct": correct,  # front usa para validar e pontuar
        "meta": meta,
        "start_ms": now_ms()
    }

@app.post("/api/answer")
def api_answer(req: AnswerRequest):
    mode = req.mode
    level = max(1, int(req.level))
    tier = clamp(int(req.tier), 1, 5)
    rating = clamp(float(req.rating), 0.05, 0.98)

    ms = max(1, int(req.end_ms - req.start_ms))
    is_correct = int(req.chosen) == int(req.correct)

    # combos/streak
    combo = int(req.combo)
    streak = int(req.streak)
    if is_correct:
        streak += 1
        combo = min(combo + 1, 20)
    else:
        streak = 0
        combo = 0

    base = compute_base_points(mode, level, tier, rating)
    time_bonus = compute_time_bonus(mode, ms)
    combo_bonus = combo * 4 if is_correct else 0
    penalty = 15 if not is_correct else 0

    points = (base + time_bonus + combo_bonus) - penalty
    points = max(0, points)

    new_rating = update_rating(rating, is_correct, ms, mode)
    new_level, new_tier = level_progress(level, tier, is_correct, streak)

    # feedback psicológico
    if is_correct:
        msgs = ["✅ Boa!", "🔥 Perfeito!", "🏆 Mandou bem!", "⚡ Rápido!", "😎 Nice!"]
        if combo >= 5:
            msgs.append("💥 COMBO INSANO!")
        if streak >= 7:
            msgs.append("🌟 STREAK LENDÁRIA!")
        msg = random.choice(msgs)
        mood = "good"
    else:
        msgs = ["❌ Quase!", "😅 Pegadinha?", "🧠 Respira e tenta de novo", "⚠️ Atenção!", "😵 Essa doeu"]
        msg = random.choice(msgs)
        mood = "bad"

    return {
        "correct": is_correct,
        "ms": ms,
        "points": points,
        "message": msg,
        "mood": mood,
        "combo": combo,
        "streak": streak,
        "level": new_level,
        "tier": new_tier,
        "rating": new_rating
    }

# =========================
# FRONT (HTML + JS)
# =========================

@app.get("/", response_class=HTMLResponse)
def home():
    return HTMLResponse(f"""
<!doctype html>
<html lang="pt-br">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1"/>
<title>Jogo Matemática — Turbo Edition</title>
<style>
  body {{
    margin:0; font-family: system-ui, -apple-system, Arial;
    background: radial-gradient(circle at top, #141a33, #060913);
    color:#fff;
  }}
  .wrap {{
    max-width:520px; margin:0 auto; padding:16px;
  }}
  h1 {{
    margin:10px 0 16px;
    font-size:26px;
  }}
  .pill {{
    display:inline-flex; gap:8px; align-items:center;
    padding:10px 12px; border-radius:14px;
    background: rgba(255,255,255,.06);
    border: 1px solid rgba(255,255,255,.08);
    margin:6px 6px 0 0;
  }}
  .panel {{
    margin-top:14px;
    background: rgba(255,255,255,.04);
    border:1px solid rgba(255,255,255,.08);
    border-radius:16px;
    padding:14px;
  }}
  .btn {{
    width:100%;
    padding:14px 12px;
    font-size:18px;
    border-radius:14px;
    border:1px solid rgba(255,255,255,.12);
    background: rgba(255,255,255,.08);
    color:#fff;
    margin-top:10px;
  }}
  .btn:active {{ transform: scale(.99); }}
  .grid {{
    display:grid;
    grid-template-columns: 1fr;
    gap:12px;
    margin-top:12px;
  }}
  .opt {{
    padding:16px;
    border-radius:16px;
    border:1px solid rgba(255,255,255,.12);
    background: rgba(255,255,255,.06);
    text-align:center;
    font-size:22px;
  }}
  .opt.good {{ border-color: rgba(50,255,140,.55); }}
  .opt.bad {{ border-color: rgba(255,80,80,.55); }}
  .bar {{
    height:10px; border-radius:99px;
    background: rgba(255,255,255,.08);
    overflow:hidden;
    margin-top:8px;
  }}
  .bar > div {{
    height:100%;
    width:0%;
    background: linear-gradient(90deg, #2ee59d, #ffca3a, #ff595e);
    transition: width .25s ease;
  }}
  .modal {{
    position:fixed; inset:0;
    background: rgba(0,0,0,.58);
    display:flex;
    align-items:center;
    justify-content:center;
    z-index:9999;
  }}
  .modalBox {{
    width:min(420px,92vw);
    background:#0b1020;
    border:1px solid rgba(255,255,255,.12);
    border-radius:18px;
    padding:16px;
  }}
  .hidden {{ display:none; }}
  .modes {{
    display:grid; grid-template-columns:1fr 1fr;
    gap:10px;
    margin-top:10px;
  }}
  .modeBtn {{
    padding:14px;
    border-radius:16px;
    border:1px solid rgba(255,255,255,.12);
    background: rgba(255,255,255,.06);
    color:#fff;
    font-size:16px;
  }}
  .small {{ opacity:.85; font-size:13px; }}
  .msg {{
    margin-top:10px;
    font-size:18px;
  }}
</style>
</head>
<body>
<div class="wrap">
  <h1>🧠 Jogo Matemática — Turbo Edition</h1>

  <div class="pill">👤 <span id="playerName">Bruno</span></div>
  <div class="pill">🏆 <span id="score">0</span></div>
  <div class="pill">⚡ Combo <span id="combo">0</span></div>
  <div class="pill">🔥 Streak <span id="streak">0</span></div>
  <div class="pill">🎚 Nível <span id="level">1</span> | Tier <span id="tier">1</span></div>
  <div class="pill">🧠 Adaptive <span id="rating">0.50</span></div>

  <div class="panel">
    <div class="small">Modo: <b id="modeLabel">—</b></div>
    <div class="small" id="hint">Escolha um modo para começar.</div>
    <div class="bar"><div id="timebar"></div></div>

    <div style="margin-top:12px; font-size:34px; font-weight:700;" id="question">—</div>

    <div class="grid" id="options"></div>

    <div class="msg" id="feedback"></div>

    <button class="btn" id="btnNext">Próxima</button>
    <button class="btn" id="btnChange">Trocar modo</button>
  </div>
</div>

<!-- MODAL: escolher modo -->
<div id="modeModal" class="modal">
  <div class="modalBox">
    <div style="font-size:20px; font-weight:700;">Escolha o modo</div>
    <div class="small">Cada modo muda o tipo de desafio. Simples de jogar, difícil de dominar.</div>
    <div class="modes">
      <button class="modeBtn" onclick="setMode('speed')">⚡ Speed<br><span class="small">tempo = bônus</span></button>
      <button class="modeBtn" onclick="setMode('logica')">🧩 Lógica<br><span class="small">padrões</span></button>
      <button class="modeBtn" onclick="setMode('armadilha')">🪤 Armadilha<br><span class="small">pegadinhas</span></button>
      <button class="modeBtn" onclick="setMode('memoria')">🧠 Memória<br><span class="small">sequência</span></button>
    </div>
    <button class="btn" onclick="closeModal()">Continuar</button>
  </div>
</div>

<script>
const state = {{
  mode: localStorage.getItem("mode") || "",
  score: Number(localStorage.getItem("score") || 0),
  combo: Number(localStorage.getItem("combo") || 0),
  streak: Number(localStorage.getItem("streak") || 0),
  level: Number(localStorage.getItem("level") || 1),
  tier: Number(localStorage.getItem("tier") || 1),
  rating: Number(localStorage.getItem("rating") || 0.50),
  q: null,
  lock: false,
}};

function saveState() {{
  localStorage.setItem("mode", state.mode);
  localStorage.setItem("score", state.score);
  localStorage.setItem("combo", state.combo);
  localStorage.setItem("streak", state.streak);
  localStorage.setItem("level", state.level);
  localStorage.setItem("tier", state.tier);
  localStorage.setItem("rating", state.rating.toFixed(2));
}}

function ui() {{
  document.getElementById("score").textContent = state.score;
  document.getElementById("combo").textContent = state.combo;
  document.getElementById("streak").textContent = state.streak;
  document.getElementById("level").textContent = state.level;
  document.getElementById("tier").textContent = state.tier;
  document.getElementById("rating").textContent = state.rating.toFixed(2);
  document.getElementById("modeLabel").textContent = state.mode || "—";
}}

function openModal() {{
  document.getElementById("modeModal").classList.remove("hidden");
}}
function closeModal() {{
  if (!state.mode) return; // não deixa fechar sem modo
  document.getElementById("modeModal").classList.add("hidden");
}}
function setMode(m) {{
  state.mode = m;
  state.combo = 0;
  state.streak = 0;
  saveState();
  ui();
  document.getElementById("feedback").textContent = "";
  closeModal();
  nextQuestion();
}}

async function nextQuestion() {{
  state.lock = true;
  ui();
  document.getElementById("options").innerHTML = "";
  document.getElementById("question").textContent = "Carregando...";
  document.getElementById("hint").textContent = "";

  const res = await fetch("/api/next", {{
    method:"POST",
    headers:{{"Content-Type":"application/json"}},
    body: JSON.stringify({{
      mode: state.mode,
      level: state.level,
      tier: state.tier,
      rating: state.rating,
      combo: state.combo,
      streak: state.streak
    }})
  }});
  const q = await res.json();
  state.q = q;

  document.getElementById("hint").textContent = q.meta?.hint || "";
  if (q.meta?.memory) {{
    // mostra sequência por 1.2s e depois troca a pergunta
    const seq = q.meta.memory.sequence.join(" ");
    document.getElementById("question").textContent = seq;
    setTimeout(() => {{
      document.getElementById("question").textContent = q.meta.memory.ask;
    }}, 1200);
  }} else {{
    document.getElementById("question").textContent = q.text;
  }}

  const box = document.getElementById("options");
  q.options.forEach(v => {{
    const b = document.createElement("div");
    b.className = "opt";
    b.textContent = v;
    b.onclick = () => choose(v, b);
    box.appendChild(b);
  }});

  // barra de tempo (efeito psicológico)
  let t0 = Date.now();
  const bar = document.getElementById("timebar");
  bar.style.width = "0%";
  const maxMs = (state.mode === "speed") ? 4500 : 9000;
  const timer = setInterval(() => {{
    const dt = Date.now() - t0;
    const pct = Math.min(100, (dt / maxMs) * 100);
    bar.style.width = pct + "%";
    if (pct >= 100) clearInterval(timer);
  }}, 80);

  state.lock = false;
}}

async function choose(val, el) {{
  if (state.lock) return;
  state.lock = true;

  const q = state.q;
  const end = Date.now();

  // feedback visual imediato
  const opts = Array.from(document.querySelectorAll(".opt"));
  opts.forEach(o => o.onclick = null);

  const res = await fetch("/api/answer", {{
    method:"POST",
    headers:{{"Content-Type":"application/json"}},
    body: JSON.stringify({{
      mode: q.mode,
      level: q.level,
      tier: q.tier,
      rating: q.rating,
      combo: state.combo,
      streak: state.streak,
      qid: q.qid,
      chosen: val,
      correct: q.correct,
      start_ms: q.start_ms,
      end_ms: end
    }})
  }});
  const out = await res.json();

  if (out.correct) {{
    el.classList.add("good");
  }} else {{
    el.classList.add("bad");
    // marca a correta
    opts.forEach(o => {{
      if (Number(o.textContent) === Number(q.correct)) o.classList.add("good");
    }});
  }}

  state.score += out.points;
  state.combo = out.combo;
  state.streak = out.streak;
  state.level = out.level;
  state.tier = out.tier;
  state.rating = out.rating;

  document.getElementById("feedback").textContent =
    `${out.message}  +${out.points} pts  (${out.ms}ms)`;

  saveState();
  ui();
}}

document.getElementById("btnNext").onclick = () => {{
  if (!state.mode) {{
    openModal();
    return;
  }}
  nextQuestion();
}};
document.getElementById("btnChange").onclick = () => {{
  openModal();
}};

(function init() {{
  ui();
  if (!state.mode) {{
    openModal();
  }} else {{
    closeModal();
    nextQuestion();
  }}
}})();
</script>
</body>
</html>
    """)

