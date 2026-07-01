"""
AURUS PRIME — Luxury On-Demand Concierge Marketplace
=====================================================
Streamlit single-file application.

Author  : Generated for deployment to Streamlit Community Cloud (streamlit.io)
Stack   : Python 3.10+ / Streamlit >= 1.33
Purpose : Landing / home experience for a luxury delivery marketplace
          (restaurants, market, pharmacy, express couriers, wine cellar,
          travel, boutiques and curated gifting). Information architecture
          mirrors a familiar quick-commerce app (top bar with hamburger
          menu + location pill + search, a slide-out sections menu, a
          category icon row, trending tags, a "most chosen" brand strip,
          and partner/courier acquisition cards) — every visual element,
          copy line and asset is original and rebuilt end-to-end in a
          black-and-gold luxury design language for the Aurus Prime brand.

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
#    touching layout code). Order mirrors a standard quick-commerce app's
#    section list, renamed and re-imagined for a luxury clientele.
# =============================================================================

BRAND_NAME = "AURUS PRIME"
BRAND_MONOGRAM = "AP"

CITIES = ["Arequipa", "Lima", "Cusco", "Trujillo", "Piura"]

# Section catalog — one simple, clickable entry per line. Shown BOTH in the
# sidebar (with "ver más / ver menos") and as the main category icon row.
# Kept intentionally short (icon + one word) so the whole app stays easy
# to scan and tap on any screen size.
CATEGORIES = [
    {"icon": "🍽️", "name": "Restaurantes"},
    {"icon": "🛒", "name": "Supermercados"},
    {"icon": "💊", "name": "Farmacia"},
    {"icon": "⚡", "name": "Express"},
    {"icon": "🏛️", "name": "Aurus Mall"},
    {"icon": "🍷", "name": "Licores"},
    {"icon": "🧺", "name": "La Cesta Gourmet"},
    {"icon": "✈️", "name": "Aurus Travel"},
    {"icon": "🌿", "name": "Turbo-Fresh"},
    {"icon": "🎁", "name": "Regalos"},
]

# How many sections show before the "Ver más" toggle (mirrors the reference
# app's collapsed sidebar state).
SIDEBAR_COLLAPSED_COUNT = 3

TRENDING_TAGS = ["Mundial", "Champagne", "Alta Relojería", "Trufa Negra", "Seda", "Caviar", "Perfumería Niche"]

FEATURED_HOUSES = [
    "Maison Verlaine", "Château Bistro", "Le Bernardin Express", "Orsini Gioielli",
    "Nord Atelier", "Casa Dorado", "Villa Cachemira", "L'Or Noir", "Ámbar & Cedro", "Silvana Home",
]

# Muted jewel tones used to rotate the featured-house avatar backgrounds,
# giving each circle a distinct identity without breaking the luxury palette.
JEWEL_TONES = ["#3B1E23", "#1E2A26", "#241C33", "#2A2417", "#1C232E"]

# Partner / courier acquisition cards — mirrors the reference app's
# "Registra tu restaurante / Registra tu comercio / Únete como repartidor"
# module, with a photo-style gradient header instead of a stock photo.
JOIN_CARDS = [
    {
        "gradient": "linear-gradient(135deg,#3a2f16,#0B0B0C)",
        "icon": "🍽️",
        "title": "Registra tu restaurante",
        "body": "Súmate a las casas gastronómicas de mayor prestigio y llega a una clientela exigente en todo el país.",
        "cta": "Conocer más",
    },
    {
        "gradient": "linear-gradient(135deg,#241c33,#0B0B0C)",
        "icon": "🏷️",
        "title": "Registra tu boutique",
        "body": "Accede a miles de clientes Aurus Prime y disfruta de una logística inmediata sin salir de tu tienda.",
        "cta": "Conocer más",
    },
    {
        "gradient": "linear-gradient(135deg,#2a2417,#0B0B0C)",
        "icon": "🎩",
        "title": "¡Únete como Aurus Courier!",
        "body": "Entregas de alto estándar, tarifas preferentes y el respaldo de una marca premium.",
        "cta": "¡Regístrate ahora!",
    },
]

SIDEBAR_OTHERS = [
    ("🍽️", "Registra tu restaurante"),
    ("🏷️", "Registra tu tienda"),
    ("🎩", "Quiero ser Aurus Courier"),
    ("📣", "Pauta en Aurus Prime"),
]

SIDEBAR_PROFILE = [
    ("👤", "Información de mi cuenta"),
    ("💳", "Métodos de pago"),
    ("🧾", "Últimas órdenes"),
]

# =============================================================================
# 3. SESSION STATE
# =============================================================================
defaults = {
    "logged_in": False,
    "user_name": "GRUPO",
    "city": CITIES[0],
    "cart_count": 0,
    "sidebar_expanded": False,
    "active_category": None,
}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val


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
.topbar-wrap { border-bottom: 1px solid var(--divider); margin-bottom: 18px; padding-bottom: 12px; }
.brand {
    font-family: 'Playfair Display', serif; font-weight:700; font-size: 1.55rem;
    letter-spacing: 2px; color: var(--ivory); display:flex; align-items:center; gap:10px;
}
.brand span { color: var(--gold); }
.brand-tag { font-family:'Cormorant Garamond', serif; font-style: italic; color: var(--muted); font-size: 0.92rem; margin-left:6px;}
.location-pill {
    display:inline-flex; align-items:center; gap:6px; border:1px solid var(--divider);
    border-radius:999px; padding:7px 16px; color: var(--gold-light); font-size:0.82rem;
    background: var(--panel);
}
.hamburger { font-size:1.3rem; color: var(--gold-light); line-height:1; }
.account-pill { display:flex; align-items:center; gap:8px; color:var(--champagne); font-size:0.85rem; justify-content:flex-end; }
.avatar-mini {
    width:30px; height:30px; border-radius:50%; border:1px solid var(--gold);
    display:flex; align-items:center; justify-content:center; font-size:0.75rem;
    color: var(--gold-light); background: var(--panel-raised); font-family:'Playfair Display', serif;
}

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

/* ---------- category icon row: plain icon + label + arrow, no box ---------- */
.st-key-cat_row div.stButton > button {
    background: transparent;
    border: none;
    color: var(--champagne);
    text-transform: none;
    letter-spacing: 0.2px;
    font-weight: 500;
    font-size: 0.95rem;
    padding: 12px 4px;
    box-shadow: none;
}
.st-key-cat_row div.stButton > button:hover {
    background: var(--panel);
    border-radius: 12px;
    color: var(--gold-light);
}

.active-banner {
    border: 1px solid var(--gold);
    background: var(--panel);
    border-radius: 12px;
    padding: 12px 18px;
    color: var(--gold-light);
    font-size: 0.9rem;
    margin-bottom: 20px;
}

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
.chip.active { background: var(--gold); color:#0B0B0C; border-color: var(--gold); font-weight:600; }

/* ---------- join cards (photo-style header + body, like the reference app) ---------- */
.join-card {
    background: var(--panel); border:1px solid var(--divider); border-radius:16px;
    overflow:hidden; height:100%;
}
.join-photo {
    height: 110px; display:flex; align-items:center; justify-content:center;
    font-size: 2.4rem; border-bottom: 1px solid var(--divider);
}
.join-body { padding: 20px 22px 24px 22px; }
.join-body h3 { font-size:1.08rem; margin: 0 0 8px 0; }
.join-body p { color: var(--muted); font-size:0.86rem; line-height:1.5; min-height: 64px; }

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
    width: 100%;
}
div.stButton > button:hover, div.stDownloadButton > button:hover {
    background: var(--gold);
    color: #0B0B0C;
    border-color: var(--gold);
}

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
section[data-testid="stSidebar"] hr { border-color: var(--divider); margin: 14px 0; }
.promo-banner {
    background: linear-gradient(120deg, #241f34, #14121c);
    border: 1px solid var(--divider);
    border-radius: 14px;
    padding: 14px 16px;
    display:flex; align-items:center; gap:10px;
    color: var(--gold-light); font-size: 0.85rem; font-weight:600;
    margin: 14px 0 6px 0;
}
.sidebar-avatar { display:flex; align-items:center; gap:10px; margin-bottom:2px; }
.sidebar-avatar .ring {
    width:40px; height:40px; border-radius:50%; border:1px solid var(--gold);
    display:flex; align-items:center; justify-content:center; background: var(--panel-raised);
    font-family:'Playfair Display', serif; color: var(--gold-light);
}
.section-row { display:flex; align-items:center; justify-content:space-between; padding: 7px 0; }
.section-row .left { display:flex; align-items:center; gap:10px; color: var(--ivory); font-size:0.92rem; }
.section-row .chev { color: var(--muted); }

/* ---------- footer ---------- */
.footer { border-top:1px solid var(--divider); margin-top: 50px; padding-top: 24px; text-align:center; color:var(--muted); font-size:0.8rem;}
.footer .crest { font-family:'Playfair Display', serif; color: var(--gold); font-size:1.4rem; letter-spacing:3px; margin-bottom:6px;}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# =============================================================================
# 5. SIDEBAR — replicates the app's slide-out menu: profile header,
#    promotions banner, section list (with "ver más / ver menos"),
#    credits, profile links, other actions, country selector, sign out.
# =============================================================================
with st.sidebar:
    st.markdown(
        f"""
        <div class="sidebar-avatar">
            <div class="ring">{st.session_state.user_name[0]}</div>
            <div>Hola, <b>{st.session_state.user_name}</b><br>
                 <span style="color:var(--gold-light); font-size:0.75rem;">★ Miembro Prime</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        "<div class='promo-banner'>🎯 &nbsp;Descubre nuestras promociones exclusivas</div>",
        unsafe_allow_html=True,
    )

    st.markdown("<div class='eyebrow'>Secciones</div>", unsafe_allow_html=True)

    visible = CATEGORIES if st.session_state.sidebar_expanded else CATEGORIES[:SIDEBAR_COLLAPSED_COUNT]
    for cat in visible:
        if st.button(f"{cat['icon']}  {cat['name']}", key=f"side_{cat['name']}", use_container_width=True):
            st.session_state.active_category = cat["name"]
            st.rerun()

    toggle_label = "Ver menos" if st.session_state.sidebar_expanded else "Ver más"
    if st.button(toggle_label, key="toggle_sections"):
        st.session_state.sidebar_expanded = not st.session_state.sidebar_expanded
        st.rerun()

    st.markdown("---")
    st.markdown("<div class='eyebrow'>Promociones y créditos</div>", unsafe_allow_html=True)
    col_a, col_b = st.columns([2, 1])
    col_a.markdown("Créditos Aurus")
    col_b.markdown("**S/ 0.00**")

    st.markdown("---")
    st.markdown("<div class='eyebrow'>Tu perfil</div>", unsafe_allow_html=True)
    for icon, label in SIDEBAR_PROFILE:
        st.markdown(f"{icon}&nbsp;&nbsp;{label}", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("<div class='eyebrow'>Otros</div>", unsafe_allow_html=True)
    for icon, label in SIDEBAR_OTHERS:
        st.markdown(f"{icon}&nbsp;&nbsp;{label}", unsafe_allow_html=True)

    st.markdown("---")
    st.selectbox("País", ["🇵🇪 Perú", "🇨🇴 Colombia", "🇲🇽 México", "🇨🇱 Chile"], key="country_select")

    if st.button("Cerrar sesión", key="logout_btn"):
        st.session_state.logged_in = False
        st.session_state.user_name = "Invitado"

# =============================================================================
# 6. TOP BAR — hamburger cue, logo, location pill, search, account, cart
# =============================================================================
st.markdown("<div class='topbar-wrap'>", unsafe_allow_html=True)
top_l, top_m, top_r = st.columns([2.3, 3, 1.7])

with top_l:
    st.markdown(
        f"""
        <div class="brand">
            <span class="hamburger">☰</span> ✦ AURUS<span> PRIME</span>
        </div>
        <div class="location-pill" style="margin-top:8px;">📍 {st.session_state.city} ▾</div>
        """,
        unsafe_allow_html=True,
    )

with top_m:
    st.write("")
    st.text_input("Buscar", placeholder="👓 Comida, restaurantes, tiendas, productos…", label_visibility="collapsed")

with top_r:
    st.write("")
    ac1, ac2 = st.columns(2)
    with ac1:
        st.button("Ingreso", key="login_btn")
    with ac2:
        st.button(f"🛍 {st.session_state.cart_count}", key="cart_btn")

st.markdown("</div>", unsafe_allow_html=True)

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
        placeholder=f"📍 ¿Dónde desea recibir su pedido en {st.session_state.city}?",
        label_visibility="collapsed",
    )
    b1, b2, b3 = st.columns([1, 1, 1])
    with b2:
        st.button("⊙ Usar mi ubicación actual", key="use_location")

