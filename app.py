from flask import Flask, request, jsonify
import hashlib
import time

app = Flask(__name__)

# =============================================
# CONFIGURAÇÕES FIXAS DIRETO NO CÓDIGO
# =============================================

# CHAVE FIXA DIRETA (igual no seu executável)
CHAVE = "T3l3gr@m-L1c3nc3-S3cr3tK3y-33614184!2024"

# LICENÇAS CADASTRADAS
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
        "licencas": len(LICENCAS)
    })

@app.route('/verificar_licenca', methods=['POST'])
def verificar_licenca():
    """Endpoint principal - SEM VARIÁVEIS DE AMBIENTE"""
    try:
        dados = request.json
        
        if not dados:
            return jsonify({"erro": "Sem dados"}), 400
        
        api_id = dados.get('api_id', '')
        telegram_id = dados.get('telegram_id', '')
        timestamp = dados.get('timestamp', 0)
        hash_recebido = dados.get('hash_verificacao', '')
        
        # 1. Licença existe?
        if api_id not in LICENCAS:
            return jsonify({"erro": "Licença não encontrada"}), 404
        
        licenca = LICENCAS[api_id]
        
        # 2. Calcular hash com chave FIXA
        string_hash = f"{api_id}:{telegram_id}:{timestamp}:{CHAVE}"
        hash_esperado = hashlib.sha256(string_hash.encode()).hexdigest()
        
        # 3. Hash correto?
        if hash_recebido != hash_esperado:
            return jsonify({"erro": "Hash inválido"}), 403
        
        # 4. Telegram ID correto?
        if str(licenca['telegram_id']) != str(telegram_id):
            return jsonify({"erro": "Telegram ID não vinculado"}), 403
        
        # TUDO OK! Retornar formato que executável espera
        resposta = f"1|{licenca['plano']}|{licenca['validade_dias']}|token-{int(time.time())}|{timestamp}|ok"
        return resposta, 200
        
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@app.route('/teste')
def teste():
    return jsonify({
        "mensagem": "Servidor funcionando!",
        "chave": CHAVE[:10] + "...",
        "hora": time.time()
    })

@app.route('/health')
def health():
    return jsonify({"status": "healthy"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
