from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import random
import time
import math
import hashlib
from typing import Dict, Any, List, Optional

app = FastAPI(title="Jogo Matemática (Turbo Edition)")

# =========================================================
# ESTADO EM MEMÓRIA (simples). Depois você troca por banco.
# =========================================================
PLAYERS: Dict[str, Dict[str, Any]] = {}
QUESTIONS: Dict[str, Dict[str, Any]] = {}

MODES = ["speed", "logic", "trap", "memory"]

def now_ms() -> int:
    return int(time.time() * 1000)

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def get_player(player_id: str) -> Dict[str, Any]:
    if player_id not in PLAYERS:
        PLAYERS[player_id] = {
            "player_id": player_id,
            "level": 1,
            "xp": 0,
            "streak": 0,
            "best_streak": 0,
            "combo": 0,
            "score": 0,
            "rating": 0.0,     # dificuldade adaptativa (sobe/desce)
            "mode": "speed",
            "last_play_day": None,
            "daily_done": False,
            "stats": {
                "correct": 0,
                "wrong": 0,
                "total": 0,
                "avg_time_ms": 0
            }
        }
    return PLAYERS[player_id]

def level_from_xp(xp: int) -> int:
    # curva simples (vai ficando mais caro)
    # nível ~ cresce com sqrt
    return max(1, int(math.sqrt(xp / 120)) + 1)

def xp_to_next(level: int) -> int:
    # custo do próximo nível
    return 120 * (level ** 2)

def update_avg(old_avg, old_n, new_value):
    if old_n <= 0:
        return new_value
    return int((old_avg * old_n + new_value) / (old_n + 1))

def sign_question_payload(q: Dict[str, Any], secret: str = "salt_local") -> str:
    # assinatura simples anti-“refresh trap” (não é segurança forte, mas ajuda)
    s = f"{q['question_id']}|{q['player_id']}|{q['created_ms']}|{secret}"
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

# =========================================================
# GERAÇÃO DE DESAFIOS (progressão por nível + modos)
# =========================================================

def band(level: int) -> int:
    # Faixas que mudam o tipo de desafio
    # 1-3: soma/sub
    # 4-6: mult/div
    # 7-9: frações/porcentagem
    # 10-12: potência/raiz + expressões
    # 13+: lógica/padrões mais forte
    if level <= 3: return 1
    if level <= 6: return 2
    if level <= 9: return 3
    if level <= 12: return 4
    return 5

def pick_difficulty(level: int, rating: float) -> Dict[str, Any]:
    # rating sobe se acerta rápido, desce se erra muito
    # gera um "tier" e parâmetros
    b = band(level)
    # tier base pelo band + rating
    tier = b + int(round(rating))
    tier = clamp(tier, 1, 7)

    # range cresce com tier
    base = 10 + tier * 10
    return {
        "tier": tier,
        "max_n": base,
        "allow_neg": tier >= 3,
        "digits": 1 if tier <= 2 else (2 if tier <= 4 else 3),
    }

