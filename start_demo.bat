@echo off
REM ============================================================
REM Script de Inicialização Rápida - Demo Cidadão Ativo
REM ============================================================

echo.
echo ╔══════════════════════════════════════════════════════════╗
echo ║                                                          ║
echo ║            🏛️  CIDADÃO ATIVO - MODO DEMO 🏛️              ║
echo ║                                                          ║
echo ║         Sistema de Denúncias Comunitárias                ║
echo ║                 Mostra Tech 2025                         ║
echo ║                                                          ║
echo ╚══════════════════════════════════════════════════════════╝
echo.

REM Verificar se o ambiente virtual existe
if not exist "venv\Scripts\activate.bat" (
    echo ❌ Ambiente virtual não encontrado!
    echo.
    echo Crie o ambiente virtual primeiro:
    echo   python -m venv venv
    echo   venv\Scripts\activate
    echo   pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

REM Ativar ambiente virtual
echo 🔧 Ativando ambiente virtual...
call venv\Scripts\activate.bat

REM Verificar se as dependências estão instaladas
echo 🔍 Verificando dependências...
python -c "import pyngrok, qrcode" 2>nul
if errorlevel 1 (
    echo.
    echo ❌ Dependências faltando! Instalando...
    pip install pyngrok qrcode[pil]
    if errorlevel 1 (
        echo.
        echo ❌ Erro ao instalar dependências!
        pause
        exit /b 1
    )
    echo ✅ Dependências instaladas!
)

REM Executar script de demonstração
echo.
echo 🚀 Iniciando demonstração...
echo.
python start_demo.py

REM Se o script foi interrompido
echo.
echo 👋 Demo encerrada!
pause
