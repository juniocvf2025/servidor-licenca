from flask import Flask, request, jsonify
import hashlib
import time

app = Flask(__name__)

# =============================================
# CONFIGURAÇÕES FIXAS - MESMAS DO SEU EXECUTÁVEL
# =============================================

# CHAVE FIXA (igual no seu executável)
CHAVE_FIXA = "T3l3gr@m-L1c3nc3-S3cr3tK3y-33614184!2024"

# LICENÇAS CADASTRADAS
LICENCAS = {
    "DONO-2025-001": {
        "telegram_id": "33614184",
        "nome": "Licença Premium",
        "plano": "P1",
        "validade_dias": 36500,  # 100 anos
        "status": "ativa"
    }
}

# =============================================
# ENDPOINTS SIMPLES
# =============================================

@app.route('/')
def home():
    """Status do servidor"""
    return jsonify({
        "status": "online",
        "versao": "3.1",
        "servico": "Sistema de Licenciamento v3.1",
        "mensagem": "Servidor funcionando!",
        "tempo": time.time()
    })

@app.route('/verificar_licenca', methods=['POST'])
def verificar_licenca():
    """Verifica licença de forma SIMPLES"""
    try:
        # Pegar dados da requisição
        dados = request.json
        
        if not dados:
            return jsonify({
                "status": "erro",
                "msg": "Dados não fornecidos"
            }), 400
        
        # Pegar campos
        api_id = dados.get('api_id', '')
        telegram_id = dados.get('telegram_id', '')
        timestamp = dados.get('timestamp', 0)
        hash_recebido = dados.get('hash_verificacao', '')
        
        # Verificar se licença existe
        if api_id not in LICENCAS:
            return jsonify({
                "status": "erro",
                "msg": "Licença não encontrada"
            }), 404
        
        licenca = LICENCAS[api_id]
        
        # Calcular hash esperado (igual no executável)
        string_hash = f"{api_id}:{telegram_id}:{timestamp}:{CHAVE_FIXA}"
        hash_esperado = hashlib.sha256(string_hash.encode()).hexdigest()
        
        # Verificar hash
        if hash_recebido != hash_esperado:
            return jsonify({
                "status": "erro",
                "msg": "Hash inválido"
            }), 403
        
        # Verificar Telegram ID
        if str(licenca['telegram_id']) != str(telegram_id):
            return jsonify({
                "status": "erro", 
                "msg": "Telegram ID não vinculado"
            }), 403
        
        # TUDO OK! Retornar licença válida
        resposta = f"1|{licenca['plano']}|{licenca['validade_dias']}|token-{int(time.time())}|{timestamp}|check"
        
        return resposta, 200
        
    except Exception as e:
        return jsonify({
            "status": "erro",
            "msg": f"Erro interno: {str(e)}"
        }), 500

@app.route('/health')
def health():
    """Health check simples"""
    return jsonify({"status": "healthy"})

@app.route('/diagnostico')
def diagnostico():
    """Diagnóstico básico"""
    return jsonify({
        "status": "online",
        "licencas_cadastradas": len(LICENCAS),
        "chave_configurada": CHAVE_FIXA[:10] + "...",
        "tempo_servidor": time.time()
    })

# =============================================
# INICIAR SERVIDOR
# =============================================

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
