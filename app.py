from flask import Flask, request, jsonify
import hashlib
import time
from datetime import datetime
import base64
import json
import os

app = Flask(__name__)

# =============================================
# DECODIFICAÇÃO EXATA DA CHAVE DO CLIENTE
# =============================================
# Do seu código: _OFS2 = "VDNsM2dyQG0tTDFjM25jMy1TM2NyM3RLM3ktMzM2MTQxODQhMjAyNA=="
SECRET_KEY_B64 = "VDNsM2dyQG0tTDFjM25jMy1TM2NyM3RLM3ktMzM2MTQxODQhMjAyNA=="
SECRET_KEY = base64.b64decode(SECRET_KEY_B64).decode('utf-8')  # "T3l3gr@m-L1c3nc3-S3cr3tK3y-33614184!2024"

print(f"🔑 Chave secreta decodificada: {SECRET_KEY}")

# =============================================
# BASE DE DADOS DE LICENÇAS COM VÍNCULO API_ID
# =============================================
licencas_validas = {
    "DONO-2025-001": {
        "vinculo_api_id": "33614184",  # DEVE SER EXATAMENTE ESTE API_ID
        "validade_dias": 3365,
        "ativo": True,
        "data_ativacao": "2024-01-01",
        "nome": "Licença Dono 2025-001",
        "max_uso": 999999,
        "usos": 0
    },
    "DONO-2025-002": {
        "vinculo_api_id": "33614184",
        "validade_dias": 30,
        "ativo": True,
        "data_ativacao": "2024-01-15",
        "nome": "Licença Dono 2025-002",
        "max_uso": 999999,
        "usos": 0
    },
    "TESTE-2024-001": {
        "vinculo_api_id": "33614184",
        "validade_dias": 7,
        "ativo": True,
        "data_ativacao": "2024-01-01",
        "nome": "Licença Teste 2024-001",
        "max_uso": 100,
        "usos": 0
    }
}

# =============================================
# FUNÇÃO PARA CALCULAR HASH IGUAL AO CLIENTE
# =============================================
def calcular_hash_cliente(licenca_id, vinculo_api_id, timestamp):
    """
    Calcula o hash EXATAMENTE como o cliente faz:
    SHA256(licenca_id:vinculo_api_id:timestamp:SECRET_KEY)
    
    Onde SECRET_KEY = "T3l3gr@m-L1c3nc3-S3cr3tK3y-33614184!2024"
    """
    input_str = f"{licenca_id}:{vinculo_api_id}:{timestamp}:{SECRET_KEY}"
    return hashlib.sha256(input_str.encode()).hexdigest()

