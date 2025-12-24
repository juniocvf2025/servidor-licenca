# app.py - SERVIDOR COMPLETO ATUALIZADO
from flask import Flask, request, jsonify
from flask_cors import CORS
import hashlib
import time
from datetime import datetime, timedelta
import json
import os
import secrets

app = Flask(__name__)
CORS(app)  # Permite requisições de qualquer origem

# =============================================
# CONFIGURAÇÕES
# =============================================

CHAVE_FIXA = "T3l3gr@m-L1c3nc3-S3cr3tK3y-33614184!2024"

# SENHA DE ADMIN - MUDE ESTA SENHA!
SENHA_ADMIN = "AdminSeguro@2025!"

# Arquivo para armazenar licenças
LICENCAS_FILE = "licencas.json"

def carregar_licencas():
    """Carrega licenças do arquivo JSON"""
    try:
        if os.path.exists(LICENCAS_FILE):
            with open(LICENCAS_FILE, 'r', encoding='utf-8') as f:
                licencas = json.load(f)
                print(f"📂 Licenças carregadas: {len(licencas)}")
                return licencas
    except Exception as e:
        print(f"❌ Erro ao carregar licenças: {e}")
    return {}

def salvar_licencas(licencas):
    """Salva licenças no arquivo JSON"""
    try:
        with open(LICENCAS_FILE, 'w', encoding='utf-8') as f:
            json.dump(licencas, f, indent=2, ensure_ascii=False)
        print(f"💾 Licenças salvas: {len(licencas)}")
        return True
    except Exception as e:
        print(f"❌ Erro ao salvar licenças: {e}")
        return False

# Carregar licenças existentes
LICENCAS = carregar_licencas()

# Se não tiver licenças, cria uma padrão (remova depois)
if not LICENCAS:
    LICENCAS = {
        "DONO-2025-001": {
            "telegram_id": "33614184",
            "plano": "PREMIUM",
            "validade_dias": 36500,
            "data_criacao": int(time.time()),
            "ultimo_acesso": None,
            "status": "ativa"
        }
    }
    salvar_licencas(LICENCAS)

# =============================================
# FUNÇÕES AUXILIARES
# =============================================

def calcular_hash(api_id, telegram_id, timestamp):
    """Calcula o hash SHA256 esperado"""
    string_hash = f"{api_id}:{telegram_id}:{timestamp}:{CHAVE_FIXA}"
    return hashlib.sha256(string_hash.encode()).hexdigest()

def gerar_id_licenca():
    """Gera um ID de licença único"""
    timestamp = int(time.time())
    random_part = secrets.token_hex(3).upper()
    return f"LIC-{timestamp}-{random_part}"

# =============================================
# ENDPOINTS ADMIN (PROTEGIDOS)
# =============================================

def verificar_admin():
    """Verifica se a requisição é de admin"""
    dados = request.json or request.args
    senha = dados.get('senha_admin') or dados.get('senha')
    return senha == SENHA_ADMIN

@app.route('/admin/adicionar', methods=['POST'])
def adicionar_licenca():
    """Adiciona uma nova licença"""
    try:
        if not verificar_admin():
            return jsonify({"sucesso": False, "erro": "Acesso negado"}), 403
        
        dados = request.json
        licenca_id = dados.get('licenca_id', '').strip()
        telegram_id = dados.get('telegram_id', '').strip()
        plano = dados.get('plano', 'BASICO').upper()
        validade_dias = int(dados.get('validade_dias', 30))
        
        if not licenca_id or not telegram_id:
            return jsonify({"sucesso": False, "erro": "Licença ID e Telegram ID são obrigatórios"}), 400
        
        # Gerar ID automático se não fornecido
        if licenca_id == "AUTO":
            licenca_id = gerar_id_licenca()
        
        # Verificar se já existe
        if licenca_id in LICENCAS:
            return jsonify({"sucesso": False, "erro": "Licença já existe"}), 400
        
        # Adicionar licença
        LICENCAS[licenca_id] = {
            "telegram_id": telegram_id,
            "plano": plano,
            "validade_dias": validade_dias,
            "data_criacao": int(time.time()),
            "ultimo_acesso": None,
            "status": "ativa"
        }
        
        salvar_licencas(LICENCAS)
        
        return jsonify({
            "sucesso": True,
            "mensagem": f"Licença {licenca_id} criada com sucesso!",
            "licenca_id": licenca_id,
            "detalhes": LICENCAS[licenca_id]
        })
        
    except Exception as e:
        return jsonify({"sucesso": False, "erro": str(e)}), 500

