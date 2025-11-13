#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de Inicialização para Demo na Mostra Tech
Inicia o ngrok, gera QR Code e executa a aplicação Flask
"""

import os
import sys
import time
import qrcode
from io import BytesIO
from pyngrok import ngrok, conf
from threading import Thread
from app import app

# Configurações
NGROK_PORT = 8000
NGROK_REGION = "sa"  # South America (mais próximo do Brasil)


def print_banner():
    """Exibe banner de boas-vindas"""
    banner = """
    ╔══════════════════════════════════════════════════════════╗
    ║                                                          ║
    ║             🏛️  CIDADÃO ATIVO - MODO DEMO 🏛️             ║
    ║                                                          ║
    ║          Sistema de Denúncias Comunitárias              ║
    ║                  Mostra Tech 2025                        ║
    ║                                                          ║
    ╚══════════════════════════════════════════════════════════╝
    """
    print(banner)


def generate_qr_code(url):
    """Gera QR Code ASCII para exibir no terminal"""
    print("\n" + "="*60)
    print(f"📱 URL PÚBLICA: {url}")
    print("="*60)

    # Gera QR Code visual
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)

    # Salva QR Code como imagem
    img = qr.make_image(fill_color="black", back_color="white")
    qr_path = os.path.join(os.path.dirname(__file__), "app", "static", "qr_code_demo.png")
    os.makedirs(os.path.dirname(qr_path), exist_ok=True)
    img.save(qr_path)
    print(f"✅ QR Code salvo em: {qr_path}")

    # Gera QR Code ASCII para terminal
    qr_ascii = qrcode.QRCode()
    qr_ascii.add_data(url)
    qr_ascii.make()

    print("\n📲 QR CODE PARA ESCANEAMENTO:")
    print("-" * 60)
    qr_ascii.print_ascii(invert=True)
    print("-" * 60)

    return qr_path


def start_ngrok():
    """Inicia túnel ngrok e retorna a URL pública"""
    print("\n🔧 Iniciando túnel ngrok...")

    try:
        # Tenta obter authtoken do ambiente ou arquivo de config
        authtoken = os.environ.get('NGROK_AUTHTOKEN')

        # Se não encontrar no ambiente, tenta configurar automaticamente
        if not authtoken:
            # Verifica se existe arquivo .ngrok_token local
            token_file = os.path.join(os.path.dirname(__file__), '.ngrok_token')
            if os.path.exists(token_file):
                with open(token_file, 'r') as f:
                    authtoken = f.read().strip()

        # Configura authtoken se encontrado
        if authtoken:
            ngrok.set_auth_token(authtoken)
            print("✅ Authtoken configurado")

        # Configura região para melhor latência
        conf.get_default().region = NGROK_REGION

        # Inicia túnel HTTP
        public_url = ngrok.connect(NGROK_PORT, bind_tls=True)

        print(f"✅ Túnel ngrok estabelecido!")
        print(f"🌐 URL Local: http://localhost:{NGROK_PORT}")
        print(f"🌍 URL Pública: {public_url}")

        return str(public_url)

    except Exception as e:
        print(f"❌ Erro ao iniciar ngrok: {e}")
        print("\n💡 DICA: Verifique se você tem uma conta ngrok e configurou o authtoken:")
        print("   1. Crie uma conta em: https://dashboard.ngrok.com/signup")
        print("   2. Obtenha seu authtoken em: https://dashboard.ngrok.com/get-started/your-authtoken")
        print("   3. Configure com: ngrok config add-authtoken <seu_token>")
        sys.exit(1)


def save_demo_url(url):
    """Salva URL pública em arquivo para acesso da aplicação"""
    env_file = os.path.join(os.path.dirname(__file__), ".env.demo")
    with open(env_file, "w", encoding="utf-8") as f:
        f.write(f"DEMO_PUBLIC_URL={url}\n")
        f.write(f"FLASK_ENV=demo\n")

    # Também salva em variável de ambiente da sessão
    os.environ["DEMO_PUBLIC_URL"] = url
    os.environ["FLASK_ENV"] = "demo"

    print(f"✅ URL salva em: {env_file}")


def run_flask_app():
    """Executa a aplicação Flask"""
    print("\n🚀 Iniciando aplicação Flask...")
    print(f"⚙️  Servidor rodando em: http://0.0.0.0:{NGROK_PORT}")
    print("\n" + "="*60)
    print("⚠️  Para encerrar a demo, pressione CTRL+C")
    print("="*60 + "\n")

    # Executa Flask com configurações de produção
    app.run(
        host="0.0.0.0",
        port=NGROK_PORT,
        debug=False,  # Desabilita debug em modo demo
        use_reloader=False  # Evita reinicializações
    )


def cleanup():
    """Limpa recursos ao encerrar"""
    print("\n\n🛑 Encerrando demo...")
    try:
        ngrok.kill()
        print("✅ Túnel ngrok encerrado")
    except:
        pass

    # Remove arquivo de URL demo
    try:
        env_file = os.path.join(os.path.dirname(__file__), ".env.demo")
        if os.path.exists(env_file):
            os.remove(env_file)
    except:
        pass

    print("👋 Até a próxima!")


def main():
    """Função principal"""
    try:
        # Exibe banner
        print_banner()

        # Inicia ngrok
        public_url = start_ngrok()

        # Salva URL para uso na aplicação
        save_demo_url(public_url)

        # Gera QR Code
        qr_path = generate_qr_code(public_url)

        # Aguarda um pouco para garantir que ngrok está pronto
        time.sleep(2)

        print("\n📋 INSTRUÇÕES PARA A MOSTRA:")
        print("1. Projete ou imprima o QR Code acima no estande")
        print("2. Visitantes podem escanear com a câmera do celular")
        print("3. Acesse também em: /qr-demo para ver o QR na web")
        print("4. Mantenha este terminal aberto durante a apresentação")

        # Executa Flask (bloqueante)
        run_flask_app()

    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupção detectada...")
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cleanup()


if __name__ == "__main__":
    main()
