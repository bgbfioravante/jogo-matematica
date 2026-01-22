from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
import random

app = FastAPI(title="Jogo Matemática")

# -------------------------
# LÓGICA DO JOGO
# -------------------------

def gerar_pergunta(nivel: int):
    max_num = 10 + nivel * 5

    operacoes = ["+", "-"]
    if nivel >= 3:
        operacoes.append("*")
    if nivel >= 5:
        operacoes.append("/")

    op = random.choice(operacoes)
    a = random.randint(1, max_num)
    b = random.randint(1, max_num)

    if op == "/":
        a = a * b

    expressao = f"{a} {op} {b}"
    resposta = round(eval(expressao), 2)

    alternativas = {resposta}
    while len(alternativas) < 4:
        alternativas.add(resposta + random.randint(-10, 10))

    alternativas = list(alternativas)
    random.shuffle(alternativas)

    return {
        "pergunta": expressao,
        "resposta": resposta,
        "alternativas": alternativas
    }

# -------------------------
# API
# -------------------------

@app.get("/api/pergunta")
def pergunta(nivel: int = 1):
    return JSONResponse(gerar_pergunta(nivel))


# -------------------------
# FRONTEND (HTML + JS)
# -------------------------

@app.get("/", response_class=HTMLResponse)
def home():
    return """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Jogo Matemática</title>
<style>
body {
    background: #0f172a;
    color: white;
    font-family: Arial, sans-serif;
    padding: 20px;
}
button {
    width: 100%;
    padding: 14px;
    margin: 6px 0;
    font-size: 18px;
    border-radius: 8px;
    border: none;
}
.correct { background: #22c55e; }
.wrong { background: #ef4444; }
.option { background: #1e293b; color: white; }
</style>
</head>

<body>
<h2>🧠 Jogo Matemática</h2>

<p>Nível: <span id="nivel">1</span></p>
<h1 id="pergunta">---</h1>

<div id="opcoes"></div>

<script>
let nivel = 1;
let respostaCorreta = null;

async function carregarPergunta() {
    const res = await fetch(`/api/pergunta?nivel=${nivel}`);
    const data = await res.json();

    respostaCorreta = data.resposta;
    document.getElementById("pergunta").innerText = data.pergunta;

    const div = document.getElementById("opcoes");
    div.innerHTML = "";

    data.alternativas.forEach(op => {
        const btn = document.createElement("button");
        btn.innerText = op;
        btn.className = "option";
        btn.onclick = () => verificar(op, btn);
        div.appendChild(btn);
    });
}

function verificar(valor, botao) {
    if (valor === respostaCorreta) {
        botao.className = "correct";
        nivel++;
        document.getElementById("nivel").innerText = nivel;
        setTimeout(carregarPergunta, 800);
    } else {
        botao.className = "wrong";
    }
}

carregarPergunta();
</script>

</body>
</html>
"""
