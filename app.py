# app.py - VERSÃO ULTRA SIMPLES
from flask import Flask, request, jsonify
import hashlib
import time

app = Flask(__name__)

# =============================================
# DADOS FIXOS - EDITÁVEIS DIRETAMENTE
# =============================================

CHAVE_FIXA = "T3l3gr@m-L1c3nc3-S3cr3tK3y-33614184!2024"

# LICENÇAS CADASTRADAS - EDITE AQUI!
# Formato: "ID_DA_LICENCA": "TELEGRAM_ID_DO_CLIENTE"
LICENCAS = {
    # SUA LICENÇA (nunca remova)
    "DONO-2025-001": "33614184",
    
    # ADICIONE SEUS CLIENTES ABAIXO:
    # "ID_QUE_VOCE_CRIOU": "TELEGRAM_ID_DO_CLIENTE"
    
    # EXEMPLOS:
    "CLIENTE-001": "123456789",
    "CLIENTE-002": "987654321",
    "CLIENTE-003": "555555555",
    
    # Adicione mais conforme vender...
}

# =============================================
# ENDPOINT ÚNICO E SIMPLES
# =============================================

@app.route('/verificar_licenca', methods=['POST', 'GET'])
def verificar_licenca():
    try:
        # Aceita GET e POST
        if request.method == 'POST':
            dados = request.get_json() or {}
        else:
            dados = request.args.to_dict()
        
        # Pegar dados
        licenca_id = dados.get('api_id') or dados.get('licenca_id', '')
        telegram_id = dados.get('telegram_id') or dados.get('vinculo_telegram', '')
        
        # Validação
        if not licenca_id or not telegram_id:
            return "0|ERRO|0|||Dados incompletos", 400
        
        # Verificar licença
        if licenca_id not in LICENCAS:
            return "0|INVALIDA|0|||Licença não encontrada", 404
        
        # Verificar Telegram ID
        if LICENCAS[licenca_id] != telegram_id:
            return f"0|INVALIDA|0|||Licença não vinculada. Esperado: {LICENCAS[licenca_id]}", 403
        
        # Verificar hash (opcional - compatibilidade)
        if 'hash_verificacao' in dados and 'timestamp' in dados:
            string_hash = f"{licenca_id}:{telegram_id}:{dados['timestamp']}:{CHAVE_FIXA}"
            hash_calculado = hashlib.sha256(string_hash.encode()).hexdigest()
            
            if dados['hash_verificacao'] != hash_calculado:
                return "0|INVALIDA|0|||Hash inválido", 403
        
        # TUDO OK - Retorna formato que seu código espera
        timestamp = int(time.time())
        return f"1|PREMIUM|36500|token-{timestamp}|{timestamp}|ok", 200
        
    except Exception as e:
        return f"0|ERRO|0|||Erro: {str(e)}", 500

# =============================================
# ENDPOINTS ADICIONAIS (ÚTEIS)
# =============================================

@app.route('/')
def home():
    """Página inicial"""
    return f"""
    <html>
    <head><title>Sistema de Licenças</title></head>
    <body style="font-family: Arial; padding: 20px;">
        <h1>✅ Sistema de Licenças Online</h1>
        <p>Total de licenças cadastradas: <strong>{len(LICENCAS)}</strong></p>
        <h3>Licenças ativas:</h3>
        <ul>
            {"".join(f'<li><strong>{lid}</strong>: Telegram ID {tid}</li>' for lid, tid in LICENCAS.items())}
        </ul>
        <h3>Como adicionar cliente:</h3>
        <ol>
            <li>Edite o arquivo app.py no GitHub</li>
            <li>Adicione uma linha no dicionário LICENCAS</li>
            <li>Formato: "ID-DA-LICENCA": "TELEGRAM_ID"</li>
            <li>Faça commit e aguarde 1-2 minutos</li>
        </ol>
        <p><em>Servidor atualizado em: {time.strftime('%d/%m/%Y %H:%M:%S')}</em></p>
    </body>
    </html>
    """

@app.route('/licencas')
def listar_licencas():
    """Lista todas licenças em JSON"""
    return jsonify({
        "total": len(LICENCAS),
        "licencas": LICENCAS
    })

@app.route('/status/<licenca_id>')
def status_licenca(licenca_id):
    """Verifica uma licença específica"""
    if licenca_id in LICENCAS:
        return jsonify({
            "valida": True,
            "licenca_id": licenca_id,
            "telegram_id": LICENCAS[licenca_id],
            "mensagem": "Licença ativa"
        })
    else:
        return jsonify({
            "valida": False,
            "mensagem": "Licença não encontrada"
        }), 404

# =============================================
# RODAR SERVIDOR
# =============================================

if __name__ == '__main__':
    print("=" * 50)
    print("🚀 SISTEMA DE LICENÇAS ULTRA SIMPLES")
    print("=" * 50)
    print(f"📊 Licenças cadastradas: {len(LICENCAS)}")
    print("\n📝 LISTA DE LICENÇAS:")
    for licenca, telegram in LICENCAS.items():
        print(f"  🔑 {licenca} → 👤 {telegram}")
    print("\n🔧 Para adicionar cliente:")
    print("  1. Edite LICENCAS no código acima")
    print("  2. Formato: 'NOVA-LICENCA': 'TELEGRAM-ID'")
    print("  3. Faça commit no GitHub")
    print("  4. Render faz deploy automático")
    print("=" * 50)
    
    app.run(host='0.0.0.0', port=5000)
