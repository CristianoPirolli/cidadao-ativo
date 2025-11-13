#!/bin/bash
# ============================================================
# Script de Inicialização Rápida - Demo Cidadão Ativo
# ============================================================

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║                                                          ║"
echo "║            🏛️  CIDADÃO ATIVO - MODO DEMO 🏛️              ║"
echo "║                                                          ║"
echo "║         Sistema de Denúncias Comunitárias                ║"
echo "║                 Mostra Tech 2025                         ║"
echo "║                                                          ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# Verificar se o ambiente virtual existe
if [ ! -f "venv/bin/activate" ]; then
    echo "❌ Ambiente virtual não encontrado!"
    echo ""
    echo "Crie o ambiente virtual primeiro:"
    echo "  python3 -m venv venv"
    echo "  source venv/bin/activate"
    echo "  pip install -r requirements.txt"
    echo ""
    exit 1
fi

# Ativar ambiente virtual
echo "🔧 Ativando ambiente virtual..."
source venv/bin/activate

# Verificar se as dependências estão instaladas
echo "🔍 Verificando dependências..."
python -c "import pyngrok, qrcode" 2>/dev/null
if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Dependências faltando! Instalando..."
    pip install pyngrok qrcode[pil]
    if [ $? -ne 0 ]; then
        echo ""
        echo "❌ Erro ao instalar dependências!"
        exit 1
    fi
    echo "✅ Dependências instaladas!"
fi

# Executar script de demonstração
echo ""
echo "🚀 Iniciando demonstração..."
echo ""
python start_demo.py

# Se o script foi interrompido
echo ""
echo "👋 Demo encerrada!"
