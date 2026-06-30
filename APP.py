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
    # --- Cálculo profesional del ángulo β (inclinación del muro respecto a la vertical) ---
    # β = arctan((H - h1) / t2)  (h1 = peralte de la zapata editable)
    # Si t2 = 0, muro vertical: β = 90°
    if t2 != 0:
        beta = math.degrees(math.atan((H - h1) / t2))
    else:
        beta = 90.0
    beta_rad = math.radians(beta)
    # 2. Coeficiente de empuje activo (Ka) - fórmula profesional con conversión explícita a radianes
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
    # Datos del fuste
    h1 = datos_entrada['h1']
    gamma_relleno = datos_entrada['gamma_relleno']
    phi_relleno = datos_entrada['phi_relleno']
    cohesion = datos_entrada['cohesion']
    Df = datos_entrada['Df']
    fc = datos_entrada['fc']
    fy = datos_entrada['fy']
    b = resultados['b']
    
    # 1. Cálculo del coeficiente pasivo
    phi_rad = math.radians(phi_relleno)
    kp = (1 + math.sin(phi_rad)) / (1 - math.sin(phi_rad))
    
    # 2. Empuje pasivo en el intradós
    Ep = 0.5 * kp * (gamma_relleno/1000) * Df**2 + 2 * cohesion * Df * math.sqrt(kp)
    Ep_kg_m = Ep * 1000  # Convertir a kg/m
    
    # 3. Altura de aplicación del empuje pasivo
    yt = Df / 3
    
    # 4. Momentos volcadores y estabilizadores
    # Empuje activo total
    ka = resultados['ka']
    Ea_relleno = 0.5 * ka * (gamma_relleno/1000) * h1**2
    Ea_sobrecarga = ka * (datos_entrada['qsc']/1000) * h1
    Ea_total = Ea_relleno + Ea_sobrecarga
    
    # Momentos volcadores
    Mvol_relleno = Ea_relleno * h1 / 3
    Mvol_sobrecarga = Ea_sobrecarga * h1 / 2
    Mvol_total = Mvol_relleno + Mvol_sobrecarga
    
    # Momentos estabilizadores (simplificado)
    W_muro = b * h1 * (datos_entrada['gamma_concreto']/1000)
    W_zapata = resultados['Bz'] * resultados['hz'] * (datos_entrada['gamma_concreto']/1000)
    W_relleno = resultados['t'] * h1 * (gamma_relleno/1000)
    
    # Brazos de momento
    x_muro = resultados['r'] + b/2
    x_zapata = resultados['Bz']/2
    x_relleno = resultados['r'] + b + resultados['t']/2
    
    Mr_muro = W_muro * x_muro
    Mr_zapata = W_zapata * x_zapata
    Mr_relleno = W_relleno * x_relleno
    Mr_pasivo = Ep * yt
    Mesta_total = Mr_muro + Mr_zapata + Mr_relleno + Mr_pasivo
    
    # 5. Factores de seguridad
    FSv = Mesta_total / Mvol_total
    FSd = (math.tan(phi_rad) * (W_muro + W_zapata + W_relleno) + Ep) / Ea_total
    
    # 6. Ubicación de la resultante y excentricidad
    W_total = W_muro + W_zapata + W_relleno
    sum_momentos = Mr_muro + Mr_zapata + Mr_relleno
    x_barra = sum_momentos / W_total
    e = abs(x_barra - resultados['Bz']/2)
    
    # 7. Cálculo del peralte efectivo
    # Momento de diseño
    Mu = 1.4 * Mvol_total  # Factor de carga
    
    # Resistencia del concreto
    fc_kg_cm2 = fc
    fy_kg_cm2 = fy
    
    # Peralte efectivo requerido
    dreq = math.sqrt(Mu * 100000 / (0.9 * 0.85 * fc_kg_cm2 * b * 100 * 0.59))
    hreq = dreq + 9  # Recubrimiento + diámetro de barra
    dreal = resultados['hz'] * 100 - 9  # Peralte real en cm
    
    # 8. Área de acero
    As = Mu * 100000 / (0.9 * fy_kg_cm2 * dreal)
    Asmin = 0.0033 * b * 100 * dreal  # Cuantía mínima
    
    # 9. Distribución del acero
    # Usar barras de 5/8" (1.98 cm²)
    area_barra = 1.98
    num_barras = math.ceil(As / area_barra)
    As_proporcionado = num_barras * area_barra
    separacion = (b * 100 - 6) / (num_barras - 1)  # 3cm de recubrimiento
    
    # 10. Verificación de cuantías
    rho_real = As_proporcionado / (b * 100 * dreal)
    rho_min = 0.0033
    rho_max = 0.0163
    
    # 11. Acero por retracción y temperatura
    As_retraccion = 0.002 * b * 100 * resultados['hz'] * 100
    num_barras_retraccion = math.ceil(As_retraccion / 1.27)  # Barras de 1/2"
    As_retraccion_proporcionado = num_barras_retraccion * 1.27
    
    return {
        'kp': kp,
        'Ep_kg_m': Ep_kg_m,
        'yt': yt,
        'Mvol_total': Mvol_total,
        'Mesta_total': Mesta_total,
        'FSv': FSv,
        'FSd': FSd,
        'x_barra': x_barra,
        'e': e,
        'dreq': dreq,
        'hreq': hreq,
        'dreal': dreal,
        'As': As,
        'Asmin': Asmin,
        'num_barras': num_barras,
        'As_proporcionado': As_proporcionado,
        'separacion': separacion,
        'rho_real': rho_real,
        'As_retraccion': As_retraccion,
        'num_barras_retraccion': num_barras_retraccion,
        'As_retraccion_proporcionado': As_retraccion_proporcionado
    }

# Función para generar PDF del reporte
def generar_pdf_reportlab(resultados, datos_entrada, diseno_fuste, plan="premium", resultados_coulomb=None, datos_entrada_coulomb=None):
    """
    Genera un PDF profesional usando ReportLab
    """
    if not REPORTLAB_AVAILABLE:
        # Crear un archivo de texto simple como fallback
        pdf_buffer = io.BytesIO()
        reporte_texto = f"""
CONSORCIO DEJ
Ingeniería y Construcción
Reporte de Muro de Contención - {plan.upper()}
Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}

Este es un reporte básico. Para reportes en PDF, instale ReportLab:
pip install reportlab

---
Generado por: CONSORCIO DEJ
        """
        pdf_buffer.write(reporte_texto.encode('utf-8'))
        pdf_buffer.seek(0)
        return pdf_buffer
    
    # Crear archivo temporal
    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(pdf_buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    styleN = styles["Normal"]
    styleH = styles["Heading1"]
    styleH2 = styles["Heading2"]
    elements = []
    
    # Función auxiliar para agregar elementos de forma segura
    def add_element(element):
        try:
            elements.append(element)
        except Exception as e:
            print(f"Error agregando elemento: {e}")
            # Agregar elemento de texto simple como fallback
            elements.append(Paragraph(str(element), styleN))
    
    # Título principal
    try:
        elements.append(Paragraph("CONSORCIO DEJ", styleH))
        elements.append(Paragraph("Ingeniería y Construcción", styleN))
        elements.append(Paragraph(f"Reporte de Muro de Contención - {plan.upper()}", styleH2))
        elements.append(Paragraph(f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}", styleN))
        elements.append(Spacer(1, 20))
    except Exception as e:
        print(f"Error en título: {e}")
        elements.append(Paragraph("CONSORCIO DEJ - Reporte de Muro de Contención", styleN))
    
    if plan == "premium":
        # MEMORIA DESCRIPTIVA
        elements.append(Paragraph("MEMORIA DESCRIPTIVA – MURO DE CONTENCIÓN EN SAN MIGUEL, PUNO (2025)", styleH))
        elements.append(Spacer(1, 20))
        
        # 1. DESCRIPCIÓN GENERAL DEL PROYECTO
        elements.append(Paragraph("1. DESCRIPCIÓN GENERAL DEL PROYECTO", styleH2))
        elements.append(Paragraph("Justificación:", styleN))
        elements.append(Paragraph("El proyecto del muro de contención en San Miguel, Puno, se justifica por la necesidad de estabilizar un talud natural en una zona con alta susceptibilidad a movimientos de masa (huaycos y erosión), que pone en riesgo viviendas, vías de acceso y terrenos agrícolas. La intervención busca garantizar la seguridad de la población y la infraestructura, así como optimizar el uso del terreno en una región con pendientes pronunciadas.", styleN))
        elements.append(Spacer(1, 10))
        
        elements.append(Paragraph("Objetivos:", styleN))
        elements.append(Paragraph("• Objetivo principal: Construir un muro de contención estable y durable que contenga presiones laterales del suelo y prevenga deslizamientos.", styleN))
        elements.append(Paragraph("• Objetivos específicos:", styleN))
        elements.append(Paragraph("  - Aplicar los métodos de Rankine y Coulomb para el diseño estructural, asegurando factores de seguridad ≥1.5.", styleN))
        elements.append(Paragraph("  - Integrar materiales locales y técnicas constructivas adaptadas al clima frío y altitud (≈3,800 msnm).", styleN))
        elements.append(Paragraph("  - Minimizar el impacto ambiental y social.", styleN))
        elements.append(Spacer(1, 10))
        
        elements.append(Paragraph("Metas:", styleN))
        elements.append(Paragraph("• Vida útil ≥50 años.", styleN))
        elements.append(Paragraph("• Reducción del 100% de riesgos asociados a deslizamientos en el área intervenida.", styleN))
        elements.append(Spacer(1, 20))
        
        # 2. CONSIDERACIONES TÉCNICAS GENERALES Y ALCANCES
        elements.append(Paragraph("2. CONSIDERACIONES TÉCNICAS GENERALES Y ALCANCES", styleH2))
        elements.append(Paragraph("Métodos de Diseño:", styleN))
        elements.append(Paragraph("• Método de Rankine: Empleado para calcular el coeficiente de presión activa (Kₐ) en suelos granulares homogéneos, considerando un ángulo de fricción interna (φ) de 30°–35° (típico de suelos arenosos-arcillosos de la zona).", styleN))
        elements.append(Paragraph("• Método de Coulomb: Utilizado para verificar presiones considerando fricción suelo-muro (δ = 2/3*φ) y geometría irregular.", styleN))
        elements.append(Spacer(1, 10))
        
        elements.append(Paragraph("Parámetros Técnicos Clave:", styleN))
        elements.append(Paragraph("• Altura del muro: 6.50 m (incluye 0.50 m de cimiento).", styleN))
        elements.append(Paragraph("• Tipo de muro: Muro de gravedad de concreto ciclópeo (f'c=175 kg/cm²) con piedra embebida, optimizado para resistir esfuerzos por empuje y sismicidad (RNC-2025).", styleN))
        elements.append(Paragraph("• Sistema de drenaje: Tuberías PVC Ø4\" con filtro de grava y geotextil para reducir presión hidrostática.", styleN))
        elements.append(Spacer(1, 10))
        
        elements.append(Paragraph("Alcances:", styleN))
        elements.append(Paragraph("• Diseño estructural y geotécnico.", styleN))
        elements.append(Paragraph("• Construcción del muro y sistema de drenaje.", styleN))
        elements.append(Paragraph("• No incluye: Estabilización de taludes aguas arriba ni pavimentación de áreas adyacentes.", styleN))
        elements.append(Spacer(1, 20))
        
        # 3. INFORMACIÓN RELEVANTE DE LA UBICACIÓN
        elements.append(Paragraph("3. INFORMACIÓN RELEVANTE DE LA UBICACIÓN", styleH2))
        elements.append(Paragraph("Características Geográficas:", styleN))
        elements.append(Paragraph("• Coordenadas: 14°45'S, 69°30'W (approx.).", styleN))
        elements.append(Paragraph("• Topografía: Pendiente promedio de 40° en zona de intervención.", styleN))
        elements.append(Paragraph("• Tipo de suelo: Suelo granular (arena arcillosa) con estratos superficiales de grava suelta. Capacidad portante: 1.8 kg/cm² (ensayos SPT).", styleN))
        elements.append(Spacer(1, 10))
        
        elements.append(Paragraph("Climatología:", styleN))
        elements.append(Paragraph("• Temperaturas: Entre -5°C (noches en invierno) y 18°C (día).", styleN))
        elements.append(Paragraph("• Precipitación: 700 mm/año, concentrada en época de lluvias (diciembre–marzo).", styleN))
        elements.append(Paragraph("• Vientos: Ráfagas hasta 50 km/h (requiere revisión de voladizo).", styleN))
        elements.append(Spacer(1, 10))
        
        elements.append(Paragraph("Accesibilidad:", styleN))
        elements.append(Paragraph("• Vías: Carretera afirmada hasta 500 m del sitio. Se requerirá transporte de materiales con volquetes 6x4.", styleN))
        elements.append(Paragraph("• Suministros: Concreto premezclado desde Juliaca (2 horas de transporte).", styleN))
        elements.append(Spacer(1, 20))
        
        # 4. CONSIDERACIONES ESPECIALES (2025)
        elements.append(Paragraph("4. CONSIDERACIONES ESPECIALES (2025)", styleH2))
        elements.append(Paragraph("• Sismicidad: Zona 3 según Norma E.030 RNC-2025. Se aplicará coeficiente sísmico Cₛ=0.25 para diseño.", styleN))
        elements.append(Paragraph("• Sostenibilidad: Uso de piedra local para reducir huella de carbono.", styleN))
        elements.append(Paragraph("• Monitoreo: Incluye 3 puntos de control de desplazamiento (inclinómetros) post-construcción.", styleN))
        elements.append(Spacer(1, 20))
        
        # RESULTADOS DE ANÁLISIS - RANKINE
        elements.append(Paragraph("5. RESULTADOS DEL ANÁLISIS - TEORÍA DE RANKINE", styleH))
        elements.append(Paragraph("5.1 DATOS DE ENTRADA - TEORÍA DE RANKINE", styleH2))
        
        # Usar .get() para evitar KeyError
        datos_tabla = [
            ["Parámetro", "Valor", "Unidad"],
            ["Peralte de Zapata (h1)", f"{datos_entrada.get('h1', 0):.2f}", "m"],
            ["Densidad del relleno", f"{datos_entrada.get('gamma_relleno', 0)}", "kg/m³"],
            ["Ángulo de fricción del relleno", f"{datos_entrada.get('phi_relleno', 0)}", "°"],
            ["Profundidad de desplante (Df)", f"{datos_entrada.get('Df', 0):.2f}", "m"],
            ["Sobrecarga (qsc)", f"{datos_entrada.get('qsc', 0)}", "kg/m²"],
            ["Resistencia del concreto (fc)", f"{datos_entrada.get('fc', 0)}", "kg/cm²"],
            ["Resistencia del acero (fy)", f"{datos_entrada.get('fy', 0)}", "kg/cm²"]
        ]
        
        tabla = Table(datos_tabla, colWidths=[200, 100, 80])
        tabla.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ]))
        elements.append(tabla)
        elements.append(Spacer(1, 20))
        
        # Dimensiones calculadas
        elements.append(Paragraph("2. DIMENSIONES CALCULADAS - RANKINE", styleH))
        dim_tabla = [
            ["Dimensión", "Valor", "Unidad"],
            ["Ancho de zapata (Bz)", f"{resultados.get('Bz', 0):.2f}", "m"],
            ["Peralte de zapata (hz)", f"{resultados.get('hz', 0):.2f}", "m"],
            ["Espesor del muro (b)", f"{resultados.get('b', 0):.2f}", "m"],
            ["Longitud de puntera (r)", f"{resultados.get('r', 0):.2f}", "m"],
            ["Longitud de talón (t)", f"{resultados.get('t', 0):.2f}", "m"],
            ["Altura de coronación (hm)", f"{resultados.get('hm', 0):.2f}", "m"]
        ]
        
        tabla_dim = Table(dim_tabla, colWidths=[200, 100, 80])
        tabla_dim.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgreen),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ]))
        elements.append(tabla_dim)
        elements.append(Spacer(1, 20))
        
        # Diseño del fuste
        elements.append(Paragraph("3. DISEÑO Y VERIFICACIÓN DEL FUSTE", styleH))
        fuste_tabla = [
            ["Parámetro", "Valor", "Unidad"],
            ["Coeficiente pasivo (kp)", f"{diseno_fuste.get('kp', 0):.2f}", ""],
            ["Empuje pasivo", f"{diseno_fuste.get('Ep_kg_m', 0):.0f}", "kg/m"],
            ["Factor de seguridad volcamiento", f"{diseno_fuste.get('FSv', 0):.2f}", ""],
            ["Factor de seguridad deslizamiento", f"{diseno_fuste.get('FSd', 0):.2f}", ""],
            ["Peralte efectivo requerido", f"{diseno_fuste.get('dreq', 0):.2f}", "cm"],
            ["Peralte efectivo real", f"{diseno_fuste.get('dreal', 0):.2f}", "cm"],
            ["Área de acero requerida", f"{diseno_fuste.get('As', 0):.2f}", "cm²"],
            ["Área de acero mínima", f"{diseno_fuste.get('Asmin', 0):.2f}", "cm²"],
            ["Número de barras 5/8\"", f"{diseno_fuste.get('num_barras', 0)}", ""],
            ["Separación entre barras", f"{diseno_fuste.get('separacion', 0):.1f}", "cm"]
        ]
        
        tabla_fuste = Table(fuste_tabla, colWidths=[200, 100, 80])
        tabla_fuste.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightyellow),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ]))
        elements.append(tabla_fuste)
        elements.append(Spacer(1, 20))
        
        # Verificaciones de estabilidad
        elements.append(Paragraph("4. VERIFICACIONES DE ESTABILIDAD", styleH))
        verificaciones = []
        
        fsv = diseno_fuste.get('FSv', 0)
        fsd = diseno_fuste.get('FSd', 0)
        
        if fsv >= 2.0:
            verificaciones.append(["Volcamiento", "CUMPLE", f"FS = {fsv:.2f} ≥ 2.0"])
        else:
            verificaciones.append(["Volcamiento", "NO CUMPLE", f"FS = {fsv:.2f} < 2.0"])
            
        if fsd >= 1.5:
            verificaciones.append(["Deslizamiento", "CUMPLE", f"FS = {fsd:.2f} ≥ 1.5"])
        else:
            verificaciones.append(["Deslizamiento", "NO CUMPLE", f"FS = {fsd:.2f} < 1.5"])
            
        dreal = diseno_fuste.get('dreal', 0)
        dreq = diseno_fuste.get('dreq', 0)
        as_proporcionado = diseno_fuste.get('As_proporcionado', 0)
        as_requerido = diseno_fuste.get('As', 0)
        
        if dreal >= dreq:
            verificaciones.append(["Peralte efectivo", "CUMPLE", f"dreal = {dreal:.2f} ≥ {dreq:.2f}"])
        else:
            verificaciones.append(["Peralte efectivo", "NO CUMPLE", f"dreal = {dreal:.2f} < {dreq:.2f}"])
            
        if as_proporcionado >= as_requerido:
            verificaciones.append(["Área de acero", "CUMPLE", f"As = {as_proporcionado:.2f} ≥ {as_requerido:.2f}"])
        else:
            verificaciones.append(["Área de acero", "NO CUMPLE", f"As = {as_proporcionado:.2f} < {as_requerido:.2f}"])
        
        verif_tabla = [["Verificación", "Estado", "Detalle"]] + verificaciones
        tabla_verif = Table(verif_tabla, colWidths=[150, 100, 150])
        tabla_verif.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightcoral),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ]))
        elements.append(tabla_verif)
        elements.append(Spacer(1, 20))
        
        # RESULTADOS DE ANÁLISIS - COULOMB
        if resultados_coulomb and datos_entrada_coulomb:
            elements.append(Paragraph("6. RESULTADOS DEL ANÁLISIS - TEORÍA DE COULOMB", styleH))
            elements.append(Paragraph("6.1 DATOS DE ENTRADA - TEORÍA DE COULOMB", styleH2))
            
            # Datos del suelo de relleno
            elements.append(Paragraph("A. DATOS DEL SUELO DE RELLENO", styleH2))
            datos_relleno_coulomb = [
                ["Parámetro", "Valor", "Unidad"],
                ["Peso específico (γ₁)", f"{datos_entrada_coulomb.get('gamma1', '')}", "t/m³"],
                ["Ángulo de fricción (φ'₁)", f"{datos_entrada_coulomb.get('phi1', '')}", "°"],
                ["Cohesión (c'₁)", f"{datos_entrada_coulomb.get('cohesion1', '')}", "kg/cm²"],
                ["Ángulo de inclinación (α)", f"{datos_entrada_coulomb.get('alpha', '')}", "°"]
            ]
            tabla_relleno_coulomb = Table(datos_relleno_coulomb, colWidths=[200, 100, 80])
            tabla_relleno_coulomb.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ]))
            elements.append(tabla_relleno_coulomb)
            elements.append(Spacer(1, 10))
            
            # Datos del suelo de la base
            elements.append(Paragraph("B. DATOS DEL SUELO DE LA BASE", styleH2))
            datos_base_coulomb = [
                ["Parámetro", "Valor", "Unidad"],
                ["Peso específico (γ₂)", f"{datos_entrada_coulomb.get('gamma2', '')}", "t/m³"],
                ["Cohesión (c'₂)", f"{datos_entrada_coulomb.get('cohesion2', '')}", "kg/cm²"],
                ["Capacidad de carga (σᵤ)", f"{datos_entrada_coulomb.get('sigma_u', '')}", "kg/cm²"],
                ["Ángulo de fricción (φ'₂)", f"{datos_entrada_coulomb.get('phi2', '')}", "°"]
            ]
            tabla_base_coulomb = Table(datos_base_coulomb, colWidths=[200, 100, 80])
            tabla_base_coulomb.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgreen),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ]))
            elements.append(tabla_base_coulomb)
            elements.append(Spacer(1, 10))
            
            # Datos del muro
            elements.append(Paragraph("C. DATOS DEL MURO", styleH2))
            datos_muro_coulomb = [
                ["Parámetro", "Valor", "Unidad"],
                ["Peso específico del muro (γ_muro)", f"{datos_entrada_coulomb.get('gamma_muro', '')}", "t/m³"],
                ["Sobrecarga (S/c)", f"{datos_entrada_coulomb.get('S_c', '')}", "kg/m²"],
                ["Altura total (H)", f"{datos_entrada_coulomb.get('H', '')}", "m"],
                ["Profundidad de desplante (D)", f"{datos_entrada_coulomb.get('D', '')}", "m"],
                ["Peralte de Zapata (h1)", f"{datos_entrada_coulomb.get('h1', '')}", "m"],
                ["Base del triángulo (t2)", f"{datos_entrada_coulomb.get('t2', '')}", "m"],
                ["Longitud del talón (b2)", f"{datos_entrada_coulomb.get('b2', '')}", "m"],
                ["Ángulo de fricción muro-suelo (δ)", f"{datos_entrada_coulomb.get('delta', '')}", "°"]
            ]
            tabla_muro_coulomb = Table(datos_muro_coulomb, colWidths=[200, 100, 80])
            tabla_muro_coulomb.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightyellow),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ]))
            elements.append(tabla_muro_coulomb)
            elements.append(Spacer(1, 20))
            
            # Resultados de Coulomb
            elements.append(Paragraph("6.2 RESULTADOS DEL ANÁLISIS COULOMB", styleH2))
            resultados_coulomb_tabla = [
                ["Parámetro", "Valor", "Unidad"],
                ["Ángulo de inclinación del muro (β)", f"{resultados_coulomb.get('beta', 0):.2f}", "°"],
                ["Coeficiente Ka (Coulomb)", f"{resultados_coulomb.get('ka', 0):.6f}", ""],
                ["Altura efectiva (H')", f"{resultados_coulomb.get('H_efectiva', 0):.2f}", "m"],
                ["Empuje activo total (Pa)", f"{resultados_coulomb.get('Pa', 0):.3f}", "t/m"],
                ["Componente horizontal (Ph)", f"{resultados_coulomb.get('Ph', 0):.3f}", "t/m"],
                ["Componente vertical (Pv)", f"{resultados_coulomb.get('Pv', 0):.3f}", "t/m"],
                ["Empuje por sobrecarga (PSC)", f"{resultados_coulomb.get('PSC', 0):.3f}", "t/m"],
                ["Empuje total horizontal", f"{resultados_coulomb.get('P_total_horizontal', 0):.3f}", "t/m"]
            ]
            
            tabla_resultados_coulomb = Table(resultados_coulomb_tabla, colWidths=[200, 100, 80])
            tabla_resultados_coulomb.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgreen),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ]))
            elements.append(tabla_resultados_coulomb)
            elements.append(Spacer(1, 20))
            
            # Comparación de métodos (solo si hay resultados de Rankine)
            if resultados and resultados.get('ka') and resultados.get('Ea_total'):
                elements.append(Paragraph("7. COMPARACIÓN DE MÉTODOS: RANKINE vs COULOMB", styleH))
                comparacion_tabla = [
                    ["Parámetro", "Rankine", "Coulomb", "Diferencia"],
                    ["Coeficiente Ka", f"{resultados.get('ka', 0):.6f}", f"{resultados_coulomb.get('ka', 0):.6f}", f"{abs(resultados.get('ka', 0) - resultados_coulomb.get('ka', 0)):.6f}"],
                    ["Empuje activo (t/m)", f"{resultados.get('Ea_total', 0):.3f}", f"{resultados_coulomb.get('Pa', 0):.3f}", f"{abs(resultados.get('Ea_total', 0) - resultados_coulomb.get('Pa', 0)):.3f}"],
                    ["Método", "Muro vertical liso", "Considera fricción", "Más realista"],
                    ["Aplicación", "Conservador", "Más preciso", "Recomendado"]
                ]
                
                tabla_comparacion = Table(comparacion_tabla, colWidths=[150, 100, 100, 100])
                tabla_comparacion.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.lightcoral),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ]))
                elements.append(tabla_comparacion)
                elements.append(Spacer(1, 20))
        else:
            # Si no hay resultados de Coulomb, mostrar mensaje
            elements.append(Paragraph("6. RESULTADOS DEL ANÁLISIS - TEORÍA DE COULOMB", styleH))
            elements.append(Paragraph("⚠️ No hay resultados de análisis Coulomb disponibles.", styleN))
            elements.append(Paragraph("Para incluir resultados de Coulomb, ejecuta primero el análisis completo de Coulomb.", styleN))
            elements.append(Spacer(1, 20))
        
        # CONCLUSIONES Y RECOMENDACIONES
        elements.append(Paragraph("8. CONCLUSIONES Y RECOMENDACIONES", styleH))
        elements.append(Paragraph("Conclusiones:", styleN))
        elements.append(Paragraph("• El análisis mediante ambos métodos (Rankine y Coulomb) proporciona una visión completa del comportamiento del muro.", styleN))
        elements.append(Paragraph("• El método de Coulomb considera la fricción suelo-muro, proporcionando resultados más realistas.", styleN))
        elements.append(Paragraph("• Los factores de seguridad calculados cumplen con los requisitos normativos.", styleN))
        elements.append(Spacer(1, 10))
        
        elements.append(Paragraph("Recomendaciones:", styleN))
        elements.append(Paragraph("• Utilizar el método de Coulomb para el diseño final por su mayor precisión.", styleN))
        elements.append(Paragraph("• Verificar la capacidad portante del suelo mediante ensayos in situ.", styleN))
        elements.append(Paragraph("• Implementar sistema de drenaje adecuado para reducir presiones hidrostáticas.", styleN))
        elements.append(Paragraph("• Realizar monitoreo continuo durante la construcción y operación.", styleN))
        elements.append(Spacer(1, 20))
        
        # FIRMA Y DATOS DEL PROFESIONAL
        elements.append(Paragraph("Elaborado por:", styleN))
        elements.append(Paragraph("[Tu Nombre]", styleN))
        elements.append(Paragraph("Ing. Civil UNI, CIP N° [XXXXX]", styleN))
        elements.append(Paragraph("Especialista en Geotecnia y Muros de Contención", styleN))
        elements.append(Paragraph(f"Julio 2025, Puno, Perú", styleN))
        elements.append(Spacer(1, 10))
        elements.append(Paragraph("Nota: Este documento es un modelo base. Ajustar valores según estudios geotécnicos específicos y expediente técnico completo.", styleN))
        
    elif plan == "coulomb":
        # Reporte Coulomb
        elements.append(Paragraph("1. DATOS DE ENTRADA - TEORÍA DE COULOMB", styleH))
        # --- Suelo de relleno ---
        elements.append(Paragraph("A. DATOS DEL SUELO DE RELLENO", styleH2))
        datos_relleno = [
            ["Parámetro", "Valor", "Unidad"],
            ["Peso específico (γ₁)", f"{datos_entrada.get('gamma1', '')}", "t/m³"],
            ["Ángulo de fricción (φ'₁)", f"{datos_entrada.get('phi1', '')}", "°"],
            ["Cohesión (c'₁)", f"{datos_entrada.get('cohesion1', '')}", "kg/cm²"],
            ["Ángulo de inclinación (α)", f"{datos_entrada.get('alpha', '')}", "°"]
        ]
        tabla_relleno = Table(datos_relleno, colWidths=[200, 100, 80])
        tabla_relleno.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ]))
        elements.append(tabla_relleno)
        elements.append(Spacer(1, 10))
        # --- Suelo de la base ---
        elements.append(Paragraph("B. DATOS DEL SUELO DE LA BASE", styleH2))
        datos_base = [
            ["Parámetro", "Valor", "Unidad"],
            ["Peso específico (γ₂)", f"{datos_entrada.get('gamma2', '')}", "t/m³"],
            ["Cohesión (c'₂)", f"{datos_entrada.get('cohesion2', '')}", "kg/cm²"],
            ["Capacidad de carga (σᵤ)", f"{datos_entrada.get('sigma_u', '')}", "kg/cm²"],
            ["Ángulo de fricción (φ'₂)", f"{datos_entrada.get('phi2', '')}", "°"]
        ]
        tabla_base = Table(datos_base, colWidths=[200, 100, 80])
        tabla_base.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgreen),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ]))
        elements.append(tabla_base)
        elements.append(Spacer(1, 10))
        # --- Datos del muro ---
        elements.append(Paragraph("C. DATOS DEL MURO", styleH2))
        datos_muro = [
            ["Parámetro", "Valor", "Unidad"],
            ["Peso específico del muro (γ_muro)", f"{datos_entrada.get('gamma_muro', '')}", "t/m³"],
            ["Sobrecarga (S/c)", f"{datos_entrada.get('S_c', '')}", "kg/m²"],
            ["Altura total (H)", f"{datos_entrada.get('H', '')}", "m"],
            ["Profundidad de desplante (D)", f"{datos_entrada.get('D', '')}", "m"],
            ["Peralte de Zapata (h1)", f"{datos_entrada.get('h1', '')}", "m"],
            ["Base del triángulo (t2)", f"{datos_entrada.get('t2', '')}", "m"],
            ["Longitud del talón (b2)", f"{datos_entrada.get('b2', '')}", "m"],
            ["Ángulo de fricción muro-suelo (δ)", f"{datos_entrada.get('delta', '')}", "°"]
        ]
        tabla_muro = Table(datos_muro, colWidths=[200, 100, 80])
        tabla_muro.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightyellow),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ]))
        elements.append(tabla_muro)
        elements.append(Spacer(1, 20))
        
        # Resultados de Coulomb
        elements.append(Paragraph("2. RESULTADOS DEL ANÁLISIS COULOMB", styleH))
        resultados_tabla = [
            ["Parámetro", "Valor", "Unidad"],
            ["Ángulo de inclinación del muro (β)", f"{resultados['beta']:.2f}", "°"],
            ["Coeficiente Ka (Coulomb)", f"{resultados['ka']:.6f}", ""],
            ["Altura efectiva (H')", f"{resultados['H_efectiva']:.2f}", "m"],
            ["Empuje activo total (Pa)", f"{resultados['Pa']:.3f}", "t/m"],
            ["Componente horizontal (Ph)", f"{resultados['Ph']:.3f}", "t/m"],
            ["Componente vertical (Pv)", f"{resultados['Pv']:.3f}", "t/m"],
            ["Empuje por sobrecarga (PSC)", f"{resultados['PSC']:.3f}", "t/m"],
            ["Empuje total horizontal", f"{resultados['P_total_horizontal']:.3f}", "t/m"]
        ]
        
        tabla_resultados = Table(resultados_tabla, colWidths=[200, 100, 80])
        tabla_resultados.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgreen),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ]))
        elements.append(tabla_resultados)
        elements.append(Spacer(1, 20))
        
        # Fórmulas utilizadas
        elements.append(Paragraph("3. FÓRMULAS UTILIZADAS", styleH))
        formulas = [
            ["Cálculo", "Fórmula", "Resultado"],
            ["Ángulo β", "β = arctan((H - h₁) / t₂)", f"{resultados['beta']:.2f}°"],
            ["Coeficiente Ka", "Fórmula completa de Coulomb", f"{resultados['ka']:.6f}"],
            ["Altura efectiva", "H' = H + (t₂/2 + b₂/2) × tan(α)", f"{resultados['H_efectiva']:.2f} m"],
            ["Empuje activo", "Pa = ½ × Ka × γ₁ × (H')²", f"{resultados['Pa']:.3f} t/m"],
            ["Componente horizontal", "Ph = Pa × cos(90° - β + δ)", f"{resultados['Ph']:.3f} t/m"],
            ["Componente vertical", "Pv = Pa × sin(90° - β + δ)", f"{resultados['Pv']:.3f} t/m"],
            ["Empuje sobrecarga", "PSC = Ka × H × (S_c/1000) × (sin(β)/sin(β+α))", f"{resultados['PSC']:.3f} t/m"]
        ]
        
        tabla_formulas = Table(formulas, colWidths=[150, 200, 100])
        tabla_formulas.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightyellow),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ]))
        elements.append(tabla_formulas)
        
    elif plan == "rankine":
        # Reporte Rankine específico
        elements.append(Paragraph("1. DATOS DE ENTRADA - TEORÍA DE RANKINE", styleH))
        datos_tabla = [
            ["Parámetro", "Valor", "Unidad"],
            ["Peralte de Zapata (h1)", f"{datos_entrada['h1']:.2f}", "m"],
            ["Profundidad de desplante (Df)", f"{datos_entrada['Df']:.2f}", "m"],
            ["Altura de coronación (hm)", f"{datos_entrada['hm']:.2f}", "m"],
            ["Densidad del relleno", f"{datos_entrada['gamma_relleno']}", "kg/m³"],
            ["Ángulo de fricción del relleno", f"{datos_entrada['phi_relleno']}", "°"],
            ["Densidad del suelo de cimentación", f"{datos_entrada['gamma_cimentacion']}", "kg/m³"],
            ["Ángulo de fricción del suelo", f"{datos_entrada['phi_cimentacion']}", "°"],
            ["Cohesión del suelo", f"{datos_entrada['cohesion']}", "t/m²"],
            ["Capacidad portante del suelo", f"{datos_entrada['sigma_adm']}", "kg/cm²"],
            ["Peso específico del concreto", f"{datos_entrada['gamma_concreto']}", "kg/m³"],
            ["Sobrecarga (qsc)", f"{datos_entrada['qsc']}", "kg/m²"],
            ["Resistencia del concreto (fc)", f"{datos_entrada['fc']}", "kg/cm²"],
            ["Resistencia del acero (fy)", f"{datos_entrada['fy']}", "kg/cm²"]
        ]
        
        tabla = Table(datos_tabla, colWidths=[200, 100, 80])
        tabla.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ]))
        elements.append(tabla)
        elements.append(Spacer(1, 20))
        
        # Coeficientes de presión
        elements.append(Paragraph("2. COEFICIENTES DE PRESIÓN - RANKINE", styleH))
        coef_tabla = [
            ["Parámetro", "Valor", "Unidad"],
            ["Coeficiente Ka (Rankine)", f"{resultados['ka']:.6f}", ""],
            ["Coeficiente Kp", f"{resultados['kp']:.6f}", ""],
            ["Altura equivalente (hs)", f"{resultados['hs']:.3f}", "m"]
        ]
        
        tabla_coef = Table(coef_tabla, colWidths=[200, 100, 80])
        tabla_coef.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgreen),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ]))
        elements.append(tabla_coef)
        elements.append(Spacer(1, 20))
        
        # Dimensiones calculadas
        elements.append(Paragraph("3. DIMENSIONES CALCULADAS", styleH))
        dim_tabla = [
            ["Dimensión", "Valor", "Unidad"],
            ["Ancho de zapata (Bz)", f"{resultados['Bz']:.2f}", "m"],
            ["Peralte de zapata (hz)", f"{resultados['hz']:.2f}", "m"],
            ["Espesor del muro (b)", f"{resultados['b']:.2f}", "m"],
            ["Longitud de puntera (r)", f"{resultados['r']:.2f}", "m"],
            ["Longitud de talón (t)", f"{resultados['t']:.2f}", "m"]
        ]
        
        tabla_dim = Table(dim_tabla, colWidths=[200, 100, 80])
        tabla_dim.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightyellow),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ]))
        elements.append(tabla_dim)
        elements.append(Spacer(1, 20))
        
        # Análisis de empujes
        elements.append(Paragraph("4. ANÁLISIS DE EMPUJES", styleH))
        empujes_tabla = [
            ["Empuje", "Valor", "Unidad"],
            ["Empuje activo por relleno", f"{resultados['Ea_relleno']:.3f}", "tn/m"],
            ["Empuje activo por sobrecarga", f"{resultados['Ea_sobrecarga']:.3f}", "tn/m"],
            ["Empuje activo total", f"{resultados['Ea_total']:.3f}", "tn/m"],
            ["Empuje pasivo", f"{resultados['Ep']:.3f}", "tn/m"]
        ]
        
        tabla_empujes = Table(empujes_tabla, colWidths=[200, 100, 80])
        tabla_empujes.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightcoral),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ]))
        elements.append(tabla_empujes)
        elements.append(Spacer(1, 20))
        
        # Factores de seguridad
        elements.append(Paragraph("5. FACTORES DE SEGURIDAD", styleH))
        fs_tabla = [
            ["Verificación", "Factor", "Estado"],
            ["Volcamiento", f"{resultados['FS_volcamiento']:.2f}", "CUMPLE" if resultados['FS_volcamiento'] >= 2.0 else "NO CUMPLE"],
            ["Deslizamiento", f"{resultados['FS_deslizamiento']:.2f}", "CUMPLE" if resultados['FS_deslizamiento'] >= 1.5 else "NO CUMPLE"]
        ]
        
        tabla_fs = Table(fs_tabla, colWidths=[150, 100, 100])
        tabla_fs.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ]))
        elements.append(tabla_fs)
        elements.append(Spacer(1, 20))
        
        # Observaciones técnicas
        elements.append(Paragraph("6. OBSERVACIONES TÉCNICAS", styleH))
        elements.append(Paragraph("• La teoría de Rankine considera muro vertical liso", styleN))
        elements.append(Paragraph("• No considera fricción entre el muro y el suelo", styleN))
        elements.append(Paragraph("• Proporciona una aproximación conservadora", styleN))
        elements.append(Paragraph("• Fórmulas más simples que Coulomb", styleN))
        elements.append(Paragraph("• Ka = tan²(45° - φ/2)", styleN))
        elements.append(Spacer(1, 20))
        
        # Recomendaciones
        elements.append(Paragraph("7. RECOMENDACIONES", styleH))
        elements.append(Paragraph("• Verificar la capacidad portante del suelo en campo", styleN))
        elements.append(Paragraph("• Revisar el diseño del refuerzo estructural según ACI 318", styleN))
        elements.append(Paragraph("• Considerar efectos sísmicos según la normativa local", styleN))
        elements.append(Paragraph("• Realizar inspecciones periódicas durante la construcción", styleN))
        
    elif plan == "coulomb":
        # Reporte Coulomb
        elements.append(Paragraph("1. DATOS DE ENTRADA - TEORÍA DE COULOMB", styleH))
        datos_tabla = [
            ["Parámetro", "Valor", "Unidad"],
            ["Altura total del muro (H)", f"{datos_entrada['H']:.2f}", "m"],
            ["Peralte de Zapata (h1)", f"{datos_entrada['h1']:.2f}", "m"],
            ["Base del triángulo (t2)", f"{datos_entrada['t2']:.2f}", "m"],
            ["Longitud del talón (b2)", f"{datos_entrada['b2']:.2f}", "m"],
            ["Ángulo de fricción (φ1)", f"{datos_entrada['phi1']}", "°"],
            ["Ángulo de fricción muro-suelo (δ)", f"{datos_entrada['delta']}", "°"],
            ["Ángulo de inclinación del terreno (α)", f"{datos_entrada['alpha']}", "°"],
            ["Peso específico del suelo (γ1)", f"{datos_entrada['gamma1']}", "t/m³"],
            ["Sobrecarga (S_c)", f"{datos_entrada['S_c']}", "kg/m²"]
        ]
        
        tabla = Table(datos_tabla, colWidths=[200, 100, 80])
        tabla.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ]))
        elements.append(tabla)
        elements.append(Spacer(1, 20))
        
        # Resultados de Coulomb
        elements.append(Paragraph("2. RESULTADOS DEL ANÁLISIS COULOMB", styleH))
        resultados_tabla = [
            ["Parámetro", "Valor", "Unidad"],
            ["Ángulo de inclinación del muro (β)", f"{resultados['beta']:.2f}", "°"],
            ["Coeficiente Ka (Coulomb)", f"{resultados['ka']:.6f}", ""],
            ["Altura efectiva (H')", f"{resultados['H_efectiva']:.2f}", "m"],
            ["Empuje activo total (Pa)", f"{resultados['Pa']:.3f}", "t/m"],
            ["Componente horizontal (Ph)", f"{resultados['Ph']:.3f}", "t/m"],
            ["Componente vertical (Pv)", f"{resultados['Pv']:.3f}", "t/m"],
            ["Empuje por sobrecarga (PSC)", f"{resultados['PSC']:.3f}", "t/m"],
            ["Empuje total horizontal", f"{resultados['P_total_horizontal']:.3f}", "t/m"]
        ]
        
        tabla_resultados = Table(resultados_tabla, colWidths=[200, 100, 80])
        tabla_resultados.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgreen),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ]))
        elements.append(tabla_resultados)
        elements.append(Spacer(1, 20))
        
        # Fórmulas utilizadas
        elements.append(Paragraph("3. FÓRMULAS UTILIZADAS", styleH))
        formulas = [
            ["Cálculo", "Fórmula", "Resultado"],
            ["Ángulo β", "β = arctan((H - h₁) / t₂)", f"{resultados['beta']:.2f}°"],
            ["Coeficiente Ka", "Fórmula completa de Coulomb", f"{resultados['ka']:.6f}"],
            ["Altura efectiva", "H' = H + (t₂/2 + b₂/2) × tan(α)", f"{resultados['H_efectiva']:.2f} m"],
            ["Empuje activo", "Pa = ½ × Ka × γ₁ × (H')²", f"{resultados['Pa']:.3f} t/m"],
            ["Componente horizontal", "Ph = Pa × cos(90° - β + δ)", f"{resultados['Ph']:.3f} t/m"],
            ["Componente vertical", "Pv = Pa × sin(90° - β + δ)", f"{resultados['Pv']:.3f} t/m"],
            ["Empuje sobrecarga", "PSC = Ka × H × (S_c/1000) × (sin(β)/sin(β+α))", f"{resultados['PSC']:.3f} t/m"]
        ]
        
        tabla_formulas = Table(formulas, colWidths=[150, 200, 100])
        tabla_formulas.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightyellow),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ]))
        elements.append(tabla_formulas)
        elements.append(Spacer(1, 20))
        
        # Observaciones técnicas
        elements.append(Paragraph("4. OBSERVACIONES TÉCNICAS", styleH))
        elements.append(Paragraph("• La teoría de Coulomb considera fricción muro-suelo", styleN))
        elements.append(Paragraph("• Apropiada para muros rugosos o inclinados", styleN))
        elements.append(Paragraph("• Fórmulas más complejas que Rankine", styleN))
        elements.append(Paragraph("• Considera el ángulo de inclinación del terreno", styleN))
        elements.append(Paragraph("• Proporciona componentes horizontal y vertical", styleN))
        elements.append(Spacer(1, 20))
        
        # Recomendaciones
        elements.append(Paragraph("5. RECOMENDACIONES", styleH))
        elements.append(Paragraph("• Usar para muros con superficies rugosas", styleN))
        elements.append(Paragraph("• Apropiado para muros inclinados", styleN))
        elements.append(Paragraph("• Verificar con Rankine para comparación", styleN))
        elements.append(Paragraph("• Considerar efectos de fricción muro-suelo", styleN))
        
    else:
        # Reporte básico
        elements.append(Paragraph("RESULTADOS BÁSICOS", styleH))
        elements.append(Paragraph(f"Peso del muro: {resultados.get('peso_muro', 0):.2f} kN", styleN))
        elements.append(Paragraph(f"Empuje del suelo: {resultados.get('empuje_suelo', 0):.2f} kN", styleN))
        elements.append(Paragraph(f"Factor de seguridad: {resultados.get('fs_volcamiento', 0):.2f}", styleN))
        elements.append(Paragraph("Este es un reporte básico del plan gratuito.", styleN))
    
    # Agregar referencias y pie de página
    elements.append(Spacer(1, 30))
    elements.append(Paragraph("REFERENCIAS TÉCNICAS", styleH2))
    elements.append(Paragraph("• Rankine, W.J.M. (1857). On the stability of loose earth", styleN))
    elements.append(Paragraph("• Coulomb, C.A. (1776). Essai sur une application des règles", styleN))
    elements.append(Paragraph("• Das, B.M. (2010). Principles of Geotechnical Engineering", styleN))
    elements.append(Paragraph("• Bowles, J.E. (1996). Foundation Analysis and Design", styleN))
    elements.append(Paragraph("• ACI 318 - Building Code Requirements for Structural Concrete", styleN))
    
    elements.append(Spacer(1, 20))
    elements.append(Paragraph("CONSORCIO DEJ - Ingeniería y Construcción", styleN))
    elements.append(Paragraph("Este reporte fue generado automáticamente por el sistema de análisis de muros de contención.", styleN))
    elements.append(Paragraph(f"Fecha de generación: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", styleN))
    
    # Construir PDF
    doc.build(elements)
    pdf_buffer.seek(0)
    return pdf_buffer

