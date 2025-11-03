#!/bin/bash

# Script para ejecutar el dashboard de ventas

echo "🍽️  Iniciando Dashboard de Análisis de Ventas - Fudo"
echo "=================================================="

# Verificar si existe el archivo .env
if [ ! -f .env ]; then
    echo "⚠️  Advertencia: No se encontró el archivo .env"
    echo "📝 Crea un archivo .env basado en .env.example"
    echo ""
fi

# Verificar si el entorno virtual existe
if [ -d "venv" ]; then
    echo "🔧 Activando entorno virtual..."
    source venv/bin/activate
fi

# Ejecutar Streamlit
echo "🚀 Iniciando Streamlit..."
streamlit run app.py

