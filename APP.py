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
# ─── Tema AURUS PRIME / Rappi (negro · dorado) ───────────────────────────────
GOLD = "#D4AF37"
GOLD_LIGHT = "#FFD700"
GOLD_DARK = "#8B6914"
BG_DARK = "#0a0a0a"
BG_CARD = "#141414"
BG_PANEL = "#111111"

APP_OPCIONES = [
    "🏗️ Cálculo Básico",
    "📊 Análisis Completo (Rankine)",
    "🔬 Análisis Coulomb",
    "🏗️ Diseño del Fuste",
    "📄 Generar Reporte",
    "📈 Gráficos",
    "ℹ️ Acerca de",
    "✉️ Contacto",
]

SIDEBAR_SECCIONES = [
    ("Restaurantes", APP_OPCIONES[0]),
    ("Supermercados", APP_OPCIONES[1]),
    ("Farmacia", APP_OPCIONES[2]),
    ("Express", APP_OPCIONES[3]),
    ("Rappi mall", APP_OPCIONES[4]),
    ("Licores", APP_OPCIONES[5]),
    ("Rappi Travel", APP_OPCIONES[6]),
    ("Turbo-Fresh", APP_OPCIONES[7]),
    ("Regalos", "💰 Planes y Precios"),
]

def inject_aurus_theme():
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&display=swap');
    html, body, [class*="css"] {{ font-family: 'Poppins', sans-serif !important; }}
    .stApp {{ background: {BG_DARK}; color: #f5f5f5; }}
    [data-testid="stHeader"] {{ background: transparent !important; }}
    [data-testid="stToolbar"], [data-testid="stDecoration"] {{ display: none !important; }}
    footer {{ visibility: hidden !important; }}
    .block-container {{ padding-top: 0.5rem !important; max-width: 100% !important; }}
    [data-testid="stSidebar"] {{
        background: #ffffff !important;
        border-right: 1px solid #eee;
        min-width: 300px !important;
        max-width: 320px !important;
    }}
    [data-testid="stSidebar"] * {{ color: #1a1a1a !important; }}
    [data-testid="stSidebar"] .stButton > button {{
        background: transparent !important;
        color: #1a1a1a !important;
        border: none !important;
        border-radius: 0 !important;
        box-shadow: none !important;
        font-weight: 600 !important;
        text-align: left !important;
        padding: 10px 0 !important;
        width: 100% !important;
        justify-content: flex-start !important;
    }}
    [data-testid="stSidebar"] .stButton > button:hover {{
        background: #f5f5f5 !important;
        color: {GOLD_DARK} !important;
    }}
    [data-testid="stSidebar"] hr {{ border-color: #eee !important; margin: 12px 0 !important; }}
    .main .stButton > button {{
        background: linear-gradient(135deg, {GOLD_LIGHT}, {GOLD}) !important;
        color: #0a0a0a !important;
        border: none !important;
        border-radius: 999px !important;
        font-weight: 700 !important;
    }}
    [data-testid="stTextInput"] input,
    [data-testid="stNumberInput"] input {{
        background: #fff !important;
        color: #333 !important;
        border: 1px solid #ddd !important;
        border-radius: 8px !important;
    }}
    [data-testid="stMainBlockContainer"] h1,
    [data-testid="stMainBlockContainer"] h2,
    [data-testid="stMainBlockContainer"] h3,
    [data-testid="stMainBlockContainer"] p,
    [data-testid="stMainBlockContainer"] label {{
        color: #f0e6c8 !important;
    }}
    .rappi-nav {{
        display: flex; align-items: center; justify-content: space-between;
        gap: 16px; padding: 12px 32px; background: #fff;
        border-bottom: 1px solid #eee; flex-wrap: wrap;
    }}
    .rappi-logo {{ font-size: 2rem; font-weight: 800; color: {GOLD}; letter-spacing: -1px; }}
    .rappi-loc {{ display: flex; align-items: center; gap: 6px; color: #333; font-weight: 600; font-size: 0.9rem; }}
    .rappi-search {{
        display: flex; align-items: center; flex: 1; max-width: 560px;
        background: #f5f5f5; border-radius: 8px; padding: 10px 16px; margin: 0 auto;
    }}
    .rappi-search input {{ border: none; background: transparent; flex: 1; font-size: 0.92rem; color: #888; outline: none; width: 100%; }}
    .rappi-hero-greet {{
        background: linear-gradient(135deg, #1a1408 0%, {GOLD_DARK} 40%, {GOLD} 100%);
        padding: 48px 32px 56px; text-align: center;
    }}
    .rappi-hero-greet h1 {{ color: #fff !important; font-size: 2.4rem; font-weight: 700; margin-bottom: 24px; }}
    .rappi-loc-box {{
        max-width: 520px; margin: 0 auto; background: #fff; border-radius: 8px;
        padding: 16px 20px; display: flex; align-items: center; gap: 12px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.15); text-align: left;
    }}
    .rappi-loc-box span {{ color: #999; font-size: 0.95rem; }}
    .rappi-loc-link {{ color: #fff; font-size: 0.88rem; margin-top: 14px; display: inline-flex; align-items: center; gap: 6px; opacity: 0.95; }}
    .rappi-section {{ padding: 32px 32px 16px; background: {BG_DARK}; }}
    .rappi-section-white {{ padding: 32px; background: #121212; }}
    .rappi-h2 {{ font-size: 1.15rem; font-weight: 700; color: #fff !important; margin-bottom: 18px; }}
    .rappi-h2-sm {{ font-size: 0.95rem; font-weight: 700; color: #ccc !important; margin-bottom: 14px; }}
    .rappi-tags {{ display: flex; flex-wrap: wrap; gap: 10px; }}
    .rappi-tag {{
        background: #1e1e1e; border: 1px solid #333; border-radius: 999px;
        padding: 8px 18px; font-size: 0.88rem; color: #eee; font-weight: 500;
    }}
    .rappi-services {{
        display: flex; gap: 20px; overflow-x: auto; padding-bottom: 12px;
        scrollbar-width: thin;
    }}
    .rappi-svc {{
        flex: 0 0 90px; text-align: center;
    }}
    .rappi-svc-icon {{
        width: 72px; height: 72px; border-radius: 16px; background: #1a1a1a;
        border: 1px solid rgba(212,175,55,0.25); display: flex; align-items: center;
        justify-content: center; font-size: 2rem; margin: 0 auto 8px;
    }}
    .rappi-svc-label {{ font-size: 0.72rem; color: {GOLD} !important; font-weight: 600; line-height: 1.2; }}
    .rappi-brands {{ display: flex; gap: 16px; overflow-x: auto; padding-bottom: 8px; }}
    .rappi-brand {{ flex: 0 0 72px; text-align: center; }}
    .rappi-brand-circle {{
        width: 64px; height: 64px; border-radius: 50%; background: #fff;
        display: flex; align-items: center; justify-content: center;
        font-size: 1.6rem; margin: 0 auto 6px; border: 2px solid #eee;
    }}
    .rappi-brand-name {{ font-size: 0.68rem; color: {GOLD} !important; font-weight: 600; }}
    .rappi-join-title {{ text-align: center; font-size: 2rem; font-weight: 700; color: #fff !important; margin: 40px 0 28px; }}
    .rappi-join-title em {{ color: {GOLD}; font-style: normal; }}
    .rappi-cards {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; max-width: 1100px; margin: 0 auto; }}
    @media (max-width: 900px) {{ .rappi-cards {{ grid-template-columns: 1fr; }} }}
    .rappi-card {{
        background: #161616; border-radius: 12px; overflow: hidden;
        border: 1px solid rgba(212,175,55,0.2); text-align: center;
    }}
    .rappi-card img {{ width: 100%; height: 160px; object-fit: cover; }}
    .rappi-card h3 {{ font-size: 1rem; font-weight: 700; color: #fff !important; padding: 16px 12px 8px; }}
    .rappi-card p {{ font-size: 0.82rem; color: #aaa !important; padding: 0 16px 16px; line-height: 1.45; }}
    .rappi-card-btn {{
        display: block; margin: 0 16px 20px; padding: 12px;
        background: rgba(212,175,55,0.15); color: {GOLD} !important;
        border-radius: 8px; font-weight: 700; font-size: 0.88rem; text-decoration: none;
        border: 1px solid rgba(212,175,55,0.35);
    }}
    .rappi-float-promo {{
        position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%);
        z-index: 999; display: flex; align-items: center; gap: 10px;
        background: linear-gradient(90deg, {GOLD_DARK}, {GOLD});
        color: #0a0a0a; padding: 14px 28px; border-radius: 8px;
        font-weight: 700; font-size: 0.92rem; box-shadow: 0 8px 32px rgba(212,175,55,0.45);
        white-space: nowrap;
    }}
    .rappi-float-badge {{
        background: #0a0a0a; color: {GOLD_LIGHT}; width: 32px; height: 32px;
        border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 800;
    }}
    .rappi-footer {{
        display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px;
        padding: 40px 32px; background: #080808; border-top: 1px solid #222;
    }}
    @media (max-width: 768px) {{ .rappi-footer {{ grid-template-columns: 1fr; }} }}
    .rappi-footer h4 {{ font-size: 0.82rem; font-weight: 700; color: {GOLD} !important; margin-bottom: 12px; }}
    .rappi-footer p {{ font-size: 0.78rem; color: #888 !important; line-height: 1.6; }}
    .sb-header {{ display: flex; justify-content: space-between; align-items: center; padding: 8px 0 16px; }}
    .sb-logo {{ font-size: 1.8rem; color: {GOLD}; font-weight: 800; }}
    .sb-close {{ width: 32px; height: 32px; border-radius: 50%; background: #eee; display: flex; align-items: center; justify-content: center; color: #666; font-size: 0.9rem; }}
    .sb-user {{ display: flex; align-items: center; gap: 12px; padding: 12px 0; }}
    .sb-avatar {{ width: 44px; height: 44px; border-radius: 50%; background: rgba(212,175,55,0.2); color: {GOLD_DARK}; font-weight: 800; font-size: 1.1rem; display: flex; align-items: center; justify-content: center; }}
    .sb-hello {{ font-size: 0.95rem; font-weight: 700; color: #1a1a1a !important; }}
    .sb-star {{ color: {GOLD}; font-size: 0.75rem; }}
    .sb-promo-box {{
        background: rgba(212,175,55,0.12); border-radius: 10px; padding: 14px 16px;
        display: flex; align-items: center; gap: 12px; margin: 12px 0;
        border: 1px solid rgba(212,175,55,0.25);
    }}
    .sb-promo-box span {{ font-size: 0.88rem; font-weight: 700; color: {GOLD_DARK} !important; }}
    .sb-label {{ font-size: 0.68rem; font-weight: 700; color: #999 !important; letter-spacing: 0.5px; text-transform: uppercase; margin: 16px 0 8px; }}
    .sb-row {{ display: flex; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid #f0f0f0; font-size: 0.88rem; font-weight: 600; color: #1a1a1a !important; }}
    .sb-row .chev {{ color: #ccc; font-size: 0.8rem; }}
    .sb-vermas {{ color: {GOLD_DARK}; font-weight: 700; font-size: 0.88rem; padding: 10px 0; }}
    .sb-credits {{ display: flex; justify-content: space-between; padding: 8px 0; font-size: 0.88rem; }}
    .sb-credits strong {{ font-weight: 800; }}
    .sb-logout {{ color: #999 !important; font-size: 0.85rem; padding: 16px 0 8px; }}
    .rappi-auth-wrap {{
        max-width: 480px; margin: 24px auto 80px; padding: 28px;
        background: #161616; border-radius: 16px; border: 1px solid rgba(212,175,55,0.3);
    }}
    .rappi-auth-wrap h3 {{ color: {GOLD_LIGHT} !important; text-align: center; font-size: 1.2rem; }}
    .rappi-main-bar {{
        padding: 10px 24px; background: #fff; border-bottom: 1px solid #eee; margin-bottom: 0;
    }}
    .rappi-main-bar .rappi-logo {{ font-size: 1.5rem; }}
    .rappi-top-promo {{
        display: flex; align-items: center; justify-content: center; flex-wrap: wrap; gap: 16px;
        padding: 10px 24px; background: linear-gradient(90deg, #0a0a0a, #1a1408, #0a0a0a);
        border-bottom: 1px solid rgba(212,175,55,0.3); color: #fff; font-size: 0.9rem;
    }}
    .rappi-content-panel {{
        background: #f8f8f8; border-radius: 12px; padding: 24px; margin: 16px 24px;
        border: 1px solid #eee;
    }}
    .rappi-content-panel h1, .rappi-content-panel h2, .rappi-content-panel h3,
    .rappi-content-panel p, .rappi-content-panel label, .rappi-content-panel span {{
        color: #1a1a1a !important;
    }}
    </style>
    """, unsafe_allow_html=True)

def render_rappi_navbar(location="Ingresar mi ubicación", search_ph="Comida, restaurantes, tiendas, productos..."):
    st.markdown(f"""
    <div class="rappi-nav">
        <div style="display:flex;align-items:center;gap:20px;">
            <div class="rappi-logo">Rappi</div>
            <div class="rappi-loc">📍 {location} ▾</div>
        </div>
        <div class="rappi-search">
            <span style="margin-right:8px;color:{GOLD};">🥸</span>
            <input type="text" placeholder="{search_ph}" readonly />
            <span style="margin-left:8px;color:#aaa;">🔍</span>
        </div>
        <div style="width:36px;height:36px;border-radius:50%;background:#eee;display:flex;align-items:center;justify-content:center;">👤</div>
    </div>
    """, unsafe_allow_html=True)

def render_greeting_hero():
    st.markdown("""
    <div class="rappi-hero-greet">
        <h1>Hola, buenos días.</h1>
        <div class="rappi-loc-box">
            <span>📍</span>
            <span>¿Dónde quieres recibir tu compra?</span>
        </div>
        <div class="rappi-loc-link">🎯 Usa tu ubicación actual</div>
    </div>
    """, unsafe_allow_html=True)

def render_service_categories():
    services = [
        ("🍔", "Restaurantes"), ("🛒", "Supermercados"), ("💊", "Farmacia"),
        ("🛍️", "Express"), ("🏬", "Rappi mall"), ("🍾", "Licores"),
        ("📦", "La Cesta"), ("✈️", "Rappi Travel"), ("⚡", "Turbo"), ("🎁", "Regalos"),
    ]
    items = "".join(
        f'<div class="rappi-svc"><div class="rappi-svc-icon">{icon}</div><div class="rappi-svc-label">{label} ›</div></div>'
        for icon, label in services
    )
    st.markdown(f"""
    <div class="rappi-section-white">
        <div class="rappi-h2">¿Necesitas algo más?</div>
        <div class="rappi-services">{items}</div>
    </div>
    """, unsafe_allow_html=True)

def render_trending_tags():
    tags = ["Mundial", "Makis", "Gaseosa", "Cerveza", "Pizza", "Snack", "Pollo a la brasa", "Chifa", "Pollo", "Postres"]
    tag_html = "".join(f'<span class="rappi-tag">{t}</span>' for t in tags)
    st.markdown(f"""
    <div class="rappi-section">
        <div class="rappi-h2-sm">Lo más buscado</div>
        <div class="rappi-tags">{tag_html}</div>
    </div>
    """, unsafe_allow_html=True)

def render_top_brands():
    brands = [
        ("🍟", "McDonald's"), ("🍔", "Bembos"), ("🍗", "Popeyes"), ("🍕", "Papa John's"),
        ("🥡", "China Wok"), ("🍗", "KFC"), ("🍕", "Little Caesars"), ("🍽️", "Fridays"),
        ("🍩", "Dunkin'"), ("🥪", "Subway"),
    ]
    items = "".join(
        f'<div class="rappi-brand"><div class="rappi-brand-circle">{icon}</div><div class="rappi-brand-name">{name}</div></div>'
        for icon, name in brands
    )
    st.markdown(f"""
    <div class="rappi-section">
        <div class="rappi-h2-sm">¡Los 10 más elegidos!</div>
        <div class="rappi-brands">{items}</div>
    </div>
    """, unsafe_allow_html=True)

def render_join_section():
    st.markdown(f"""
    <div class="rappi-section">
        <div class="rappi-join-title">Únete a <em>Rappi</em></div>
        <div class="rappi-cards">
            <div class="rappi-card">
                <img src="https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=400&q=80" alt="Restaurante"/>
                <h3>Registra tu restaurante</h3>
                <p>Únete a la red de restaurantes más grande de Latinoamérica y recibe más pedidos.</p>
                <span class="rappi-card-btn">Conocer más</span>
            </div>
            <div class="rappi-card">
                <img src="https://images.unsplash.com/photo-1441986300917-64674bd600d8?w=400&q=80" alt="Comercio"/>
                <h3>Registra tu comercio</h3>
                <p>Vende tus productos en Rappi y llega a miles de clientes en tu ciudad.</p>
                <span class="rappi-card-btn">Conocer más</span>
            </div>
            <div class="rappi-card">
                <img src="https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=400&q=80" alt="Repartidor"/>
                <h3>¡Únete como repartidor!</h3>
                <p>Genera ingresos extras entregando pedidos con horarios flexibles.</p>
                <span class="rappi-card-btn">¡Regístrate ahora!</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_floating_promo():
    st.markdown("""
    <div class="rappi-float-promo">
        <div class="rappi-float-badge">%</div>
        Descubre las <strong>PROMOCIONES</strong> que tenemos para ti
    </div>
    """, unsafe_allow_html=True)

def render_footer():
    st.markdown("""
    <div class="rappi-footer">
        <div>
            <h4>Top Marcas y Cadenas de Restaurantes</h4>
            <p>McDonald's · Bembos · KFC · Papa John's · China Wok · Little Caesars · Dunkin' · Subway</p>
        </div>
        <div>
            <h4>Encuéntranos en estos países</h4>
            <p>Perú · Colombia · México · Brasil · Chile · Argentina · Ecuador · Uruguay · Costa Rica</p>
        </div>
        <div>
            <h4>Pide tu comida favorita cerca de ti</h4>
            <p>Arequipa · Lima · Cusco · Trujillo · Piura · Chiclayo · Iquitos · Huancayo</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_rappi_sidebar(user_name="GRUPO", logged_in=False, show_all_sections=True):
    initial = user_name[0].upper() if user_name else "G"
    st.sidebar.markdown(f"""
    <div class="sb-header">
        <div class="sb-logo">🥸</div>
        <div class="sb-close">✕</div>
    </div>
    <div class="sb-user">
        <div class="sb-avatar">{initial}</div>
        <div>
            <div class="sb-hello">Hola, <strong>{user_name.upper()}</strong></div>
            <div class="sb-star">⭐</div>
        </div>
    </div>
    <div class="sb-promo-box">
        <span>🏷️⚽</span>
        <span>Descubre nuestras promociones</span>
    </div>
    """, unsafe_allow_html=True)

    st.sidebar.markdown('<div class="sb-label">Secciones</div>', unsafe_allow_html=True)
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

    if show_all_sections:
        st.sidebar.markdown('<div class="sb-vermas">Ver menos</div>', unsafe_allow_html=True)
    else:
        st.sidebar.markdown('<div class="sb-vermas">Ver más</div>', unsafe_allow_html=True)

    st.sidebar.markdown("---")
    st.sidebar.markdown('<div class="sb-label">Promociones y créditos:</div>', unsafe_allow_html=True)
    st.sidebar.markdown("""
    <div class="sb-credits"><span>Créditos</span><strong>S/ 0.00</strong></div>
    """, unsafe_allow_html=True)

    st.sidebar.markdown('<div class="sb-label">Tu perfil:</div>', unsafe_allow_html=True)
    for item in ["Información de mi cuenta", "Métodos de pagos", "Últimas órdenes"]:
        st.sidebar.markdown(f'<div class="sb-row"><span>{item}</span><span class="chev">›</span></div>', unsafe_allow_html=True)

    st.sidebar.markdown('<div class="sb-label">Otros</div>', unsafe_allow_html=True)
    for item in ["Registra tu restaurante", "Registra tu tienda", "Quiero ser Rappitender@", "Pauta en Rappi"]:
        st.sidebar.markdown(f'<div class="sb-row"><span>{item}</span><span class="chev">›</span></div>', unsafe_allow_html=True)

    st.sidebar.markdown("""
    <div class="sb-row"><span>🇵🇪 Perú</span><span class="chev">›</span></div>
    """, unsafe_allow_html=True)

def render_top_promo_banner():
    if st.session_state.get("promo_dismissed"):
        return
    st.markdown("""
    <div class="rappi-top-promo">
        <span>🛵</span>
        <span><strong>¿Nuevo en Rappi?</strong> Disfruta de envíos gratis por semanas</span>
    </div>
    """, unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns([3, 1, 1, 0.3])
    with c2:
        if st.button("Registrarme", key="top_promo_reg"):
            st.session_state["auth_tab"] = "register"
            st.rerun()
    with c3:
        st.markdown('<p style="text-align:center;margin-top:6px;font-size:0.82rem;"><a href="#" style="color:#fff;">Términos y condiciones</a></p>', unsafe_allow_html=True)
    with c4:
        if st.button("✕", key="top_promo_close"):
            st.session_state["promo_dismissed"] = True
            st.rerun()

def render_app_navbar(subtitle="Diseño y Análisis de Muros de Contención"):
    st.markdown(f"""
    <div class="rappi-main-bar">
        <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px;">
            <div class="rappi-logo">Rappi</div>
            <div style="color:#666;font-size:0.85rem;font-weight:500;">{subtitle}</div>
            <div class="rappi-loc">📍 Arequipa ▾</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

st.set_page_config(
    page_title="Rappi - AURUS PRIME",
    page_icon="🥸",
    layout="wide",
    initial_sidebar_state="expanded"
)

inject_aurus_theme()

# Sistema de autenticación y pagos
def show_pricing_page():
    """Mostrar página de precios y planes"""
    st.title("💰 Planes y Precios - AURUS PRIME")
    
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
    render_rappi_sidebar(user_name="GRUPO", logged_in=False, show_all_sections=True)
    render_rappi_navbar()
    render_top_promo_banner()
    render_greeting_hero()
    render_service_categories()
    render_floating_promo()
    render_trending_tags()
    render_top_brands()
    render_join_section()
    render_footer()

    st.markdown('<div class="rappi-auth-wrap">', unsafe_allow_html=True)
    st.markdown("### Ingreso a la aplicación")
    st.markdown("<p style='text-align:center;color:#888;font-size:0.85rem;'>Muros de contención · Rankine · Coulomb · Reportes PDF</p>", unsafe_allow_html=True)

    if "auth_tab" not in st.session_state:
        st.session_state["auth_tab"] = "login"

    auth_options = ["login", "register", "pricing"]
    auth_labels = {"login": "Iniciar Sesión", "register": "Registrarse", "pricing": "Planes y Precios"}
    current = st.session_state.get("auth_tab", "login")
    if current not in auth_options:
        current = "login"
    selected = st.radio(
        "Sección",
        auth_options,
        format_func=lambda x: auth_labels[x],
        index=auth_options.index(current),
        horizontal=True,
        label_visibility="collapsed",
        key="auth_section_radio",
    )
    st.session_state["auth_tab"] = selected

    if selected == "login":
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

    elif selected == "register":
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

    elif selected == "pricing":
        show_pricing_page()

    st.markdown('</div>', unsafe_allow_html=True)

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
    if "promo_dismissed" not in st.session_state:
        st.session_state["promo_dismissed"] = False
    show_auth_page()
else:
    render_app_navbar()
    plan_updated = update_user_plan()
    if plan_updated:
        st.success("🎉 ¡Tu plan ha sido actualizado!")
        st.rerun()

    user_data = st.session_state.get('user_data', {})
    plan = user_data.get('plan', 'gratuito')
    user_name = user_data.get('name') or user_data.get('username') or st.session_state.get('user', 'Usuario')

    if 'opcion' not in st.session_state:
        st.session_state['opcion'] = APP_OPCIONES[0]
    if 'show_pricing' not in st.session_state:
        st.session_state['show_pricing'] = False

    render_rappi_sidebar(user_name=str(user_name), logged_in=True, show_all_sections=True)

    st.sidebar.markdown(f"""
    <div class="sb-credits"><span>Plan actual</span><strong>{plan.title()}</strong></div>
    """, unsafe_allow_html=True)

    if st.sidebar.button("Cerrar sesión", key="sb_logout"):
        st.session_state['logged_in'] = False
        st.session_state['user_data'] = None
        st.session_state['user'] = None
        st.session_state['plan'] = None
        st.session_state['opcion'] = APP_OPCIONES[0]
        st.session_state['show_pricing'] = False
        st.rerun()

    is_admin = st.session_state.get('user') == 'admin'
    if is_admin:
        st.sidebar.markdown("---")
        st.sidebar.markdown('<div class="sb-label">Panel administrador</div>', unsafe_allow_html=True)
        c1, c2, c3 = st.sidebar.columns(3)
        with c1:
            if st.button("Gratuito", key="sidebar_free"):
                st.session_state['plan'] = "gratuito"
                if 'user_data' in st.session_state:
                    st.session_state['user_data']['plan'] = "gratuito"
                st.rerun()
        with c2:
            if st.button("Premium", key="sidebar_premium"):
                st.session_state['plan'] = "premium"
                if 'user_data' in st.session_state:
                    st.session_state['user_data']['plan'] = "premium"
                st.rerun()
        with c3:
            if st.button("Empresarial", key="sidebar_enterprise"):
                st.session_state['plan'] = "empresarial"
                if 'user_data' in st.session_state:
                    st.session_state['user_data']['plan'] = "empresarial"
                st.rerun()

    opcion = st.session_state.get('opcion', APP_OPCIONES[0])

    if st.session_state.get('show_pricing', False):
        show_pricing_page()
        if st.button("← Volver a la aplicación"):
            st.session_state['show_pricing'] = False
            st.rerun()
    elif opcion == "🏗️ Cálculo Básico":
        st.title("Cálculo Básico de Muro de Contención")
        st.info("Plan gratuito: Cálculos básicos de estabilidad")
        
        # Pestañas para diferentes tipos de cálculos
        tab1, tab2, tab3 = st.tabs(["📏 Dimensiones", "🏗️ Materiales", "⚖️ Cargas"])
        
 