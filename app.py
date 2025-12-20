# servidor_licenca.py - Sistema de Licenciamento FORTIFICADO OTIMIZADO
from flask import Flask, request, jsonify
import hashlib
import time
import os
from datetime import datetime, timedelta
from functools import wraps
import threading
import json
from collections import defaultdict
import logging
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)

# Configuração de logging (substitui writes diretos no arquivo)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Executor para operações assíncronas
executor = ThreadPoolExecutor(max_workers=4)

# Configurações de segurança
CHAVE_SECRETA_SERVIDOR = os.environ.get('CHAVE_SECRETA', 'CHAVE_PADRAO_SEGURA_ALTERE_NO_RENDER')
INTERNAL_SECRET = os.environ.get('INTERNAL_SECRET', 'INTERNA_PARA_PRODUCAO_ALTERE_NO_RENDER')

# Banco de dados SIMULADO com formato DONO-2025-XXX
licencas_db = {
    "DONO-2025-001": {  # API_ID no formato que seu executável espera
        "telegram_id": "33614184",  # SEU ID REAL do Telegram
        "validade": "3025-12-31",
        "plano": "premium",
        "ultima_verificacao": None,
        "tentativas_falhas": 0,
        "bloqueado_ate": None
    },
    "DONO-2025-002": {  # Outra licença de exemplo
        "telegram_id": "outro_usuario",
        "validade": "2024-10-31",
        "plano": "basico",
        "ultima_verificacao": None,
        "tentativas_falhas": 0,
        "bloqueado_ate": None
    }
}

# Cache para respostas frequentes
cache_respostas = {}
cache_lock = threading.Lock()
CACHE_TTL = 10  # 10 segundos

# Sistema de proteção otimizado
tentativas_falhas = defaultdict(dict)
bloqueios_ativos = {}
lock = threading.Lock()

# Cache de hash calculado para evitar recálculos
hash_cache = {}
HASH_CACHE_TTL = 300  # 5 minutos

def limpar_cache_antigo():
    """Limpa cache antigo periodicamente"""
    agora = time.time()
    with cache_lock:
        chaves_para_remover = []
        for chave, (timestamp, _) in cache_respostas.items():
            if agora - timestamp > CACHE_TTL:
                chaves_para_remover.append(chave)
        
        for chave in chaves_para_remover:
            del cache_respostas[chave]
        
        # Limpa hash cache
        chaves_hash_para_remover = []
        for chave, (timestamp, _) in hash_cache.items():
            if agora - timestamp > HASH_CACHE_TTL:
                chaves_hash_para_remover.append(chave)
        
        for chave in chaves_hash_para_remover:
            del hash_cache[chave]

def registrar_tentativa_falha_async(ip, api_id=None):
    """Registra tentativa falha de forma assíncrona"""
    executor.submit(_registrar_tentativa_falha_sync, ip, api_id)

def _registrar_tentativa_falha_sync(ip, api_id=None):
    """Implementação síncrona (executada em thread separada)"""
    agora = time.time()
    
    with lock:
        # Limpa tentativas antigas primeiro
        limpar_tentativas_antigas_sync(agora)
        
        # Incrementa contador de tentativas
        if ip not in tentativas_falhas:
            tentativas_falhas[ip] = {
                'contagem': 1,
                'primeiro_timestamp': agora,
                'ultima_tentativa': agora,
                'api_ids': set([api_id]) if api_id else set()
            }
        else:
            tentativas_falhas[ip]['contagem'] += 1
            tentativas_falhas[ip]['ultima_tentativa'] = agora
            if api_id:
                tentativas_falhas[ip]['api_ids'].add(api_id)
        
        # Aplica bloqueios progressivos
        contagem = tentativas_falhas[ip]['contagem']
        
        if contagem >= 10:
            bloqueios_ativos[ip] = agora + 3600
        elif contagem >= 5:
            bloqueios_ativos[ip] = agora + 900

def limpar_tentativas_antigas_sync(agora):
    """Versão síncrona da limpeza"""
    ips_para_remover = []
    
    for ip, dados in list(tentativas_falhas.items()):
        if agora - dados['primeiro_timestamp'] > 3600:
            ips_para_remover.append(ip)
    
    for ip in ips_para_remover:
        del tentativas_falhas[ip]
        if ip in bloqueios_ativos:
            del bloqueios_ativos[ip]