@app.route('/admin/listar', methods=['GET'])
def listar_licencas():
    """Lista todas as licenças"""
    try:
        if not verificar_admin():
            return jsonify({"sucesso": False, "erro": "Acesso negado"}), 403
        
        # Filtrar por status se fornecido
        status_filtro = request.args.get('status', '').lower()
        
        if status_filtro:
            licencas_filtradas = {
                k: v for k, v in LICENCAS.items() 
                if v.get('status', 'ativa').lower() == status_filtro
            }
            contagem = len(licencas_filtradas)
        else:
            licencas_filtradas = LICENCAS
            contagem = len(LICENCAS)
        
        return jsonify({
            "sucesso": True,
            "total": contagem,
            "licencas": licencas_filtradas
        })
        
    except Exception as e:
        return jsonify({"sucesso": False, "erro": str(e)}), 500

@app.route('/admin/remover/<licenca_id>', methods=['DELETE'])
def remover_licenca(licenca_id):
    """Remove uma licença"""
    try:
        if not verificar_admin():
            return jsonify({"sucesso": False, "erro": "Acesso negado"}), 403
        
        if licenca_id not in LICENCAS:
            return jsonify({"sucesso": False, "erro": "Licença não encontrada"}), 404
        
        # Remover licença
        licenca_removida = LICENCAS.pop(licenca_id)
        salvar_licencas(LICENCAS)
        
        return jsonify({
            "sucesso": True,
            "mensagem": f"Licença {licenca_id} removida",
            "licenca_removida": licenca_removida
        })
        
    except Exception as e:
        return jsonify({"sucesso": False, "erro": str(e)}), 500

@app.route('/admin/atualizar/<licenca_id>', methods=['PUT'])
def atualizar_licenca(licenca_id):
    """Atualiza uma licença existente"""
    try:
        if not verificar_admin():
            return jsonify({"sucesso": False, "erro": "Acesso negado"}), 403
        
        if licenca_id not in LICENCAS:
            return jsonify({"sucesso": False, "erro": "Licença não encontrada"}), 404
        
        dados = request.json
        
        # Atualizar campos permitidos
        if 'telegram_id' in dados:
            LICENCAS[licenca_id]['telegram_id'] = dados['telegram_id'].strip()
        
        if 'plano' in dados:
            LICENCAS[licenca_id]['plano'] = dados['plano'].upper()
        
        if 'validade_dias' in dados:
            LICENCAS[licenca_id]['validade_dias'] = int(dados['validade_dias'])
        
        if 'status' in dados:
            LICENCAS[licenca_id]['status'] = dados['status'].lower()
        
        salvar_licencas(LICENCAS)
        
        return jsonify({
            "sucesso": True,
            "mensagem": f"Licença {licenca_id} atualizada",
            "licenca": LICENCAS[licenca_id]
        })
        
    except Exception as e:
        return jsonify({"sucesso": False, "erro": str(e)}), 500

# =============================================
# ENDPOINT DE VERIFICAÇÃO (PARA CLIENTES)
# =============================================

