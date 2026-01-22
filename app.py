import os
from flask import Flask

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")


@app.get("/")
def home():
    return r"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>MATE GAME — Web</title>
  <style>
    :root{
      --bg0:#070A12;
      --bg1:#0B1020;
      --card:#0f1730;
      --card2:#0c1430;
      --line:#22305a;
      --text:#EAF0FF;
      --muted:#AEB9E1;
      --good:#41f3a2;
      --bad:#ff5e7a;
      --pri:#2f6cff;
      --pri2:#5d8dff;
      --gold:#ffd36b;
    }
    *{box-sizing:border-box}
    body{
      margin:0;
      font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
      color:var(--text);
      background: radial-gradient(1000px 500px at 20% -10%, rgba(47,108,255,.35), transparent 50%),
                  radial-gradient(1000px 500px at 80% -10%, rgba(65,243,162,.25), transparent 50%),
                  linear-gradient(180deg, var(--bg0), var(--bg1));
      min-height:100vh;
      overflow-x:hidden;
    }
    .wrap{max-width:980px;margin:0 auto;padding:20px}
    .top{
      display:flex;align-items:center;justify-content:space-between;gap:12px;
      padding:16px 18px;border:1px solid rgba(34,48,90,.6);
      background: rgba(15,23,48,.65); backdrop-filter: blur(10px);
      border-radius:16px;
      box-shadow: 0 18px 50px rgba(0,0,0,.35);
    }
    .brand{display:flex;align-items:center;gap:12px}
    .logo{
      width:42px;height:42px;border-radius:14px;
      background: linear-gradient(135deg, var(--pri), var(--good));
      box-shadow: 0 12px 30px rgba(47,108,255,.25);
      display:grid;place-items:center;font-weight:900;color:#07102a;
    }
    h1{margin:0;font-size:18px;letter-spacing:.3px}
    .sub{margin:2px 0 0;color:var(--muted);font-size:12px}
    .pill{
      display:inline-flex;align-items:center;gap:8px;
      border:1px solid rgba(34,48,90,.7);
      background: rgba(11,16,32,.55);
      padding:8px 10px;border-radius:999px;color:var(--muted);
      font-size:12px;
      white-space:nowrap;
    }
    .grid{display:grid;grid-template-columns: 1.05fr .95fr;gap:14px;margin-top:14px}
    @media (max-width:900px){ .grid{grid-template-columns:1fr} }
    .card{
      border:1px solid rgba(34,48,90,.7);
      background: rgba(15,23,48,.62);
      backdrop-filter: blur(10px);
      border-radius:18px;
      padding:16px;
      box-shadow: 0 18px 60px rgba(0,0,0,.30);
      position:relative;
      overflow:hidden;
    }
    .card::before{
      content:"";
      position:absolute;inset:-2px;
      background: radial-gradient(600px 180px at 15% 0%, rgba(47,108,255,.16), transparent 65%),
                  radial-gradient(600px 180px at 85% 0%, rgba(65,243,162,.12), transparent 65%);
      pointer-events:none;
    }
    .card > *{position:relative}
    .titleRow{display:flex;align-items:center;justify-content:space-between;gap:10px}
    .title{font-weight:800;font-size:14px;color:var(--text)}
    .small{color:var(--muted);font-size:12px}
    .row{display:flex;gap:10px;margin-top:10px}
    .row > *{flex:1}
    label{display:block;color:var(--muted);font-size:12px;margin:10px 0 6px}
    input, select{
      width:100%;
      padding:12px 12px;
      border-radius:12px;
      border:1px solid rgba(34,48,90,.85);
      background: rgba(7,10,18,.55);
      color:var(--text);
      outline:none;
    }
    input:focus, select:focus{border-color: rgba(93,141,255,.95); box-shadow:0 0 0 3px rgba(47,108,255,.18)}
    button{
      width:100%;
      padding:12px 12px;
      border-radius:12px;
      border:1px solid rgba(47,108,255,.95);
      background: linear-gradient(135deg, var(--pri), var(--pri2));
      color:white;
      font-weight:800;
      cursor:pointer;
      transition: transform .08s ease, filter .15s ease;
    }
    button:active{transform: translateY(1px) scale(.99)}
    button.secondary{
      border-color: rgba(34,48,90,.85);
      background: rgba(7,10,18,.40);
      color:var(--text);
      font-weight:700;
    }
    .stats{
      display:flex;flex-wrap:wrap;gap:8px;margin-top:12px
    }
    .stat{
      padding:8px 10px;border-radius:999px;
      background: rgba(7,10,18,.45);
      border:1px solid rgba(34,48,90,.75);
      color:var(--muted);
      font-size:12px;
      display:flex;gap:6px;align-items:center;
    }
    .stat b{color:var(--text)}
    .gameArea{
      display:flex;flex-direction:column;gap:12px;margin-top:12px
    }
    .question{
      text-align:center;
      font-size:54px;
      font-weight:900;
      letter-spacing: 1px;
      padding:18px 10px;
      border-radius:16px;
      background: rgba(7,10,18,.45);
      border:1px solid rgba(34,48,90,.75);
      user-select:none;
    }
    .meterWrap{
      height:10px;border-radius:999px;
      background: rgba(7,10,18,.55);
      border:1px solid rgba(34,48,90,.75);
      overflow:hidden;
    }
    .meter{
      height:100%;
      width:100%;
      background: linear-gradient(90deg, var(--good), var(--gold), var(--bad));
      transform-origin:left;
      transform: scaleX(1);
      transition: transform .1s linear;
    }
    .msg{
      min-height:22px;
      font-size:13px;
      color:var(--muted);
      text-align:center;
    }
    .msg.ok{color:var(--good);font-weight:800}
    .msg.bad{color:var(--bad);font-weight:800}
    .kbd{
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      padding:2px 6px;border-radius:8px;
      background: rgba(7,10,18,.55);
      border:1px solid rgba(34,48,90,.75);
      color:var(--text);
      font-size:12px;
    }
    .rankList{
      margin-top:12px;
      display:flex;flex-direction:column;gap:8px;
      max-height:260px;
      overflow:auto;
      padding-right:4px;
    }
    .rankItem{
      display:flex;align-items:center;justify-content:space-between;gap:10px;
      padding:10px 10px;border-radius:14px;
      background: rgba(7,10,18,.40);
      border:1px solid rgba(34,48,90,.70);
      font-size:13px;
      color:var(--muted);
    }
    .rankItem b{color:var(--text)}
    .badge{
      font-weight:900;
      color: #07102a;
      background: linear-gradient(135deg, var(--gold), #fff0b6);
      padding:6px 10px;border-radius:999px;
    }
    .footerNote{margin-top:14px;color:var(--muted);font-size:12px;text-align:center}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="top">
      <div class="brand">
        <div class="logo">÷</div>
        <div>
          <h1>MATE GAME — Web</h1>
          <div class="sub">Agora sim com cara de jogo: vidas, fases, tempo, combo e ranking.</div>
        </div>
      </div>
      <div class="pill">
        Terminal continua em <span class="kbd">main.py</span> (rodar com <span class="kbd">python main.py</span>)
      </div>
    </div>

    <div class="grid">
      <!-- SETUP -->
      <div class="card">
        <div class="titleRow">
          <div class="title">Configuração</div>
          <div class="small">Dica: aperta <span class="kbd">Enter</span> pra enviar resposta</div>
        </div>

        <label>Nome do competidor</label>
        <input id="name" placeholder="Ex: Bruno" maxlength="24"/>

        <div class="row">
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
            <select id="diff">
              <option value="easy" selected>Fácil</option>
              <option value="medium">Médio</option>
              <option value="hard">Difícil</option>
            </select>
          </div>
        </div>

        <div class="row">
          <div>
            <label>Rodadas</label>
            <select id="rounds">
              <option value="10" selected>10</option>
              <option value="20">20</option>
              <option value="30">30</option>
            </select>
          </div>
          <div>
            <label>Tempo por questão</label>
            <select id="timeLimit">
              <option value="0">Sem tempo</option>
              <option value="8" selected>8s</option>
              <option value="5">5s</option>
              <option value="3">3s</option>
            </select>
          </div>
        </div>

        <div class="row">
          <button id="btnPlay">▶️ Jogar</button>
          <button id="btnResetAll" class="secondary">🧹 Reset geral</button>
        </div>

        <div class="stats" id="stats">
          <div class="stat">Jogador: <b id="stName">—</b></div>
          <div class="stat">Pontos: <b id="stScore">0</b></div>
          <div class="stat">Streak: <b id="stStreak">0</b></div>
          <div class="stat">Vidas: <b id="stLives">3</b></div>
          <div class="stat">Rodada: <b id="stRound">0</b>/<b id="stRounds">0</b></div>
          <div class="stat">Nível: <b id="stLevel">1</b></div>
        </div>
      </div>

      <!-- GAME -->
      <div class="card">
        <div class="titleRow">
          <div class="title">Partida</div>
          <div class="small" id="stModeDiff">—</div>
        </div>

        <div class="gameArea">
          <div class="meterWrap" title="Tempo">
            <div class="meter" id="meter"></div>
          </div>

          <div class="question" id="q">—</div>

          <div class="row">
            <input id="ans" placeholder="Sua resposta…" inputmode="numeric" />
            <button id="btnSend">Responder</button>
          </div>

          <div class="msg" id="msg"></div>

          <div class="row">
            <button id="btnNext" class="secondary">Próxima</button>
            <button id="btnGiveUp" class="secondary">Desistir</button>
          </div>
        </div>

        <div class="footerNote">
          Ranking salvo no navegador (local). Depois a gente liga num ranking global.
        </div>
      </div>
    </div>

    <!-- RANKING -->
    <div class="card" style="margin-top:14px;">
      <div class="titleRow">
        <div class="title">🏆 Ranking (Top 10)</div>
        <div class="small">Salvo no seu navegador</div>
      </div>
      <div class="rankList" id="rank"></div>
    </div>

    <div class="footerNote">
      Se o Render “dormir”, a primeira abertura pode demorar no plano free.
    </div>
  </div>

<script>
  // ---------- util ----------
  const $ = (id) => document.getElementById(id);

  function beep(type="ok"){
    try{
      const ctx = new (window.AudioContext || window.webkitAudioContext)();
      const o = ctx.createOscillator();
      const g = ctx.createGain();
      o.type = "sine";
      o.frequency.value = type==="ok" ? 660 : 220;
      g.gain.value = 0.08;
      o.connect(g); g.connect(ctx.destination);
      o.start();
      setTimeout(()=>{ o.stop(); ctx.close(); }, 80);
    }catch(e){}
  }

  function setMsg(text, kind=""){
    const m = $("msg");
    m.textContent = text || "";
    m.className = "msg " + kind;
  }

  function clamp(n, a, b){ return Math.max(a, Math.min(b, n)); }

  // ---------- ranking (local) ----------
  const RKEY = "mate_game_rank_v1";
  function loadRank(){
    try { return JSON.parse(localStorage.getItem(RKEY) || "[]"); } catch { return []; }
  }
  function saveRank(list){
    localStorage.setItem(RKEY, JSON.stringify(list.slice(0, 10)));
  }
  function addRank(entry){
    const list = loadRank();
    list.push(entry);
    list.sort((a,b)=>b.score-a.score);
    saveRank(list);
    renderRank();
  }
  function renderRank(){
    const list = loadRank();
    const root = $("rank");
    root.innerHTML = "";
    if(list.length===0){
      root.innerHTML = `<div class="rankItem"><span>Nenhum registro ainda.</span><span class="small">Jogue uma partida 🙂</span></div>`;
      return;
    }
    list.slice(0,10).forEach((e, i)=>{
      const medal = i===0 ? "🥇" : i===1 ? "🥈" : i===2 ? "🥉" : "🏅";
      const el = document.createElement("div");
      el.className = "rankItem";
      el.innerHTML = `
        <div style="display:flex;gap:10px;align-items:center;">
          <span class="badge">${medal} #${i+1}</span>
          <div>
            <div><b>${e.name}</b> — ${e.score} pts</div>
            <div class="small">${e.modeLabel} • ${e.diffLabel} • ${e.rounds}Q</div>
          </div>
        </div>
        <div class="small">lvl ${e.level}</div>
      `;
      root.appendChild(el);
    });
  }

  // ---------- game ----------
  const MODES = {
    add: "Soma",
    sub: "Subtração",
    mul: "Multiplicação",
    div: "Divisão",
    mix: "Misto",
  };
  const DIFFS = {
    easy:   {label:"Fácil",  max:10},
    medium: {label:"Médio",  max:30},
    hard:   {label:"Difícil",max:100},
  };

  let st = {
    name:"",
    mode:"mix",
    diff:"easy",
    roundsTotal:10,
    timeLimit:8,
    score:0,
    streak:0,
    lives:3,
    round:0,
    level:1,
    qText:"—",
    qAnswer:null,
    qStart:0,
    timer:null
  };

  function computeLevel(score){
    return 1 + Math.floor(score / 120);
  }

  function pickOp(){
    if(st.mode !== "mix") return st.mode;
    const ops = ["add","sub","mul","div"];
    return ops[Math.floor(Math.random()*ops.length)];
  }

  function makeQuestion(){
    const maxN = DIFFS[st.diff].max;
    const op = pickOp();
    let a = 1 + Math.floor(Math.random()*maxN);
    let b = 1 + Math.floor(Math.random()*maxN);

    if(op==="add"){
      st.qText = `${a} + ${b}`;
      st.qAnswer = a + b;
      return;
    }
    if(op==="sub"){
      const x = Math.max(a,b), y = Math.min(a,b);
      st.qText = `${x} - ${y}`;
      st.qAnswer = x - y;
      return;
    }
    if(op==="mul"){
      const aa = 1 + Math.floor(Math.random()*Math.max(3, Math.floor(maxN/2)));
      const bb = 1 + Math.floor(Math.random()*Math.max(3, Math.floor(maxN/2)));
      st.qText = `${aa} × ${bb}`;
      st.qAnswer = aa * bb;
      return;
    }
    if(op==="div"){
      const divisor = 1 + Math.floor(Math.random()*Math.max(2, Math.floor(maxN/3)));
      const q = 1 + Math.floor(Math.random()*Math.max(2, Math.floor(maxN/3)));
      const dividendo = divisor * q;
      st.qText = `${dividendo} ÷ ${divisor}`;
      st.qAnswer = q;
      return;
    }
  }

  function pointsFor(correct, elapsed){
    if(!correct) return 0;
    const base = 10;
    const streakBonus = clamp(st.streak, 0, 10) * 2;
    let speedBonus = 0;
    if(st.timeLimit > 0){
      speedBonus = clamp(Math.floor((st.timeLimit - elapsed) * 2), 0, 12);
    }else{
      speedBonus = clamp(6 - Math.floor(elapsed), 0, 6);
    }
    return base + streakBonus + speedBonus;
  }

  function stopTimer(){
    if(st.timer){ clearInterval(st.timer); st.timer=null; }
  }

  function startTimer(){
    stopTimer();
    const meter = $("meter");
    meter.style.transform = "scaleX(1)";
    if(st.timeLimit <= 0) return;

    const started = st.qStart;
    st.timer = setInterval(()=>{
      const elapsed = (Date.now() - started) / 1000;
      const ratio = clamp(1 - (elapsed / st.timeLimit), 0, 1);
      meter.style.transform = `scaleX(${ratio})`;

      if(elapsed >= st.timeLimit){
        // time over
        stopTimer();
        wrong("⏱️ Tempo esgotado!");
      }
    }, 80);
  }

  function render(){
    $("stName").textContent = st.name || "—";
    $("stScore").textContent = st.score;
    $("stStreak").textContent = st.streak;
    $("stLives").textContent = st.lives;
    $("stRound").textContent = st.round;
    $("stRounds").textContent = st.roundsTotal;
    $("stLevel").textContent = st.level;
    $("q").textContent = st.qText || "—";
    $("stModeDiff").textContent = `${MODES[st.mode]} • ${DIFFS[st.diff].label} • ${st.timeLimit>0 ? st.timeLimit+"s" : "sem tempo"}`;
  }

  function lockGameUI(locked){
    $("btnSend").disabled = locked;
    $("btnNext").disabled = locked;
    $("ans").disabled = locked;
  }

  function newRound(){
    if(st.lives <= 0){
      endGame("💀 Fim de jogo. Sem vidas.");
      return;
    }
    if(st.round >= st.roundsTotal){
      endGame("🏁 Partida finalizada!");
      return;
    }

    st.round += 1;
    makeQuestion();
    st.qStart = Date.now();
    setMsg("", "");
    $("ans").value = "";
    $("ans").focus();
    lockGameUI(false);
    render();
    startTimer();
  }

  function correct(elapsed){
    stopTimer();
    st.streak += 1;
    const gained = pointsFor(true, elapsed);
    st.score += gained;
    st.level = computeLevel(st.score);
    beep("ok");
    setMsg(`✅ Correto! +${gained} pts (tempo ${elapsed.toFixed(1)}s)`, "ok");
    lockGameUI(true);
  }

  function wrong(reason){
    stopTimer();
    st.streak = 0;
    st.lives -= 1;
    beep("bad");
    setMsg(`${reason} ❌ Correto: ${st.qAnswer}`, "bad");
    lockGameUI(true);
    render();
    if(st.lives <= 0){
      endGame("💀 Fim de jogo. Sem vidas.");
    }
  }

  function submit(){
    if(st.qAnswer === null) return;
    const raw = $("ans").value.trim();
    if(!raw){ setMsg("Digite uma resposta.", "bad"); return; }
    const n = Number(raw);
    if(!Number.isFinite(n)){ setMsg("Resposta inválida.", "bad"); return; }

    const elapsed = (Date.now() - st.qStart)/1000;
    if(n === st.qAnswer) correct(elapsed);
    else wrong("Errou!");
    render();
  }

  function endGame(msg){
    stopTimer();
    lockGameUI(true);
    setMsg(msg + ` Pontos: ${st.score}`, st.lives>0 ? "ok":"bad");
    // salva no ranking
    if((st.name || "").trim().length >= 2){
      addRank({
        name: st.name,
        score: st.score,
        modeLabel: MODES[st.mode],
        diffLabel: DIFFS[st.diff].label,
        rounds: st.roundsTotal,
        level: st.level,
        ts: Date.now()
      });
    }
  }

  function startGame(){
    st.name = $("name").value.trim().slice(0,24);
    st.mode = $("mode").value;
    st.diff = $("diff").value;
    st.roundsTotal = Number($("rounds").value) || 10;
    st.timeLimit = Number($("timeLimit").value) || 0;

    st.score = 0;
    st.streak = 0;
    st.lives = 3;
    st.round = 0;
    st.level = 1;
    st.qText = "—";
    st.qAnswer = null;
    st.qStart = 0;

    render();
    setMsg("Boa! Começou. Responda e aperte Enter 😄", "ok");
    newRound();
  }

  function resetAll(){
    stopTimer();
    localStorage.removeItem(RKEY);
    renderRank();
    setMsg("Reset geral feito (ranking apagado).", "ok");
  }

  $("btnPlay").addEventListener("click", startGame);
  $("btnSend").addEventListener("click", submit);
  $("btnNext").addEventListener("click", newRound);
  $("btnGiveUp").addEventListener("click", ()=> endGame("🏳️ Você desistiu."));
  $("btnResetAll").addEventListener("click", resetAll);
  $("ans").addEventListener("keydown", (e)=>{ if(e.key==="Enter") submit(); });

  renderRank();
  render();
  setMsg("Configure e clique em Jogar.", "");
</script>
</body>
</html>
"""


if __name__ == "__main__":
    app.run(debug=True)