# =============================================================================
# 9. CATEGORY ROW — "¿Necesitas algo más?" equivalent: one simple row of
#    clickable icon buttons, kept short and practical on purpose.
# =============================================================================
st.markdown(
    "<div class='section-title'><h2>¿Qué necesita hoy?</h2><div class='rule'></div></div>",
    unsafe_allow_html=True,
)

if st.session_state.active_category:
    st.markdown(
        f"<div class='active-banner'>✦ Estás viendo: <b>{st.session_state.active_category}</b> "
        f"&nbsp;·&nbsp; próximamente disponible con catálogo completo.</div>",
        unsafe_allow_html=True,
    )

cat_row = st.container(key="cat_row")
with cat_row:
    cat_cols = st.columns(len(CATEGORIES))
    for col, cat in zip(cat_cols, CATEGORIES):
        with col:
            if st.button(f"{cat['icon']}   {cat['name']}  →", key=f"main_{cat['name']}", use_container_width=True):
                st.session_state.active_category = cat["name"]
                st.rerun()

# =============================================================================
# 10. TRENDING TAGS ("Lo más buscado")
# =============================================================================
st.markdown(
    "<div class='section-title'><h2>Lo más buscado</h2><div class='rule'></div></div>",
    unsafe_allow_html=True,
)
chips_html = "".join(
    f"<span class='chip{' active' if i == 0 else ''}'>{tag}</span>"
    for i, tag in enumerate(TRENDING_TAGS)
)
st.markdown(f"<div class='chip-row'>{chips_html}</div>", unsafe_allow_html=True)