# =============================================
# ENDPOINT PRINCIPAL - FORMATO EXATO DO CLIENTE
# =============================================
@app.route('/verificar_licenca', methods=['POST'])
def verificar_licenca():
    """Endpoint que aceita EXATAMENTE o formato do cliente"""
    try:
        print("\n" + "="*60)
        print("🔐 VERIFICAÇÃO DE LICENÇA - FORMATO CLIENTE")
        print("="*60)
        
        # 1. Obter dados JSON
        if not request.is_json:
            print("❌ Content-Type não é JSON")
            return jsonify({
                "valido": False,
                "message": "Content-Type deve ser application/json"
            }), 400
        
        dados = request.get_json()
        print(f"📦 JSON recebido: {json.dumps(dados, indent=2)}")
        
        # 2. Extrair campos EXATOS do cliente
        # O cliente envia: api_id, telegram_id, timestamp, hash_verificacao
        licenca_id = dados.get('api_id')
        vinculo_api_id = dados.get('telegram_id')
        timestamp = dados.get('timestamp')
        hash_recebido = dados.get('hash_verificacao')
        
        # 3. Verificar campos obrigatórios
        campos_faltando = []
        if not licenca_id: campos_faltando.append('api_id')
        if not vinculo_api_id: campos_faltando.append('telegram_id')
        if not timestamp: campos_faltando.append('timestamp')
        if not hash_recebido: campos_faltando.append('hash_verificacao')
        
        if campos_faltando:
            print(f"❌ Campos faltando: {campos_faltando}")
            return jsonify({
                "valido": False,
                "message": f"Campos obrigatórios faltando: {', '.join(campos_faltando)}"
            }), 400
        
        print(f"\n📋 Dados extraídos:")
        print(f"   Licença ID: {licenca_id}")
        print(f"   Vínculo API_ID: {vinculo_api_id}")
        print(f"   Timestamp: {timestamp}")
        print(f"   Hash recebido: {hash_recebido}")
        
        # 4. Verificar formato da licença
        import re
        if not re.match(r'^[A-Z]+-\d{4}-\d{3}$', licenca_id):
            print(f"❌ Formato de licença inválido: {licenca_id}")
            return jsonify({
                "valido": False,
                "message": "Formato do ID inválido. Use: DONO-2025-001"
            }), 400
        
        # 5. Verificar se licença existe
        if licenca_id not in licencas_validas:
            print(f"❌ Licença não encontrada: {licenca_id}")
            return jsonify({
                "valido": False,
                "message": "Licença não encontrada"
            }), 404
        
        licenca_info = licencas_validas[licenca_id]
        print(f"✅ Licença encontrada: {licenca_info['nome']}")
        
        # 6. Verificar se licença está ativa
        if not licenca_info.get('ativo', True):
            print(f"❌ Licença desativada: {licenca_id}")
            return jsonify({
                "valido": False,
                "message": "Licença desativada"
            }), 403
        
        # 7. Verificar vínculo API_ID (CRÍTICO!)
        if str(licenca_info['vinculo_api_id']) != str(vinculo_api_id):
            print(f"❌ API_ID não vinculado: esperado {licenca_info['vinculo_api_id']}, recebido {vinculo_api_id}")
            return jsonify({
                "valido": False,
                "message": "API_ID não vinculado a esta licença",
                "esperado": licenca_info['vinculo_api_id'],
                "recebido": vinculo_api_id
            }), 403
        
        print(f"✅ API_ID vinculado corretamente: {vinculo_api_id}")
        
        # 8. Verificar validade da licença
        data_ativacao = datetime.strptime(licenca_info['data_ativacao'], '%Y-%m-%d')
        dias_passados = (datetime.now() - data_ativacao).days
        dias_restantes = licenca_info['validade_dias'] - dias_passados
        
        if dias_restantes <= 0:
            print(f"❌ Licença expirada: {dias_passados} dias passados")
            return jsonify({
                "valido": False,
                "message": "Licença expirada",
                "dias_restantes": 0
            }), 403
        
        print(f"✅ Validade OK: {dias_restantes} dias restantes")
        
        # 9. Verificar timestamp (não muito antigo)
        tempo_atual = int(time.time())
        tempo_requisicao = int(timestamp)
        
        if abs(tempo_atual - tempo_requisicao) > 300:  # 5 minutos de tolerância
            print(f"❌ Timestamp expirado: {tempo_requisicao} (atual: {tempo_atual})")
            return jsonify({
                "valido": False,
                "message": "Timestamp expirado"
            }), 403
        
        print(f"✅ Timestamp válido: diferença {abs(tempo_atual - tempo_requisicao)} segundos")
        
        # 10. CALCULAR E VERIFICAR HASH (PARTE MAIS IMPORTANTE!)
        print(f"\n🔐 CALCULANDO HASH...")
        print(f"   Entrada: '{licenca_id}:{vinculo_api_id}:{timestamp}:{SECRET_KEY}'")
        
        hash_calculado = calcular_hash_cliente(licenca_id, vinculo_api_id, timestamp)
        print(f"   Hash calculado: {hash_calculado}")
        print(f"   Hash recebido:  {hash_recebido}")
        
        if hash_calculado != hash_recebido:
            print(f"❌ HASH NÃO CONFERE!")
            print(f"   Diferença detectada")
            
            # Debug: mostrar possíveis erros
            print(f"\n🔍 DEBUG - Tentando variações:")
            
            # Variação 1: Com pipe
            hash_pipe = hashlib.sha256(f"{licenca_id}|{vinculo_api_id}|{timestamp}|{SECRET_KEY}".encode()).hexdigest()
            print(f"   Com |: {hash_pipe[:20]}...")
            
            # Variação 2: Sem separador
            hash_sem = hashlib.sha256(f"{licenca_id}{vinculo_api_id}{timestamp}{SECRET_KEY}".encode()).hexdigest()
            print(f"   Sem separador: {hash_sem[:20]}...")
            
            # Variação 3: Ordem diferente
            hash_ordem = hashlib.sha256(f"{timestamp}:{licenca_id}:{vinculo_api_id}:{SECRET_KEY}".encode()).hexdigest()
            print(f"   Ordem dif: {hash_ordem[:20]}...")
            
            return jsonify({
                "valido": False,
                "message": "Falha na verificação de segurança (hash inválido)",
                "hash_calculado": hash_calculado,
                "hash_recebido": hash_recebido
            }), 403
        
        print(f"✅ HASH VÁLIDO!")
        
        # 11. Atualizar contador de usos
        licenca_info['usos'] = licenca_info.get('usos', 0) + 1
        licenca_info['ultima_verificacao'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 12. Verificar limite de usos
        if licenca_info['usos'] > licenca_info['max_uso']:
            print(f"⚠️ Limite de usos atingido: {licenca_info['usos']}/{licenca_info['max_uso']}")
        
        # 13. Retornar resposta de SUCESSO
        print(f"\n🎉 LICENÇA VÁLIDA! Enviando resposta...")
        
        resposta = {
            "valido": True,
            "message": f"✅ Licença válida! ({dias_restantes} dias restantes)",
            "licenca_id": licenca_id,
            "vinculo_api_id": vinculo_api_id,
            "dias_restantes": dias_restantes,
            "usos": licenca_info['usos'],
            "max_usos": licenca_info['max_uso'],
            "timestamp": tempo_atual,
            "hash_verificado": True
        }
        
        # Formato que o cliente espera (com | ou JSON)
        formato = request.args.get('formato', 'json')
        
        if formato == 'pipe':
            # Formato pipe: "1|licenca_id|dias_restantes"
            resposta_texto = f"1|{licenca_id}|{dias_restantes}"
            print(f"📤 Resposta (pipe): {resposta_texto}")
            return resposta_texto, 200, {'Content-Type': 'text/plain'}
        else:
            # Formato JSON
            print(f"📤 Resposta (JSON): {json.dumps(resposta, indent=2)}")
            return jsonify(resposta), 200
        
    except Exception as e:
        print(f"\n💥 ERRO INTERNO: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            "valido": False,
            "message": f"Erro interno: {str(e)}"
        }), 500

