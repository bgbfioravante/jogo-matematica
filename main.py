from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
import random

app = FastAPI(title="Jogo de Matemática (Levels)")

# ----------------------------
# "Banco" simples na memória
# ----------------------------
# Para não repetir perguntas iguais, guardamos o histórico por "player_id"
SEEN = {}  # player_id -> set(pergunta_id)


def _mk_player(player_id: str):
    if player_id not in SEEN:
        SEEN[player_id] = set()


def gerar_pergunta(level: int, player_id: str):
    """
    Gera uma pergunta diferente, com 3 alternativas (A/B/C).
    Dificuldade cresce com o level.
    """
    _mk_player(player_id)

    # Aumenta faixa de números com o level
    faixa = min(10 + level * 2, 300)

    # Escolhe tipo de conta por level
    # níveis baixos: + e -
    # intermediário: adiciona *
    # altos: mistura e aumenta números
    ops = ["+", "-"] if level <= 20 else ["+", "-", "*"]

    while True:
        op = random.choice(ops)
        a = random.randint(1, faixa)
        b = random.randint(1, faixa)

        if op == "+":
            ans = a + b
            texto = f"{a} + {b} = ?"
        elif op == "-":
            # evita resultado negativo nos níveis baixos
            if level <= 30 and b > a:
                a, b = b, a
            ans = a - b
            texto = f"{a} - {b} = ?"
        else:
            # multiplica com números menores p/ não explodir
            a = random.randint(2, max(3, faixa // 10))
            b = random.randint(2, max(3, faixa // 10))
            ans = a * b
            texto = f"{a} × {b} = ?"

        # cria id da pergunta para evitar repetição
        pid = f"{level}|{texto}|{ans}"
        if pid not in SEEN[player_id]:
            SEEN[player_id].add(pid)
            break

    # gera 2 alternativas erradas
    err1 = ans + random.randint(1, max(3, faixa // 5))
    err2 = ans - random.randint(1, max(3, faixa // 5))
    if err2 == ans:
        err2 -= 2
    if err1 == ans:
        err1 += 2

    # embaralha alternativas
    opcoes = [ans, err1, err2]
    random.shuffle(opcoes)

    letras = ["A", "B", "C"]
    alternativas = {letras[i]: opcoes[i] for i in range(3)}
    correta = letras[opcoes.index(ans)]

    return {
        "id": pid,
        "pergunta": texto,
        "alternativas": alternativas,
        "correta": correta,
    }


# --------------------------------
# Endpoints de API (JSON)
# --------------------------------
@app.get("/api/pergunta")
def api_pergunta(level: int = 1, player_id: str = "bruno"):
    level = max(1, min(100, level))
    return JSONResponse(gerar_pergunta(level, player_id))


@app.post("/api/responder")
def api_responder(payload: dict):
    """
    payload esperado:
    {
      "player_id": "bruno",
      "level": 10,
      "pergunta_id": "...",
      "resposta": "A" | "B" | "C",
      "correta": "A" | "B" | "C"
    }
    """
    player_id = payload.get("player_id", "bruno")
    level = int(payload.get("level", 1))
    resposta = (payload.get("resposta") or "").strip().upper()
    correta = (payload.get("correta") or "").strip().upper()

    level = max(1, min(100, level))

    acertou = (resposta == correta)

    if acertou:
        novo_level = min(100, level + 1)
    else:
        novo_level = max(1, level - 10)

    return JSONResponse({
        "acertou": acertou,
        "level_anterior": level,
        "novo_level": novo_level
    })


# --------------------------------
# App (HTML) - abre no navegador
# --------------------------------
@app.get("/", response_class=HTMLResponse)
def home():
    return HTMLResponse(f"""
<!doctype html>
<html lang="pt-br">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Jogo de Matemática (Levels)</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; }}
    .box {{ max-width: 680px; margin: 0 auto; }}
    .row {{ display:flex; gap:12px; flex-wrap:wrap; align-items:center; }}
    .card {{ border:1px solid #ddd; border-radius:12px; padding:16px; margin-top:16px; }}
    button {{ padding:12px 14px; border-radius:10px; border:1px solid #ccc; cursor:pointer; background:#fff; }}
    button:hover {{ background:#f5f5f5; }}
    .opt {{ min-width: 140px; }}
    .big {{ font-size: 22px; font-weight: 700; }}
    .muted {{ color:#666; }}
    .good {{ color: #0a7a2f; font-weight:700; }}
    .bad {{ color: #b00020; font-weight:700; }}
    .pill {{ padding:6px 10px; border-radius:999px; background:#eee; }}
  </style>
</head>
<body>
  <div class="box">
    <div class="row">
      <div class="big">🎯 Jogo de Matemática (100 níveis)</div>
      <div class="pill" id="levelPill">Level: 1</div>
    </div>
    <div class="muted">Acertou ✅ sobe 1 level. Errou ❌ volta 10 levels. Perguntas sempre diferentes.</div>

    <div class="card">
      <div class="row">
        <label class="muted">Player ID:</label>
        <input id="playerId" value="bruno" style="padding:10px;border:1px solid #ccc;border-radius:10px;" />
        <button onclick="resetar()">Reset</button>
        <button onclick="novaPergunta()">Nova pergunta</button>
      </div>

      <h2 id="pergunta">Carregando...</h2>

      <div class="row" id="opcoes"></div>

      <div id="resultado" style="margin-top:14px;"></div>
    </div>

    <div class="muted" style="margin-top:18px;">
      Dica: salve esta página na tela inicial do iPhone (Compartilhar → Adicionar à Tela de Início).
    </div>
  </div>

<script>
let level = 1;
let perguntaAtual = null;

function setLevel(n) {{
  level = Math.max(1, Math.min(100, n));
  document.getElementById("levelPill").innerText = "Level: " + level;
}}

function getPlayerId() {{
  return document.getElementById("playerId").value.trim() || "bruno";
}}

async function novaPergunta() {{
  const player_id = getPlayerId();
  document.getElementById("resultado").innerHTML = "";
  document.getElementById("pergunta").innerText = "Carregando...";
  document.getElementById("opcoes").innerHTML = "";

  const resp = await fetch(`/api/pergunta?level=${{level}}&player_id=${{encodeURIComponent(player_id)}}`);
  perguntaAtual = await resp.json();

  document.getElementById("pergunta").innerText = perguntaAtual.pergunta;

  const opcoesDiv = document.getElementById("opcoes");
  const alts = perguntaAtual.alternativas;

  for (const letra of ["A","B","C"]) {{
    const btn = document.createElement("button");
    btn.className = "opt";
    btn.innerText = `${{letra}}) ${{alts[letra]}}`;
    btn.onclick = () => responder(letra);
    opcoesDiv.appendChild(btn);
  }}
}}

async function responder(letra) {{
  if (!perguntaAtual) return;

  const payload = {{
    player_id: getPlayerId(),
    level: level,
    pergunta_id: perguntaAtual.id,
    resposta: letra,
    correta: perguntaAtual.correta
  }};

  const resp = await fetch("/api/responder", {{
    method: "POST",
    headers: {{ "Content-Type": "application/json" }},
    body: JSON.stringify(payload)
  }});
  const res = await resp.json();

  if (res.acertou) {{
    document.getElementById("resultado").innerHTML =
      `<div class="good">✅ Acertou! Você subiu para o level ${{res.novo_level}}.</div>`;
  }} else {{
    document.getElementById("resultado").innerHTML =
      `<div class="bad">❌ Errou! Você voltou para o level ${{res.novo_level}}.</div>
       <div class="muted">A correta era: <b>${{perguntaAtual.correta}}</b></div>`;
  }}

  setLevel(res.novo_level);

  // sempre troca a pergunta
  setTimeout(novaPergunta, 400);
}}

function resetar() {{
  setLevel(1);
  novaPergunta();
}}

novaPergunta();
</script>
</body>
</html>
""")


# Render usa a variável PORT; localmente pode rodar com uvicorn também
if __name__ == "__main__":
    import os
    import uvicorn
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