# Función para dibujar el muro de contención
def dibujar_muro_streamlit(dimensiones, h1, Df, qsc, metodo="rankine", datos_coulomb=None):
    """
    Dibuja el muro de contención con las dimensiones calculadas para Streamlit.
    
    Parámetros:
    -----------
    dimensiones : dict
        Diccionario con las dimensiones calculadas del muro
    h1 : float
        Peralte de Zapata (m)
    Df : float
        Profundidad de desplante (m)
    qsc : float
        Sobrecarga (kg/m²)
    metodo : str
        Método de análisis ("rankine" o "coulomb")
    datos_coulomb : dict, optional
        Datos específicos del método Coulomb (ángulos β, α, δ, etc.)
    
    Retorna:
    --------
    matplotlib.figure.Figure
        Figura con el dibujo del muro
    """
    # Configurar estilo profesional
    plt.style.use('default')
    fig, ax = plt.subplots(figsize=(14, 12))
    
    # Extraer dimensiones
    Bz = dimensiones['Bz']
    hz = dimensiones['hz']
    b = dimensiones['b']
    r = dimensiones['r']
    t = dimensiones['t']
    hm = dimensiones['hm']
    
    # Colores profesionales mejorados
    color_zapata = '#4FC3F7'  # Azul claro profesional
    color_muro = '#FF5722'    # Naranja vibrante
    color_relleno = '#FFC107' # Amarillo dorado
    color_suelo = '#8D6E63'   # Marrón tierra
    color_agua = '#81C784'    # Verde agua
    color_acero = '#607D8B'   # Gris acero
    
    # Dibujar suelo de cimentación con gradiente
    suelo_gradient = np.linspace(0.3, 0.8, 50)
    for i, alpha in enumerate(suelo_gradient):
        y_pos = -Df + (i * Df / 50)
        ax.add_patch(Rectangle((-1, y_pos), Bz+2, Df/50, 
                              facecolor=color_suelo, edgecolor='none', alpha=alpha))
    
    # Dibujar zapata con efecto 3D
    ax.add_patch(Rectangle((0, 0), Bz, hz, facecolor=color_zapata, 
                          edgecolor='#1565C0', linewidth=3))
    
    # Dibujar muro principal con gradiente
    for i in range(10):
        alpha = 0.7 + (i * 0.03)
        ax.add_patch(Rectangle((r, hz + i*h1/10), b, h1/10, 
                              facecolor=color_muro, edgecolor='#D84315', 
                              linewidth=1, alpha=alpha))
    
    # Dibujar parte superior del muro
    ax.add_patch(Rectangle((r, hz + h1), b, hm, facecolor=color_muro, 
                          edgecolor='#D84315', linewidth=3))
    
    # Dibujar relleno con patrón
    relleno_pts = [(r+b, hz), (Bz, hz), (Bz, hz+h1+hm), (r+b, hz+h1+hm)]
    ax.add_patch(Polygon(relleno_pts, facecolor=color_relleno, 
                        edgecolor='#F57F17', linewidth=2, alpha=0.8))
    
    # Agregar patrón de relleno (puntos)
    for i in range(20):
        x = r + b + (i * t / 20) + np.random.normal(0, 0.02)
        y = hz + np.random.uniform(0, h1+hm)
        if x < Bz and y < hz+h1+hm:
            ax.scatter(x, y, c='#F57F17', s=15, alpha=0.6)
    
    # Dibujar sobrecarga con flechas mejoradas y profesionales
    flechas_x = np.linspace(r+b+0.1, Bz-0.1, 15)
    for i, x in enumerate(flechas_x):
        color_flecha = '#D32F2F' if i % 3 == 0 else '#F44336' if i % 3 == 1 else '#E53935'
        ax.arrow(x, hz+h1+hm+0.7, 0, -0.5, head_width=0.1, head_length=0.2, 
                fc=color_flecha, ec=color_flecha, linewidth=4, alpha=0.9)
    
    # Texto de sobrecarga con fondo profesional (más pequeño)
    ax.text(Bz/2, hz+h1+hm+0.8, f'SOBRECARGA: {qsc} kg/m²', 
            ha='center', fontsize=10, fontweight='bold', 
            bbox=dict(boxstyle="round,pad=0.3", facecolor='#FFEBEE', 
                     edgecolor='#D32F2F', linewidth=2, alpha=0.9))
    
    # Agregar línea de nivel del terreno
    ax.axhline(y=hz, color='#795548', linewidth=2, linestyle='-', alpha=0.8)
    ax.text(Bz+0.2, hz, 'NIVEL TERRENO', fontsize=8, fontweight='bold', 
            color='#795548', rotation=90, va='center')
    
    # Añadir dimensiones con estilo profesional (más pequeñas)
    dimension_style = dict(arrowstyle='<->', color='#1976D2', linewidth=2)
    
    # Dimensiones horizontales
    ax.annotate('', xy=(0, hz/2), xytext=(r, hz/2), arrowprops=dimension_style)
    ax.text(r/2, hz/2-0.1, f'r={r}m', ha='center', fontsize=8, fontweight='bold', 
            color='#1976D2', bbox=dict(boxstyle="round,pad=0.1", facecolor='white', 
                                      edgecolor='#1976D2', alpha=0.8))
    
    ax.annotate('', xy=(r, hz/2), xytext=(r+b, hz/2), arrowprops=dimension_style)
    ax.text(r+b/2, hz/2-0.1, f'b={b}m', ha='center', fontsize=8, fontweight='bold', 
            color='#1976D2', bbox=dict(boxstyle="round,pad=0.1", facecolor='white', 
                                      edgecolor='#1976D2', alpha=0.8))
    
    ax.annotate('', xy=(r+b, hz/2), xytext=(Bz, hz/2), arrowprops=dimension_style)
    ax.text(r+b+t/2, hz/2-0.1, f't={t}m', ha='center', fontsize=8, fontweight='bold', 
            color='#1976D2', bbox=dict(boxstyle="round,pad=0.1", facecolor='white', 
                                      edgecolor='#1976D2', alpha=0.8))
    
    # Dimensiones verticales
    ax.annotate('', xy=(r+b/2, hz), xytext=(r+b/2, hz+h1), arrowprops=dimension_style)
    ax.text(r+b/2-0.15, hz+h1/2, f'h1={h1}m', ha='right', fontsize=8, fontweight='bold', 
            color='#1976D2', bbox=dict(boxstyle="round,pad=0.1", facecolor='white', 
                                      edgecolor='#1976D2', alpha=0.8))
    
    ax.annotate('', xy=(r+b/2, hz+h1), xytext=(r+b/2, hz+h1+hm), arrowprops=dimension_style)
    ax.text(r+b/2-0.15, hz+h1+hm/2, f'hm={hm}m', ha='right', fontsize=8, fontweight='bold', 
            color='#1976D2', bbox=dict(boxstyle="round,pad=0.1", facecolor='white', 
                                      edgecolor='#1976D2', alpha=0.8))
    
    ax.annotate('', xy=(r+b/2, 0), xytext=(r+b/2, -Df), arrowprops=dimension_style)
    ax.text(r+b/2-0.15, -Df/2, f'Df={Df}m', ha='right', fontsize=8, fontweight='bold', 
            color='#1976D2', bbox=dict(boxstyle="round,pad=0.1", facecolor='white', 
                                      edgecolor='#1976D2', alpha=0.8))
    
    ax.annotate('', xy=(0, 0), xytext=(0, hz), arrowprops=dimension_style)
    ax.text(-0.15, hz/2, f'hz={hz}m', ha='right', fontsize=8, fontweight='bold', 
            color='#1976D2', bbox=dict(boxstyle="round,pad=0.1", facecolor='white', 
                                      edgecolor='#1976D2', alpha=0.8))
    
    ax.annotate('', xy=(0, 0), xytext=(Bz, 0), arrowprops=dimension_style)
    ax.text(Bz/2, -0.2, f'Bz={Bz}m', ha='center', fontsize=8, fontweight='bold', 
            color='#1976D2', bbox=dict(boxstyle="round,pad=0.1", facecolor='white', 
                                      edgecolor='#1976D2', alpha=0.8))
    
    # Ajustar límites del gráfico para mejor visualización
    ax.set_xlim(-1.0, Bz+1.0)
    ax.set_ylim(-Df-0.5, hz+h1+hm+1.0)
    
    # Configurar aspecto y títulos profesionales
    ax.set_aspect('equal')
    
    # Título según el método
    if metodo == "coulomb" and datos_coulomb:
        titulo = f'DISEÑO PROFESIONAL DE MURO DE CONTENCIÓN - MÉTODO COULOMB\nCONSORCIO DEJ - Ingeniería y Construcción'
        subtitulo = f'β={datos_coulomb.get("beta", 0):.1f}°, α={datos_coulomb.get("alpha", 0):.1f}°, δ={datos_coulomb.get("delta", 0):.1f}°'
    else:
        titulo = 'DISEÑO PROFESIONAL DE MURO DE CONTENCIÓN - MÉTODO RANKINE\nCONSORCIO DEJ - Ingeniería y Construcción'
        subtitulo = 'Muro vertical liso - Sin fricción muro-suelo'
    
    ax.set_title(f'{titulo}\n{subtitulo}', 
                fontsize=16, fontweight='bold', pad=20, color='#1565C0')
    ax.set_xlabel('Distancia (metros)', fontsize=12, fontweight='bold', color='#424242')
    ax.set_ylabel('Altura (metros)', fontsize=12, fontweight='bold', color='#424242')
    
    # Agregar leyenda profesional (más pequeña y posicionada para no obstruir)
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor=color_zapata, edgecolor='#1565C0', label='ZAPATA'),
        Patch(facecolor=color_muro, edgecolor='#D84315', label='MURO'),
        Patch(facecolor=color_relleno, edgecolor='#F57F17', label='RELLENO'),
        Patch(facecolor=color_suelo, edgecolor='#5D4037', label='SUELO')
    ]
    ax.legend(handles=legend_elements, loc='upper left', fontsize=8, 
             frameon=True, fancybox=True, shadow=True, 
             title='ELEMENTOS', title_fontsize=9, bbox_to_anchor=(0.02, 0.98))
    
    # Agregar visualización de ángulos para método Coulomb
    if metodo == "coulomb" and datos_coulomb:
        # Dibujar ángulo β (inclinación del muro)
        beta = datos_coulomb.get("beta", 0)
        if beta > 0:
            # Línea vertical de referencia
            ax.plot([r+b/2, r+b/2], [hz, hz+h1], 'k--', linewidth=1, alpha=0.5)
            # Línea del muro inclinado
            ax.plot([r+b/2, r+b/2 + 0.3*math.cos(math.radians(90-beta))], 
                   [hz+h1, hz+h1 + 0.3*math.sin(math.radians(90-beta))], 
                   'r-', linewidth=2)
            # Arco del ángulo β
            arc_beta = np.linspace(90-beta, 90, 20)
            arc_x = r+b/2 + 0.15 * np.cos(np.radians(arc_beta))
            arc_y = hz+h1 + 0.15 * np.sin(np.radians(arc_beta))
            ax.plot(arc_x, arc_y, 'r-', linewidth=2)
            ax.text(r+b/2 + 0.2, hz+h1 + 0.1, f'β={beta:.1f}°', 
                   fontsize=10, fontweight='bold', color='red',
                   bbox=dict(boxstyle="round,pad=0.2", facecolor='white', edgecolor='red', alpha=0.8))
        
        # Dibujar ángulo α (inclinación del terreno)
        alpha = datos_coulomb.get("alpha", 0)
        if alpha > 0:
            # Línea horizontal de referencia
            ax.plot([r+b, Bz], [hz, hz], 'k--', linewidth=1, alpha=0.5)
            # Línea del terreno inclinado
            ax.plot([r+b, Bz], [hz, hz + (Bz-r-b)*math.tan(math.radians(alpha))], 
                   'g-', linewidth=2)
            # Arco del ángulo α
            arc_alpha = np.linspace(0, alpha, 20)
            arc_x = r+b + 0.3 * np.cos(np.radians(arc_alpha))
            arc_y = hz + 0.3 * np.sin(np.radians(arc_alpha))
            ax.plot(arc_x, arc_y, 'g-', linewidth=2)
            ax.text(r+b + 0.4, hz + 0.2, f'α={alpha:.1f}°', 
                   fontsize=10, fontweight='bold', color='green',
                   bbox=dict(boxstyle="round,pad=0.2", facecolor='white', edgecolor='green', alpha=0.8))
        
        # Mostrar información adicional de Coulomb
        info_text = f"""
        MÉTODO COULOMB:
        • β (inclinación muro): {beta:.1f}°
        • α (inclinación terreno): {alpha:.1f}°
        • δ (fricción muro-suelo): {datos_coulomb.get("delta", 0):.1f}°
        • Ka: {datos_coulomb.get("Ka", 0):.4f}
        • H efectiva: {datos_coulomb.get("H_efectiva", 0):.2f} m
        """
        ax.text(Bz + 0.3, hz + h1/2, info_text, fontsize=9, fontweight='bold',
               bbox=dict(boxstyle="round,pad=0.3", facecolor='#E8F5E8', 
                        edgecolor='#4CAF50', linewidth=2, alpha=0.9),
               verticalalignment='center')
    
    # Agregar grid sutil
    ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)
    
    # Configurar fondo
    ax.set_facecolor('#FAFAFA')
    fig.patch.set_facecolor('white')
    
    plt.tight_layout()
    return fig

