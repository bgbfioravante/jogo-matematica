from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from datetime import datetime, date
import random
import uuid
import math

app = FastAPI()

# -----------------------------
# In-memory stores (simples)
# -----------------------------
QUESTIONS = {}  # qid -> {correct_index:int, answer:any, meta:dict}
LEADERBOARD = {}  # name -> best_score (max)
RECENT = {}  # player_id -> last_seen iso


# -----------------------------
# Helpers
# -----------------------------
def clamp(x, a, b):
    return max(a, min(b, x))


def now_iso():
    return datetime.utcnow().isoformat()


def seeded_rng(seed: str) -> random.Random:
    # RNG determinístico a partir de string
    r = random.Random()
    r.seed(seed)
    return r


def make_choices(correct, spread=8, n=4, rng=None, allow_float=False):
    rng = rng or random.Random()
    choices = set()
    choices.add(correct)

    # gerar "distratores"
    while len(choices) < n:
        if isinstance(correct, float) or allow_float:
            # distratores próximos
            delta = (rng.randint(-spread, spread) or 1) * (0.1 if rng.random() < 0.5 else 0.5)
            cand = round(float(correct) + delta, 2)
        else:
            delta = rng.randint(-spread, spread) or 1
            cand = int(correct) + delta
        choices.add(cand)

    choices = list(choices)
    rng.shuffle(choices)
    correct_index = choices.index(correct)
    return choices, correct_index


