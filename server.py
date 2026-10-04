try:
    from flask import Flask, send_from_directory, request, Response, jsonify
except ImportError:
    print("You don't have Flask installed, run `$ pip3 install flask` and try again")
    exit(1)

import os
import sys
import requests as req

# Importar el agente
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
from agent import run_agent, SYSTEM_PROMPT

static_file_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), './')
app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

FASTAPI = "http://127.0.0.1:8000"

# Historial de conversación en memoria
chat_history = [{"role": "system", "content": SYSTEM_PROMPT}]

# Endpoint del chat
@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json(silent=True) or {}
    user_input = data.get("message", "").strip()
    if not user_input:
        return jsonify({"error": "Mensaje vacío"}), 400
    try:
        reply = run_agent(user_input, chat_history)
        return jsonify({"reply": reply})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/chat/reset', methods=['POST'])
def reset_chat():
    global chat_history
    chat_history = [{"role": "system", "content": SYSTEM_PROMPT}]
    return jsonify({"ok": True})

# Proxy hacia la FastAPI
@app.route('/api/<path:path>', methods=['GET', 'POST', 'PATCH', 'DELETE'])
def proxy(path):
    url = f"{FASTAPI}/{path}"
    resp = req.request(
        method=request.method,
        url=url,
        json=request.get_json(silent=True),
        params=request.args,
        timeout=10,
    )
    return Response(resp.content, status=resp.status_code, content_type=resp.headers.get('Content-Type', 'application/json'))

@app.route('/api/', methods=['GET'])
def proxy_root():
    resp = req.get(f"{FASTAPI}/", timeout=10)
    return Response(resp.content, status=resp.status_code, content_type='application/json')

# Serving the index file
@app.route('/', methods=['GET'])
def serve_dir_directory_index():
    if os.path.exists("index.html"):
        return send_from_directory(static_file_dir, 'index.html')
    else:
        return "<h1 align='center'>404</h1><h2 align='center'>Missing index.html file</h2>"

@app.route('/<path:path>', methods=['GET'])
def serve_any_other_file(path):
    if not os.path.isfile(os.path.join(static_file_dir, path)):
        path = os.path.join(path, 'index.html')
    response = send_from_directory(static_file_dir, path)
    response.cache_control.max_age = 0
    return response

app.run(host='0.0.0.0', port=3000, debug=True, use_reloader=False)