# =============================================
# ENDPOINT DE TESTE/DEBUG
# =============================================
@app.route('/testar_hash', methods=['GET', 'POST'])
def testar_hash():
    """Testa o cálculo do hash"""
    if request.method == 'GET':
        return '''
        <h3>🧪 Testar Hash do Cliente</h3>
        <form method="POST">
            <p>Licença ID: <input name="licenca_id" value="DONO-2025-001"></p>
            <p>API_ID Vinculado: <input name="api_id" value="33614184"></p>
            <p>Timestamp: <input name="timestamp" value="''' + str(int(time.time())) + '''"></p>
            <button type="submit">Calcular Hash</button>
        </form>
        
        <h4>Chave Secreta:</h4>
        <pre>''' + SECRET_KEY + '''</pre>
        <pre>Base64: ''' + SECRET_KEY_B64 + '''</pre>
        '''
    else:
        licenca_id = request.form.get('licenca_id')
        api_id = request.form.get('api_id')
        timestamp = request.form.get('timestamp', str(int(time.time())))
        
        input_str = f"{licenca_id}:{api_id}:{timestamp}:{SECRET_KEY}"
        hash_result = hashlib.sha256(input_str.encode()).hexdigest()
        
        return f'''
        <h3>🔐 Hash Calculado</h3>
        <p><strong>Entrada:</strong> {input_str}</p>
        <p><strong>Hash SHA256:</strong> {hash_result}</p>
        
        <h4>JSON para enviar:</h4>
        <pre>
{{
    "api_id": "{licenca_id}",
    "telegram_id": "{api_id}",
    "timestamp": {timestamp},
    "hash_verificacao": "{hash_result}"
}}
        </pre>
        
        <p><a href="/testar_hash">Testar novamente</a></p>
        '''

