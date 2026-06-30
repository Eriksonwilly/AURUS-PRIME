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

# 1. Configuración de página DEBE SER LO PRIMERO
st.set_page_config(
    page_title="Rappi - AURUS PRIME",
    page_icon="🥸",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Definición de constantes básicas para evitar NameError
APP_OPCIONES = [
    "🏗️ Cálculo Básico",
    "📊 Análisis Completo (Rankine)",
    "📊 Análisis Completo (Coulomb)",
    "📐 Diseño del Fuste",
    "ℹ️ Acerca de",
    "✉️ Contacto"
]

SIDEBAR_SECCIONES = [
    (opt, opt) for opt in APP_OPCIONES
]

# Importar sistema de pagos simple
try:
    from simple_payment_system import payment_system
    PAYMENT_SYSTEM_AVAILABLE = True
except ImportError:
    PAYMENT_SYSTEM_AVAILABLE = False

# Importaciones opcionales con manejo de errores
try:
    import plotly.express as px
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

try:
    from reportlab.lib.pagesizes import A4, letter
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

# --- COMIENZO DE FUNCIONES DE CÁLCULO (MANTENIDAS) ---

# Función para calcular empuje activo según teoría de Coulomb
def calcular_empuje_coulomb(datos_entrada):
    H = datos_entrada['H']
    h1 = datos_entrada['h1']
    t1 = datos_entrada.get('t1', 0)
    t2 = datos_entrada['t2']
    b2 = datos_entrada['b2']
    phi1 = datos_entrada['phi1']
    delta = datos_entrada['delta']
    alpha = datos_entrada['alpha']
    gamma1 = datos_entrada['gamma1']
    S_c = datos_entrada['S_c']
    if t2 != 0:
        beta = math.degrees(math.atan((H - h1) / t2))
    else:
        beta = 90.0
    beta_rad = math.radians(beta)
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
    H_efectiva = H + (t1 + t2) * math.tan(alpha_rad)
    Pa = 0.5 * Ka * gamma1 * (H_efectiva) ** 2
    Ph = Pa * math.cos(math.radians(90) - beta_rad + delta_rad)
    Pv = Pa * math.sin(math.radians(90) - beta_rad + delta_rad)
    PSC = Ka * H * (S_c / 1000) * (math.sin(beta_rad) / math.sin(beta_rad + alpha_rad))
    P_total_horizontal = Ph + PSC
    return {
        'beta': beta, 'Ka': Ka, 'H_efectiva': H_efectiva, 'Pa': Pa,
        'Ph': Ph, 'Pv': Pv, 'PSC': PSC, 'P_total_horizontal': P_total_horizontal
    }

def calcular_diseno_fuste(resultados, datos_entrada):
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
    separacion = (b * 100 - 6) / (num_barras - 1) if num_barras > 1 else 0
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

# --- FUNCIONES DE UI SIMPLIFICADAS ---

def inject_aurus_theme():
    st.markdown("""
    <style>
    .main { background-color: #f5f5f5; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #FF5722; color: white; }
    </style>
    """, unsafe_allow_html=True)

def show_auth_page():
    inject_aurus_theme()
    st.title("🏗️ AURUS PRIME - Muros de Contención")
    st.markdown("### Bienvenido al sistema de diseño estructural")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🚀 Iniciar Modo Demo (Gratis)"):
            st.session_state['logged_in'] = True
            st.session_state['user_data'] = {"username": "demo", "plan": "gratuito", "name": "Usuario Demo"}
            st.session_state['user'] = "demo"
            st.session_state['plan'] = "gratuito"
            st.rerun()
    with col2:
        if st.button("👨‍💼 Iniciar como Administrador"):
            st.session_state['logged_in'] = True
            st.session_state['user_data'] = {"username": "admin", "plan": "premium", "name": "Administrador"}
            st.session_state['user'] = "admin"
            st.session_state['plan'] = "premium"
            st.rerun()

# --- FLUJO PRINCIPAL ---

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    show_auth_page()
else:
    st.sidebar.title("Navegación")
    opcion = st.sidebar.selectbox("Seleccione una opción", APP_OPCIONES)
    
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state['logged_in'] = False
        st.rerun()

    if opcion == "🏗️ Cálculo Básico":
        st.title("🏗️ Cálculo Básico de Muro")
        altura = st.number_input("Altura (m)", value=3.0)
        base = st.number_input("Base (m)", value=1.5)
        if st.button("Calcular"):
            st.success(f"Cálculo realizado para muro de {altura}m")
    
    elif opcion == "📊 Análisis Completo (Rankine)":
        st.title("📊 Análisis de Rankine")
        st.info("Disponible en versión Premium")
        
    elif opcion == "📊 Análisis Completo (Coulomb)":
        st.title("📊 Análisis de Coulomb")
        st.info("Disponible en versión Premium")
        
    elif opcion == "📐 Diseño del Fuste":
        st.title("📐 Diseño del Fuste")
        st.info("Disponible en versión Premium")
        
    else:
        st.title(opcion)
        st.write("Sección en desarrollo.")
