# servidor_licenca.py - Sistema de Licenciamento FORTIFICADO
from flask import Flask, request, jsonify
import hashlib
import time
import os
from datetime import datetime, timedelta
from functools import wraps
import threading

app = Flask(__name__)

# Configurações de segurança
CHAVE_SECRETA_SERVIDOR = os.environ.get('CHAVE_SECRETA', 'CHAVE_PADRAO_SEGURA_ALTERE_NO_RENDER')
INTERNAL_SECRET = os.environ.get('INTERNAL_SECRET', 'INTERNA_PARA_PRODUCAO_ALTERE_NO_RENDER')

# Banco de dados SIMULADO
licencas_db = {
    "TEL-33614184-PRO": {  # API_ID formatado (não seu ID Telegram)
        "telegram_id": "33614184",  # SEU ID REAL do Telegram
        "validade": "2024-12-31",
        "plano": "premium",
        "ultima_verificacao": None,
        "tentativas_falhas": 0,
        "bloqueado_ate": None
    }
}

# Sistema de proteção contra força bruta
tentativas_falhas = {}  # IP -> {contagem, primeiro_timestamp, bloqueado_ate}
bloqueios_ativos = {}   # IP -> timestamp_desbloqueio
lock = threading.Lock()  # Para thread safety

def limpar_tentativas_antigas():
    """Limpa tentativas antigas da memória"""
    agora = time.time()
    ips_para_remover = []
    
    with lock:
        for ip, dados in list(tentativas_falhas.items()):
            if agora - dados['primeiro_timestamp'] > 3600:  # 1 hora
                ips_para_remover.append(ip)
        
        for ip in ips_para_remover:
            del tentativas_falhas[ip]
            if ip in bloqueios_ativos:
                del bloqueios_ativos[ip]

def registrar_tentativa_falha(ip, api_id=None):
    """Registra tentativa falha e aplica bloqueio se necessário"""
    agora = time.time()
    
    with lock:
        # Limpa tentativas antigas primeiro
        limpar_tentativas_antigas()
        
        # Verifica se IP já está bloqueado
        if ip in bloqueios_ativos and agora < bloqueios_ativos[ip]:
            tempo_restante = int(bloqueios_ativos[ip] - agora)
            return f"IP bloqueado por {tempo_restante} segundos"
        
        # Incrementa contador de tentativas
        if ip not in tentativas_falhas:
            tentativas_falhas[ip] = {
                'contagem': 1,
                'primeiro_timestamp': agora,
                'ultima_tentativa': agora
            }
        else:
            tentativas_falhas[ip]['contagem'] += 1
            tentativas_falhas[ip]['ultima_tentativa'] = agora
        
        # Aplica bloqueios progressivos
        contagem = tentativas_falhas[ip]['contagem']
        
        if contagem >= 10:  # 10 tentativas = bloqueio de 1 hora
            bloqueios_ativos[ip] = agora + 3600
            return "Muitas tentativas falhas. IP bloqueado por 1 hora."
        
        elif contagem >= 5:  # 5 tentativas = bloqueio de 15 minutos
            bloqueios_ativos[ip] = agora + 900
            return "Muitas tentativas falhas. IP bloqueado por 15 minutos."
        
        return None

def verificar_bloqueio_ip(ip):
    """Verifica se IP está bloqueado"""
    agora = time.time()
    
    with lock:
        if ip in bloqueios_ativos and agora < bloqueios_ativos[ip]:
            tempo_restante = int(bloqueios_ativos[ip] - agora)
            return True, tempo_restante
    
    return False, 0

def verificar_bloqueio_licenca(api_id):
    """Verifica se licença está bloqueada por muitas tentativas"""
    if api_id in licencas_db:
        licenca = licencas_db[api_id]
        
        if licenca.get('bloqueado_ate'):
            if datetime.now() < licenca['bloqueado_ate']:
                tempo_restante = (licenca['bloqueado_ate'] - datetime.now()).seconds
                return True, tempo_restante
        
        # Bloqueia licença se muitas tentativas falhas
        if licenca.get('tentativas_falhas', 0) >= 5:
            licenca['bloqueado_ate'] = datetime.now() + timedelta(minutes=30)
            return True, 1800
    
    return False, 0