def verificar_bloqueio_ip_rapido(ip):
    """Verificação otimizada de bloqueio de IP"""
    agora = time.time()
    
    # Verificação rápida sem lock se possível
    if ip not in bloqueios_ativos:
        return False, 0
    
    with lock:
        if ip in bloqueios_ativos and agora < bloqueios_ativos[ip]:
            tempo_restante = int(bloqueios_ativos[ip] - agora)
            return True, tempo_restante
    
    return False, 0

def calcular_hash_cache(api_id, telegram_id, timestamp):
    """Calcula hash com cache para melhor performance"""
    chave = f"{api_id}:{telegram_id}:{timestamp}"
    agora = time.time()
    
    with cache_lock:
        if chave in hash_cache:
            cache_time, hash_value = hash_cache[chave]
            if agora - cache_time < HASH_CACHE_TTL:
                return hash_value
    
    # Calcula novo hash
    hash_value = hashlib.sha256(
        f"{api_id}:{telegram_id}:{timestamp}:{CHAVE_SECRETA_SERVIDOR}".encode()
    ).hexdigest()
    
    with cache_lock:
        hash_cache[chave] = (agora, hash_value)
    
    return hash_value

def gerar_resposta_ofuscada_cache(api_id, licenca):
    """Gera resposta com cache"""
    agora = time.time()
    
    # Verifica cache primeiro
    with cache_lock:
        if api_id in cache_respostas:
            cache_time, resposta = cache_respostas[api_id]
            if agora - cache_time < CACHE_TTL:
                return resposta
    
    # Gera nova resposta
    data_validade = datetime.strptime(licenca['validade'], '%Y-%m-%d')
    dias_restantes = (data_validade - datetime.now()).days
    
    # Token de sessão único com timestamp
    timestamp_atual = int(agora)
    token_sessao = hashlib.sha256(
        f"{api_id}:{timestamp_atual}:{CHAVE_SECRETA_SERVIDOR}:SESSAO".encode()
    ).hexdigest()[:16]
    
    codigos = {"premium": "P1", "basico": "B2", "expiracao_proxima": "W3"}
    codigo_plano = codigos.get(licenca['plano'], "U0")
    status = "1" if dias_restantes > 0 else "0"
    
    payload = f"{status}|{codigo_plano}|{dias_restantes}|{token_sessao}|{timestamp_atual}"
    checksum = hashlib.md5(f"{payload}:{INTERNAL_SECRET}:{timestamp_atual}".encode()).hexdigest()[:8]
    resposta = f"{payload}|{checksum}"
    
    # Armazena em cache
    with cache_lock:
        cache_respostas[api_id] = (agora, resposta)
    
    return resposta

def registrar_log_async(tipo, dados):
    """Registra log de forma assíncrona"""
    executor.submit(_registrar_log_sync, tipo, dados)

def _registrar_log_sync(tipo, dados):
    """Registra log em arquivo (thread separada)"""
    try:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if tipo == 'suspeita':
            mensagem = f"{timestamp}: SUSPEITA - {dados}\n"
            with open('suspeitas.log', 'a') as f:
                f.write(mensagem)
        elif tipo == 'acesso':
            mensagem = f"{timestamp}: VALIDO - {dados}\n"
            with open('acessos_validos.log', 'a') as f:
                f.write(mensagem)
    except Exception as e:
        logger.error(f"Erro ao registrar log: {e}")

