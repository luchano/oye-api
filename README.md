# 🍽️ Dashboard de Análisis Estratégico de Ventas - Fudo

Dashboard interactivo para análisis estratégico de ventas de tu negocio gastronómico utilizando la API de Fudo.

## 🚀 Características

- **Análisis de ventas por día**: Evolución diaria de ventas con gráficos interactivos
- **Análisis de ventas por hora**: Identificación de horas pico y patrones horarios
- **Análisis de ventas por mes**: Tendencias mensuales y comparativas
- **Métricas clave**: Total de ventas, transacciones, mejor día/hora, ticket promedio
- **Dashboard interactivo**: Visualizaciones dinámicas con Plotly y Streamlit

## 📋 Requisitos Previos

- Python 3.8 o superior
- Acceso a la API de Fudo (https://dev.fu.do/api/)
- Credenciales de API (API Key y Secret, si son requeridas)

## 🔧 Instalación

1. **Clonar o descargar el proyecto**

2. **Crear un entorno virtual (recomendado)**
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

3. **Instalar dependencias**
```bash
pip install -r requirements.txt
```

4. **Configurar variables de entorno**

   Copia el archivo `.env.example` a `.env`:
```bash
cp .env.example .env
```

   Edita el archivo `.env` y configura tus credenciales:
```
FUDO_ENVIRONMENT=production
FUDO_API_KEY=tu_api_key_aqui
FUDO_API_SECRET=tu_api_secret_aqui
```

   **⚠️ Importante**: Para obtener tus credenciales de API (`apiKey` y `apiSecret`), 
   debes contactar a **soporte@fu.do** indicando:
   - El nombre de la cuenta en Fudo
   - El usuario al que quieres dar acceso a la API
   
   Se recomienda crear un usuario especialmente para acceso API (ej: api@turestaurante.com).

## 🎯 Uso

### Ejecutar el Dashboard

**⚠️ IMPORTANTE: Primero debes activar el entorno virtual**

1. **Activa el entorno virtual** (si aún no está activado):
```bash
source venv/bin/activate  # En macOS/Linux
# O en Windows: venv\Scripts\activate
```

2. **Ejecuta el dashboard**:
```bash
streamlit run app.py
```

El dashboard se abrirá automáticamente en tu navegador en `http://localhost:8501`

**Alternativa rápida**: Puedes usar el script incluido (solo macOS/Linux):
```bash
./run.sh
```

### Navegación del Dashboard

1. **Sidebar**: Configura el período de análisis (7-365 días) y selecciona la vista
2. **Resumen General**: Métricas clave y gráficos combinados
3. **Por Día**: Análisis detallado de ventas diarias
4. **Por Hora**: Análisis de patrones horarios y horas pico
5. **Por Mes**: Tendencias mensuales y comparativas

## 📊 Estructura del Proyecto

```
oye-api/
├── app.py                 # Dashboard principal con Streamlit
├── fudo_client.py         # Cliente para la API de Fudo
├── analytics.py           # Funciones de análisis de ventas
├── requirements.txt       # Dependencias del proyecto
├── .env.example          # Ejemplo de configuración
├── .gitignore            # Archivos ignorados por git
└── README.md             # Este archivo
```

## 🔌 Integración con la API de Fudo

El cliente de API está configurado para usar la API oficial de Fudo:

- **URL Base**: `https://api.fu.do/v1alpha1` (producción)
- **Autenticación**: Token Bearer obtenido mediante `apiKey` y `apiSecret`
- **Endpoint de Ventas**: `/sales`
- **Filtros**: Usa el formato `filter[createdAt]=and(gte.FECHA,lte.FECHA)`
- **Paginación**: Maneja automáticamente paginación de hasta 500 items por página

### Autenticación

El cliente maneja automáticamente:
- ✅ Obtención del token de autenticación
- ✅ Renovación automática del token (expira cada 24 horas)
- ✅ Reintentos cuando el token expira

### Formato de Datos

El cliente mapea automáticamente los campos de la API de Fudo:
- `createdAt` → `datetime`
- `totalAmount` → `amount`
- Manejo de diferentes formatos de respuesta

**Nota**: Si no hay conexión a la API o faltan credenciales, el sistema usará datos de ejemplo para desarrollo y testing.

## 📈 Métricas Disponibles

- **Ventas Totales**: Suma de todas las ventas en el período
- **Número de Transacciones**: Cantidad total de ventas
- **Ticket Promedio**: Promedio por transacción
- **Mediana de Transacciones**: Valor mediano
- **Mejor Día**: Día con mayores ventas
- **Peor Día**: Día con menores ventas
- **Mejor Hora**: Hora del día con mayores ventas

## 🛠️ Personalización

### Modificar el formato de datos esperado

Si la API de Fudo retorna datos en un formato diferente, ajusta la función `_process_data()` en `analytics.py` para mapear correctamente los campos.

### Agregar nuevas visualizaciones

Puedes agregar nuevas vistas en `app.py` siguiendo el mismo patrón de las vistas existentes.

### Cambiar el período de cache

El cache de datos se actualiza cada 5 minutos por defecto. Puedes modificarlo en `app.py` cambiando el parámetro `ttl` en `@st.cache_data(ttl=300)`.

## 🐛 Solución de Problemas

### Error de conexión a la API
- Verifica que las credenciales en `.env` sean correctas
- Revisa que la URL de la API sea correcta
- Consulta la documentación de la API de Fudo para endpoints específicos

### Datos no se muestran
- Asegúrate de que el período seleccionado tenga datos disponibles
- Revisa el formato de los datos retornados por la API

### Dependencias faltantes
```bash
# Asegúrate de activar el entorno virtual primero
source venv/bin/activate  # En macOS/Linux
pip install --upgrade -r requirements.txt
```

### Error: "command not found: streamlit"
Este error ocurre cuando intentas ejecutar streamlit sin activar el entorno virtual. 

**Solución**:
1. Activa el entorno virtual: `source venv/bin/activate`
2. Verifica que streamlit esté instalado: `pip list | grep streamlit`
3. Si no está instalado, ejecuta: `pip install -r requirements.txt`
4. Luego ejecuta: `streamlit run app.py`

## 📝 Notas

- Los datos se cachean durante 5 minutos para mejorar el rendimiento
- El dashboard usa datos de ejemplo si no hay conexión a la API (útil para desarrollo)
- Las visualizaciones son completamente interactivas (zoom, pan, hover, etc.)

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Por favor, abre un issue o pull request.

## 📄 Licencia

Este proyecto es de uso interno para análisis de ventas.

---

**Desarrollado con ❤️ para análisis estratégico de ventas gastronómicas**