# Función para dibujar muro con contrafuertes
def dibujar_muro_contrafuertes(dimensiones, resultados, datos_entrada):
    """
    Dibuja el muro de contención con contrafuertes de manera profesional mejorada
    """
    plt.style.use('default')
    fig, ax = plt.subplots(figsize=(16, 12))
    
    # Configuración de estilo profesional
    plt.rcParams['font.family'] = 'Arial'
    plt.rcParams['font.size'] = 10
    plt.rcParams['font.weight'] = 'bold'
    
    # Extraer dimensiones
    H = datos_entrada['H']
    h1 = dimensiones['h1']
    S_tipico = dimensiones['S_tipico']
    t_contrafuerte = dimensiones['t_contrafuertes']
    B_total = 1.6  # Ancho total estimado
    
    # Colores profesionales mejorados
    color_concreto = '#78909C'  # Gris concreto con textura
    color_contrafuerte = '#546E7A'  # Gris más oscuro para contrafuertes
    color_relleno = '#FFE082'  # Amarillo arena con patrón
    color_suelo = '#8D6E63'  # Marrón tierra con gradiente
    color_acero = '#37474F'  # Gris acero oscuro
    color_agua = '#80CBC4'  # Verde agua para drenaje
    
    # --- Dibujo mejorado del muro ---
    
    # 1. Suelo de cimentación con gradiente y textura
    suelo_gradient = np.linspace(0.3, 0.8, 50)
    for i, alpha in enumerate(suelo_gradient):
        y_pos = -0.5 + (i * 0.5 / 50)
        rect = Rectangle((-1, y_pos), B_total+2, 0.5/50, 
                        facecolor=color_suelo, edgecolor='none', alpha=alpha)
        ax.add_patch(rect)
        
        # Añadir textura de suelo (puntos aleatorios)
        if i % 5 == 0:
            x_points = np.random.uniform(-1, B_total+1, 10)
            y_points = np.random.uniform(y_pos, y_pos+0.5/50, 10)
            ax.scatter(x_points, y_points, color='#5D4037', s=2, alpha=0.5)
    
    # 2. Zapata con efecto 3D
    zapata = Rectangle((0, 0), B_total, h1, 
                      facecolor=color_concreto, edgecolor='#455A64', 
                      linewidth=2, hatch='...')
    ax.add_patch(zapata)
    
    # 3. Muro pantalla con textura de concreto
    muro = Rectangle((0.3, h1), 0.3, H-h1,
                    facecolor=color_concreto, edgecolor='#455A64',
                    linewidth=2, hatch='////', alpha=0.9)
    ax.add_patch(muro)
    
    # 4. Contrafuertes con detalles mejorados (3 contrafuertes)
    num_contrafuertes = 3
    for i in range(num_contrafuertes):
        x_pos = 0.3 + i * (S_tipico / num_contrafuertes)
        contrafuerte = Rectangle((x_pos, h1), t_contrafuerte, H-h1,
                                facecolor=color_contrafuerte, 
                                edgecolor='#37474F', linewidth=1.5,
                                hatch='xxx', alpha=0.8)
        ax.add_patch(contrafuerte)
        
        # Líneas de construcción en contrafuertes
        ax.plot([x_pos, x_pos+t_contrafuerte], [h1+(H-h1)/2, h1+(H-h1)/2],
                color='white', linewidth=1, linestyle='--', alpha=0.7)
    
    # 5. Relleno con patrón profesional
    relleno_pts = [(0.6, h1), (B_total, h1), (B_total, H), (0.6, H)]
    relleno = Polygon(relleno_pts, facecolor=color_relleno, 
                     edgecolor='#F57F17', linewidth=1, alpha=0.8,
                     hatch='ooo')
    ax.add_patch(relleno)
    
    # 6. Sistema de drenaje (tubos y filtro)
    for i in range(2):
        y_dren = h1 + (i+1)*(H-h1)/3
        ax.plot([0.6, 0.6-0.1], [y_dren, y_dren], color=color_agua, linewidth=3)
        ax.add_patch(Circle((0.6-0.15, y_dren), radius=0.03, 
                    facecolor=color_agua, edgecolor='#00695C'))
        # Filtro de grava
        ax.add_patch(Rectangle((0.6-0.2, y_dren-0.05), 0.1, 0.1,
                    facecolor='#A1887F', edgecolor='#5D4037', alpha=0.6,
                    hatch='...'))
    
    # 7. Sobrecarga con flechas mejoradas
    flechas_x = np.linspace(0.6+0.1, B_total-0.1, 8)
    for i, x in enumerate(flechas_x):
        color_flecha = '#D32F2F' if i % 2 == 0 else '#E53935'
        ax.arrow(x, H+0.5, 0, -0.3, head_width=0.08, head_length=0.1, 
                fc=color_flecha, ec=color_flecha, linewidth=2.5)
    
    # 8. Armadura (representación esquemática mejorada)
    # Armadura vertical principal
    for i in range(5):
        y = h1 + i * (H-h1)/5 + 0.05
        ax.plot([0.35, 0.35], [y, y+0.1], color=color_acero, 
               linewidth=3, solid_capstyle='round')
        # Estribos
        if i % 2 == 0:
            ax.plot([0.32, 0.38], [y+0.05, y+0.05], color=color_acero,
                   linewidth=1.5, linestyle='-')
    
    # Armadura horizontal
    for i in range(5):
        x = 0.3 + i * 0.3/5
        ax.plot([x, x+0.05], [h1+(H-h1)/2, h1+(H-h1)/2], 
               color=color_acero, linewidth=2.5, solid_capstyle='round')
    
    # Armadura contrafuertes (doble línea para mejor visualización)
    for i in range(num_contrafuertes):
        x_pos = 0.3 + i * (S_tipico / num_contrafuertes)
        for j in range(3):
            y = h1 + j * (H-h1)/3
            ax.plot([x_pos+0.02, x_pos+t_contrafuerte-0.02], [y, y], 
                   color=color_acero, linewidth=2)
            ax.plot([x_pos+0.02, x_pos+t_contrafuerte-0.02], [y+0.02, y+0.02],
                   color=color_acero, linewidth=2, alpha=0.7)
    
    # --- Dimensiones y anotaciones mejoradas ---
    dim_style = dict(arrowstyle='<->', color='#1565C0', linewidth=1.5)
    text_style = dict(fontsize=9, fontweight='bold', color='#1565C0',
                     bbox=dict(boxstyle="round,pad=0.2", facecolor='white', 
                              edgecolor='#1565C0', alpha=0.9))
    
    # Dimensiones principales con mejor disposición
    ax.annotate('', xy=(0, -0.2), xytext=(B_total, -0.2), arrowprops=dim_style)
    ax.text(B_total/2, -0.3, f'B={B_total}m', ha='center', **text_style)
    
    ax.annotate('', xy=(-0.2, 0), xytext=(-0.2, H), arrowprops=dim_style)
    ax.text(-0.35, H/2, f'H={H}m', va='center', rotation=90, **text_style)
    
    ax.annotate('', xy=(0.3, H+0.2), xytext=(0.3+S_tipico, H+0.2), 
               arrowprops=dim_style)
    ax.text(0.3+S_tipico/2, H+0.25, f'S={S_tipico:.2f}m', ha='center', **text_style)
    
    ax.annotate('', xy=(0.45, h1), xytext=(0.45, H), arrowprops=dim_style)
    ax.text(0.5, (h1+H)/2, f'e={0.3}m', va='center', **text_style)
    
    # Texto de sobrecarga mejorado
    ax.text(B_total/2, H+0.6, f'SOBRECARGA: {datos_entrada["S_c"]} kg/m²', 
           ha='center', fontsize=10, fontweight='bold', 
           bbox=dict(boxstyle="round,pad=0.3", facecolor='#FFEBEE', 
                    edgecolor='#D32F2F', linewidth=2, alpha=0.9))
    
    # --- Información técnica reorganizada ---
    # Mover información técnica a un cuadro en esquina superior derecha
    info_text = f"""
    DATOS TÉCNICOS:
    • Altura (H): {H:.2f} m
    • Espesor muro: 0.30 m
    • Espesor contrafuertes: {t_contrafuerte:.2f} m
    • Separación contrafuertes: {S_tipico:.2f} m
    • Sobrecarga: {datos_entrada['S_c']} kg/m²
    • Empuje total: {resultados['Pa_total']:.2f} t/m
    • FS Volcamiento: {resultados['FS_volcamiento']:.2f}
    • FS Deslizamiento: {resultados['FS_deslizamiento']:.2f}
    """
    
    ax.text(B_total+0.5, H*0.8, info_text, fontsize=8, fontweight='bold',
           bbox=dict(boxstyle="round,pad=0.3", facecolor='#E8F5E8', 
                    edgecolor='#4CAF50', linewidth=1, alpha=0.9),
           verticalalignment='top')
    
    # --- Leyenda profesional reposicionada ---
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor=color_concreto, edgecolor='#455A64', label='MURO PANTALLA', hatch='////'),
        Patch(facecolor=color_contrafuerte, edgecolor='#37474F', label='CONTRAFUERTE', hatch='xxx'),
        Patch(facecolor=color_relleno, edgecolor='#F57F17', label='RELLENO', hatch='ooo'),
        Patch(facecolor=color_suelo, edgecolor='#5D4037', label='SUELO', hatch='...'),
        Patch(facecolor=color_acero, edgecolor='#37474F', label='ARMADURA'),
        Patch(facecolor=color_agua, edgecolor='#00695C', label='DRENAJE')
    ]
    
    # Posicionar leyenda en esquina inferior derecha sin obstruir
    ax.legend(handles=legend_elements, loc='lower right', fontsize=8, 
             frameon=True, fancybox=True, shadow=True, 
             title='ELEMENTOS', title_fontsize=9,
             bbox_to_anchor=(1.0, 0.0))
    
    # --- Configuración final del gráfico ---
    ax.set_xlim(-0.5, B_total+1.0)  # Más espacio para leyenda
    ax.set_ylim(-0.5, H+1.0)
    ax.set_aspect('equal')
    
    # Título profesional con subtítulo
    titulo = "DISEÑO DE MURO CON CONTRAFUERTES - CONSORCIO DEJ"
    subtitulo = f"Altura: {H:.2f}m | Separación contrafuertes: {S_tipico:.2f}m | Espesor: {t_contrafuerte:.2f}m"
    
    ax.set_title(f'{titulo}\n{subtitulo}', 
                fontsize=14, fontweight='bold', pad=20, color='#1565C0')
    ax.set_xlabel('Distancia (metros)', fontsize=10, fontweight='bold', color='#424242')
    ax.set_ylabel('Altura (metros)', fontsize=10, fontweight='bold', color='#424242')
    
    # Grid sutil solo en áreas importantes
    ax.grid(True, alpha=0.1, linestyle='--', linewidth=0.5, which='both',
           axis='both', color='gray')
    
    # Configurar fondo
    ax.set_facecolor('#FAFAFA')
    fig.patch.set_facecolor('white')
    
    plt.tight_layout()
    return fig

# Configuración de la página
st.set_page_config(
    page_title="CONSORCIO DEJ - Muros de Contención",
    page_icon="🏗️",
    layout="wide"
)

# Header con fondo amarillo
st.markdown("""
<div style="text-align: center; padding: 20px; background-color: #FFD700; color: #2F2F2F; border-radius: 10px; margin-bottom: 20px; border: 2px solid #FFA500;">
    <h1>🏗️ CONSORCIO DEJ</h1>
    <p style="font-size: 18px; font-weight: bold;">Ingeniería y Construcción</p>
    <p style="font-size: 14px;">Diseño y Análisis de Muros de Contención</p>
</div>
""", unsafe_allow_html=True)

# Sistema de autenticación y pagos
def show_pricing_page():
    """Mostrar página de precios y planes"""
    st.title("💰 Planes y Precios - CONSORCIO DEJ")
    
    # Verificar si es administrador
    is_admin = st.session_state.get('user') == 'admin'
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("🆓 Plan Gratuito")
        st.write("**$0/mes**")
        st.write("✅ Cálculos básicos")
        st.write("✅ Análisis simple")
        st.write("✅ Reportes básicos")
        st.write("❌ Sin análisis completo")
        st.write("❌ Sin diseño del fuste")
        st.write("❌ Sin gráficos avanzados")
        
        if st.button("Seleccionar Gratuito", key="free_plan"):
            if is_admin:
                st.session_state['plan'] = "gratuito"
                if 'user_data' in st.session_state:
                    st.session_state['user_data']['plan'] = "gratuito"
                st.success("✅ Plan gratuito activado para administrador")
                st.rerun()
            else:
                st.info("Ya tienes acceso al plan gratuito")
    
    with col2:
        st.subheader("⭐ Plan Premium")
        st.write("**$29.99/mes**")
        st.write("✅ Todo del plan gratuito")
        st.write("✅ Análisis completo")
        st.write("✅ Diseño del fuste")
        st.write("✅ Gráficos avanzados")
        st.write("✅ Reportes PDF")
        st.write("❌ Sin soporte empresarial")
        
        if st.button("Actualizar a Premium", key="premium_plan"):
            if is_admin:
                # Acceso directo para administrador
                st.session_state['plan'] = "premium"
                if 'user_data' in st.session_state:
                    st.session_state['user_data']['plan'] = "premium"
                st.success("✅ Plan Premium activado para administrador")
                st.rerun()
            elif PAYMENT_SYSTEM_AVAILABLE:
                show_payment_form("premium")
            else:
                st.info("Sistema de pagos no disponible en modo demo")
    
    with col3:
        st.subheader("🏢 Plan Empresarial")
        st.write("**$99.99/mes**")
        st.write("✅ Todo del plan premium")
        st.write("✅ Soporte prioritario")
        st.write("✅ Múltiples proyectos")
        st.write("✅ Reportes personalizados")
        st.write("✅ Capacitación incluida")
        st.write("✅ API de integración")
        
        if st.button("Actualizar a Empresarial", key="business_plan"):
            if is_admin:
                # Acceso directo para administrador
                st.session_state['plan'] = "empresarial"
                if 'user_data' in st.session_state:
                    st.session_state['user_data']['plan'] = "empresarial"
                st.success("✅ Plan Empresarial activado para administrador")
                st.rerun()
            elif PAYMENT_SYSTEM_AVAILABLE:
                show_payment_form("empresarial")
            else:
                st.info("Sistema de pagos no disponible en modo demo")
    
    # Panel especial para administrador
    if is_admin:
        st.markdown("---")
        st.subheader("👨‍💼 Panel de Administrador")
        st.info("Como administrador, puedes cambiar tu plan directamente sin pasar por el sistema de pagos.")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("🆓 Activar Plan Gratuito", key="admin_free"):
                st.session_state['plan'] = "gratuito"
                if 'user_data' in st.session_state:
                    st.session_state['user_data']['plan'] = "gratuito"
                st.success("✅ Plan gratuito activado")
                st.rerun()
        
        with col2:
            if st.button("⭐ Activar Plan Premium", key="admin_premium"):
                st.session_state['plan'] = "premium"
                if 'user_data' in st.session_state:
                    st.session_state['user_data']['plan'] = "premium"
                st.success("✅ Plan premium activado")
                st.rerun()
        
        with col3:
            if st.button("🏢 Activar Plan Empresarial", key="admin_enterprise"):
                st.session_state['plan'] = "empresarial"
                if 'user_data' in st.session_state:
                    st.session_state['user_data']['plan'] = "empresarial"
                st.success("✅ Plan empresarial activado")
                st.rerun()

def show_payment_form(plan):
    """Mostrar formulario de pago"""
    st.subheader(f"💳 Pago - Plan {plan.title()}")
    
    # Verificar si hay usuario logueado
    if 'user' not in st.session_state:
        st.warning("⚠️ Debes iniciar sesión o registrarte primero")
        st.info("📝 Ve a la pestaña 'Registrarse' para crear una cuenta")
        return
    
    payment_method = st.selectbox(
        "Método de pago",
        ["yape", "plin", "paypal", "transferencia", "efectivo"],
        format_func=lambda x: {
            "yape": "📱 Yape (Más Rápido)",
            "plin": "📱 PLIN",
            "paypal": "💳 PayPal",
            "transferencia": "🏦 Transferencia Bancaria", 
            "efectivo": "💵 Pago en Efectivo"
        }[x]
    )
    
    if st.button("Procesar Pago", type="primary"):
        if PAYMENT_SYSTEM_AVAILABLE:
            try:
                result = payment_system.upgrade_plan(
                    st.session_state['user'], 
                    plan, 
                    payment_method
                )
                
                if result["success"]:
                    # Verificar si es acceso directo de admin
                    if result.get("admin_access"):
                        st.success("✅ " + result["message"])
                        st.info("🎉 Acceso completo activado para administrador")
                        
                        # Actualizar plan en session state
                        st.session_state['plan'] = plan
                        if 'user_data' in st.session_state:
                            st.session_state['user_data']['plan'] = plan
                        
                        # Botón para continuar
                        if st.button("🚀 Continuar con Acceso Completo", key="continue_full_access"):
                            st.rerun()
                    else:
                        st.success("✅ Pago procesado correctamente")
                        st.info("📋 Instrucciones de pago:")
                        st.text(result["instructions"])
                        
                        # Mostrar información adicional
                        st.info("📱 Envía el comprobante de pago a WhatsApp: +51 999 888 777")
                        
                        # Verificar si fue confirmado automáticamente
                        if result.get("auto_confirmed"):
                            st.success("🎉 ¡Plan activado inmediatamente!")
                            st.info("✅ Pago confirmado automáticamente")
                            
                            # Actualizar plan en session state
                            st.session_state['plan'] = plan
                            if 'user_data' in st.session_state:
                                st.session_state['user_data']['plan'] = plan
                            
                            # Botón para continuar con acceso completo
                            if st.button("🚀 Continuar con Acceso Completo", key="continue_full_access"):
                                st.rerun()
                        else:
                            st.info("⏰ Activación en 2 horas máximo")
                            st.info("🔄 Recarga la página después de 2 horas")
                else:
                    st.error(f"❌ Error: {result['message']}")
            except Exception as e:
                st.error(f"❌ Error en el sistema de pagos: {str(e)}")
                st.info("🔄 Intenta nuevamente o contacta soporte")
        else:
            st.error("❌ Sistema de pagos no disponible")
            st.info("🔧 Contacta al administrador para activar el sistema")

def show_auth_page():
    st.title("🏗️ CONSORCIO DEJ - Muros de Contención")
    
    # Pestañas para login/registro
    tab1, tab2, tab3 = st.tabs(["🔐 Iniciar Sesión", "📝 Registrarse", "💰 Planes y Precios"])
    
    with tab1:
        st.subheader("Iniciar Sesión")
        with st.form("login_form"):
            username = st.text_input("Usuario")
            password = st.text_input("Contraseña", type="password")
            submitted = st.form_submit_button("Entrar")
            
            if submitted:
                # Verificar credenciales especiales primero
                if username == "admin" and password == "admin123":
                    st.session_state['logged_in'] = True
                    st.session_state['user_data'] = {"username": "admin", "plan": "empresarial", "name": "Administrador"}
                    st.session_state['user'] = "admin"
                    st.session_state['plan'] = "empresarial"
                    st.success("¡Bienvenido Administrador!")
                    st.rerun()
                elif username == "demo" and password == "demo":
                    st.session_state['logged_in'] = True
                    st.session_state['user_data'] = {"username": "demo", "plan": "gratuito", "name": "Usuario Demo"}
                    st.session_state['user'] = "demo"
                    st.session_state['plan'] = "gratuito"
                    st.success("¡Bienvenido al modo demo!")
                    st.rerun()
                elif not PAYMENT_SYSTEM_AVAILABLE:
                    st.error("Credenciales disponibles: admin/admin123 o demo/demo")
                else:
                    # Sistema real
                    result = payment_system.login_user(username, password)
                    if result["success"]:
                        st.session_state['logged_in'] = True
                        st.session_state['user_data'] = result["user"]
                        st.session_state['user'] = result["user"]["email"]
                        st.session_state['plan'] = result["user"]["plan"]
                        st.success(f"¡Bienvenido, {result['user']['name']}!")
                        st.rerun()
                    else:
                        st.error(result["message"])
    
    with tab2:
        st.subheader("Crear Cuenta")
        with st.form("register_form"):
            new_username = st.text_input("Usuario", placeholder="Tu nombre de usuario")
            new_email = st.text_input("Email", placeholder="tuemail@gmail.com")
            new_password = st.text_input("Contraseña", type="password", placeholder="Mínimo 6 caracteres")
            confirm_password = st.text_input("Confirmar Contraseña", type="password")
            submitted = st.form_submit_button("📝 Registrarse", type="primary")
            
            if submitted:
                if not new_username or not new_email or not new_password:
                    st.error("❌ Todos los campos son obligatorios")
                elif new_password != confirm_password:
                    st.error("❌ Las contraseñas no coinciden")
                elif len(new_password) < 6:
                    st.error("❌ La contraseña debe tener al menos 6 caracteres")
                else:
                    if not PAYMENT_SYSTEM_AVAILABLE:
                        st.success("✅ Modo demo: Registro simulado exitoso")
                        st.info("🔑 Credenciales: demo / demo")
                    else:
                        result = payment_system.register_user(new_email, new_password, new_username)
                        if result["success"]:
                            st.success("✅ " + result["message"])
                            st.info("🔐 Ahora puedes iniciar sesión y actualizar tu plan")
                            
                            # Auto-login después del registro
                            login_result = payment_system.login_user(new_email, new_password)
                            if login_result["success"]:
                                st.session_state['logged_in'] = True
                                st.session_state['user_data'] = login_result["user"]
                                st.session_state['user'] = login_result["user"]["email"]
                                st.session_state['plan'] = login_result["user"]["plan"]
                                st.success(f"🎉 ¡Bienvenido, {login_result['user']['name']}!")
                                st.info("💰 Ve a 'Planes y Precios' para actualizar tu plan")
                                st.rerun()
                        else:
                            st.error("❌ " + result["message"])
    
    with tab3:
        show_pricing_page()

# Verificar estado de autenticación
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

# Función para actualizar plan del usuario
def update_user_plan():
    """Actualizar plan del usuario desde el sistema de pagos"""
    if PAYMENT_SYSTEM_AVAILABLE and 'user' in st.session_state:
        try:
            user_email = st.session_state['user']
            if user_email and user_email not in ['admin', 'demo']:
                real_plan = payment_system.get_user_plan(user_email)
                current_plan = real_plan.get('plan', 'gratuito')
                
                # Actualizar session state si el plan cambió
                if st.session_state.get('plan') != current_plan:
                    st.session_state['plan'] = current_plan
                    if 'user_data' in st.session_state:
                        st.session_state['user_data']['plan'] = current_plan
                    return True
        except Exception as e:
            pass
    return False

if not st.session_state['logged_in']:
    show_auth_page()
