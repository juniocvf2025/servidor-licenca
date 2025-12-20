# servidor_licenca.py - Sistema de Licenciamento com DIAGNÓSTICO
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
import traceback

app = Flask(__name__)

# Configuração de logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Executor para operações assíncronas
executor = ThreadPoolExecutor(max_workers=4)

# Configurações de segurança
CHAVE_SECRETA_SERVIDOR = os.environ.get('CHAVE_SECRETA', 'CHAVE_PADRAO_SEGURA_ALTERE_NO_RENDER')
INTERNAL_SECRET = os.environ.get('INTERNAL_SECRET', 'INTERNA_PARA_PRODUCAO_ALTERE_NO_RENDER')

# Banco de dados - ESTRUTURA CORRIGIDA
try:
    # Formato garantido para evitar problemas de tipo
    licencas_db = {
        "DONO-2025-001": {
            "telegram_id": "33614184",
            "validade": "3025-12-31",
            "plano": "premium",
            "ultima_verificacao": None,
            "tentativas_falhas": 0,
            "telegram_errados": 0,
            "bloqueado_ate": None,
            "data_criacao": "2024-01-01"
        },
        "DONO-2025-002": {
            "telegram_id": "outro_usuario",
            "validade": "2024-10-31",
            "plano": "basico",
            "ultima_verificacao": None,
            "tentativas_falhas": 0,
            "telegram_errados": 0,
            "bloqueado_ate": None,
            "data_criacao": "2024-01-01"
        }
    }
    logger.info("Banco de dados de licenças carregado com sucesso")
except Exception as e:
    logger.error(f"ERRO CRÍTICO ao carregar banco de dados: {e}")
    licencas_db = {}  # Fallback vazio

# Sistema de proteção com LIMITES AJUSTADOS
tentativas_falhas = defaultdict(dict)
bloqueios_ativos = {}
lock = threading.Lock()

# Cache para performance
cache_respostas = {}
cache_lock = threading.Lock()
CACHE_TTL = 30  # 30 segundos para evitar requisições muito frequentes

# Controle de diagnóstico
diagnosticos = {
    "ultimas_requisicoes": [],
    "erros_recentes": [],
    "performance": [],
    "bloqueios_aplicados": []
}
diag_lock = threading.Lock()

def registrar_diagnostico(tipo, dados):
    """Registra eventos para diagnóstico"""
    with diag_lock:
        timestamp = datetime.now().isoformat()
        registro = {"timestamp": timestamp, "dados": dados}
        
        if tipo == "requisicao":
            diagnosticos["ultimas_requisicoes"].append(registro)
            # Mantém apenas últimos 100
            diagnosticos["ultimas_requisicoes"] = diagnosticos["ultimas_requisicoes"][-100:]
        
        elif tipo == "erro":
            diagnosticos["erros_recentes"].append(registro)
            diagnosticos["erros_recentes"] = diagnosticos["erros_recentes"][-50:]
        
        elif tipo == "bloqueio":
            diagnosticos["bloqueios_aplicados"].append(registro)
            diagnosticos["bloqueios_aplicados"] = diagnosticos["bloqueios_aplicados"][-20:]

def limpar_cache_antigo():
    """Limpa cache antigo"""
    agora = time.time()
    with cache_lock:
        chaves_para_remover = []
        for chave, (timestamp, _) in cache_respostas.items():
            if agora - timestamp > CACHE_TTL:
                chaves_para_remover.append(chave)
        
        for chave in chaves_para_remover:
            del cache_respostas[chave]

def registrar_tentativa_falha_async(ip, api_id=None):
    """Registra tentativa falha de forma assíncrona"""
    executor.submit(_registrar_tentativa_falha_sync, ip, api_id)

