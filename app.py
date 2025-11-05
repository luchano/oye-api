"""
Dashboard interactivo para análisis estratégico de ventas
Utilizando la API de Fudo
"""
import streamlit as st
import plotly.express as px
import pandas as pd
import os
import hashlib
from datetime import datetime, timedelta

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
    # Si la variable no existe, os.getenv retorna None
    correct_password = os.getenv("DASHBOARD_PASSWORD")
    
    # Si la variable no está definida o es None, permitir acceso
    if correct_password is None:
        # Limpiar el estado de sesión si existe
        if "password_correct" in st.session_state:
            del st.session_state["password_correct"]
        return True
    
    # Convertir a string y limpiar
    correct_password = str(correct_password).strip()
    
    # Si está vacía o comienza con # (comentario), permitir acceso
    if not correct_password or correct_password.startswith("#"):
        # Limpiar el estado de sesión si existe
        if "password_correct" in st.session_state:
            del st.session_state["password_correct"]
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
# Forzar limpieza del estado si la contraseña no está configurada
dashboard_password = os.getenv("DASHBOARD_PASSWORD")
if dashboard_password is None or (isinstance(dashboard_password, str) and dashboard_password.strip().startswith("#")):
    # Si la contraseña está comentada o no existe, limpiar estado de sesión
    if "password_correct" in st.session_state:
        del st.session_state["password_correct"]

if not check_password():
    st.stop()

# CSS personalizado para diseño moderno
st.markdown("""
<style>
    /* Estilos generales - más compacto */
    .main .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
    }
    
    /* Header con gradiente - más compacto */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem 1.5rem;
        border-radius: 10px;
        margin-bottom: 1rem;
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
    }
    
    .main-header h1 {
        color: white;
        font-size: 1.8rem;
        font-weight: 700;
        margin: 0;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.2);
    }
    
    .main-header p {
        color: rgba(255,255,255,0.9);
        font-size: 0.9rem;
        margin-top: 0.25rem;
    }
    
    /* Métricas más compactas */
    [data-testid="stMetricValue"] {
        font-size: 1.5rem !important;
        font-weight: 700 !important;
        color: #667eea !important;
    }
    
    [data-testid="stMetricLabel"] {
        font-size: 0.8rem !important;
        font-weight: 600 !important;
        color: #FAFAFA !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    [data-testid="stMetricDelta"] {
        font-size: 0.75rem !important;
    }
    
    /* Sidebar más compacto */
    .css-1d391kg {
        padding-top: 1rem;
    }
    
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1e1e2e 0%, #2d2d44 100%);
    }
    
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h2 {
        color: white;
        font-weight: 600;
    }
    
    /* Cards para gráficos - más compactas */
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        margin-bottom: 0.75rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.15);
    }
    
    /* Botones y controles - más compactos */
    [data-testid="stRadio"] label {
        font-weight: 500;
        padding: 0.25rem;
        font-size: 0.9rem;
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
    
    /* Títulos de sección - más compactos */
    h2 {
        color: #667eea !important;
        font-weight: 600 !important;
        margin-top: 1rem !important;
        font-size: 1.3rem !important;
    }
    
    h3 {
        color: #764ba2 !important;
        font-weight: 500 !important;
        font-size: 1.1rem !important;
    }
    
    h4 {
        font-size: 1rem !important;
        margin-top: 0.75rem !important;
    }
</style>
""", unsafe_allow_html=True)

# Header principal con gradiente
st.markdown("""
<div class="main-header">
    <h1>🍽️ Dashboard de Análisis Estratégico de Ventas</h1>
    <p style='font-size: 0.9rem; margin-top: 0.25rem;'>Análisis en tiempo real • Powered by Fudo API</p>
</div>
""", unsafe_allow_html=True)