# Decorator para proteção de endpoints
def proteger_endpoint(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Obtém IP do cliente
        if request.headers.get('X-Forwarded-For'):
            ip = request.headers.get('X-Forwarded-For').split(',')[0].strip()
        else:
            ip = request.remote_addr
        
        # Verifica bloqueio de IP
        bloqueado, tempo = verificar_bloqueio_ip(ip)
        if bloqueado:
            return jsonify({
                "status": "erro",
                "msg": f"IP temporariamente bloqueado. Tente novamente em {tempo} segundos.",
                "codigo": "IP_BLOQUEADO"
            }), 429
        
        # Continua com a função original
        return f(*args, **kwargs)
    
    return decorated_function

@app.route('/verificar_licenca', methods=['POST'])
@proteger_endpoint
def verificar_licenca():
    """Versão FORTIFICADA com proteção contra força bruta"""
    try:
        dados = request.json
        
        # Obtém IP para logging
        if request.headers.get('X-Forwarded-For'):
            ip_cliente = request.headers.get('X-Forwarded-For').split(',')[0].strip()
        else:
            ip_cliente = request.remote_addr
        
        # 1. Validação básica
        required = ['api_id', 'telegram_id', 'timestamp', 'hash_verificacao']
        if not all(k in dados for k in required):
            # Registra tentativa maliciosa
            registrar_tentativa_falha(ip_cliente)
            return jsonify({"status": "erro", "msg": "Dados incompletos"}), 400
        
        # 2. Verifica timestamp (prevenção replay)
        tempo_atual = time.time()
        if abs(tempo_atual - dados['timestamp']) > 300:  # 5 minutos
            registrar_tentativa_falha(ip_cliente, dados.get('api_id'))
            return jsonify({"status": "erro", "msg": "Timestamp inválido"}), 403
        
        # 3. Verifica hash de verificação
        hash_calculado = hashlib.sha256(
            f"{dados['api_id']}:{dados['telegram_id']}:{dados['timestamp']}:{CHAVE_SECRETA_SERVIDOR}".encode()
        ).hexdigest()
        
        if dados['hash_verificacao'] != hash_calculado:
            # Hash inválido - possível ataque
            registrar_tentativa_falha(ip_cliente, dados.get('api_id'))
            
            # Incrementa tentativas na licença
            api_id = str(dados['api_id'])
            if api_id in licencas_db:
                licencas_db[api_id]['tentativas_falhas'] = licencas_db[api_id].get('tentativas_falhas', 0) + 1
            
            return jsonify({
                "status": "erro", 
                "msg": "Autenticação inválida",
                "codigo": "HASH_INVALIDO"
            }), 403
        
        # 4. Verifica bloqueio da licença
        api_id = str(dados['api_id'])
        bloqueado, tempo = verificar_bloqueio_licenca(api_id)
        if bloqueado:
            return jsonify({
                "status": "erro",
                "msg": f"Licensa temporariamente bloqueada. Tente novamente em {tempo} segundos.",
                "codigo": "LICENCA_BLOQUEADA"
            }), 429
        
        # 5. Verifica se licença existe
        if api_id not in licencas_db:
            registrar_tentativa_falha(ip_cliente, api_id)
            return jsonify({"status": "erro", "msg": "Licença não encontrada"}), 404
        
        licenca = licencas_db[api_id]
        
        # 6. VERIFICAÇÃO CRÍTICA: Telegram ID corresponde?
        if licenca['telegram_id'] != dados['telegram_id']:
            # Tentativa de uso com ID diferente - ALTO RISCO
            registrar_tentativa_falha(ip_cliente, api_id)
            licenca['tentativas_falhas'] = licenca.get('tentativas_falhas', 0) + 1
            
            # Registra tentativa suspeita
            registrar_suspeita(api_id, dados['telegram_id'], ip_cliente)
            
            # Bloqueia após 3 tentativas com ID errado
            if licenca.get('tentativas_falhas', 0) >= 3:
                licenca['bloqueado_ate'] = datetime.now() + timedelta(hours=1)
            
            return jsonify({
                "status": "erro", 
                "msg": "Vínculo inválido",
                "codigo": "TELEGRAM_MISMATCH"
            }), 403
        
        # 7. Verifica validade
        if datetime.now() > datetime.strptime(licenca['validade'], '%Y-%m-%d'):
            return jsonify({"status": "erro", "msg": "Licença expirada"}), 403
        
        # 8. RESET das tentativas falhas (sucesso!)
        licenca['tentativas_falhas'] = 0
        licenca['bloqueado_ate'] = None
        licenca['ultima_verificacao'] = datetime.now().isoformat()
        
        # 9. Resposta OFUSCADA
        resposta = gerar_resposta_ofuscada(api_id, licenca)
        
        # 10. Log de acesso bem-sucedido
        registrar_acesso_valido(api_id, ip_cliente)
        
        return resposta, 200
        
    except Exception as e:
        return jsonify({"status": "erro", "msg": f"Erro interno: {str(e)[:50]}"}), 500

def gerar_resposta_ofuscada(api_id, licenca):
    """Gera resposta em formato específico que só seu cliente entende"""
    
    codigos = {
        "premium": "P1",
        "basico": "B2",
        "expiracao_proxima": "W3"
    }
    
    data_validade = datetime.strptime(licenca['validade'], '%Y-%m-%d')
    dias_restantes = (data_validade - datetime.now()).days
    
    # Token de sessão único com timestamp
    timestamp_atual = int(time.time())
    token_sessao = hashlib.sha256(
        f"{api_id}:{timestamp_atual}:{CHAVE_SECRETA_SERVIDOR}:SESSAO".encode()
    ).hexdigest()[:16]
    
    # Formato ofuscado: STATUS|CODIGO_PLANO|DIAS|TOKEN|TIMESTAMP|CHECKSUM
    codigo_plano = codigos.get(licenca['plano'], "U0")
    status = "1" if dias_restantes > 0 else "0"
    
    payload = f"{status}|{codigo_plano}|{dias_restantes}|{token_sessao}|{timestamp_atual}"
    
    checksum = hashlib.md5(f"{payload}:{INTERNAL_SECRET}:{timestamp_atual}".encode()).hexdigest()[:8]
    
    return f"{payload}|{checksum}"

def registrar_suspeita(api_id, telegram_id_tentado, ip_cliente):
    """Registra tentativa suspeita para análise"""
    try:
        with open('suspeitas.log', 'a') as f:
            f.write(f"{datetime.now()}: SUSPEITA - API_ID={api_id} usou Telegram_ID={telegram_id_tentado} IP={ip_cliente}\n")
    except:
        pass

def registrar_acesso_valido(api_id, ip_cliente):
    """Registra acesso válido para auditoria"""
    try:
        with open('acessos_validos.log', 'a') as f:
            f.write(f"{datetime.now()}: VALIDO - API_ID={api_id} IP={ip_cliente}\n")
    except:
        pass

# Endpoint de status do sistema (com proteção)
@app.route('/')
def index():
    return jsonify({
        "status": "online",
        "servico": "Sistema de Licenciamento FORTIFICADO v3.0",
        "versao": "3.0",
        "protecoes": [
            "Força bruta (IP e licença)",
            "Rate limiting inteligente",
            "Bloqueios progressivos",
            "Logs de segurança",
            "Resposta ofuscada"
        ]
    })

@app.route('/health')
def health_check():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "licencas_cadastradas": len(licencas_db),
        "ips_bloqueados": len([ip for ip, tempo in bloqueios_ativos.items() if time.time() < tempo])
    })

# Endpoint ADMIN para ver tentativas (protegido por IP)
@app.route('/admin/tentativas')
def admin_tentativas():
    # Proteção básica - só permite IPs específicos
    ip_permitidos = ['127.0.0.1']  # Adicione seu IP aqui
    
    if request.headers.get('X-Forwarded-For'):
        ip = request.headers.get('X-Forwarded-For').split(',')[0].strip()
    else:
        ip = request.remote_addr
    
    if ip not in ip_permitidos:
        return jsonify({"status": "erro", "msg": "Acesso não autorizado"}), 403
    
    with lock:
        return jsonify({
            "tentativas_falhas": tentativas_falhas,
            "bloqueios_ativos": bloqueios_ativos,
            "timestamp": time.time()
        })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
