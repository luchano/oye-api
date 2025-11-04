"""
Dashboard interactivo para análisis estratégico de ventas
Utilizando la API de Fudo
"""
import streamlit as st
import plotly.express as px
import pandas as pd
import os
import hashlib

from fudo_client import FudoAPIClient
from analytics import SalesAnalytics

# Función helper para formatear montos
def format_amount(amount):
    """
    Formatea un monto para visualización.
    Los montos de la API de Fudo ya vienen en la unidad correcta (pesos),
    así que solo retornamos el valor sin conversión.
    """
    if amount is None:
        return 0.0
    # Los montos ya están en pesos, no en centavos
    # No hacer conversión
    return float(amount)

# Función para formatear montos grandes de forma compacta
def format_compact_amount(amount):
    """
    Formatea un monto grande de forma compacta para evitar overflow.
    Usa formato abreviado: M para millones, K para miles.
    
    Ejemplos:
    - 299,947,523.68 -> $299.95M
    - 1,500,000 -> $1.50M
    - 50,000 -> $50.00K
    - 500 -> $500.00
    """
    if amount is None or amount == 0:
        return "$0.00"
    
    amount = float(amount)
    
    # Si es mayor o igual a 1 millón, usar formato M
    if abs(amount) >= 1_000_000:
        return f"${amount / 1_000_000:.2f}M"
    # Si es mayor o igual a 1,000, usar formato K
    elif abs(amount) >= 1_000:
        return f"${amount / 1_000:.2f}K"
    # Si es menor a 1,000, mostrar completo sin decimales si es entero
    else:
        if amount == int(amount):
            return f"${int(amount):,}"
        else:
            return f"${amount:,.2f}"