@app.route('/verificar_licenca', methods=['POST', 'GET'])
def verificar_licenca():
    """Endpoint principal para verificação de licenças"""
    try:
        # Aceita tanto POST (JSON) quanto GET (parâmetros)
        if request.method == 'POST':
            dados = request.json or {}
        else:
            dados = request.args.to_dict()
        
        # Extrair dados
        api_id = dados.get('api_id') or dados.get('licenca_id') or ''
        telegram_id = dados.get('telegram_id') or dados.get('vinculo_telegram') or ''
        timestamp = dados.get('timestamp', '')
        hash_recebido = dados.get('hash_verificacao') or dados.get('hash') or ''
        
        # Debug log
        print(f"🔍 Verificação recebida:")
        print(f"   Licença ID: {api_id}")
        print(f"   Telegram ID: {telegram_id}")
        print(f"   Timestamp: {timestamp}")
        print(f"   Hash recebido: {hash_recebido[:20]}..." if hash_recebido else "   Sem hash")
        
        # Validações básicas
        if not api_id:
            return jsonify({
                "sucesso": False,
                "erro": "Licença ID não fornecido",
                "codigo": "LICENCA_INVALIDA"
            }), 400
        
        if not telegram_id:
            return jsonify({
                "sucesso": False,
                "erro": "Telegram ID não fornecido",
                "codigo": "TELEGRAM_ID_FALTANDO"
            }), 400
        
        # Verificar se licença existe
        if api_id not in LICENCAS:
            return jsonify({
                "sucesso": False,
                "erro": "Licença não encontrada",
                "codigo": "LICENCA_NAO_ENCONTRADA"
            }), 404
        
        licenca = LICENCAS[api_id]
        
        # Verificar status
        if licenca.get('status', 'ativa') != 'ativa':
            return jsonify({
                "sucesso": False,
                "erro": "Licença inativa",
                "codigo": "LICENCA_INATIVA"
            }), 403
        
        # Verificar hash se fornecido
        if hash_recebido and timestamp:
            try:
                hash_esperado = calcular_hash(api_id, telegram_id, timestamp)
                
                if hash_recebido != hash_esperado:
                    print(f"❌ Hash inválido!")
                    print(f"   Esperado: {hash_esperado}")
                    print(f"   Recebido: {hash_recebido}")
                    
                    return jsonify({
                        "sucesso": False,
                        "erro": "Hash de verificação inválido",
                        "codigo": "HASH_INVALIDO"
                    }), 403
            except Exception as hash_error:
                print(f"⚠️ Erro ao verificar hash: {hash_error}")
        
        # Verificar se Telegram ID corresponde
        if str(licenca['telegram_id']) != str(telegram_id):
            return jsonify({
                "sucesso": False,
                "erro": "Licença não vinculada a este usuário",
                "codigo": "VINCULO_INCORRETO",
                "detalhes": {
                    "esperado": licenca['telegram_id'],
                    "recebido": telegram_id
                }
            }), 403
        
        # Atualizar último acesso
        LICENCAS[api_id]['ultimo_acesso'] = int(time.time())
        salvar_licencas(LICENCAS)
        
        # Calcular data de expiração
        data_criacao = licenca.get('data_criacao', int(time.time()))
        validade_dias = licenca.get('validade_dias', 30)
        data_expiracao = data_criacao + (validade_dias * 24 * 60 * 60)
        dias_restantes = max(0, (data_expiracao - int(time.time())) // (24 * 60 * 60))
        
        # Resposta de sucesso (múltiplos formatos suportados)
        timestamp_resp = int(time.time())
        
        # Formato 1: Pipe (compatível com código antigo)
        resposta_pipe = f"1|{licenca['plano']}|{dias_restantes}|token-{timestamp_resp}|{timestamp_resp}|ok"
        
        # Formato 2: JSON completo
        resposta_json = {
            "sucesso": True,
            "licenca_id": api_id,
            "telegram_id": telegram_id,
            "plano": licenca['plano'],
            "dias_restantes": dias_restantes,
            "validade_total_dias": validade_dias,
            "data_expiracao": data_expiracao,
            "timestamp": timestamp_resp,
            "token": f"token-{timestamp_resp}",
            "mensagem": "Licença válida"
        }
        
        # Verificar qual formato o cliente prefere
        formato = dados.get('formato', 'pipe').lower()
        
        if formato == 'json' or 'application/json' in request.headers.get('Accept', ''):
            return jsonify(resposta_json), 200
        else:
            return resposta_pipe, 200
        
    except Exception as e:
        print(f"❌ Erro na verificação: {e}")
        return jsonify({
            "sucesso": False,
            "erro": "Erro interno no servidor",
            "codigo": "ERRO_INTERNO"
        }), 500

# =============================================
# ENDPOINTS PÚBLICOS
# =============================================

@app.route('/')
def home():
    """Página inicial"""
    return jsonify({
        "status": "online",
        "servico": "Sistema de Licenciamento Dinâmico",
        "versao": "2.0",
        "desenvolvedor": "Sistema de Licenças",
        "endpoints": {
            "verificacao": "/verificar_licenca",
            "admin_adicionar": "/admin/adicionar (POST)",
            "admin_listar": "/admin/listar (GET)",
            "status": "/status"
        },
        "licencas_ativas": len([l for l in LICENCAS.values() if l.get('status') == 'ativa']),
        "total_licencas": len(LICENCAS),
        "suporta_formatos": ["pipe", "json"]
    })

@app.route('/status', methods=['GET'])
def status():
    """Endpoint de status do servidor"""
    return jsonify({
        "status": "online",
        "timestamp": int(time.time()),
        "licencas_ativas": len([l for l in LICENCAS.values() if l.get('status') == 'ativa']),
        "total_licencas": len(LICENCAS),
        "uptime": "servidor ativo"
    })

@app.route('/teste', methods=['GET'])
def teste():
    """Endpoint de teste simples"""
    return jsonify({
        "mensagem": "Servidor funcionando!",
        "timestamp": int(time.time()),
        "versao": "2.0"
    })

# =============================================
# INICIALIZAÇÃO
# =============================================

if __name__ == '__main__':
    print("🚀 Servidor de Licenciamento Iniciando...")
    print(f"📊 Licenças carregadas: {len(LICENCAS)}")
    print(f"🔑 Chave de segurança: {CHAVE_FIXA[:10]}...")
    print(f"👑 Senha admin: {SENHA_ADMIN[:5]}...")
    print("=" * 50)
    print("📡 Endpoints disponíveis:")
    print("  /verificar_licenca - Verificação de licenças")
    print("  /admin/adicionar - Adicionar licença (POST)")
    print("  /admin/listar - Listar licenças (GET)")
    print("  /status - Status do servidor")
    print("=" * 50)
    
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
