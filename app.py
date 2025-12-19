from flask import Flask, request, jsonify
from datetime import datetime
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Servidor de Licenças Online"

@app.route('/verificar_licenca', methods=['POST'])
def verificar_licenca():
    try:
        dados = request.json
        api_id = dados.get('api_id', '')
        # Lógica simples de exemplo. Modifique depois!
        if api_id and len(api_id) >= 6:
            return jsonify({
                "valido": True,
                "mensagem": f"Licença válida para API_ID: {api_id[:10]}...",
                "timestamp": str(datetime.now())
            })
        else:
            return jsonify({
                "valido": False,
                "mensagem": "API_ID inválido ou ausente"
            })
    except Exception as e:
        return jsonify({"valido": False, "mensagem": f"Erro: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)