# Sidebar para configuración más compacto
st.sidebar.markdown("""
<div style='padding: 0.75rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 8px; margin-bottom: 1rem;'>
    <h3 style='color: white; margin: 0; font-size: 1.1rem;'>⚙️ Configuración</h3>
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

# Obtener fecha actual
today = datetime.now().date()

# Botones de preset compactos
st.sidebar.markdown("**Presets rápidos:**")
preset_cols = st.sidebar.columns(3)

with preset_cols[0]:
    if st.button("30d", use_container_width=True, help="Últimos 30 días"):
        st.session_state['start_date'] = today - timedelta(days=30)
        st.session_state['end_date'] = today
        st.rerun()
    if st.button("90d", use_container_width=True, help="Último trimestre"):
        st.session_state['start_date'] = today - timedelta(days=90)
        st.session_state['end_date'] = today
        st.rerun()

with preset_cols[1]:
    if st.button("7d", use_container_width=True, help="Última semana"):
        st.session_state['start_date'] = today - timedelta(days=7)
        st.session_state['end_date'] = today
        st.rerun()
    if st.button("180d", use_container_width=True, help="Último semestre"):
        st.session_state['start_date'] = today - timedelta(days=180)
        st.session_state['end_date'] = today
        st.rerun()

with preset_cols[2]:
    if st.button("Mes", use_container_width=True, help="Mes anterior"):
        first_day_last_month = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
        last_day_last_month = today.replace(day=1) - timedelta(days=1)
        st.session_state['start_date'] = first_day_last_month
        st.session_state['end_date'] = last_day_last_month
        st.rerun()

# Inicializar fechas en session_state si no existen
if 'start_date' not in st.session_state:
    st.session_state['start_date'] = today - timedelta(days=30)
if 'end_date' not in st.session_state:
    st.session_state['end_date'] = today

# Selectores de fecha compactos
st.sidebar.markdown("**Rango personalizado:**")
date_cols = st.sidebar.columns(2)
with date_cols[0]:
    start_date = st.date_input(
        "Inicio",
        value=st.session_state['start_date'],
        max_value=today,
        help="Fecha de inicio",
        label_visibility="visible"
    )
with date_cols[1]:
    end_date = st.date_input(
        "Fin",
        value=st.session_state['end_date'],
        max_value=today,
        min_value=start_date,
        help="Fecha de fin",
        label_visibility="visible"
    )

# Actualizar session_state si las fechas cambiaron manualmente
if start_date != st.session_state.get('start_date'):
    st.session_state['start_date'] = start_date
if end_date != st.session_state.get('end_date'):
    st.session_state['end_date'] = end_date

# Validar que la fecha fin sea mayor o igual a la fecha inicio
if end_date < start_date:
    st.sidebar.error("⚠️ La fecha fin debe ser mayor o igual a la fecha inicio")
    st.stop()

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
def load_sales_data(start_date: str, end_date: str, include_related: bool = False):
    """Carga datos de ventas desde la API"""
    client = FudoAPIClient()
    sales_data = client.get_sales(
        start_date=start_date,
        end_date=end_date,
        include_related=include_related
    )
    return sales_data, client

# Cargar datos
with st.spinner("Cargando datos de ventas..."):
    try:
        # Convertir fechas a formato string para la API
        start_date_str = start_date.strftime("%Y-%m-%d")
        end_date_str = end_date.strftime("%Y-%m-%d")
        
        # Cargar con include para obtener items.product.productCategory en una sola petición
        sales_data, client = load_sales_data(start_date_str, end_date_str, include_related=True)
        # Usar zona horaria de Buenos Aires (GMT-3)
        analytics = SalesAnalytics(sales_data, timezone="America/Argentina/Buenos_Aires", api_client=client)
        
        if analytics.df.empty:
            st.error("No se encontraron datos de ventas para el período seleccionado.")
            st.stop()
    except Exception as e:
        st.error(f"Error al cargar datos: {str(e)}")
        st.stop()

# Mostrar vista según selección
if view_type == "📈 Resumen General":
    st.markdown("""
    <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1rem; border-radius: 10px; margin-bottom: 1rem; box-shadow: 0 2px 8px rgba(0,0,0,0.15);'>
        <h2 style='color: white; margin: 0; font-size: 1.5rem;'>📈 Resumen General</h2>
    </div>
    """, unsafe_allow_html=True)
    
    # Métricas clave con diseño mejorado
    metrics = analytics.get_key_metrics()
    
    # Row 1: Métricas principales
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        total_sales = format_amount(metrics.get('total_sales', 0))
        total_sales_compact = format_compact_amount(total_sales)
        avg_trans = format_amount(metrics.get('avg_transaction', 0))
        st.markdown(f"""
        <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1rem; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.15);'>
            <div style='color: rgba(255,255,255,0.9); font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 0.25rem;'>💰 Ventas Totales</div>
            <div style='color: white; font-size: 1.5rem; font-weight: 700; line-height: 1.2;' title='Total: ${total_sales:,.2f}'>{total_sales_compact}</div>
            <div style='color: rgba(255,255,255,0.8); font-size: 0.75rem; margin-top: 0.25rem;'>Promedio: ${avg_trans:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        median_trans = format_amount(metrics.get('median_transaction', 0))
        st.markdown(f"""
        <div style='background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); padding: 1rem; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.15);'>
            <div style='color: rgba(255,255,255,0.9); font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 0.25rem;'>🛒 Transacciones</div>
            <div style='color: white; font-size: 1.5rem; font-weight: 700;'>{f"{metrics.get('total_transactions', 0):,}"}</div>
            <div style='color: rgba(255,255,255,0.8); font-size: 0.75rem; margin-top: 0.25rem;'>Mediana: ${median_trans:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        best_day = metrics.get('best_day', {})
        if best_day:
            best_day_sales = format_amount(best_day.get('sales', 0))
            st.markdown(f"""
            <div style='background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); padding: 1rem; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.15);'>
                <div style='color: rgba(255,255,255,0.9); font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 0.25rem;'>⭐ Mejor Día</div>
                <div style='color: white; font-size: 1.2rem; font-weight: 700;'>{best_day.get('date', 'N/A')}</div>
                <div style='color: rgba(255,255,255,0.8); font-size: 0.75rem; margin-top: 0.25rem;'>${best_day_sales:,.2f}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style='background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); padding: 1rem; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.15);'>
                <div style='color: rgba(255,255,255,0.9); font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 0.25rem;'>⭐ Mejor Día</div>
                <div style='color: white; font-size: 1.2rem; font-weight: 700;'>N/A</div>
            </div>
            """, unsafe_allow_html=True)
    
    with col4:
        best_hour = metrics.get('best_hour', {})
        if best_hour:
            best_hour_sales = format_amount(best_hour.get('sales', 0))
            st.markdown(f"""
            <div style='background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); padding: 1rem; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.15);'>
                <div style='color: rgba(255,255,255,0.9); font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 0.25rem;'>🔥 Mejor Hora</div>
                <div style='color: white; font-size: 1.2rem; font-weight: 700;'>{f"{best_hour.get('hour', 0):02d}:00"}</div>
                <div style='color: rgba(255,255,255,0.8); font-size: 0.75rem; margin-top: 0.25rem;'>${best_hour_sales:,.2f}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style='background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); padding: 1rem; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.15);'>
                <div style='color: rgba(255,255,255,0.9); font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 0.25rem;'>🔥 Mejor Hora</div>
                <div style='color: white; font-size: 1.2rem; font-weight: 700;'>N/A</div>
            </div>
            """, unsafe_allow_html=True)
    
    with col5:
        total_people = metrics.get('total_people', 0)
        avg_people = metrics.get('avg_people_per_transaction', 0)
        st.markdown(f"""
        <div style='background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%); padding: 1rem; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.15);'>
            <div style='color: rgba(255,255,255,0.9); font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 0.25rem;'>👥 Número de Pax</div>
            <div style='color: white; font-size: 1.5rem; font-weight: 700;'>{total_people:,}</div>
            <div style='color: rgba(255,255,255,0.8); font-size: 0.75rem; margin-top: 0.25rem;'>Promedio: {avg_people:,.1f}</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Gráfico de número de Pax por día
    st.subheader("👥 Número de Pax por Día")
    daily_pax_data = analytics.get_sales_by_day()
    if not daily_pax_data.empty and 'total_people' in daily_pax_data.columns:
        daily_pax_display = daily_pax_data.copy()
        
        # Gráfico de barras de número de Pax por día
        fig_pax_daily = px.bar(
            daily_pax_display,
            x='date',
            y='total_people',
            title="Número de Personas Atendidas por Día de Servicio",
            labels={'total_people': 'Número de Pax', 'date': 'Día de Servicio'},
            color='total_people',
            color_continuous_scale='Blues'
        )
        fig_pax_daily.update_layout(
            xaxis=dict(
                type='date',
                tickmode='linear',
                dtick=86400000.0,
                tickformat='%d/%m',
                showgrid=True
            ),
            height=500,
            yaxis_title="Número de Pax"
        )
        st.plotly_chart(fig_pax_daily, use_container_width=True)
        
        # Gráfico de líneas para número de Pax
        fig_pax_line = px.line(
            daily_pax_display,
            x='date',
            y='total_people',
            markers=True,
            title="Evolución del Número de Personas por Día",
            labels={'total_people': 'Número de Pax', 'date': 'Día de Servicio'},
        )
        fig_pax_line.update_traces(line_color='#43e97b', line_width=3)
        fig_pax_line.update_layout(
            xaxis=dict(
                type='date',
                tickmode='linear',
                dtick=86400000.0,
                tickformat='%d/%m',
                showgrid=True
            ),
            height=400,
            yaxis_title="Número de Pax"
        )
        st.plotly_chart(fig_pax_line, use_container_width=True)
    else:
        st.info("ℹ️ No hay datos de número de personas disponibles")
    
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
    
    # Gráfico de ventas por categoría
    st.subheader("🏷️ Ventas por Categoría de Productos")
    category_data = analytics.get_sales_by_category(debug=True)
    if not category_data.empty:
        # Crear copia y convertir montos
        category_display = category_data.copy()
        category_display['total_sales'] = category_display['total_sales'].apply(format_amount)
        
        # Gráfico de barras horizontales para mejor visualización
        fig = px.bar(
            category_display,
            x='total_sales',
            y='category',
            orientation='h',
            title="Distribución de Ventas por Categoría",
            labels={'total_sales': 'Ventas ($)', 'category': 'Categoría'},
            color='total_sales',
            color_continuous_scale='Plasma'
        )
        fig.update_layout(
            yaxis={'categoryorder': 'total ascending'},
            height=max(400, len(category_display) * 50)  # Altura dinámica según número de categorías
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Mostrar tabla con detalles
        st.markdown("#### 📋 Detalles por Categoría")
        category_table = category_display.copy()
        category_table['total_sales'] = category_table['total_sales'].apply(lambda x: f"${x:,.2f}")
        category_table['avg_sale'] = category_table['avg_sale'].apply(lambda x: f"${x:,.2f}")
        category_table.columns = ['Categoría', 'Ventas Totales', 'N° Transacciones', 'Ticket Promedio']
        st.dataframe(category_table, use_container_width=True, hide_index=True)
    else:
        st.info("ℹ️ No se encontraron datos de categorías en las ventas. Esto puede deberse a que la API no incluye información de categorías de productos en los datos de ventas.")

elif view_type == "📅 Por Día":
    st.markdown("""
    <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1rem; border-radius: 10px; margin-bottom: 1rem; box-shadow: 0 2px 8px rgba(0,0,0,0.15);'>
        <h2 style='color: white; margin: 0; font-size: 1.5rem;'>📅 Análisis de Ventas por Día de Servicio</h2>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div style='background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); padding: 1rem; border-radius: 10px; margin-bottom: 1rem; box-shadow: 0 4px 15px rgba(0,0,0,0.2);'>
        <p style='color: white; margin: 0; font-size: 0.95rem;'>
            <strong>ℹ️ Día de Servicio:</strong> Incluye ventas desde las 12:00 del día hasta las 05:00 del día siguiente. 
            Todo se atribuye al día en que empezó el servicio (día de apertura).
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Gráfico de ventas por día con desglose por categoría
    st.subheader("📊 Ventas por Día Desglosadas por Categoría")
    daily_category_data = analytics.get_sales_by_day_and_category(top_n=10)
    if not daily_category_data.empty:
        daily_category_display = daily_category_data.copy()
        daily_category_display['total_sales'] = daily_category_display['total_sales'].apply(format_amount)
        
        # Crear gráfico de barras apiladas
        fig = px.bar(
            daily_category_display,
            x='date',
            y='total_sales',
            color='category',
            title="Ventas por Día Desglosadas por Categoría (Top 10 + Otros)",
            labels={'total_sales': 'Ventas ($)', 'date': 'Día de Servicio', 'category': 'Categoría'},
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        fig.update_layout(
            xaxis=dict(
                type='date',
                dtick=86400000.0,  # Un día en milisegundos
                tickformat='%d/%m',
                showgrid=True
            ),
            barmode='stack',
            height=500
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("ℹ️ No hay datos disponibles para mostrar el desglose por categoría")
    
    # Gráfico de número de Pax por día
    st.subheader("👥 Número de Pax por Día")
    daily_pax_data = analytics.get_sales_by_day()
    
    if not daily_pax_data.empty and 'total_people' in daily_pax_data.columns:
        daily_pax_display = daily_pax_data.copy()
        
        # Gráfico de barras de número de Pax por día
        fig_pax_daily = px.bar(
            daily_pax_display,
            x='date',
            y='total_people',
            title="Número de Personas Atendidas por Día de Servicio",
            labels={'total_people': 'Número de Pax', 'date': 'Día de Servicio'},
            color='total_people',
            color_continuous_scale='Blues'
        )
        fig_pax_daily.update_layout(
            xaxis=dict(
                type='date',
                tickmode='linear',
                dtick=86400000.0,
                tickformat='%d/%m',
                showgrid=True
            ),
            height=500,
            yaxis_title="Número de Pax"
        )
        st.plotly_chart(fig_pax_daily, use_container_width=True)
        
        # Gráfico de líneas para número de Pax
        fig_pax_line = px.line(
            daily_pax_display,
            x='date',
            y='total_people',
            markers=True,
            title="Evolución del Número de Personas por Día",
            labels={'total_people': 'Número de Pax', 'date': 'Día de Servicio'},
        )
        fig_pax_line.update_traces(line_color='#43e97b', line_width=3)
        fig_pax_line.update_layout(
            xaxis=dict(
                type='date',
                tickmode='linear',
                dtick=86400000.0,
                tickformat='%d/%m',
                showgrid=True
            ),
            height=400,
            yaxis_title="Número de Pax"
        )
        st.plotly_chart(fig_pax_line, use_container_width=True)
    else:
        st.info("ℹ️ No hay datos de número de personas disponibles")
    
    # Gráfico tradicional de ventas por día (sin desglose)
    st.subheader("📈 Ventas Totales por Día")
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
        if 'total_people' in daily_table.columns:
            daily_table['total_people'] = daily_table['total_people'].apply(lambda x: f"{int(x):,}")
            daily_table.columns = ['Día de Servicio (inicio)', 'Ventas Totales', 'Ticket Promedio', 'N° Transacciones', 'Número de Pax']
        else:
            daily_table.columns = ['Día de Servicio (inicio)', 'Ventas Totales', 'Ticket Promedio', 'N° Transacciones']
        st.dataframe(daily_table, use_container_width=True, hide_index=True)
    else:
        st.warning("No hay datos disponibles para mostrar")

elif view_type == "🕐 Por Hora":
    st.markdown("""
    <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1rem; border-radius: 10px; margin-bottom: 1rem; box-shadow: 0 2px 8px rgba(0,0,0,0.15);'>
        <h2 style='color: white; margin: 0; font-size: 1.5rem;'>🕐 Análisis de Ventas por Hora</h2>
    </div>
    """, unsafe_allow_html=True)
    
    # Gráfico de ventas por hora con desglose por categoría
    st.subheader("📊 Ventas por Hora Desglosadas por Categoría")
    hourly_category_data = analytics.get_sales_by_hour_and_category(top_n=10)
    if not hourly_category_data.empty:
        hourly_category_display = hourly_category_data.copy()
        hourly_category_display['total_sales'] = hourly_category_display['total_sales'].apply(format_amount)
        
        # Crear gráfico de barras apiladas
        fig = px.bar(
            hourly_category_display,
            x='hour_label',
            y='total_sales',
            color='category',
            title="Ventas por Hora Desglosadas por Categoría (Top 10 + Otros)",
            labels={'total_sales': 'Ventas ($)', 'hour_label': 'Hora del Día', 'category': 'Categoría'},
            category_orders={'hour_label': hourly_category_display['hour_label'].unique().tolist()},
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        fig.update_layout(
            xaxis=dict(type='category'),
            barmode='stack',
            height=500
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("ℹ️ No hay datos disponibles para mostrar el desglose por categoría")
    
    # Gráfico de número de Pax por hora
    st.subheader("👥 Número de Pax por Hora")
    hourly_data = analytics.get_sales_by_hour()
    
    if not hourly_data.empty and 'total_people' in hourly_data.columns:
        hourly_pax_display = hourly_data.copy()
        
        # Gráfico de barras de número de Pax por hora
        fig_pax = px.bar(
            hourly_pax_display,
            x='hour_label',
            y='total_people',
            title="Número de Personas Atendidas por Hora del Día (desde 12:00)",
            labels={'total_people': 'Número de Pax', 'hour_label': 'Hora'},
            color='total_people',
            color_continuous_scale='Blues',
            category_orders={'hour_label': hourly_pax_display['hour_label'].tolist()}
        )
        fig_pax.update_layout(
            xaxis=dict(type='category'),
            height=500,
            yaxis_title="Número de Pax"
        )
        st.plotly_chart(fig_pax, use_container_width=True)
        
        # Gráfico de área para número de Pax
        fig_pax_area = px.area(
            hourly_pax_display,
            x='hour_label',
            y='total_people',
            title="Distribución de Personas por Hora (Área) - desde 12:00",
            labels={'total_people': 'Número de Pax', 'hour_label': 'Hora'},
            category_orders={'hour_label': hourly_pax_display['hour_label'].tolist()}
        )
        fig_pax_area.update_traces(fill='tozeroy', line_color='#43e97b')
        fig_pax_area.update_layout(
            xaxis=dict(type='category'),
            height=400,
            yaxis_title="Número de Pax"
        )
        st.plotly_chart(fig_pax_area, use_container_width=True)
    else:
        st.info("ℹ️ No hay datos de número de personas disponibles")
    
    # Gráfico tradicional de ventas por hora (sin desglose)
    st.subheader("📈 Ventas Totales por Hora")
    
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
        
        # Formatear valores antes de renombrar columnas
        hourly_table['total_sales'] = hourly_table['total_sales'].apply(lambda x: f"${x:,.2f}")
        hourly_table['avg_sale'] = hourly_table['avg_sale'].apply(lambda x: f"${x:,.2f}")
        
        if 'total_people' in hourly_table.columns:
            hourly_table['total_people'] = hourly_table['total_people'].apply(lambda x: f"{int(x):,}")
            hourly_table = hourly_table[['hour_label', 'total_sales', 'avg_sale', 'num_transactions', 'total_people']].copy()
            hourly_table.columns = ['Hora', 'Ventas Totales', 'Ticket Promedio', 'N° Transacciones', 'Número de Pax']
        else:
            hourly_table = hourly_table[['hour_label', 'total_sales', 'avg_sale', 'num_transactions']].copy()
            hourly_table.columns = ['Hora', 'Ventas Totales', 'Ticket Promedio', 'N° Transacciones']
        
        st.dataframe(hourly_table, use_container_width=True, hide_index=True)
    else:
        st.warning("No hay datos disponibles para mostrar")

elif view_type == "📆 Por Mes":
    st.markdown("""
    <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1rem; border-radius: 10px; margin-bottom: 1rem; box-shadow: 0 2px 8px rgba(0,0,0,0.15);'>
        <h2 style='color: white; margin: 0; font-size: 1.5rem;'>📆 Análisis de Ventas por Mes</h2>
    </div>
    """, unsafe_allow_html=True)
    
    # Gráfico de ventas por mes con desglose por categoría
    st.subheader("📊 Ventas por Mes Desglosadas por Categoría")
    monthly_category_data = analytics.get_sales_by_month_and_category(top_n=10)
    if not monthly_category_data.empty:
        monthly_category_display = monthly_category_data.copy()
        monthly_category_display['total_sales'] = monthly_category_display['total_sales'].apply(format_amount)
        
        # Crear gráfico de barras apiladas
        fig = px.bar(
            monthly_category_display,
            x='month_str',
            y='total_sales',
            color='category',
            title="Ventas por Mes Desglosadas por Categoría (Top 10 + Otros)",
            labels={'total_sales': 'Ventas ($)', 'month_str': 'Mes', 'category': 'Categoría'},
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        fig.update_layout(
            xaxis=dict(type='category'),
            barmode='stack',
            height=500
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("ℹ️ No hay datos disponibles para mostrar el desglose por categoría")
    
    # Gráfico de número de Pax por mes
    st.subheader("👥 Número de Pax por Mes")
    monthly_pax_data = analytics.get_sales_by_month()
    
    if not monthly_pax_data.empty and 'total_people' in monthly_pax_data.columns:
        monthly_pax_display = monthly_pax_data.copy()
        
        # Gráfico de barras de número de Pax por mes
        fig_pax_monthly = px.bar(
            monthly_pax_display,
            x='month_str',
            y='total_people',
            title="Número de Personas Atendidas por Mes",
            labels={'total_people': 'Número de Pax', 'month_str': 'Mes'},
            color='total_people',
            color_continuous_scale='Blues'
        )
        fig_pax_monthly.update_layout(
            xaxis=dict(type='category'),
            height=500,
            yaxis_title="Número de Pax"
        )
        st.plotly_chart(fig_pax_monthly, use_container_width=True)
        
        # Gráfico de líneas para número de Pax
        fig_pax_monthly_line = px.line(
            monthly_pax_display,
            x='month_str',
            y='total_people',
            markers=True,
            title="Evolución del Número de Personas por Mes",
            labels={'total_people': 'Número de Pax', 'month_str': 'Mes'},
        )
        fig_pax_monthly_line.update_traces(line_color='#43e97b', line_width=3)
        fig_pax_monthly_line.update_layout(
            xaxis=dict(type='category'),
            height=400,
            yaxis_title="Número de Pax"
        )
        st.plotly_chart(fig_pax_monthly_line, use_container_width=True)
    else:
        st.info("ℹ️ No hay datos de número de personas disponibles")
    
    # Gráfico tradicional de ventas por mes (sin desglose)
    st.subheader("📈 Ventas Totales por Mes")
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
        if 'total_people' in monthly_table.columns:
            monthly_table['total_people'] = monthly_table['total_people'].apply(lambda x: f"{int(x):,}")
            monthly_table = monthly_table[['month_str', 'total_sales', 'avg_sale', 'num_transactions', 'total_people']]
            monthly_table.columns = ['Mes', 'Ventas Totales', 'Ticket Promedio', 'N° Transacciones', 'Número de Pax']
        else:
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