@app.route('/status', methods=['GET'])
def status():
    """Status do servidor"""
    licencas_info = []
    for id_lic, info in licencas_validas.items():
        licencas_info.append({
            "id": id_lic,
            "nome": info['nome'],
            "vinculo_api_id": info['vinculo_api_id'],
            "validade_dias": info['validade_dias'],
            "usos": info.get('usos', 0),
            "max_usos": info['max_uso'],
            "ativo": info['ativo']
        })
    
    return jsonify({
        "status": "online",
        "servidor": "Sistema de Licenciamento com Vínculo API_ID",
        "versao": "1.0-exato",
        "timestamp": int(time.time()),
        "chave_secreta": SECRET_KEY[:10] + "...",
        "total_licencas": len(licencas_validas),
        "licencas": licencas_info
    })

# =============================================
# ADMINISTRAÇÃO
# =============================================
@app.route('/admin/adicionar_licenca', methods=['POST'])
def adicionar_licenca():
    """Adiciona nova licença (protegido por senha em produção)"""
    dados = request.get_json()
    
    licenca_id = dados.get('licenca_id')
    vinculo_api_id = dados.get('vinculo_api_id', '33614184')
    validade_dias = dados.get('validade_dias', 30)
    nome = dados.get('nome', f'Licença {licenca_id}')
    
    if not licenca_id:
        return jsonify({"erro": "licenca_id é obrigatório"}), 400
    
    licencas_validas[licenca_id] = {
        "vinculo_api_id": vinculo_api_id,
        "validade_dias": validade_dias,
        "ativo": True,
        "data_ativacao": datetime.now().strftime('%Y-%m-%d'),
        "nome": nome,
        "max_uso": 999999,
        "usos": 0
    }
    
    return jsonify({
        "sucesso": True,
        "message": f"Licença {licenca_id} adicionada",
        "licenca": licencas_validas[licenca_id]
    })

# =============================================
# INICIALIZAÇÃO
# =============================================
if __name__ == '__main__':
    PORT = int(os.environ.get('PORT', 5000))
    HOST = os.environ.get('HOST', '0.0.0.0')
    DEBUG = os.environ.get('DEBUG', 'True').lower() == 'true'
    
    print("\n" + "="*70)
    print("🚀 SERVIDOR DE LICENÇAS - VÍNCULO API_ID")
    print("="*70)
    print(f"🔑 Chave secreta decodificada: {SECRET_KEY}")
    print(f"🔗 Vínculo API_ID obrigatório: 33614184")
    print(f"📡 URL: http://{HOST if HOST != '0.0.0.0' else 'localhost'}:{PORT}")
    print(f"🔧 Modo debug: {DEBUG}")
    print("\n📋 Licenças disponíveis:")
    for lic_id, info in licencas_validas.items():
        print(f"   • {lic_id} -> API_ID: {info['vinculo_api_id']} ({info['validade_dias']} dias)")
    
    print("\n🌐 Endpoints:")
    print("   POST /verificar_licenca     - Verificar licença (formato cliente)")
    print("   GET  /testar_hash           - Testar cálculo de hash")
    print("   GET  /status                - Status do servidor")
    print("   POST /admin/adicionar_licenca - Adicionar nova licença")
    print("="*70 + "\n")
    
    app.run(host=HOST, port=PORT, debug=DEBUG)
