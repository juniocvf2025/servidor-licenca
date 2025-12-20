from flask import Flask, request, jsonify
from datetime import datetime
import json
import os

app = Flask(__name__)

# Nome do arquivo que armazena as licenças
ARQUIVO_LICENCAS = "licencas.json"

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
    try:
        dados = request.json
        api_id = dados.get('api_id', '').strip()  # Remove espaços

        # Carrega as licenças válidas do arquivo
        banco_de_dados = carregar_licencas()
        licencas_validas = banco_de_dados.get("licencas_validas", [])

        # Lógica de verificação REAL
        if api_id and api_id in licencas_validas:
            return jsonify({
                "valido": True,
                "mensagem": f"Licença válida para o cliente {api_id}",
                "timestamp": str(datetime.now())
            })
        else:
            return jsonify({
                "valido": False,
                "mensagem": "API_ID não encontrado ou licença inválida."
            })
    except Exception as e:
        return jsonify({"valido": False, "mensagem": f"Erro interno: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
