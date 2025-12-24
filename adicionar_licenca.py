# adicionar_licenca.py (PARA VOCÊ USAR)
import requests
import json

def adicionar_licenca(licenca_id, telegram_id, plano="P1", dias=365):
    """Script para você adicionar licenças no servidor"""
    
    url = "https://seu-servidor.onrender.com/admin/adicionar_licenca"
    
    dados = {
        "senha_admin": "SUA_SENHA_FORTE_AQUI",  # MUDE PARA UMA SENHA FORTE!
        "licenca_id": licenca_id,
        "telegram_id": telegram_id,
        "plano": plano,
        "validade_dias": dias
    }
    
    try:
        resposta = requests.post(url, json=dados, timeout=10)
        
        if resposta.status_code == 200:
            print(f"✅ Licença {licenca_id} adicionada para Telegram ID {telegram_id}")
            print(f"📋 Resposta: {resposta.json()}")
        else:
            print(f"❌ Erro: {resposta.status_code}")
            print(f"📋 Detalhes: {resposta.text}")
            
    except Exception as e:
        print(f"❌ Erro de conexão: {e}")

# Exemplo de uso:
if __name__ == "__main__":
    print("📝 Sistema de Adição de Licenças")
    print("=" * 40)
    
    while True:
        print("\n1. Adicionar nova licença")
        print("2. Sair")
        
        opcao = input("\nEscolha uma opção: ")
        
        if opcao == "1":
            licenca_id = input("ID da Licença (ex: CLIENTE-001): ").strip()
            telegram_id = input("Telegram ID do cliente: ").strip()
            plano = input("Plano (P1, P2, P3) [P1]: ").strip() or "P1"
            dias = input("Dias de validade [365]: ").strip() or "365"
            
            if licenca_id and telegram_id:
                adicionar_licenca(licenca_id, telegram_id, plano, int(dias))
            else:
                print("❌ Licença ID e Telegram ID são obrigatórios!")
                
        elif opcao == "2":
            print("👋 Até logo!")
            break
