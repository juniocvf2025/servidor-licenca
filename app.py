from flask import Flask, request, jsonify, render_template
import hashlib
import time
from datetime import datetime, timedelta
import json
import os

app = Flask(__name__)

# =============================================
# BASE DE DADOS DE LICENÇAS (EM MEMÓRIA)
# =============================================
licencas_validas = {
    "DONO-2025-001": {
        "api_id_vinculado": "33614184",  # API_ID vinculado a esta licença
        "validade_dias": 3365,
        "ativo": True,
        "data_ativacao": "2025-01-01",
        "ultima_verificacao": None
    },
    "DONO-2025-002": {
        "api_id_vinculado": "33614184",  # Mesmo API_ID pode ter múltiplas licenças
        "validade_dias": 30,
        "ativo": True,
        "data_ativacao": "2024-01-15",
        "ultima_verificacao": None
    },
    "TESTE-2024-001": {
        "api_id_vinculado": "33614184",
        "validade_dias": 7,
        "ativo": True,
        "data_ativacao": "2024-01-01",
        "ultima_verificacao": None
    }
}

# Chave secreta para validação (deve ser a mesma usada no cliente)
SECRET_KEY = "TDNsM2dyQG0tTDFjM25jMy1TM2NyM3RLM3ktMzM2MTQxODQhMjAyNA=="

# =============================================
# ROTAS DO SERVIDOR
# =============================================

@app.route('/')
def index():
    """Página inicial do servidor de licenças"""
    return render_template('index.html', total_licencas=len(licencas_validas))