def _registrar_tentativa_falha_sync(ip, api_id=None):
    """Implementação síncrona"""
    try:
        agora = time.time()
        
        with lock:
            # Limpa tentativas antigas
            _limpar_tentativas_antigas(agora)
            
            # Registra tentativa
            if ip not in tentativas_falhas:
                tentativas_falhas[ip] = {
                    'contagem': 1,
                    'primeiro_timestamp': agora,
                    'ultima_tentativa': agora,
                    'api_ids': [api_id] if api_id else []
                }
            else:
                tentativas_falhas[ip]['contagem'] += 1
                tentativas_falhas[ip]['ultima_tentativa'] = agora
                if api_id and api_id not in tentativas_falhas[ip]['api_ids']:
                    tentativas_falhas[ip]['api_ids'].append(api_id)
            
            contagem = tentativas_falhas[ip]['contagem']
            
            # LIMITES MAIS FLEXÍVEIS PARA TESTE
            if contagem >= 15:  # Aumentado de 10 para 15
                bloqueios_ativos[ip] = agora + 1800  # 30 minutos (era 1 hora)
                registrar_diagnostico("bloqueio", {"ip": ip, "duracao": "30min", "tentativas": contagem})
                logger.warning(f"IP {ip} bloqueado por 30 minutos ({contagem} tentativas)")
            
            elif contagem >= 8:  # Aumentado de 5 para 8
                bloqueios_ativos[ip] = agora + 600  # 10 minutos (era 15)
                registrar_diagnostico("bloqueio", {"ip": ip, "duracao": "10min", "tentativas": contagem})
                logger.warning(f"IP {ip} bloqueado por 10 minutos ({contagem} tentativas)")
    
    except Exception as e:
        logger.error(f"Erro ao registrar tentativa falha: {e}")

def _limpar_tentativas_antigas(agora):
    """Limpa tentativas antigas"""
    try:
        ips_para_remover = []
        for ip, dados in list(tentativas_falhas.items()):
            if agora - dados['primeiro_timestamp'] > 7200:  # 2 horas
                ips_para_remover.append(ip)
        
        for ip in ips_para_remover:
            del tentativas_falhas[ip]
            if ip in bloqueios_ativos:
                del bloqueios_ativos[ip]
    
    except Exception as e:
        logger.error(f"Erro ao limpar tentativas antigas: {e}")

def verificar_bloqueio_ip(ip):
    """Verificação simplificada de bloqueio de IP"""
    agora = time.time()
    
    # Verificação rápida
    if ip not in bloqueios_ativos:
        return False, 0
    
    with lock:
        if ip in bloqueios_ativos and agora < bloqueios_ativos[ip]:
            tempo_restante = int(bloqueios_ativos[ip] - agora)
            return True, tempo_restante
    
    return False, 0

def verificar_licenca_bloqueada(api_id):
    """Verifica se licença específica está bloqueada"""
    try:
        if api_id in licencas_db:
            licenca = licencas_db[api_id]
            
            if licenca.get('bloqueado_ate'):
                if isinstance(licenca['bloqueado_ate'], str):
                    bloqueado_ate = datetime.fromisoformat(licenca['bloqueado_ate'])
                else:
                    bloqueado_ate = licenca['bloqueado_ate']
                
                if datetime.now() < bloqueado_ate:
                    tempo_restante = int((bloqueado_ate - datetime.now()).total_seconds())
                    return True, tempo_restante
        
        return False, 0
    
    except Exception as e:
        logger.error(f"Erro ao verificar bloqueio de licença {api_id}: {e}")
        return False, 0

