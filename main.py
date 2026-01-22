import json
import os
import random
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

RANKING_FILE = "rankings.json"


# ----------------------------
# Dados e persistência
# ----------------------------
def load_data() -> Dict:
    if not os.path.exists(RANKING_FILE):
        return {
            "overall": [],            # lista de dicts: {name, score, mode, difficulty, ts}
            "by_mode": {},            # mode -> lista
            "best_by_player": {}      # name -> melhor score
        }
    try:
        with open(RANKING_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        data.setdefault("overall", [])
        data.setdefault("by_mode", {})
        data.setdefault("best_by_player", {})
        return data
    except Exception:
        # Se o arquivo corromper, recomeça (melhor que quebrar o jogo)
        return {
            "overall": [],
            "by_mode": {},
            "best_by_player": {}
        }


def save_data(data: Dict) -> None:
    with open(RANKING_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def now_ts() -> int:
    return int(time.time())


def add_ranking_entry(data: Dict, entry: Dict, top_n: int = 20) -> None:
    # ranking geral
    data["overall"].append(entry)
    data["overall"] = sorted(data["overall"], key=lambda x: x["score"], reverse=True)[:top_n]

    # ranking por modo
    mode = entry["mode"]
    data["by_mode"].setdefault(mode, [])
    data["by_mode"][mode].append(entry)
    data["by_mode"][mode] = sorted(data["by_mode"][mode], key=lambda x: x["score"], reverse=True)[:top_n]

    # melhor por jogador
    name = entry["name"]
    best = data["best_by_player"].get(name, 0)
    if entry["score"] > best:
        data["best_by_player"][name] = entry["score"]


# ----------------------------
# Configurações do jogo
# ----------------------------
MODES = {
    "1": ("Soma", "add"),
    "2": ("Subtração", "sub"),
    "3": ("Multiplicação", "mul"),
    "4": ("Divisão", "div"),
    "5": ("Misto", "mix"),
}

DIFFICULTIES = {
    "1": ("Fácil", 10),
    "2": ("Médio", 30),
    "3": ("Difícil", 100),
}

TIME_MODES = {
    "1": ("Sem tempo", None),
    "2": ("Relâmpago (5s)", 5),
    "3": ("Relâmpago (3s)", 3),
}


@dataclass
class GameConfig:
    player_name: str
    mode_key: str        # add/sub/mul/div/mix
    mode_label: str
    diff_label: str
    max_number: int
    time_limit: Optional[int]
    rounds: int


# ----------------------------
# UI simples (terminal)
# ----------------------------
def clear() -> None:
    # limpa no Windows e Unix
    os.system("cls" if os.name == "nt" else "clear")


def pause(msg: str = "Enter para continuar...") -> None:
    input(msg)


def header(title: str) -> None:
    print("=" * 50)
    print(title.center(50))
    print("=" * 50)


def ask_choice(prompt: str, valid: List[str]) -> str:
    while True:
        choice = input(prompt).strip()
        if choice in valid:
            return choice
        print("Opção inválida. Tente novamente.")


def ask_int(prompt: str, min_v: int, max_v: int) -> int:
    while True:
        raw = input(prompt).strip()
        if raw.isdigit():
            v = int(raw)
            if min_v <= v <= max_v:
                return v
        print(f"Digite um número entre {min_v} e {max_v}.")


def ask_name() -> str:
    while True:
        name = input("Nome do competidor: ").strip()
        if len(name) >= 2:
            return name
        print("Digite pelo menos 2 caracteres.")


# ----------------------------
# Geração de questões
# ----------------------------
def make_question(op: str, max_n: int) -> Tuple[str, int]:
    a = random.randint(1, max_n)
    b = random.randint(1, max_n)

    if op == "add":
        return f"{a} + {b} = ?", a + b

    if op == "sub":
        # garante resultado não-negativo (pra ficar mais amigável)
        x, y = max(a, b), min(a, b)
        return f"{x} - {y} = ?", x - y

    if op == "mul":
        # reduz um pouco a multiplicação no difícil pra não ficar gigante
        aa = random.randint(1, max(3, max_n // 2))
        bb = random.randint(1, max(3, max_n // 2))
        return f"{aa} × {bb} = ?", aa * bb

    if op == "div":
        # gera divisão exata: (a*b)/b
        divisor = random.randint(1, max(2, max_n // 3))
        quociente = random.randint(1, max(2, max_n // 3))
        dividendo = divisor * quociente
        return f"{dividendo} ÷ {divisor} = ?", quociente

    raise ValueError("Operação inválida")


def pick_operation(mode_key: str) -> str:
    if mode_key != "mix":
        return mode_key
    return random.choice(["add", "sub", "mul", "div"])


# ----------------------------
# Pontuação e progressão
# ----------------------------
def calc_points(correct: bool, streak: int, time_limit: Optional[int], elapsed: float) -> int:
    if not correct:
        return 0

    base = 10
    # bônus por streak
    streak_bonus = min(streak, 10)  # trava bônus
    pts = base + streak_bonus * 2

    # bônus relâmpago (se tiver tempo)
    if time_limit is not None:
        # quanto mais rápido, maior bônus (mínimo 0)
        speed_bonus = max(0, int((time_limit - elapsed) * 2))
        pts += speed_bonus

    return pts


def level_from_score(score: int) -> int:
    # sobe nível a cada 100 pontos (simples e satisfatório)
    return 1 + (score // 100)


# ----------------------------
# Loop do jogo
# ----------------------------
def play_game(cfg: GameConfig) -> Dict:
    clear()
    header("MATE GAME — Partida")
    print(f"Jogador: {cfg.player_name}")
    print(f"Modo: {cfg.mode_label} | Dificuldade: {cfg.diff_label} | Rodadas: {cfg.rounds}")
    if cfg.time_limit:
        print(f"Tempo por questão: {cfg.time_limit}s (relâmpago)")
    else:
        print("Tempo por questão: sem limite")
    print("-" * 50)
    pause()

    score = 0
    streak = 0
    correct_count = 0

    for i in range(1, cfg.rounds + 1):
        clear()
        lvl = level_from_score(score)
        header(f"Questão {i}/{cfg.rounds}  |  Nível {lvl}  |  Pontos {score}  |  Streak {streak}")

        op = pick_operation(cfg.mode_key)
        text, answer = make_question(op, cfg.max_number)

        start = time.time()
        raw = input(f"{text}  (ou 'sair' para encerrar) \n> ").strip().lower()
        elapsed = time.time() - start

        if raw == "sair":
            break

        # tempo estourado?
        if cfg.time_limit is not None and elapsed > cfg.time_limit:
            streak = 0
            print(f"⏱️ Tempo esgotado! ({elapsed:.1f}s > {cfg.time_limit}s) Resposta era: {answer}")
            pause()
            continue

        # valida resposta numérica
        try:
            user_ans = int(raw)
        except ValueError:
            streak = 0
            print("Resposta inválida (não é número).")
            print(f"A resposta correta era: {answer}")
            pause()
            continue

        correct = (user_ans == answer)

        if correct:
            streak += 1
            correct_count += 1
            gained = calc_points(True, streak, cfg.time_limit, elapsed)
            score += gained
            print(f"✅ Correto! +{gained} pontos  (tempo: {elapsed:.1f}s)")
        else:
            streak = 0
            print(f"❌ Errado. Você respondeu {user_ans}. Correto: {answer}  (tempo: {elapsed:.1f}s)")

        pause()

    # resumo
    clear()
    header("Resumo da Partida")
    print(f"Jogador: {cfg.player_name}")
    print(f"Modo: {cfg.mode_label} | Dificuldade: {cfg.diff_label}")
    print(f"Pontuação final: {score}")
    print(f"Acertos: {correct_count}/{cfg.rounds}")
    print(f"Nível final: {level_from_score(score)}")
    print("-" * 50)
    pause()

    return {
        "name": cfg.player_name,
        "score": score,
        "mode": cfg.mode_label,
        "mode_key": cfg.mode_key,
        "difficulty": cfg.diff_label,
        "ts": now_ts(),
    }


# ----------------------------
# Rankings (visualização)
# ----------------------------
def print_ranking(entries: List[Dict], title: str) -> None:
    clear()
    header(title)
    if not entries:
        print("Nenhum registro ainda.")
        pause()
        return

    for idx, e in enumerate(entries, start=1):
        name = e.get("name", "—")
        score = e.get("score", 0)
        mode = e.get("mode", "—")
        diff = e.get("difficulty", "—")
        print(f"{idx:02d}. {name:<18} | {score:>5} pts | {mode:<12} | {diff}")
    print("-" * 50)
    pause()


def show_rankings(data: Dict) -> None:
    while True:
        clear()
        header("Rankings")
        print("1) Ranking geral (Top 20)")
        print("2) Ranking por modo")
        print("3) Melhor pontuação por jogador")
        print("0) Voltar")
        ch = ask_choice("> ", ["1", "2", "3", "0"])

        if ch == "1":
            print_ranking(data["overall"], "Ranking Geral — Top 20")
        elif ch == "2":
            clear()
            header("Escolha o modo")
            for k, (label, key) in MODES.items():
                print(f"{k}) {label}")
            print("0) Voltar")
            mk = ask_choice("> ", list(MODES.keys()) + ["0"])
            if mk == "0":
                continue
            mode_label, mode_key = MODES[mk]
            entries = data["by_mode"].get(mode_label, [])
            print_ranking(entries, f"Ranking — {mode_label} (Top 20)")
        elif ch == "3":
            clear()
            header("Melhor por Jogador")
            best_map = data.get("best_by_player", {})
            if not best_map:
                print("Nenhum registro ainda.")
                pause()
                continue
            best_list = sorted(best_map.items(), key=lambda x: x[1], reverse=True)[:20]
            for idx, (name, best) in enumerate(best_list, start=1):
                print(f"{idx:02d}. {name:<18} | {best:>5} pts")
            print("-" * 50)
            pause()
        else:
            return


# ----------------------------
# Configuração da partida
# ----------------------------
def build_config(player_name: str) -> GameConfig:
    clear()
    header("Configurar Partida")

    print("Escolha o modo:")
    for k, (label, _) in MODES.items():
        print(f"{k}) {label}")
    mode_choice = ask_choice("> ", list(MODES.keys()))
    mode_label, mode_key = MODES[mode_choice]

    clear()
    header("Dificuldade")
    for k, (label, max_n) in DIFFICULTIES.items():
        print(f"{k}) {label} (números até {max_n})")
    diff_choice = ask_choice("> ", list(DIFFICULTIES.keys()))
    diff_label, max_number = DIFFICULTIES[diff_choice]

    clear()
    header("Tempo")
    for k, (label, t) in TIME_MODES.items():
        print(f"{k}) {label}")
    time_choice = ask_choice("> ", list(TIME_MODES.keys()))
    _, time_limit = TIME_MODES[time_choice]

    clear()
    header("Rodadas")
    rounds = ask_int("Quantas questões? (5 a 50) > ", 5, 50)

    return GameConfig(
        player_name=player_name,
        mode_key=mode_key,
        mode_label=mode_label,
        diff_label=diff_label,
        max_number=max_number,
        time_limit=time_limit,
        rounds=rounds
    )


# ----------------------------
# Menu principal
# ----------------------------
def main_menu() -> None:
    data = load_data()

    player_name: Optional[str] = None

    while True:
        clear()
        header("MATE GAME")
        if player_name:
            best = data.get("best_by_player", {}).get(player_name, 0)
            print(f"Jogador atual: {player_name}  |  Melhor: {best} pts")
        else:
            print("Jogador atual: (nenhum)")
        print("-" * 50)

        print("1) Novo competidor / Trocar jogador")
        print("2) Iniciar partida")
        print("3) Rankings")
        print("4) Ajuda rápida")
        print("0) Sair")

        ch = ask_choice("> ", ["1", "2", "3", "4", "0"])

        if ch == "1":
            clear()
            header("Novo competidor")
            player_name = ask_name()
            print(f"Ok, {player_name}! ✅")
            pause()

        elif ch == "2":
            if not player_name:
                clear()
                header("Atenção")
                print("Você precisa cadastrar um nome antes de jogar.")
                pause()
                continue

            cfg = build_config(player_name)
            result = play_game(cfg)

            # salva resultado se pontuou
            entry = {
                "name": result["name"],
                "score": result["score"],
                "mode": result["mode"],
                "difficulty": result["difficulty"],
                "ts": result["ts"],
            }
            add_ranking_entry(data, entry, top_n=20)
            save_data(data)

        elif ch == "3":
            show_rankings(data)

        elif ch == "4":
            clear()
            header("Ajuda rápida")
            print("• Digite 'sair' durante uma questão para encerrar a partida.")
            print("• 'Relâmpago' dá bônus por rapidez, mas se passar do tempo, perde a questão.")
            print("• Streak (sequência de acertos) aumenta seus pontos.")
            print("• O ranking fica salvo no arquivo rankings.json na mesma pasta do jogo.")
            print("-" * 50)
            pause()

        else:
            clear()
            header("Até mais!")
            print("Saindo...")
            break


if __name__ == "__main__":
    main_menu()
