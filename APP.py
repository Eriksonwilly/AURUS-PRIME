"""
AURUS PRIME — Luxury On-Demand Concierge Marketplace
=====================================================
Streamlit single-file application.

Author  : Generated for deployment to Streamlit Community Cloud (streamlit.io)
Stack   : Python 3.10+ / Streamlit >= 1.33
Purpose : Landing / home experience for a luxury delivery marketplace
          (boutiques, gourmet, pharmacy, express couriers, wine cellar,
          travel and curated gifting) inspired structurally by common
          quick-commerce apps, redesigned end-to-end for a premium,
          "old-money" luxury audience.

Design tokens (see DESIGN SYSTEM section below):
    Background : #0B0B0C (obsidian)
    Panel      : #141416 (graphite)
    Gold       : #C9A227 (antique gold)  /  #E8CD7A (gold light)
    Ivory      : #F5F1E8
    Champagne  : #EFE6D8
    Muted text : #A8A29B
    Divider    : rgba(201,162,39,0.25)

    Display face : "Playfair Display" (serif, headlines)
    Accent face  : "Cormorant Garamond" (serif italic, quotes/eyebrows)
    Utility face : "Inter" (sans, UI chrome / labels / body)

Run locally:
    pip install -r requirements.txt
    streamlit run app.py

Deploy:
    1. Push this repo to GitHub (app.py + requirements.txt + .streamlit/config.toml)
    2. Go to https://share.streamlit.io -> "New app"
    3. Point it at your repo / branch / app.py
    4. Deploy. Done.
"""

import streamlit as st
from datetime import datetime