@app.route('/verificar_licenca', methods=['POST'])
def verificar_licenca_diagnostico():
    """Endpoint principal com diagnóstico integrado"""
    inicio = time.time()
    ip_cliente = None
    api_id = None
    
    try:
        # Log da requisição recebida
        logger.info(f"Requisição POST recebida em /verificar_licenca")
        
        # 1. Validação inicial rápida
        if not request.is_json:
            registrar_diagnostico("erro", {"tipo": "not_json", "ip": request.remote_addr})
            return jsonify({
                "status": "erro", 
                "msg": "Content-Type deve ser application/json"
            }), 400
        
        dados = request.json
        logger.debug(f"Dados recebidos: {str(dados)[:200]}...")
        
        # 2. Obtém IP
        ip_cliente = request.remote_addr
        if request.headers.get('X-Forwarded-For'):
            ip_cliente = request.headers.get('X-Forwarded-For').split(',')[0].strip()
        
        logger.info(f"IP do cliente: {ip_cliente}")
        
        # 3. Valida campos obrigatórios
        required = ['api_id', 'telegram_id', 'timestamp', 'hash_verificacao']
        campos_faltando = [k for k in required if k not in dados]
        
        if campos_faltando:
            registrar_diagnostico("erro", {
                "tipo": "campos_faltando", 
                "campos": campos_faltando,
                "ip": ip_cliente
            })
            registrar_tentativa_falha_async(ip_cliente)
            return jsonify({
                "status": "erro", 
                "msg": f"Dados incompletos. Faltando: {', '.join(campos_faltando)}"
            }), 400
        
        api_id = str(dados['api_id'])
        telegram_id = str(dados['telegram_id'])
        timestamp_cliente = float(dados['timestamp'])
        
        # 4. Verifica bloqueio de IP (rápido)
        bloqueado_ip, tempo_ip = verificar_bloqueio_ip(ip_cliente)
        if bloqueado_ip:
            registrar_diagnostico("bloqueio", {
                "tipo": "ip_bloqueado",
                "ip": ip_cliente,
                "tempo_restante": tempo_ip
            })
            return jsonify({
                "status": "erro",
                "msg": f"IP bloqueado. Tente novamente em {tempo_ip} segundos.",
                "codigo": "IP_BLOQUEADO",
                "tempo_restante": tempo_ip
            }), 429
        
        # 5. Verifica timestamp (com tolerância aumentada)
        tempo_atual = time.time()
        diferenca_tempo = abs(tempo_atual - timestamp_cliente)
        
        if diferenca_tempo > 600:  # 10 minutos (era 5)
            logger.warning(f"Timestamp inválido: dif={diferenca_tempo:.1f}s, cliente={timestamp_cliente}, servidor={tempo_atual}")
            registrar_tentativa_falha_async(ip_cliente, api_id)
            return jsonify({
                "status": "erro", 
                "msg": f"Timestamp inválido. Diferença: {diferenca_tempo:.1f} segundos",
                "diferenca_tempo": diferenca_tempo
            }), 403
        
        # 6. Verifica hash
        hash_calculado = hashlib.sha256(
            f"{api_id}:{telegram_id}:{timestamp_cliente}:{CHAVE_SECRETA_SERVIDOR}".encode()
        ).hexdigest()
        
        if dados['hash_verificacao'] != hash_calculado:
            logger.warning(f"Hash inválido para API_ID: {api_id}")
            registrar_tentativa_falha_async(ip_cliente, api_id)
            registrar_diagnostico("erro", {
                "tipo": "hash_invalido",
                "api_id": api_id,
                "ip": ip_cliente
            })
            return jsonify({
                "status": "erro", 
                "msg": "Autenticação inválida",
                "codigo": "HASH_INVALIDO"
            }), 403
        
        # 7. Verifica se licença existe
        if api_id not in licencas_db:
            logger.warning(f"Licença não encontrada: {api_id}")
            registrar_tentativa_falha_async(ip_cliente, api_id)
            return jsonify({
                "status": "erro", 
                "msg": f"Licença {api_id} não encontrada",
                "codigo": "LICENCA_NAO_ENCONTRADA"
            }), 404
        
        licenca = licencas_db[api_id]
        
        # 8. Verifica bloqueio da licença
        bloqueado_licenca, tempo_licenca = verificar_licenca_bloqueada(api_id)
        if bloqueado_licenca:
            logger.warning(f"Licença {api_id} bloqueada por {tempo_licenca}s")
            return jsonify({
                "status": "erro",
                "msg": f"Licença bloqueada. Tente novamente em {tempo_licenca} segundos.",
                "codigo": "LICENCA_BLOQUEADA",
                "tempo_restante": tempo_licenca
            }), 429
        
        # 9. Verifica Telegram ID
        if str(licenca['telegram_id']) != telegram_id:
            logger.warning(f"Telegram ID não corresponde: esperado={licenca['telegram_id']}, recebido={telegram_id}")
            
            # Atualiza contador em thread separada
            executor.submit(_processar_telegram_errado, api_id, telegram_id, ip_cliente)
            
            return jsonify({
                "status": "erro", 
                "msg": "Vínculo inválido",
                "codigo": "TELEGRAM_MISMATCH"
            }), 403
        
        # 10. Verifica validade
        try:
            data_validade = datetime.strptime(str(licenca['validade']), '%Y-%m-%d')
            if datetime.now() > data_validade:
                logger.warning(f"Licença {api_id} expirada em {licenca['validade']}")
                return jsonify({
                    "status": "erro", 
                    "msg": f"Licença expirada em {licenca['validade']}",
                    "codigo": "LICENCA_EXPIRADA"
                }), 403
        except Exception as e:
            logger.error(f"Erro ao verificar validade da licença {api_id}: {e}")
            return jsonify({
                "status": "erro", 
                "msg": "Erro ao verificar validade da licença",
                "codigo": "ERRO_VALIDADE"
            }), 500
        
        # 11. ATUALIZAÇÃO RÁPIDA (sem operações pesadas)
        licenca['ultima_verificacao'] = datetime.now().isoformat()
        
        # Reduz contadores em caso de sucesso
        if licenca.get('tentativas_falhas', 0) > 0:
            licenca['tentativas_falhas'] = max(0, licenca['tentativas_falhas'] - 1)
        
        # 12. Gera resposta OFUSCADA
        data_validade = datetime.strptime(str(licenca['validade']), '%Y-%m-%d')
        dias_restantes = (data_validade - datetime.now()).days
        
        timestamp_atual = int(time.time())
        token_sessao = hashlib.sha256(
            f"{api_id}:{timestamp_atual}:{CHAVE_SECRETA_SERVIDOR}:SESSAO".encode()
        ).hexdigest()[:16]
        
        codigos = {"premium": "P1", "basico": "B2"}
        codigo_plano = codigos.get(licenca['plano'], "U0")
        status = "1" if dias_restantes > 0 else "0"
        
        payload = f"{status}|{codigo_plano}|{dias_restantes}|{token_sessao}|{timestamp_atual}"
        checksum = hashlib.md5(f"{payload}:{INTERNAL_SECRET}:{timestamp_atual}".encode()).hexdigest()[:8]
        resposta = f"{payload}|{checksum}"
        
        # 13. Log de sucesso (assíncrono)
        executor.submit(_log_acesso_valido, api_id, ip_cliente, dias_restantes)
        
        tempo_total = time.time() - inicio
        
        registrar_diagnostico("requisicao", {
            "api_id": api_id,
            "ip": ip_cliente,
            "status": "sucesso",
            "tempo_ms": round(tempo_total * 1000, 2)
        })
        
        logger.info(f"Licença {api_id} validada com sucesso em {tempo_total*1000:.2f}ms")
        
        return resposta, 200
        
    except Exception as e:
        tempo_total = time.time() - inicio
        logger.error(f"ERRO CRÍTICO em verificar_licenca: {e}")
        logger.error(traceback.format_exc())
        
        registrar_diagnostico("erro", {
            "tipo": "excecao_nao_tratada",
            "erro": str(e),
            "ip": ip_cliente,
            "api_id": api_id,
            "tempo_ms": round(tempo_total * 1000, 2),
            "traceback": traceback.format_exc()[:500]
        })
        
        return jsonify({
            "status": "erro", 
            "msg": "Erro interno do servidor",
            "codigo": "ERRO_INTERNO",
            "tempo_processamento": round(tempo_total, 2)
        }), 500

