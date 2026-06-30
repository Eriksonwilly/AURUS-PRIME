import streamlit as st
import math
import numpy as np
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon, Circle
import io
import tempfile
import os

# --- DEFINICIÓN DE SECCIONES DEL SIDEBAR (Solución al NameError) ---
SIDEBAR_SECCIONES = [
    ("📊 Análisis Rankine", "Rankine"),
    ("📐 Análisis Coulomb", "Coulomb"),
    ("🧱 Muro Contrafuertes", "Contrafuertes"),
    ("💰 Planes y Precios", "💰 Planes y Precios"),
    ("🎁 Regalos", "Regalos")
]

# Importar sistema de pagos simple
try:
    from simple_payment_system import payment_system
    PAYMENT_SYSTEM_AVAILABLE = True
except ImportError:
    PAYMENT_SYSTEM_AVAILABLE = False
    st.warning("⚠️ Sistema de pagos no disponible. Usando modo demo.")

# Importaciones opcionales con manejo de errores
try:
    import plotly.express as px
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    st.warning("⚠️ Plotly no está instalado. Los gráficos interactivos no estarán disponibles.")

try:
    from reportlab.lib.pagesizes import A4, letter
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    st.warning("⚠️ ReportLab no está instalado. La generación de PDFs no estará disponible.")

# Función para calcular empuje activo según teoría de Coulomb
def calcular_empuje_coulomb(datos_entrada):
    """
    Calcula el empuje activo según la teoría de Coulomb (fórmula Excel exacta de la imagen)
    """
    H = datos_entrada['H']
    h1 = datos_entrada['h1']  # ← aquí se usa el valor editable
    t1 = datos_entrada.get('t1', 0)
    t2 = datos_entrada['t2']
    b2 = datos_entrada['b2']
    phi1 = datos_entrada['phi1']
    delta = datos_entrada['delta']
    alpha = datos_entrada['alpha']
    gamma1 = datos_entrada['gamma1']
    S_c = datos_entrada['S_c']
    # 1. Ángulo de inclinación del muro (β) en grados
    if t2 != 0:
        beta = math.degrees(math.atan((H - h1) / t2))
    else:
        beta = 90.0
    beta_rad = math.radians(beta)
    # 2. Coeficiente de empuje activo (Ka)
    phi1_rad = math.radians(phi1)
    delta_rad = math.radians(delta)
    alpha_rad = math.radians(alpha)
    num = math.sin(math.radians(beta + phi1)) ** 2
    den = (math.sin(math.radians(beta)) ** 2) * math.sin(math.radians(beta - delta)) * (
        1 + math.sqrt(
            (math.sin(math.radians(phi1 + delta)) * math.sin(math.radians(phi1 - alpha))) /
            (math.sin(math.radians(beta - delta)) * math.sin(math.radians(beta + alpha)))
        )
    ) ** 2
    Ka = num / den
    # 3. Altura efectiva del muro (H')
    H_efectiva = H + (t1 + t2) * math.tan(alpha_rad)
    # 4. Empuje activo total (Pa)
    Pa = 0.5 * Ka * gamma1 * (H_efectiva) ** 2
    # 5. Componentes del empuje activo
    Ph = Pa * math.cos(math.radians(90) - beta_rad + delta_rad)
    Pv = Pa * math.sin(math.radians(90) - beta_rad + delta_rad)
    # 6. Empuje por sobrecarga (PSC)
    PSC = Ka * H * (S_c / 1000) * (math.sin(beta_rad) / math.sin(beta_rad + alpha_rad))
    # 7. Empuje total (horizontal + sobrecarga)
    P_total_horizontal = Ph + PSC
    return {
        'beta': beta,
        'Ka': Ka,
        'H_efectiva': H_efectiva,
        'Pa': Pa,
        'Ph': Ph,
        'Pv': Pv,
        'PSC': PSC,
        'P_total_horizontal': P_total_horizontal
    }

