# app.py CORRIGIDO (servidor dinâmico)
from flask import Flask, request, jsonify
import hashlib
import time
from datetime import datetime
import json
import os

app = Flask(__name__)

# =============================================
# CONFIGURAÇÕES DINÂMICAS
# =============================================

CHAVE_FIXA = "T3l3gr@m-L1c3nc3-S3cr3tK3y-33614184!2024"

# ARQUIVO PARA ARMAZENAR LICENÇAS DINAMICAMENTE
LICENCAS_FILE = "licencas.json"

def carregar_licencas():
    """Carrega licenças do arquivo JSON"""
    try:
        if os.path.exists(LICENCAS_FILE):
            with open(LICENCAS_FILE, 'r') as f:
                return json.load(f)
    except:
        pass
    return {}

def salvar_licencas(licencas):
    """Salva licenças no arquivo JSON"""
    try:
        with open(LICENCAS_FILE, 'w') as f:
            json.dump(licencas, f, indent=2)
        return True
    except:
        return False

# Carregar licenças existentes
LICENCAS = carregar_licencas()

# =============================================
# ENDPOINTS ADMIN (para você adicionar licenças)
# =============================================

@app.route('/admin/adicionar_licenca', methods=['POST'])
def adicionar_licenca():
    """ENDPOINT PARA VOCÊ ADICIONAR LICENÇAS"""
    try:
        dados = request.json
        
        # Verificar senha de admin (adicione uma senha forte!)
        senha_admin = dados.get('senha_admin')
        if senha_admin != "SUA_SENHA_FORTE_AQUI":  # MUDE ISSO!
            return jsonify({"erro": "Acesso negado"}), 403
        
        licenca_id = dados.get('licenca_id')
        telegram_id = dados.get('telegram_id')
        plano = dados.get('plano', 'P1')
        validade_dias = dados.get('validade_dias', 365)
        
        if not licenca_id or not telegram_id:
            return jsonify({"erro": "Dados incompletos"}), 400
        
        # Adicionar licença
        LICENCAS[licenca_id] = {
            "telegram_id": str(telegram_id),
            "plano": plano,
            "validade_dias": validade_dias,
            "data_criacao": int(time.time())
        }
        
        # Salvar no arquivo
        salvar_licencas(LICENCAS)
        
        return jsonify({
            "sucesso": True,
            "mensagem": f"Licença {licenca_id} adicionada para Telegram ID {telegram_id}",
            "licencas_total": len(LICENCAS)
        })
        
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@app.route('/admin/listar_licencas', methods=['GET'])
def listar_licencas():
    """Lista todas as licenças"""
    senha = request.args.get('senha')
    if senha != "SUA_SENHA_FORTE_AQUI":  # MUDE ISSO!
        return jsonify({"erro": "Acesso negado"}), 403
    
    return jsonify({
        "total": len(LICENCAS),
        "licencas": LICENCAS
    })

# =============================================
# ENDPOINT DE VERIFICAÇÃO (para os clientes)
# =============================================

@app.route('/verificar_licenca', methods=['POST'])
def verificar_licenca():
    """Verificação para os clientes (executável)"""
    try:
        dados = request.json
        
        if not dados:
            return jsonify({"erro": "Sem dados"}), 400
        
        # Dados do cliente
        api_id = dados.get('api_id') or dados.get('licenca_id', '')
        telegram_id = dados.get('telegram_id') or dados.get('vinculo_telegram', '')
        
        if not api_id or not telegram_id:
            return jsonify({"erro": "Dados incompletos"}), 400
        
        # Verificar se licença existe
        if api_id not in LICENCAS:
            return jsonify({"erro": "Licença não encontrada"}), 404
        
        licenca = LICENCAS[api_id]
        
        # Verificar hash (segurança)
        if 'hash_verificacao' in dados and 'timestamp' in dados:
            timestamp = dados.get('timestamp', 0)
            hash_recebido = dados.get('hash_verificacao', '')
            
            # Calcular hash esperado
            string_hash = f"{api_id}:{telegram_id}:{timestamp}:{CHAVE_FIXA}"
            hash_esperado = hashlib.sha256(string_hash.encode()).hexdigest()
            
            if hash_recebido != hash_esperado:
                return jsonify({"erro": "Hash inválido"}), 403
        
        # 🔥 AQUI ESTÁ A MUDANÇA PRINCIPAL 🔥
        # Verificar se o Telegram ID do cliente bate com o cadastrado
        # O cliente envia SEU Telegram ID, e nós verificamos se ele está cadastrado para aquela licença
        if str(licenca['telegram_id']) != str(telegram_id):
            return jsonify({
                "erro": "Licença não vinculada a este usuário",
                "esperado": licenca['telegram_id'],
                "recebido": telegram_id
            }), 403
        
        # TUDO OK! Retornar licença válida
        timestamp_resp = int(time.time())
        resposta = f"1|{licenca['plano']}|{licenca['validade_dias']}|token-{timestamp_resp}|{timestamp_resp}|ok"
        return resposta, 200
        
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

# =============================================
# OUTROS ENDPOINTS
# =============================================

@app.route('/')
def home():
    return jsonify({
        "status": "online",
        "servico": "Sistema de Licenciamento Dinâmico",
        "licencas_ativas": len(LICENCAS),
        "admin_endpoints": True
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
