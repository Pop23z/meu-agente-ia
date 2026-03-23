import anthropic
import json
import os
from ddgs import DDGS
from flask import Flask, request, jsonify, render_template_string

client = anthropic.Anthropic()
app = Flask(__name__)
MEMORIA_ARQUIVO = "memoria.json"

def carregar_memoria():
    if os.path.exists(MEMORIA_ARQUIVO):
        with open(MEMORIA_ARQUIVO, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def salvar_memoria(historico):
    with open(MEMORIA_ARQUIVO, "w", encoding="utf-8") as f:
        json.dump(historico, f, ensure_ascii=False, indent=2)

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Meu Agente IA</title>
    <meta charset="utf-8">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: 'Segoe UI', Arial, sans-serif; background: #f0f2f5; height: 100vh; display: flex; align-items: center; justify-content: center; }
        .container { width: 100%; max-width: 720px; height: 90vh; background: white; border-radius: 16px; box-shadow: 0 4px 24px rgba(0,0,0,0.10); display: flex; flex-direction: column; overflow: hidden; }
        .header { padding: 20px 24px; background: #1a1a2e; color: white; display: flex; justify-content: space-between; align-items: center; }
        .header h1 { font-size: 18px; font-weight: 600; }
        .header p { font-size: 13px; color: #aaa; margin-top: 2px; }
        .header button { font-size: 12px; background: rgba(255,255,255,0.15); color: white; border: none; padding: 6px 12px; border-radius: 20px; cursor: pointer; }
        .header button:hover { background: rgba(255,255,255,0.25); }
        .chat { flex: 1; overflow-y: auto; padding: 24px; display: flex; flex-direction: column; gap: 16px; }
        .boas-vindas { text-align: center; color: #999; font-size: 14px; margin: auto; }
        .boas-vindas div { font-size: 32px; margin-bottom: 10px; }
        .msg { display: flex; flex-direction: column; max-width: 85%; }
        .msg.user { align-self: flex-end; align-items: flex-end; }
        .msg.agent { align-self: flex-start; align-items: flex-start; }
        .msg-label { font-size: 11px; color: #999; margin-bottom: 4px; }
        .msg-bubble { padding: 12px 16px; border-radius: 16px; font-size: 14px; line-height: 1.6; white-space: pre-wrap; word-break: break-word; }
        .msg.user .msg-bubble { background: #1a1a2e; color: white; border-bottom-right-radius: 4px; }
        .msg.agent .msg-bubble { background: #f0f2f5; color: #1a1a2e; border-bottom-left-radius: 4px; }
        .loading { display: flex; gap: 4px; padding: 14px 16px; background: #f0f2f5; border-radius: 16px; border-bottom-left-radius: 4px; }
        .loading span { width: 8px; height: 8px; background: #aaa; border-radius: 50%; animation: bounce 1.2s infinite; }
        .loading span:nth-child(2) { animation-delay: 0.2s; }
        .loading span:nth-child(3) { animation-delay: 0.4s; }
        @keyframes bounce { 0%,80%,100%{transform:translateY(0)} 40%{transform:translateY(-8px)} }
        .input-area { padding: 16px 24px; border-top: 1px solid #eee; display: flex; gap: 10px; align-items: center; }
        .input-area input { flex: 1; padding: 12px 16px; border: 1.5px solid #e0e0e0; border-radius: 24px; font-size: 14px; outline: none; transition: border 0.2s; }
        .input-area input:focus { border-color: #1a1a2e; }
        .input-area button.send { width: 44px; height: 44px; border-radius: 50%; background: #1a1a2e; border: none; cursor: pointer; display: flex; align-items: center; justify-content: center; flex-shrink: 0; transition: opacity 0.2s; }
        .input-area button.send:hover { opacity: 0.85; }
        .input-area button.send svg { width: 18px; height: 18px; fill: white; }
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <div>
            <h1>Meu Agente IA</h1>
            <p>Pesquisa na web e salva arquivos por voce</p>
        </div>
        <button onclick="limparMemoria()">Limpar memoria</button>
    </div>
    <div class="chat" id="chat">
        <div class="boas-vindas" id="boas-vindas">
            <div>&#x1F916;</div>
            <p>Ola! Digite uma tarefa e eu executo por voce.</p>
            <p style="margin-top:6px;font-size:12px;">Lembro de tudo que conversamos antes!</p>
        </div>
    </div>
    <div class="input-area">
        <input type="text" id="msg" placeholder="Digite sua tarefa..." />
        <button class="send" onclick="enviar()">
            <svg viewBox="0 0 24 24"><path d="M2 21l21-9L2 3v7l15 2-15 2z"/></svg>
        </button>
    </div>
</div>
<script>
    const chat = document.getElementById("chat");

    function addMsg(tipo, texto) {
        const bv = document.getElementById("boas-vindas");
        if (bv) bv.remove();
        const div = document.createElement("div");
        div.className = "msg " + tipo;
        const label = document.createElement("div");
        label.className = "msg-label";
        label.textContent = tipo === "user" ? "Voce" : "Agente";
        const bubble = document.createElement("div");
        bubble.className = "msg-bubble";
        bubble.textContent = texto;
        div.appendChild(label);
        div.appendChild(bubble);
        chat.appendChild(div);
        chat.scrollTop = chat.scrollHeight;
    }

    function addLoading() {
        const bv = document.getElementById("boas-vindas");
        if (bv) bv.remove();
        const div = document.createElement("div");
        div.className = "msg agent";
        div.id = "loading";
        const label = document.createElement("div");
        label.className = "msg-label";
        label.textContent = "Agente";
        const loader = document.createElement("div");
        loader.className = "loading";
        loader.innerHTML = "<span></span><span></span><span></span>";
        div.appendChild(label);
        div.appendChild(loader);
        chat.appendChild(div);
        chat.scrollTop = chat.scrollHeight;
    }

    async function enviar() {
        const input = document.getElementById("msg");
        const msg = input.value.trim();
        if (!msg) return;
        input.value = "";
        addMsg("user", msg);
        addLoading();
        const res = await fetch("/chat", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({mensagem: msg})
        });
        const data = await res.json();
        document.getElementById("loading").remove();
        addMsg("agent", data.resposta);
    }

    async function limparMemoria() {
        await fetch("/limpar", {method: "POST"});
        chat.innerHTML = "";
        const bv = document.createElement("div");
        bv.className = "boas-vindas";
        bv.id = "boas-vindas";
        bv.innerHTML = "<div>&#x1F916;</div><p>Memoria apagada! Comece uma nova conversa.</p>";
        chat.appendChild(bv);
    }

    window.onload = async function() {
        const res = await fetch("/historico");
        const data = await res.json();
        if (data.historico.length > 0) {
            data.historico.forEach(function(m) {
                addMsg(m.role === "user" ? "user" : "agent", m.content);
            });
        }
    }

    document.getElementById("msg").addEventListener("keypress", function(e) {
        if (e.key === "Enter") enviar();
    });
</script>
</body>
</html>
"""

def buscar_na_web(query):
    with DDGS() as ddgs:
        resultados = list(ddgs.text(query, max_results=5))
    texto = ""
    for r in resultados:
        texto += "Titulo: " + r["title"] + "\nResumo: " + r["body"] + "\n\n"
    return texto

def salvar_arquivo(nome, conteudo):
    with open(nome, "w", encoding="utf-8") as f:
        f.write(conteudo)
    return "Arquivo " + nome + " salvo com sucesso."

ferramentas = [
    {
        "name": "buscar_na_web",
        "description": "Busca informacoes atuais na internet sobre qualquer assunto.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "O que pesquisar"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "salvar_arquivo",
        "description": "Salva um texto em um arquivo local.",
        "input_schema": {
            "type": "object",
            "properties": {
                "nome": {"type": "string", "description": "Nome do arquivo"},
                "conteudo": {"type": "string", "description": "Conteudo a salvar"}
            },
            "required": ["nome", "conteudo"]
        }
    }
]

def executar_ferramenta(nome, inputs):
    if nome == "buscar_na_web":
        return buscar_na_web(inputs["query"])
    elif nome == "salvar_arquivo":
        return salvar_arquivo(inputs["nome"], inputs["conteudo"])

def rodar_agente(tarefa):
    historico = carregar_memoria()
    historico.append({"role": "user", "content": tarefa})
    mensagens = historico.copy()
    resposta_final = ""
    while True:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=4096,
            tools=ferramentas,
            messages=mensagens
        )
        for bloco in response.content:
            if hasattr(bloco, "text") and bloco.text:
                resposta_final += bloco.text
        if response.stop_reason == "end_turn":
            break
        if response.stop_reason == "tool_use":
            mensagens.append({"role": "assistant", "content": response.content})
            resultados = []
            for bloco in response.content:
                if bloco.type == "tool_use":
                    resposta_final += "\nUsando ferramenta: " + bloco.name + "...\n"
                    resultado = executar_ferramenta(bloco.name, bloco.input)
                    resultados.append({
                        "type": "tool_result",
                        "tool_use_id": bloco.id,
                        "content": resultado
                    })
            mensagens.append({"role": "user", "content": resultados})
    historico.append({"role": "assistant", "content": resposta_final})
    salvar_memoria(historico)
    return resposta_final

@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/historico")
def historico():
    mem = carregar_memoria()
    simples = [m for m in mem if isinstance(m.get("content"), str)]
    return jsonify({"historico": simples})

@app.route("/chat", methods=["POST"])
def chat():
    dados = request.json
    resposta = rodar_agente(dados["mensagem"])
    return jsonify({"resposta": resposta})

@app.route("/limpar", methods=["POST"])
def limpar():
    salvar_memoria([])
    return jsonify({"ok": True})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)