# Función para calcular diseño del fuste del muro
def calcular_diseno_fuste(resultados, datos_entrada):
    """
    Calcula el diseño y verificación del fuste del muro según PARTE 2.2.py
    """
    h1 = datos_entrada['h1']
    gamma_relleno = datos_entrada['gamma_relleno']
    phi_relleno = datos_entrada['phi_relleno']
    cohesion = datos_entrada['cohesion']
    Df = datos_entrada['Df']
    fc = datos_entrada['fc']
    fy = datos_entrada['fy']
    b = resultados['b']
    
    phi_rad = math.radians(phi_relleno)
    kp = (1 + math.sin(phi_rad)) / (1 - math.sin(phi_rad))
    
    Ep = 0.5 * kp * (gamma_relleno/1000) * Df**2 + 2 * cohesion * Df * math.sqrt(kp)
    Ep_kg_m = Ep * 1000  
    
    yt = Df / 3
    
    ka = resultados['ka']
    Ea_relleno = 0.5 * ka * (gamma_relleno/1000) * h1**2
    Ea_sobrecarga = ka * (datos_entrada['qsc']/1000) * h1
    Ea_total = Ea_relleno + Ea_sobrecarga
    
    Mvol_relleno = Ea_relleno * h1 / 3
    Mvol_sobrecarga = Ea_sobrecarga * h1 / 2
    Mvol_total = Mvol_relleno + Mvol_sobrecarga
    
    W_muro = b * h1 * (datos_entrada['gamma_concreto']/1000)
    W_zapata = resultados['Bz'] * resultados['hz'] * (datos_entrada['gamma_concreto']/1000)
    W_relleno = resultados['t'] * h1 * (gamma_relleno/1000)
    
    x_muro = resultados['r'] + b/2
    x_zapata = resultados['Bz']/2
    x_relleno = resultados['r'] + b + resultados['t']/2
    
    Mr_muro = W_muro * x_muro
    Mr_zapata = W_zapata * x_zapata
    Mr_relleno = W_relleno * x_relleno
    Mr_pasivo = Ep * yt
    Mesta_total = Mr_muro + Mr_zapata + Mr_relleno + Mr_pasivo
    
    FSv = Mesta_total / Mvol_total
    FSd = (math.tan(phi_rad) * (W_muro + W_zapata + W_relleno) + Ep) / Ea_total
    
    W_total = W_muro + W_zapata + W_relleno
    sum_momentos = Mr_muro + Mr_zapata + Mr_relleno
    x_barra = sum_momentos / W_total
    e = abs(x_barra - resultados['Bz']/2)
    
    Mu = 1.4 * Mvol_total  
    fc_kg_cm2 = fc
    fy_kg_cm2 = fy
    
    dreq = math.sqrt(Mu * 100000 / (0.9 * 0.85 * fc_kg_cm2 * b * 100 * 0.59))
    hreq = dreq + 9  
    dreal = resultados['hz'] * 100 - 9  
    
    As = Mu * 100000 / (0.9 * fy_kg_cm2 * dreal)
    Asmin = 0.0033 * b * 100 * dreal  
    
    area_barra = 1.98
    num_barras = math.ceil(As / area_barra)
    As_proporcionado = num_barras * area_barra
    separacion = (b * 100 - 6) / (num_barras - 1)  
    
    rho_real = As_proporcionado / (b * 100 * dreal)
    rho_min = 0.0033
    rho_max = 0.0163
    
    As_retraccion = 0.002 * b * 100 * resultados['hz'] * 100
    num_barras_retraccion = math.ceil(As_retraccion / 1.27)  
    As_retraccion_proporcionado = num_barras_retraccion * 1.27
    
    return {
        'kp': kp, 'Ep_kg_m': Ep_kg_m, 'yt': yt, 'Mvol_total': Mvol_total,
        'Mesta_total': Mesta_total, 'FSv': FSv, 'FSd': FSd, 'x_barra': x_barra,
        'e': e, 'dreq': dreq, 'hreq': hreq, 'dreal': dreal, 'As': As,
        'Asmin': Asmin, 'num_barras': num_barras, 'As_proporcionado': As_proporcionado,
        'separacion': separacion, 'rho_real': rho_real, 'As_retraccion': As_retraccion,
        'num_barras_retraccion': num_barras_retraccion, 'As_retraccion_proporcionado': As_retraccion_proporcionado
    }

