# servidor_licenca.py - Sistema de Licenciamento com Vínculo Telegram
from flask import Flask, request, jsonify
import hashlib
import time
import os
from datetime import datetime, timedelta

app = Flask(__name__)

# Configurações de segurança (usar variáveis de ambiente no Render)
CHAVE_SECRETA_SERVIDOR = os.environ.get('CHAVE_SECRETA', 'CHAVE_PADRAO_SEGURA_ALTERE_NO_RENDER')
INTERNAL_SECRET = os.environ.get('INTERNAL_SECRET', 'INTERNA_PARA_PRODUCAO_ALTERE_NO_RENDER')

# Banco de dados SIMULADO (substitua por real)
# SEU ID DO TELEGRAM: 33614184
licencas_db = {
    "33614184": {  # API_ID do usuário (SEU ID DO TELEGRAM)
        "telegram_id": "33614184",  # ID único do Telegram (@username ou 5511999999999)
        "validade": "2024-12-31",
        "plano": "premium",
        "ultima_verificacao": None
    },
    "27539672": {  # Exemplo de outro usuário
        "telegram_id": "user123456",  # ID único do Telegram
        "validade": "2024-10-31",
        "plano": "basico",
        "ultima_verificacao": None
    }
}

@app.route('/verificar_licenca', methods=['POST'])
def verificar_licenca():
    """Versão reforçada com vínculo Telegram - resposta ofuscada"""
    try:
        dados = request.json
        
        # 1. Validação básica
        required = ['api_id', 'telegram_id', 'timestamp', 'hash_verificacao']
        if not all(k in dados for k in required):
            return jsonify({"status": "erro", "msg": "Dados incompletos"}), 400
        
        # 2. Verifica timestamp (prevenção replay)
        tempo_atual = time.time()
        if abs(tempo_atual - dados['timestamp']) > 300:  # 5 minutos
            return jsonify({"status": "erro", "msg": "Timestamp inválido"}), 403
        
        # 3. Verifica hash de verificação
        hash_calculado = hashlib.sha256(
            f"{dados['api_id']}:{dados['telegram_id']}:{dados['timestamp']}:{CHAVE_SECRETA_SERVIDOR}".encode()
        ).hexdigest()
        
        if dados['hash_verificacao'] != hash_calculado:
            return jsonify({"status": "erro", "msg": "Autenticação inválida"}), 403
        
        # 4. Verifica licença no banco
        api_id = str(dados['api_id'])
        if api_id not in licencas_db:
            return jsonify({"status": "erro", "msg": "Licença não encontrada"}), 404
        
        licenca = licencas_db[api_id]
        
        # 5. VERIFICAÇÃO CRÍTICA: Telegram ID corresponde?
        if licenca['telegram_id'] != dados['telegram_id']:
            # Registra tentativa de uso com ID diferente
            registrar_suspeita(api_id, dados['telegram_id'])
            return jsonify({
                "status": "erro", 
                "msg": "Vínculo inválido",
                "codigo": "TELEGRAM_MISMATCH"
            }), 403
        
        # 6. Verifica validade
        if datetime.now() > datetime.strptime(licenca['validade'], '%Y-%m-%d'):
            return jsonify({"status": "erro", "msg": "Licença expirada"}), 403
        
        # 7. Atualiza último acesso
        licenca['ultima_verificacao'] = datetime.now().isoformat()
        
        # 8. Resposta OFUSCADA (padrão específico)
        resposta = gerar_resposta_ofuscada(api_id, licenca)
        
        return resposta, 200
        
    except Exception as e:
        return jsonify({"status": "erro", "msg": f"Erro interno: {str(e)[:50]}"}), 500

def gerar_resposta_ofuscada(api_id, licenca):
    """Gera resposta em formato específico que só seu cliente entende"""
    
    # Códigos secretos para tipos de resposta
    codigos = {
        "premium": "P1",
        "basico": "B2",
        "expiracao_proxima": "W3"
    }
    
    # Calcula dias restantes
    data_validade = datetime.strptime(licenca['validade'], '%Y-%m-%d')
    dias_restantes = (data_validade - datetime.now()).days
    
    # Gera token de sessão único
    token_sessao = hashlib.sha256(
        f"{api_id}:{datetime.now().timestamp()}:SESSAO_TOKEN".encode()
    ).hexdigest()[:16]
    
    # Formato ofuscado: STATUS|CODIGO_PLANO|DIAS|TOKEN|CHECKSUM
    codigo_plano = codigos.get(licenca['plano'], "U0")
    status = "1" if dias_restantes > 0 else "0"
    
    payload = f"{status}|{codigo_plano}|{dias_restantes}|{token_sessao}"
    
    # Checksum interno
    checksum = hashlib.md5(f"{payload}:{INTERNAL_SECRET}".encode()).hexdigest()[:8]
    
    return f"{payload}|{checksum}"

def registrar_suspeita(api_id, telegram_id_tentado):
    """Registra tentativa suspeita para análise"""
    try:
        with open('suspeitas.log', 'a') as f:
            f.write(f"{datetime.now()}: API_ID={api_id} tentou com Telegram_ID={telegram_id_tentado}\n")
    except:
        pass

# Endpoint de teste para verificar se o servidor está online
@app.route('/')
def index():
    return jsonify({
        "status": "online",
        "servico": "Sistema de Licenciamento com Vínculo Telegram",
        "versao": "2.0",
        "autor": "ID Telegram: 33614184",
        "endpoints": {
            "verificar_licenca": "POST /verificar_licenca"
        }
    })

# Endpoint de saúde do servidor
@app.route('/health')
def health_check():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "licencas_cadastradas": len(licencas_db)
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