def _processar_telegram_errado(api_id, telegram_id_tentado, ip_cliente):
    """Processa erro de Telegram ID em thread separada"""
    try:
        if api_id in licencas_db:
            licenca = licencas_db[api_id]
            
            # Incrementa contador
            telegram_errados = licenca.get('telegram_errados', 0) + 1
            licenca['telegram_errados'] = telegram_errados
            
            # Bloqueio mais brando para testes
            if telegram_errados >= 10:  # Aumentado de 5 para 10
                licenca['bloqueado_ate'] = datetime.now() + timedelta(minutes=30)
                logger.warning(f"Licença {api_id} bloqueada por 30 minutos (10 tentativas com Telegram ID errado)")
            
            # Log
            with open('suspeitas.log', 'a') as f:
                f.write(f"{datetime.now()}: SUSPEITA - API_ID={api_id} tentou Telegram_ID={telegram_id_tentado} IP={ip_cliente} (erro {telegram_errados})\n")
    
    except Exception as e:
        logger.error(f"Erro ao processar telegram errado: {e}")

def _log_acesso_valido(api_id, ip_cliente, dias_restantes):
    """Log de acesso válido em thread separada"""
    try:
        with open('acessos_validos.log', 'a') as f:
            f.write(f"{datetime.now()}: VALIDO - API_ID={api_id} IP={ip_cliente} Dias_restantes={dias_restantes}\n")
    except Exception as e:
        logger.error(f"Erro ao logar acesso válido: {e}")