# Función para generar PDF del reporte
def generar_pdf_reportlab(resultados, datos_entrada, diseno_fuste, plan="premium", resultados_coulomb=None, datos_entrada_coulomb=None):
    if not REPORTLAB_AVAILABLE:
        pdf_buffer = io.BytesIO()
        reporte_texto = f"CONSORCIO DEJ\nReporte Básico - {plan.upper()}\nFecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        pdf_buffer.write(reporte_texto.encode('utf-8'))
        pdf_buffer.seek(0)
        return pdf_buffer
    
    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(pdf_buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    styleN = styles["Normal"]
    styleH = styles["Heading1"]
    styleH2 = styles["Heading2"]
    elements = []
    
    elements.append(Paragraph("CONSORCIO DEJ", styleH))
    elements.append(Paragraph(f"Reporte de Muro de Contención - {plan.upper()}", styleH2))
    elements.append(Spacer(1, 20))
    
    if plan == "premium":
        elements.append(Paragraph("MEMORIA DESCRIPTIVA", styleH))
        # (Resto de la lógica de generación premium simplificada para legibilidad)
    
    doc.build(elements)
    pdf_buffer.seek(0)
    return pdf_buffer

# Función para dibujar el muro de contención
def dibujar_muro_streamlit(dimensiones, h1, Df, qsc, metodo="rankine", datos_coulomb=None):
    plt.style.use('default')
    fig, ax = plt.subplots(figsize=(14, 12))
    
    Bz = dimensiones['Bz']
    hz = dimensiones['hz']
    b = dimensiones['b']
    r = dimensions['r']
    t = dimensiones['t']
    hm = dimensiones['hm']
    
    ax.add_patch(Rectangle((0, 0), Bz, hz, facecolor='#4FC3F7', edgecolor='#1565C0', linewidth=3))
    ax.add_patch(Rectangle((r, hz), b, h1 + hm, facecolor='#FF5722', edgecolor='#D84315', linewidth=3))
    
    ax.set_xlim(-1.0, Bz+1.0)
    ax.set_ylim(-Df-0.5, hz+h1+hm+1.0)
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.3)
    return fig

# Función para dibujar muro con contrafuertes
def dibujar_muro_contrafuertes(dimensiones, resultados, datos_entrada):
    fig, ax = plt.subplots(figsize=(16, 12))
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.1)
    return fig

# Configuración de la página e inyección de estilos de AURUS PRIME / Rappi
GOLD = "#D4AF37"
GOLD_LIGHT = "#FFD700"
GOLD_DARK = "#8B6914"
BG_DARK = "#0a0a0a"
BG_CARD = "#141414"

def inject_aurus_theme():
    st.markdown(f"""
    <style>
    html, body, [class*="css"] {{ font-family: 'Poppins', sans-serif !important; }}
    .stApp {{ background: {BG_DARK}; color: #f5f5f5; }}
    [data-testid="stSidebar"] {{ background: #ffffff !important; min-width: 300px !important; }}
    [data-testid="stSidebar"] * {{ color: #1a1a1a !important; }}
    </style>
    """, unsafe_allow_html=True)

def render_rappi_sidebar(user_name="GRUPO", logged_in=False, show_all_sections=True):
    initial = user_name[0].upper() if user_name else "G"
    st.sidebar.markdown(f"<h3>Hola, {user_name.upper()}</h3>", unsafe_allow_html=True)

    st.sidebar.markdown('**Secciones**')
    sections = SIDEBAR_SECCIONES if show_all_sections else SIDEBAR_SECCIONES[:4]
    for label, _ in sections:
        if st.sidebar.button(f"{label}  ›", key=f"sb_sec_{label}"):
            if logged_in:
                if _ == "💰 Planes y Precios":
                    st.session_state["show_pricing"] = True
                else:
                    st.session_state["opcion"] = _
                    st.session_state["show_pricing"] = False
            else:
                st.session_state["auth_tab"] = "register" if label == "Regalos" else "login"
            st.rerun()

st.set_page_config(
    page_title="Rappi - AURUS PRIME",
    page_icon="🥸",
    layout="wide",
    initial_sidebar_state="expanded"
)

inject_aurus_theme()

# Sistema de autenticación y páginas
def show_pricing_page():
    """Mostrar página de precios y planes"""
    st.title("💰 Planes y Precios - AURUS PRIME")
    is_admin = st.session_state.get('user') == 'admin'
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.subheader("🆓 Plan Gratuito")
        st.write("**$0/mes**")
        if st.button("Seleccionar Gratuito", key="free_plan"):
            if is_admin:
                st.session_state['plan'] = "gratuito"
                if 'user_data' in st.session_state:
                    st.session_state['user_data']['plan'] = "gratuito"
                st.success("Plan Gratuito asignado correctamente.")
                st.rerun()