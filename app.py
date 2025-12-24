from flask import Flask, request, jsonify
import hashlib
import time
from datetime import datetime
import base64
import os

app = Flask(__name__)

# =============================================
# CONFIGURAÇÃO EXATA DO SEU CLIENTE
# =============================================

# Chave secreta DECODIFICADA do seu cliente
SECRET_KEY = "T3l3gr@m-L1c3nc3-S3cr3tK3y-33614184!2024"

# Base64 da chave (igual ao _OFS2 do seu cliente)
SECRET_KEY_B64 = "VDNsM2dyQG0tTDFjM25jMy1TM2NyM3RLM3ktMzM2MTQxODQhMjAyNA=="

print(f"🔑 Servidor iniciado com chave: {SECRET_KEY}")

# =============================================
# BANCO DE LICENÇAS (EM MEMÓRIA)
# =============================================
licencas = {
    "DONO-2025-001": {
        "vinculo_api_id": "33614184",
        "validade_dias": 365,
        "ativo": True,
        "data_ativacao": "2024-01-01"
    },
    "DONO-2025-002": {
        "vinculo_api_id": "33614184",
        "validade_dias": 30,
        "ativo": True,
        "data_ativacao": "2024-01-15"
    },
    "TESTE-2024-001": {
        "vinculo_api_id": "33614184",
        "validade_dias": 7,
        "ativo": True,
        "data_ativacao": "2024-01-01"
    }
}

# =============================================
# FUNÇÕES AUXILIARES
# =============================================
def calcular_hash_cliente(licenca_id, api_id, timestamp):
    """Calcula hash EXATAMENTE como o cliente"""
    input_str = f"{licenca_id}:{api_id}:{timestamp}:{SECRET_KEY}"
    return hashlib.sha256(input_str.encode()).hexdigest()

# =============================================
# ROTAS
# =============================================
@app.route('/')
def home():
    return """
    <h1>✅ Servidor de Licenças - API_ID Vinculado</h1>
    <p><strong>Status:</strong> Online</p>
    <p><strong>API_ID Vinculado:</strong> 33614184</p>
    <p><strong>Licenças:</strong> DONO-2025-001, DONO-2025-002, TESTE-2024-001</p>
    <p><strong>Endpoint:</strong> POST /verificar_licenca</p>
    """

@app.route('/verificar_licenca', methods=['POST'])
def verificar_licenca():
    """Endpoint principal - formato exato do cliente"""
    try:
        # 1. Obter dados
        if not request.is_json:
            return jsonify({
                "valido": False,
                "message": "Content-Type deve ser application/json"
            }), 400
        
        dados = request.get_json()
        
        # 2. Extrair campos (nomes exatos do cliente)
        licenca_id = dados.get('api_id')
        vinculo_api_id = dados.get('telegram_id')
        timestamp = dados.get('timestamp')
        hash_recebido = dados.get('hash_verificacao')
        
        # 3. Validar campos
        if not all([licenca_id, vinculo_api_id, timestamp, hash_recebido]):
            return jsonify({
                "valido": False,
                "message": "Campos obrigatórios faltando"
            }), 400
        
        # 4. Verificar se licença existe
        if licenca_id not in licencas:
            return jsonify({
                "valido": False,
                "message": "Licença não encontrada"
            }), 404
        
        licenca = licencas[licenca_id]
        
        # 5. Verificar se está ativa
        if not licenca.get('ativo', True):
            return jsonify({
                "valido": False,
                "message": "Licença desativada"
            }), 403
        
        # 6. Verificar vínculo API_ID
        if str(licenca['vinculo_api_id']) != str(vinculo_api_id):
            return jsonify({
                "valido": False,
                "message": f"API_ID não vinculado. Esperado: {licenca['vinculo_api_id']}"
            }), 403
        
        # 7. Calcular e verificar hash
        hash_calculado = calcular_hash_cliente(licenca_id, vinculo_api_id, timestamp)
        
        if hash_recebido != hash_calculado:
            return jsonify({
                "valido": False,
                "message": "Falha na verificação de segurança",
                "hash_calculado": hash_calculado,
                "hash_recebido": hash_recebido
            }), 403
        
        # 8. Calcular dias restantes
        data_ativacao = datetime.strptime(licenca['data_ativacao'], '%Y-%m-%d')
        dias_passados = (datetime.now() - data_ativacao).days
        dias_restantes = licenca['validade_dias'] - dias_passados
        
        if dias_restantes <= 0:
            return jsonify({
                "valido": False,
                "message": "Licença expirada"
            }), 403
        
        # 9. Retornar sucesso
        return jsonify({
            "valido": True,
            "message": f"✅ Licença válida! ({dias_restantes} dias restantes)",
            "licenca_id": licenca_id,
            "vinculo_api_id": vinculo_api_id,
            "dias_restantes": dias_restantes,
            "timestamp": int(time.time())
        })
        
    except Exception as e:
        return jsonify({
            "valido": False,
            "message": f"Erro interno: {str(e)}"
        }), 500

@app.route('/status', methods=['GET'])
def status():
    """Endpoint de status"""
    return jsonify({
        "status": "online",
        "servidor": "servidor-licenca-fix",
        "versao": "2.0-fix",
        "api_id_vinculado": "33614184",
        "licencas_ativas": len([l for l in licencas.values() if l.get('ativo', True)]),
        "total_licencas": len(licencas),
        "timestamp": int(time.time())
    })

@app.route('/debug_hash', methods=['GET'])
def debug_hash():
    """Debug: mostra como calcular o hash"""
    licenca_id = request.args.get('licenca_id', 'DONO-2025-001')
    api_id = request.args.get('api_id', '33614184')
    timestamp = request.args.get('timestamp', str(int(time.time())))
    
    hash_val = calcular_hash_cliente(licenca_id, api_id, timestamp)
    
    return jsonify({
        "entrada": f"{licenca_id}:{api_id}:{timestamp}:{SECRET_KEY}",
        "hash_sha256": hash_val,
        "exemplo_json": {
            "api_id": licenca_id,
            "telegram_id": api_id,
            "timestamp": timestamp,
            "hash_verificacao": hash_val
        }
    })

# =============================================
# INICIALIZAÇÃO
# =============================================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