def make_arithmetic_question(tier: int, max_n: int, allow_neg: bool) -> Dict[str, Any]:
    ops = []
    if tier <= 2:
        ops = ["+", "-"]
    elif tier <= 4:
        ops = ["+", "-", "×", "÷"]
    else:
        ops = ["+", "-", "×", "÷", "^"]

    op = random.choice(ops)

    if op in ["+", "-"]:
        a = random.randint(1, max_n)
        b = random.randint(1, max_n)
        if op == "-" and not allow_neg:
            a, b = max(a, b), min(a, b)
        answer = a + b if op == "+" else a - b
        text = f"{a} {op} {b} = ?"
        return {"text": text, "answer": answer, "meta": {"type": "arith", "op": op}}

    if op == "×":
        a = random.randint(2, max(5, max_n // 3))
        b = random.randint(2, max(5, max_n // 3))
        answer = a * b
        text = f"{a} × {b} = ?"
        return {"text": text, "answer": answer, "meta": {"type": "arith", "op": op}}

    if op == "÷":
        b = random.randint(2, max(5, max_n // 4))
        answer = random.randint(2, max(10, max_n // 6))
        a = b * answer
        text = f"{a} ÷ {b} = ?"
        return {"text": text, "answer": answer, "meta": {"type": "arith", "op": op}}

    # potência (tier alto)
    if op == "^":
        a = random.randint(2, 6)
        b = random.randint(2, 4)
        answer = a ** b
        text = f"{a}^{b} = ?"
        return {"text": text, "answer": answer, "meta": {"type": "arith", "op": op}}

def make_logic_question(tier: int) -> Dict[str, Any]:
    # padrões / sequência
    # tier define o “pulo” e complexidade
    if tier <= 3:
        start = random.randint(1, 20)
        step = random.randint(2, 9)
        seq = [start + i * step for i in range(4)]
        answer = start + 4 * step
        text = f"Complete a sequência: {seq[0]}, {seq[1]}, {seq[2]}, {seq[3]}, ?"
        return {"text": text, "answer": answer, "meta": {"type": "logic", "kind": "arithmetic_seq"}}

    if tier <= 5:
        start = random.randint(2, 6)
        ratio = random.randint(2, 4)
        seq = [start * (ratio ** i) for i in range(4)]
        answer = start * (ratio ** 4)
        text = f"Complete a sequência: {seq[0]}, {seq[1]}, {seq[2]}, {seq[3]}, ?"
        return {"text": text, "answer": answer, "meta": {"type": "logic", "kind": "geom_seq"}}

    # “mistura”: +, × alternando
    a = random.randint(2, 10)
    add = random.randint(2, 9)
    mul = random.randint(2, 4)
    seq = [a]
    for i in range(3):
        seq.append(seq[-1] + add if i % 2 == 0 else seq[-1] * mul)
    # próximo passo
    answer = seq[-1] + add if 3 % 2 == 0 else seq[-1] * mul
    text = f"Padrão alternado: {seq[0]}, {seq[1]}, {seq[2]}, {seq[3]}, ?"
    return {"text": text, "answer": answer, "meta": {"type": "logic", "kind": "alt_ops"}}

def make_memory_question(tier: int) -> Dict[str, Any]:
    # mostra por poucos segundos e depois pergunta
    # aqui o servidor já manda o “prompt” e o front controla o hide
    length = clamp(3 + tier, 4, 10)
    digits = [str(random.randint(0, 9)) for _ in range(length)]
    code = "".join(digits)
    # pergunta: qual era o código?
    text = f"MEMÓRIA: memorize o código → {code}"
    return {"text": text, "answer": code, "meta": {"type": "memory", "hide_after_ms": clamp(1600 + tier * 250, 1500, 3500)}}

def make_trap_question(tier: int, max_n: int) -> Dict[str, Any]:
    # “Armadilha”: pegadinha de prioridade / aproximação / sinal / distrações
    if tier <= 3:
        a = random.randint(3, max(10, max_n//2))
        b = random.randint(2, 9)
        c = random.randint(2, 9)
        # prioridade: multiplicação antes de soma
        text = f"Pegadinha: {a} + {b} × {c} = ?"
        answer = a + (b * c)
        return {"text": text, "answer": answer, "meta": {"type": "trap", "kind": "precedence"}}

    if tier <= 5:
        a = random.randint(10, max_n)
        b = random.randint(2, 9)
        text = f"Pegadinha: {a} ÷ {b} (arredonde para inteiro mais próximo)"
        answer = int(round(a / b))
        return {"text": text, "answer": answer, "meta": {"type": "trap", "kind": "round"}}

    # sinais
    a = random.randint(5, max_n)
    b = random.randint(5, max_n)
    text = f"Pegadinha: -({a} - {b}) = ?"
    answer = -(a - b)
    return {"text": text, "answer": answer, "meta": {"type": "trap", "kind": "sign"}}

def make_options(correct, meta: Dict[str, Any], tier: int) -> List[Any]:
    # opções “inteligentes”: perto do correto + armadilhas coerentes
    opts = set()

    def add_opt(x):
        if isinstance(correct, str):
            if isinstance(x, str) and x != "":
                opts.add(x)
        else:
            try:
                opts.add(int(x))
            except:
                pass

    add_opt(correct)

    if isinstance(correct, str):
        # memória: mudar 1 dígito
        for _ in range(10):
            s = list(correct)
            idx = random.randrange(len(s))
            s[idx] = str((int(s[idx]) + random.randint(1, 9)) % 10)
            add_opt("".join(s))
            if len(opts) >= 4:
                break
        # fallback
        while len(opts) < 4:
            add_opt("".join(str(random.randint(0,9)) for _ in range(len(correct))))
        out = list(opts)
        random.shuffle(out)
        return out[:4]

    # numérico
    spread = clamp(2 + tier * 2, 4, 18)
    candidates = [
        correct + 1,
        correct - 1,
        correct + spread,
        correct - spread,
        correct + (spread // 2),
        correct - (spread // 2),
    ]

    # armadilhas específicas
    if meta.get("type") == "trap" and meta.get("kind") == "precedence":
        # “errado comum”: (a+b)*c (não sabemos a,b,c aqui, mas criamos um desvio maior)
        candidates.append(correct + spread * 3)
        candidates.append(correct - spread * 3)

    for c in candidates:
        add_opt(c)

    while len(opts) < 4:
        add_opt(correct + random.randint(-spread * 3, spread * 3))

    out = list(opts)
    random.shuffle(out)
    return out[:4]

def generate_question(player: Dict[str, Any]) -> Dict[str, Any]:
    level = player["level"]
    rating = player["rating"]
    mode = player["mode"]

    diff = pick_difficulty(level, rating)
    tier = diff["tier"]

    if mode == "speed":
        q = make_arithmetic_question(tier, diff["max_n"], diff["allow_neg"])
        time_limit_ms = clamp(6500 - tier * 450, 1800, 6500)
    elif mode == "logic":
        q = make_logic_question(tier)
        time_limit_ms = clamp(12000 - tier * 500, 5000, 12000)
    elif mode == "trap":
        q = make_trap_question(tier, diff["max_n"])
        time_limit_ms = clamp(9000 - tier * 450, 3500, 9000)
    elif mode == "memory":
        q = make_memory_question(tier)
        time_limit_ms = clamp(10000 - tier * 400, 4500, 10000)
    else:
        player["mode"] = "speed"
        return generate_question(player)

    correct = q["answer"]
    options = make_options(correct, q["meta"], tier)

    qid = f"q_{player['player_id']}_{now_ms()}_{random.randint(1000,9999)}"
    created = now_ms()

    stored = {
        "question_id": qid,
        "player_id": player["player_id"],
        "mode": mode,
        "level": level,
        "tier": tier,
        "text": q["text"],
        "meta": q["meta"],
        "options": options,
        "correct": correct,
        "created_ms": created,
        "time_limit_ms": time_limit_ms,
    }
    QUESTIONS[qid] = stored

    payload = {
        "question_id": qid,
        "mode": mode,
        "level": level,
        "tier": tier,
        "text": q["text"],
        "meta": q["meta"],
        "options": options,
        "created_ms": created,
        "time_limit_ms": time_limit_ms,
        "sig": sign_question_payload(stored),
        "player": {
            "score": player["score"],
            "level": player["level"],
            "xp": player["xp"],
            "xp_next": xp_to_next(player["level"]),
            "streak": player["streak"],
            "combo": player["combo"],
            "rating": round(player["rating"], 2),
            "mode": player["mode"],
        }
    }
    return payload

def compute_score_delta(correct: bool, time_ms: int, time_limit_ms: int, tier: int, streak: int, combo: int, mode: str) -> Dict[str, Any]:
    # Base
    base = 10 + tier * 4

    # Speed bonus / penalty
    speed_factor = clamp(1.0 - (time_ms / max(1, time_limit_ms)), -0.5, 1.0)
    speed_bonus = int(round(base * 0.8 * max(0.0, speed_factor)))

    # Combo multiplier
    combo_mult = 1.0 + min(combo, 12) * 0.07

    # Mode spice
    mode_mult = {
        "speed": 1.0,
        "logic": 1.25,
        "trap": 1.2,
        "memory": 1.15
    }.get(mode, 1.0)

    if correct:
        gained = int(round((base + speed_bonus) * combo_mult * mode_mult))
        xp_gain = int(round((6 + tier * 2) * (1.0 + min(streak, 20) * 0.03)))
        # bonus “perfeito”
        perfect = time_ms <= int(time_limit_ms * 0.35)
        if perfect:
            gained += int(10 + tier * 3)
            xp_gain += 6
        return {"score": gained, "xp": xp_gain, "perfect": perfect, "penalty": 0}
    else:
        # penalidade: quebra combo e tira pontos, mas sem “matar” o player
        penalty = int(round((8 + tier * 3) * mode_mult))
        return {"score": -penalty, "xp": 0, "perfect": False, "penalty": penalty}

def adjust_rating(player: Dict[str, Any], correct: bool, time_ms: int, time_limit_ms: int):
    # adaptativo: acerto rápido => sobe; erro => desce
    # também leva em conta "quão rápido"
    if correct:
        speed = clamp(1.0 - (time_ms / max(1, time_limit_ms)), 0.0, 1.0)
        player["rating"] += 0.10 + 0.25 * speed
    else:
        player["rating"] -= 0.35
    player["rating"] = clamp(player["rating"], -1.5, 3.5)

def apply_leveling(player: Dict[str, Any]):
    new_level = level_from_xp(player["xp"])
    if new_level > player["level"]:
        player["level"] = new_level

class StartPayload(BaseModel):
    player_id: str
    mode: str

class AnswerPayload(BaseModel):
    player_id: str
    question_id: str
    sig: str
    answer: Any
    time_ms: int

@app.post("/api/start")
def api_start(payload: StartPayload):
    player = get_player(payload.player_id)
    if payload.mode in MODES:
        player["mode"] = payload.mode
    else:
        player["mode"] = "speed"
    q = generate_question(player)
    return JSONResponse(q)

@app.post("/api/next")
def api_next(payload: StartPayload):
    player = get_player(payload.player_id)
    if payload.mode in MODES:
        player["mode"] = payload.mode
    q = generate_question(player)
    return JSONResponse(q)

@app.post("/api/answer")
def api_answer(payload: AnswerPayload):
    player = get_player(payload.player_id)
    q = QUESTIONS.get(payload.question_id)
    if not q:
        return JSONResponse({"ok": False, "error": "Pergunta expirada. Clique em Próxima."}, status_code=400)

    # assinatura confere?
    if payload.sig != sign_question_payload(q):
        return JSONResponse({"ok": False, "error": "Assinatura inválida. Recarregue a pergunta."}, status_code=400)

    # valida tempo
    time_ms = max(0, int(payload.time_ms))
    time_limit = int(q["time_limit_ms"])
    timed_out = time_ms > time_limit + 1500  # tolerância

    correct_value = q["correct"]
    user_answer = payload.answer

    is_correct = False
    if isinstance(correct_value, str):
        is_correct = str(user_answer).strip() == correct_value
    else:
        try:
            is_correct = int(user_answer) == int(correct_value)
        except:
            is_correct = False

    if timed_out:
        is_correct = False

    # stats
    st = player["stats"]
    st["total"] += 1
    st["avg_time_ms"] = update_avg(st["avg_time_ms"], st["total"]-1, time_ms)
    if is_correct:
        st["correct"] += 1
    else:
        st["wrong"] += 1

    # combo/streak
    if is_correct:
        player["streak"] += 1
        player["combo"] += 1
        player["best_streak"] = max(player["best_streak"], player["streak"])
    else:
        player["streak"] = 0
        player["combo"] = 0

    adjust_rating(player, is_correct, time_ms, time_limit)

    tier = int(q["tier"])
    mode = q["mode"]
    delta = compute_score_delta(is_correct, time_ms, time_limit, tier, player["streak"], player["combo"], mode)

    player["score"] += delta["score"]
    player["score"] = max(0, player["score"])  # não deixa negativo
    player["xp"] += delta["xp"]
    apply_leveling(player)

    # “limpa” a pergunta pra não responder 2x
    QUESTIONS.pop(payload.question_id, None)

    # mensagens “psicológicas”
    if is_correct:
        if delta["perfect"]:
            mood = "PERFEITO! 🔥"
        elif player["combo"] >= 5:
            mood = f"COMBO x{player['combo']} ⚡"
        else:
            mood = "Boa! ✅"
    else:
        mood = "Quase! 😅" if not timed_out else "Tempo! ⏳"

    # “o que desbloqueou” (feedback de progressão)
    b = band(player["level"])
    unlock = {
        1: "Soma/Subtração",
        2: "Multiplicação/Divisão",
        3: "Frações/Porcentagens (misturadas)",
        4: "Potência/Expressões",
        5: "Lógica avançada e pegadinhas"
    }.get(b, "Desafios avançados")

    return JSONResponse({
        "ok": True,
        "correct": is_correct,
        "timed_out": timed_out,
        "correct_answer": correct_value if isinstance(correct_value, str) else int(correct_value),
        "delta": delta,
        "mood": mood,
        "unlock": unlock,
        "player": {
            "score": player["score"],
            "level": player["level"],
            "xp": player["xp"],
            "xp_next": xp_to_next(player["level"]),
            "streak": player["streak"],
            "best_streak": player["best_streak"],
            "combo": player["combo"],
            "rating": round(player["rating"], 2),
            "mode": player["mode"],
            "stats": player["stats"]
        }
    })

# =========================================================
# FRONTEND (HTML + JS) — você pode manter seu HTML atual
# e só trocar o <script> se preferir.
# =========================================================

HTML = r"""
<!doctype html>
<html lang="pt-br">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>Jogo Matemática — Turbo</title>
  <style>
    :root{
      --bg:#0b1020; --card:#121a33; --card2:#0f1730;
      --txt:#e9eeff; --mut:#9aa8d7;
      --ok:#19d18a; --bad:#ff4d6d; --warn:#ffd166; --acc:#6aa6ff;
      --shadow: 0 10px 30px rgba(0,0,0,.35);
    }
    body{margin:0;background:radial-gradient(1200px 600px at 20% 0%, #16214a, var(--bg));
      color:var(--txt);font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial;}
    .wrap{max-width:980px;margin:0 auto;padding:18px;}
    .top{display:flex;gap:12px;flex-wrap:wrap;align-items:center;justify-content:space-between;}
    .title{font-weight:800;font-size:18px;letter-spacing:.2px}
    .pill{background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.10);
      padding:8px 10px;border-radius:999px;color:var(--mut);font-size:12px}
    .grid{display:grid;grid-template-columns:1.2fr .8fr;gap:14px;margin-top:14px}
    @media(max-width:900px){.grid{grid-template-columns:1fr}}
    .card{background:linear-gradient(180deg,var(--card),var(--card2));
      border:1px solid rgba(255,255,255,.10);border-radius:16px;padding:14px;box-shadow:var(--shadow)}
    .row{display:flex;gap:10px;align-items:center;flex-wrap:wrap}
    .modes{display:flex;gap:8px;flex-wrap:wrap;margin-top:8px}
    button{cursor:pointer;border:0;border-radius:12px;padding:10px 12px;
      font-weight:700;color:var(--txt);background:rgba(255,255,255,.08);
      border:1px solid rgba(255,255,255,.12)}
    button:hover{filter:brightness(1.08)}
    .btn-main{background:linear-gradient(90deg,var(--acc),#8b5cf6);border:0}
    .btn-ghost{background:transparent;border:1px solid rgba(255,255,255,.16)}
    .btn-mode.active{outline:2px solid rgba(106,166,255,.45)}
    .q{font-size:22px;font-weight:900;margin:8px 0 6px}
    .meta{color:var(--mut);font-size:12px}
    .timer{height:10px;background:rgba(255,255,255,.08);border-radius:999px;overflow:hidden;margin-top:10px}
    .bar{height:100%;width:100%;background:linear-gradient(90deg,var(--ok),var(--warn),var(--bad))}
    .opts{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:12px}
    @media(max-width:520px){.opts{grid-template-columns:1fr}}
    .opt{padding:12px;border-radius:14px;background:rgba(255,255,255,.06);
      border:1px solid rgba(255,255,255,.12);font-size:16px;font-weight:800}
    .opt.ok{border-color:rgba(25,209,138,.8);background:rgba(25,209,138,.12)}
    .opt.bad{border-color:rgba(255,77,109,.8);background:rgba(255,77,109,.10)}
    .flash{animation:pop .22s ease-out}
    @keyframes pop{from{transform:scale(.98)}to{transform:scale(1)}}
    .hud{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-top:10px}
    @media(max-width:600px){.hud{grid-template-columns:repeat(2,1fr)}}
    .k{color:var(--mut);font-size:11px}
    .v{font-weight:900;font-size:16px}
    .msg{margin-top:10px;font-weight:900}
    .msg.ok{color:var(--ok)} .msg.bad{color:var(--bad)} .msg.warn{color:var(--warn)}
    .small{color:var(--mut);font-size:12px}
    .badge{display:inline-flex;align-items:center;gap:8px;padding:8px 10px;border-radius:999px;
      background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.10)}
    .sep{height:1px;background:rgba(255,255,255,.10);margin:12px 0}
    input{background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.12);
      border-radius:12px;color:var(--txt);padding:10px 12px;font-weight:800;outline:none}
    .memHide{filter:blur(10px);user-select:none}
  </style>
</head>
<body>
<div class="wrap">
  <div class="top">
    <div class="title">🧠 Jogo Matemática — Turbo Edition</div>
    <div class="row">
      <span class="pill" id="pillUnlock">Desafios: —</span>
      <span class="pill" id="pillRating">Adaptive: —</span>
    </div>
  </div>

  <div class="grid">
    <div class="card">
      <div class="row" style="justify-content:space-between">
        <div class="row">
          <span class="badge">👤 <span id="playerIdView">player</span></span>
          <span class="badge">🏆 <span id="scoreView">0</span></span>
          <span class="badge">⚡ Combo <span id="comboView">0</span></span>
          <span class="badge">🔥 Streak <span id="streakView">0</span></span>
        </div>
        <div class="row">
          <button class="btn-ghost" id="btnNewId">Trocar jogador</button>
          <button class="btn-main" id="btnNext">Próxima</button>
        </div>
      </div>

      <div class="sep"></div>

      <div class="row" style="justify-content:space-between">
        <div>
          <div class="meta" id="metaLine">Modo: — | Nível: — | Tier: —</div>
          <div class="q" id="qText">Clique em "Próxima" para começar.</div>
          <div class="small" id="smallHint"></div>
        </div>
      </div>

      <div class="timer"><div class="bar" id="bar"></div></div>

      <div class="opts" id="opts"></div>

      <div class="msg" id="msg"></div>
    </div>

    <div class="card">
      <div class="k">MODOS (muda o jogo de verdade)</div>
      <div class="modes">
        <button class="btn-mode" data-mode="speed">⚡ Speed</button>
        <button class="btn-mode" data-mode="logic">🧩 Lógica</button>
        <button class="btn-mode" data-mode="trap">🪤 Armadilha</button>
        <button class="btn-mode" data-mode="memory">🧠 Memória</button>
      </div>

      <div class="sep"></div>

      <div class="hud">
        <div class="badge"><div><div class="k">Nível</div><div class="v" id="levelView">1</div></div></div>
        <div class="badge"><div><div class="k">XP</div><div class="v"><span id="xpView">0</span>/<span id="xpNextView">120</span></div></div></div>
        <div class="badge"><div><div class="k">Acertos</div><div class="v" id="accView">0</div></div></div>
        <div class="badge"><div><div class="k">Tempo médio</div><div class="v" id="avgView">—</div></div></div>
      </div>

      <div class="sep"></div>
      <div class="small">
        💡 Dica: o jogo fica mais difícil se você acertar rápido.  
        Erros baixam a dificuldade — mas quebram combo.
      </div>
    </div>
  </div>
</div>

<script>
(() => {
  // =========================
  // UTIL / ESTADO
  // =========================
  const $ = (id) => document.getElementById(id);
  const sleep = (ms) => new Promise(r => setTimeout(r, ms));

  const state = {
    playerId: localStorage.getItem("player_id") || ("p_" + Math.random().toString(16).slice(2, 10)),
    mode: localStorage.getItem("mode") || "speed",
    question: null,
    startedAt: 0,
    timer: null,
    timeLeftMs: 0,
    locked: false
  };

  function setActiveModeBtn() {
    document.querySelectorAll(".btn-mode").forEach(b => {
      b.classList.toggle("active", b.dataset.mode === state.mode);
    });
  }

  function fmtMs(ms){
    if (!ms && ms !== 0) return "—";
    if (ms < 1000) return ms + "ms";
    return (ms/1000).toFixed(1) + "s";
  }

  function moodFlash(kind){
    const el = $("msg");
    el.classList.remove("ok","bad","warn","flash");
    el.classList.add("flash");
    if (kind) el.classList.add(kind);
  }

  function renderPlayer(p){
    $("playerIdView").textContent = state.playerId;
    $("scoreView").textContent = p.score;
    $("comboView").textContent = p.combo;
    $("streakView").textContent = p.streak;

    $("levelView").textContent = p.level;
    $("xpView").textContent = p.xp;
    $("xpNextView").textContent = p.xp_next;

    const total = p.stats.total || 0;
    const correct = p.stats.correct || 0;
    const acc = total ? Math.round((correct/total)*100) : 0;
    $("accView").textContent = acc + "%";
    $("avgView").textContent = fmtMs(p.stats.avg_time_ms);

    $("pillRating").textContent = "Adaptive: " + (p.rating ?? "—");
  }

  function renderQuestion(q){
    state.question = q;
    state.locked = false;
    $("metaLine").textContent = `Modo: ${q.mode} | Nível: ${q.level} | Tier: ${q.tier}`;
    $("qText").textContent = q.text;
    $("smallHint").textContent = hintFor(q);

    $("opts").innerHTML = "";
    $("msg").textContent = "";

    // memory mode: esconder depois
    if (q.meta && q.meta.type === "memory" && q.meta.hide_after_ms){
      $("qText").classList.remove("memHide");
      setTimeout(() => {
        // só esconde se ainda for a mesma pergunta
        if (state.question && state.question.question_id === q.question_id) {
          $("qText").classList.add("memHide");
          $("qText").textContent = "MEMÓRIA: qual era o código?";
        }
      }, q.meta.hide_after_ms);
    } else {
      $("qText").classList.remove("memHide");
    }

    q.options.forEach((opt) => {
      const b = document.createElement("button");
      b.className = "opt";
      b.textContent = opt;
      b.onclick = () => choose(opt, b);
      $("opts").appendChild(b);
    });

    // timer
    startTimer(q.time_limit_ms);
    state.startedAt = performance.now();

    $("pillUnlock").textContent = "Desafios: " + (q.player?.mode ? "—" : "—");
    if (q.player) renderPlayer(q.player);
  }

  function hintFor(q){
    if (!q.meta) return "";
    const t = q.meta.type;
    if (t === "trap") return "🪤 Atenção: tem pegadinha.";
    if (t === "logic") return "🧩 Procure o padrão.";
    if (t === "memory") return "🧠 Memorize rápido e responda.";
    if (t === "arith") return "⚡ Velocidade dá bônus.";
    return "";
  }

  function startTimer(limitMs){
    stopTimer();
    state.timeLeftMs = limitMs;
    updateBar(1);
    state.timer = setInterval(() => {
      state.timeLeftMs -= 60;
      const ratio = Math.max(0, state.timeLeftMs / limitMs);
      updateBar(ratio);
      if (state.timeLeftMs <= 0){
        stopTimer();
        if (!state.locked) {
          // auto envia errado por tempo
          submitAnswer("__timeout__");
        }
      }
    }, 60);
  }

  function stopTimer(){
    if (state.timer) clearInterval(state.timer);
    state.timer = null;
  }

  function updateBar(ratio){
    $("bar").style.width = (ratio*100).toFixed(1) + "%";
  }

  async function api(path, data){
    const res = await fetch(path, {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify(data)
    });
    const j = await res.json();
    if (!res.ok) throw new Error(j.error || "Erro");
    return j;
  }

  async function next(){
    const q = await api("/api/next", {player_id: state.playerId, mode: state.mode});
    renderQuestion(q);
    setActiveModeBtn();
  }

  async function start(){
    const q = await api("/api/start", {player_id: state.playerId, mode: state.mode});
    renderQuestion(q);
    setActiveModeBtn();
  }

  function choose(opt, btn){
    if (state.locked) return;
    submitAnswer(opt, btn);
  }

  async function submitAnswer(answer, clickedBtn){
    if (!state.question) return;
    state.locked = true;
    stopTimer();

    const elapsed = Math.max(0, Math.round(performance.now() - state.startedAt));
    try{
      const result = await api("/api/answer", {
        player_id: state.playerId,
        question_id: state.question.question_id,
        sig: state.question.sig,
        answer,
        time_ms: elapsed
      });

      // feedback
      $("pillUnlock").textContent = "Desafios: " + result.unlock;
      renderPlayer(result.player);

      if (result.correct){
        $("msg").textContent = `${result.mood} +${result.delta.score} pts  | +${result.delta.xp} XP`;
        moodFlash("ok");
      } else {
        $("msg").textContent = `${result.mood} (-${result.delta.penalty} pts)  | Resposta: ${result.correct_answer}`;
        moodFlash(result.timed_out ? "warn" : "bad");
      }

      // marcar botões
      const opts = Array.from(document.querySelectorAll(".opt"));
      opts.forEach(b => {
        if (String(b.textContent) === String(result.correct_answer)) b.classList.add("ok");
        if (clickedBtn && b === clickedBtn && !result.correct) b.classList.add("bad");
      });

      // “gancho viciante”: pequena pausa e próxima
      await sleep(result.correct ? 450 : 700);
      await next();
    } catch(e){
      $("msg").textContent = "Erro: " + e.message;
      moodFlash("bad");
      state.locked = false;
    }
  }

  function newPlayerId(){
    const id = prompt("Digite um nome/ID (ex: bruno) ou deixe vazio para aleatório:");
    state.playerId = id && id.trim() ? id.trim() : ("p_" + Math.random().toString(16).slice(2, 10));
    localStorage.setItem("player_id", state.playerId);
    start();
  }

  // =========================
  // EVENTOS UI
  // =========================
  document.querySelectorAll(".btn-mode").forEach(b => {
    b.addEventListener("click", async () => {
      state.mode = b.dataset.mode;
      localStorage.setItem("mode", state.mode);
      setActiveModeBtn();
      await next();
    });
  });

  $("btnNext").addEventListener("click", next);
  $("btnNewId").addEventListener("click", newPlayerId);

  // boot
  $("playerIdView").textContent = state.playerId;
  setActiveModeBtn();
  start();
})();
</script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
def home():
    return HTMLResponse(HTML)