# Configuración de la página
st.set_page_config(
    page_title="Dashboard de Ventas - Fudo",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Función de autenticación
def check_password():
    """Verifica si el usuario ha ingresado la contraseña correcta"""
    
    # Obtener contraseña de variable de entorno
    correct_password = os.getenv("DASHBOARD_PASSWORD", "")
    
    # Si no hay contraseña configurada, permitir acceso (modo desarrollo)
    if not correct_password:
        return True
    
    # Verificar si ya está autenticado
    if "password_correct" in st.session_state and st.session_state["password_correct"]:
        return True
    
    # Mostrar formulario de login
    st.markdown("""
    <div style='display: flex; justify-content: center; align-items: center; height: 80vh;'>
        <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    padding: 3rem; border-radius: 20px; box-shadow: 0 10px 40px rgba(0,0,0,0.3);
                    max-width: 400px; width: 100%;'>
            <h2 style='color: white; text-align: center; margin-bottom: 2rem;'>
                🔐 Acceso Restringido
            </h2>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    placeholder = st.empty()
    
    with placeholder.form("login"):
        st.markdown("### Ingresa la contraseña")
        password = st.text_input("Contraseña", type="password", label_visibility="collapsed")
        submit = st.form_submit_button("Ingresar", use_container_width=True)
        
        if submit:
            # Hash de la contraseña ingresada para comparación segura
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            stored_hash = hashlib.sha256(correct_password.encode()).hexdigest()
            
            if password_hash == stored_hash:
                st.session_state["password_correct"] = True
                placeholder.empty()
                st.rerun()
            else:
                st.error("❌ Contraseña incorrecta. Intenta nuevamente.")
                st.session_state["password_correct"] = False
    
    return False

# Verificar autenticación antes de mostrar el contenido
if not check_password():
    st.stop()

# CSS personalizado para diseño moderno
st.markdown("""
<style>
    /* Estilos generales */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    /* Header con gradiente */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        margin-bottom: 2rem;
        box-shadow: 0 10px 30px rgba(0,0,0,0.3);
    }
    
    .main-header h1 {
        color: white;
        font-size: 2.5rem;
        font-weight: 700;
        margin: 0;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
    }
    
    .main-header p {
        color: rgba(255,255,255,0.9);
        font-size: 1.1rem;
        margin-top: 0.5rem;
    }
    
    /* Métricas con estilo mejorado */
    [data-testid="stMetricValue"] {
        font-size: 2rem !important;
        font-weight: 700 !important;
        color: #667eea !important;
    }
    
    [data-testid="stMetricLabel"] {
        font-size: 0.9rem !important;
        font-weight: 600 !important;
        color: #FAFAFA !important;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    [data-testid="stMetricDelta"] {
        font-size: 0.85rem !important;
    }
    
    /* Sidebar mejorado */
    .css-1d391kg {
        padding-top: 2rem;
    }
    
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1e1e2e 0%, #2d2d44 100%);
    }
    
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h2 {
        color: white;
        font-weight: 600;
    }
    
    /* Cards para gráficos */
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 12px;
        color: white;
        margin-bottom: 1rem;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    }
    
    /* Botones y controles */
    [data-testid="stRadio"] label {
        font-weight: 500;
        padding: 0.5rem;
    }
    
    /* Tablas */
    [data-testid="stDataFrame"] {
        border-radius: 10px;
        overflow: hidden;
    }
    
    /* Hover effects */
    .element-container:hover {
        transform: translateY(-2px);
        transition: all 0.3s ease;
    }
    
    /* Divider mejorado */
    hr {
        border: none;
        height: 2px;
        background: linear-gradient(90deg, transparent, #667eea, transparent);
        margin: 2rem 0;
    }
    
    /* Info boxes */
    .info-box {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        margin: 1rem 0;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    }
    
    /* Warning boxes */
    [data-testid="stAlert"] {
        border-radius: 10px;
    }
    
    /* Títulos de sección */
    h2 {
        color: #667eea !important;
        font-weight: 600 !important;
        margin-top: 2rem !important;
    }
    
    h3 {
        color: #764ba2 !important;
        font-weight: 500 !important;
    }
</style>
""", unsafe_allow_html=True)

# Header principal con gradiente
st.markdown("""
<div class="main-header">
    <h1>🍽️ Dashboard de Análisis Estratégico de Ventas</h1>
    <p>Análisis en tiempo real de tu negocio gastronómico • Powered by Fudo API</p>
</div>
""", unsafe_allow_html=True)

# Sidebar para configuración con estilo mejorado
st.sidebar.markdown("""
<div style='padding: 1rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 10px; margin-bottom: 2rem;'>
    <h2 style='color: white; margin: 0; font-size: 1.3rem;'>⚙️ Configuración</h2>
</div>
""", unsafe_allow_html=True)

# Botón de cerrar sesión (si hay contraseña configurada)
if os.getenv("DASHBOARD_PASSWORD"):
    st.sidebar.markdown("---")
    if st.sidebar.button("🔓 Cerrar Sesión", use_container_width=True):
        st.session_state["password_correct"] = False
        st.rerun()

# Opciones de fecha
st.sidebar.markdown("**📅 Período de Análisis**")
days_to_analyze = st.sidebar.slider(
    "Días",
    min_value=7,
    max_value=365,
    value=30,
    step=1,
    label_visibility="collapsed"
)

st.sidebar.markdown("<br>", unsafe_allow_html=True)

# Selección de vista
st.sidebar.markdown("**📊 Vista de Análisis**")
view_type = st.sidebar.radio(
    "Selecciona la vista",
    ["📈 Resumen General", "📅 Por Día", "🕐 Por Hora", "📆 Por Mes"],
    label_visibility="collapsed"
)


# Inicializar cliente de API
@st.cache_data(ttl=300)  # Cache por 5 minutos
def load_sales_data(days: int):
    """Carga datos de ventas desde la API"""
    client = FudoAPIClient()
    sales_data = client.get_sales_by_date_range(days)
    return sales_data

# Cargar datos
with st.spinner("Cargando datos de ventas..."):
    try:
        sales_data = load_sales_data(days_to_analyze)
        # Usar zona horaria de Buenos Aires (GMT-3)
        analytics = SalesAnalytics(sales_data, timezone="America/Argentina/Buenos_Aires")
        
        if analytics.df.empty:
            st.error("No se encontraron datos de ventas para el período seleccionado.")
            st.stop()
    except Exception as e:
        st.error(f"Error al cargar datos: {str(e)}")
        st.stop()

# Mostrar vista según selección
if view_type == "📈 Resumen General":
    st.markdown("""
    <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1.5rem; border-radius: 15px; margin-bottom: 2rem; box-shadow: 0 4px 15px rgba(0,0,0,0.2);'>
        <h2 style='color: white; margin: 0; font-size: 2rem;'>📈 Resumen General</h2>
    </div>
    """, unsafe_allow_html=True)
    
    # Métricas clave con diseño mejorado
    metrics = analytics.get_key_metrics()
    
    # Row 1: Métricas principales
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_sales = format_amount(metrics.get('total_sales', 0))
        total_sales_compact = format_compact_amount(total_sales)
        avg_trans = format_amount(metrics.get('avg_transaction', 0))
        st.markdown(f"""
        <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1.5rem; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.2);'>
            <div style='color: rgba(255,255,255,0.9); font-size: 0.9rem; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 0.5rem;'>💰 Ventas Totales</div>
            <div style='color: white; font-size: 2rem; font-weight: 700; line-height: 1.2;' title='Total: ${total_sales:,.2f}'>{total_sales_compact}</div>
            <div style='color: rgba(255,255,255,0.8); font-size: 0.85rem; margin-top: 0.5rem;'>Promedio: ${avg_trans:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        median_trans = format_amount(metrics.get('median_transaction', 0))
        st.markdown(f"""
        <div style='background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); padding: 1.5rem; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.2);'>
            <div style='color: rgba(255,255,255,0.9); font-size: 0.9rem; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 0.5rem;'>🛒 Transacciones</div>
            <div style='color: white; font-size: 2rem; font-weight: 700;'>{f"{metrics.get('total_transactions', 0):,}"}</div>
            <div style='color: rgba(255,255,255,0.8); font-size: 0.85rem; margin-top: 0.5rem;'>Mediana: ${median_trans:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        best_day = metrics.get('best_day', {})
        if best_day:
            best_day_sales = format_amount(best_day.get('sales', 0))
            st.markdown(f"""
            <div style='background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); padding: 1.5rem; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.2);'>
                <div style='color: rgba(255,255,255,0.9); font-size: 0.9rem; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 0.5rem;'>⭐ Mejor Día</div>
                <div style='color: white; font-size: 1.8rem; font-weight: 700;'>{best_day.get('date', 'N/A')}</div>
                <div style='color: rgba(255,255,255,0.8); font-size: 0.85rem; margin-top: 0.5rem;'>${best_day_sales:,.2f}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style='background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); padding: 1.5rem; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.2);'>
                <div style='color: rgba(255,255,255,0.9); font-size: 0.9rem; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 0.5rem;'>⭐ Mejor Día</div>
                <div style='color: white; font-size: 1.8rem; font-weight: 700;'>N/A</div>
            </div>
            """, unsafe_allow_html=True)
    
    with col4:
        best_hour = metrics.get('best_hour', {})
        if best_hour:
            best_hour_sales = format_amount(best_hour.get('sales', 0))
            st.markdown(f"""
            <div style='background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); padding: 1.5rem; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.2);'>
                <div style='color: rgba(255,255,255,0.9); font-size: 0.9rem; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 0.5rem;'>🔥 Mejor Hora</div>
                <div style='color: white; font-size: 1.8rem; font-weight: 700;'>{f"{best_hour.get('hour', 0):02d}:00"}</div>
                <div style='color: rgba(255,255,255,0.8); font-size: 0.85rem; margin-top: 0.5rem;'>${best_hour_sales:,.2f}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style='background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); padding: 1.5rem; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.2);'>
                <div style='color: rgba(255,255,255,0.9); font-size: 0.9rem; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 0.5rem;'>🔥 Mejor Hora</div>
                <div style='color: white; font-size: 1.8rem; font-weight: 700;'>N/A</div>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Gráficos combinados
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📅 Ventas por Día de Servicio")
        daily_data = analytics.get_sales_by_day()
        if not daily_data.empty:
            # Crear copia y convertir montos
            daily_display = daily_data.copy()
            daily_display['total_sales'] = daily_display['total_sales'].apply(format_amount)
            # Gráfico de líneas - mostrar todos los días individualmente
            fig = px.line(
                daily_display,
                x='date',
                y='total_sales',
                markers=True,
                title="Evolución de Ventas por Día de Servicio",
                labels={'total_sales': 'Ventas ($)', 'date': 'Día de Servicio (inicio)'}
            )
            fig.update_traces(line_color='#1f77b4', line_width=2)
            # Configurar para mostrar cada día individualmente
            fig.update_layout(
                hovermode='x unified',
                xaxis=dict(
                    type='date',
                    tickmode='linear',
                    dtick=86400000.0,  # Un día en milisegundos
                    tickformat='%d/%m',  # Formato: día/mes
                    showgrid=True,
                    nticks=min(len(daily_display), 30)  # Máximo 30 días para evitar saturación
                )
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No hay datos disponibles para mostrar")
    
    with col2:
        st.subheader("🕐 Ventas por Hora del Día")
        hourly_data = analytics.get_sales_by_hour()
        if not hourly_data.empty:
            # Crear copia y convertir montos
            hourly_display = hourly_data.copy()
            hourly_display['total_sales'] = hourly_display['total_sales'].apply(format_amount)
            # Usar hour_label para el eje X y mantener el orden correcto
            fig = px.bar(
                hourly_display,
                x='hour_label',
                y='total_sales',
                title="Distribución de Ventas por Hora (desde 12:00)",
                labels={'total_sales': 'Ventas ($)', 'hour_label': 'Hora del Día'},
                color='total_sales',
                color_continuous_scale='Viridis',
                category_orders={'hour_label': hourly_display['hour_label'].tolist()}
            )
            fig.update_layout(xaxis=dict(type='category'))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No hay datos disponibles para mostrar")
    
    # Gráfico de días de la semana
    st.subheader("📊 Ventas por Día de la Semana")
    weekday_data = analytics.get_sales_by_weekday()
    if not weekday_data.empty:
        # Crear copia y convertir montos
        weekday_display = weekday_data.copy()
        weekday_display['total_sales'] = weekday_display['total_sales'].apply(format_amount)
        fig = px.bar(
            weekday_display,
            x='weekday',
            y='total_sales',
            title="Comparación de Ventas por Día de la Semana",
            labels={'total_sales': 'Ventas ($)', 'weekday': 'Día de la Semana'},
            color='total_sales',
            color_continuous_scale='Blues'
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No hay datos disponibles para mostrar")

elif view_type == "📅 Por Día":
    st.markdown("""
    <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1.5rem; border-radius: 15px; margin-bottom: 2rem; box-shadow: 0 4px 15px rgba(0,0,0,0.2);'>
        <h2 style='color: white; margin: 0; font-size: 2rem;'>📅 Análisis de Ventas por Día de Servicio</h2>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div style='background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); padding: 1rem; border-radius: 10px; margin-bottom: 1.5rem; box-shadow: 0 4px 15px rgba(0,0,0,0.2);'>
        <p style='color: white; margin: 0; font-size: 0.95rem;'>
            <strong>ℹ️ Día de Servicio:</strong> Incluye ventas desde las 12:00 del día hasta las 05:00 del día siguiente. 
            Todo se atribuye al día en que empezó el servicio (día de apertura).
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    daily_data = analytics.get_sales_by_day()
    
    if not daily_data.empty:
        # Crear copia y convertir montos
        daily_display = daily_data.copy()
        daily_display['total_sales'] = daily_display['total_sales'].apply(format_amount)
        daily_display['avg_sale'] = daily_display['avg_sale'].apply(format_amount)
        
        # Gráfico de líneas - mostrar todos los días individualmente
        fig = px.line(
            daily_display,
            x='date',
            y='total_sales',
            markers=True,
            title="Evolución de Ventas por Día de Servicio",
            labels={'total_sales': 'Ventas Totales ($)', 'date': 'Día de Servicio (inicio)'},
            hover_data=['num_transactions', 'avg_sale']
        )
        fig.update_traces(line_color='#2E86AB', line_width=3)
        # Configurar para mostrar cada día individualmente sin agrupar
        fig.update_layout(
            hovermode='x unified', 
            height=500,
            xaxis=dict(
                type='date',
                tickmode='linear',
                dtick=86400000.0,  # Un día en milisegundos (24 horas)
                tickformat='%d/%m',  # Formato: día/mes
                showgrid=True,
                nticks=len(daily_display)  # Mostrar un tick por cada día
            )
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Gráfico de barras - mostrar todos los días individualmente
        fig2 = px.bar(
            daily_display,
            x='date',
            y='total_sales',
            title="Ventas por Día de Servicio (Barras)",
            labels={'total_sales': 'Ventas Totales ($)', 'date': 'Día de Servicio (inicio)'},
            color='total_sales',
            color_continuous_scale='Blues'
        )
        # Configurar para mostrar cada día individualmente
        fig2.update_layout(
            height=400,
            xaxis=dict(
                type='date',
                tickmode='linear',
                dtick=86400000.0,  # Un día en milisegundos
                tickformat='%d/%m',  # Formato: día/mes
                showgrid=True,
                nticks=min(len(daily_display), 30)  # Máximo 30 días para evitar saturación
            )
        )
        st.plotly_chart(fig2, use_container_width=True)
        
        # Tabla de datos
        st.subheader("📋 Datos Detallados por Día de Servicio")
        daily_table = daily_display.copy()
        daily_table['date'] = daily_table['date'].dt.strftime('%Y-%m-%d')
        daily_table['total_sales'] = daily_table['total_sales'].apply(lambda x: f"${x:,.2f}")
        daily_table['avg_sale'] = daily_table['avg_sale'].apply(lambda x: f"${x:,.2f}")
        daily_table.columns = ['Día de Servicio (inicio)', 'Ventas Totales', 'Ticket Promedio', 'N° Transacciones']
        st.dataframe(daily_table, use_container_width=True, hide_index=True)
    else:
        st.warning("No hay datos disponibles para mostrar")

elif view_type == "🕐 Por Hora":
    st.markdown("""
    <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1.5rem; border-radius: 15px; margin-bottom: 2rem; box-shadow: 0 4px 15px rgba(0,0,0,0.2);'>
        <h2 style='color: white; margin: 0; font-size: 2rem;'>🕐 Análisis de Ventas por Hora</h2>
    </div>
    """, unsafe_allow_html=True)
    
    hourly_data = analytics.get_sales_by_hour()
    
    if not hourly_data.empty:
        # Crear copia y convertir montos
        hourly_display = hourly_data.copy()
        hourly_display['total_sales'] = hourly_display['total_sales'].apply(format_amount)
        hourly_display['avg_sale'] = hourly_display['avg_sale'].apply(format_amount)
        
        # Gráfico de barras (ordenado desde 12:00)
        fig = px.bar(
            hourly_display,
            x='hour_label',
            y='total_sales',
            title="Ventas por Hora del Día (desde 12:00)",
            labels={'total_sales': 'Ventas Totales ($)', 'hour_label': 'Hora'},
            color='total_sales',
            color_continuous_scale='Viridis',
            hover_data=['num_transactions', 'avg_sale'],
            category_orders={'hour_label': hourly_display['hour_label'].tolist()}
        )
        fig.update_layout(
            xaxis=dict(type='category'),
            height=500
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Gráfico de área (ordenado desde 12:00)
        fig2 = px.area(
            hourly_display,
            x='hour_label',
            y='total_sales',
            title="Distribución de Ventas por Hora (Área) - desde 12:00",
            labels={'total_sales': 'Ventas Totales ($)', 'hour_label': 'Hora'},
            category_orders={'hour_label': hourly_display['hour_label'].tolist()}
        )
        # Configurar el relleno del área
        fig2.update_traces(fill='tozeroy')
        fig2.update_layout(
            xaxis=dict(type='category'),
            height=400
        )
        st.plotly_chart(fig2, use_container_width=True)
        
        # Análisis de horas pico
        st.subheader("🔥 Análisis de Horas Pico")
        top_hours = hourly_display.nlargest(5, 'total_sales')
        for idx, row in top_hours.iterrows():
            st.metric(
                label=f"Hora {row['hour_label']}",
                value=f"${row['total_sales']:,.2f}",
                delta=f"{int(row['num_transactions'])} transacciones"
            )
        
        # Tabla de datos (mantener orden desde 12:00)
        st.subheader("📋 Datos Detallados por Hora")
        hourly_table = hourly_display.copy()
        hourly_table = hourly_table[['hour_label', 'total_sales', 'avg_sale', 'num_transactions']].copy()
        hourly_table['total_sales'] = hourly_table['total_sales'].apply(lambda x: f"${x:,.2f}")
        hourly_table['avg_sale'] = hourly_table['avg_sale'].apply(lambda x: f"${x:,.2f}")
        hourly_table.columns = ['Hora', 'Ventas Totales', 'Ticket Promedio', 'N° Transacciones']
        st.dataframe(hourly_table, use_container_width=True, hide_index=True)
    else:
        st.warning("No hay datos disponibles para mostrar")

elif view_type == "📆 Por Mes":
    st.markdown("""
    <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1.5rem; border-radius: 15px; margin-bottom: 2rem; box-shadow: 0 4px 15px rgba(0,0,0,0.2);'>
        <h2 style='color: white; margin: 0; font-size: 2rem;'>📆 Análisis de Ventas por Mes</h2>
    </div>
    """, unsafe_allow_html=True)
    
    monthly_data = analytics.get_sales_by_month()
    
    if not monthly_data.empty:
        # Crear copia y convertir montos
        monthly_display = monthly_data.copy()
        monthly_display['total_sales'] = monthly_display['total_sales'].apply(format_amount)
        monthly_display['avg_sale'] = monthly_display['avg_sale'].apply(format_amount)
        
        # Gráfico de barras
        fig = px.bar(
            monthly_display,
            x='month_str',
            y='total_sales',
            title="Ventas Mensuales",
            labels={'total_sales': 'Ventas Totales ($)', 'month_str': 'Mes'},
            color='total_sales',
            color_continuous_scale='Greens',
            hover_data=['num_transactions', 'avg_sale']
        )
        fig.update_layout(height=500)
        st.plotly_chart(fig, use_container_width=True)
        
        # Gráfico de líneas con tendencia
        fig2 = px.line(
            monthly_display,
            x='month_str',
            y='total_sales',
            markers=True,
            title="Tendencia de Ventas Mensuales",
            labels={'total_sales': 'Ventas Totales ($)', 'month_str': 'Mes'}
        )
        fig2.update_traces(line_color='#28A745', line_width=3)
        fig2.update_layout(height=400)
        st.plotly_chart(fig2, use_container_width=True)
        
        # Tabla de datos
        st.subheader("📋 Datos Detallados por Mes")
        monthly_table = monthly_display.copy()
        monthly_table['total_sales'] = monthly_table['total_sales'].apply(lambda x: f"${x:,.2f}")
        monthly_table['avg_sale'] = monthly_table['avg_sale'].apply(lambda x: f"${x:,.2f}")
        monthly_table = monthly_table[['month_str', 'total_sales', 'avg_sale', 'num_transactions']]
        monthly_table.columns = ['Mes', 'Ventas Totales', 'Ticket Promedio', 'N° Transacciones']
        st.dataframe(monthly_table, use_container_width=True, hide_index=True)
    else:
        st.warning("No hay datos disponibles para mostrar")

# Footer mejorado
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown(
    """
    <div style='text-align: center; padding: 2rem; background: linear-gradient(135deg, #1e1e2e 0%, #2d2d44 100%); border-radius: 15px; margin-top: 2rem;'>
        <p style='color: rgba(255,255,255,0.7); margin: 0; font-size: 0.9rem;'>
            📊 Dashboard de Análisis Estratégico de Ventas | Powered by <strong style='color: #667eea;'>Fudo API</strong>
        </p>
    </div>
    """,
    unsafe_allow_html=True
)

