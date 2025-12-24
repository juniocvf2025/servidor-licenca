# app.py para o servidor (coloque no OnRender)
from flask import Flask, request, jsonify
import hashlib
import time
from datetime import datetime
import base64

app = Flask(__name__)

# CHAVE EXATA DO SEU CLIENTE
SECRET_KEY = base64.b64decode("VDNsM2dyQG0tTDFjM25jMy1TM2NyM3RLM3ktMzM2MTQxODQhMjAyNA==").decode()

# LICENÇAS EXATAS DO SEU CÓDIGO
licencas = {
    "DONO-2025-001": {"api_id": "33614184", "dias": 3365, "ativo": True},
    "DONO-2025-002": {"api_id": "33614184", "dias": 30, "ativo": True},
    "TESTE-2024-001": {"api_id": "33614184", "dias": 7, "ativo": True},
}

def calcular_hash(licenca_id, api_id, timestamp):
    return hashlib.sha256(f"{licenca_id}:{api_id}:{timestamp}:{SECRET_KEY}".encode()).hexdigest()

@app.route('/')
def home():
    return "✅ Servidor de Licenças Online - Vinculado API_ID 33614184"

@app.route('/verificar_licenca', methods=['POST'])
def verificar():
    try:
        data = request.json
        licenca_id = data.get('api_id')
        api_id = data.get('telegram_id')
        timestamp = data.get('timestamp')
        hash_recebido = data.get('hash_verificacao')
        
        # Validações
        if not all([licenca_id, api_id, timestamp, hash_recebido]):
            return jsonify({"valido": False, "message": "Dados incompletos"}), 400
        
        if licenca_id not in licencas:
            return jsonify({"valido": False, "message": "Licença não encontrada"}), 404
        
        licenca = licencas[licenca_id]
        
        if not licenca['ativo']:
            return jsonify({"valido": False, "message": "Licença inativa"}), 403
        
        if licenca['api_id'] != api_id:
            return jsonify({"valido": False, "message": "API_ID não vinculado"}), 403
        
        # Verificar hash
        hash_calculado = calcular_hash(licenca_id, api_id, timestamp)
        
        if hash_recebido != hash_calculado:
            return jsonify({"valido": False, "message": "Hash inválido"}), 403
        
        # Sucesso
        return jsonify({
            "valido": True,
            "message": f"✅ Licença válida! ({licenca['dias']} dias)",
            "licenca_id": licenca_id,
            "dias_restantes": licenca['dias']
        })
        
    except Exception as e:
        return jsonify({"valido": False, "message": f"Erro: {str(e)}"}), 500

@app.route('/status')
def status():
    return jsonify({
        "status": "online",
        "servidor": "servidor-licenca-fix",
        "licencas": len(licencas),
        "api_id_vinculado": "33614184"
    })

if __name__ == '__main__':
    app.run(debug=True)