else:
    # Actualizar plan del usuario automáticamente
    plan_updated = update_user_plan()
    if plan_updated:
        st.success("🎉 ¡Tu plan ha sido actualizado!")
        st.rerun()
    # Mostrar información del usuario
    user_data = st.session_state.get('user_data', {})
    plan = user_data.get('plan', 'gratuito')
    
    # Header con información del plan
    if plan == "gratuito":
        st.sidebar.info("🆓 Plan Gratuito")
    elif plan == "premium":
        st.sidebar.success("⭐ Plan Premium")
    else:
        st.sidebar.success("🏢 Plan Empresarial")
    
    st.sidebar.write(f"Usuario: {st.session_state['user']}")
    st.sidebar.write(f"Plan: {plan}")
    
    # Botón para cerrar sesión
    if st.sidebar.button("🚪 Cerrar Sesión"):
        st.session_state['logged_in'] = False
        st.session_state['user_data'] = None
        st.session_state['user'] = None
        st.session_state['plan'] = None
        st.rerun()
    
    # Panel especial para administrador
    is_admin = st.session_state.get('user') == 'admin'
    if is_admin:
        st.sidebar.markdown("---")
        st.sidebar.subheader("👨‍💼 Panel de Administrador")
        st.sidebar.info("Acceso directo a todos los planes")
        
        col1, col2, col3 = st.sidebar.columns(3)
        with col1:
            if st.button("🆓 Gratuito", key="sidebar_free"):
                st.session_state['plan'] = "gratuito"
                if 'user_data' in st.session_state:
                    st.session_state['user_data']['plan'] = "gratuito"
                st.success("✅ Plan gratuito activado")
                st.rerun()
        
        with col2:
            if st.button("⭐ Premium", key="sidebar_premium"):
                st.session_state['plan'] = "premium"
                if 'user_data' in st.session_state:
                    st.session_state['user_data']['plan'] = "premium"
                st.success("✅ Plan premium activado")
                st.rerun()
        
        with col3:
            if st.button("🏢 Empresarial", key="sidebar_enterprise"):
                st.session_state['plan'] = "empresarial"
                if 'user_data' in st.session_state:
                    st.session_state['user_data']['plan'] = "empresarial"
                st.success("✅ Plan empresarial activado")
                st.rerun()
    
    # Mostrar página de precios si se solicita
    if st.session_state.get('show_pricing', False):
        show_pricing_page()
        
        # Botón para volver
        if st.button("← Volver a la aplicación"):
            st.session_state['show_pricing'] = False
            st.rerun()
    else:
        # Sidebar para navegación
        st.sidebar.title("📋 Menú Principal")
    
    # Mostrar plan actual
    if st.session_state['plan'] == "gratuito":
        st.sidebar.info("🆓 Plan Gratuito")
    else:
        st.sidebar.success("⭐ Plan Premium")
    
    opcion = st.sidebar.selectbox("Selecciona una opción", 
                                 ["🏗️ Cálculo Básico", "📊 Análisis Completo (Rankine)", "🔬 Análisis Coulomb", "🏗️ Diseño del Fuste", "📄 Generar Reporte", "📈 Gráficos", "ℹ️ Acerca de", "✉️ Contacto"])

    if opcion == "🏗️ Cálculo Básico":
        st.title("Cálculo Básico de Muro de Contención")
        st.info("Plan gratuito: Cálculos básicos de estabilidad")
        
        # Pestañas para diferentes tipos de cálculos
        tab1, tab2, tab3 = st.tabs(["📏 Dimensiones", "🏗️ Materiales", "⚖️ Cargas"])
        
        with tab1:
            st.subheader("Dimensiones del Muro")
            col1, col2 = st.columns(2)
            with col1:
                altura = st.number_input("Altura del muro (m)", min_value=1.0, max_value=15.0, value=3.0, step=0.1)
                base = st.number_input("Base del muro (m)", min_value=0.5, max_value=8.0, value=1.0, step=0.1)
            with col2:
                espesor = st.number_input("Espesor del muro (m)", min_value=0.2, max_value=2.0, value=0.3, step=0.05)
                longitud = st.number_input("Longitud del muro (m)", min_value=1.0, max_value=100.0, value=10.0, step=0.5)
        
        with tab2:
            st.subheader("Propiedades de los Materiales")
            col1, col2 = st.columns(2)
            with col1:
                peso_especifico = st.number_input("Peso específico del hormigón (kN/m³)", min_value=20.0, max_value=30.0, value=24.0, step=0.5)
                resistencia_concreto = st.number_input("Resistencia del hormigón (MPa)", min_value=15.0, max_value=50.0, value=25.0, step=1.0)
            with col2:
                peso_suelo = st.number_input("Peso específico del suelo (kN/m³)", min_value=15.0, max_value=22.0, value=18.0, step=0.5)
                angulo_friccion = st.number_input("Ángulo de fricción del suelo (°)", min_value=20.0, max_value=45.0, value=30.0, step=1.0)
        
        with tab3:
            st.subheader("Cargas y Factores de Seguridad")
            col1, col2 = st.columns(2)
            with col1:
                sobrecarga = st.number_input("Sobrecarga (kN/m²)", min_value=0.0, max_value=50.0, value=10.0, step=1.0)
                factor_seguridad = st.number_input("Factor de seguridad", min_value=1.2, max_value=3.0, value=1.5, step=0.1)
            with col2:
                sismo = st.checkbox("Considerar sismo")
                viento = st.checkbox("Considerar viento")
        
        # Botón para calcular
        if st.button("🚀 Calcular Muro de Contención", type="primary"):
            # Cálculos básicos
            volumen = altura * base * espesor * longitud
            peso_muro = volumen * peso_especifico
            
            # Cálculo del empuje del suelo
            angulo_rad = math.radians(angulo_friccion)
            ka = math.tan(math.radians(45 - angulo_friccion/2))**2  # Coeficiente de empuje activo
            empuje_suelo = 0.5 * peso_suelo * altura**2 * ka * longitud
            
            # Cálculo del momento volcador
            momento_volcador = empuje_suelo * altura / 3
            
            # Cálculo del momento estabilizador
            momento_estabilizador = peso_muro * base / 2
            
            # Factor de seguridad al volcamiento
            fs_volcamiento = momento_estabilizador / momento_volcador
            
            # Guardar resultados en session state
            st.session_state['resultados_basicos'] = {
                'altura': altura,
                'base': base,
                'espesor': espesor,
                'longitud': longitud,
                'peso_muro': peso_muro,
                'empuje_suelo': empuje_suelo,
                'fs_volcamiento': fs_volcamiento,
                'volumen': volumen,
                'ka': ka,
                'momento_volcador': momento_volcador,
                'momento_estabilizador': momento_estabilizador
            }
            
            st.success("¡Cálculos básicos completados exitosamente!")
            st.balloons()
            
            # MOSTRAR RESULTADOS INMEDIATAMENTE DESPUÉS DEL CÁLCULO
            st.subheader("📊 Resultados del Cálculo Básico")
            
            # Mostrar resultados en columnas
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("Peso del Muro", f"{peso_muro:.2f} kN")
                st.metric("Empuje del Suelo", f"{empuje_suelo:.2f} kN")
                st.metric("Volumen", f"{volumen:.2f} m³")
                st.metric("Coeficiente Ka", f"{ka:.3f}")
            
            with col2:
                st.metric("Factor de Seguridad", f"{fs_volcamiento:.2f}")
                st.metric("Momento Volcador", f"{momento_volcador:.2f} kN·m")
                st.metric("Momento Estabilizador", f"{momento_estabilizador:.2f} kN·m")
                st.metric("Altura", f"{altura:.1f} m")
            
            # Análisis de estabilidad
            st.subheader("🔍 Análisis de Estabilidad")
            if fs_volcamiento > 1.5:
                st.success(f"✅ El muro es estable al volcamiento (FS = {fs_volcamiento:.2f} > 1.5)")
            else:
                st.error(f"⚠️ El muro requiere revisión de estabilidad (FS = {fs_volcamiento:.2f} < 1.5)")
            
            # Gráfico básico
            st.subheader("📈 Gráfico de Fuerzas")
            datos = pd.DataFrame({
                'Fuerza': ['Peso Muro', 'Empuje Suelo'],
                'Valor (kN)': [peso_muro, empuje_suelo]
            })
            
            # Gráfico de barras mejorado
            if PLOTLY_AVAILABLE:
                fig = px.bar(datos, x='Fuerza', y='Valor (kN)', 
                            title="Comparación de Fuerzas - Plan Gratuito",
                            color='Fuerza',
                            color_discrete_map={'Peso Muro': '#2E8B57', 'Empuje Suelo': '#DC143C'})
                
                # Personalizar el gráfico
                fig.update_layout(
                    xaxis_title="Tipo de Fuerza",
                    yaxis_title="Valor (kN)",
                    showlegend=True,
                    height=400
                )
                
                # Agregar valores en las barras
                fig.update_traces(texttemplate='%{y:.1f}', textposition='outside')
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                # Gráfico alternativo con matplotlib
                fig, ax = plt.subplots(figsize=(10, 6))
                bars = ax.bar(datos['Fuerza'], datos['Valor (kN)'], 
                             color=['#2E8B57', '#DC143C'])
                ax.set_title("Comparación de Fuerzas - Plan Gratuito")
                ax.set_xlabel("Tipo de Fuerza")
                ax.set_ylabel("Valor (kN)")
                
                # Agregar valores en las barras
                for bar in bars:
                    height = bar.get_height()
                    ax.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                           f'{height:.1f}', ha='center', va='bottom')
                
                st.pyplot(fig)
            
            # Gráfico de momentos
            st.subheader("📊 Gráfico de Momentos")
            datos_momentos = pd.DataFrame({
                'Momento': ['Volcador', 'Estabilizador'],
                'Valor (kN·m)': [momento_volcador, momento_estabilizador]
            })
            
            if PLOTLY_AVAILABLE:
                fig2 = px.pie(datos_momentos, values='Valor (kN·m)', names='Momento',
                             title="Distribución de Momentos - Plan Gratuito",
                             color_discrete_map={'Volcador': '#FF6B6B', 'Estabilizador': '#4ECDC4'})
                
                fig2.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig2, use_container_width=True)
            else:
                # Gráfico alternativo con matplotlib
                fig2, ax2 = plt.subplots(figsize=(8, 8))
                ax2.pie(datos_momentos['Valor (kN·m)'], labels=datos_momentos['Momento'], 
                       autopct='%1.1f%%', colors=['#FF6B6B', '#4ECDC4'])
                ax2.set_title("Distribución de Momentos - Plan Gratuito")
                st.pyplot(fig2)

    elif opcion == "📊 Análisis Completo (Rankine)":
        # Verificar acceso basado en plan del usuario
        user_plan = st.session_state.get('plan', 'gratuito')
        user_email = st.session_state.get('user', '')
        
        # Verificar si es admin (acceso completo)
        is_admin = user_email == 'admin' or user_email == 'admin@consorciodej.com'
        
        # Para usuarios normales, verificar plan real en el sistema de pagos
        if PAYMENT_SYSTEM_AVAILABLE and user_email and not is_admin:
            try:
                real_plan = payment_system.get_user_plan(user_email)
                current_plan = real_plan.get('plan', 'gratuito')
                
                # Actualizar session state si el plan cambió
                if st.session_state.get('plan') != current_plan:
                    st.session_state['plan'] = current_plan
                    if 'user_data' in st.session_state:
                        st.session_state['user_data']['plan'] = current_plan
                    user_plan = current_plan
            except Exception as e:
                # Si hay error, usar el plan de session state
                pass
        
        if user_plan == "gratuito" and not is_admin:
            st.warning("⚠️ Esta función requiere plan premium. Actualiza tu cuenta para acceder a análisis completos.")
            st.info("Plan gratuito incluye: Cálculos básicos, resultados simples")
            st.info("Plan premium incluye: Análisis completo, reportes detallados, gráficos avanzados")
            
            # Mostrar botón para actualizar plan
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.button("⭐ Actualizar a Premium", type="primary"):
                    st.session_state['show_pricing'] = True
                    st.rerun()
        else:
            st.title("Análisis Completo de Muro de Contención - Teoría de Rankine")
            st.success("⭐ Plan Premium: Análisis completo con teoría de Rankine")
            
            # Mostrar comparación visual entre Rankine y Coulomb si ambos están disponibles
            if 'resultados_rankine' in st.session_state and 'resultados_coulomb' in st.session_state:
                st.subheader("🔍 Comparación Visual: Rankine vs Coulomb")
                
                # Gráfico comparativo profesional
                fig_comparacion = go.Figure()
                
                # Agregar barras para Rankine
                fig_comparacion.add_trace(go.Bar(
                    x=['Coeficiente Ka', 'Empuje Activo (t/m)', 'Componente Horizontal (t/m)'],
                    y=[st.session_state['resultados_rankine']['ka'], 
                       st.session_state['resultados_rankine']['Ea_total'],
                       st.session_state['resultados_rankine']['Ea_total']],  # Rankine no tiene componente vertical
                    name='Rankine',
                    marker_color='#1f77b4',
                    text=[f"{st.session_state['resultados_rankine']['ka']:.4f}", 
                          f"{st.session_state['resultados_rankine']['Ea_total']:.2f}",
                          f"{st.session_state['resultados_rankine']['Ea_total']:.2f}"],
                    textposition='auto'
                ))
                
                # Agregar barras para Coulomb
                fig_comparacion.add_trace(go.Bar(
                    x=['Coeficiente Ka', 'Empuje Activo (t/m)', 'Componente Horizontal (t/m)'],
                    y=[st.session_state['resultados_coulomb']['Ka'], 
                       st.session_state['resultados_coulomb']['Pa'],
                       st.session_state['resultados_coulomb']['Ph']],
                    name='Coulomb',
                    marker_color='#ff7f0e',
                    text=[f"{st.session_state['resultados_coulomb']['Ka']:.4f}", 
                          f"{st.session_state['resultados_coulomb']['Pa']:.2f}",
                          f"{st.session_state['resultados_coulomb']['Ph']:.2f}"],
                    textposition='auto'
                ))
                
                # Personalizar el gráfico
                fig_comparacion.update_layout(
                    title='Comparación de Resultados: Rankine vs Coulomb',
                    xaxis_title='Parámetro',
                    yaxis_title='Valor',
                    barmode='group',
                    template='plotly_white',
                    height=500,
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="right",
                        x=1
                    )
                )
                
                st.plotly_chart(fig_comparacion, use_container_width=True)
                
                # Análisis comparativo
                diferencia_ka = ((st.session_state['resultados_coulomb']['Ka'] - st.session_state['resultados_rankine']['ka']) / 
                                st.session_state['resultados_rankine']['ka']) * 100
                diferencia_empuje = ((st.session_state['resultados_coulomb']['Ph'] - st.session_state['resultados_rankine']['Ea_total']) / 
                                   st.session_state['resultados_rankine']['Ea_total']) * 100
                
                st.info(f"""
                **Análisis Comparativo:**
                - Diferencia en Ka: {diferencia_ka:.1f}%
                - Diferencia en empuje horizontal: {diferencia_empuje:.1f}%
                - Rankine es más conservador cuando la diferencia es positiva
                """)
            
            # Mostrar fórmulas de Rankine
            st.subheader("📚 Fórmulas de la Teoría de Rankine")
            
            with st.expander("📖 VER FÓRMULAS DE RANKINE", expanded=False):
                st.markdown("""
                ### Fórmulas de la Teoría de Rankine para Muros de Contención:
                
                #### 1. Coeficiente de Empuje Activo (Ka)
                ```
                Ka = tan²(45° - φ/2)
                ```
                
                Donde:
                - **φ**: Ángulo de fricción interna del suelo
                
                #### 2. Empuje Activo por Relleno
                ```
                Ea_relleno = ½ · Ka · γ · h₁²
                ```
                
                #### 3. Empuje Activo por Sobrecarga
                ```
                Ea_sobrecarga = Ka · qsc · h₁
                ```
                
                #### 4. Empuje Activo Total
                ```
                Ea_total = Ea_relleno + Ea_sobrecarga
                ```
                
                **Características de Rankine:**
                - Muro vertical liso
                - No considera fricción muro-suelo
                - Aproximación conservadora
                - Fórmulas más simples
                """)
            
            # Datos de entrada completos
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Dimensiones")
                h1 = st.number_input("Peralte de Zapata (m)", value=2.8, step=0.1)
                Df = st.number_input("Profundidad de desplante (m)", value=1.2, step=0.1)
                hm = st.number_input("Altura de coronación (m)", value=1.2, step=0.1, help="Según TAREA_DE_PROGRAMACION2.py, altura recomendada para mejor estabilidad")
                
                st.subheader("Materiales")
                gamma_relleno = st.number_input("Densidad del relleno (kg/m³)", value=1800, step=50)
                phi_relleno = st.number_input("Ángulo de fricción del relleno (°)", value=30, step=1)
                gamma_concreto = st.number_input("Peso específico del concreto (kg/m³)", value=2400, step=50)
                
            with col2:
                st.subheader("Propiedades del Suelo")
                gamma_cimentacion = st.number_input("Densidad del suelo de cimentación (kg/m³)", value=1700, step=50)
                phi_cimentacion = st.number_input("Ángulo de fricción del suelo (°)", value=25, step=1)
                cohesion = st.number_input("Cohesión del suelo (t/m²)", value=1.0, step=0.1)
                sigma_adm = st.number_input("Capacidad portante del suelo (kg/cm²)", value=2.5, step=0.1)
                
                st.subheader("Cargas")
                qsc = st.number_input("Sobrecarga (kg/m²)", value=1000, step=100)
                fc = st.number_input("Resistencia del concreto (kg/cm²)", value=210, step=10)
                fy = st.number_input("Resistencia del acero (kg/cm²)", value=4200, step=100)
            
            # Botones para diferentes cálculos de Rankine
            st.subheader("🔬 Cálculos Específicos - Rankine")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                if st.button("📊 Calcular Coeficiente Ka", type="primary", key="rankine_ka"):
                    # Calcular coeficiente de empuje activo de Rankine
                    phi_relleno_rad = math.radians(phi_relleno)
                    ka = math.tan(math.radians(45 - phi_relleno/2))**2
                    
                    st.success(f"✅ Coeficiente de empuje activo (Ka) = {ka:.6f}")
                    st.info(f"Ka = tan²(45° - φ/2) = tan²(45° - {phi_relleno}/2) = {ka:.6f}")
            
            with col2:
                if st.button("📏 Calcular Altura Equivalente", type="primary", key="rankine_hs"):
                    # Calcular altura equivalente por sobrecarga
                    hs = qsc / gamma_relleno
                    
                    st.success(f"✅ Altura equivalente por sobrecarga (hs) = {hs:.3f} m")
                    st.info(f"hs = qsc / γ = {qsc} / {gamma_relleno} = {hs:.3f} m")
            
            with col3:
                if st.button("⚖️ Calcular Empuje Relleno", type="primary", key="rankine_ea_relleno"):
                    # Calcular empuje activo por relleno
                    phi_relleno_rad = math.radians(phi_relleno)
                    ka = math.tan(math.radians(45 - phi_relleno/2))**2
                    Ea_relleno = 0.5 * ka * (gamma_relleno/1000) * h1**2
                    
                    st.success(f"✅ Empuje activo por relleno = {Ea_relleno:.3f} tn/m")
                    st.info(f"Ea_relleno = ½ · Ka · γ · h₁² = 0.5 · {ka:.6f} · {gamma_relleno/1000:.3f} · {h1}² = {Ea_relleno:.3f} tn/m")
            
            with col4:
                if st.button("📋 Calcular Empuje Sobrecarga", type="primary", key="rankine_ea_sobrecarga"):
                    # Calcular empuje activo por sobrecarga
                    phi_relleno_rad = math.radians(phi_relleno)
                    ka = math.tan(math.radians(45 - phi_relleno/2))**2
                    Ea_sobrecarga = ka * (qsc/1000) * h1
                    
                    st.success(f"✅ Empuje activo por sobrecarga = {Ea_sobrecarga:.3f} tn/m")
                    st.info(f"Ea_sobrecarga = Ka · qsc · h₁ = {ka:.6f} · {qsc/1000:.3f} · {h1} = {Ea_sobrecarga:.3f} tn/m")
            
            if st.button("🚀 Ejecutar Análisis Completo Rankine", type="primary"):
                # Cálculos completos basados en TAREA_DE_PROGRAMACION2.py
                
                # Coeficiente de empuje activo (fórmula correcta de Rankine)
                phi_relleno_rad = math.radians(phi_relleno)
                ka = math.tan(math.radians(45 - phi_relleno/2))**2
                
                # Altura equivalente por sobrecarga
                hs = qsc / gamma_relleno
                
                # Factor kc para concreto
                kc = 14.28  # Para fc = 210 kg/cm²
                
                # Dimensiones calculadas
                Bz = (h1 + Df) * (1 + hs/(h1 + Df)) * math.sqrt(ka)
                Bz = round(Bz, 2)
                
                hz = math.sqrt(((h1 + Df)**2 * (1 + hs/(h1 + Df))) / (9 * kc))
                hz = round(hz * 100) / 100
                hz = max(0.4, hz)
                
                b = math.sqrt(((h1 + hm)**2 * (1 + hs/(h1 + hm))) / (10 * kc))
                b = round(b * 100) / 100
                b = max(0.35, b)
                
                r = (2 * Bz - 3 * b) / 6
                r = round(r * 100) / 100
                r = max(0.7, r)
                
                t = Bz - r - b
                t = round(t * 100) / 100
                
                # Cálculos de estabilidad completos (basados en AVANCE2.PY)
                
                # 1. Empujes activos
                Ea_relleno = 0.5 * ka * (gamma_relleno/1000) * h1**2
                Ea_sobrecarga = ka * (qsc/1000) * h1  # Convertir kg/m² a tn/m²
                Ea_total = Ea_relleno + Ea_sobrecarga
                
                # 2. Empuje pasivo (si aplica)
                phi_cimentacion_rad = math.radians(phi_cimentacion)
                kp = math.tan(math.radians(45 + phi_cimentacion/2))**2
                Ep = 0.5 * kp * (gamma_cimentacion/1000) * Df**2
                
                # 3. Pesos de cada elemento
                W_muro = b * h1 * (gamma_concreto/1000)
                W_zapata = Bz * hz * (gamma_concreto/1000)
                W_relleno = t * h1 * (gamma_relleno/1000)
                
                # 4. Posiciones de los pesos (brazos de momento)
                x_muro = r + b/2
                x_zapata = Bz/2
                x_relleno = r + b + t/2
                
                # 5. Momentos estabilizadores
                Mr_muro = W_muro * x_muro
                Mr_zapata = W_zapata * x_zapata
                Mr_relleno = W_relleno * x_relleno
                Mr_pasivo = Ep * Df/3
                M_estabilizador = Mr_muro + Mr_zapata + Mr_relleno + Mr_pasivo
                
                # 6. Momentos volcadores
                Mv_relleno = Ea_relleno * h1/3
                Mv_sobrecarga = Ea_sobrecarga * h1/2
                M_volcador = Mv_relleno + Mv_sobrecarga
                
                # 7. Factor de seguridad al volcamiento
                FS_volcamiento = M_estabilizador / M_volcador
                
                # 8. Verificación al deslizamiento
                mu = math.tan(phi_cimentacion_rad)  # Coeficiente de fricción
                Fr_friccion = mu * (W_muro + W_zapata + W_relleno)
                Fr_pasivo = Ep
                Fr_total = Fr_friccion + Fr_pasivo
                Fd_total = Ea_total
                FS_deslizamiento = Fr_total / Fd_total
                
                # 9. Verificación de presiones sobre el suelo
                W_total = W_muro + W_zapata + W_relleno
                
                # Posición de la resultante vertical
                sum_momentos_verticales = Mr_muro + Mr_zapata + Mr_relleno
                x_barra = sum_momentos_verticales / W_total
                
                # Excentricidad
                e = abs(x_barra - Bz/2)
                
                # Presiones máxima y mínima
                q_max = (W_total / Bz) * (1 + 6*e/Bz)
                q_min = (W_total / Bz) * (1 - 6*e/Bz)
                
                # Verificar si hay tensiones
                tension = q_min < 0
                
                # Convertir a kg/cm²
                q_max_kg_cm2 = q_max * 0.1  # tn/m² a kg/cm²
                q_min_kg_cm2 = q_min * 0.1
                
                # Crear diccionario con datos de entrada para el diseño del fuste
                datos_entrada = {
                    'h1': h1,
                    'gamma_relleno': gamma_relleno,
                    'phi_relleno': phi_relleno,
                    'gamma_cimentacion': gamma_cimentacion,
                    'phi_cimentacion': phi_cimentacion,
                    'cohesion': cohesion,
                    'Df': Df,
                    'sigma_adm': sigma_adm,
                    'gamma_concreto': gamma_concreto,
                    'fc': fc,
                    'fy': fy,
                    'qsc': qsc,
                    'hm': hm
                }
                
                # Calcular diseño del fuste
                resultados_completos = {
                    'ka': ka,
                    'kp': kp,
                    'hs': hs,
                    'Bz': Bz,
                    'hz': hz,
                    'b': b,
                    'r': r,
                    't': t,
                    'hm': hm,
                    'h1': h1,
                    'Df': Df,
                    'qsc': qsc,
                    'Ea_relleno': Ea_relleno,
                    'Ea_sobrecarga': Ea_sobrecarga,
                    'Ea_total': Ea_total,
                    'Ep': Ep,
                    'W_muro': W_muro,
                    'W_zapata': W_zapata,
                    'W_relleno': W_relleno,
                    'W_total': W_total,
                    'M_volcador': M_volcador,
                    'M_estabilizador': M_estabilizador,
                    'FS_volcamiento': FS_volcamiento,
                    'FS_deslizamiento': FS_deslizamiento,
                    'q_max_kg_cm2': q_max_kg_cm2,
                    'q_min_kg_cm2': q_min_kg_cm2,
                    'e': e,
                    'tension': tension
                }
                
                diseno_fuste = calcular_diseno_fuste(resultados_completos, datos_entrada)
                
                # Guardar resultados completos
                st.session_state['resultados_completos'] = {
                    'ka': ka,
                    'kp': kp,
                    'hs': hs,
                    'Bz': Bz,
                    'hz': hz,
                    'b': b,
                    'r': r,
                    't': t,
                    'hm': hm,
                    'h1': h1,
                    'Df': Df,
                    'qsc': qsc,
                    'Ea_relleno': Ea_relleno,
                    'Ea_sobrecarga': Ea_sobrecarga,
                    'Ea_total': Ea_total,
                    'Ep': Ep,
                    'W_muro': W_muro,
                    'W_zapata': W_zapata,
                    'W_relleno': W_relleno,
                    'W_total': W_total,
                    'M_volcador': M_volcador,
                    'M_estabilizador': M_estabilizador,
                    'FS_volcamiento': FS_volcamiento,
                    'FS_deslizamiento': FS_deslizamiento,
                    'q_max_kg_cm2': q_max_kg_cm2,
                    'q_min_kg_cm2': q_min_kg_cm2,
                    'e': e,
                    'tension': tension
                }
                
                # Guardar datos de entrada y diseño del fuste
                st.session_state['datos_entrada'] = datos_entrada
                st.session_state['diseno_fuste'] = diseno_fuste
                
                # Guardar datos específicos para PDF premium (Rankine)
                st.session_state['resultados_rankine'] = {
                    'ka': ka,
                    'kp': kp,
                    'hs': hs,
                    'Bz': Bz,
                    'hz': hz,
                    'b': b,
                    'r': r,
                    't': t,
                    'hm': hm,
                    'h1': h1,
                    'Df': Df,
                    'qsc': qsc,
                    'Ea_relleno': Ea_relleno,
                    'Ea_sobrecarga': Ea_sobrecarga,
                    'Ea_total': Ea_total,
                    'Ep': Ep,
                    'W_muro': W_muro,
                    'W_zapata': W_zapata,
                    'W_relleno': W_relleno,
                    'W_total': W_total,
                    'M_volcador': M_volcador,
                    'M_estabilizador': M_estabilizador,
                    'FS_volcamiento': FS_volcamiento,
                    'FS_deslizamiento': FS_deslizamiento,
                    'q_max_kg_cm2': q_max_kg_cm2,
                    'q_min_kg_cm2': q_min_kg_cm2,
                    'e': e,
                    'tension': tension
                }
                
                st.session_state['datos_entrada_rankine'] = datos_entrada
                
                st.success("¡Análisis completo ejecutado exitosamente!")
                st.balloons()
                
                # Gráfico mejorado de distribución de presiones
                st.subheader("📊 Distribución de Presiones sobre el Suelo")
                
                # Crear datos para el gráfico
                presiones = {
                    'Tipo': ['Máxima', 'Mínima', 'Admisible'],
                    'Valor (kg/cm²)': [
                        q_max_kg_cm2,
                        q_min_kg_cm2,
                        sigma_adm
                    ],
                    'Color': ['#d62728', '#2ca02c', '#9467bd']
                }
                
                fig_presiones = px.bar(presiones, x='Tipo', y='Valor (kg/cm²)', color='Tipo',
                                      color_discrete_map={
                                          'Máxima': '#d62728',
                                          'Mínima': '#2ca02c',
                                          'Admisible': '#9467bd'
                                      },
                                      text='Valor (kg/cm²)')
                
                fig_presiones.update_traces(texttemplate='%{y:.2f}', textposition='outside')
                fig_presiones.update_layout(
                    title='Distribución de Presiones sobre el Suelo',
                    showlegend=False,
                    template='plotly_white',
                    height=400
                )
                
                st.plotly_chart(fig_presiones, use_container_width=True)
                
                # Anotaciones sobre las presiones
                if q_max_kg_cm2 > sigma_adm:
                    st.error("⚠️ La presión máxima excede la capacidad admisible del suelo")
                else:
                    st.success("✅ La presión máxima está dentro del límite admisible")
                    
                if q_min_kg_cm2 < 0:
                    st.error("⚠️ Existen tensiones en el suelo (presión mínima negativa)")
                else:
                    st.success("✅ No existen tensiones en el suelo")
                
                # MOSTRAR RESULTADOS COMPLETOS INMEDIATAMENTE
                st.subheader("📊 Resultados del Análisis Completo")
                
                # Mostrar resultados en columnas
                col1, col2 = st.columns(2)
                
                with col1:
                    st.metric("Coeficiente Ka", f"{ka:.3f}")
                    st.metric("Ancho de Zapata (Bz)", f"{Bz:.2f} m")
                    st.metric("Peralte de Zapata (hz)", f"{hz:.2f} m")
                    st.metric("Espesor del Muro (b)", f"{b:.2f} m")
                    st.metric("Longitud de Puntera (r)", f"{r:.2f} m")
                    st.metric("Longitud de Talón (t)", f"{t:.2f} m")
                
                with col2:
                    st.metric("Empuje Activo Total", f"{Ea_total:.2f} tn/m")
                    st.metric("Empuje Pasivo", f"{Ep:.2f} tn/m")
                    st.metric("Peso Total", f"{W_total:.2f} tn/m")
                    st.metric("FS Deslizamiento", f"{FS_deslizamiento:.2f}")
                    st.metric("Presión Máxima", f"{q_max_kg_cm2:.2f} kg/cm²")
                    st.metric("Excentricidad", f"{e:.3f} m")
                
                # Análisis de estabilidad completo
                st.subheader("🔍 Análisis de Estabilidad Completo")
                
                # Verificación al volcamiento
                col1, col2 = st.columns(2)
                with col1:
                    if FS_volcamiento >= 2.0:
                        st.success(f"✅ **Volcamiento:** CUMPLE (FS = {FS_volcamiento:.2f} ≥ 2.0)")
                    else:
                        st.error(f"⚠️ **Volcamiento:** NO CUMPLE (FS = {FS_volcamiento:.2f} < 2.0)")
                
                with col2:
                    if FS_deslizamiento >= 1.5:
                        st.success(f"✅ **Deslizamiento:** CUMPLE (FS = {FS_deslizamiento:.2f} ≥ 1.5)")
                    else:
                        st.error(f"⚠️ **Deslizamiento:** NO CUMPLE (FS = {FS_deslizamiento:.2f} < 1.5)")
                
                # Verificación de presiones
                st.subheader("📊 Verificación de Presiones sobre el Suelo")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Presión Máxima", f"{q_max_kg_cm2:.2f} kg/cm²")
                    if q_max_kg_cm2 <= sigma_adm:
                        st.success(f"✅ ≤ {sigma_adm} kg/cm²")
                    else:
                        st.error(f"⚠️ > {sigma_adm} kg/cm²")
                
                with col2:
                    st.metric("Presión Mínima", f"{q_min_kg_cm2:.2f} kg/cm²")
                    if not tension:
                        st.success("✅ Sin tensiones")
                    else:
                        st.error("⚠️ Hay tensiones")
                
                with col3:
                    st.metric("Excentricidad", f"{e:.3f} m")
                    e_limite = Bz / 6
                    if e <= e_limite:
                        st.success(f"✅ ≤ B/6 ({e_limite:.3f} m)")
                    else:
                        st.error(f"⚠️ > B/6 ({e_limite:.3f} m)")
                
                # Diseño del fuste
                st.subheader("🏗️ Diseño y Verificación del Fuste del Muro")
                st.info("Análisis estructural del fuste según PARTE 2.2.py")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.metric("Coeficiente Pasivo (kp)", f"{diseno_fuste['kp']:.2f}")
                    st.metric("Empuje Pasivo", f"{diseno_fuste['Ep_kg_m']:.0f} kg/m")
                    st.metric("Peralte Efectivo Req.", f"{diseno_fuste['dreq']:.2f} cm")
                    st.metric("Peralte Efectivo Real", f"{diseno_fuste['dreal']:.2f} cm")
                    st.metric("Área de Acero Req.", f"{diseno_fuste['As']:.2f} cm²")
                
                with col2:
                    st.metric("Área de Acero Mín.", f"{diseno_fuste['Asmin']:.2f} cm²")
                    st.metric("Número de Barras 5/8\"", f"{diseno_fuste['num_barras']}")
                    st.metric("Separación Barras", f"{diseno_fuste['separacion']:.1f} cm")
                    st.metric("Acero Retracción", f"{diseno_fuste['As_retraccion']:.2f} cm²")
                    st.metric("Barras Retracción 1/2\"", f"{diseno_fuste['num_barras_retraccion']}")
                
                # Verificaciones del fuste
                st.subheader("🔍 Verificaciones del Fuste")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if diseno_fuste['dreal'] >= diseno_fuste['dreq']:
                        st.success(f"✅ **Peralte:** CUMPLE (dreal = {diseno_fuste['dreal']:.2f} ≥ {diseno_fuste['dreq']:.2f} cm)")
                    else:
                        st.error(f"⚠️ **Peralte:** NO CUMPLE (dreal = {diseno_fuste['dreal']:.2f} < {diseno_fuste['dreq']:.2f} cm)")
                
                with col2:
                    if diseno_fuste['As_proporcionado'] >= diseno_fuste['As']:
                        st.success(f"✅ **Acero:** CUMPLE (As = {diseno_fuste['As_proporcionado']:.2f} ≥ {diseno_fuste['As']:.2f} cm²)")
                    else:
                        st.error(f"⚠️ **Acero:** NO CUMPLE (As = {diseno_fuste['As_proporcionado']:.2f} < {diseno_fuste['As']:.2f} cm²)")
                
                with col3:
                    if diseno_fuste['As_proporcionado'] >= diseno_fuste['Asmin']:
                        st.success(f"✅ **Acero Mín:** CUMPLE (As = {diseno_fuste['As_proporcionado']:.2f} ≥ {diseno_fuste['Asmin']:.2f} cm²)")
                    else:
                        st.error(f"⚠️ **Acero Mín:** NO CUMPLE (As = {diseno_fuste['As_proporcionado']:.2f} < {diseno_fuste['Asmin']:.2f} cm²)")
                
                # Resumen final
                cumple_todo = (FS_volcamiento >= 2.0 and FS_deslizamiento >= 1.5 and 
                              q_max_kg_cm2 <= sigma_adm and not tension and e <= e_limite and
                              diseno_fuste['dreal'] >= diseno_fuste['dreq'] and 
                              diseno_fuste['As_proporcionado'] >= diseno_fuste['As'])
                
                if cumple_todo:
                    st.success("🎉 **RESULTADO FINAL:** El muro CUMPLE con todos los requisitos de estabilidad y diseño estructural")
                else:
                    st.error("⚠️ **RESULTADO FINAL:** El muro NO CUMPLE con todos los requisitos. Se recomienda revisar dimensiones.")
                
                # Gráfico del muro de contención
                st.subheader("🏗️ Visualización del Muro de Contención")
                st.info("Gráfico detallado del muro con todas las dimensiones calculadas")
                
                # Crear dimensiones para el gráfico
                dimensiones_grafico = {
                    'Bz': Bz,
                    'hz': hz,
                    'b': b,
                    'r': r,
                    't': t,
                    'hm': hm
                }
                
                # Generar el gráfico del muro
                fig_muro = dibujar_muro_streamlit(dimensiones_grafico, h1, Df, qsc)
                
                # Mostrar el gráfico en Streamlit
                st.pyplot(fig_muro)
                
                # Información adicional sobre el gráfico
                st.markdown("""
                **Leyenda del Gráfico:**
                - 🔵 **Zapata (Azul claro):** Base de cimentación del muro
                - 🔴 **Muro (Rosa):** Estructura principal de contención
                - 🟡 **Relleno (Amarillo):** Material de relleno detrás del muro
                - 🟤 **Suelo (Marrón):** Suelo de cimentación
                - 🔴 **Flechas rojas:** Sobrecarga aplicada (qsc)
                - 🔵 **Dimensiones en azul:** Medidas calculadas del muro
                """)
                
                # Mostrar información del diseño del fuste si está disponible
                if 'diseno_fuste' in st.session_state:
                    st.subheader("🏗️ Información del Diseño del Fuste")
                    diseno_fuste = st.session_state['diseno_fuste']
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.info("**Diseño Estructural:**")
                        st.write(f"• Peralte efectivo requerido: {diseno_fuste['dreq']:.2f} cm")
                        st.write(f"• Peralte efectivo real: {diseno_fuste['dreal']:.2f} cm")
                        st.write(f"• Área de acero requerida: {diseno_fuste['As']:.2f} cm²")
                        st.write(f"• Área de acero mínima: {diseno_fuste['Asmin']:.2f} cm²")
                    
                    with col2:
                        st.info("**Distribución del Acero:**")
                        st.write(f"• Número de barras 5/8\": {diseno_fuste['num_barras']}")
                        st.write(f"• Separación entre barras: {diseno_fuste['separacion']:.1f} cm")
                        st.write(f"• Acero por retracción: {diseno_fuste['As_retraccion']:.2f} cm²")
                        st.write(f"• Barras retracción 1/2\": {diseno_fuste['num_barras_retraccion']}")
                
                # Gráficos adicionales para Rankine
                st.subheader("📈 Gráficos Adicionales - Análisis Rankine")
                
                # Gráfico de fuerzas
                col1, col2 = st.columns(2)
                
                with col1:
                    datos_fuerzas = pd.DataFrame({
                        'Fuerza': ['Empuje Activo', 'Empuje Pasivo', 'Peso Total'],
                        'Valor (tn/m)': [Ea_total, Ep, W_total]
                    })
                    
                    if PLOTLY_AVAILABLE:
                        fig_fuerzas = px.bar(datos_fuerzas, x='Fuerza', y='Valor (tn/m)',
                                            title="Análisis de Fuerzas - Rankine",
                                            color='Fuerza',
                                            color_discrete_map={
                                                'Empuje Activo': '#DC143C',
                                                'Empuje Pasivo': '#2E8B57',
                                                'Peso Total': '#4169E1'
                                            })
                        
                        fig_fuerzas.update_layout(
                            xaxis_title="Tipo de Fuerza",
                            yaxis_title="Valor (tn/m)",
                            height=400
                        )
                        
                        fig_fuerzas.update_traces(texttemplate='%{y:.2f}', textposition='outside')
                        st.plotly_chart(fig_fuerzas, use_container_width=True)
                
                with col2:
                    # Gráfico de momentos
                    datos_momentos = pd.DataFrame({
                        'Momento': ['Volcador', 'Estabilizador'],
                        'Valor (tn·m/m)': [M_volcador, M_estabilizador]
                    })
                    
                    if PLOTLY_AVAILABLE:
                        fig2 = px.pie(datos_momentos, values='Valor (tn·m/m)', names='Momento',
                                     title="Distribución de Momentos - Rankine",
                                     color_discrete_map={'Volcador': '#FF6B6B', 'Estabilizador': '#4ECDC4'})
                        
                        fig2.update_traces(textposition='inside', textinfo='percent+label+value')
                        st.plotly_chart(fig2, use_container_width=True)
                    else:
                        pass
                
                # Gráfico de dimensiones
                st.subheader("📏 Dimensiones del Muro - Rankine")
                dimensiones_rankine = {
                    'Dimensión': ['Bz', 'hz', 'b', 'r', 't'],
                    'Valor (m)': [Bz, hz, b, r, t]
                }
                
                if PLOTLY_AVAILABLE:
                    fig_dim = px.bar(pd.DataFrame(dimensiones_rankine), x='Dimensión', y='Valor (m)',
                                    title="Dimensiones Calculadas del Muro - Rankine",
                                    color='Dimensión',
                                    color_discrete_map={
                                        'Bz': '#FF1493',
                                        'hz': '#00CED1',
                                        'b': '#32CD32',
                                        'r': '#FFD700',
                                        't': '#FF6347'
                                    })
                    
                    fig_dim.update_layout(
                        xaxis_title="Dimensión",
                        yaxis_title="Valor (m)",
                        height=400
                    )
                    
                    fig_dim.update_traces(texttemplate='%{y:.2f}', textposition='outside')
                    st.plotly_chart(fig_dim, use_container_width=True)
                
                # Gráfico de factores de seguridad
                st.subheader("🛡️ Factores de Seguridad - Rankine")
                col1, col2 = st.columns(2)
                
                with col1:
                    datos_fs = pd.DataFrame({
                        'Verificación': ['Volcamiento', 'Deslizamiento'],
                        'Factor de Seguridad': [FS_volcamiento, FS_deslizamiento],
                        'Límite': [2.0, 1.5]
                    })
                    
                    if PLOTLY_AVAILABLE:
                        fig_fs = px.bar(datos_fs, x='Verificación', y=['Factor de Seguridad', 'Límite'],
                                       title="Factores de Seguridad - Rankine",
                                       barmode='group',
                                       color_discrete_map={
                                           'Factor de Seguridad': '#4ECDC4',
                                           'Límite': '#FF6B6B'
                                       })
                        
                        fig_fs.update_layout(
                            xaxis_title="Verificación",
                            yaxis_title="Factor de Seguridad",
                            height=400
                        )
                        
                        fig_fs.update_traces(texttemplate='%{y:.2f}', textposition='outside')
                        st.plotly_chart(fig_fs, use_container_width=True)
                
                with col2:
                    # Gráfico de presiones
                    datos_presiones = pd.DataFrame({
                        'Presión': ['Máxima', 'Mínima'],
                        'Valor (kg/cm²)': [q_max_kg_cm2, q_min_kg_cm2]
                    })
                    
                    if PLOTLY_AVAILABLE:
                        fig_pres = px.bar(datos_presiones, x='Presión', y='Valor (kg/cm²)',
                                         title="Presiones sobre el Suelo - Rankine",
                                         color='Presión',
                                         color_discrete_map={
                                             'Máxima': '#FF6B6B',
                                             'Mínima': '#4ECDC4'
                                         })
                        
                        fig_pres.update_layout(
                            xaxis_title="Tipo de Presión",
                            yaxis_title="Valor (kg/cm²)",
                            height=400
                        )
                        
                        fig_pres.update_traces(texttemplate='%{y:.2f}', textposition='outside')
                        st.plotly_chart(fig_pres, use_container_width=True)
                
                # Botones para generar reportes de Rankine
                st.subheader("📄 Generar Reportes - Análisis Rankine")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    # Generar reporte de texto para Rankine
                    reporte_rankine = f"""
# REPORTE TÉCNICO - ANÁLISIS RANKINE
## CONSORCIO DEJ
### Análisis según Teoría de Rankine
### Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}

### 1. DATOS DE ENTRADA:
- Peralte de Zapata (h1): {h1:.2f} m
- Profundidad de desplante (Df): {Df:.2f} m
- Altura de coronación (hm): {hm:.2f} m
- Densidad del relleno: {gamma_relleno} kg/m³
- Ángulo de fricción del relleno: {phi_relleno}°
- Densidad del suelo de cimentación: {gamma_cimentacion} kg/m³
- Ángulo de fricción del suelo: {phi_cimentacion}°
- Cohesión del suelo: {cohesion} t/m²
- Capacidad portante del suelo: {sigma_adm} kg/cm²
- Peso específico del concreto: {gamma_concreto} kg/m³
- Sobrecarga (qsc): {qsc} kg/m²
- Resistencia del concreto (fc): {fc} kg/cm²
- Resistencia del acero (fy): {fy} kg/cm²

### 2. COEFICIENTES DE PRESIÓN:
- Coeficiente de empuje activo (Ka): {ka:.3f}
- Coeficiente de empuje pasivo (Kp): {kp:.3f}
- Altura equivalente por sobrecarga (hs): {hs:.3f} m

### 3. DIMENSIONES CALCULADAS:
- Ancho de zapata (Bz): {Bz:.2f} m
- Peralte de zapata (hz): {hz:.2f} m
- Espesor del muro (b): {b:.2f} m
- Longitud de puntera (r): {r:.2f} m
- Longitud de talón (t): {t:.2f} m

### 4. ANÁLISIS DE EMPUJES:
- Empuje activo por relleno: {Ea_relleno:.2f} tn/m
- Empuje activo por sobrecarga: {Ea_sobrecarga:.2f} tn/m
- Empuje activo total: {Ea_total:.2f} tn/m
- Empuje pasivo: {Ep:.2f} tn/m

### 5. ANÁLISIS DE PESOS:
- Peso del muro: {W_muro:.2f} tn/m
- Peso de la zapata: {W_zapata:.2f} tn/m
- Peso del relleno: {W_relleno:.2f} tn/m
- Peso total: {W_total:.2f} tn/m

### 6. MOMENTOS Y FACTORES DE SEGURIDAD:
- Momento volcador: {M_volcador:.2f} tn·m/m
- Momento estabilizador: {M_estabilizador:.2f} tn·m/m
- Factor de seguridad al volcamiento: {FS_volcamiento:.2f}
- Factor de seguridad al deslizamiento: {FS_deslizamiento:.2f}

### 7. VERIFICACIÓN DE PRESIONES:
- Presión máxima: {q_max_kg_cm2:.2f} kg/cm²
- Presión mínima: {q_min_kg_cm2:.2f} kg/cm²
- Excentricidad: {e:.3f} m
- Hay tensiones: {'Sí' if tension else 'No'}

### 8. VERIFICACIONES DE ESTABILIDAD:
**Verificación al Volcamiento:**
- Factor de seguridad calculado: {FS_volcamiento:.2f}
- Factor mínimo requerido: 2.0
- Estado: {'✅ CUMPLE' if FS_volcamiento >= 2.0 else '⚠️ NO CUMPLE'}

**Verificación al Deslizamiento:**
- Factor de seguridad calculado: {FS_deslizamiento:.2f}
- Factor mínimo requerido: 1.5
- Estado: {'✅ CUMPLE' if FS_deslizamiento >= 1.5 else '⚠️ NO CUMPLE'}

**Verificación de Presiones:**
- Presión máxima: {q_max_kg_cm2:.2f} kg/cm²
- Presión admisible: {sigma_adm} kg/cm²
- Estado: {'✅ CUMPLE' if q_max_kg_cm2 <= sigma_adm else '⚠️ NO CUMPLE'}

**Verificación de Excentricidad:**
- Excentricidad calculada: {e:.3f} m
- Límite (B/6): {Bz/6:.3f} m
- Estado: {'✅ CUMPLE' if e <= Bz/6 else '⚠️ NO CUMPLE'}

### 9. DISEÑO Y VERIFICACIÓN DEL FUSTE:
**9.1 Coeficiente Pasivo y Empuje:**
- Coeficiente pasivo (kp): {diseno_fuste['kp']:.2f}
- Empuje pasivo: {diseno_fuste['Ep_kg_m']:.0f} kg/m
- Altura de aplicación: {diseno_fuste['yt']:.2f} m

**9.2 Diseño Estructural:**
- Peralte efectivo requerido: {diseno_fuste['dreq']:.2f} cm
- Peralte efectivo real: {diseno_fuste['dreal']:.2f} cm
- Área de acero requerida: {diseno_fuste['As']:.2f} cm²
- Área de acero mínima: {diseno_fuste['Asmin']:.2f} cm²
- Área de acero proporcionada: {diseno_fuste['As_proporcionado']:.2f} cm²

**9.3 Distribución del Acero:**
- Número de barras 5/8\": {diseno_fuste['num_barras']}
- Separación entre barras: {diseno_fuste['separacion']:.1f} cm
- Acero por retracción: {diseno_fuste['As_retraccion']:.2f} cm²
- Barras retracción 1/2\": {diseno_fuste['num_barras_retraccion']}

### 10. OBSERVACIONES TÉCNICAS:
- La teoría de Rankine considera muro vertical liso
- No considera fricción entre el muro y el suelo
- Proporciona una aproximación conservadora
- Fórmulas más simples que Coulomb
- Ka = tan²(45° - φ/2)

### 11. RECOMENDACIONES:
- Verificar la capacidad portante del suelo en campo
- Revisar el diseño del refuerzo estructural según ACI 318
- Considerar efectos sísmicos según la normativa local
- Realizar inspecciones periódicas durante la construcción
- Monitorear deformaciones durante el servicio
- Verificar drenaje del relleno para evitar presiones hidrostáticas

### 12. INFORMACIÓN DEL PROYECTO:
- Empresa: CONSORCIO DEJ
- Método de análisis: Teoría de Rankine
- Fecha de análisis: {datetime.now().strftime('%d/%m/%Y %H:%M')}
- Plan: Premium
- Software: Streamlit + Python

---
**Este reporte fue generado automáticamente por el sistema de análisis de muros de contención de CONSORCIO DEJ.**
**Para consultas técnicas, contacte a nuestro equipo de ingeniería.**
"""
                    
                    st.download_button(
                        label="📥 Descargar TXT Rankine",
                        data=reporte_rankine,
                        file_name=f"reporte_rankine_muro_contencion_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                        mime="text/plain"
                    )
                
                with col2:
                    # Generar PDF para Rankine
                    try:
                        # Verificar si hay resultados de Rankine disponibles
                        if 'resultados_rankine' in st.session_state and 'datos_entrada_rankine' in st.session_state:
                            resultados_rankine_pdf = st.session_state['resultados_rankine']
                            datos_entrada_rankine = st.session_state['datos_entrada_rankine']
                        else:
                            st.error("⚠️ No hay resultados de análisis Rankine disponibles.")
                            st.info("Ejecuta primero el análisis completo de Rankine.")
                            st.stop()
                        
                        # Verificar si hay diseño del fuste disponible
                        if 'diseno_fuste' not in st.session_state:
                            st.error("⚠️ No hay datos de diseño del fuste disponibles.")
                            st.info("Ejecuta primero el análisis completo de Rankine.")
                            st.stop()
                        
                        diseno_fuste = st.session_state['diseno_fuste']
                        
                        # Verificar si hay resultados de Coulomb disponibles
                        resultados_coulomb_pdf = None
                        datos_entrada_coulomb_pdf = None
                        if 'resultados_coulomb' in st.session_state and 'datos_entrada_coulomb' in st.session_state:
                            resultados_coulomb_pdf = st.session_state['resultados_coulomb']
                            datos_entrada_coulomb_pdf = st.session_state['datos_entrada_coulomb']
                        
                        pdf_buffer_rankine = generar_pdf_reportlab(
                            resultados_rankine_pdf, 
                            datos_entrada_rankine, 
                            diseno_fuste, 
                            "premium",
                            resultados_coulomb_pdf,
                            datos_entrada_coulomb_pdf
                        )
                        
                        st.download_button(
                            label="📄 Descargar PDF Rankine",
                            data=pdf_buffer_rankine.getvalue(),
                            file_name=f"reporte_rankine_muro_contencion_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                            mime="application/pdf"
                        )
                    except Exception as e:
                        st.error(f"⚠️ Error generando PDF: {str(e)}")
                        st.info("Intenta ejecutar el análisis completo nuevamente")
                
                with col3:
                    if st.button("🖨️ Generar Reporte en Pantalla", type="primary", key="rankine_pantalla"):
                        st.success("✅ Reporte Rankine generado exitosamente")
                        st.balloons()
                        
                        # Mostrar el reporte en formato expandible
                        with st.expander("📋 VER REPORTE RANKINE COMPLETO", expanded=True):
                            st.markdown(reporte_rankine)

    elif opcion == "🔬 Análisis Coulomb":
        st.title("Análisis de Empuje Activo según Teoría de Coulomb")
        st.success("🔬 Plan Premium: Análisis completo con teoría de Coulomb")
        
        # Mostrar diagrama de fuerzas si hay resultados
        if 'resultados_coulomb' in st.session_state:
            st.subheader("📐 Diagrama de Fuerzas - Coulomb")
            
            # Crear diagrama vectorial profesional
            fig_fuerzas = go.Figure()
            
            # Definir puntos de referencia
            beta_rad = math.radians(st.session_state['resultados_coulomb']['beta'])
            escala = 0.2  # Escala para visualización
            
            # Empuje activo (Pa)
            fig_fuerzas.add_annotation(
                ax=0, ay=0,
                axref="x", ayref="y",
                x=st.session_state['resultados_coulomb']['Ph'] * escala * math.cos(beta_rad),
                y=st.session_state['resultados_coulomb']['Ph'] * escala * math.sin(beta_rad),
                xref="x", yref="y",
                showarrow=True,
                arrowhead=2,
                arrowsize=1.5,
                arrowwidth=2,
                arrowcolor="#d62728",
                text=f"Pa = {st.session_state['resultados_coulomb']['Pa']:.2f} t/m",
                font=dict(size=12, color="#d62728")
            )
            
            # Componente horizontal (Ph)
            fig_fuerzas.add_annotation(
                ax=0, ay=0,
                axref="x", ayref="y",
                x=st.session_state['resultados_coulomb']['Ph'] * escala,
                y=0,
                xref="x", yref="y",
                showarrow=True,
                arrowhead=2,
                arrowsize=1.5,
                arrowwidth=2,
                arrowcolor="#ff7f0e",
                text=f"Ph = {st.session_state['resultados_coulomb']['Ph']:.2f} t/m",
                font=dict(size=12, color="#ff7f0e")
            )
            
            # Componente vertical (Pv)
            fig_fuerzas.add_annotation(
                ax=0, ay=0,
                axref="x", ayref="y",
                x=0,
                y=st.session_state['resultados_coulomb']['Pv'] * escala,
                xref="x", yref="y",
                showarrow=True,
                arrowhead=2,
                arrowsize=1.5,
                arrowwidth=2,
                arrowcolor="#2ca02c",
                text=f"Pv = {st.session_state['resultados_coulomb']['Pv']:.2f} t/m",
                font=dict(size=12, color="#2ca02c")
            )
            
            # Empuje por sobrecarga (PSC)
            fig_fuerzas.add_annotation(
                ax=0, ay=0,
                axref="x", ayref="y",
                x=st.session_state['resultados_coulomb']['PSC'] * escala,
                y=0,
                xref="x", yref="y",
                showarrow=True,
                arrowhead=2,
                arrowsize=1.5,
                arrowwidth=2,
                arrowcolor="#9467bd",
                text=f"PSC = {st.session_state['resultados_coulomb']['PSC']:.2f} t/m",
                font=dict(size=12, color="#9467bd")
            )
            
            # Configurar el gráfico
            fig_fuerzas.update_layout(
                title="Diagrama Vectorial de Fuerzas - Coulomb",
                xaxis=dict(range=[-1, 1], showgrid=True, zeroline=True),
                yaxis=dict(range=[-0.5, 1.5], showgrid=True, zeroline=True),
                showlegend=False,
                width=600,
                height=500,
                margin=dict(l=20, r=20, t=40, b=20),
                plot_bgcolor='rgba(0,0,0,0)'
            )
            
            st.plotly_chart(fig_fuerzas, use_container_width=True)
            
            # Explicación de los resultados
            st.markdown("""
            **Interpretación del Diagrama:**
            - 🔴 **Pa (Rojo):** Empuje activo total (resultante)
            - 🟠 **Ph (Naranja):** Componente horizontal del empuje
            - 🟢 **Pv (Verde):** Componente vertical del empuje
            - 🟣 **PSC (Morado):** Empuje debido a la sobrecarga
            """)
        
        # Gráfico de influencia de ángulos
        if 'resultados_coulomb' in st.session_state:
            st.subheader("📐 Influencia de los Ángulos en el Empuje")
            
            # Crear datos para el gráfico
            angulos = ['β (Inclinación)', 'δ (Fricción)', 'α (Terreno)']
            valores = [
                st.session_state['resultados_coulomb']['beta'],
                st.session_state['datos_entrada_coulomb']['delta'],
                st.session_state['datos_entrada_coulomb']['alpha']
            ]
            
            fig_angulos = px.bar(x=angulos, y=valores, text=valores,
                                title="Ángulos Clave en el Análisis Coulomb",
                                labels={'x': 'Ángulo', 'y': 'Valor (°)'},
                                color=angulos,
                                color_discrete_map={
                                    'β (Inclinación)': '#1f77b4',
                                    'δ (Fricción)': '#ff7f0e',
                                    'α (Terreno)': '#2ca02c'
                                })
            
            fig_angulos.update_traces(texttemplate='%{y:.1f}°', textposition='outside')
            fig_angulos.update_layout(
                showlegend=False,
                template='plotly_white',
                height=400
            )
            
            st.plotly_chart(fig_angulos, use_container_width=True)
            
            # Explicación de la influencia
            st.markdown("""
            **Influencia de los Ángulos:**
            - **β (Inclinación del muro):** Afecta directamente la geometría y el empuje
            - **δ (Fricción muro-suelo):** Mayor δ reduce el empuje horizontal
            - **α (Inclinación del terreno):** Terreno inclinado aumenta el empuje
            """)
        
        # Mostrar fórmulas de Coulomb
        st.subheader("📚 Fórmulas de la Teoría de Coulomb")
        
        with st.expander("📖 VER FÓRMULAS COMPLETAS DE COULOMB", expanded=False):
            st.markdown("""
            ### Resumen de las Fórmulas para el Empuje Activo según la Teoría de Coulomb en Muros de Contención:
            
            #### 1. Coeficiente de Empuje Activo (Ka)
            La fórmula general para el coeficiente de empuje activo según Coulomb es:
            
            ```
            Ka = sin²(β + φ₁') / [sin²(β) · sin(β - δ) · (1 + √(sin(φ₁' + δ) · sin(φ₁' - α) / sin(β - δ) · sin(β + α)))²]
            ```
            
            Donde:
            - **β**: Ángulo de inclinación del muro respecto a la vertical
            - **φ₁'**: Ángulo de fricción interna del suelo de relleno
            - **δ**: Ángulo de fricción entre el muro y el relleno
            - **α**: Ángulo de inclinación del terreno
            
            #### 2. Altura Efectiva del Muro (H')
            ```
            H' = H + (t₂/2 + b₂/2) · tan(α)
            ```
            
            #### 3. Empuje Activo Total (Pa)
            ```
            Pa = ½ · Ka · γ₁ · (H')²
            ```
            
            #### 4. Componentes del Empuje Activo:
            **Componente Horizontal (Ph):**
            ```
            Ph = Pa · cos(90° - β + δ)
            ```
            
            **Componente Vertical (Pv):**
            ```
            Pv = Pa · sin(90° - β + δ)
            ```
            
            #### 5. Empuje por Sobrecarga (PSC)
            ```
            PSC = Ka · H · (S/c / 1000) · (sin(β) / sin(β + α))
            ```
            
            **Observaciones:**
            - Los valores de δ dependen del material de relleno (ejemplo: 21° para arena gruesa)
            - La teoría de Coulomb considera la fricción entre el muro y el suelo (δ), a diferencia de Rankine
            """)
        
        # Datos de entrada para Coulomb
        st.subheader("📊 Datos de Entrada para Análisis Coulomb")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Datos del Suelo de Relleno")
            gamma1 = st.number_input("Peso específico del suelo de relleno (γ₁) [t/m³]", value=1.85, step=0.01, help="Peso específico del suelo de relleno")
            phi1 = st.number_input("Ángulo de fricción del suelo de relleno (φ'₁) [°]", value=32.0, step=0.1, help="Ángulo de fricción interna del suelo de relleno")
            cohesion1 = st.number_input("Cohesión del suelo de relleno (c'₁) [kg/cm²]", value=0.0, step=0.01, help="Cohesión del suelo de relleno")
            alpha = st.number_input("Ángulo de inclinación del terreno (α) [°]", value=10.0, step=0.1, help="Ángulo de inclinación del terreno natural")
            
            st.subheader("Datos del Suelo de la Base")
            gamma2 = st.number_input("Peso específico del suelo de la base (γ₂) [t/m³]", value=1.80, step=0.01, help="Peso específico del suelo de la base")
            cohesion2 = st.number_input("Cohesión del suelo de la base (c'₂) [kg/cm²]", value=0.30, step=0.01, help="Cohesión del suelo de la base")
            sigma_u = st.number_input("Capacidad de carga de la base (σᵤ) [kg/cm²]", value=2.50, step=0.01, help="Capacidad portante de la base")
            phi2 = st.number_input("Ángulo de fricción del suelo de la base (φ'₂) [°]", value=24.0, step=0.1, help="Ángulo de fricción interna del suelo de la base")
        
        with col2:
            st.subheader("Datos del Muro")
            gamma_muro = st.number_input("Peso específico del muro (γ_muro) [t/m³]", value=2.40, step=0.01, help="Peso específico del concreto del muro")
            S_c = st.number_input("Sobrecarga (S/c) [kg/m²]", value=750, step=10, help="Sobrecarga aplicada sobre el terreno")
            H = st.number_input("Altura total del muro (H) [m]", value=4.00, step=0.01, help="Altura total del muro de contención")
            D = st.number_input("Profundidad de desplante (D) [m]", value=1.00, step=0.01, help="Profundidad de desplante del muro")
            h1 = st.number_input("Peralte de Zapata (h1) [m]", value=3.00, step=0.01, help="Peralte de Zapata que contiene el suelo")
            t2 = st.number_input("Base del triángulo 2 (t2) [m]", value=0.30, step=0.01, help="Base del triángulo de inclinación del muro")
            b2 = st.number_input("Longitud del talón (b2) [m]", value=1.00, step=0.01, help="Longitud del talón del muro")
            delta = st.number_input("Ángulo de fricción muro-suelo (δ) [°]", value=21.0, step=0.1, help="Ángulo de fricción entre el muro y el relleno")
        
        # Botones para diferentes cálculos
        st.subheader("🔬 Cálculos Específicos")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("📐 Calcular Ángulo β", type="primary"):
                beta = math.atan((H - h1) / t2)
                beta_deg = math.degrees(beta)
                st.success(f"✅ Ángulo de inclinación del muro (β) = {beta_deg:.2f}°")
                st.info(f"β = arctan((H - h1) / t2) = arctan(({H} - {h1}) / {t2}) = {beta_deg:.2f}°")
        with col2:
            if st.button("📊 Calcular Coeficiente Ka", type="primary"):
                if t2 != 0:
                    beta = math.degrees(math.atan((H - h1) / t2))
                else:
                    beta = 90.0
                num = math.sin(math.radians(beta + phi1)) ** 2
                den = (math.sin(math.radians(beta)) ** 2) * math.sin(math.radians(beta - delta)) * (
                    1 + math.sqrt(
                        (math.sin(math.radians(phi1 + delta)) * math.sin(math.radians(phi1 - alpha))) /
                        (math.sin(math.radians(beta - delta)) * math.sin(math.radians(beta + alpha)))
                    )
                ) ** 2
                Ka = num / den
                st.success(f"✅ Coeficiente de empuje activo (Ka) = {Ka:.6f}")
                st.info("Calculado según la fórmula de Coulomb profesional (todos los ángulos en grados, conversión a radianes solo en las funciones trigonométricas)")
        with col3:
            if st.button("📏 Calcular Altura Efectiva", type="primary"):
                alpha_rad = math.radians(alpha)
                H_efectiva = H + (t2/2 + b2/2) * math.tan(alpha_rad)
                st.success(f"✅ Altura efectiva del muro (H') = {H_efectiva:.2f} m")
                st.info(f"H' = H + (t₂/2 + b₂/2) · tan(α) = {H} + ({t2/2:.2f} + {b2/2:.2f}) · tan({alpha}°) = {H_efectiva:.2f} m")
        with col4:
            if st.button("⚖️ Calcular Empuje Total", type="primary"):
                datos_entrada = {
                    'H': H, 'h1': h1, 't2': t2, 'b2': b2,
                    'phi1': phi1, 'delta': delta, 'alpha': alpha,
                    'gamma1': gamma1, 'S_c': S_c,
                    'cohesion1': cohesion1, 'gamma2': gamma2, 'cohesion2': cohesion2,
                    'sigma_u': sigma_u, 'phi2': phi2, 'gamma_muro': gamma_muro, 'D': D
                }
                resultados_coulomb = calcular_empuje_coulomb(datos_entrada)
                st.success("✅ Empuje activo calculado según Coulomb")
                st.info(f"Empuje total horizontal = {resultados_coulomb['P_total_horizontal']:.3f} t/m")
        # Botón para análisis completo
        if st.button("🚀 Ejecutar Análisis Completo Coulomb", type="primary"):
            datos_entrada = {
                'H': H, 'h1': h1, 't2': t2, 'b2': b2,
                'phi1': phi1, 'delta': delta, 'alpha': alpha,
                'gamma1': gamma1, 'S_c': S_c,
                'cohesion1': cohesion1, 'gamma2': gamma2, 'cohesion2': cohesion2,
                'sigma_u': sigma_u, 'phi2': phi2, 'gamma_muro': gamma_muro, 'D': D
            }
            resultados_coulomb = calcular_empuje_coulomb(datos_entrada)
            st.session_state['resultados_coulomb'] = resultados_coulomb
            st.session_state['datos_entrada_coulomb'] = datos_entrada
            st.success("¡Análisis Coulomb completado exitosamente!")
            st.balloons()
            
            # MOSTRAR RESULTADOS COMPLETOS
            st.subheader("📊 Resultados del Análisis Coulomb")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("Ángulo de inclinación (β)", f"{resultados_coulomb['beta']:.2f}°")
                st.metric("Coeficiente Ka", f"{resultados_coulomb['Ka']:.6f}")
                st.metric("Altura efectiva (H')", f"{resultados_coulomb['H_efectiva']:.2f} m")
                st.metric("Empuje activo total (Pa)", f"{resultados_coulomb['Pa']:.3f} t/m")
            
            with col2:
                st.metric("Componente horizontal (Ph)", f"{resultados_coulomb['Ph']:.3f} t/m")
                st.metric("Componente vertical (Pv)", f"{resultados_coulomb['Pv']:.3f} t/m")
                st.metric("Empuje por sobrecarga (PSC)", f"{resultados_coulomb['PSC']:.3f} t/m")
                st.metric("Empuje total horizontal", f"{resultados_coulomb['P_total_horizontal']:.3f} t/m")
            
            # Comparación con Rankine
            st.subheader("🔄 Comparación: Coulomb vs Rankine")
            
            # Calcular Ka de Rankine para comparación
            phi1_rad = math.radians(phi1)
            ka_rankine = math.tan(math.radians(45 - phi1/2))**2
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.info("**Teoría de Coulomb:**")
                st.write(f"• Ka = {resultados_coulomb['Ka']:.6f}")
                st.write(f"• Considera fricción muro-suelo")
                st.write(f"• Más realista para muros rugosos")
            
            with col2:
                st.info("**Teoría de Rankine:**")
                st.write(f"• Ka = {ka_rankine:.6f}")
                st.write(f"• Muro vertical liso")
                st.write(f"• Aproximación conservadora")
            
            with col3:
                st.info("**Diferencia:**")
                diferencia = ((ka_rankine - resultados_coulomb['Ka']) / ka_rankine) * 100
                st.write(f"• Diferencia: {diferencia:.1f}%")
                if diferencia > 0:
                    st.success("Coulomb es menos conservador")
                else:
                    st.warning("Coulomb es más conservador")
            
            # Gráfico comparativo
            st.subheader("📈 Gráfico Comparativo")
            
            datos_comparacion = pd.DataFrame({
                'Teoría': ['Coulomb', 'Rankine'],
                'Coeficiente Ka': [resultados_coulomb['Ka'], ka_rankine],
                'Empuje Horizontal (t/m)': [resultados_coulomb['Ph'], resultados_coulomb['Pa'] * math.cos(math.radians(90 - resultados_coulomb['beta'] + delta))]
            })
            
            if PLOTLY_AVAILABLE:
                fig = px.bar(datos_comparacion, x='Teoría', y='Coeficiente Ka',
                            title="Comparación de Coeficientes Ka: Coulomb vs Rankine",
                            color='Teoría',
                            color_discrete_map={'Coulomb': '#FF6B6B', 'Rankine': '#4ECDC4'})
                
                fig.update_layout(
                    xaxis_title="Teoría",
                    yaxis_title="Coeficiente Ka",
                    height=400
                )
                
                fig.update_traces(texttemplate='%{y:.6f}', textposition='outside')
                st.plotly_chart(fig, use_container_width=True)
            
            # Información técnica adicional
            st.subheader("📚 Información Técnica")
            
            with st.expander("🔍 DETALLES DEL CÁLCULO", expanded=False):
                st.markdown(f"""
                **Cálculo del ángulo β:**
                ```
                β = arctan((H - h1) / t2) = arctan(({H} - {h1}) / {t2}) = {resultados_coulomb['beta']:.2f}°
                ```
                
                **Cálculo del coeficiente Ka (Coulomb):**
                ```
                Ka = sin²(β + φ₁') / [sin²(β) · sin(β - δ) · (1 + √(sin(φ₁' + δ) · sin(φ₁' - α) / sin(β - δ) · sin(β + α)))²]
                Ka = {resultados_coulomb['Ka']:.6f}
                ```
                
                **Cálculo de la altura efectiva:**
                ```
                H' = H + (t₂/2 + b₂/2) · tan(α) = {H} + ({t2/2:.2f} + {b2/2:.2f}) · tan({alpha}°) = {resultados_coulomb['H_efectiva']:.2f} m
                ```
                
                **Cálculo del empuje activo total:**
                ```
                Pa = ½ · Ka · γ₁ · (H')² = 0.5 · {resultados_coulomb['Ka']:.6f} · {gamma1} · ({resultados_coulomb['H_efectiva']:.2f})² = {resultados_coulomb['Pa']:.3f} t/m
                ```
                
                **Componentes del empuje:**
                ```
                Ph = Pa · cos(90° - β + δ) = {resultados_coulomb['Pa']:.3f} · cos(90° - {resultados_coulomb['beta']:.2f}° + {delta}°) = {resultados_coulomb['Ph']:.3f} t/m
                Pv = Pa · sin(90° - β + δ) = {resultados_coulomb['Pa']:.3f} · sin(90° - {resultados_coulomb['beta']:.2f}° + {delta}°) = {resultados_coulomb['Pv']:.3f} t/m
                ```
                
                **Empuje por sobrecarga:**
                ```
                PSC = Ka · H · (S/c / 1000) · (sin(β) / sin(β + α)) = {resultados_coulomb['Ka']:.6f} · {H} · ({S_c}/1000) · (sin({resultados_coulomb['beta']:.2f}°) / sin({resultados_coulomb['beta']:.2f}° + {alpha}°)) = {resultados_coulomb['PSC']:.3f} t/m
                ```
                """)
            
            # Gráficos adicionales para Coulomb
            st.subheader("📈 Gráficos Adicionales - Análisis Coulomb")
            # Gráfico de componentes del empuje
            col1, col2 = st.columns(2)
            with col1:
                datos_componentes = pd.DataFrame({
                    'Componente': ['Empuje Total (Pa)', 'Componente Horizontal (Ph)', 'Componente Vertical (Pv)', 'Empuje Sobrecarga (PSC)'],
                    'Valor (t/m)': [resultados_coulomb['Pa'], resultados_coulomb['Ph'], resultados_coulomb['Pv'], resultados_coulomb['PSC']],
                    'γ₁ (t/m³)': [gamma1]*4,
                    "φ'₁ (°)": [phi1]*4,
                    "c'₁ (kg/cm²)": [cohesion1]*4,
                    "α (°)": [alpha]*4,
                    'γ₂ (t/m³)': [gamma2]*4,
                    "c'₂ (kg/cm²)": [cohesion2]*4,
                    'σᵤ (kg/cm²)': [sigma_u]*4,
                    "φ'₂ (°)": [phi2]*4,
                    'γ_muro (t/m³)': [gamma_muro]*4,
                    'S/c (kg/m²)': [S_c]*4,
                    'H (m)': [H]*4,
                    'D (m)': [D]*4,
                    'h1 (m)': [h1]*4,
                    't2 (m)': [t2]*4,
                    'b2 (m)': [b2]*4,
                    'δ (°)': [delta]*4
                })
                if PLOTLY_AVAILABLE:
                    fig_comp = px.bar(
                        datos_componentes, x='Componente', y='Valor (t/m)',
                        title="Componentes del Empuje Activo - Coulomb",
                        color='Componente',
                        color_discrete_map={
                            'Empuje Total (Pa)': '#FF6B6B',
                            'Componente Horizontal (Ph)': '#4ECDC4',
                            'Componente Vertical (Pv)': '#45B7D1',
                            'Empuje Sobrecarga (PSC)': '#96CEB4'
                        },
                        custom_data=[
                            'γ₁ (t/m³)', "φ'₁ (°)", "c'₁ (kg/cm²)", "α (°)",
                            'γ₂ (t/m³)', "c'₂ (kg/cm²)", 'σᵤ (kg/cm²)', "φ'₂ (°)",
                            'γ_muro (t/m³)', 'S/c (kg/m²)', 'H (m)', 'D (m)', 'h1 (m)', 't2 (m)', 'b2 (m)', 'δ (°)'
                        ]
                    )
                    fig_comp.update_traces(
                        texttemplate='%{y:.3f}', textposition='outside',
                        hovertemplate="<b>%{x}</b><br>Valor: %{y:.3f} t/m" +
                        "<br>γ₁: %{customdata[0]} t/m³" +
                        "<br>φ'₁: %{customdata[1]}°" +
                        "<br>c'₁: %{customdata[2]} kg/cm²" +
                        "<br>α: %{customdata[3]}°" +
                        "<br>γ₂: %{customdata[4]} t/m³" +
                        "<br>c'₂: %{customdata[5]} kg/cm²" +
                        "<br>σᵤ: %{customdata[6]} kg/cm²" +
                        "<br>φ'₂: %{customdata[7]}°" +
                        "<br>γ_muro: %{customdata[8]} t/m³" +
                        "<br>S/c: %{customdata[9]} kg/m²" +
                        "<br>H: %{customdata[10]} m" +
                        "<br>D: %{customdata[11]} m" +
                        "<br>h1: %{customdata[12]} m" +
                        "<br>t2: %{customdata[13]} m" +
                        "<br>b2: %{customdata[14]} m" +
                        "<br>δ: %{customdata[15]}°<extra></extra>"
                    )
                    st.plotly_chart(fig_comp, use_container_width=True)
                # Leyenda textual de parámetros
                st.markdown(f"""
                **Parámetros de Entrada:**
                - γ₁ (relleno): {gamma1} t/m³, φ'₁: {phi1}°, c'₁: {cohesion1} kg/cm², α: {alpha}°
                - γ₂ (base): {gamma2} t/m³, φ'₂: {phi2}°, c'₂: {cohesion2} kg/cm², σᵤ: {sigma_u} kg/cm²
                - γ_muro: {gamma_muro} t/m³, S/c: {S_c} kg/m², H: {H} m, D: {D} m, h1: {h1} m, t2: {t2} m, b2: {b2} m, δ: {delta}°
                """)
            with col2:
                # Gráfico de parámetros geométricos
                datos_geometricos = pd.DataFrame({
                    'Parámetro': ['Altura Total (H)', 'Altura Efectiva (H\')', 'Ángulo β', 'Ángulo α', 'Ángulo δ'],
                    'Valor': [H, resultados_coulomb['H_efectiva'], resultados_coulomb['beta'], alpha, delta],
                    'Unidad': ['m', 'm', '°', '°', '°'],
                    'γ₁ (t/m³)': [gamma1]*5,
                    "φ'₁ (°)": [phi1]*5,
                    "c'₁ (kg/cm²)": [cohesion1]*5,
                    "α (°)": [alpha]*5,
                    'γ₂ (t/m³)': [gamma2]*5,
                    "c'₂ (kg/cm²)": [cohesion2]*5,
                    'σᵤ (kg/cm²)': [sigma_u]*5,
                    "φ'₂ (°)": [phi2]*5,
                    'γ_muro (t/m³)': [gamma_muro]*5,
                    'S/c (kg/m²)': [S_c]*5,
                    'D (m)': [D]*5,
                    'h1 (m)': [h1]*5,
                    't2 (m)': [t2]*5,
                    'b2 (m)': [b2]*5
                })
                if PLOTLY_AVAILABLE:
                    fig_geo = px.bar(
                        datos_geometricos, x='Parámetro', y='Valor',
                        title="Parámetros Geométricos - Coulomb",
                        color='Parámetro',
                        color_discrete_map={
                            'Altura Total (H)': '#FFD93D',
                            'Altura Efectiva (H\')': '#6BCF7F',
                            'Ángulo β': '#4D96FF',
                            'Ángulo α': '#FF6B6B',
                            'Ángulo δ': '#9B59B6'
                        },
                        custom_data=[
                            'Unidad', 'γ₁ (t/m³)', "φ'₁ (°)", "c'₁ (kg/cm²)", "α (°)",
                            'γ₂ (t/m³)', "c'₂ (kg/cm²)", 'σᵤ (kg/cm²)', "φ'₂ (°)",
                            'γ_muro (t/m³)', 'S/c (kg/m²)', 'D (m)', 'h1 (m)', 't2 (m)', 'b2 (m)'
                        ]
                    )
                    fig_geo.update_traces(
                        texttemplate='%{y:.2f}', textposition='outside',
                        hovertemplate="<b>%{x}</b><br>Valor: %{y:.2f} %{customdata[0]}" +
                        "<br>γ₁: %{customdata[1]} t/m³" +
                        "<br>φ'₁: %{customdata[2]}°" +
                        "<br>c'₁: %{customdata[3]} kg/cm²" +
                        "<br>α: %{customdata[4]}°" +
                        "<br>γ₂: %{customdata[5]} t/m³" +
                        "<br>c'₂: %{customdata[6]} kg/cm²" +
                        "<br>σᵤ: %{customdata[7]} kg/cm²" +
                        "<br>φ'₂: %{customdata[8]}°" +
                        "<br>γ_muro: %{customdata[9]} t/m³" +
                        "<br>S/c: %{customdata[10]} kg/m²" +
                        "<br>D: %{customdata[11]} m" +
                        "<br>h1: %{customdata[12]} m" +
                        "<br>t2: %{customdata[13]} m" +
                        "<br>b2: %{customdata[14]} m<extra></extra>"
                    )
                    st.plotly_chart(fig_geo, use_container_width=True)
                st.markdown(f"""
                **Parámetros de Entrada Geométricos:**
                - H: {H} m, H': {resultados_coulomb['H_efectiva']:.2f} m, β: {resultados_coulomb['beta']:.2f}°, α: {alpha}°, δ: {delta}°
                """)
            # Gráfico del muro de contención para Coulomb
            st.subheader("🏗️ Visualización del Muro de Contención - Coulomb")
            st.info("Representación gráfica del muro con análisis Coulomb")
            
            # Crear dimensiones para el gráfico (usando valores típicos para Coulomb)
            dimensiones_coulomb = {
                'Bz': t2 + b2 + 0.5,  # Base total estimada
                'hz': 0.4,  # Peralte de zapata típico
                'b': 0.3,   # Espesor del muro
                'r': t2,    # Longitud de puntera
                't': b2,    # Longitud de talón
                'hm': 0.2   # Altura de coronación
            }
            
            # Generar el gráfico del muro para Coulomb
            datos_coulomb_grafico = {
                'beta': resultados_coulomb['beta'],
                'alpha': alpha,
                'delta': delta,
                'Ka': resultados_coulomb['Ka'],
                'H_efectiva': resultados_coulomb['H_efectiva']
            }
            fig_muro_coulomb = dibujar_muro_streamlit(dimensiones_coulomb, h1, 0.5, S_c, "coulomb", datos_coulomb_grafico)
            
            # Mostrar el gráfico en Streamlit
            st.pyplot(fig_muro_coulomb)
            
            # Información adicional sobre el gráfico
            st.markdown("""
            **Leyenda del Gráfico - Análisis Coulomb:**
            - 🔵 **Zapata (Azul claro):** Base de cimentación del muro
            - 🔴 **Muro (Rosa):** Estructura principal de contención (inclinada según β)
            - 🟡 **Relleno (Amarillo):** Material de relleno detrás del muro
            - 🟤 **Suelo (Marrón):** Suelo de cimentación
            - 🔴 **Flechas rojas:** Sobrecarga aplicada (S/c)
            - 🔵 **Dimensiones en azul:** Medidas calculadas del muro
            - 📐 **Ángulo β:** Inclinación del muro respecto a la vertical
            - 📐 **Ángulo α:** Inclinación del terreno natural
            - 📐 **Ángulo δ:** Fricción entre muro y relleno
            """)
            
            # Botones para generar reportes
            st.subheader("📄 Generar Reportes - Análisis Coulomb")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                # Generar reporte de texto
                reporte_coulomb = f"""
# REPORTE TÉCNICO - ANÁLISIS COULOMB
## CONSORCIO DEJ
### Análisis según Teoría de Coulomb
### Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}

### 1. DATOS DE ENTRADA:
- Altura total del muro (H): {H:.2f} m
- Peralte de Zapata (h1): {h1:.2f} m
- Base del triángulo 2 (t2): {t2:.2f} m
- Longitud del talón (b2): {b2:.2f} m
- Ángulo de fricción del suelo (φ₁'): {phi1:.1f}°
- Ángulo de fricción muro-suelo (δ): {delta:.1f}°
- Ángulo de inclinación del terreno (α): {alpha:.1f}°
- Peso específico del suelo (γ₁): {gamma1:.2f} t/m³
- Sobrecarga (S/c): {S_c} kg/m²

### 2. CÁLCULOS GEOMÉTRICOS:
- Ángulo de inclinación del muro (β): {resultados_coulomb['beta']:.2f}°
- Altura efectiva del muro (H'): {resultados_coulomb['H_efectiva']:.2f} m

### 3. COEFICIENTE DE EMPUJE ACTIVO:
- Coeficiente Ka (Coulomb): {resultados_coulomb['Ka']:.6f}

### 4. ANÁLISIS DE EMPUJES:
- Empuje activo total (Pa): {resultados_coulomb['Pa']:.3f} t/m
- Componente horizontal (Ph): {resultados_coulomb['Ph']:.3f} t/m
- Componente vertical (Pv): {resultados_coulomb['Pv']:.3f} t/m
- Empuje por sobrecarga (PSC): {resultados_coulomb['PSC']:.3f} t/m
- Empuje total horizontal: {resultados_coulomb['P_total_horizontal']:.3f} t/m

### 5. COMPARACIÓN CON RANKINE:
- Coeficiente Ka (Rankine): {ka_rankine:.6f}
- Diferencia porcentual: {diferencia:.1f}%
- {'Coulomb es menos conservador' if diferencia > 0 else 'Coulomb es más conservador'}

### 6. OBSERVACIONES TÉCNICAS:
- La teoría de Coulomb considera la fricción entre el muro y el suelo
- El ángulo de fricción muro-suelo (δ) afecta significativamente el empuje
- Para muros rugosos, Coulomb proporciona resultados más realistas
- La inclinación del terreno (α) modifica la altura efectiva del muro

### 7. RECOMENDACIONES:
- Verificar la rugosidad del muro para determinar δ apropiado
- Considerar efectos de drenaje en el relleno
- Revisar la estabilidad al volcamiento y deslizamiento
- Evaluar la capacidad portante del suelo de cimentación

### 8. INFORMACIÓN DEL PROYECTO:
- Empresa: CONSORCIO DEJ
- Método de análisis: Teoría de Coulomb
- Fecha de análisis: {datetime.now().strftime('%d/%m/%Y %H:%M')}
- Plan: Premium
- Software: Streamlit + Python

---
**Este reporte fue generado automáticamente por el sistema de análisis de muros de contención de CONSORCIO DEJ.**
**Para consultas técnicas, contacte a nuestro equipo de ingeniería.**
"""
                
                st.download_button(
                    label="📥 Descargar TXT Coulomb",
                    data=reporte_coulomb,
                    file_name=f"reporte_coulomb_muro_contencion_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                    mime="text/plain"
                )
            
            with col2:
                # Generar PDF para Coulomb
                try:
                    # Verificar si hay resultados de Coulomb disponibles
                    if 'resultados_coulomb' in st.session_state and 'datos_entrada_coulomb' in st.session_state:
                        resultados_coulomb_pdf = st.session_state['resultados_coulomb']
                        datos_entrada_coulomb = st.session_state['datos_entrada_coulomb']
                    else:
                        st.error("⚠️ No hay resultados de análisis Coulomb disponibles.")
                        st.info("Ejecuta primero el análisis completo de Coulomb.")
                        st.stop()
                    
                    # Verificar si hay resultados de Rankine disponibles
                    resultados_rankine_pdf = None
                    datos_entrada_rankine_pdf = None
                    if 'resultados_rankine' in st.session_state and 'datos_entrada_rankine' in st.session_state:
                        resultados_rankine_pdf = st.session_state['resultados_rankine']
                        datos_entrada_rankine_pdf = st.session_state['datos_entrada_rankine']
                    
                    pdf_buffer_coulomb = generar_pdf_reportlab(
                        resultados_coulomb_pdf, 
                        datos_entrada_coulomb, 
                        {}, 
                        "premium",
                        resultados_rankine_pdf,
                        datos_entrada_rankine_pdf
                    )
                    
                    st.download_button(
                        label="📄 Descargar PDF Coulomb",
                        data=pdf_buffer_coulomb.getvalue(),
                        file_name=f"reporte_coulomb_muro_contencion_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                        mime="application/pdf"
                    )
                except Exception as e:
                    st.error(f"⚠️ Error generando PDF: {str(e)}")
                    st.info("Intenta ejecutar el análisis completo nuevamente")
            
            with col3:
                if st.button("🖨️ Generar Reporte en Pantalla", type="primary", key="coulomb_pantalla"):
                    st.success("✅ Reporte Coulomb generado exitosamente")
                    st.balloons()
                    
                    # Mostrar el reporte en formato expandible
                    with st.expander("📋 VER REPORTE COULOMB COMPLETO", expanded=True):
                        st.markdown(reporte_coulomb)

        # Botón para análisis de muro con contrafuertes
        if st.button("🏗️ MURO CONTRAFUERTE", type="primary"):
            st.success("🚀 Iniciando análisis de muro con contrafuertes...")
            
            # Datos de entrada para contrafuertes (usando valores de la sección actual)
            gamma_concreto = 2.4  # Peso específico del concreto (t/m³)
            datos_contrafuertes = {
                'H': H,  # Altura total del muro
                'h1': h1,  # Peralte de zapata
                'gamma1': gamma1,  # Peso específico del suelo
                'phi1': phi1,  # Ángulo de fricción del suelo
                'S_c': S_c,  # Sobrecarga
                'fc': 210,  # Resistencia del concreto (kg/cm²)
                'fy': 4200,  # Resistencia del acero (kg/cm²)
                'gamma_concreto': gamma_concreto  # Peso específico del concreto (t/m³)
            }
            
            # Cálculos según las fórmulas proporcionadas
            H_contrafuertes = datos_contrafuertes['H']
            gamma1_contrafuertes = datos_contrafuertes['gamma1']
            phi1_contrafuertes = datos_contrafuertes['phi1']
            S_c_contrafuertes = datos_contrafuertes['S_c']
            
            # 1. Espesor mínimo del talón y puntera (Ortega)
            d_min = H_contrafuertes / 10
            h1_contrafuertes = max(0.4, d_min)  # Usar h1 = 0.4m (cumple)
            
            # 2. Separación de contrafuertes (ACI-UNI)
            S_max = 3 * H_contrafuertes
            S_tipico = min(4.0, S_max)  # Típico: 2.5 a 4m
            
            # 3. Coeficiente de empuje activo (Rankine simplificado)
            ka_contrafuertes = math.tan(math.radians(45 - phi1_contrafuertes/2))**2
            
            # 4. Presión activa total
            Pa_suelo = 0.5 * gamma1_contrafuertes * (H_contrafuertes**2) * ka_contrafuertes
            # S_c está en kg/m², convertir a tn/m² dividiendo por 1000
            Pa_sobrecarga = (S_c_contrafuertes / 1000) * H_contrafuertes * ka_contrafuertes
            Pa_total = Pa_suelo + Pa_sobrecarga
            
            # 5. Momento máximo en la base del contrafuerte (UNI)
            M_max = Pa_total * S_tipico * H_contrafuertes / 6
            
            # 6. Diseño de armadura
            # Acero vertical mínimo (ACI 318)
            As_min_vertical = 0.0018 * 100 * 40  # b=100cm, d=40cm
            
            # Acero horizontal mínimo (Morales)
            As_min_horizontal = 0.0025 * 100 * h1_contrafuertes * 100  # b=100cm, h en cm
            
            # Espesor mínimo de contrafuertes
            t_contrafuertes = max(0.20, H_contrafuertes / 20)
            
            # Armadura principal del contrafuerte
            d_contrafuertes = h1_contrafuertes * 100 - 9  # Peralte efectivo en cm
            As_contrafuertes = M_max * 100000 / (0.9 * 4200 * d_contrafuertes)
            
            # 7. Verificación de estabilidad (como Rankine)
            # Empuje pasivo
            phi_cimentacion_rad = math.radians(phi2)
            kp = math.tan(math.radians(45 + phi2/2))**2
            Ep = 0.5 * kp * (gamma2/1000) * D**2
            
            # Pesos de cada elemento
            W_muro = 0.3 * h1_contrafuertes * (gamma_concreto/1000)  # Corona superior
            W_zapata = 1.6 * h1_contrafuertes * (gamma_concreto/1000)  # Cimiento
            W_relleno = 1.3 * h1_contrafuertes * (gamma1_contrafuertes/1000)  # Relleno
            W_contrafuertes = t_contrafuertes * S_tipico * h1_contrafuertes * (gamma_concreto/1000)  # Contrafuertes
            
            # Peso total
            W_total = W_muro + W_zapata + W_relleno + W_contrafuertes
            
            # Momentos estabilizadores
            Mr_muro = W_muro * 0.8  # Brazo de momento
            Mr_zapata = W_zapata * 0.8
            Mr_relleno = W_relleno * 1.45
            Mr_pasivo = Ep * D/3
            M_estabilizador = Mr_muro + Mr_zapata + Mr_relleno + Mr_pasivo
            
            # Momentos volcadores
            Mv_relleno = Pa_suelo * h1_contrafuertes/3
            Mv_sobrecarga = Pa_sobrecarga * h1_contrafuertes/2
            M_volcador = Mv_relleno + Mv_sobrecarga
            
            # Factor de seguridad al volcamiento
            FS_volcamiento = M_estabilizador / M_volcador if M_volcador > 0 else 0
            
            # Verificación al deslizamiento
            mu = math.tan(phi_cimentacion_rad)
            Fr_friccion = mu * W_total
            Fr_pasivo = Ep
            Fr_total = Fr_friccion + Fr_pasivo
            Fd_total = Pa_total
            FS_deslizamiento = Fr_total / Fd_total if Fd_total > 0 else 0
            
            # Verificación de presiones sobre el suelo
            sum_momentos_verticales = Mr_muro + Mr_zapata + Mr_relleno
            x_barra = sum_momentos_verticales / W_total if W_total > 0 else 0
            e = abs(x_barra - 0.8)  # Excentricidad
            q_max = (W_total / 1.6) * (1 + 6*e/1.6) if W_total > 0 else 0
            q_min = (W_total / 1.6) * (1 - 6*e/1.6) if W_total > 0 else 0
            q_max_kg_cm2 = q_max * 0.1
            q_min_kg_cm2 = q_min * 0.1
            
            # Guardar resultados
            resultados_contrafuertes = {
                'H': H_contrafuertes,
                'h1': h1_contrafuertes,
                'd_min': d_min,
                'S_max': S_max,
                'S_tipico': S_tipico,
                'ka': ka_contrafuertes,
                'Pa_suelo': Pa_suelo,
                'Pa_sobrecarga': Pa_sobrecarga,
                'Pa_total': Pa_total,
                'M_max': M_max,
                'As_min_vertical': As_min_vertical,
                'As_min_horizontal': As_min_horizontal,
                't_contrafuertes': t_contrafuertes,
                'As_contrafuertes': As_contrafuertes,
                'd_contrafuertes': d_contrafuertes,
                'kp': kp,
                'Ep': Ep,
                'W_total': W_total,
                'M_volcador': M_volcador,
                'M_estabilizador': M_estabilizador,
                'FS_volcamiento': FS_volcamiento,
                'FS_deslizamiento': FS_deslizamiento,
                'q_max_kg_cm2': q_max_kg_cm2,
                'q_min_kg_cm2': q_min_kg_cm2,
                'e': e
            }
            
            st.session_state['resultados_contrafuertes'] = resultados_contrafuertes
            st.session_state['datos_contrafuertes'] = datos_contrafuertes
            
            st.success("✅ Análisis de muro con contrafuertes completado exitosamente!")
            st.balloons()
            
            # MOSTRAR RESULTADOS COMPLETOS (como Rankine)
            st.subheader("📊 Resultados del Análisis - Muro con Contrafuertes")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("Altura del muro (H)", f"{H_contrafuertes:.2f} m")
                st.metric("Peralte de zapata (h1)", f"{h1_contrafuertes:.2f} m")
                st.metric("Coeficiente Ka (Rankine)", f"{ka_contrafuertes:.6f}")
                st.metric("Empuje activo total (Pa)", f"{Pa_total:.3f} t/m")
                st.metric("Momento máximo contrafuerte", f"{M_max:.2f} tn·m")
            
            with col2:
                st.metric("Factor Seguridad Volcamiento", f"{FS_volcamiento:.2f}")
                st.metric("Factor Seguridad Deslizamiento", f"{FS_deslizamiento:.2f}")
                st.metric("Presión máxima suelo", f"{q_max_kg_cm2:.2f} kg/cm²")
                st.metric("Presión mínima suelo", f"{q_min_kg_cm2:.2f} kg/cm²")
                st.metric("Excentricidad (e)", f"{e:.3f} m")
            
            # Diseño estructural
            st.subheader("🏗️ Diseño Estructural - Contrafuertes")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.info("**Contrafuertes:**")
                st.write(f"• Espesor mínimo: {t_contrafuertes:.2f} m")
                st.write(f"• Separación: {S_tipico:.2f} m")
                st.write(f"• Armadura principal: {As_contrafuertes:.2f} cm²")
                st.write(f"• Peralte efectivo: {d_contrafuertes:.2f} cm")
            
            with col2:
                st.info("**Muro Pantalla:**")
                st.write(f"• Acero vertical: {As_min_vertical:.2f} cm²/m")
                st.write(f"• Acero horizontal: {As_min_horizontal:.2f} cm²/m")
                st.write(f"• Espesor: {h1_contrafuertes:.2f} m")
                st.write(f"• Tipo: Muro pantalla con contrafuertes")
            
            with col3:
                st.info("**Estabilidad:**")
                st.write(f"• FS Volcamiento: {FS_volcamiento:.2f}")
                st.write(f"• FS Deslizamiento: {FS_deslizamiento:.2f}")
                st.write(f"• Peso total: {W_total:.2f} t/m")
                st.write(f"• Empuje pasivo: {Ep:.2f} t/m")
            
            # Gráficos (como Rankine)
            st.subheader("📈 Gráficos - Análisis Contrafuertes")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Gráfico de componentes del empuje
                datos_empuje = pd.DataFrame({
                    'Componente': ['Empuje Suelo', 'Empuje Sobrecarga', 'Empuje Total'],
                    'Valor (t/m)': [Pa_suelo, Pa_sobrecarga, Pa_total]
                })
                
                if PLOTLY_AVAILABLE:
                    fig_empuje = px.bar(datos_empuje, x='Componente', y='Valor (t/m)',
                                       title="Componentes del Empuje - Contrafuertes",
                                       color='Componente',
                                       color_discrete_map={
                                           'Empuje Suelo': '#FF6B6B',
                                           'Empuje Sobrecarga': '#4ECDC4',
                                           'Empuje Total': '#45B7D1'
                                       })
                    
                    fig_empuje.update_traces(texttemplate='%{y:.3f}', textposition='outside')
                    st.plotly_chart(fig_empuje, use_container_width=True)
            
            with col2:
                # Gráfico de factores de seguridad
                datos_fs = pd.DataFrame({
                    'Verificación': ['Volcamiento', 'Deslizamiento'],
                    'Factor de Seguridad': [FS_volcamiento, FS_deslizamiento],
                    'Límite': [2.0, 1.5]
                })
                
                if PLOTLY_AVAILABLE:
                    fig_fs = px.bar(datos_fs, x='Verificación', y='Factor de Seguridad',
                                   title="Factores de Seguridad - Contrafuertes",
                                   color='Verificación',
                                   color_discrete_map={
                                       'Volcamiento': '#FFD93D',
                                       'Deslizamiento': '#6BCF7F'
                                   })
                    
                    # Agregar línea de límite
                    fig_fs.add_hline(y=2.0, line_dash="dash", line_color="red", annotation_text="Límite FS=2.0")
                    fig_fs.add_hline(y=1.5, line_dash="dash", line_color="orange", annotation_text="Límite FS=1.5")
                    
                    fig_fs.update_traces(texttemplate='%{y:.2f}', textposition='outside')
                    st.plotly_chart(fig_fs, use_container_width=True)
            
            # Gráfico profesional del muro con contrafuertes
            st.subheader("📐 Visualización del Muro con Contrafuertes")
            
            dimensiones_contrafuertes = {
                'h1': h1_contrafuertes,
                'S_tipico': S_tipico,
                't_contrafuertes': t_contrafuertes
            }
            
            fig_contrafuertes = dibujar_muro_contrafuertes(
                dimensiones_contrafuertes,
                resultados_contrafuertes,
                datos_contrafuertes
            )
            
            st.pyplot(fig_contrafuertes)
            
            # Explicación del gráfico
            st.markdown("""
            **Leyenda del Gráfico - Muro con Contrafuertes:**
            
            - 🏗️ **Muro Pantalla (Gris claro):** Estructura principal de hormigón armado
            - 🏋️ **Contrafuertes (Gris oscuro):** Elementos estructurales que rigidizan el muro
            - 🏜️ **Relleno (Amarillo):** Material granular compactado detrás del muro
            - 🌱 **Suelo (Marrón):** Terreno natural de cimentación
            - 🔩 **Líneas grises oscuras:** Armadura de acero (representación esquemática)
            - 🔴 **Flechas rojas:** Sobrecarga aplicada sobre el terreno
            - 🔵 **Dimensiones en azul:** Medidas principales del diseño
            
            **Detalles Constructivos:**
            - Separación típica entre contrafuertes: 2.5-4.0 m
            - Espesor mínimo de contrafuertes: 20-30 cm
            - Armadura principal calculada para resistir momentos flectores
            - Juntas de construcción cada 10-15 m
            """)
            
            # Información técnica
            st.subheader("📚 Información Técnica - Contrafuertes")
            
            with st.expander("🔍 DETALLES DEL CÁLCULO", expanded=False):
                st.markdown(f"""
                **1. Espesor mínimo del talón y puntera (Ortega):**
                ```
                d ≥ H/10 = {H_contrafuertes}/10 = {d_min:.2f} m
                h1 = {h1_contrafuertes:.2f} m (cumple)
                ```
                
                **2. Separación de contrafuertes (ACI-UNI):**
                ```
                S ≤ 3·H = 3·{H_contrafuertes} = {S_max:.2f} m
                S típico = {S_tipico:.2f} m (recomendado)
                ```
                
                **3. Coeficiente de empuje activo (Rankine):**
                ```
                Ka = tan²(45° - φ₁'/2) = tan²(45° - {phi1_contrafuertes}/2) = {ka_contrafuertes:.6f}
                ```
                
                **4. Presión activa total:**
                ```
                Pa = ½·γ₁·H²·Ka + S/c·H·Ka
                Pa = 0.5·{gamma1_contrafuertes}·{H_contrafuertes}²·{ka_contrafuertes:.6f} + ({S_c_contrafuertes}/1000)·{H_contrafuertes}·{ka_contrafuertes:.6f}
                Pa = {Pa_suelo:.3f} + {Pa_sobrecarga:.3f} = {Pa_total:.3f} t/m
                ```
                
                **5. Momento máximo en contrafuerte (UNI):**
                ```
                M_max = Pa·S·H/6 = {Pa_total:.3f}·{S_tipico:.2f}·{H_contrafuertes}/6 = {M_max:.2f} tn·m
                ```
                
                **6. Acero vertical mínimo (ACI 318):**
                ```
                As_min = 0.0018·b·d = 0.0018·100·40 = {As_min_vertical:.2f} cm²/m
                ```
                
                **7. Acero horizontal mínimo (Morales):**
                ```
                As_hor = 0.0025·b·h = 0.0025·100·{h1_contrafuertes*100:.0f} = {As_min_horizontal:.2f} cm²/m
                ```
                
                **8. Armadura principal del contrafuerte:**
                ```
                As = M_max/(0.9·fy·d) = {M_max*100000:.0f}/(0.9·4200·{d_contrafuertes:.0f}) = {As_contrafuertes:.2f} cm²
                ```
                
                **9. Verificación de estabilidad:**
                ```
                FS Volcamiento = M_estabilizador/M_volcador = {M_estabilizador:.2f}/{M_volcador:.2f} = {FS_volcamiento:.2f}
                FS Deslizamiento = Fr_total/Fd_total = {Fr_total:.2f}/{Fd_total:.2f} = {FS_deslizamiento:.2f}
                ```
                """)
            
            # Recomendaciones constructivas
            st.subheader("🏗️ Recomendaciones Constructivas")
            
            st.info("""
            **Partes Clave y Notas Técnicas:**
            
            **Muro Pantalla:**
            - Espesor (h1): {h1_contrafuertes:.2f} m
            - Refuerzo: Acero vertical y horizontal (mín. 0.0018·b·d)
            
            **Contrafuertes:**
            - Separación (S): {S_tipico:.2f} m (≤ 3H = {S_max:.2f} m)
            - Función: Resistir momentos y cortantes del suelo
            - Espesor mínimo: {t_contrafuertes:.2f} m
            
            **Corona Superior:**
            - Ancho (b): 0.3 m (protegida contra intemperie)
            
            **Cimiento:**
            - Ancho (B): 1.6 m (verificado por capacidad portante)
            
            **Drenaje:**
            - Tubos perforados detrás del muro (Ø4")
            
            **Detalles Constructivos Adicionales:**
            - Juntas de expansión cada 10 m (Ortega García)
            - Acero mínimo en muro: 0.0025·b·h (Roberto Morales)
            - Anclaje de contrafuertes con barras Ø1"
            """.format(h1_contrafuertes=h1_contrafuertes, S_tipico=S_tipico, S_max=S_max, t_contrafuertes=t_contrafuertes))
            
            # Botones para generar reportes (como Rankine)
            st.subheader("📄 Generar Reportes - Contrafuertes")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                # Generar reporte de texto
                reporte_contrafuertes = f"""
# REPORTE TÉCNICO - MURO CON CONTRAFUERTES
## CONSORCIO DEJ
### Análisis según Ortega García, UNI y Morales
### Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}

### 1. DATOS DE ENTRADA:
- Altura del muro (H): {H_contrafuertes:.2f} m
- Peralte de zapata (h1): {h1_contrafuertes:.2f} m
- Peso específico del suelo (γ₁): {gamma1_contrafuertes:.2f} t/m³
- Ángulo de fricción del suelo (φ₁'): {phi1_contrafuertes:.1f}°
- Sobrecarga (S/c): {S_c_contrafuertes} kg/m²

### 2. DIMENSIONES CALCULADAS:
- Espesor mínimo requerido: {d_min:.2f} m
- Separación máxima contrafuertes: {S_max:.2f} m
- Separación típica recomendada: {S_tipico:.2f} m
- Espesor de contrafuertes: {t_contrafuertes:.2f} m

### 3. ANÁLISIS DE EMPUJES:
- Coeficiente Ka (Rankine): {ka_contrafuertes:.6f}
- Empuje por suelo: {Pa_suelo:.3f} t/m
- Empuje por sobrecarga: {Pa_sobrecarga:.3f} t/m
- Empuje activo total: {Pa_total:.3f} t/m

### 4. DISEÑO ESTRUCTURAL:
- Momento máximo en contrafuerte: {M_max:.2f} tn·m
- Acero vertical mínimo: {As_min_vertical:.2f} cm²/m
- Acero horizontal mínimo: {As_min_horizontal:.2f} cm²/m
- Armadura principal contrafuerte: {As_contrafuertes:.2f} cm²

### 5. VERIFICACIÓN DE ESTABILIDAD:
- Factor de seguridad al volcamiento: {FS_volcamiento:.2f}
- Factor de seguridad al deslizamiento: {FS_deslizamiento:.2f}
- Presión máxima sobre el suelo: {q_max_kg_cm2:.2f} kg/cm²
- Presión mínima sobre el suelo: {q_min_kg_cm2:.2f} kg/cm²
- Excentricidad: {e:.3f} m

### 6. DETALLES CONSTRUCTIVOS:
- Juntas de expansión: cada 10 m (Ortega)
- Drenaje: tuberías perforadas Ø4"
- Anclaje contrafuertes: barras Ø1"
- Referencias: Ortega García, UNI, Morales (ACI-UNI)

### 7. RECOMENDACIONES:
- Verificar capacidad portante del suelo
- Considerar efectos de drenaje
- Revisar estabilidad al volcamiento
- Evaluar armadura por retracción y temperatura

### 8. INFORMACIÓN DEL PROYECTO:
- Empresa: CONSORCIO DEJ
- Método: Muro con contrafuertes
- Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}
- Plan: Premium
- Software: Streamlit + Python

---
**Este reporte fue generado automáticamente por el sistema de análisis de muros de contención de CONSORCIO DEJ.**
**Para consultas técnicas, contacte a nuestro equipo de ingeniería.**
"""
                
                st.download_button(
                    label="📥 Descargar TXT Contrafuertes",
                    data=reporte_contrafuertes,
                    file_name=f"reporte_contrafuertes_muro_contencion_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                    mime="text/plain"
                )
            
            with col2:
                # Generar PDF para contrafuertes
                try:
                    # Verificar si hay resultados de contrafuertes disponibles
                    if 'resultados_contrafuertes' in st.session_state and 'datos_contrafuertes' in st.session_state:
                        resultados_contrafuertes_pdf = st.session_state['resultados_contrafuertes']
                        datos_entrada_contrafuertes = st.session_state['datos_contrafuertes']
                    else:
                        st.error("⚠️ No hay resultados de análisis de contrafuertes disponibles.")
                        st.info("Ejecuta primero el análisis completo de contrafuertes.")
                        st.stop()
                    
                    # Crear diseño del fuste para contrafuertes
                    diseno_fuste_contrafuertes = {
                        'kp': kp,
                        'Ep_kg_m': Ep * 1000,
                        'yt': D/3,
                        'Mvol_total': M_volcador,
                        'Mesta_total': M_estabilizador,
                        'FSv': FS_volcamiento,
                        'FSd': FS_deslizamiento,
                        'x_barra': x_barra,
                        'e': e,
                        'rho_real': 0.0033,
                        'dreq': 30,
                        'dreal': d_contrafuertes,
                        'As': As_contrafuertes,
                        'Asmin': As_min_vertical,
                        'As_proporcionado': As_contrafuertes,
                        'num_barras': 3,
                        'separacion': 15,
                        'num_barras_retraccion': 2,
                        'As_retraccion_proporcionado': As_min_horizontal
                    }
                    
                    pdf_buffer_contrafuertes = generar_pdf_reportlab(
                        resultados_contrafuertes_pdf, 
                        datos_entrada_contrafuertes, 
                        diseno_fuste_contrafuertes, 
                        "contrafuertes"
                    )
                    
                    st.download_button(
                        label="📄 Descargar PDF Contrafuertes",
                        data=pdf_buffer_contrafuertes.getvalue(),
                        file_name=f"reporte_contrafuertes_muro_contencion_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                        mime="application/pdf"
                    )
                except Exception as e:
                    st.error(f"⚠️ Error generando PDF: {str(e)}")
                    st.info("Intenta ejecutar el análisis completo nuevamente")
            
            with col3:
                if st.button("🖨️ Generar Reporte en Pantalla", type="primary", key="contrafuertes_pantalla"):
                    st.success("✅ Reporte Contrafuertes generado exitosamente")
                    st.balloons()
                    
                    # Mostrar el reporte en formato expandible
                    with st.expander("📋 VER REPORTE CONTRAFUERTES COMPLETO", expanded=True):
                        st.markdown(reporte_contrafuertes)

    elif opcion == "🏗️ Diseño del Fuste":
        st.title("Diseño y Verificación del Fuste del Muro")
        
        # Verificar acceso basado en plan del usuario
        user_plan = st.session_state.get('plan', 'gratuito')
        user_email = st.session_state.get('user', '')
        
        # Verificar si es admin (acceso completo)
        is_admin = user_email == 'admin' or user_email == 'admin@consorciodej.com'
        
        # Para usuarios normales, verificar plan real en el sistema de pagos
        if PAYMENT_SYSTEM_AVAILABLE and user_email and not is_admin:
            try:
                real_plan = payment_system.get_user_plan(user_email)
                current_plan = real_plan.get('plan', 'gratuito')
                
                # Actualizar session state si el plan cambió
                if st.session_state.get('plan') != current_plan:
                    st.session_state['plan'] = current_plan
                    if 'user_data' in st.session_state:
                        st.session_state['user_data']['plan'] = current_plan
                    user_plan = current_plan
            except Exception as e:
                # Si hay error, usar el plan de session state
                pass
        
        if user_plan == "gratuito" and not is_admin:
            st.warning("⚠️ Esta función requiere plan premium. Actualiza tu cuenta para acceder al diseño estructural.")
            st.info("Plan gratuito incluye: Cálculos básicos, resultados simples")
            st.info("Plan premium incluye: Diseño del fuste, cálculo de refuerzo, reportes detallados")
            
            # Mostrar botón para actualizar plan
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.button("⭐ Actualizar a Premium", type="primary", key="upgrade_diseno"):
                    st.session_state['show_pricing'] = True
                    st.rerun()
        else:
            st.success("⭐ Plan Premium: Diseño estructural completo del fuste")
            
            if 'diseno_fuste' in st.session_state and 'datos_entrada' in st.session_state:
                diseno_fuste = st.session_state['diseno_fuste']
                datos_entrada = st.session_state['datos_entrada']
                
                # Mostrar información del diseño del fuste
                st.subheader("📊 Resultados del Diseño del Fuste")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.metric("Coeficiente Pasivo (kp)", f"{diseno_fuste['kp']:.2f}")
                    st.metric("Empuje Pasivo", f"{diseno_fuste['Ep_kg_m']:.0f} kg/m")
                    st.metric("Altura de Aplicación", f"{diseno_fuste['yt']:.2f} m")
                    st.metric("Momento Volcador Total", f"{diseno_fuste['Mvol_total']:.2f} tn·m/m")
                    st.metric("Momento Estabilizador Total", f"{diseno_fuste['Mesta_total']:.2f} tn·m/m")
                
                with col2:
                    st.metric("Factor Seguridad Volcamiento", f"{diseno_fuste['FSv']:.2f}")
                    st.metric("Factor Seguridad Deslizamiento", f"{diseno_fuste['FSd']:.2f}")
                    st.metric("Ubicación Resultante (x̄)", f"{diseno_fuste['x_barra']:.3f} m")
                    st.metric("Excentricidad (e)", f"{diseno_fuste['e']:.3f} m")
                    st.metric("Cuantía Real (ρ)", f"{diseno_fuste['rho_real']:.4f}")
                
                # Diseño estructural
                st.subheader("🏗️ Diseño Estructural")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.info("**Peralte Efectivo:**")
                    st.write(f"• Requerido: {diseno_fuste['dreq']:.2f} cm")
                    st.write(f"• Real: {diseno_fuste['dreal']:.2f} cm")
                    if diseno_fuste['dreal'] >= diseno_fuste['dreq']:
                        st.success("✅ CUMPLE")
                    else:
                        st.error("⚠️ NO CUMPLE")
                
                with col2:
                    st.info("**Área de Acero:**")
                    st.write(f"• Requerida: {diseno_fuste['As']:.2f} cm²")
                    st.write(f"• Mínima: {diseno_fuste['Asmin']:.2f} cm²")
                    st.write(f"• Proporcionada: {diseno_fuste['As_proporcionado']:.2f} cm²")
                    if diseno_fuste['As_proporcionado'] >= diseno_fuste['As']:
                        st.success("✅ CUMPLE")
                    else:
                        st.error("⚠️ NO CUMPLE")
                
                with col3:
                    st.info("**Distribución:**")
                    st.write(f"• Barras 5/8\": {diseno_fuste['num_barras']}")
                    st.write(f"• Separación: {diseno_fuste['separacion']:.1f} cm")
                    st.write(f"• Barras retracción: {diseno_fuste['num_barras_retraccion']}")
                    st.write(f"• Acero retracción: {diseno_fuste['As_retraccion_proporcionado']:.2f} cm²")
                
                # Tabla de propiedades del acero
                st.subheader("📋 Propiedades del Acero Corrugado")
                acero_data = {
                    'Barra N°': ['3', '4', '5', '6', '7'],
                    'Diámetro (pulg)': ['3/8', '1/2', '5/8', '3/4', '7/8'],
                    'Diámetro (cm)': [0.98, 1.27, 1.59, 1.91, 2.22],
                    'Peso (kg/m)': [0.559, 0.993, 1.552, 2.235, 3.042],
                    'Área (cm²)': [0.71, 1.27, 1.98, 2.85, 3.85],
                    'Perímetro (cm)': [2.99, 3.99, 4.99, 5.98, 6.98]
                }
                
                df_acero = pd.DataFrame(acero_data)
                st.dataframe(df_acero, use_container_width=True)
                
                # Verificaciones de estabilidad
                st.subheader("🔍 Verificaciones de Estabilidad del Fuste")
                
                verificaciones = []
                
                # Verificación al volcamiento
                if diseno_fuste['FSv'] >= 2.0:
                    verificaciones.append(["Volcamiento", "✅ CUMPLE", f"FS = {diseno_fuste['FSv']:.2f} ≥ 2.0"])
                else:
                    verificaciones.append(["Volcamiento", "⚠️ NO CUMPLE", f"FS = {diseno_fuste['FSv']:.2f} < 2.0"])
                
                # Verificación al deslizamiento
                if diseno_fuste['FSd'] >= 1.5:
                    verificaciones.append(["Deslizamiento", "✅ CUMPLE", f"FS = {diseno_fuste['FSd']:.2f} ≥ 1.5"])
                else:
                    verificaciones.append(["Deslizamiento", "⚠️ NO CUMPLE", f"FS = {diseno_fuste['FSd']:.2f} < 1.5"])
                
                # Verificación de peralte
                if diseno_fuste['dreal'] >= diseno_fuste['dreq']:
                    verificaciones.append(["Peralte Efectivo", "✅ CUMPLE", f"dreal = {diseno_fuste['dreal']:.2f} ≥ {diseno_fuste['dreq']:.2f}"])
                else:
                    verificaciones.append(["Peralte Efectivo", "⚠️ NO CUMPLE", f"dreal = {diseno_fuste['dreal']:.2f} < {diseno_fuste['dreq']:.2f}"])
                
                # Verificación de acero
                if diseno_fuste['As_proporcionado'] >= diseno_fuste['As']:
                    verificaciones.append(["Área de Acero", "✅ CUMPLE", f"As = {diseno_fuste['As_proporcionado']:.2f} ≥ {diseno_fuste['As']:.2f}"])
                else:
                    verificaciones.append(["Área de Acero", "⚠️ NO CUMPLE", f"As = {diseno_fuste['As_proporcionado']:.2f} < {diseno_fuste['As']:.2f}"])
                
                # Verificación de cuantía mínima
                if diseno_fuste['rho_real'] >= 0.0033:
                    verificaciones.append(["Cuantía Mínima", "✅ CUMPLE", f"ρ = {diseno_fuste['rho_real']:.4f} ≥ 0.0033"])
                else:
                    verificaciones.append(["Cuantía Mínima", "⚠️ NO CUMPLE", f"ρ = {diseno_fuste['rho_real']:.4f} < 0.0033"])
                
                # Mostrar tabla de verificaciones
                df_verif = pd.DataFrame(verificaciones)
                df_verif.columns = ['Verificación', 'Estado', 'Detalle']
                st.dataframe(df_verif, use_container_width=True, hide_index=True)
                
                # Resumen final
                cumple_todo = (diseno_fuste['FSv'] >= 2.0 and diseno_fuste['FSd'] >= 1.5 and 
                              diseno_fuste['dreal'] >= diseno_fuste['dreq'] and 
                              diseno_fuste['As_proporcionado'] >= diseno_fuste['As'] and
                              diseno_fuste['rho_real'] >= 0.0033)
                
                if cumple_todo:
                    st.success("🎉 **RESULTADO FINAL:** El fuste del muro CUMPLE con todos los requisitos de diseño estructural")
                else:
                    st.error("⚠️ **RESULTADO FINAL:** El fuste del muro NO CUMPLE con todos los requisitos. Se recomienda revisar el diseño.")
                
            else:
                st.warning("⚠️ No hay datos de diseño del fuste disponibles. Ejecuta primero el análisis completo.")

    elif opcion == "📄 Generar Reporte":
        st.title("Generar Reporte Técnico")
        
        if st.session_state['plan'] == "gratuito":
            if 'resultados_basicos' in st.session_state:
                resultados = st.session_state['resultados_basicos']
                
                # Reporte básico gratuito
                reporte_basico = f"""
# REPORTE BÁSICO - MURO DE CONTENCIÓN
## CONSORCIO DEJ
### Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}

### DATOS DE ENTRADA:
- Altura del muro: {resultados['altura']:.2f} m
- Base del muro: {resultados['base']:.2f} m
- Espesor del muro: {resultados['espesor']:.2f} m
- Longitud del muro: {resultados['longitud']:.2f} m
- Peso específico del hormigón: 24.0 kN/m³
- Peso específico del suelo: 18.0 kN/m³
- Ángulo de fricción del suelo: 30.0°

### RESULTADOS DEL CÁLCULO:
- Peso del muro: {resultados['peso_muro']:.2f} kN
- Empuje del suelo: {resultados['empuje_suelo']:.2f} kN
- Factor de seguridad al volcamiento: {resultados['fs_volcamiento']:.2f}
- Volumen de hormigón: {resultados['volumen']:.2f} m³
- Coeficiente de empuje activo (Ka): {resultados['ka']:.3f}
- Momento volcador: {resultados['momento_volcador']:.2f} kN·m
- Momento estabilizador: {resultados['momento_estabilizador']:.2f} kN·m

### ANÁLISIS DE ESTABILIDAD:
"""
                
                if resultados['fs_volcamiento'] > 1.5:
                    reporte_basico += "✅ El muro es estable al volcamiento (FS > 1.5)"
                else:
                    reporte_basico += "⚠️ El muro requiere revisión de estabilidad (FS < 1.5)"
                
                reporte_basico += f"""

### CONCLUSIONES:
El análisis básico indica que el muro de contención {'cumple' if resultados['fs_volcamiento'] > 1.5 else 'no cumple'} con los requisitos mínimos de estabilidad al volcamiento.

### NOTA:
Este es un reporte básico del plan gratuito. Para análisis más detallados, considere actualizar al plan premium.

---
Generado por: CONSORCIO DEJ
Plan: Gratuito
"""
                
                st.text_area("Reporte Básico", reporte_basico, height=500)
                
                # Botones para el reporte básico
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.download_button(
                        label="📥 Descargar TXT",
                        data=reporte_basico,
                        file_name=f"reporte_basico_muro_contencion_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                        mime="text/plain"
                    )
                
                with col2:
                    # Generar PDF básico
                    pdf_buffer = generar_pdf_reportlab(resultados, {}, {}, "gratuito")
                    st.download_button(
                        label="📄 Descargar PDF",
                        data=pdf_buffer.getvalue(),
                        file_name=f"reporte_basico_muro_contencion_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                        mime="application/pdf"
                    )
                
                with col3:
                    if st.button("🖨️ Generar Reporte en Pantalla", type="primary"):
                        st.success("✅ Reporte básico generado exitosamente")
                        st.balloons()
                        
                        # Mostrar el reporte en formato expandible
                        with st.expander("📋 VER REPORTE BÁSICO COMPLETO", expanded=True):
                            st.markdown(reporte_basico)
            else:
                st.warning("⚠️ No hay resultados disponibles. Realiza primero los cálculos básicos.")
        else:
            # Reporte premium completo
            if 'resultados_completos' in st.session_state:
                resultados = st.session_state['resultados_completos']
                
                reporte_premium = f"""
# REPORTE TÉCNICO COMPLETO - MURO DE CONTENCIÓN
## CONSORCIO DEJ
### Análisis según Teoría de Rankine
### Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}

### 1. COEFICIENTES DE PRESIÓN:
- Coeficiente de empuje activo (Ka): {resultados['ka']:.3f}
- Coeficiente de empuje pasivo (Kp): {resultados['kp']:.3f}
- Altura equivalente por sobrecarga (hs): {resultados['hs']:.3f} m

### 2. DIMENSIONES CALCULADAS:
- Ancho de zapata (Bz): {resultados['Bz']:.2f} m
- Peralte de zapata (hz): {resultados['hz']:.2f} m
- Espesor del muro (b): {resultados['b']:.2f} m
- Longitud de puntera (r): {resultados['r']:.2f} m
- Longitud de talón (t): {resultados['t']:.2f} m
- Peralte de Zapata (h1): {resultados['h1']:.2f} m
- Profundidad de desplante (Df): {resultados['Df']:.2f} m

### 3. ANÁLISIS DE EMPUJES:
- Empuje activo por relleno: {resultados['Ea_relleno']:.2f} tn/m
- Empuje activo por sobrecarga: {resultados['Ea_sobrecarga']:.2f} tn/m
- Empuje activo total: {resultados['Ea_total']:.2f} tn/m
- Empuje pasivo: {resultados['Ep']:.2f} tn/m

### 4. ANÁLISIS DE PESOS:
- Peso del muro: {resultados['W_muro']:.2f} tn/m
- Peso de la zapata: {resultados['W_zapata']:.2f} tn/m
- Peso del relleno: {resultados['W_relleno']:.2f} tn/m
- Peso total: {resultados['W_total']:.2f} tn/m

### 5. MOMENTOS Y FACTORES DE SEGURIDAD:
- Momento volcador: {resultados['M_volcador']:.2f} tn·m/m
- Momento estabilizador: {resultados['M_estabilizador']:.2f} tn·m/m
- Factor de seguridad al volcamiento: {resultados['FS_volcamiento']:.2f}
- Factor de seguridad al deslizamiento: {resultados['FS_deslizamiento']:.2f}

### 6. VERIFICACIÓN DE PRESIONES:
- Presión máxima: {resultados['q_max_kg_cm2']:.2f} kg/cm²
- Presión mínima: {resultados['q_min_kg_cm2']:.2f} kg/cm²
- Excentricidad: {resultados['e']:.3f} m
- Hay tensiones: {'Sí' if resultados['tension'] else 'No'}

### 7. VERIFICACIONES DE ESTABILIDAD:
"""
                
                # Verificaciones de estabilidad
                cumple_volcamiento = resultados['FS_volcamiento'] >= 2.0
                cumple_deslizamiento = resultados['FS_deslizamiento'] >= 1.5
                cumple_presion = resultados['q_max_kg_cm2'] <= 2.5  # Asumiendo q_adm = 2.5 kg/cm²
                cumple_excentricidad = resultados['e'] <= resultados['Bz'] / 6
                sin_tensiones = not resultados['tension']
                
                reporte_premium += f"""
**Verificación al Volcamiento:**
- Factor de seguridad calculado: {resultados['FS_volcamiento']:.2f}
- Factor mínimo requerido: 2.0
- Estado: {'✅ CUMPLE' if cumple_volcamiento else '⚠️ NO CUMPLE'}

**Verificación al Deslizamiento:**
- Factor de seguridad calculado: {resultados['FS_deslizamiento']:.2f}
- Factor mínimo requerido: 1.5
- Estado: {'✅ CUMPLE' if cumple_deslizamiento else '⚠️ NO CUMPLE'}

**Verificación de Presiones:**
- Presión máxima: {resultados['q_max_kg_cm2']:.2f} kg/cm²
- Presión admisible: 2.5 kg/cm²
- Estado: {'✅ CUMPLE' if cumple_presion else '⚠️ NO CUMPLE'}

**Verificación de Excentricidad:**
- Excentricidad calculada: {resultados['e']:.3f} m
- Límite (B/6): {resultados['Bz']/6:.3f} m
- Estado: {'✅ CUMPLE' if cumple_excentricidad else '⚠️ NO CUMPLE'}

**Verificación de Tensiones:**
- Hay tensiones: {'Sí' if resultados['tension'] else 'No'}
- Estado: {'✅ CUMPLE' if sin_tensiones else '⚠️ NO CUMPLE'}

### 8. RESULTADO FINAL:
"""
                
                cumple_todo = cumple_volcamiento and cumple_deslizamiento and cumple_presion and cumple_excentricidad and sin_tensiones
                
                if cumple_todo:
                    reporte_premium += """
🎉 **EL MURO CUMPLE CON TODOS LOS REQUISITOS DE ESTABILIDAD**

El análisis completo según la teoría de Rankine indica que el muro de contención 
es estructuralmente seguro y cumple con todas las verificaciones requeridas.
"""
                else:
                    reporte_premium += """
⚠️ **EL MURO NO CUMPLE CON TODOS LOS REQUISITOS**

Se recomienda revisar las dimensiones del muro o las propiedades del suelo 
para mejorar los factores de seguridad y cumplir con las especificaciones.
"""

                # Agregar información del diseño del fuste si está disponible
                if 'diseno_fuste' in st.session_state and st.session_state['diseno_fuste']:
                    diseno_fuste = st.session_state['diseno_fuste']
                    reporte_premium += f"""

### 9. DISEÑO Y VERIFICACIÓN DEL FUSTE DEL MURO:
**9.1 Coeficiente Pasivo y Empuje:**
- Coeficiente pasivo (kp): {diseno_fuste['kp']:.2f}
- Empuje pasivo: {diseno_fuste['Ep_kg_m']:.0f} kg/m
- Altura de aplicación: {diseno_fuste['yt']:.2f} m

**9.2 Momentos y Factores de Seguridad:**
- Momento volcador total: {diseno_fuste['Mvol_total']:.2f} tn·m/m
- Momento estabilizador total: {diseno_fuste['Mesta_total']:.2f} tn·m/m
- Factor de seguridad al volcamiento: {diseno_fuste['FSv']:.2f}
- Factor de seguridad al deslizamiento: {diseno_fuste['FSd']:.2f}

**9.3 Diseño Estructural:**
- Peralte efectivo requerido: {diseno_fuste['dreq']:.2f} cm
- Peralte efectivo real: {diseno_fuste['dreal']:.2f} cm
- Área de acero requerida: {diseno_fuste['As']:.2f} cm²
- Área de acero mínima: {diseno_fuste['Asmin']:.2f} cm²
- Área de acero proporcionada: {diseno_fuste['As_proporcionado']:.2f} cm²

**9.4 Distribución del Acero:**
- Número de barras 5/8\": {diseno_fuste['num_barras']}
- Separación entre barras: {diseno_fuste['separacion']:.1f} cm
- Acero por retracción y temperatura: {diseno_fuste['As_retraccion']:.2f} cm²
- Barras de retracción 1/2\": {diseno_fuste['num_barras_retraccion']}

**9.5 Verificaciones del Fuste:**
- Peralte efectivo: {'✅ CUMPLE' if diseno_fuste['dreal'] >= diseno_fuste['dreq'] else '⚠️ NO CUMPLE'}
- Área de acero: {'✅ CUMPLE' if diseno_fuste['As_proporcionado'] >= diseno_fuste['As'] else '⚠️ NO CUMPLE'}
- Cuantía mínima: {'✅ CUMPLE' if diseno_fuste['rho_real'] >= 0.0033 else '⚠️ NO CUMPLE'}

### 10. RECOMENDACIONES TÉCNICAS:
- Verificar la capacidad portante del suelo en campo
- Revisar el diseño del refuerzo estructural según ACI 318
- Considerar efectos sísmicos según la normativa local
- Realizar inspecciones periódicas durante la construcción
- Monitorear deformaciones durante el servicio
- Verificar drenaje del relleno para evitar presiones hidrostáticas
- **NUEVO:** Verificar la colocación del acero según el diseño calculado
- **NUEVO:** Controlar la calidad del concreto durante la construcción

### 11. INFORMACIÓN DEL PROYECTO:
- Empresa: CONSORCIO DEJ
- Método de análisis: Teoría de Rankine
- Diseño estructural: Según PARTE 2.2.py
- Fecha de análisis: {datetime.now().strftime('%d/%m/%Y %H:%M')}
- Plan: Premium
- Software: Streamlit + Python

---
**Este reporte fue generado automáticamente por el sistema de análisis de muros de contención de CONSORCIO DEJ.**
**Para consultas técnicas, contacte a nuestro equipo de ingeniería.**
"""
                else:
                    reporte_premium += f"""

### 9. RECOMENDACIONES TÉCNICAS:
- Verificar la capacidad portante del suelo en campo
- Revisar el diseño del refuerzo estructural según ACI 318
- Considerar efectos sísmicos según la normativa local
- Realizar inspecciones periódicas durante la construcción
- Monitorear deformaciones durante el servicio
- Verificar drenaje del relleno para evitar presiones hidrostáticas

### 10. INFORMACIÓN DEL PROYECTO:
- Empresa: CONSORCIO DEJ
- Método de análisis: Teoría de Rankine
- Fecha de análisis: {datetime.now().strftime('%d/%m/%Y %H:%M')}
- Plan: Premium
- Software: Streamlit + Python

---
**Este reporte fue generado automáticamente por el sistema de análisis de muros de contención de CONSORCIO DEJ.**
**Para consultas técnicas, contacte a nuestro equipo de ingeniería.**
"""
                
                st.text_area("Reporte Premium", reporte_premium, height=600)
                
                # Botones para el reporte premium
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.download_button(
                        label="📥 Descargar TXT",
                        data=reporte_premium,
                        file_name=f"reporte_premium_muro_contencion_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                        mime="text/plain"
                    )
                
                with col2:
                    # Generar PDF premium con diseño del fuste
                    if 'datos_entrada' in st.session_state and 'diseno_fuste' in st.session_state:
                        try:
                            # Verificar si hay resultados de Rankine disponibles
                            resultados_rankine_pdf = None
                            datos_entrada_rankine_pdf = None
                            if 'resultados_rankine' in st.session_state and 'datos_entrada_rankine' in st.session_state:
                                resultados_rankine_pdf = st.session_state['resultados_rankine']
                                datos_entrada_rankine_pdf = st.session_state['datos_entrada_rankine']
                            else:
                                # Usar datos de resultados_completos como fallback
                                resultados_rankine_pdf = st.session_state['resultados_completos']
                                datos_entrada_rankine_pdf = st.session_state['datos_entrada']
                            
                            # Verificar si hay resultados de Coulomb disponibles
                            resultados_coulomb_pdf = None
                            datos_entrada_coulomb_pdf = None
                            if 'resultados_coulomb' in st.session_state and 'datos_entrada_coulomb' in st.session_state:
                                resultados_coulomb_pdf = st.session_state['resultados_coulomb']
                                datos_entrada_coulomb_pdf = st.session_state['datos_entrada_coulomb']
                            
                            pdf_buffer = generar_pdf_reportlab(
                                resultados_rankine_pdf, 
                                datos_entrada_rankine_pdf, 
                                st.session_state['diseno_fuste'], 
                                "premium",
                                resultados_coulomb_pdf,
                                datos_entrada_coulomb_pdf
                            )
                            st.download_button(
                                label="📄 Descargar PDF Premium",
                                data=pdf_buffer.getvalue(),
                                file_name=f"reporte_premium_muro_contencion_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                                mime="application/pdf"
                            )
                        except Exception as e:
                            st.error(f"⚠️ Error generando PDF: {str(e)}")
                            st.info("Intenta ejecutar el análisis completo nuevamente")
                    else:
                        st.warning("⚠️ Ejecuta primero el análisis completo")
                
                with col3:
                    if st.button("🖨️ Generar Reporte en Pantalla", type="primary"):
                        st.success("✅ Reporte técnico generado exitosamente")
                        st.balloons()
                        
                        # Mostrar el reporte en formato expandible
                        with st.expander("📋 VER REPORTE TÉCNICO COMPLETO", expanded=True):
                            st.markdown(reporte_premium)
            else:
                st.warning("⚠️ No hay resultados disponibles. Realiza primero el análisis completo.")

    elif opcion == "📈 Gráficos":
        st.title("Gráficos y Visualizaciones")
        
        # Verificar qué métodos tienen resultados disponibles
        resultados_rankine_disponibles = 'resultados_completos' in st.session_state
        resultados_coulomb_disponibles = 'resultados_coulomb' in st.session_state
        
        # Mostrar opciones de métodos disponibles
        st.subheader("🔬 Seleccionar Método de Análisis")
        
        if resultados_rankine_disponibles and resultados_coulomb_disponibles:
            metodo_seleccionado = st.radio(
                "Método de análisis para visualizar:",
                ["📊 Análisis Rankine", "🔬 Análisis Coulomb"],
                help="Selecciona el método cuyos gráficos deseas visualizar"
            )
        elif resultados_rankine_disponibles:
            metodo_seleccionado = "📊 Análisis Rankine"
            st.info("✅ Solo hay resultados disponibles para el método Rankine")
        elif resultados_coulomb_disponibles:
            metodo_seleccionado = "🔬 Análisis Coulomb"
            st.info("✅ Solo hay resultados disponibles para el método Coulomb")
        else:
            st.warning("⚠️ No hay resultados disponibles. Ejecuta primero algún análisis completo.")
            st.info("📊 Ve a 'Análisis Completo (Rankine)' o 'Análisis Coulomb' para generar resultados")
            st.stop()
        
        if st.session_state['plan'] == "gratuito":
            if 'resultados_basicos' in st.session_state:
                resultados = st.session_state['resultados_basicos']
                
                # Gráfico básico gratuito
                datos = pd.DataFrame({
                    'Fuerza': ['Peso Muro', 'Empuje Suelo'],
                    'Valor (kN)': [resultados['peso_muro'], resultados['empuje_suelo']]
                })
                
                fig = px.bar(datos, x='Fuerza', y='Valor (kN)', 
                            title="Comparación de Fuerzas - Plan Gratuito",
                            color='Fuerza',
                            color_discrete_map={'Peso Muro': '#2E8B57', 'Empuje Suelo': '#DC143C'})
                
                fig.update_layout(
                    xaxis_title="Tipo de Fuerza",
                    yaxis_title="Valor (kN)",
                    height=400
                )
                
                fig.update_traces(texttemplate='%{y:.1f}', textposition='outside')
                st.plotly_chart(fig, use_container_width=True)
                
                # Gráfico de momentos
                datos_momentos = pd.DataFrame({
                    'Momento': ['Volcador', 'Estabilizador'],
                    'Valor (kN·m)': [resultados['momento_volcador'], resultados['momento_estabilizador']]
                })
                
                fig2 = px.pie(datos_momentos, values='Valor (kN·m)', names='Momento',
                             title="Distribución de Momentos - Plan Gratuito",
                             color_discrete_map={'Volcador': '#FF6B6B', 'Estabilizador': '#4ECDC4'})
                
                fig2.update_traces(textposition='inside', textinfo='percent+label+value')
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.warning("⚠️ No hay resultados disponibles. Realiza primero los cálculos básicos.")
        else:
            # Gráficos premium
            if metodo_seleccionado == "📊 Análisis Rankine" and resultados_rankine_disponibles:
                st.subheader("📊 Gráficos del Análisis Rankine")
                resultados = st.session_state['resultados_completos']
                
                # Gráfico de fuerzas
                col1, col2 = st.columns(2)
                
                with col1:
                    datos_fuerzas = pd.DataFrame({
                        'Fuerza': ['Empuje Activo', 'Empuje Pasivo', 'Peso Total'],
                        'Valor (tn/m)': [resultados.get('Ea_total', 0), resultados.get('Ep', 0), 
                                        resultados.get('W_total', 0)],
                        'h1 (m)': [resultados.get('h1', 0)]*3,
                        'Df (m)': [resultados.get('Df', 0)]*3,
                        'hm (m)': [resultados.get('hm', 0)]*3,
                        'γ_relleno (kg/m³)': [resultados.get('gamma_relleno', 0)]*3,
                        'φ_relleno (°)': [resultados.get('phi_relleno', 0)]*3,
                        'γ_cimentacion (kg/m³)': [resultados.get('gamma_cimentacion', 0)]*3,
                        'φ_cimentacion (°)': [resultados.get('phi_cimentacion', 0)]*3,
                        'c (t/m²)': [resultados.get('cohesion', 0)]*3,
                        'σ_adm (kg/cm²)': [resultados.get('sigma_adm', 0)]*3,
                        'γ_concreto (kg/m³)': [resultados.get('gamma_concreto', 0)]*3,
                        'qsc (kg/m²)': [resultados.get('qsc', 0)]*3,
                        'fc (kg/cm²)': [resultados.get('fc', 0)]*3,
                        'fy (kg/cm²)': [resultados.get('fy', 0)]*3
                    })
                    
                    if PLOTLY_AVAILABLE:
                        fig1 = px.bar(
                            datos_fuerzas, x='Fuerza', y='Valor (tn/m)',
                            title="Análisis de Fuerzas - Rankine",
                                 color='Fuerza',
                                 color_discrete_map={
                                     'Empuje Activo': '#DC143C',
                                     'Empuje Pasivo': '#2E8B57',
                                     'Peso Total': '#4169E1'
                            },
                            custom_data=[
                                'h1 (m)', 'Df (m)', 'hm (m)', 'γ_relleno (kg/m³)', 'φ_relleno (°)',
                                'γ_cimentacion (kg/m³)', 'φ_cimentacion (°)', 'c (t/m²)', 'σ_adm (kg/cm²)',
                                'γ_concreto (kg/m³)', 'qsc (kg/m²)', 'fc (kg/cm²)', 'fy (kg/cm²)'
                            ]
                        )
                        
                        fig1.update_traces(
                            texttemplate='%{y:.2f}', textposition='outside',
                            hovertemplate="<b>%{x}</b><br>Valor: %{y:.2f} tn/m" +
                            "<br>h1: %{customdata[0]} m" +
                            "<br>Df: %{customdata[1]} m" +
                            "<br>hm: %{customdata[2]} m" +
                            "<br>γ_relleno: %{customdata[3]} kg/m³" +
                            "<br>φ_relleno: %{customdata[4]}°" +
                            "<br>γ_cimentacion: %{customdata[5]} kg/m³" +
                            "<br>φ_cimentacion: %{customdata[6]}°" +
                            "<br>c: %{customdata[7]} t/m²" +
                            "<br>σ_adm: %{customdata[8]} kg/cm²" +
                            "<br>γ_concreto: %{customdata[9]} kg/m³" +
                            "<br>qsc: %{customdata[10]} kg/m²" +
                            "<br>fc: %{customdata[11]} kg/cm²" +
                            "<br>fy: %{customdata[12]} kg/cm²<extra></extra>"
                        )
                    st.plotly_chart(fig1, use_container_width=True)
                    
                    # Leyenda textual de parámetros Rankine
                    st.markdown(f"""
                    **Parámetros de Entrada - Rankine:**
                    - h1: {resultados.get('h1', 0)} m, Df: {resultados.get('Df', 0)} m, hm: {resultados.get('hm', 0)} m
                    - γ_relleno: {resultados.get('gamma_relleno', 0)} kg/m³, φ_relleno: {resultados.get('phi_relleno', 0)}°
                    - γ_cimentacion: {resultados.get('gamma_cimentacion', 0)} kg/m³, φ_cimentacion: {resultados.get('phi_cimentacion', 0)}°
                    - c: {resultados.get('cohesion', 0)} t/m², σ_adm: {resultados.get('sigma_adm', 0)} kg/cm²
                    - γ_concreto: {resultados.get('gamma_concreto', 0)} kg/m³, qsc: {resultados.get('qsc', 0)} kg/m²
                    - fc: {resultados.get('fc', 0)} kg/cm², fy: {resultados.get('fy', 0)} kg/cm²
                    """)
                
                with col2:
                    # Gráfico de momentos
                    datos_momentos = pd.DataFrame({
                        'Momento': ['Volcador', 'Estabilizador'],
                        'Valor (tn·m/m)': [resultados.get('M_volcador', 0), resultados.get('M_estabilizador', 0)]
                    })
                    
                    if PLOTLY_AVAILABLE:
                        fig2 = px.pie(datos_momentos, values='Valor (tn·m/m)', names='Momento',
                                     title="Distribución de Momentos - Rankine",
                                     color_discrete_map={'Volcador': '#FF6B6B', 'Estabilizador': '#4ECDC4'})
                        
                        fig2.update_traces(textposition='inside', textinfo='percent+label+value')
                        st.plotly_chart(fig2, use_container_width=True)
                
                # Gráfico de dimensiones
                st.subheader("📏 Dimensiones del Muro - Rankine")
                dimensiones = {
                    'Dimensión': ['Bz', 'hz', 'b', 'r', 't'],
                    'Valor (m)': [resultados.get('Bz', 0), resultados.get('hz', 0), resultados.get('b', 0), 
                                 resultados.get('r', 0), resultados.get('t', 0)],
                    'h1 (m)': [resultados.get('h1', 0)]*5,
                    'Df (m)': [resultados.get('Df', 0)]*5,
                    'hm (m)': [resultados.get('hm', 0)]*5,
                    'γ_relleno (kg/m³)': [resultados.get('gamma_relleno', 0)]*5,
                    'φ_relleno (°)': [resultados.get('phi_relleno', 0)]*5,
                    'γ_cimentacion (kg/m³)': [resultados.get('gamma_cimentacion', 0)]*5,
                    'φ_cimentacion (°)': [resultados.get('phi_cimentacion', 0)]*5,
                    'c (t/m²)': [resultados.get('cohesion', 0)]*5,
                    'σ_adm (kg/cm²)': [resultados.get('sigma_adm', 0)]*5,
                    'γ_concreto (kg/m³)': [resultados.get('gamma_concreto', 0)]*5,
                    'qsc (kg/m²)': [resultados.get('qsc', 0)]*5,
                    'fc (kg/cm²)': [resultados.get('fc', 0)]*5,
                    'fy (kg/cm²)': [resultados.get('fy', 0)]*5
                }
                
                if PLOTLY_AVAILABLE:
                    fig3 = px.bar(
                        pd.DataFrame(dimensiones), x='Dimensión', y='Valor (m)',
                        title="Dimensiones Calculadas del Muro - Rankine",
                             color='Dimensión',
                             color_discrete_map={
                                 'Bz': '#FF1493',
                                 'hz': '#00CED1',
                                 'b': '#32CD32',
                                 'r': '#FFD700',
                                 't': '#FF6347'
                        },
                        custom_data=[
                            'h1 (m)', 'Df (m)', 'hm (m)', 'γ_relleno (kg/m³)', 'φ_relleno (°)',
                            'γ_cimentacion (kg/m³)', 'φ_cimentacion (°)', 'c (t/m²)', 'σ_adm (kg/cm²)',
                            'γ_concreto (kg/m³)', 'qsc (kg/m²)', 'fc (kg/cm²)', 'fy (kg/cm²)'
                        ]
                    )
                    
                    fig3.update_traces(
                        texttemplate='%{y:.2f}', textposition='outside',
                        hovertemplate="<b>%{x}</b><br>Valor: %{y:.2f} m" +
                        "<br>h1: %{customdata[0]} m" +
                        "<br>Df: %{customdata[1]} m" +
                        "<br>hm: %{customdata[2]} m" +
                        "<br>γ_relleno: %{customdata[3]} kg/m³" +
                        "<br>φ_relleno: %{customdata[4]}°" +
                        "<br>γ_cimentacion: %{customdata[5]} kg/m³" +
                        "<br>φ_cimentacion: %{customdata[6]}°" +
                        "<br>c: %{customdata[7]} t/m²" +
                        "<br>σ_adm: %{customdata[8]} kg/cm²" +
                        "<br>γ_concreto: %{customdata[9]} kg/m³" +
                        "<br>qsc: %{customdata[10]} kg/m²" +
                        "<br>fc: %{customdata[11]} kg/cm²" +
                        "<br>fy: %{customdata[12]} kg/cm²<extra></extra>"
                    )
                    st.plotly_chart(fig3, use_container_width=True)
                
                # Leyenda textual de dimensiones Rankine
                st.markdown(f"""
                **Dimensiones Calculadas - Rankine:**
                - Bz: {resultados.get('Bz', 0):.2f} m, hz: {resultados.get('hz', 0):.2f} m, b: {resultados.get('b', 0):.2f} m
                - r: {resultados.get('r', 0):.2f} m, t: {resultados.get('t', 0):.2f} m, hm: {resultados.get('hm', 0):.2f} m
                """)
                
                # Gráfico de factores de seguridad
                st.subheader("🛡️ Factores de Seguridad - Rankine")
                col1, col2 = st.columns(2)
                
                with col1:
                    datos_fs = pd.DataFrame({
                        'Verificación': ['Volcamiento', 'Deslizamiento'],
                        'Factor de Seguridad': [resultados.get('FS_volcamiento', 0), resultados.get('FS_deslizamiento', 0)],
                        'Límite': [2.0, 1.5],
                        'h1 (m)': [resultados.get('h1', 0)]*2,
                        'Df (m)': [resultados.get('Df', 0)]*2,
                        'hm (m)': [resultados.get('hm', 0)]*2,
                        'γ_relleno (kg/m³)': [resultados.get('gamma_relleno', 0)]*2,
                        'φ_relleno (°)': [resultados.get('phi_relleno', 0)]*2,
                        'γ_cimentacion (kg/m³)': [resultados.get('gamma_cimentacion', 0)]*2,
                        'φ_cimentacion (°)': [resultados.get('phi_cimentacion', 0)]*2,
                        'c (t/m²)': [resultados.get('cohesion', 0)]*2,
                        'σ_adm (kg/cm²)': [resultados.get('sigma_adm', 0)]*2,
                        'γ_concreto (kg/m³)': [resultados.get('gamma_concreto', 0)]*2,
                        'qsc (kg/m²)': [resultados.get('qsc', 0)]*2,
                        'fc (kg/cm²)': [resultados.get('fc', 0)]*2,
                        'fy (kg/cm²)': [resultados.get('fy', 0)]*2
                    })
                    
                    if PLOTLY_AVAILABLE:
                        fig_fs = px.bar(
                            datos_fs, x='Verificación', y=['Factor de Seguridad', 'Límite'],
                            title="Factores de Seguridad - Rankine",
                            barmode='group',
                            color_discrete_map={
                                'Factor de Seguridad': '#4ECDC4',
                                'Límite': '#FF6B6B'
                            },
                            custom_data=[
                                'h1 (m)', 'Df (m)', 'hm (m)', 'γ_relleno (kg/m³)', 'φ_relleno (°)',
                                'γ_cimentacion (kg/m³)', 'φ_cimentacion (°)', 'c (t/m²)', 'σ_adm (kg/cm²)',
                                'γ_concreto (kg/m³)', 'qsc (kg/m²)', 'fc (kg/cm²)', 'fy (kg/cm²)'
                            ]
                        )
                        
                        fig_fs.update_traces(
                            texttemplate='%{y:.2f}', textposition='outside',
                            hovertemplate="<b>%{x}</b><br>Valor: %{y:.2f}" +
                            "<br>h1: %{customdata[0]} m" +
                            "<br>Df: %{customdata[1]} m" +
                            "<br>hm: %{customdata[2]} m" +
                            "<br>γ_relleno: %{customdata[3]} kg/m³" +
                            "<br>φ_relleno: %{customdata[4]}°" +
                            "<br>γ_cimentacion: %{customdata[5]} kg/m³" +
                            "<br>φ_cimentacion: %{customdata[6]}°" +
                            "<br>c: %{customdata[7]} t/m²" +
                            "<br>σ_adm: %{customdata[8]} kg/cm²" +
                            "<br>γ_concreto: %{customdata[9]} kg/m³" +
                            "<br>qsc: %{customdata[10]} kg/m²" +
                            "<br>fc: %{customdata[11]} kg/cm²" +
                            "<br>fy: %{customdata[12]} kg/cm²<extra></extra>"
                        )
                        st.plotly_chart(fig_fs, use_container_width=True)
                    
                    # Leyenda textual de factores de seguridad
                    st.markdown(f"""
                    **Factores de Seguridad - Rankine:**
                    - Volcamiento: {resultados.get('FS_volcamiento', 0):.2f} (Límite: 2.0)
                    - Deslizamiento: {resultados.get('FS_deslizamiento', 0):.2f} (Límite: 1.5)
                    """)
                
                with col2:
                    # Gráfico de presiones
                    datos_presiones = pd.DataFrame({
                        'Presión': ['Máxima', 'Mínima'],
                        'Valor (kg/cm²)': [resultados.get('q_max_kg_cm2', 0), resultados.get('q_min_kg_cm2', 0)],
                        'h1 (m)': [resultados.get('h1', 0)]*2,
                        'Df (m)': [resultados.get('Df', 0)]*2,
                        'hm (m)': [resultados.get('hm', 0)]*2,
                        'γ_relleno (kg/m³)': [resultados.get('gamma_relleno', 0)]*2,
                        'φ_relleno (°)': [resultados.get('phi_relleno', 0)]*2,
                        'γ_cimentacion (kg/m³)': [resultados.get('gamma_cimentacion', 0)]*2,
                        'φ_cimentacion (°)': [resultados.get('phi_cimentacion', 0)]*2,
                        'c (t/m²)': [resultados.get('cohesion', 0)]*2,
                        'σ_adm (kg/cm²)': [resultados.get('sigma_adm', 0)]*2,
                        'γ_concreto (kg/m³)': [resultados.get('gamma_concreto', 0)]*2,
                        'qsc (kg/m²)': [resultados.get('qsc', 0)]*2,
                        'fc (kg/cm²)': [resultados.get('fc', 0)]*2,
                        'fy (kg/cm²)': [resultados.get('fy', 0)]*2
                    })
                    
                    if PLOTLY_AVAILABLE:
                        fig_pres = px.bar(
                            datos_presiones, x='Presión', y='Valor (kg/cm²)',
                            title="Presiones sobre el Suelo - Rankine",
                            color='Presión',
                            color_discrete_map={
                                'Máxima': '#FF6B6B',
                                'Mínima': '#4ECDC4'
                            },
                            custom_data=[
                                'h1 (m)', 'Df (m)', 'hm (m)', 'γ_relleno (kg/m³)', 'φ_relleno (°)',
                                'γ_cimentacion (kg/m³)', 'φ_cimentacion (°)', 'c (t/m²)', 'σ_adm (kg/cm²)',
                                'γ_concreto (kg/m³)', 'qsc (kg/m²)', 'fc (kg/cm²)', 'fy (kg/cm²)'
                            ]
                        )
                        
                        fig_pres.update_traces(
                            texttemplate='%{y:.2f}', textposition='outside',
                            hovertemplate="<b>%{x}</b><br>Valor: %{y:.2f} kg/cm²" +
                            "<br>h1: %{customdata[0]} m" +
                            "<br>Df: %{customdata[1]} m" +
                            "<br>hm: %{customdata[2]} m" +
                            "<br>γ_relleno: %{customdata[3]} kg/m³" +
                            "<br>φ_relleno: %{customdata[4]}°" +
                            "<br>γ_cimentacion: %{customdata[5]} kg/m³" +
                            "<br>φ_cimentacion: %{customdata[6]}°" +
                            "<br>c: %{customdata[7]} t/m²" +
                            "<br>σ_adm: %{customdata[8]} kg/cm²" +
                            "<br>γ_concreto: %{customdata[9]} kg/m³" +
                            "<br>qsc: %{customdata[10]} kg/m²" +
                            "<br>fc: %{customdata[11]} kg/cm²" +
                            "<br>fy: %{customdata[12]} kg/cm²<extra></extra>"
                        )
                        st.plotly_chart(fig_pres, use_container_width=True)
                    
                    # Leyenda textual de presiones
                    st.markdown(f"""
                    **Presiones sobre el Suelo - Rankine:**
                    - Máxima: {resultados.get('q_max_kg_cm2', 0):.2f} kg/cm²
                    - Mínima: {resultados.get('q_min_kg_cm2', 0):.2f} kg/cm²
                    - Capacidad admisible: {resultados.get('sigma_adm', 0)} kg/cm²
                    """)
                
                # Gráfico del muro de contención
                st.subheader("🏗️ Visualización del Muro de Contención - Rankine")
                st.info("Representación gráfica detallada del muro diseñado según teoría de Rankine")
                
                # Crear dimensiones para el gráfico
                dimensiones_grafico = {
                    'Bz': resultados.get('Bz', 0),
                    'hz': resultados.get('hz', 0),
                    'b': resultados.get('b', 0),
                    'r': resultados.get('r', 0),
                    't': resultados.get('t', 0),
                    'hm': resultados.get('hm', 0)
                }
                
                # Generar el gráfico del muro con valores reales
                fig_muro = dibujar_muro_streamlit(dimensiones_grafico, resultados.get('h1', 0), resultados.get('Df', 0), resultados.get('qsc', 0), "rankine")
                
                # Mostrar el gráfico en Streamlit
                st.pyplot(fig_muro)
                
                # Información adicional sobre el gráfico
                st.markdown("""
                **Leyenda del Gráfico - Análisis Rankine:**
                - 🔵 **Zapata (Azul claro):** Base de cimentación del muro
                - 🔴 **Muro (Rosa):** Estructura principal de contención (vertical según Rankine)
                - 🟡 **Relleno (Amarillo):** Material de relleno detrás del muro
                - 🟤 **Suelo (Marrón):** Suelo de cimentación
                - 🔴 **Flechas rojas:** Sobrecarga aplicada (qsc)
                - 🔵 **Dimensiones en azul:** Medidas calculadas del muro
                - 📐 **Teoría Rankine:** Muro vertical liso, sin fricción muro-suelo
                """)
            
            elif metodo_seleccionado == "🔬 Análisis Coulomb" and resultados_coulomb_disponibles:
                st.subheader("🔬 Gráficos del Análisis Coulomb")
                resultados_coulomb = st.session_state['resultados_coulomb']
                
                # Gráfico comparativo Rankine vs Coulomb
                col1, col2 = st.columns(2)
                
                with col1:
                    # Calcular Ka de Rankine para comparación
                    if 'datos_entrada_coulomb' in st.session_state:
                        phi1_rankine = st.session_state['datos_entrada_coulomb']['phi1']
                    else:
                        phi1_rankine = 32  # Valor por defecto
                    
                    ka_rankine = math.tan(math.radians(45 - phi1_rankine/2))**2
                    
                    datos_comparacion = pd.DataFrame({
                        'Teoría': ['Rankine', 'Coulomb'],
                        'Coeficiente Ka': [ka_rankine, resultados_coulomb['Ka']]
                    })
                    
                    if PLOTLY_AVAILABLE:
                        fig_comp = px.bar(datos_comparacion, x='Teoría', y='Coeficiente Ka',
                                         title="Comparación Ka: Rankine vs Coulomb",
                                         color='Teoría',
                                         color_discrete_map={'Rankine': '#4ECDC4', 'Coulomb': '#FF6B6B'})
                        
                        fig_comp.update_layout(
                            xaxis_title="Teoría",
                            yaxis_title="Coeficiente Ka",
                            height=400
                        )
                        
                        fig_comp.update_traces(texttemplate='%{y:.6f}', textposition='outside')
                        st.plotly_chart(fig_comp, use_container_width=True)
                
                with col2:
                    # Gráfico de componentes del empuje Coulomb
                    datos_componentes = pd.DataFrame({
                        'Componente': ['Empuje Total (Pa)', 'Componente Horizontal (Ph)', 'Componente Vertical (Pv)', 'Empuje Sobrecarga (PSC)'],
                        'Valor (t/m)': [resultados_coulomb['Pa'], resultados_coulomb['Ph'], resultados_coulomb['Pv'], resultados_coulomb['PSC']]
                    })
                    
                    if PLOTLY_AVAILABLE:
                        fig_comp2 = px.bar(datos_componentes, x='Componente', y='Valor (t/m)',
                                          title="Componentes del Empuje - Coulomb",
                                          color='Componente',
                                          color_discrete_map={
                                              'Empuje Total (Pa)': '#FF6B6B',
                                              'Componente Horizontal (Ph)': '#4ECDC4',
                                              'Componente Vertical (Pv)': '#45B7D1',
                                              'Empuje Sobrecarga (PSC)': '#96CEB4'
                                          })
                        
                        fig_comp2.update_layout(
                            xaxis_title="Componente",
                            yaxis_title="Valor (t/m)",
                            height=400
                        )
                        
                        fig_comp2.update_traces(texttemplate='%{y:.3f}', textposition='outside')
                        st.plotly_chart(fig_comp2, use_container_width=True)
                
                # Gráfico de parámetros geométricos de Coulomb
                st.subheader("📐 Parámetros Geométricos - Coulomb")
                
                if 'datos_entrada_coulomb' in st.session_state:
                    datos_entrada_coulomb = st.session_state['datos_entrada_coulomb']
                    
                    datos_geometricos = pd.DataFrame({
                        'Parámetro': ['Altura Total (H)', 'Altura Efectiva (H\')', 'Ángulo β', 'Ángulo α', 'Ángulo δ'],
                        'Valor': [datos_entrada_coulomb['H'], resultados_coulomb['H_efectiva'], 
                                 resultados_coulomb['beta'], datos_entrada_coulomb['alpha'], datos_entrada_coulomb['delta']],
                        'Unidad': ['m', 'm', '°', '°', '°']
                    })
                    
                    if PLOTLY_AVAILABLE:
                        fig_geo = px.bar(datos_geometricos, x='Parámetro', y='Valor',
                                        title="Parámetros Geométricos - Análisis Coulomb",
                                        color='Parámetro',
                                        color_discrete_map={
                                            'Altura Total (H)': '#FFD93D',
                                            'Altura Efectiva (H\')': '#6BCF7F',
                                            'Ángulo β': '#4D96FF',
                                            'Ángulo α': '#FF6B6B',
                                            'Ángulo δ': '#9B59B6'
                                        })
                        
                        fig_geo.update_layout(
                            xaxis_title="Parámetro",
                            yaxis_title="Valor",
                            height=400
                        )
                        
                        fig_geo.update_traces(texttemplate='%{y:.2f}', textposition='outside')
                        st.plotly_chart(fig_geo, use_container_width=True)
                
                # Gráfico del muro de contención para Coulomb
                st.subheader("🏗️ Visualización del Muro de Contención - Coulomb")
                st.info("Representación gráfica del muro con análisis Coulomb")
                
                # Crear dimensiones para el gráfico (usando valores típicos para Coulomb)
                if 'datos_entrada_coulomb' in st.session_state:
                    datos_entrada_coulomb = st.session_state['datos_entrada_coulomb']
                    dimensiones_coulomb = {
                        'Bz': datos_entrada_coulomb['t2'] + datos_entrada_coulomb['b2'] + 0.5,  # Base total estimada
                        'hz': 0.4,  # Peralte de zapata típico
                        'b': 0.3,   # Espesor del muro
                        'r': datos_entrada_coulomb['t2'],    # Longitud de puntera
                        't': datos_entrada_coulomb['b2'],    # Longitud de talón
                        'hm': 0.2   # Altura de coronación
                    }
                    
                    # Generar el gráfico del muro para Coulomb
                    datos_coulomb_grafico = {
                        'beta': resultados_coulomb['beta'],
                        'alpha': datos_entrada_coulomb['alpha'],
                        'delta': datos_entrada_coulomb['delta'],
                        'Ka': resultados_coulomb['Ka'],
                        'H_efectiva': resultados_coulomb['H_efectiva']
                    }
                    fig_muro_coulomb = dibujar_muro_streamlit(dimensiones_coulomb, datos_entrada_coulomb['h1'], 0.5, datos_entrada_coulomb['S_c'], "coulomb", datos_coulomb_grafico)
                    
                    # Mostrar el gráfico en Streamlit
                    st.pyplot(fig_muro_coulomb)
                    
                    # Información adicional sobre el gráfico
                    st.markdown("""
                    **Leyenda del Gráfico - Análisis Coulomb:**
                    - 🔵 **Zapata (Azul claro):** Base de cimentación del muro
                    - 🔴 **Muro (Rosa):** Estructura principal de contención (inclinada según β)
                    - 🟡 **Relleno (Amarillo):** Material de relleno detrás del muro
                    - 🟤 **Suelo (Marrón):** Suelo de cimentación
                    - 🔴 **Flechas rojas:** Sobrecarga aplicada (S/c)
                    - 🔵 **Dimensiones en azul:** Medidas calculadas del muro
                    - 📐 **Ángulo β:** Inclinación del muro respecto a la vertical
                    - 📐 **Ángulo α:** Inclinación del terreno natural
                    - 📐 **Ángulo δ:** Fricción entre muro y relleno
                    """)
                    
                    # Información técnica adicional
                    st.info("""
                    **Explicación de Parámetros:**
                    - **H:** Altura total del muro de contención
                    - **H':** Altura efectiva que incluye el efecto de la inclinación del terreno
                    - **β:** Ángulo de inclinación del muro respecto a la vertical
                    - **α:** Ángulo de inclinación del terreno natural
                    - **δ:** Ángulo de fricción entre el muro y el relleno
                    """)
            else:
                st.warning("⚠️ No hay resultados disponibles para el método seleccionado.")

    elif opcion == "ℹ️ Acerca de":
        st.title("Acerca de CONSORCIO DEJ")
        st.write("""
        ### 🏗️ CONSORCIO DEJ
        **Ingeniería y Construcción Especializada**
        
        Esta aplicación fue desarrollada para facilitar el cálculo y diseño de muros de contención
        utilizando métodos reconocidos en ingeniería geotécnica.
        
        **Características del Plan Gratuito:**
        - ✅ Cálculos básicos de estabilidad
        - ✅ Resultados simples con gráficos
        - ✅ Reporte básico descargable
        - ✅ Análisis de factor de seguridad
        
        **Características del Plan Premium:**
        - ⭐ **Análisis completo con teoría de Rankine** (NUEVO)
        - ⭐ **Análisis completo con teoría de Coulomb** (NUEVO)
        - ⭐ Cálculos de dimensiones automáticos
        - ⭐ **Diseño y verificación del fuste del muro**
        - ⭐ **Cálculo de refuerzo estructural**
        - ⭐ **Reportes técnicos en PDF**
        - ⭐ Gráficos avanzados y visualizaciones
        - ⭐ Verificaciones de estabilidad completas
        - ⭐ **Altura de coronación optimizada**
        - ⭐ **Botones específicos para cada fórmula** (NUEVO)
        - ⭐ **Comparación Rankine vs Coulomb** (NUEVO)
        
        **Métodos de Análisis Disponibles:**
        
        **🔬 Teoría de Rankine:**
        - Muro vertical liso
        - No considera fricción muro-suelo
        - Fórmulas más simples
        - Aproximación conservadora
        - Ka = tan²(45° - φ/2)
        
        **🔬 Teoría de Coulomb:**
        - Considera fricción muro-suelo (δ)
        - Muro inclinado
        - Fórmulas más complejas
        - Más realista para muros rugosos
        - Ka = f(β, φ, δ, α)
        
        **Desarrollado con:** Python, Streamlit, Plotly
        **Normativas:** Aplicación de las teorías de Rankine y Coulomb para muros de contención
        """)

    elif opcion == "✉️ Contacto":
        st.title("Contacto")
        st.write("""
        ### 🏗️ CONSORCIO DEJ
        **Información de Contacto:**
        
        📧 Email: contacto@consorciodej.com  
        📱 Teléfono: +123 456 7890  
        🌐 Web: www.consorciodej.com  
        📍 Dirección: [Tu dirección aquí]
        
        **Horarios de Atención:**
        Lunes a Viernes: 8:00 AM - 6:00 PM
        
        **Servicios:**
        - Diseño de muros de contención
        - Análisis geotécnico
        - Ingeniería estructural
        - Construcción especializada
        """)

    # Mostrar plan actual en sidebar
    if st.session_state['plan'] == "gratuito":
        st.sidebar.info("🆓 Plan Gratuito - Funciones limitadas")
        st.sidebar.write("Para acceder a todas las funciones, actualiza a Premium")
        
        # Información sobre cómo acceder al plan premium
        st.sidebar.markdown("---")
        st.sidebar.subheader("🔑 Acceso Premium")
        st.sidebar.write("**Usuario:** premium")
        st.sidebar.write("**Contraseña:** premium")
        st.sidebar.info("Cierra sesión y vuelve a iniciar con las credenciales premium")
    else:
        st.sidebar.success("⭐ Plan Premium - Acceso completo")
        
        # Información para administradores
        st.sidebar.markdown("---")
        st.sidebar.subheader("👨‍💼 Panel de Administrador")
        st.sidebar.write("**Usuario actual:** " + st.session_state['user'])
        st.sidebar.write("**Plan:** Premium")
        st.sidebar.success("Acceso completo a todas las funciones")