@app.route('/verificar_licenca', methods=['POST'])
def verificar_licenca_otimizada():
    """Versão OTIMIZADA do endpoint principal"""
    try:
        dados = request.json
        
        # 1. Validação básica RÁPIDA
        required = ['api_id', 'telegram_id', 'timestamp', 'hash_verificacao']
        if not all(k in dados for k in required):
            return jsonify({"status": "erro", "msg": "Dados incompletos"}), 400
        
        # Obtém IP (apenas quando necessário)
        ip_cliente = request.remote_addr
        if request.headers.get('X-Forwarded-For'):
            ip_cliente = request.headers.get('X-Forwarded-For').split(',')[0].strip()
        
        # 2. Verificação de timestamp (rápido)
        tempo_atual = time.time()
        if abs(tempo_atual - dados['timestamp']) > 300:
            registrar_tentativa_falha_async(ip_cliente, dados.get('api_id'))
            return jsonify({"status": "erro", "msg": "Timestamp inválido"}), 403
        
        # 3. Verifica bloqueio de IP (otimizado)
        bloqueado, tempo = verificar_bloqueio_ip_rapido(ip_cliente)
        if bloqueado:
            return jsonify({
                "status": "erro",
                "msg": f"IP bloqueado. Tente novamente em {tempo} segundos.",
                "codigo": "IP_BLOQUEADO"
            }), 429
        
        # 4. Verificação de hash com CACHE
        hash_calculado = calcular_hash_cache(
            dados['api_id'], 
            dados['telegram_id'], 
            dados['timestamp']
        )
        
        if dados['hash_verificacao'] != hash_calculado:
            registrar_tentativa_falha_async(ip_cliente, dados.get('api_id'))
            return jsonify({
                "status": "erro", 
                "msg": "Autenticação inválida",
                "codigo": "HASH_INVALIDO"
            }), 403
        
        api_id = str(dados['api_id'])
        
        # 5. Verifica se licença existe (acesso rápido ao dict)
        if api_id not in licencas_db:
            registrar_tentativa_falha_async(ip_cliente, api_id)
            return jsonify({"status": "erro", "msg": "Licença não encontrada"}), 404
        
        licenca = licencas_db[api_id]
        
        # 6. VERIFICAÇÃO CRÍTICA: Telegram ID
        if licenca['telegram_id'] != dados['telegram_id']:
            # Thread separada para processamento pesado
            executor.submit(processar_erro_telegram, api_id, dados['telegram_id'], ip_cliente)
            return jsonify({
                "status": "erro", 
                "msg": "Vínculo inválido",
                "codigo": "TELEGRAM_MISMATCH"
            }), 403
        
        # 7. Verifica validade (cálculo rápido)
        data_validade = datetime.strptime(licenca['validade'], '%Y-%m-%d')
        if datetime.now() > data_validade:
            return jsonify({"status": "erro", "msg": "Licença expirada"}), 403
        
        # 8. Atualiza último acesso (operação leve)
        licenca['ultima_verificacao'] = datetime.now().isoformat()
        
        # 9. Gera resposta com CACHE
        resposta = gerar_resposta_ofuscada_cache(api_id, licenca)
        
        # 10. Log assíncrono
        registrar_log_async('acesso', f"API_ID={api_id} IP={ip_cliente}")
        
        return resposta, 200
        
    except Exception as e:
        logger.error(f"Erro em verificar_licenca: {e}")
        return jsonify({"status": "erro", "msg": "Erro interno do servidor"}), 500

def processar_erro_telegram(api_id, telegram_id_tentado, ip_cliente):
    """Processa erro de telegram_id em thread separada"""
    if api_id in licencas_db:
        licenca = licencas_db[api_id]
        
        # Incrementa contador
        telegram_errados = licenca.get('telegram_errados', 0) + 1
        licenca['telegram_errados'] = telegram_errados
        
        # Aplica bloqueio se necessário
        if telegram_errados >= 5:
            licenca['bloqueado_ate'] = datetime.now() + timedelta(hours=1)
        
        # Log assíncrono
        registrar_log_async('suspeita', 
            f"API_ID={api_id} usou Telegram_ID={telegram_id_tentado} IP={ip_cliente}")

# Endpoint para limpar cache (útil para debug)
@app.route('/admin/limpar_cache', methods=['POST'])
def limpar_cache():
    with cache_lock:
        cache_respostas.clear()
        hash_cache.clear()
    return jsonify({"status": "sucesso", "msg": "Cache limpo"})

# Restante do código mantido (endpoints /, /health, /admin/tentativas)...

if __name__ == '__main__':
    # Limpa cache periodicamente
    def limpar_cache_periodicamente():
        while True:
            time.sleep(60)
            limpar_cache_antigo()
    
    thread = threading.Thread(target=limpar_cache_periodicamente, daemon=True)
    thread.start()
    
    app.run(debug=False, host='0.0.0.0', port=5000)