def difficulty_params(mode: str, level: int, skill: float):
    """
    skill: 0..1 (adaptativo)
    level: 1..
    """
    # tier aumenta com level + skill
    tier = 1 + (level // 3)
    tier = clamp(tier, 1, 8)

    # base range
    base = 10 + tier * 6
    # skill empurra range
    base = int(base * (1.0 + 0.8 * skill))

    # time limit (ms) principalmente pro speed
    if mode == "speed":
        t = int(4200 - (tier * 250) - (skill * 1200))
        t = clamp(t, 1400, 5000)
    else:
        t = 0

    return tier, base, t


def gen_question(mode: str, level: int, skill: float, rng: random.Random):
    tier, base, time_limit_ms = difficulty_params(mode, level, skill)

    # mix por tier
    ops = []
    if tier <= 2:
        ops = ["add", "sub"]
    elif tier <= 4:
        ops = ["add", "sub", "mul"]
    elif tier <= 6:
        ops = ["add", "sub", "mul", "div", "pct"]
    else:
        ops = ["mul", "div", "pct", "pow", "mix"]

    # modos mudam o tipo de pergunta
    if mode == "logica":
        # padrões e sequências
        kind = rng.choice(["seq", "oddOne", "miniLogic"])
        if kind == "seq":
            step = rng.randint(1, 4 + tier)
            start = rng.randint(1, base)
            # às vezes progressão multiplicativa
            if tier >= 5 and rng.random() < 0.35:
                mult = rng.randint(2, 4)
                seq = [start, start * mult, start * mult * mult, start * mult * mult * mult]
                ans = start * mult * mult * mult * mult
                prompt = f"Complete a sequência: {seq[0]}, {seq[1]}, {seq[2]}, {seq[3]}, ?"
                choices, ci = make_choices(ans, spread=base // 2, n=4, rng=rng)
                meta = {"tier": tier, "time_limit_ms": 0, "mode": mode, "kind": kind}
                return prompt, choices, ci, meta
            else:
                seq = [start, start + step, start + 2 * step, start + 3 * step]
                ans = start + 4 * step
                prompt = f"Complete a sequência: {seq[0]}, {seq[1]}, {seq[2]}, {seq[3]}, ?"
                choices, ci = make_choices(ans, spread=base // 2, n=4, rng=rng)
                meta = {"tier": tier, "time_limit_ms": 0, "mode": mode, "kind": kind}
                return prompt, choices, ci, meta

        if kind == "oddOne":
            # 3 seguem regra, 1 é intruso
            rule = rng.choice(["even", "mul3", "prime", "square"])
            pool = []
            if rule == "even":
                pool = [rng.randrange(2, base, 2) for _ in range(3)]
                odd = rng.randrange(1, base, 2)
            elif rule == "mul3":
                pool = [3 * rng.randint(1, base // 3) for _ in range(3)]
                odd = rng.randint(1, base)
                while odd % 3 == 0:
                    odd = rng.randint(1, base)
            elif rule == "prime":
                primes = []
                x = 2
                while len(primes) < 60 and x < base * 3:
                    is_p = True
                    for p in range(2, int(math.sqrt(x)) + 1):
                        if x % p == 0:
                            is_p = False
                            break
                    if is_p:
                        primes.append(x)
                    x += 1
                pool = [rng.choice(primes) for _ in range(3)]
                odd = rng.randint(4, base * 2)
                while any(odd == p for p in pool) or all(odd % k != 0 for k in range(2, int(math.sqrt(odd)) + 1)):
                    odd = rng.randint(4, base * 2)
            else:  # square
                a = rng.randint(2, int(math.sqrt(base * 4)))
                b = rng.randint(2, int(math.sqrt(base * 4)))
                c = rng.randint(2, int(math.sqrt(base * 4)))
                pool = [a * a, b * b, c * c]
                odd = rng.randint(5, base * 2)
                while int(math.isqrt(odd)) ** 2 == odd:
                    odd = rng.randint(5, base * 2)

            arr = pool + [odd]
            rng.shuffle(arr)
            correct = odd
            prompt = f"Qual é o intruso (não segue a regra)? {arr[0]}, {arr[1]}, {arr[2]}, {arr[3]}"
            choices = arr[:]  # 4 opções já são os 4 números
            ci = choices.index(correct)
            meta = {"tier": tier, "time_limit_ms": 0, "mode": mode, "kind": kind, "rule": rule}
            return prompt, choices, ci, meta

        # miniLogic
        # "Se A=2, B=4, C=6... quanto é G?"
        letters = "ABCDEFGH"
        idx = rng.randint(3, 7)
        step = rng.choice([2, 3, 4])
        prompt = f"Se A={step}, B={2*step}, C={3*step}... quanto é {letters[idx-1]}?"
        ans = idx * step
        choices, ci = make_choices(ans, spread=step * 5, n=4, rng=rng)
        meta = {"tier": tier, "time_limit_ms": 0, "mode": mode, "kind": "miniLogic"}
        return prompt, choices, ci, meta

    if mode == "memoria":
        # "flash" 3 números por 1.2s, depois pergunta soma/maior/menor
        kind = rng.choice(["sum3", "max3", "min3"])
        nums = [rng.randint(1, base) for _ in range(3)]
        if kind == "sum3":
            prompt = f"MEMÓRIA: memorize → {nums[0]}  {nums[1]}  {nums[2]} | Pergunta: qual é a SOMA?"
            ans = sum(nums)
            choices, ci = make_choices(ans, spread=base, n=4, rng=rng)
        elif kind == "max3":
            prompt = f"MEMÓRIA: memorize → {nums[0]}  {nums[1]}  {nums[2]} | Pergunta: qual é o MAIOR?"
            ans = max(nums)
            choices = nums[:]  # usa os próprios nums como escolhas
            rng.shuffle(choices)
            ci = choices.index(ans)
        else:
            prompt = f"MEMÓRIA: memorize → {nums[0]}  {nums[1]}  {nums[2]} | Pergunta: qual é o MENOR?"
            ans = min(nums)
            choices = nums[:]
            rng.shuffle(choices)
            ci = choices.index(ans)

        meta = {"tier": tier, "time_limit_ms": 0, "mode": mode, "kind": kind, "flash": nums}
        return prompt, choices, ci, meta

    # modos numéricos (speed / armadilha / default)
    op = rng.choice(ops)

    if op == "add":
        a = rng.randint(1, base)
        b = rng.randint(1, base)
        ans = a + b
        prompt = f"{a} + {b} = ?"
        choices, ci = make_choices(ans, spread=max(6, base // 5), n=4, rng=rng)

    elif op == "sub":
        a = rng.randint(1, base)
        b = rng.randint(1, base)
        if b > a:
            a, b = b, a
        ans = a - b
        prompt = f"{a} − {b} = ?"
        choices, ci = make_choices(ans, spread=max(6, base // 5), n=4, rng=rng)

    elif op == "mul":
        a = rng.randint(2, 6 + tier * 2)
        b = rng.randint(2, 6 + tier * 2)
        ans = a * b
        prompt = f"{a} × {b} = ?"
        choices, ci = make_choices(ans, spread=max(8, tier * 6), n=4, rng=rng)

    elif op == "div":
        b = rng.randint(2, 6 + tier * 2)
        ans = rng.randint(2, 8 + tier * 2)
        a = b * ans
        prompt = f"{a} ÷ {b} = ?"
        choices, ci = make_choices(ans, spread=max(6, tier * 4), n=4, rng=rng)

    elif op == "pct":
        p = rng.choice([5, 10, 12, 15, 20, 25, 30, 40, 50])
        n = rng.randint(10, base * 2)
        # arredonda pra ficar inteiro em muitos casos
        if rng.random() < 0.6:
            n = n - (n % 10)
        ans = int(round(n * (p / 100)))
        prompt = f"{p}% de {n} = ?"
        choices, ci = make_choices(ans, spread=max(10, base // 3), n=4, rng=rng)

    elif op == "pow":
        a = rng.randint(2, 4 + (tier // 2))
        b = rng.choice([2, 3])
        ans = a ** b
        prompt = f"{a}^{b} = ?"
        choices, ci = make_choices(ans, spread=max(10, ans // 5), n=4, rng=rng)

    else:  # mix
        a = rng.randint(2, 12 + tier * 2)
        b = rng.randint(2, 12 + tier * 2)
        c = rng.randint(1, 10 + tier)
        ans = a * b + c
        prompt = f"{a}×{b} + {c} = ?"
        choices, ci = make_choices(ans, spread=max(10, tier * 10), n=4, rng=rng)

    # Armadilha: distrator “pegadinha” proposital (prioridade)
    if mode == "armadilha":
        # tenta colocar opções muito próximas (erro comum)
        if "×" in prompt:
            # distrações por troca de fator
            alt1 = (a * b) + (1 if rng.random() < 0.5 else -1)
            alt2 = (a * (b + 1))
            alt3 = (a + b)
            candidates = [ans, alt1, alt2, alt3]
            candidates = [int(x) for x in candidates]
            candidates = list(dict.fromkeys(candidates))  # unique mantendo ordem
            while len(candidates) < 4:
                candidates.append(ans + rng.randint(-10, 10))
            candidates = candidates[:4]
            rng.shuffle(candidates)
            choices = candidates
            ci = choices.index(ans)
        else:
            # soma/sub: confundir sinal
            try:
                if " + " in prompt:
                    alt = a - b
                else:
                    alt = a + b
                candidates = [ans, alt, ans + 1, ans - 1]
                candidates = list(dict.fromkeys(candidates))
                while len(candidates) < 4:
                    candidates.append(ans + rng.randint(-7, 7))
                candidates = candidates[:4]
                rng.shuffle(candidates)
                choices = candidates
                ci = choices.index(ans)
            except Exception:
                pass

    meta = {"tier": tier, "time_limit_ms": time_limit_ms, "mode": mode, "kind": op}
    return prompt, choices, ci, meta


def score_delta(correct: bool, mode: str, tier: int, elapsed_ms: int, combo: int, streak: int):
    """
    Pontuação:
    - base por tier
    - speed: bônus por tempo
    - combo/streak: multiplicador
    - erro: penalidade e quebra combo
    """
    base = 10 + tier * 6

    if not correct:
        # penalidade leve, cresce com tier
        return -max(6, 5 + tier * 2)

    bonus_time = 0
    if mode == "speed":
        # quanto menor o tempo, mais bônus
        # (elapsed_ms já vem do cliente)
        t = clamp(elapsed_ms, 200, 8000)
        bonus_time = int(max(0, (3500 - t) / 200)) * 3  # 0..~45

    # combo multiplica
    mult = 1.0 + min(combo, 10) * 0.08 + min(streak, 20) * 0.03
    return int((base + bonus_time) * mult)


# -----------------------------
# Frontend (HTML+CSS+JS)
# -----------------------------
HTML = r"""
<!doctype html>
<html lang="pt-br">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"/>
  <title>Jogo Matemática — Turbo Edition</title>

  <link rel="manifest" href="/manifest.webmanifest">
  <meta name="theme-color" content="#0b1220"/>
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">

  <style>
    :root{
      --bg:#0b1220;
      --card:rgba(255,255,255,.06);
      --card2:rgba(255,255,255,.09);
      --txt:#eaf0ff;
      --muted:rgba(234,240,255,.6);
      --accent:#7c5cff;
      --good:#37d67a;
      --bad:#ff4d6d;
      --warn:#ffcc00;
      --shadow: 0 20px 60px rgba(0,0,0,.45);
      --radius: 18px;
    }
    *{box-sizing:border-box}
    body{
      margin:0;
      font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial;
      background: radial-gradient(1200px 600px at 20% -20%, rgba(124,92,255,.35), transparent 55%),
                  radial-gradient(900px 500px at 90% 10%, rgba(55,214,122,.25), transparent 55%),
                  var(--bg);
      color:var(--txt);
      min-height:100vh;
      padding: 14px 14px 90px;
    }
    .wrap{max-width: 760px; margin: 0 auto;}
    .title{
      display:flex;align-items:center;gap:10px;
      font-weight:800;font-size: 28px; letter-spacing:.2px;
      margin: 6px 0 12px;
    }
    .pillRow{display:flex; gap:10px; flex-wrap:wrap; margin: 10px 0 14px;}
    .pill{
      background: var(--card);
      border:1px solid rgba(255,255,255,.08);
      padding: 10px 12px;
      border-radius: 999px;
      color: var(--muted);
      display:flex; gap:8px; align-items:center;
      backdrop-filter: blur(10px);
    }
    .grid{display:grid; gap:12px;}
    .card{
      background: linear-gradient(180deg, rgba(255,255,255,.07), rgba(255,255,255,.05));
      border:1px solid rgba(255,255,255,.10);
      border-radius: var(--radius);
      padding: 14px;
      box-shadow: var(--shadow);
      backdrop-filter: blur(12px);
    }
    .topStats{
      display:grid; grid-template-columns: 1fr 1fr 1fr;
      gap:10px;
    }
    .stat{
      background: var(--card);
      border:1px solid rgba(255,255,255,.08);
      border-radius: 16px;
      padding: 12px;
      display:flex; flex-direction:column; gap:6px;
      min-height:72px;
    }
    .stat .k{font-size:12px; color: var(--muted)}
    .stat .v{font-size:18px; font-weight:800}
    .row{display:flex; gap:10px; flex-wrap:wrap; align-items:center;}
    .btn{
      border:0;
      background: rgba(255,255,255,.09);
      color: var(--txt);
      border:1px solid rgba(255,255,255,.12);
      padding: 12px 14px;
      border-radius: 14px;
      cursor:pointer;
      font-weight:700;
      transition: transform .08s ease, background .15s ease;
      user-select:none;
    }
    .btn:active{transform: scale(.98)}
    .btn.primary{
      background: linear-gradient(135deg, rgba(124,92,255,.95), rgba(99,72,255,.65));
      border-color: rgba(124,92,255,.8);
    }
    .btn.ghost{
      background: transparent;
      border-color: rgba(255,255,255,.14);
    }
    .btn.small{padding:8px 10px; border-radius: 12px; font-size: 13px}
    .question{
      font-size: 42px;
      font-weight: 900;
      margin: 10px 0 6px;
      letter-spacing:.3px;
    }
    .sub{
      color:var(--muted);
      font-weight:600;
      margin: 6px 0 10px;
    }
    .bar{
      height:10px;
      background: rgba(255,255,255,.08);
      border:1px solid rgba(255,255,255,.12);
      border-radius: 999px;
      overflow:hidden;
      margin: 10px 0 12px;
    }
    .bar>div{
      height:100%;
      width: 0%;
      background: linear-gradient(90deg, var(--good), var(--warn), var(--bad));
      transition: width .12s linear;
    }
    .choices{
      display:grid; grid-template-columns: 1fr; gap: 10px;
    }
    .choice{
      width:100%;
      text-align:center;
      font-size: 22px;
      font-weight:900;
      padding: 16px 14px;
      border-radius: 16px;
      background: rgba(255,255,255,.06);
      border:1px solid rgba(255,255,255,.12);
      cursor:pointer;
      transition: transform .08s ease, background .12s ease, border-color .12s ease;
    }
    .choice:active{transform: scale(.98)}
    .choice.good{border-color: rgba(55,214,122,.85); background: rgba(55,214,122,.14)}
    .choice.bad{border-color: rgba(255,77,109,.85); background: rgba(255,77,109,.12)}
    .toast{
      margin-top: 10px;
      font-weight: 900;
      font-size: 18px;
      min-height: 22px;
    }
    .toast.good{color: var(--good)}
    .toast.bad{color: var(--bad)}
    .modes{
      display:grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 10px;
      margin-top: 14px;
    }
    .modeBtn{
      padding: 14px;
      border-radius: 16px;
      border:1px solid rgba(255,255,255,.12);
      background: rgba(255,255,255,.06);
      cursor:pointer;
      font-weight:900;
      display:flex; align-items:center; justify-content:space-between;
      gap:12px;
      user-select:none;
    }
    .modeBtn.active{
      border-color: rgba(124,92,255,.9);
      background: rgba(124,92,255,.18);
    }
    .modeBtn .hint{font-size:12px; color:var(--muted); font-weight:700}
    .bottomDock{
      position: fixed;
      left:0; right:0; bottom:0;
      padding: 12px 14px 18px;
      background: linear-gradient(180deg, transparent, rgba(11,18,32,.88) 22%, rgba(11,18,32,.98));
      backdrop-filter: blur(10px);
    }
    .dockInner{max-width:760px; margin:0 auto; display:flex; gap:10px; justify-content:space-between; align-items:center;}
    .tag{
      font-size:12px; color:var(--muted); font-weight:700;
      background: rgba(255,255,255,.06);
      border:1px solid rgba(255,255,255,.10);
      padding:8px 10px;
      border-radius:999px;
      display:flex; gap:8px; align-items:center;
    }

    /* Overlay (start screen) */
    .overlay{
      position: fixed; inset:0;
      background: rgba(0,0,0,.55);
      display:none;
      align-items:center;
      justify-content:center;
      padding: 18px;
      z-index: 50;
    }
    .overlay.show{display:flex;}
    .modal{
      width: 100%;
      max-width: 620px;
      background: linear-gradient(180deg, rgba(255,255,255,.10), rgba(255,255,255,.06));
      border:1px solid rgba(255,255,255,.14);
      border-radius: 22px;
      box-shadow: var(--shadow);
      padding: 16px;
      backdrop-filter: blur(14px);
    }
    .modal h2{margin: 6px 0 10px; font-size: 22px}
    .input{
      width:100%;
      padding: 14px 12px;
      border-radius: 16px;
      border:1px solid rgba(255,255,255,.14);
      background: rgba(0,0,0,.18);
      color: var(--txt);
      font-weight: 800;
      font-size: 16px;
      outline: none;
    }
    .hintLine{color: var(--muted); font-weight:700; font-size: 13px; margin-top: 8px;}
    .leader{
      margin-top: 14px;
      padding-top: 10px;
      border-top: 1px solid rgba(255,255,255,.10);
    }
    .leader ol{margin: 10px 0 0 18px; color:var(--muted); font-weight:800}
    .leader li{margin: 6px 0}
    @media (max-width:520px){
      .topStats{grid-template-columns: 1fr 1fr; }
      .question{font-size: 36px;}
      .modes{grid-template-columns: 1fr;}
    }
  </style>
</head>

<body>
  <div class="wrap">
    <div class="title">🧠 Jogo Matemática — Turbo Edition</div>

    <div class="pillRow">
      <div class="pill">🎮 <span id="uiMode">Modo: —</span></div>
      <div class="pill">🧩 <span id="uiLevel">Nível: 1</span></div>
      <div class="pill">🧪 <span id="uiTier">Tier: 1</span></div>
      <div class="pill">🤖 <span id="uiSkill">Adaptive: 0.50</span></div>
    </div>

    <div class="card">
      <div class="topStats">
        <div class="stat">
          <div class="k">👤 Jogador</div>
          <div class="v" id="uiName">—</div>
        </div>
        <div class="stat">
          <div class="k">🏆 Pontos</div>
          <div class="v" id="uiScore">0</div>
        </div>
        <div class="stat">
          <div class="k">⚡ Combo</div>
          <div class="v" id="uiCombo">0</div>
        </div>
        <div class="stat">
          <div class="k">🔥 Streak</div>
          <div class="v" id="uiStreak">0</div>
        </div>
        <div class="stat">
          <div class="k">✅ Acertos</div>
          <div class="v" id="uiHits">0</div>
        </div>
        <div class="stat">
          <div class="k">❌ Erros</div>
          <div class="v" id="uiMiss">0</div>
        </div>
      </div>

      <div style="height:12px"></div>

      <div class="row">
        <button class="btn ghost" id="btnStart">Trocar jogador / modo</button>
        <button class="btn primary" id="btnNext">Próxima</button>
        <span class="tag" id="uiTip">✨ Escolha um modo e comece.</span>
      </div>

      <div style="height:12px"></div>

      <div class="sub" id="uiLine">Modo: — | Nível: 1 | Tier: 1</div>
      <div class="question" id="uiQuestion">—</div>

      <div class="sub" id="uiSub">💡 Dica: velocidade dá bônus no modo Speed.</div>

      <div class="bar" id="timeBarWrap" style="display:none">
        <div id="timeBar"></div>
      </div>

      <div class="choices" id="uiChoices"></div>
      <div class="toast" id="uiToast"></div>
    </div>
  </div>

  <div class="bottomDock">
    <div class="dockInner">
      <div class="tag">📱 iPhone: abra no Safari → Compartilhar → “Adicionar à Tela de Início”</div>
      <button class="btn small" id="btnLeaderboard">🏅 Ranking</button>
    </div>
  </div>

  <!-- Start overlay -->
  <div class="overlay" id="overlay">
    <div class="modal">
      <h2>🚀 Começar</h2>
      <input class="input" id="nameInput" placeholder="Seu nome (ex: Bruno)"/>
      <div class="hintLine">Escolha um modo (cada modo muda o “tipo de cérebro” que você usa).</div>

      <div class="modes" id="modeGrid"></div>

      <div style="height:12px"></div>
      <div class="row" style="justify-content:space-between">
        <button class="btn ghost" id="btnClose">Fechar</button>
        <button class="btn primary" id="btnPlay">Jogar</button>
      </div>

      <div class="leader" id="leaderBox" style="display:none">
        <div class="hintLine">🏅 Top 10 (melhores pontuações)</div>
        <ol id="leaderList"></ol>
      </div>
    </div>
  </div>

<script>
  // -----------------------------
  // PWA (service worker)
  // -----------------------------
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js').catch(()=>{});
  }

  // -----------------------------
  // State (NUNCA undefined)
  // -----------------------------
  const state = {
    playerId: localStorage.getItem('playerId') || crypto.randomUUID(),
    name: localStorage.getItem('playerName') || '',
    mode: localStorage.getItem('playerMode') || 'speed',
    level: Number(localStorage.getItem('playerLevel') || 1),
    tier: 1,
    skill: Number(localStorage.getItem('playerSkill') || 0.50),
    score: Number(localStorage.getItem('playerScore') || 0),
    combo: Number(localStorage.getItem('playerCombo') || 0),
    streak: Number(localStorage.getItem('playerStreak') || 0),
    hits: Number(localStorage.getItem('playerHits') || 0),
    miss: Number(localStorage.getItem('playerMiss') || 0),
    lastQ: null,
    lastStartMs: 0
  };
  localStorage.setItem('playerId', state.playerId);

  const MODES = [
    {id:'speed', icon:'⚡', name:'Speed', hint:'tempo dá bônus'},
    {id:'logica', icon:'🧩', name:'Lógica', hint:'sequências & intruso'},
    {id:'armadilha', icon:'🪤', name:'Armadilha', hint:'pegadinhas'},
    {id:'memoria', icon:'🧠', name:'Memória', hint:'memorize rápido'},
  ];

  // -----------------------------
  // UI refs
  // -----------------------------
  const ui = {
    overlay: document.getElementById('overlay'),
    modeGrid: document.getElementById('modeGrid'),
    nameInput: document.getElementById('nameInput'),
    btnStart: document.getElementById('btnStart'),
    btnNext: document.getElementById('btnNext'),
    btnClose: document.getElementById('btnClose'),
    btnPlay: document.getElementById('btnPlay'),
    btnLeaderboard: document.getElementById('btnLeaderboard'),

    uiMode: document.getElementById('uiMode'),
    uiLevel: document.getElementById('uiLevel'),
    uiTier: document.getElementById('uiTier'),
    uiSkill: document.getElementById('uiSkill'),
    uiName: document.getElementById('uiName'),
    uiScore: document.getElementById('uiScore'),
    uiCombo: document.getElementById('uiCombo'),
    uiStreak: document.getElementById('uiStreak'),
    uiHits: document.getElementById('uiHits'),
    uiMiss: document.getElementById('uiMiss'),
    uiLine: document.getElementById('uiLine'),
    uiQuestion: document.getElementById('uiQuestion'),
    uiSub: document.getElementById('uiSub'),
    uiChoices: document.getElementById('uiChoices'),
    uiToast: document.getElementById('uiToast'),
    uiTip: document.getElementById('uiTip'),

    timeBarWrap: document.getElementById('timeBarWrap'),
    timeBar: document.getElementById('timeBar'),

    leaderBox: document.getElementById('leaderBox'),
    leaderList: document.getElementById('leaderList'),
  };

  function saveState() {
    localStorage.setItem('playerName', state.name);
    localStorage.setItem('playerMode', state.mode);
    localStorage.setItem('playerLevel', String(state.level));
    localStorage.setItem('playerSkill', String(state.skill.toFixed(4)));
    localStorage.setItem('playerScore', String(state.score));
    localStorage.setItem('playerCombo', String(state.combo));
    localStorage.setItem('playerStreak', String(state.streak));
    localStorage.setItem('playerHits', String(state.hits));
    localStorage.setItem('playerMiss', String(state.miss));
  }

  function modeLabel(id){
    const m = MODES.find(x=>x.id===id);
    return m ? `${m.icon} ${m.name}` : id;
  }

  function tipForMode(id){
    if (id==='speed') return '⚡ Responda rápido para bônus.';
    if (id==='logica') return '🧩 Padrões e “intruso” ficam mais difíceis com o nível.';
    if (id==='armadilha') return '🪤 Cuidado: opções parecem certas. Leia com calma.';
    if (id==='memoria') return '🧠 Memorize rápido e responda sem vacilar.';
    return '✨ Jogue e melhore.';
  }

  function renderModeGrid() {
    ui.modeGrid.innerHTML = '';
    MODES.forEach(m=>{
      const b = document.createElement('div');
      b.className = 'modeBtn' + (state.mode===m.id ? ' active' : '');
      b.innerHTML = `<div><div style="font-size:16px">${m.icon} ${m.name}</div><div class="hint">${m.hint}</div></div>
                     <div style="opacity:.7">▶</div>`;
      b.onclick = ()=>{
        state.mode = m.id;
        localStorage.setItem('playerMode', state.mode);
        renderModeGrid();
      };
      ui.modeGrid.appendChild(b);
    });
  }

  function showOverlay(show, withLeaderboard=false){
    ui.overlay.classList.toggle('show', show);
    ui.nameInput.value = state.name || '';
    renderModeGrid();
    if (withLeaderboard) loadLeaderboard();
    ui.leaderBox.style.display = withLeaderboard ? 'block' : 'none';
  }

  async function loadLeaderboard(){
    try{
      const r = await fetch('/api/leaderboard');
      const data = await r.json();
      ui.leaderList.innerHTML = '';
      data.top.forEach((x)=>{
        const li = document.createElement('li');
        li.textContent = `${x.name} — ${x.score} pts`;
        ui.leaderList.appendChild(li);
      });
    }catch(e){
      ui.leaderList.innerHTML = '<li>Sem dados</li>';
    }
  }

  function paintUI(){
    ui.uiMode.textContent = `Modo: ${modeLabel(state.mode)}`;
    ui.uiLevel.textContent = `Nível: ${state.level}`;
    ui.uiTier.textContent = `Tier: ${state.tier}`;
    ui.uiSkill.textContent = `Adaptive: ${state.skill.toFixed(2)}`;

    ui.uiName.textContent = state.name ? state.name : '—';
    ui.uiScore.textContent = String(state.score);
    ui.uiCombo.textContent = String(state.combo);
    ui.uiStreak.textContent = String(state.streak);
    ui.uiHits.textContent = String(state.hits);
    ui.uiMiss.textContent = String(state.miss);

    ui.uiLine.textContent = `Modo: ${state.mode} | Nível: ${state.level} | Tier: ${state.tier}`;
    ui.uiTip.textContent = tipForMode(state.mode);
  }

  function toast(msg, kind=''){
    ui.uiToast.textContent = msg || '';
    ui.uiToast.className = 'toast ' + (kind||'');
  }

  function renderChoices(q){
    ui.uiChoices.innerHTML = '';
    q.choices.forEach((c, idx)=>{
      const btn = document.createElement('button');
      btn.className = 'choice';
      btn.textContent = String(c);
      btn.onclick = ()=> submitAnswer(idx);
      ui.uiChoices.appendChild(btn);
    });
  }

  // Timer bar (speed)
  let timerTick = null;
  function startTimer(ms){
    if (!ms || ms<=0){
      ui.timeBarWrap.style.display = 'none';
      if (timerTick) clearInterval(timerTick);
      timerTick = null;
      return;
    }
    ui.timeBarWrap.style.display = 'block';
    const start = performance.now();
    if (timerTick) clearInterval(timerTick);
    timerTick = setInterval(()=>{
      const t = performance.now()-start;
      const pct = clamp((t/ms)*100, 0, 100);
      ui.timeBar.style.width = pct + '%';
      if (t>=ms){
        clearInterval(timerTick);
        timerTick = null;
        // auto-erro se estourar tempo
        toast('⏳ Tempo esgotado! (-combo)', 'bad');
        submitAnswer(-1, true); // timeout
      }
    }, 50);
  }

  async function getQuestion(){
    paintUI();
    toast('');
    ui.btnNext.disabled = true;

    const payload = {
      mode: state.mode,
      level: state.level,
      skill: state.skill,
      combo: state.combo,
      streak: state.streak
    };

    const res = await fetch('/api/question', {
      method:'POST',
      headers:{
        'Content-Type':'application/json',
        'X-Player-Id': state.playerId,
        'X-Player-Name': state.name || ''
      },
      body: JSON.stringify(payload)
    });
    const q = await res.json();

    state.lastQ = q;
    state.tier = q.meta.tier || state.tier;
    state.lastStartMs = performance.now();

    ui.uiQuestion.textContent = q.prompt;
    ui.uiSub.textContent = q.hint || tipForMode(state.mode);
    renderChoices(q);
    startTimer(q.meta.time_limit_ms || 0);

    paintUI();
    ui.btnNext.disabled = false;
  }

  async function submitAnswer(answerIndex, isTimeout=false){
    if (!state.lastQ) return;

    // trava botões
    const btns = ui.uiChoices.querySelectorAll('button.choice');
    btns.forEach(b=>b.disabled=true);

    const elapsed = Math.max(0, Math.round(performance.now() - state.lastStartMs));
    const payload = {
      qid: state.lastQ.qid,
      answer_index: answerIndex,
      elapsed_ms: elapsed,
      timeout: isTimeout
    };

    const res = await fetch('/api/answer', {
      method:'POST',
      headers:{
        'Content-Type':'application/json',
        'X-Player-Id': state.playerId,
        'X-Player-Name': state.name || ''
      },
      body: JSON.stringify(payload)
    });
    const out = await res.json();

    // pintar escolhas
    btns.forEach((b, i)=>{
      if (i === out.correct_index) b.classList.add('good');
      if (answerIndex === i && !out.correct) b.classList.add('bad');
    });

    // aplicar state
    state.score = out.state.score;
    state.combo = out.state.combo;
    state.streak = out.state.streak;
    state.level = out.state.level;
    state.skill = out.state.skill;
    state.hits = out.state.hits;
    state.miss = out.state.miss;

    saveState();
    paintUI();

    if (out.correct){
      toast(`${out.msg}  (+${out.delta} pts)`, 'good');
    } else {
      toast(`${out.msg}  (${out.delta} pts)`, 'bad');
    }

    // depois de um tempinho, já busca a próxima (fica viciante)
    setTimeout(()=> getQuestion().catch(()=>{}), out.correct ? 650 : 900);
  }

  function ensureStart(){
    // força tela inicial se não tem nome
    if (!state.name || state.name.trim().length < 2){
      showOverlay(true, true);
    } else {
      paintUI();
      getQuestion().catch(()=>{});
    }
  }

  // -----------------------------
  // Events
  // -----------------------------
  ui.btnStart.onclick = ()=> showOverlay(true, true);
  ui.btnClose.onclick = ()=> showOverlay(false, false);
  ui.btnLeaderboard.onclick = ()=> showOverlay(true, true);

  ui.btnPlay.onclick = ()=>{
    const nm = (ui.nameInput.value || '').trim();
    state.name = nm.length ? nm : 'Jogador';
    localStorage.setItem('playerName', state.name);
    saveState();
    showOverlay(false, false);
    getQuestion().catch(()=>{});
  };

  ui.btnNext.onclick = ()=> getQuestion().catch(()=>{});

  // init
  ensureStart();
</script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def index():
    return HTMLResponse(HTML)


@app.get("/manifest.webmanifest")
def manifest():
    # PWA básico (instalável)
    data = {
        "name": "Jogo Matemática — Turbo",
        "short_name": "Math Turbo",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#0b1220",
        "theme_color": "#0b1220",
        "icons": [
            {
                "src": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEAAAAAQCAYAAABAfUpWAAAACXBIWXMAAAsSAAALEgHS3X78AAAAtklEQVR4nO2WwQ3CMAxF5xgkQmQwA3QwA3QwA3QwA3QwA7S9JYcJr4c0lqg8n7oQbq8c8dQm3kqk8lJ0q0k7bQh5o9n4kqCkJp4oWm4c9m9bqkqg7hQwQmB4Qqf0Qqk0oQ+QF4Ew0A8m1yQxHhQv0m2b8b9p8Hn9vQxg0Qp9m3w6gXv3gYwqjGkVb7sZ3m5YgAAAABJRU5ErkJggg==",
                "sizes": "64x64",
                "type": "image/png"
            }
        ]
    }
    return JSONResponse(data)


@app.get("/sw.js")
def sw():
    # Service worker simples (cache do HTML e assets)
    js = """
self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open('math-turbo-v1').then((cache) => cache.addAll(['/','/manifest.webmanifest']))
  );
});
self.addEventListener('fetch', (e) => {
  e.respondWith(
    caches.match(e.request).then((r) => r || fetch(e.request))
  );
});
"""
    return HTMLResponse(js, media_type="application/javascript")


@app.post("/api/question")
async def api_question(request: Request):
    body = await request.json()
    mode = (body.get("mode") or "speed").strip()
    level = int(body.get("level") or 1)
    skill = float(body.get("skill") or 0.5)

    player_id = request.headers.get("X-Player-Id", "anon")
    player_name = request.headers.get("X-Player-Name", "")

    RECENT[player_id] = now_iso()

    # seed mistura player+tempo pra não repetir sempre igual
    seed = f"{player_id}|{mode}|{level}|{round(skill,3)}|{uuid.uuid4().hex[:6]}"
    rng = seeded_rng(seed)

    prompt, choices, correct_index, meta = gen_question(mode, level, skill, rng)

    # hints curtas por modo
    hint_map = {
        "speed": "⚡ Velocidade dá bônus. Erro quebra combo.",
        "logica": "🧩 Procure padrão/regel. Nível alto = mais pegadinha.",
        "armadilha": "🪤 Leia com calma. Parece certo, mas não é.",
        "memoria": "🧠 Memorize os números e responda sem hesitar."
    }

    qid = uuid.uuid4().hex
    QUESTIONS[qid] = {
        "correct_index": int(correct_index),
        "meta": meta,
        "created": now_iso(),
        "mode": mode,
        "level": level
    }

    return JSONResponse({
        "qid": qid,
        "prompt": prompt,
        "choices": choices,
        "hint": hint_map.get(mode, "✨ Boa sorte."),
        "meta": meta
    })


@app.post("/api/answer")
async def api_answer(request: Request):
    body = await request.json()
    qid = body.get("qid")
    answer_index = body.get("answer_index", -1)
    elapsed_ms = int(body.get("elapsed_ms") or 0)
    timeout = bool(body.get("timeout") or False)

    player_id = request.headers.get("X-Player-Id", "anon")
    player_name = (request.headers.get("X-Player-Name") or "").strip() or "Jogador"

    q = QUESTIONS.get(qid)
    if not q:
        # questão expirou / não existe
        return JSONResponse({
            "correct": False,
            "correct_index": 0,
            "delta": 0,
            "msg": "⚠️ Questão inválida. Tenta de novo.",
            "state": {
                "score": 0, "combo": 0, "streak": 0, "level": 1, "skill": 0.5, "hits": 0, "miss": 0
            }
        })

    correct_index = int(q["correct_index"])
    correct = (answer_index == correct_index) and (not timeout)

    mode = q["meta"].get("mode", "speed")
    tier = int(q["meta"].get("tier", 1))

    # Estado vem do client? não confiamos; mantemos "leve" no client.
    # Aqui fazemos ajuste adaptativo e pontuação por retorno.
    # Como o client guarda score local, devolvemos deltas e "regras"
    # e o client aplica. Mas pra simplificar, devolvemos state completo
    # derivado de "best effort" lendo headers recentes.
    #
    # OBS: sem sessão real no backend, a fonte de verdade é o client.
    # Ainda assim dá pra dar "regras consistentes".

    # Recupera "estado" aproximado usando leaderboard como referência? não.
    # Melhor: o client envia score atual? (não estamos recebendo)
    # Então: retornamos delta, e client soma. MAS no JS acima já substitui pelo state.
    # Vamos então aceitar do client via headers opcionais no futuro. Por agora:
    # -> vamos manter "state server-side por player" (simples) num dict.
    if not hasattr(app.state, "PLAYER"):
        app.state.PLAYER = {}
    P = app.state.PLAYER

    if player_id not in P:
        P[player_id] = {
            "score": 0, "combo": 0, "streak": 0, "level": 1, "skill": 0.5,
            "hits": 0, "miss": 0, "name": player_name
        }

    st = P[player_id]
    st["name"] = player_name

    # pontuação
    delta = score_delta(correct, mode, tier, elapsed_ms, st["combo"], st["streak"])

    if correct:
        st["score"] += max(0, delta)
        st["combo"] += 1
        st["streak"] += 1
        st["hits"] += 1

        # progressão de nível: sobe a cada 3 acertos seguidos OU combo alto
        if (st["streak"] % 3 == 0) or (st["combo"] in [5, 8, 12]):
            st["level"] += 1

        # adaptativo: melhora skill com acerto, mais se foi rápido no speed
        bump = 0.02 + (0.02 if mode == "speed" and elapsed_ms < 2500 else 0.0)
        st["skill"] = clamp(st["skill"] + bump, 0.0, 1.0)

        msg_pool = [
            "✅ Boa!", "🔥 Perfeito!", "⚡ Rápido!", "🏆 Mandou bem!", "💎 Precisão!"
        ]
        msg = random.choice(msg_pool)

    else:
        st["score"] = max(0, st["score"] + delta)  # delta é negativo
        st["miss"] += 1
        st["combo"] = 0
        st["streak"] = 0

        # adaptativo: reduz skill um pouco no erro
        st["skill"] = clamp(st["skill"] - 0.03, 0.0, 1.0)

        msg = "❌ Errou! " + ("⏳ Tempo!" if timeout else "Tenta a próxima.")
        # desce nível só se estiver muito alto e errar repetido
        if st["level"] > 1 and st["miss"] % 5 == 0:
            st["level"] -= 1

    # leaderboard: guarda melhor score do nome
    best = LEADERBOARD.get(player_name, 0)
    if st["score"] > best:
        LEADERBOARD[player_name] = st["score"]

    return JSONResponse({
        "correct": correct,
        "correct_index": correct_index,
        "delta": int(delta),
        "msg": msg,
        "state": {
            "score": int(st["score"]),
            "combo": int(st["combo"]),
            "streak": int(st["streak"]),
            "level": int(st["level"]),
            "skill": float(round(st["skill"], 4)),
            "hits": int(st["hits"]),
            "miss": int(st["miss"])
        }
    })


@app.get("/api/leaderboard")
def api_leaderboard():
    top = sorted(
        [{"name": n, "score": s} for n, s in LEADERBOARD.items()],
        key=lambda x: x["score"],
        reverse=True
    )[:10]
    return JSONResponse({"top": top})


# Health check
@app.get("/health")
def health():
    return {"ok": True, "time": now_iso()}