@app.route('/verificar_licenca', methods=['POST'])
def verificar_licenca():
    """Endpoint principal para verificação de licenças"""
    try:
        # Obter dados da requisição
        dados = request.get_json()
        
        if not dados:
            return jsonify({
                "valido": False,
                "message": "Dados inválidos",
                "erro": "JSON inválido"
            }), 400
        
        # Extrair campos
        licenca_id = dados.get('api_id')  # campo 'api_id' no cliente
        api_id_vinculado = dados.get('telegram_id')  # campo 'telegram_id' no cliente
        timestamp = dados.get('timestamp')
        hash_recebido = dados.get('hash_verificacao')
        
        # Verificar campos obrigatórios
        if not all([licenca_id, api_id_vinculado, timestamp, hash_recebido]):
            return jsonify({
                "valido": False,
                "message": "Campos obrigatórios faltando",
                "erro": "Faltam parâmetros"
            }), 400
        
        # 1. Verificar se a licença existe
        if licenca_id not in licencas_validas:
            return jsonify({
                "valido": False,
                "message": "Licença não encontrada",
                "erro": "ID_licenca_inexistente"
            }), 404
        
        licenca = licencas_validas[licenca_id]
        
        # 2. Verificar se a licença está ativa
        if not licenca.get('ativo', True):
            return jsonify({
                "valido": False,
                "message": "Licença desativada",
                "erro": "Licenca_desativada"
            }), 403
        
        # 3. Verificar vínculo do API_ID
        if str(licenca['api_id_vinculado']) != str(api_id_vinculado):
            return jsonify({
                "valido": False,
                "message": "API_ID não vinculado a esta licença",
                "erro": "API_ID_nao_vinculado"
            }), 403
        
        # 4. Verificar validade (em dias)
        data_ativacao = datetime.strptime(licenca['data_ativacao'], '%Y-%m-%d')
        dias_passados = (datetime.now() - data_ativacao).days
        dias_restantes = licenca['validade_dias'] - dias_passados
        
        if dias_restantes <= 0:
            return jsonify({
                "valido": False,
                "message": "Licença expirada",
                "erro": "Licenca_expirada",
                "dias_restantes": 0
            }), 403
        
        # 5. Verificar hash de segurança
        # O cliente deve calcular: hash = SHA256(licenca_id:api_id_vinculado:timestamp:SECRET_KEY)
        hash_calculado = hashlib.sha256(
            f"{licenca_id}:{api_id_vinculado}:{timestamp}:{SECRET_KEY}".encode()
        ).hexdigest()
        
        if hash_recebido != hash_calculado:
            return jsonify({
                "valido": False,
                "message": "Falha na verificação de segurança",
                "erro": "Hash_invalido"
            }), 403
        
        # 6. Verificar timestamp (não muito antigo)
        tempo_atual = int(time.time())
        tempo_requisicao = int(timestamp)
        
        if abs(tempo_atual - tempo_requisicao) > 300:  # 5 minutos de tolerância
            return jsonify({
                "valido": False,
                "message": "Timestamp expirado",
                "erro": "Timestamp_expirado"
            }), 403
        
        # 7. Atualizar última verificação
        licenca['ultima_verificacao'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 8. Retornar sucesso
        return jsonify({
            "valido": True,
            "message": f"Licença válida! {dias_restantes} dias restantes",
            "dias_restantes": dias_restantes,
            "licenca_id": licenca_id,
            "api_id_vinculado": api_id_vinculado,
            "validade_dias": licenca['validade_dias'],
            "timestamp": tempo_atual
        }), 200
        
    except Exception as e:
        return jsonify({
            "valido": False,
            "message": f"Erro interno: {str(e)}",
            "erro": "erro_interno"
        }), 500

@app.route('/admin/licencas', methods=['GET'])
def listar_licencas():
    """Endpoint administrativo para listar todas as licenças"""
    # Em produção, adicionar autenticação aqui
    return jsonify({
        "total_licencas": len(licencas_validas),
        "licencas": licencas_validas
    }), 200

@app.route('/admin/licenca/<licenca_id>', methods=['GET', 'POST', 'DELETE'])
def gerenciar_licenca(licenca_id):
    """Endpoint administrativo para gerenciar licenças"""
    if request.method == 'GET':
        if licenca_id in licencas_validas:
            return jsonify({
                "licenca": licencas_validas[licenca_id]
            }), 200
        else:
            return jsonify({
                "erro": "Licença não encontrada"
            }), 404
    
    elif request.method == 'POST':
        dados = request.get_json()
        
        # Validar dados
        campos_obrigatorios = ['api_id_vinculado', 'validade_dias']
        if not all(campo in dados for campo in campos_obrigatorios):
            return jsonify({
                "erro": "Campos obrigatórios faltando"
            }), 400
        
        # Criar/atualizar licença
        licencas_validas[licenca_id] = {
            "api_id_vinculado": dados['api_id_vinculado'],
            "validade_dias": dados['validade_dias'],
            "ativo": dados.get('ativo', True),
            "data_ativacao": dados.get('data_ativacao', datetime.now().strftime('%Y-%m-%d')),
            "ultima_verificacao": None
        }
        
        return jsonify({
            "message": f"Licença {licenca_id} atualizada/criada com sucesso",
            "licenca": licencas_validas[licenca_id]
        }), 200
    
    elif request.method == 'DELETE':
        if licenca_id in licencas_validas:
            del licencas_validas[licenca_id]
            return jsonify({
                "message": f"Licença {licenca_id} removida com sucesso"
            }), 200
        else:
            return jsonify({
                "erro": "Licença não encontrada"
            }), 404

@app.route('/status', methods=['GET'])
def status():
    """Endpoint de status do servidor"""
    return jsonify({
        "status": "online",
        "servidor": "Sistema de Licenciamento",
        "versao": "1.0",
        "data": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "licencas_ativas": len([l for l in licencas_validas.values() if l.get('ativo', True)]),
        "total_licencas": len(licencas_validas)
    }), 200

# =============================================
# TEMPLATE HTML PARA PÁGINA INICIAL
# =============================================
@app.route('/static/<path:filename>')
def static_files(filename):
    return app.send_static_file(filename)

# =============================================
# CONFIGURAÇÃO E INICIALIZAÇÃO
# =============================================

def criar_templates():
    """Cria os templates HTML necessários"""
    os.makedirs('templates', exist_ok=True)
    
    # Template index.html
    index_html = '''
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Sistema de Licenciamento</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f5f5f5;
            }
            .header {
                background-color: #0078D4;
                color: white;
                padding: 20px;
                border-radius: 10px;
                text-align: center;
                margin-bottom: 20px;
            }
            .status-card {
                background-color: white;
                border-radius: 10px;
                padding: 20px;
                margin-bottom: 20px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .endpoint {
                background-color: #f8f9fa;
                border-left: 4px solid #0078D4;
                padding: 15px;
                margin-bottom: 10px;
                border-radius: 0 5px 5px 0;
            }
            code {
                background-color: #e9ecef;
                padding: 2px 5px;
                border-radius: 3px;
                font-family: 'Courier New', monospace;
            }
            .success { color: #28a745; }
            .error { color: #dc3545; }
            .warning { color: #ffc107; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🔐 Sistema de Licenciamento</h1>
            <p>Servidor de verificação de licenças com vínculo API_ID</p>
        </div>
        
        <div class="status-card">
            <h2>📊 Status do Servidor</h2>
            <p><strong>Status:</strong> <span class="success">● Online</span></p>
            <p><strong>Licenças cadastradas:</strong> {{ total_licencas }}</p>
            <p><strong>Data/Hora:</strong> <span id="datetime"></span></p>
        </div>
        
        <div class="status-card">
            <h2>🛠️ Endpoints Disponíveis</h2>
            
            <div class="endpoint">
                <h3>POST /verificar_licenca</h3>
                <p><strong>Descrição:</strong> Verifica se uma licença é válida</p>
                <p><strong>Parâmetros (JSON):</strong></p>
                <ul>
                    <li><code>api_id</code>: ID da licença (ex: DONO-2025-001)</li>
                    <li><code>telegram_id</code>: API_ID do Telegram vinculado</li>
                    <li><code>timestamp</code>: Timestamp atual</li>
                    <li><code>hash_verificacao</code>: Hash SHA256 de verificação</li>
                </ul>
            </div>
            
            <div class="endpoint">
                <h3>GET /status</h3>
                <p><strong>Descrição:</strong> Retorna status do servidor</p>
            </div>
            
            <div class="endpoint">
                <h3>GET /admin/licencas</h3>
                <p><strong>Descrição:</strong> Lista todas as licenças (administrativo)</p>
            </div>
        </div>
        
        <div class="status-card">
            <h2>📖 Exemplo de Requisição</h2>
            <pre style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; overflow-x: auto;">
// Exemplo em Python
import requests
import hashlib
import time

licenca_id = "DONO-2025-001"
api_id_vinculado = "33614184"
timestamp = int(time.time())
secret_key = "SUA_CHAVE_SECRETA"

# Calcular hash
hash_input = f"{licenca_id}:{api_id_vinculado}:{timestamp}:{secret_key}"
hash_verificacao = hashlib.sha256(hash_input.encode()).hexdigest()

# Enviar requisição
dados = {
    "api_id": licenca_id,
    "telegram_id": api_id_vinculado,
    "timestamp": timestamp,
    "hash_verificacao": hash_verificacao
}

resposta = requests.post("http://seuservidor.com/verificar_licenca", json=dados)
print(resposta.json())</pre>
        </div>
        
        <div class="status-card">
            <h2>🔒 Segurança</h2>
            <ul>
                <li>Hash SHA256 para verificação de autenticidade</li>
                <li>Timestamp com validade de 5 minutos</li>
                <li>Vínculo obrigatório entre licença e API_ID</li>
                <li>Validade por dias configurável</li>
            </ul>
        </div>
        
        <script>
            // Atualizar data/hora
            function updateDateTime() {
                const now = new Date();
                document.getElementById('datetime').textContent = 
                    now.toLocaleString('pt-BR');
            }
            updateDateTime();
            setInterval(updateDateTime, 1000);
        </script>
    </body>
    </html>
    '''
    
    with open('templates/index.html', 'w', encoding='utf-8') as f:
        f.write(index_html)

def criar_arquivo_config():
    """Cria arquivo de configuração básico"""
    config = {
        "secret_key": "TDNsM2dyQG0tTDFjM25jMy1TM2NyM3RLM3ktMzM2MTQxODQhMjAyNA==",
        "porta": 5000,
        "host": "0.0.0.0",
        "debug": False,
        "tolerancia_timestamp": 300,
        "licencas_exemplo": {
            "DONO-2025-001": {
                "api_id_vinculado": "33614184",
                "validade_dias": 365
            }
        }
    }
    
    with open('config.json', 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4)

if __name__ == '__main__':
    # Criar templates e configurações
    criar_templates()
    criar_arquivo_config()
    
    # Configurações do servidor
    PORT = int(os.environ.get('PORT', 5000))
    HOST = os.environ.get('HOST', '0.0.0.0')
    DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    print(f"🚀 Iniciando servidor de licenciamento...")
    print(f"📡 Endpoint principal: POST {HOST}:{PORT}/verificar_licenca")
    print(f"🔗 Página web: http://{HOST}:{PORT}/")
    print(f"📊 Total de licenças: {len(licencas_validas)}")
    print(f"🔐 Chave secreta configurada: {SECRET_KEY[:10]}...")
    
    # Iniciar servidor
    app.run(host=HOST, port=PORT, debug=DEBUG)