# Endpoint de diagnóstico
@app.route('/diagnostico', methods=['GET'])
def endpoint_diagnostico():
    """Endpoint para diagnóstico do sistema"""
    with diag_lock:
        return jsonify({
            "status": "online",
            "timestamp": datetime.now().isoformat(),
            "licencas_cadastradas": len(licencas_db),
            "cache_tamanho": len(cache_respostas),
            "bloqueios_ativos": len([ip for ip, t in bloqueios_ativos.items() if time.time() < t]),
            "tentativas_registradas": len(tentativas_falhas),
            "ultimas_requisicoes": diagnosticos.get("ultimas_requisicoes", [])[-5:],
            "erros_recentes": diagnosticos.get("erros_recentes", [])[-5:],
            "bloqueios_aplicados": diagnosticos.get("bloqueios_aplicados", [])[-5:],
            "ambiente": {
                "python_version": os.sys.version,
                "servidor": "Flask",
                "debug": app.debug
            }
        })

# Endpoint para testar licença específica (útil para debug)
@app.route('/testar_licenca/<api_id>', methods=['GET'])
def testar_licenca(api_id):
    """Testa se uma licença específica existe e está válida"""
    if api_id in licencas_db:
        licenca = licencas_db[api_id]
        return jsonify({
            "status": "encontrada",
            "api_id": api_id,
            "telegram_id": licenca['telegram_id'],
            "validade": licenca['validade'],
            "plano": licenca['plano'],
            "dias_restantes": (datetime.strptime(licenca['validade'], '%Y-%m-%d') - datetime.now()).days,
            "bloqueado": licenca.get('bloqueado_ate') is not None,
            "bloqueado_ate": licenca.get('bloqueado_ate'),
            "tentativas_falhas": licenca.get('tentativas_falhas', 0),
            "telegram_errados": licenca.get('telegram_errados', 0)
        })
    else:
        return jsonify({
            "status": "nao_encontrada",
            "api_id": api_id,
            "msg": "Licença não encontrada no banco de dados"
        }), 404

# Endpoint para resetar proteções (APENAS PARA DESENVOLVIMENTO)
@app.route('/admin/reset_protecoes', methods=['POST'])
def reset_protecoes():
    """Reseta sistema de proteção (CUIDADO: usar apenas em dev)"""
    with lock:
        tentativas_falhas.clear()
        bloqueios_ativos.clear()
    
    # Limpa bloqueios de licenças
    for licenca in licencas_db.values():
        licenca['bloqueado_ate'] = None
        licenca['tentativas_falhas'] = 0
        licenca['telegram_errados'] = 0
    
    logger.warning("Sistema de proteções resetado manualmente")
    
    return jsonify({
        "status": "sucesso",
        "msg": "Sistema de proteções resetado",
        "tentativas_limpas": True,
        "bloqueios_limpos": True
    })

# Endpoints originais mantidos
@app.route('/')
def index():
    return jsonify({
        "status": "online",
        "servico": "Sistema de Licenciamento v3.1 (DIAGNÓSTICO)",
        "versao": "3.1",
        "endpoints": {
            "GET /": "Status do servidor",
            "POST /verificar_licenca": "Verificar licença (principal)",
            "GET /diagnostico": "Diagnóstico do sistema",
            "GET /testar_licenca/<api_id>": "Testar licença específica",
            "GET /health": "Health check",
            "POST /admin/reset_protecoes": "Resetar proteções (dev only)"
        }
    })

@app.route('/health')
def health_check():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "licencas_cadastradas": len(licencas_db),
        "memoria_utilizada": len(tentativas_falhas) + len(bloqueios_ativos)
    })

if __name__ == '__main__':
    # Thread para limpeza periódica
    def manutencao_periodica():
        while True:
            time.sleep(300)  # A cada 5 minutos
            try:
                limpar_cache_antigo()
                logger.info("Manutenção periódica executada")
            except Exception as e:
                logger.error(f"Erro na manutenção periódica: {e}")
    
    thread = threading.Thread(target=manutencao_periodica, daemon=True)
    thread.start()
    
    logger.info("Servidor de licenciamento iniciando...")
    logger.info(f"Licenças carregadas: {list(licencas_db.keys())}")
    
    app.run(debug=False, host='0.0.0.0', port=5000)
