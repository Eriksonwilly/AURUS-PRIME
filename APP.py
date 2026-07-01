"""
AURUS PRIME — Luxury On-Demand Delivery Marketplace
=====================================================
Streamlit single-file application.

Author  : Generated for deployment to Streamlit Community Cloud (streamlit.io)
Stack   : Python 3.10+ / Streamlit >= 1.33

ARCHITECTURE NOTES (read this before extending the app)
---------------------------------------------------------
This build replaces decorative buttons with a real, working navigation flow:

    Home ──▶ Categoría ──▶ Tienda ──▶ Carrito ──▶ Checkout ──▶ Confirmación

Pattern used: **session_state router**. `st.session_state.page` holds the
current "screen" name. Every button calls `go(page, **params)`, which
updates that state and triggers `st.rerun()`. Each screen is rendered by
its own `render_*()` function — content is fully separated from routing.

Layers, from bottom to top:
    1. DATA LAYER      (section 2)  -> CATEGORIES, STORE catalog, PRODUCTS
    2. STATE LAYER      (section 3)  -> st.session_state defaults, cart helpers
    3. DESIGN SYSTEM    (section 4)  -> fonts, colors, component CSS
    4. NAVIGATION LAYER (section 5)  -> go(), sidebar, top bar (shown on every screen)
    5. SCREENS          (section 6)  -> render_home / render_category / render_store /
                                         render_cart / render_checkout / render_success
    6. ROUTER           (section 7)  -> dispatches to the right render_* function

For a real commercial deployment, swap the in-memory DATA LAYER (Python
lists/dicts) for calls to a real backend (Postgres/Supabase, a REST API,
etc.) and swap the in-memory cart (st.session_state) for a persisted cart
(per logged-in user, in your database) — the rest of the architecture
(router + screens) stays the same.

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
# 2. DATA LAYER — content + "business" catalog.
#    In production, replace these constants with calls to your real backend
#    (a database or REST API) but keep the exact same shape (list of dicts)
#    so the render_* functions below don't need to change.
# =============================================================================

BRAND_NAME = "AURUS PRIME"
BRAND_MONOGRAM = "AP"

CATEGORIES = [
    {"icon": "🍽️", "name": "Restaurantes"},
    {"icon": "🛒", "name": "Supermercados"},
    {"icon": "💊", "name": "Farmacia"},
    {"icon": "⚡", "name": "Express"},
    {"icon": "🏛️", "name": "Aurus Mall"},
    {"icon": "🍷", "name": "Licores"},
    {"icon": "🧺", "name": "La Cesta"},
    {"icon": "✈️", "name": "Aurus Travel"},
    {"icon": "🌿", "name": "Turbo"},
    {"icon": "🎁", "name": "Regalos"},
]
SIDEBAR_COLLAPSED_COUNT = 3

TRENDING_TAGS = ["Mundial", "Snack", "Gaseosa", "Cerveza"]

# Fictional luxury houses used to seed every category with real, clickable
# stores. Swap this for `SELECT * FROM stores WHERE category = ...` in
# production. Real, trademarked third-party brands are intentionally NOT
# used here (see the note at the end of the chat reply).
HOUSE_NAMES = [
    "Maison Verlaine", "Château Bistro", "Le Bernardin Express", "Orsini Gioielli",
    "Nord Atelier", "Casa Dorado", "Villa Cachemira", "L'Or Noir", "Ámbar & Cedro", "Silvana Home",
]
JEWEL_TONES = ["#3B1E23", "#1E2A26", "#241C33", "#2A2417", "#1C232E"]

# Generic product menu reused per store (in production: one menu per store,
# pulled from your database / POS integration).
PRODUCT_TEMPLATE = [
    {"icon": "🥂", "name": "Copa de bienvenida", "price": 45.00},
    {"icon": "🍱", "name": "Selección del chef", "price": 98.00},
    {"icon": "🍰", "name": "Postre de la casa", "price": 32.00},
    {"icon": "☕", "name": "Café de origen", "price": 18.00},
]

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


def get_stores(category_name: str):
    """Return the 3 stores available for a category (rotates the house list
    so every category shows a different, stable set)."""
    idx = next(i for i, c in enumerate(CATEGORIES) if c["name"] == category_name)
    return [HOUSE_NAMES[(idx + i) % len(HOUSE_NAMES)] for i in range(3)]


# =============================================================================
# 3. STATE LAYER — session defaults + cart / navigation helpers
# =============================================================================
defaults = {
    "user_name": "GRUPO",
    "sidebar_expanded": False,
    "page": "home",             # home | category | store | cart | checkout | success
    "selected_category": None,
    "selected_store": None,
    "cart": {},                 # key -> {"name","price","store","qty"}
}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val


def go(page: str, **params):
    """Central navigation helper: every functional button calls this."""
    st.session_state.page = page
    for k, v in params.items():
        st.session_state[k] = v
    st.rerun()


def add_to_cart(store: str, product: dict):
    key = f"{store}__{product['name']}"
    if key in st.session_state.cart:
        st.session_state.cart[key]["qty"] += 1
    else:
        st.session_state.cart[key] = {
            "name": product["name"], "price": product["price"], "store": store, "qty": 1,
        }


def remove_from_cart(key: str):
    st.session_state.cart.pop(key, None)


def cart_count() -> int:
    return sum(item["qty"] for item in st.session_state.cart.values())


def cart_total() -> float:
    return sum(item["qty"] * item["price"] for item in st.session_state.cart.values())


def greeting() -> str:
    hour = datetime.now().hour
    if hour < 12:
        return "buenos días"
    if hour < 19:
        return "buenas tardes"
    return "buenas noches"


# =============================================================================
# 4. DESIGN SYSTEM — fonts, colors, component CSS
# =============================================================================
CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,500;0,600;0,700;1,500&family=Cormorant+Garamond:ital,wght@0,500;1,500&family=Inter:wght@400;500;600&display=swap');

:root{
    --bg: #0B0B0C; --panel: #141416; --panel-raised: #1A1A1D;
    --gold: #C9A227; --gold-light: #E8CD7A;
    --ivory: #F5F1E8; --champagne: #EFE6D8; --muted: #A8A29B;
    --divider: rgba(201,162,39,0.25);
}
html, body, [class*="css"]  { font-family: 'Inter', sans-serif; }
.stApp { background-color: var(--bg); color: var(--ivory); }
#MainMenu, footer, header[data-testid="stHeader"] { visibility: hidden; height:0; }
.block-container { padding-top: 1.2rem; padding-bottom: 3rem; max-width: 1180px; }
h1, h2, h3 { font-family: 'Playfair Display', serif !important; color: var(--ivory); letter-spacing: 0.3px; }

.eyebrow { text-transform: uppercase; letter-spacing: 3px; font-size: 0.72rem; color: var(--gold-light); font-weight: 600; margin-bottom: 6px; }

.topbar-wrap { border-bottom: 1px solid var(--divider); margin-bottom: 18px; padding-bottom: 12px; }
.brand { font-family: 'Playfair Display', serif; font-weight:700; font-size: 1.55rem; letter-spacing: 2px; color: var(--ivory); display:flex; align-items:center; gap:10px; cursor:pointer; }
.brand span { color: var(--gold); }
.location-pill { display:inline-flex; align-items:center; gap:6px; border:1px solid var(--divider); border-radius:999px; padding:7px 16px; color: var(--gold-light); font-size:0.82rem; background: var(--panel); }
.hamburger { font-size:1.3rem; color: var(--gold-light); line-height:1; }
.avatar-mini { width:30px; height:30px; border-radius:50%; border:1px solid var(--gold); display:flex; align-items:center; justify-content:center; font-size:0.75rem; color: var(--gold-light); background: var(--panel-raised); font-family:'Playfair Display', serif; }

.ribbon { background: linear-gradient(90deg, #1A1A1D 0%, #0B0B0C 100%); border: 1px solid var(--divider); border-radius: 999px; padding: 9px 22px; display:flex; align-items:center; gap:10px; justify-content:center; font-size: 0.85rem; color: var(--champagne); margin-bottom: 26px; }
.ribbon b { color: var(--gold-light); }

.hero { background: radial-gradient(circle at 20% 20%, #1c1a12 0%, #0B0B0C 60%); border: 1px solid var(--divider); border-radius: 18px; padding: 44px 48px; text-align:center; margin-bottom: 34px; }
.hero h1 { font-size: 2.5rem; margin:0; }

.section-title { display:flex; align-items:baseline; gap:14px; margin: 38px 0 16px 0; }
.section-title h2 { font-size: 1.5rem; margin:0; }
.section-title .rule { flex:1; height:1px; background: var(--divider); }

.st-key-cat_row div.stButton > button { background: transparent; border: none; color: var(--champagne); text-transform: none; letter-spacing: 0.2px; font-weight: 500; font-size: 0.95rem; padding: 12px 4px; box-shadow: none; }
.st-key-cat_row div.stButton > button:hover { background: var(--panel); border-radius: 12px; color: var(--gold-light); }

.active-banner { border: 1px solid var(--gold); background: var(--panel); border-radius: 12px; padding: 12px 18px; color: var(--gold-light); font-size: 0.9rem; margin-bottom: 20px; }

.avatar-ring { width:64px; height:64px; border-radius:50%; border: 1px solid var(--gold); display:flex; align-items:center; justify-content:center; font-family:'Playfair Display', serif; color: var(--gold-light); font-size:1.1rem; margin: 0 auto 10px auto; background: var(--panel-raised); }
.house-name { text-align:center; font-size:0.82rem; color: var(--champagne); }

.chip-row { display:flex; flex-wrap:wrap; gap:10px; margin-bottom: 6px;}
.chip { border:1px solid var(--divider); color: var(--champagne); border-radius:999px; padding: 7px 16px; font-size:0.82rem; background: var(--panel); }
.chip.active { background: var(--gold); color:#0B0B0C; border-color: var(--gold); font-weight:600; }

.join-card { background: var(--panel); border:1px solid var(--divider); border-radius:16px; overflow:hidden; height:100%; }
.join-photo { height: 100px; display:flex; align-items:center; justify-content:center; font-size: 2.2rem; border-bottom: 1px solid var(--divider); }
.join-body { padding: 18px 20px 22px 20px; }
.join-body h3 { font-size:1.05rem; margin: 0 0 8px 0; }
.join-body p { color: var(--muted); font-size:0.85rem; line-height:1.5; min-height: 64px; }

.store-card, .product-row, .cart-row { background: var(--panel); border:1px solid var(--divider); border-radius:14px; padding:16px 18px; margin-bottom:12px; }
.store-card h4, .product-row h4 { margin:0 0 4px 0; font-size:1.05rem; }
.store-card .meta, .product-row .meta { color: var(--muted); font-size:0.8rem; }
.price-tag { color: var(--gold-light); font-weight:600; font-family:'Playfair Display', serif; }
.cart-total-box { border:1px solid var(--gold); border-radius:14px; padding:18px 22px; text-align:right; background:var(--panel); }

div.stButton > button, div.stDownloadButton > button { background: transparent; color: var(--gold-light); border: 1px solid var(--gold); border-radius: 999px; padding: 8px 22px; letter-spacing: 1.2px; text-transform: uppercase; font-size: 0.72rem; font-weight: 600; transition: all .18s ease; width: 100%; }
div.stButton > button:hover, div.stDownloadButton > button:hover { background: var(--gold); color: #0B0B0C; border-color: var(--gold); }

div[data-baseweb="select"] > div, .stTextInput > div > div, .stNumberInput > div > div, .stTextArea textarea { background: var(--panel) !important; border: 1px solid var(--divider) !important; color: var(--ivory) !important; border-radius: 10px !important; }

section[data-testid="stSidebar"] { background-color: #0E0E10; border-right: 1px solid var(--divider); }
section[data-testid="stSidebar"] hr { border-color: var(--divider); margin: 14px 0; }
.promo-banner { background: linear-gradient(120deg, #241f34, #14121c); border: 1px solid var(--divider); border-radius: 14px; padding: 14px 16px; display:flex; align-items:center; gap:10px; color: var(--gold-light); font-size: 0.85rem; font-weight:600; margin: 14px 0 6px 0; }
.sidebar-avatar { display:flex; align-items:center; gap:10px; margin-bottom:2px; }
.sidebar-avatar .ring { width:40px; height:40px; border-radius:50%; border:1px solid var(--gold); display:flex; align-items:center; justify-content:center; background: var(--panel-raised); font-family:'Playfair Display', serif; color: var(--gold-light); }
.cart-mini { border:1px solid var(--divider); border-radius:12px; padding:12px 14px; margin: 10px 0; }
.cart-mini .row { display:flex; justify-content:space-between; font-size:0.85rem; color:var(--champagne); }

.footer { border-top:1px solid var(--divider); margin-top: 50px; padding-top: 24px; text-align:center; color:var(--muted); font-size:0.8rem;}
.footer .crest { font-family:'Playfair Display', serif; color: var(--gold); font-size:1.4rem; letter-spacing:3px; margin-bottom:6px;}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# =============================================================================
# 5. NAVIGATION LAYER — sidebar + top bar. Rendered on every screen so the
#    person can always jump back home, browse sections, or reach the cart.
# =============================================================================
with st.sidebar:
    st.markdown(
        f"""<div class="sidebar-avatar"><div class="ring">{st.session_state.user_name[0]}</div>
        <div>Hola, <b>{st.session_state.user_name}</b><br>
        <span style="color:var(--gold-light); font-size:0.75rem;">★ Miembro Prime</span></div></div>""",
        unsafe_allow_html=True,
    )
    st.markdown("<div class='promo-banner'>🎯 &nbsp;Descubre nuestras promociones exclusivas</div>", unsafe_allow_html=True)

    # live cart summary — always visible, always accurate
    st.markdown(
        f"""<div class="cart-mini">
            <div class="row"><span>🛍 Carrito</span><span>{cart_count()} ítem(s)</span></div>
            <div class="row"><span>Subtotal</span><span>S/ {cart_total():.2f}</span></div>
        </div>""",
        unsafe_allow_html=True,
    )
    if st.button("Ver carrito →", key="side_cart_btn", use_container_width=True):
        go("cart")

    st.markdown("<div class='eyebrow'>Secciones</div>", unsafe_allow_html=True)
    visible = CATEGORIES if st.session_state.sidebar_expanded else CATEGORIES[:SIDEBAR_COLLAPSED_COUNT]
    for cat in visible:
        if st.button(f"{cat['icon']}  {cat['name']}", key=f"side_{cat['name']}", use_container_width=True):
            go("category", selected_category=cat["name"])
    toggle_label = "Ver menos" if st.session_state.sidebar_expanded else "Ver más"
    if st.button(toggle_label, key="toggle_sections"):
        st.session_state.sidebar_expanded = not st.session_state.sidebar_expanded
        st.rerun()

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
        st.session_state.user_name = "Invitado"

# top bar
st.markdown("<div class='topbar-wrap'>", unsafe_allow_html=True)
top_l, top_m, top_r = st.columns([2.3, 3, 1.7])
with top_l:
    if st.button("☰ ✦ AURUS PRIME", key="brand_home_btn"):
        go("home")
    st.markdown(f"<div class='location-pill'>📍 Ingresar mi ubicación ▾</div>", unsafe_allow_html=True)
with top_m:
    st.write("")
    st.text_input("Buscar", placeholder="Comida, restaurantes, tiendas, productos…", label_visibility="collapsed")
with top_r:
    st.write("")
    ac1, ac2 = st.columns(2)
    with ac1:
        st.markdown(f"<div class='avatar-mini' style='margin-left:auto;'>{st.session_state.user_name[0]}</div>", unsafe_allow_html=True)
    with ac2:
        if st.button(f"🛍 {cart_count()}", key="cart_btn"):
            go("cart")
st.markdown("</div>", unsafe_allow_html=True)

# =============================================================================
# 6. SCREENS — one function per "page". Each is self-contained: it reads
#    what it needs from session_state and only calls go() on user action.
# =============================================================================

def render_home():
    st.markdown(
        "<div class='ribbon'>✦ &nbsp;¿Nuevo en Aurus Prime? Disfruta de <b>envíos de cortesía</b> "
        "en tus primeras semanas &nbsp;·&nbsp; <b>Regístrate</b></div>",
        unsafe_allow_html=True,
    )
    st.markdown(f"<div class='hero'><h1>Hola, {greeting()}.</h1></div>", unsafe_allow_html=True)

    st.markdown("<div class='section-title'><h2>¿Necesitas algo más?</h2><div class='rule'></div></div>", unsafe_allow_html=True)
    cat_row = st.container(key="cat_row")
    with cat_row:
        cols = st.columns(len(CATEGORIES))
        for col, cat in zip(cols, CATEGORIES):
            with col:
                if st.button(f"{cat['icon']}   {cat['name']}  →", key=f"main_{cat['name']}", use_container_width=True):
                    go("category", selected_category=cat["name"])

    st.markdown("<div class='section-title'><h2>Lo más buscado</h2><div class='rule'></div></div>", unsafe_allow_html=True)
    chips_html = "".join(f"<span class='chip{' active' if i == 0 else ''}'>{tag}</span>" for i, tag in enumerate(TRENDING_TAGS))
    st.markdown(f"<div class='chip-row'>{chips_html}</div>", unsafe_allow_html=True)

    st.markdown("<div class='section-title'><h2>¡Los 10 más elegidos!</h2><div class='rule'></div></div>", unsafe_allow_html=True)
    house_cols = st.columns(5)
    for i, house in enumerate(HOUSE_NAMES):
        initials = "".join([w[0] for w in house.split()[:2]]).upper()
        tone = JEWEL_TONES[i % len(JEWEL_TONES)]
        with house_cols[i % 5]:
            if st.button(f"{initials}\n{house}", key=f"house_{house}", use_container_width=True, help=f"Ver {house}"):
                go("store", selected_store=house, selected_category="Restaurantes")
            st.markdown(f"<div class='house-name' style='margin-top:-8px;'>{house}</div>", unsafe_allow_html=True)

    st.markdown("<div class='section-title'><h2>Únase a <span style=\"color:var(--gold);\">Aurus Prime</span></h2><div class='rule'></div></div>", unsafe_allow_html=True)
    join_cols = st.columns(3)
    for i, card in enumerate(JOIN_CARDS):
        with join_cols[i]:
            st.markdown(
                f"""<div class="join-card"><div class="join-photo" style="background:{card['gradient']};">{card['icon']}</div>
                <div class="join-body"><h3>{card['title']}</h3><p>{card['body']}</p></div></div>""",
                unsafe_allow_html=True,
            )
            st.write("")
            st.button(card["cta"], key=f"join_{i}")


def render_category():
    cat_name = st.session_state.selected_category
    if st.button("← Volver al inicio", key="back_home_cat"):
        go("home")
    st.markdown(f"<div class='section-title'><h2>{cat_name}</h2><div class='rule'></div></div>", unsafe_allow_html=True)

    for store in get_stores(cat_name):
        c1, c2 = st.columns([4, 1])
        with c1:
            st.markdown(
                f"""<div class="store-card"><h4>{store}</h4>
                <div class="meta">⭐ 4.8 · 25-35 min · Envío S/ 6.90</div></div>""",
                unsafe_allow_html=True,
            )
        with c2:
            st.write("")
            if st.button("Ver tienda", key=f"open_{store}"):
                go("store", selected_store=store)


def render_store():
    store = st.session_state.selected_store
    if st.button("← Volver", key="back_cat"):
        if st.session_state.selected_category:
            go("category", selected_category=st.session_state.selected_category)
        else:
            go("home")
    st.markdown(f"<div class='section-title'><h2>{store}</h2><div class='rule'></div></div>", unsafe_allow_html=True)

    for product in PRODUCT_TEMPLATE:
        c1, c2, c3 = st.columns([3, 1, 1])
        with c1:
            st.markdown(
                f"""<div class="product-row"><h4>{product['icon']} {product['name']}</h4>
                <span class="price-tag">S/ {product['price']:.2f}</span></div>""",
                unsafe_allow_html=True,
            )
        with c3:
            st.write("")
            if st.button("Agregar", key=f"add_{store}_{product['name']}"):
                add_to_cart(store, product)
                st.toast(f"{product['name']} agregado al carrito", icon="✦")
                st.rerun()


def render_cart():
    if st.button("← Seguir comprando", key="back_home_cart"):
        go("home")
    st.markdown("<div class='section-title'><h2>Tu carrito</h2><div class='rule'></div></div>", unsafe_allow_html=True)

    if not st.session_state.cart:
        st.info("Tu carrito está vacío. Explora una categoría y agrega productos.")
        return

    for key, item in list(st.session_state.cart.items()):
        c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
        with c1:
            st.markdown(
                f"""<div class="cart-row"><h4>{item['name']}</h4>
                <div class="meta">{item['store']} · S/ {item['price']:.2f} c/u</div></div>""",
                unsafe_allow_html=True,
            )
        with c2:
            st.write("")
            st.markdown(f"<div style='text-align:center; padding-top:14px;'>Cant: {item['qty']}</div>", unsafe_allow_html=True)
        with c3:
            st.write("")
            if st.button("＋", key=f"plus_{key}"):
                st.session_state.cart[key]["qty"] += 1
                st.rerun()
        with c4:
            st.write("")
            if st.button("Quitar", key=f"remove_{key}"):
                remove_from_cart(key)
                st.rerun()

    st.markdown(
        f"<div class='cart-total-box'>Total a pagar<br><span class='price-tag' style='font-size:1.4rem;'>S/ {cart_total():.2f}</span></div>",
        unsafe_allow_html=True,
    )
    st.write("")
    if st.button("Ir a pagar →", key="go_checkout"):
        go("checkout")


def render_checkout():
    if st.button("← Volver al carrito", key="back_cart"):
        go("cart")
    st.markdown("<div class='section-title'><h2>Confirmar pedido</h2><div class='rule'></div></div>", unsafe_allow_html=True)

    if not st.session_state.cart:
        st.info("Tu carrito está vacío.")
        return

    with st.form("checkout_form"):
        st.text_input("Dirección de entrega", placeholder="Av. Ejemplo 123, Arequipa")
        st.selectbox("Método de pago", ["Tarjeta terminada en 4532", "Yape", "Efectivo"])
        st.text_area("Instrucciones para el Aurus Courier (opcional)")
        st.markdown(
            f"<div class='cart-total-box'>Total a pagar<br><span class='price-tag' style='font-size:1.4rem;'>S/ {cart_total():.2f}</span></div>",
            unsafe_allow_html=True,
        )
        submitted = st.form_submit_button("Confirmar pedido")
        if submitted:
            st.session_state.cart = {}
            go("success")


def render_success():
    st.markdown(
        """<div class="hero"><div class="eyebrow" style="justify-content:center; display:flex;">Pedido confirmado</div>
        <h1>✦ Gracias por su preferencia</h1><p style="color:var(--muted);">
        Su Aurus Courier está siendo asignado. Recibirá el detalle en breve.</p></div>""",
        unsafe_allow_html=True,
    )
    if st.button("Volver al inicio", key="back_home_success"):
        go("home")


# =============================================================================
# 7. ROUTER — dispatches to the active screen. This is the only place that
#    knows about st.session_state.page.
# =============================================================================
ROUTES = {
    "home": render_home,
    "category": render_category,
    "store": render_store,
    "cart": render_cart,
    "checkout": render_checkout,
    "success": render_success,
}
ROUTES.get(st.session_state.page, render_home)()

# =============================================================================
# 8. FOOTER — shown on every screen
# =============================================================================
st.markdown(
    f"""<div class="footer"><div class="crest">✦ {BRAND_MONOGRAM} ✦</div>
    <div>AURUS PRIME · Concierge de lujo a domicilio</div>
    <div style="margin-top:6px;">Términos y condiciones · Privacidad · Ayuda · © {datetime.now().year} Aurus Prime</div></div>""",
    unsafe_allow_html=True,
)
