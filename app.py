from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return """
    <h1>MATE GAME</h1>
    <p>Projeto em Python (terminal).</p>
    <p>Execute localmente com: <b>python main.py</b></p>
    <p>Versão web em construção.</p>
    """