# =============================================================================
# 1. PAGE CONFIGURATION — must be the first Streamlit call
# =============================================================================
st.set_page_config(
    page_title="Aurus Prime | Concierge de Lujo a Domicilio",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =============================================================================
# 2. DATA — content model (edit here to change copy / catalog without
#    touching layout code)
# =============================================================================

BRAND_NAME = "AURUS PRIME"
BRAND_MONOGRAM = "AP"

CITIES = ["Arequipa", "Lima", "Cusco", "Trujillo", "Piura"]

CATEGORIES = [
    {"icon": "🛍️", "name": "Boutiques",        "desc": "Moda y accesorios de autor"},
    {"icon": "💊", "name": "Farmacia Prime",   "desc": "Bienestar y cuidado premium"},
    {"icon": "⚡", "name": "Aurus Express",    "desc": "Entrega inmediata, 30 min"},
    {"icon": "🏛️", "name": "Aurus Mall",       "desc": "Casas de lujo bajo un mismo techo"},
    {"icon": "🍷", "name": "La Cava",          "desc": "Vinos y espirituosos selectos"},
    {"icon": "🧺", "name": "La Cesta Gourmet", "desc": "Delicatessen y alta despensa"},
    {"icon": "✈️", "name": "Aurus Travel",     "desc": "Experiencias y reservas exclusivas"},
    {"icon": "🌿", "name": "Aurus Fresh",      "desc": "Mercado fino en 15 minutos"},
    {"icon": "🎁", "name": "Regalos Selectos", "desc": "Obsequios curados para cada ocasión"},
]

TRENDING_TAGS = ["Champagne", "Alta Relojería", "Trufa Negra", "Seda", "Cuero Italiano", "Caviar", "Perfumería Niche"]

FEATURED_HOUSES = [
    "Maison Verlaine", "Château Bistro", "Le Bernardin Express", "Orsini Gioielli",
    "Nord Atelier", "Casa Dorado", "Villa Cachemira", "L'Or Noir", "Ámbar & Cedro", "Silvana Home",
]

JOIN_CARDS = [
    {
        "icon": "🏷️",
        "title": "Registra tu boutique",
        "body": "Súmate a un círculo selecto de firmas y llega a una clientela exigente en todo el país.",
        "cta": "Conocer más",
    },
    {
        "icon": "🍽️",
        "title": "Registra tu casa gourmet",
        "body": "Lleva tu propuesta culinaria a la mesa de quienes buscan excelencia, sin salir de tu cocina.",
        "cta": "Conocer más",
    },
    {
        "icon": "🎩",
        "title": "Sé Aurus Courier",
        "body": "Entregas de alto estándar, tarifas preferentes y el respaldo de una marca premium.",
        "cta": "Postular ahora",
    },
]

# =============================================================================
# 3. SESSION STATE
# =============================================================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_name" not in st.session_state:
    st.session_state.user_name = "Invitado"
if "city" not in st.session_state:
    st.session_state.city = CITIES[0]
if "cart_count" not in st.session_state:
    st.session_state.cart_count = 0


def greeting() -> str:
    """Return a time-appropriate greeting, in the voice of a concierge."""
    hour = datetime.now().hour
    if hour < 12:
        return "Buenos días"
    if hour < 19:
        return "Buenas tardes"
    return "Buenas noches"


# =============================================================================
# 4. DESIGN SYSTEM — fonts, colors, component CSS
# =============================================================================
CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,500;0,600;0,700;1,500&family=Cormorant+Garamond:ital,wght@0,500;1,500&family=Inter:wght@400;500;600&display=swap');

:root{
    --bg:            #0B0B0C;
    --panel:         #141416;
    --panel-raised:  #1A1A1D;
    --gold:          #C9A227;
    --gold-light:    #E8CD7A;
    --ivory:         #F5F1E8;
    --champagne:     #EFE6D8;
    --muted:         #A8A29B;
    --divider:       rgba(201,162,39,0.25);
}

/* ---------- global resets ---------- */
html, body, [class*="css"]  { font-family: 'Inter', sans-serif; }
.stApp { background-color: var(--bg); color: var(--ivory); }
#MainMenu, footer, header[data-testid="stHeader"] { visibility: hidden; height:0; }
.block-container { padding-top: 1.2rem; padding-bottom: 3rem; max-width: 1180px; }

h1, h2, h3 { font-family: 'Playfair Display', serif !important; color: var(--ivory); letter-spacing: 0.3px; }

/* ---------- eyebrow / small caps labels ---------- */
.eyebrow {
    font-family: 'Inter', sans-serif;
    text-transform: uppercase;
    letter-spacing: 3px;
    font-size: 0.72rem;
    color: var(--gold-light);
    font-weight: 600;
    margin-bottom: 6px;
}

/* ---------- top bar ---------- */
.topbar {
    display:flex; align-items:center; justify-content:space-between;
    padding: 10px 4px 18px 4px; border-bottom: 1px solid var(--divider); margin-bottom: 18px;
}
.brand {
    font-family: 'Playfair Display', serif; font-weight:700; font-size: 1.55rem;
    letter-spacing: 2px; color: var(--ivory);
}
.brand span { color: var(--gold); }
.brand-tag { font-family:'Cormorant Garamond', serif; font-style: italic; color: var(--muted); font-size: 0.95rem; margin-left:10px;}

/* ---------- announcement ribbon ---------- */
.ribbon {
    background: linear-gradient(90deg, #1A1A1D 0%, #0B0B0C 100%);
    border: 1px solid var(--divider);
    border-radius: 999px;
    padding: 9px 22px;
    display:flex; align-items:center; gap:10px; justify-content:center;
    font-size: 0.85rem; color: var(--champagne); margin-bottom: 26px;
    letter-spacing: 0.4px;
}
.ribbon b { color: var(--gold-light); }

/* ---------- hero ---------- */
.hero {
    background: radial-gradient(circle at 20% 20%, #1c1a12 0%, #0B0B0C 60%);
    border: 1px solid var(--divider);
    border-radius: 18px;
    padding: 56px 48px;
    text-align:center;
    margin-bottom: 34px;
}
.hero h1 { font-size: 2.7rem; margin-bottom: 4px; }
.hero p.sub { font-family:'Cormorant Garamond', serif; font-style: italic; font-size:1.25rem; color: var(--muted); margin-top:0; }

/* ---------- section headers ---------- */
.section-title { display:flex; align-items:baseline; gap:14px; margin: 38px 0 16px 0; }
.section-title h2 { font-size: 1.5rem; margin:0; }
.section-title .rule { flex:1; height:1px; background: var(--divider); }

/* ---------- category / house cards ---------- */
.card {
    background: var(--panel);
    border: 1px solid var(--divider);
    border-radius: 14px;
    padding: 20px 16px;
    text-align:center;
    transition: all .18s ease;
    height: 100%;
}
.card:hover { border-color: var(--gold); transform: translateY(-3px); }
.card .icon { font-size: 1.8rem; margin-bottom:8px; }
.card .name { font-family:'Playfair Display', serif; font-size:1.02rem; color: var(--ivory); margin-bottom:4px; }
.card .desc { font-size: 0.78rem; color: var(--muted); }

/* ---------- monogram avatar for featured houses ---------- */
.avatar-ring {
    width:64px; height:64px; border-radius:50%;
    border: 1px solid var(--gold);
    display:flex; align-items:center; justify-content:center;
    font-family:'Playfair Display', serif; color: var(--gold-light); font-size:1.1rem;
    margin: 0 auto 10px auto; background: var(--panel-raised);
}
.house-name { text-align:center; font-size:0.82rem; color: var(--champagne); }

/* ---------- chips ---------- */
.chip-row { display:flex; flex-wrap:wrap; gap:10px; margin-bottom: 6px;}
.chip {
    border:1px solid var(--divider); color: var(--champagne); border-radius:999px;
    padding: 7px 16px; font-size:0.82rem; background: var(--panel);
}

/* ---------- join cards ---------- */
.join-card {
    background: var(--panel); border:1px solid var(--divider); border-radius:16px;
    padding: 28px 24px; height:100%;
}
.join-card .icon { font-size:1.9rem; margin-bottom:10px;}
.join-card h3 { font-size:1.15rem; margin: 0 0 8px 0; }
.join-card p { color: var(--muted); font-size:0.88rem; line-height:1.5; }

/* ---------- buttons (Streamlit override) ---------- */
div.stButton > button, div.stDownloadButton > button {
    background: transparent;
    color: var(--gold-light);
    border: 1px solid var(--gold);
    border-radius: 999px;
    padding: 8px 22px;
    font-family: 'Inter', sans-serif;
    letter-spacing: 1.2px;
    text-transform: uppercase;
    font-size: 0.72rem;
    font-weight: 600;
    transition: all .18s ease;
}
div.stButton > button:hover, div.stDownloadButton > button:hover {
    background: var(--gold);
    color: #0B0B0C;
    border-color: var(--gold);
}
.stButton.primary div.stButton > button { background: var(--gold); color:#0B0B0C; }

/* ---------- inputs ---------- */
div[data-baseweb="select"] > div, .stTextInput > div > div {
    background: var(--panel) !important;
    border: 1px solid var(--divider) !important;
    color: var(--ivory) !important;
    border-radius: 10px !important;
}

/* ---------- sidebar ---------- */
section[data-testid="stSidebar"] {
    background-color: #0E0E10;
    border-right: 1px solid var(--divider);
}
section[data-testid="stSidebar"] .eyebrow { margin-top: 18px; }
section[data-testid="stSidebar"] hr { border-color: var(--divider); }

/* ---------- footer ---------- */
.footer { border-top:1px solid var(--divider); margin-top: 50px; padding-top: 24px; text-align:center; color:var(--muted); font-size:0.8rem;}
.footer .crest { font-family:'Playfair Display', serif; color: var(--gold); font-size:1.4rem; letter-spacing:3px; margin-bottom:6px;}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# =============================================================================
# 5. SIDEBAR — replicates the app's slide-out menu (sections, promotions,
#    profile, other actions, country selector, sign out)
# =============================================================================
with st.sidebar:
    st.markdown(f"<div class='brand'>✦ <span>{BRAND_MONOGRAM}</span></div>", unsafe_allow_html=True)
    st.markdown(
        f"<p style='color:var(--muted); font-family:\"Cormorant Garamond\",serif; font-style:italic;'>"
        f"Hola, {st.session_state.user_name}</p>",
        unsafe_allow_html=True,
    )

    st.markdown("<div class='eyebrow'>Secciones</div>", unsafe_allow_html=True)
    for cat in CATEGORIES:
        st.markdown(f"{cat['icon']}&nbsp;&nbsp;**{cat['name']}**", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("<div class='eyebrow'>Promociones y créditos</div>", unsafe_allow_html=True)
    col_a, col_b = st.columns([2, 1])
    col_a.markdown("Créditos Aurus")
    col_b.markdown("**S/ 0.00**")

    st.markdown("---")
    st.markdown("<div class='eyebrow'>Tu perfil</div>", unsafe_allow_html=True)
    st.markdown("Información de mi cuenta")
    st.markdown("Métodos de pago")
    st.markdown("Últimas órdenes")

    st.markdown("---")
    st.markdown("<div class='eyebrow'>Otros</div>", unsafe_allow_html=True)
    st.markdown("Registra tu boutique")
    st.markdown("Registra tu casa gourmet")
    st.markdown("Quiero ser Aurus Courier")
    st.markdown("Publicidad en Aurus Prime")

    st.markdown("---")
    st.selectbox("País", ["🇵🇪 Perú", "🇨🇴 Colombia", "🇲🇽 México", "🇨🇱 Chile"], key="country_select")

    if st.button("Cerrar sesión", key="logout_btn"):
        st.session_state.logged_in = False
        st.session_state.user_name = "Invitado"

# =============================================================================
# 6. TOP BAR — logo, location, search, account, cart
# =============================================================================
top_l, top_r = st.columns([3, 2])
with top_l:
    st.markdown(
        f"<div class='brand'>✦ AURUS<span> PRIME</span>"
        f"<span class='brand-tag'>Concierge de lujo a domicilio</span></div>",
        unsafe_allow_html=True,
    )
with top_r:
    c1, c2, c3 = st.columns([2, 3, 1])
    with c1:
        st.session_state.city = st.selectbox("Ubicación", CITIES, label_visibility="collapsed")
    with c2:
        st.text_input("Buscar", placeholder="Boutiques, gourmet, casas, productos…", label_visibility="collapsed")
    with c3:
        st.button(f"🛍 {st.session_state.cart_count}", key="cart_btn")

st.markdown("<hr style='border-color:var(--divider); margin-top:0;'>", unsafe_allow_html=True)

# =============================================================================
# 7. ANNOUNCEMENT RIBBON
# =============================================================================
st.markdown(
    "<div class='ribbon'>✦ &nbsp;¿Nuevo en Aurus Prime? Disfruta de <b>envíos de cortesía</b> "
    "en tus primeras semanas &nbsp;·&nbsp; <b>Regístrate</b></div>",
    unsafe_allow_html=True,
)

# =============================================================================
# 8. HERO
# =============================================================================
st.markdown(
    f"""
    <div class="hero">
        <div class="eyebrow" style="justify-content:center; display:flex;">Bienvenido a un nuevo estándar</div>
        <h1>{greeting()}.</h1>
        <p class="sub">¿Qué desea recibir hoy, con la discreción y el cuidado que le caracterizan?</p>
    </div>
    """,
    unsafe_allow_html=True,
)

hc1, hc2, hc3 = st.columns([1, 3, 1])
with hc2:
    st.text_input(
        "Dirección de entrega",
        placeholder=f"¿Dónde desea recibir su pedido en {st.session_state.city}?",
        label_visibility="collapsed",
    )
    b1, b2, b3 = st.columns([1, 1, 1])
    with b2:
        st.button("Usar mi ubicación actual", key="use_location")

# =============================================================================
# 9. CATEGORY GRID
# =============================================================================
st.markdown(
    "<div class='section-title'><h2>¿Qué necesita hoy?</h2><div class='rule'></div></div>",
    unsafe_allow_html=True,
)

cols = st.columns(3)
for i, cat in enumerate(CATEGORIES):
    with cols[i % 3]:
        st.markdown(
            f"""
            <div class="card">
                <div class="icon">{cat['icon']}</div>
                <div class="name">{cat['name']}</div>
                <div class="desc">{cat['desc']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.write("")  # vertical spacing between rows

# =============================================================================
# 10. TRENDING TAGS
# =============================================================================
st.markdown(
    "<div class='section-title'><h2>Lo más solicitado</h2><div class='rule'></div></div>",
    unsafe_allow_html=True,
)
chips_html = "".join(f"<span class='chip'>{tag}</span>" for tag in TRENDING_TAGS)
st.markdown(f"<div class='chip-row'>{chips_html}</div>", unsafe_allow_html=True)

# =============================================================================
# 11. FEATURED HOUSES
# =============================================================================
st.markdown(
    "<div class='section-title'><h2>Las 10 casas más elegidas</h2><div class='rule'></div></div>",
    unsafe_allow_html=True,
)
house_cols = st.columns(5)
for i, house in enumerate(FEATURED_HOUSES):
    initials = "".join([w[0] for w in house.split()[:2]]).upper()
    with house_cols[i % 5]:
        st.markdown(
            f"""
            <div class="avatar-ring">{initials}</div>
            <div class="house-name">{house}</div>
            """,
            unsafe_allow_html=True,
        )
        st.write("")

# =============================================================================
# 12. JOIN AURUS PRIME (partners / couriers)
# =============================================================================
st.markdown(
    "<div class='section-title'><h2>Únase a Aurus Prime</h2><div class='rule'></div></div>",
    unsafe_allow_html=True,
)
join_cols = st.columns(3)
for i, card in enumerate(JOIN_CARDS):
    with join_cols[i]:
        st.markdown(
            f"""
            <div class="join-card">
                <div class="icon">{card['icon']}</div>
                <h3>{card['title']}</h3>
                <p>{card['body']}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.write("")
        st.button(card["cta"], key=f"join_{i}")

# =============================================================================
# 13. FOOTER
# =============================================================================
st.markdown(
    f"""
    <div class="footer">
        <div class="crest">✦ {BRAND_MONOGRAM} ✦</div>
        <div>AURUS PRIME · Concierge de lujo a domicilio</div>
        <div style="margin-top:6px;">Términos y condiciones · Privacidad · Ayuda · © {datetime.now().year} Aurus Prime</div>
    </div>
    """,
    unsafe_allow_html=True,
)