# =============================================================================
# 11. FEATURED HOUSES ("¡Los 10 más elegidos!")
# =============================================================================
st.markdown(
    "<div class='section-title'><h2>¡Las 10 casas más elegidas!</h2><div class='rule'></div></div>",
    unsafe_allow_html=True,
)
house_cols = st.columns(5)
for i, house in enumerate(FEATURED_HOUSES):
    initials = "".join([w[0] for w in house.split()[:2]]).upper()
    tone = JEWEL_TONES[i % len(JEWEL_TONES)]
    with house_cols[i % 5]:
        st.markdown(
            f"""
            <div class="avatar-ring" style="background:{tone};">{initials}</div>
            <div class="house-name">{house}</div>
            """,
            unsafe_allow_html=True,
        )
        st.write("")

# =============================================================================
# 12. JOIN AURUS PRIME (partners / couriers) — mirrors "Únete a Rappi"
# =============================================================================
st.markdown(
    "<div class='section-title'><h2>Únase a <span style=\"color:var(--gold);\">Aurus Prime</span></h2>"
    "<div class='rule'></div></div>",
    unsafe_allow_html=True,
)
join_cols = st.columns(3)
for i, card in enumerate(JOIN_CARDS):
    with join_cols[i]:
        st.markdown(
            f"""
            <div class="join-card">
                <div class="join-photo" style="background:{card['gradient']};">{card['icon']}</div>
                <div class="join-body">
                    <h3>{card['title']}</h3>
                    <p>{card['body']}</p>
                </div>
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
