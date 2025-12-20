# app.py ATUALIZADO (no servidor)
from flask import Flask, request, jsonify
import hashlib
import time
from datetime import datetime

app = Flask(__name__)

# =============================================
# CONFIGURAÇÕES
# =============================================

CHAVE_FIXA = "T3l3gr@m-L1c3nc3-S3cr3tK3y-33614184!2024"

LICENCAS = {
    "DONO-2025-001": {
        "telegram_id": "33614184",
        "plano": "P1",
        "validade_dias": 36500
    }
}

# =============================================
# ENDPOINTS
# =============================================

@app.route('/')
def home():
    return jsonify({
        "status": "online",
        "versao": "3.1",
        "servico": "Sistema de Licenciamento v3.1",
        "chave_configurada": True,
        "licencas": len(LICENCAS),
        "suporta_dois_formatos": True
    })

@app.route('/verificar_licenca', methods=['POST'])
def verificar_licenca():
    """Aceita AMBOS os formatos: antigo e novo"""
    try:
        dados = request.json
        
        if not dados:
            return jsonify({"erro": "Sem dados"}), 400
        
        # TENTAR FORMATO NOVO primeiro
        api_id = dados.get('api_id') or dados.get('licenca_id', '')
        telegram_id = dados.get('telegram_id') or dados.get('vinculo_telegram', '')
        
        if not api_id or not telegram_id:
            return jsonify({"erro": "Dados incompletos"}), 400
        
        # Verificar se licença existe
        if api_id not in LICENCAS:
            return jsonify({"erro": "Licença não encontrada"}), 404
        
        licenca = LICENCAS[api_id]
        
        # Se tem hash_verificacao, é formato NOVO - verificar hash
        if 'hash_verificacao' in dados and 'timestamp' in dados:
            timestamp = dados.get('timestamp', 0)
            hash_recebido = dados.get('hash_verificacao', '')
            
            # Calcular hash esperado
            string_hash = f"{api_id}:{telegram_id}:{timestamp}:{CHAVE_FIXA}"
            hash_esperado = hashlib.sha256(string_hash.encode()).hexdigest()
            
            if hash_recebido != hash_esperado:
                return jsonify({"erro": "Hash inválido"}), 403
        
        # Verificar Telegram ID
        if str(licenca['telegram_id']) != str(telegram_id):
            return jsonify({"erro": "Telegram ID não vinculado"}), 403
        
        # TUDO OK! Retornar licença válida
        timestamp_resp = int(time.time())
        resposta = f"1|{licenca['plano']}|{licenca['validade_dias']}|token-{timestamp_resp}|{timestamp_resp}|ok"
        return resposta, 200
        
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@app.route('/health')
def health():
    return jsonify({"status": "healthy"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
