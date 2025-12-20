from flask import Flask, request, jsonify
from datetime import datetime
import json
import os
import time  # <-- NOVA IMPORTACAO para o rate limiting

app = Flask(__name__)

# Nome do arquivo que armazena as licenças
ARQUIVO_LICENCAS = "licencas.json"

# --- Dicionário para armazenar tentativas de acesso (Rate Limiting) ---
# Em um sistema maior, use Redis. Para seu caso, em memória é suficiente.
tentativas_por_ip = {}

def carregar_licencas():
    """Carrega a lista de licenças do arquivo JSON."""
    try:
        if os.path.exists(ARQUIVO_LICENCAS):
            with open(ARQUIVO_LICENCAS, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"Erro ao carregar licenças: {e}")
    # Retorna uma lista vazia padrão se o arquivo não existir ou der erro
    return {"licencas_validas": []}

@app.route('/')
def home():
    return "✅ Servidor de Licenças Online"

@app.route('/verificar_licenca', methods=['POST'])
def verificar_licenca():
    # --- INÍCIO DO SISTEMA DE RATE LIMITING ---
    ip_cliente = request.remote_addr
    hora_atual = time.time()

    # Limpa tentativas antigas (mais de 1 minuto) deste IP
    if ip_cliente in tentativas_por_ip:
        # Mantém apenas registros com menos de 60 segundos
        tentativas_por_ip[ip_cliente] = [
            tentativa for tentativa in tentativas_por_ip[ip_cliente]
            if hora_atual - tentativa < 60
        ]
    else:
        tentativas_por_ip[ip_cliente] = []

    # Bloqueia se tiver 10 ou mais tentativas no último minuto
    if len(tentativas_por_ip[ip_cliente]) >= 10:
        return jsonify({
            "valido": False,
            "mensagem": "⏳ Muitas tentativas seguidas. Aguarde 1 minuto."
        }), 429  # Código HTTP 429 = "Too Many Requests"

    # Registra a tentativa atual deste IP
    tentativas_por_ip[ip_cliente].append(hora_atual)
    # --- FIM DO SISTEMA DE RATE LIMITING ---

    # --- LÓGICA ORIGINAL DE VERIFICAÇÃO DE LICENÇA ---
    try:
        dados = request.json
        api_id = dados.get('api_id', '').strip()

        # Carrega as licenças válidas do arquivo
        banco_de_dados = carregar_licencas()
        licencas_validas = banco_de_dados.get("licencas_validas", [])

        # Verificação REAL contra a lista
        if api_id and api_id in licencas_validas:
            return jsonify({
                "valido": True,
                "mensagem": f"✅ Licença válida para {api_id}",
                "timestamp": str(datetime.now())
            })
        else:
            return jsonify({
                "valido": False,
                "mensagem": "❌ API_ID não encontrado ou licença inválida."
            })
    except Exception as e:
        return jsonify({"valido": False, "mensagem": f"Erro interno: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
