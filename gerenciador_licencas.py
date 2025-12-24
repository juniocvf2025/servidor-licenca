# gerenciador_licencas.py
import requests
import json
import sys

class GerenciadorLicencas:
    def __init__(self, url_base, senha_admin):
        self.url_base = url_base.rstrip('/')
        self.senha_admin = senha_admin
        
    def adicionar(self, telegram_id, licenca_id="AUTO", plano="PREMIUM", dias=30):
        """Adiciona uma nova licença"""
        url = f"{self.url_base}/admin/adicionar"
        
        dados = {
            "senha_admin": self.senha_admin,
            "licenca_id": licenca_id,
            "telegram_id": telegram_id,
            "plano": plano,
            "validade_dias": dias
        }
        
        try:
            resposta = requests.post(url, json=dados, timeout=10)
            
            if resposta.status_code == 200:
                resultado = resposta.json()
                print(f"\n✅ LICENÇA CRIADA COM SUCESSO!")
                print(f"📋 Licença ID: {resultado['licenca_id']}")
                print(f"👤 Telegram ID: {telegram_id}")
                print(f"📦 Plano: {plano}")
                print(f"⏳ Validade: {dias} dias")
                print(f"📝 Mensagem: {resultado['mensagem']}")
                return resultado['licenca_id']
            else:
                print(f"❌ ERRO: {resposta.status_code}")
                print(resposta.text)
                return None
                
        except Exception as e:
            print(f"❌ Erro de conexão: {e}")
            return None
    
    def listar(self, status=None):
        """Lista todas as licenças"""
        url = f"{self.url_base}/admin/listar"
        params = {"senha_admin": self.senha_admin}
        
        if status:
            params['status'] = status
        
        try:
            resposta = requests.get(url, params=params, timeout=10)
            
            if resposta.status_code == 200:
                resultado = resposta.json()
                licencas = resultado['licencas']
                
                print(f"\n📋 LICENÇAS ({resultado['total']} total):")
                print("=" * 80)
                
                for licenca_id, dados in licencas.items():
                    status_lic = dados.get('status', 'ativa')
                    plano = dados.get('plano', 'DESCONHECIDO')
                    telegram = dados.get('telegram_id', 'N/A')
                    dias = dados.get('validade_dias', 0)
                    
                    print(f"🔑 {licenca_id}")
                    print(f"   👤 Telegram: {telegram}")
                    print(f"   📦 Plano: {plano}")
                    print(f"   ⏳ Dias: {dias}")
                    print(f"   📊 Status: {status_lic.upper()}")
                    print(f"   {'─' * 40}")
                    
                return licencas
            else:
                print(f"❌ ERRO: {resposta.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Erro de conexão: {e}")
            return None
    
    def remover(self, licenca_id):
        """Remove uma licença"""
        url = f"{self.url_base}/admin/remover/{licenca_id}"
        
        dados = {"senha_admin": self.senha_admin}
        
        try:
            resposta = requests.delete(url, json=dados, timeout=10)
            
            if resposta.status_code == 200:
                print(f"\n✅ Licença {licenca_id} REMOVIDA com sucesso!")
                return True
            else:
                print(f"❌ ERRO: {resposta.status_code}")
                print(resposta.text)
                return False
                
        except Exception as e:
            print(f"❌ Erro de conexão: {e}")
            return False
    
    def testar_cliente(self, licenca_id, telegram_id):
        """Testa uma licença como se fosse um cliente"""
        url = f"{self.url_base}/verificar_licenca"
        
        import hashlib
        import time
        
        # Calcular hash
        timestamp = int(time.time())
        chave_fixa = "T3l3gr@m-L1c3nc3-S3cr3tK3y-33614184!2024"
        string_hash = f"{licenca_id}:{telegram_id}:{timestamp}:{chave_fixa}"
        hash_calculado = hashlib.sha256(string_hash.encode()).hexdigest()
        
        dados = {
            "api_id": licenca_id,
            "telegram_id": telegram_id,
            "timestamp": timestamp,
            "hash_verificacao": hash_calculado
        }
        
        try:
            resposta = requests.post(url, json=dados, timeout=10)
            
            print(f"\n🧪 TESTE DE CLIENTE:")
            print(f"📤 Enviado: Licença={licenca_id}, Telegram={telegram_id}")
            print(f"📥 Status: {resposta.status_code}")
            print(f"📥 Resposta: {resposta.text[:200]}")
            
            if resposta.status_code == 200:
                print("✅ VERIFICAÇÃO BEM-SUCEDIDA!")
            else:
                print("❌ VERIFICAÇÃO FALHOU!")
                
            return resposta.status_code == 200
            
        except Exception as e:
            print(f"❌ Erro: {e}")
            return False

# Interface de linha de comando
def menu_principal():
    url_base = "https://servidor-licenca-fix.onrender.com"
    senha_admin = "AdminSeguro@2025!"  # MUDE ESTA SENHA!
    
    gerenciador = GerenciadorLicencas(url_base, senha_admin)
    
    while True:
        print("\n" + "=" * 50)
        print("🔧 GERENCIADOR DE LICENÇAS")
        print("=" * 50)
        print("1. Adicionar nova licença")
        print("2. Listar todas as licenças")
        print("3. Remover licença")
        print("4. Testar licença (como cliente)")
        print("5. Verificar status do servidor")
        print("0. Sair")
        
        opcao = input("\n👉 Escolha uma opção: ").strip()
        
        if opcao == "1":
            print("\n📝 ADICIONAR NOVA LICENÇA")
            telegram_id = input("Telegram ID do cliente: ").strip()
            licenca_id = input("ID da licença [AUTO para gerar]: ").strip() or "AUTO"
            plano = input("Plano [PREMIUM]: ").strip() or "PREMIUM"
            dias = input("Dias de validade [30]: ").strip() or "30"
            
            if telegram_id:
                gerenciador.adicionar(telegram_id, licenca_id, plano, int(dias))
            else:
                print("❌ Telegram ID é obrigatório!")
                
        elif opcao == "2":
            status_filtro = input("Filtrar por status [ativa, inativa, deixe vazio para todas]: ").strip()
            gerenciador.listar(status_filtro if status_filtro else None)
            
        elif opcao == "3":
            licenca_id = input("ID da licença a remover: ").strip()
            if licenca_id and input(f"Tem certeza que quer remover {licenca_id}? (s/n): ").lower() == 's':
                gerenciador.remover(licenca_id)
                
        elif opcao == "4":
            licenca_id = input("ID da licença: ").strip()
            telegram_id = input("Telegram ID para testar: ").strip()
            if licenca_id and telegram_id:
                gerenciador.testar_cliente(licenca_id, telegram_id)
                
        elif opcao == "5":
            try:
                resposta = requests.get(f"{url_base}/status", timeout=5)
                print(f"\n📡 Status do servidor: {resposta.json()}")
            except Exception as e:
                print(f"❌ Erro: {e}")
                
        elif opcao == "0":
            print("👋 Até logo!")
            break
        else:
            print("❌ Opção inválida!")

if __name__ == "__main__":
    menu_principal()
