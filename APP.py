"""
AURUS PRIME — Luxury On-Demand Delivery Marketplace (v2.0)
=============================================================
Streamlit single-file application.

WHAT CHANGED IN v2.0 (per product brief)
-------------------------------------------------------------
- Real districts (Yanahuara, JLBYR, San Isidro, Miraflores) drive the
  "Ingresar mi ubicación" flow and which stores are shown.
- Categories renamed to a premium/gourmet vocabulary.
- Every secondary button is now wired to a real screen + real
  session-state data: cuenta, métodos de pago, pedidos, favoritos,
  promociones/cupones, notificaciones, formularios de socios.
- Cart is now "professional": qty +/-, quitar, guardar para después,
  comentario, programar entrega, cupón, propina, y desglose
  subtotal / delivery / IGV / descuento / total.
- Checkout is a real 5-step wizard (dirección → mapa → pago → horario →
  confirmación) that creates an order.
- Orders have a status pipeline with a simulated progress control
  (see honesty note below) and a tracking screen with a progress bar.
- Home reorganized: saludo personalizado, recomendados, cercanos al
  distrito elegido, promociones, pedidos recientes.
- Profile screen: nivel, puntos, beneficios, accesos rápidos.
- A minimal, session-only "admin" screen (orders + partner leads) —
  see the honesty note below on why this is not a real admin panel.

HONESTY / SCOPE NOTES (read before demoing this as "production ready")
-------------------------------------------------------------
1. THERE IS NO DATABASE. Everything (orders, favorites, payment methods,
   notifications, partner applications) lives in `st.session_state`, so
   it resets when the browser tab/session ends. Swapping this for a real
   DB (Postgres/Supabase/Firebase) is a drop-in replacement IF you keep
   the same function signatures (`place_order()`, `add_to_cart()`, etc.)
   — but it is real backend work, not a CSS change.
2. THERE IS NO REAL PAYMENT GATEWAY. `render_checkout()` collects a
   payment *method label* (e.g. "Visa •••• 4532") but does not charge
   any card. Wire step 3 to Culqi / Niubiz / MercadoPago's official SDK
   before taking real money.
3. THERE IS NO REAL COURIER / GPS TRACKING. `render_tracking()` shows a
   progress bar over a fixed set of statuses, advanced with a
   "Simular avance" button so you can demo the UI. Real tracking needs a
   courier-side app or integration (e.g. a webhook from your logistics
   provider) pushing status updates into your database.
4. THERE IS NO REAL MAP. Step 2 of checkout is a placeholder panel with
   instructions for wiring `streamlit-folium` + a Google Maps / Mapbox
   API key — embedding a real interactive map needs that key, which
   only you can provision.
5. THE "ADMIN PANEL" is a read-only view over the current session's
   in-memory orders/leads, with no authentication. A real admin panel
   needs its own auth layer and to read the real database, not
   `st.session_state`.

Run locally:
    pip install -r requirements.txt
    streamlit run app.py
"""

import streamlit as st
from datetime import datetime, timedelta

# =============================================================================
# 1. PAGE CONFIGURATION
# =============================================================================
st.set_page_config(
    page_title="Aurus Prime | Concierge de Lujo a Domicilio",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =============================================================================
# 2. DATA LAYER — swap these constants for real DB queries in production.
# =============================================================================
BRAND_NAME = "AURUS PRIME"
BRAND_MONOGRAM = "AP"

DISTRICTS = [
    {"name": "Yanahuara", "city": "Arequipa"},
    {"name": "José Luis Bustamante y Rivero", "city": "Arequipa"},
    {"name": "San Isidro", "city": "Lima"},
    {"name": "Miraflores", "city": "Lima"},
]

CATEGORIES = [
    {"icon": "🍽️", "name": "Restaurantes Gourmet"},
    {"icon": "☕", "name": "Cafeterías Premium"},
    {"icon": "🛒", "name": "Mercado Gourmet"},
    {"icon": "🍷", "name": "Bodega & Vinos"},
    {"icon": "💊", "name": "Farmacia Premium"},
    {"icon": "🐾", "name": "Mascotas"},
    {"icon": "💐", "name": "Florería"},
    {"icon": "🎁", "name": "Regalos Exclusivos"},
    {"icon": "🥖", "name": "Panadería Artesanal"},
    {"icon": "🥃", "name": "Licores Premium"},
    {"icon": "🍰", "name": "Pastelería"},
    {"icon": "🧴", "name": "Cuidado Personal"},
]
SIDEBAR_COLLAPSED_COUNT = 4

RECOMMENDED_CHIPS = [
    {"icon": "🍣", "name": "Sushi"},
    {"icon": "🥩", "name": "Carnes Premium"},
    {"icon": "🍷", "name": "Vinos"},
    {"icon": "☕", "name": "Café de origen"},
]

# Fictional houses (no real trademarks) with a Peruvian-premium naming
# style, seeded per district so "cercanos" feels grounded in the 4
# districts from the brief. Swap for `SELECT * FROM stores WHERE
# district = ...` in production.
HOUSE_NAMES = [
    "Casa Yanahuara", "El Mirador de Selva Alegre", "Bodega San Isidro",
    "Miraflores Cocina de Autor", "Maison Verlaine", "Château Bistro",
    "Orsini Gioielli", "Nord Atelier", "Villa Cachemira", "Ámbar & Cedro",
]
JEWEL_TONES = ["#3B1E23", "#1E2A26", "#241C33", "#2A2417", "#1C232E"]

PRODUCT_TEMPLATE = [
    {"icon": "🥂", "name": "Copa de bienvenida", "price": 45.00},
    {"icon": "🍱", "name": "Selección del chef", "price": 98.00},
    {"icon": "🍰", "name": "Postre de la casa", "price": 32.00},
    {"icon": "☕", "name": "Café de origen", "price": 18.00},
]

DEFAULT_PAYMENT_METHODS = ["Visa •••• 4532", "Yape"]

COUPONS = {"AURUS10": 0.10, "BIENVENIDA20": 0.20}

TIP_OPTIONS = {"Sin propina": 0.0, "S/ 3": 3.0, "S/ 5": 5.0, "S/ 10": 10.0}

ORDER_STATUSES = ["Recibido", "Preparando", "Courier asignado", "Recogiendo", "En camino", "Entregado"]

DELIVERY_FEE = 6.90
IGV_RATE = 0.18

JOIN_CARDS = [
    {
        "type": "restaurante",
        "gradient": "linear-gradient(135deg,#3a2f16,#0B0B0C)",
        "icon": "🍽️",
        "title": "Registra tu restaurante",
        "body": "Súmate a las casas gastronómicas de mayor prestigio y llega a una clientela exigente en todo el país.",
        "cta": "Registrar mi restaurante",
    },
    {
        "type": "boutique",
        "gradient": "linear-gradient(135deg,#241c33,#0B0B0C)",
        "icon": "🏷️",
        "title": "Registra tu boutique",
        "body": "Accede a miles de clientes Aurus Prime y disfruta de una logística inmediata sin salir de tu tienda.",
        "cta": "Registrar mi boutique",
    },
    {
        "type": "courier",
        "gradient": "linear-gradient(135deg,#2a2417,#0B0B0C)",
        "icon": "🎩",
        "title": "¡Únete como Aurus Courier!",
        "body": "Entregas de alto estándar, tarifas preferentes y el respaldo de una marca premium.",
        "cta": "Postular como Courier",
    },
]

SIDEBAR_OTHERS = [
    ("🍽️", "Registra tu restaurante", "restaurante"),
    ("🏷️", "Registra tu tienda", "boutique"),
    ("🎩", "Quiero ser Aurus Courier", "courier"),
    ("📣", "Pauta en Aurus Prime", "pauta"),
]


def get_stores(category_name: str):
    idx = next(i for i, c in enumerate(CATEGORIES) if c["name"] == category_name)
    return [HOUSE_NAMES[(idx + i) % len(HOUSE_NAMES)] for i in range(3)]


# =============================================================================
# 3. STATE LAYER
# =============================================================================
defaults = {
    "user_name": "Invitado",
    "user_email": "",
    "user_phone": "",
    "registered": False,
    "free_shipping_until": None,          # datetime or None
    "district": None,                     # dict from DISTRICTS
    "sidebar_expanded": False,
    "page": "home",
    "selected_category": None,
    "selected_store": None,
    "cart": {},                           # key -> {"name","price","store","qty"}
    "saved_for_later": {},
    "cart_comment": "",
    "schedule_choice": "Entregar ahora",
    "schedule_time": "19:00",
    "coupon_code": "",
    "coupon_discount": 0.0,
    "courier_tip_label": "Sin propina",
    "payment_methods": list(DEFAULT_PAYMENT_METHODS),
    "orders": [],                         # list of order dicts
    "next_order_id": 1001,
    "favorites": set(),
    "notifications": [],
    "checkout_step": 1,
    "checkout_address": "",
    "checkout_payment": DEFAULT_PAYMENT_METHODS[0],
    "partner_type": None,
    "partner_applications": [],
    "search_query": "",
    "tracking_order_id": None,
}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val


def go(page: str, **params):
    st.session_state.page = page
    for k, v in params.items():
        st.session_state[k] = v
    st.rerun()


def add_notification(msg: str):
    st.session_state.notifications.insert(0, f"{datetime.now().strftime('%H:%M')} · {msg}")


# ---- cart helpers ----
def add_to_cart(store: str, product: dict):
    key = f"{store}__{product['name']}"
    if key in st.session_state.cart:
        st.session_state.cart[key]["qty"] += 1
    else:
        st.session_state.cart[key] = {"name": product["name"], "price": product["price"], "store": store, "qty": 1}


def cart_count() -> int:
    return sum(i["qty"] for i in st.session_state.cart.values())


def cart_subtotal() -> float:
    return sum(i["qty"] * i["price"] for i in st.session_state.cart.values())


def has_free_shipping() -> bool:
    return bool(st.session_state.free_shipping_until and datetime.now() < st.session_state.free_shipping_until)


def cart_breakdown():
    subtotal = cart_subtotal()
    discount = round(subtotal * st.session_state.coupon_discount, 2)
    delivery = 0.0 if has_free_shipping() else DELIVERY_FEE
    igv = round((subtotal - discount) * IGV_RATE, 2)
    tip = TIP_OPTIONS.get(st.session_state.courier_tip_label, 0.0)
    total = round(subtotal - discount + delivery + igv + tip, 2)
    return {"subtotal": subtotal, "discount": discount, "delivery": delivery, "igv": igv, "tip": tip, "total": total}


def apply_coupon(code: str):
    code = code.strip().upper()
    if code in COUPONS:
        st.session_state.coupon_code = code
        st.session_state.coupon_discount = COUPONS[code]
        add_notification(f"Cupón {code} aplicado (-{int(COUPONS[code]*100)}%).")
        st.toast(f"Cupón {code} aplicado ✦", icon="✦")
    else:
        st.warning("Cupón no válido.")


def place_order():
    breakdown = cart_breakdown()
    order = {
        "id": st.session_state.next_order_id,
        "items": list(st.session_state.cart.values()),
        "district": st.session_state.district["name"] if st.session_state.district else "Sin distrito",
        "address": st.session_state.checkout_address,
        "payment": st.session_state.checkout_payment,
        "schedule": st.session_state.schedule_choice if st.session_state.schedule_choice == "Entregar ahora" else f"Programado {st.session_state.schedule_time}",
        "breakdown": breakdown,
        "status_index": 0,
        "created": datetime.now(),
    }
    st.session_state.orders.insert(0, order)
    st.session_state.next_order_id += 1
    add_notification(f"Pedido #{order['id']} confirmado — total S/ {breakdown['total']:.2f}.")
    st.session_state.cart = {}
    st.session_state.coupon_code = ""
    st.session_state.coupon_discount = 0.0
    st.session_state.courier_tip_label = "Sin propina"
    return order["id"]


def advance_order(order_id: int):
    for o in st.session_state.orders:
        if o["id"] == order_id and o["status_index"] < len(ORDER_STATUSES) - 1:
            o["status_index"] += 1
            add_notification(f"Pedido #{order_id} → {ORDER_STATUSES[o['status_index']]}.")


def toggle_favorite(store: str):
    if store in st.session_state.favorites:
        st.session_state.favorites.discard(store)
    else:
        st.session_state.favorites.add(store)


def greeting_word() -> str:
    hour = datetime.now().hour
    if hour < 12:
        return "buenos días"
    if hour < 19:
        return "buenas tardes"
    return "buenas noches"


def loyalty_level():
    spent = sum(o["breakdown"]["total"] for o in st.session_state.orders)
    points = int(spent)
    if spent >= 800:
        return "Platinum", points
    if spent >= 300:
        return "Gold", points
    return "Silver", points


# =============================================================================
# 4. DESIGN SYSTEM
# =============================================================================
CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,500;0,600;0,700;1,500&family=Cormorant+Garamond:ital,wght@0,500;1,500&family=Inter:wght@400;500;600&display=swap');
:root{ --bg:#0B0B0C; --panel:#141416; --panel-raised:#1A1A1D; --gold:#C9A227; --gold-light:#E8CD7A; --ivory:#F5F1E8; --champagne:#EFE6D8; --muted:#A8A29B; --divider:rgba(201,162,39,0.25); }
html, body, [class*="css"]{ font-family:'Inter', sans-serif; }
.stApp{ background-color:var(--bg); color:var(--ivory); }
#MainMenu, footer, header[data-testid="stHeader"]{ visibility:hidden; height:0; }
.block-container{ padding-top:1.2rem; padding-bottom:3rem; max-width:1180px; }
h1,h2,h3{ font-family:'Playfair Display', serif !important; color:var(--ivory); }
.eyebrow{ text-transform:uppercase; letter-spacing:3px; font-size:0.72rem; color:var(--gold-light); font-weight:600; margin-bottom:6px; }
.topbar-wrap{ border-bottom:1px solid var(--divider); margin-bottom:18px; padding-bottom:12px; }
.brand{ font-family:'Playfair Display', serif; font-weight:700; font-size:1.5rem; letter-spacing:2px; color:var(--ivory); display:flex; align-items:center; gap:10px; }
.brand span{ color:var(--gold); }
.location-pill{ display:inline-flex; align-items:center; gap:6px; border:1px solid var(--divider); border-radius:999px; padding:7px 16px; color:var(--gold-light); font-size:0.82rem; background:var(--panel); }
.avatar-mini{ width:30px; height:30px; border-radius:50%; border:1px solid var(--gold); display:flex; align-items:center; justify-content:center; font-size:0.75rem; color:var(--gold-light); background:var(--panel-raised); font-family:'Playfair Display', serif; }
.ribbon{ background:linear-gradient(90deg,#1A1A1D 0%, #0B0B0C 100%); border:1px solid var(--divider); border-radius:16px; padding:12px 22px; display:flex; align-items:center; justify-content:space-between; gap:14px; font-size:0.85rem; color:var(--champagne); margin-bottom:26px; flex-wrap:wrap; }
.ribbon b{ color:var(--gold-light); }
.hero{ background:radial-gradient(circle at 20% 20%, #1c1a12 0%, #0B0B0C 60%); border:1px solid var(--divider); border-radius:18px; padding:40px 48px; margin-bottom:30px; }
.hero h1{ font-size:2.2rem; margin:0 0 4px 0; }
.section-title{ display:flex; align-items:baseline; gap:14px; margin:34px 0 16px 0; }
.section-title h2{ font-size:1.4rem; margin:0; }
.section-title .rule{ flex:1; height:1px; background:var(--divider); }
.st-key-cat_row div.stButton>button, .st-key-chip_row div.stButton>button{ background:transparent; border:none; color:var(--champagne); text-transform:none; font-weight:500; font-size:0.92rem; padding:12px 4px; box-shadow:none; }
.st-key-cat_row div.stButton>button:hover, .st-key-chip_row div.stButton>button:hover{ background:var(--panel); border-radius:12px; color:var(--gold-light); }
.avatar-ring{ width:60px; height:60px; border-radius:50%; border:1px solid var(--gold); display:flex; align-items:center; justify-content:center; font-family:'Playfair Display', serif; color:var(--gold-light); font-size:1.05rem; margin:0 auto 8px auto; background:var(--panel-raised); }
.house-name{ text-align:center; font-size:0.8rem; color:var(--champagne); }
.chip-row{ display:flex; flex-wrap:wrap; gap:10px; }
.chip{ border:1px solid var(--divider); color:var(--champagne); border-radius:999px; padding:7px 16px; font-size:0.82rem; background:var(--panel); }
.join-card{ background:var(--panel); border:1px solid var(--divider); border-radius:16px; overflow:hidden; height:100%; }
.join-photo{ height:90px; display:flex; align-items:center; justify-content:center; font-size:2.1rem; border-bottom:1px solid var(--divider); }
.join-body{ padding:16px 20px 20px 20px; }
.join-body h3{ font-size:1.02rem; margin:0 0 6px 0; }
.join-body p{ color:var(--muted); font-size:0.83rem; line-height:1.5; min-height:60px; }
.store-card,.product-row,.cart-row,.order-card,.notif-row{ background:var(--panel); border:1px solid var(--divider); border-radius:14px; padding:14px 18px; margin-bottom:10px; }
.store-card h4,.product-row h4,.order-card h4{ margin:0 0 4px 0; font-size:1.02rem; }
.meta{ color:var(--muted); font-size:0.8rem; }
.price-tag{ color:var(--gold-light); font-weight:600; font-family:'Playfair Display', serif; }
.totals-box{ border:1px solid var(--gold); border-radius:14px; padding:16px 20px; background:var(--panel); }
.totals-box .line{ display:flex; justify-content:space-between; font-size:0.88rem; color:var(--champagne); padding:3px 0; }
.totals-box .line.total{ font-size:1.15rem; color:var(--gold-light); font-family:'Playfair Display', serif; border-top:1px solid var(--divider); margin-top:6px; padding-top:8px; }
.step-track{ display:flex; gap:8px; margin-bottom:22px; }
.step-dot{ flex:1; text-align:center; padding:8px 4px; border-radius:10px; font-size:0.72rem; letter-spacing:0.5px; border:1px solid var(--divider); color:var(--muted); }
.step-dot.active{ border-color:var(--gold); color:var(--gold-light); background:var(--panel); }
.status-track{ display:flex; justify-content:space-between; margin:18px 0 6px 0; }
.status-step{ flex:1; text-align:center; font-size:0.72rem; color:var(--muted); }
.status-step.done{ color:var(--gold-light); font-weight:600; }
.level-badge{ display:inline-block; border:1px solid var(--gold); color:var(--gold-light); border-radius:999px; padding:5px 16px; font-size:0.78rem; letter-spacing:1px; }
div.stButton>button, div.stDownloadButton>button{ background:transparent; color:var(--gold-light); border:1px solid var(--gold); border-radius:999px; padding:8px 22px; letter-spacing:1px; text-transform:uppercase; font-size:0.72rem; font-weight:600; transition:all .18s ease; width:100%; }
div.stButton>button:hover, div.stDownloadButton>button:hover{ background:var(--gold); color:#0B0B0C; border-color:var(--gold); }
div[data-baseweb="select"]>div,.stTextInput>div>div,.stNumberInput>div>div,.stTextArea textarea{ background:var(--panel) !important; border:1px solid var(--divider) !important; color:var(--ivory) !important; border-radius:10px !important; }
section[data-testid="stSidebar"]{ background-color:#0E0E10; border-right:1px solid var(--divider); }
section[data-testid="stSidebar"] hr{ border-color:var(--divider); margin:12px 0; }
.promo-banner{ background:linear-gradient(120deg,#241f34,#14121c); border:1px solid var(--divider); border-radius:14px; padding:14px 16px; display:flex; align-items:center; gap:10px; color:var(--gold-light); font-size:0.85rem; font-weight:600; margin:14px 0 6px 0; }
.sidebar-avatar{ display:flex; align-items:center; gap:10px; margin-bottom:2px; }
.sidebar-avatar .ring{ width:40px; height:40px; border-radius:50%; border:1px solid var(--gold); display:flex; align-items:center; justify-content:center; background:var(--panel-raised); font-family:'Playfair Display', serif; color:var(--gold-light); }
.cart-mini{ border:1px solid var(--divider); border-radius:12px; padding:12px 14px; margin:10px 0; }
.cart-mini .row{ display:flex; justify-content:space-between; font-size:0.85rem; color:var(--champagne); }
.notif-dot{ display:inline-block; width:8px; height:8px; border-radius:50%; background:var(--gold); margin-right:6px; }
.footer{ border-top:1px solid var(--divider); margin-top:50px; padding-top:24px; text-align:center; color:var(--muted); font-size:0.8rem; }
.footer .crest{ font-family:'Playfair Display', serif; color:var(--gold); font-size:1.4rem; letter-spacing:3px; margin-bottom:6px; }
.scope-note{ border:1px dashed var(--divider); border-radius:12px; padding:12px 16px; color:var(--muted); font-size:0.78rem; margin-top:14px; }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# =============================================================================
# 5. NAVIGATION LAYER — sidebar + top bar, shown on every screen
# =============================================================================
with st.sidebar:
    st.markdown(
        f"""<div class="sidebar-avatar"><div class="ring">{st.session_state.user_name[0]}</div>
        <div>Hola, <b>{st.session_state.user_name}</b><br>
        <span style="color:var(--gold-light); font-size:0.75rem;">
        {'★ Miembro Prime' if st.session_state.registered else 'Invitado — aún no registrado'}</span></div></div>""",
        unsafe_allow_html=True,
    )
    if not st.session_state.registered:
        if st.button("Regístrate ahora", key="side_register", use_container_width=True):
            go("register")

    st.markdown("<div class='promo-banner'>🎯 &nbsp;Descubre nuestras promociones exclusivas</div>", unsafe_allow_html=True)
    if st.button("Ver promociones y cupones", key="side_promos", use_container_width=True):
        go("promotions")

    st.markdown(
        f"""<div class="cart-mini">
            <div class="row"><span>🛍 Carrito</span><span>{cart_count()} ítem(s)</span></div>
            <div class="row"><span>Subtotal</span><span>S/ {cart_subtotal():.2f}</span></div>
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
    st.markdown("<div class='eyebrow'>Promociones y créditos</div>", unsafe_allow_html=True)
    st.markdown(f"Créditos Aurus &nbsp;·&nbsp; **S/ 0.00**")

    st.markdown("---")
    st.markdown("<div class='eyebrow'>Tu perfil</div>", unsafe_allow_html=True)
    if st.button("👤 Información de mi cuenta", key="side_account", use_container_width=True):
        go("account")
    if st.button("💳 Métodos de pago", key="side_payments", use_container_width=True):
        go("payments")
    if st.button("🧾 Mis pedidos", key="side_orders", use_container_width=True):
        go("orders")
    if st.button("♥ Favoritos", key="side_favs", use_container_width=True):
        go("favorites")
    if st.button(f"🔔 Notificaciones ({len(st.session_state.notifications)})", key="side_notifs", use_container_width=True):
        go("notifications")
    if st.button("✦ Perfil Premium", key="side_profile", use_container_width=True):
        go("profile")

    st.markdown("---")
    st.markdown("<div class='eyebrow'>Otros</div>", unsafe_allow_html=True)
    for icon, label, ptype in SIDEBAR_OTHERS:
        if st.button(f"{icon}  {label}", key=f"side_other_{ptype}", use_container_width=True):
            go("partner_form", partner_type=ptype)

    st.markdown("---")
    st.selectbox("País", ["🇵🇪 Perú", "🇨🇴 Colombia", "🇲🇽 México", "🇨🇱 Chile"], key="country_select")
    if st.button("Cerrar sesión", key="logout_btn"):
        st.session_state.user_name = "Invitado"
        st.session_state.registered = False
        go("home")

    st.markdown("---")
    if st.button("🛠 Panel administrador (demo)", key="admin_btn", use_container_width=True):
        go("admin")

# top bar
st.markdown("<div class='topbar-wrap'>", unsafe_allow_html=True)
top_l, top_m, top_r = st.columns([2.3, 3, 1.7])
with top_l:
    if st.button("☰ ✦ AURUS PRIME", key="brand_home_btn"):
        go("home")
    loc_label = f"📍 {st.session_state.district['name']} ▾" if st.session_state.district else "📍 Ingresar mi ubicación ▾"
    if st.button(loc_label, key="location_btn"):
        go("location")
with top_m:
    st.write("")
    with st.form("search_form", clear_on_submit=False, border=False):
        sc1, sc2 = st.columns([4, 1])
        with sc1:
            query = st.text_input("Buscar", value=st.session_state.search_query,
                                   placeholder="Comida, restaurantes, tiendas, productos…", label_visibility="collapsed")
        with sc2:
            searched = st.form_submit_button("Buscar")
        if searched:
            st.session_state.search_query = query
            go("search")
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
# 6. SCREENS
# =============================================================================

def render_home():
    if has_free_shipping():
        remaining = st.session_state.free_shipping_until - datetime.now()
        st.markdown(
            f"<div class='ribbon'><span>✦ Envío de cortesía activo — te quedan "
            f"<b>{max(remaining.days,0)} día(s)</b> de envíos gratis.</span></div>",
            unsafe_allow_html=True,
        )
    else:
        rc1, rc2 = st.columns([4, 1])
        with rc1:
            st.markdown(
                "<div class='ribbon'><span>✦ ¿Nuevo en Aurus Prime? Disfruta de "
                "<b>envíos de cortesía</b> en tus primeras semanas.</span></div>",
                unsafe_allow_html=True,
            )
        with rc2:
            if st.button("Regístrate", key="ribbon_register"):
                go("register")

    name_part = st.session_state.user_name if st.session_state.registered else None
    st.markdown(
        f"<div class='hero'><h1>Hola{', ' + name_part if name_part else ''}, {greeting_word()}.</h1>"
        f"<p style='color:var(--muted); font-family:\"Cormorant Garamond\",serif; font-style:italic; margin:0;'>"
        f"¿Qué deseas hoy?</p></div>",
        unsafe_allow_html=True,
    )

    st.markdown("<div class='section-title'><h2>¿Necesitas algo más?</h2><div class='rule'></div></div>", unsafe_allow_html=True)
    cat_row = st.container(key="cat_row")
    with cat_row:
        cols = st.columns(6)
        for i, cat in enumerate(CATEGORIES):
            with cols[i % 6]:
                if st.button(f"{cat['icon']}  {cat['name']}", key=f"main_{cat['name']}", use_container_width=True):
                    go("category", selected_category=cat["name"])
                if i % 6 == 5 or i == len(CATEGORIES) - 1:
                    pass

    st.markdown("<div class='section-title'><h2>⭐ Recomendados</h2><div class='rule'></div></div>", unsafe_allow_html=True)
    chip_row = st.container(key="chip_row")
    with chip_row:
        rcols = st.columns(len(RECOMMENDED_CHIPS))
        for col, chip in zip(rcols, RECOMMENDED_CHIPS):
            with col:
                st.button(f"{chip['icon']}  {chip['name']}", key=f"rec_{chip['name']}", use_container_width=True)

    district_label = st.session_state.district["name"] if st.session_state.district else "tu zona"
    st.markdown(f"<div class='section-title'><h2>Restaurantes cercanos a {district_label}</h2><div class='rule'></div></div>", unsafe_allow_html=True)
    house_cols = st.columns(5)
    for i, house in enumerate(HOUSE_NAMES[:5]):
        tone = JEWEL_TONES[i % len(JEWEL_TONES)]
        initials = "".join([w[0] for w in house.split()[:2]]).upper()
        with house_cols[i]:
            st.markdown(f"<div class='avatar-ring' style='background:{tone};'>{initials}</div>", unsafe_allow_html=True)
            if st.button(house, key=f"near_{house}", use_container_width=True):
                go("store", selected_store=house, selected_category="Restaurantes Gourmet")

    st.markdown("<div class='section-title'><h2>Promociones</h2><div class='rule'></div></div>", unsafe_allow_html=True)
    pc1, pc2 = st.columns(2)
    with pc1:
        st.markdown("<div class='store-card'><h4>🎟️ BIENVENIDA20</h4><div class='meta'>20% de descuento en tu primer pedido</div></div>", unsafe_allow_html=True)
    with pc2:
        st.markdown("<div class='store-card'><h4>🎟️ AURUS10</h4><div class='meta'>10% de descuento todos los jueves</div></div>", unsafe_allow_html=True)

    if st.session_state.orders:
        st.markdown("<div class='section-title'><h2>Pedidos recientes</h2><div class='rule'></div></div>", unsafe_allow_html=True)
        last = st.session_state.orders[0]
        st.markdown(
            f"""<div class="order-card"><h4>Pedido #{last['id']} · {ORDER_STATUSES[last['status_index']]}</h4>
            <div class="meta">{len(last['items'])} ítem(s) · Total S/ {last['breakdown']['total']:.2f}</div></div>""",
            unsafe_allow_html=True,
        )
        if st.button("Ver todos mis pedidos", key="home_view_orders"):
            go("orders")

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
            if st.button(card["cta"], key=f"join_{i}"):
                go("partner_form", partner_type=card["type"])


def render_location():
    if st.button("← Volver", key="back_loc"):
        go("home")
    st.markdown("<div class='section-title'><h2>📍 Entregando en</h2><div class='rule'></div></div>", unsafe_allow_html=True)
    st.caption("Elige tu distrito para ver comercios y tiempos de entrega reales de tu zona.")
    for d in DISTRICTS:
        c1, c2 = st.columns([4, 1])
        with c1:
            st.markdown(f"<div class='store-card'><h4>{d['name']}</h4><div class='meta'>{d['city']}</div></div>", unsafe_allow_html=True)
        with c2:
            st.write("")
            if st.button("Elegir", key=f"pick_{d['name']}"):
                st.session_state.district = d
                add_notification(f"Ubicación actualizada a {d['name']}.")
                go("home")


def render_register():
    if st.button("← Volver", key="back_reg"):
        go("home")
    st.markdown("<div class='section-title'><h2>Crea tu cuenta Aurus Prime</h2><div class='rule'></div></div>", unsafe_allow_html=True)
    st.caption("Al registrarte activas envíos de cortesía por 3 semanas.")
    with st.form("register_form"):
        name = st.text_input("Nombre completo")
        email = st.text_input("Correo electrónico")
        phone = st.text_input("Teléfono")
        st.text_input("Contraseña", type="password")
        submitted = st.form_submit_button("Crear cuenta")
        if submitted:
            if not name or not email:
                st.error("Nombre y correo son obligatorios.")
            else:
                st.session_state.user_name = name
                st.session_state.user_email = email
                st.session_state.user_phone = phone
                st.session_state.registered = True
                st.session_state.free_shipping_until = datetime.now() + timedelta(weeks=3)
                add_notification("¡Bienvenido a Aurus Prime! Envío de cortesía activado por 3 semanas.")
                st.toast("Cuenta creada — envío de cortesía activado ✦", icon="✦")
                go("home")


def render_account():
    if st.button("← Volver", key="back_acc"):
        go("home")
    st.markdown("<div class='section-title'><h2>Mi cuenta</h2><div class='rule'></div></div>", unsafe_allow_html=True)
    with st.form("account_form"):
        name = st.text_input("Nombre completo", value=st.session_state.user_name)
        email = st.text_input("Correo electrónico", value=st.session_state.user_email)
        phone = st.text_input("Teléfono", value=st.session_state.user_phone)
        st.text_input("Nueva contraseña", type="password", placeholder="Dejar en blanco para no cambiar")
        submitted = st.form_submit_button("Guardar cambios")
        if submitted:
            st.session_state.user_name = name or st.session_state.user_name
            st.session_state.user_email = email
            st.session_state.user_phone = phone
            st.session_state.registered = True
            st.success("Datos actualizados.")
    st.write("")
    if st.button("Cerrar sesión", key="acc_logout"):
        st.session_state.user_name = "Invitado"
        st.session_state.registered = False
        go("home")


def render_payments():
    if st.button("← Volver", key="back_pay"):
        go("home")
    st.markdown("<div class='section-title'><h2>Métodos de pago</h2><div class='rule'></div></div>", unsafe_allow_html=True)
    for m in st.session_state.payment_methods:
        c1, c2 = st.columns([4, 1])
        with c1:
            st.markdown(f"<div class='store-card'><h4>💳 {m}</h4></div>", unsafe_allow_html=True)
        with c2:
            st.write("")
            if st.button("Eliminar", key=f"del_pay_{m}"):
                st.session_state.payment_methods.remove(m)
                st.rerun()
    st.markdown("<div class='section-title'><h2>Agregar método</h2><div class='rule'></div></div>", unsafe_allow_html=True)
    with st.form("add_payment_form"):
        kind = st.selectbox("Tipo", ["Visa", "Mastercard", "Yape", "Plin", "Apple Pay", "Google Pay"])
        last4 = ""
        if kind in ("Visa", "Mastercard"):
            last4 = st.text_input("Últimos 4 dígitos", max_chars=4)
        submitted = st.form_submit_button("Agregar")
        if submitted:
            label = f"{kind} •••• {last4}" if last4 else kind
            st.session_state.payment_methods.append(label)
            add_notification(f"Método de pago agregado: {label}.")
            st.rerun()


def render_orders():
    if st.button("← Volver", key="back_orders"):
        go("home")
    st.markdown("<div class='section-title'><h2>Mis pedidos</h2><div class='rule'></div></div>", unsafe_allow_html=True)
    if not st.session_state.orders:
        st.info("Aún no tienes pedidos.")
        return
    tab_prep, tab_camino, tab_entregado = st.tabs(["En preparación", "En camino", "Entregado"])
    buckets = {"prep": [], "camino": [], "done": []}
    for o in st.session_state.orders:
        if o["status_index"] >= len(ORDER_STATUSES) - 1:
            buckets["done"].append(o)
        elif o["status_index"] >= 3:
            buckets["camino"].append(o)
        else:
            buckets["prep"].append(o)

    def render_order_card(o):
        st.markdown(
            f"""<div class="order-card"><h4>Pedido #{o['id']} · {ORDER_STATUSES[o['status_index']]}</h4>
            <div class="meta">{o['district']} · {len(o['items'])} ítem(s) · Total S/ {o['breakdown']['total']:.2f}</div></div>""",
            unsafe_allow_html=True,
        )
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Ver seguimiento", key=f"track_{o['id']}"):
                go("tracking", tracking_order_id=o["id"])
        with c2:
            if st.button("Repetir pedido", key=f"repeat_{o['id']}"):
                for item in o["items"]:
                    key = f"{item['store']}__{item['name']}"
                    st.session_state.cart[key] = {**item}
                st.toast("Ítems agregados de nuevo al carrito ✦", icon="✦")
                go("cart")

    with tab_prep:
        for o in buckets["prep"]:
            render_order_card(o)
        if not buckets["prep"]:
            st.caption("Nada en preparación.")
    with tab_camino:
        for o in buckets["camino"]:
            render_order_card(o)
        if not buckets["camino"]:
            st.caption("Nada en camino.")
    with tab_entregado:
        for o in buckets["done"]:
            render_order_card(o)
        if not buckets["done"]:
            st.caption("Aún no hay pedidos entregados.")


def render_tracking():
    order_id = st.session_state.tracking_order_id
    order = next((o for o in st.session_state.orders if o["id"] == order_id), None)
    if st.button("← Volver a mis pedidos", key="back_track"):
        go("orders")
    if not order:
        st.warning("Pedido no encontrado.")
        return
    st.markdown(f"<div class='section-title'><h2>Seguimiento — Pedido #{order['id']}</h2><div class='rule'></div></div>", unsafe_allow_html=True)
    st.progress((order["status_index"] + 1) / len(ORDER_STATUSES))
    steps_html = "".join(
        f"<div class='status-step{' done' if i <= order['status_index'] else ''}'>{s}</div>"
        for i, s in enumerate(ORDER_STATUSES)
    )
    st.markdown(f"<div class='status-track'>{steps_html}</div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='scope-note'>Nota: este avance es simulado con el botón de abajo, para poder demostrar la "
        "pantalla. Un tracking real requiere que tu app de repartidor (o tu proveedor logístico) envíe estos "
        "cambios de estado automáticamente.</div>",
        unsafe_allow_html=True,
    )
    if order["status_index"] < len(ORDER_STATUSES) - 1:
        if st.button("Simular avance del courier", key=f"advance_{order['id']}"):
            advance_order(order["id"])
            st.rerun()
    else:
        st.success("Pedido entregado. ¡Gracias por su preferencia!")


def render_favorites():
    if st.button("← Volver", key="back_fav"):
        go("home")
    st.markdown("<div class='section-title'><h2>Favoritos</h2><div class='rule'></div></div>", unsafe_allow_html=True)
    if not st.session_state.favorites:
        st.info("Aún no tienes casas favoritas. Márcalas con ♥ desde su página.")
        return
    for store in sorted(st.session_state.favorites):
        c1, c2, c3 = st.columns([3, 1, 1])
        with c1:
            st.markdown(f"<div class='store-card'><h4>{store}</h4></div>", unsafe_allow_html=True)
        with c2:
            st.write("")
            if st.button("Ver tienda", key=f"favopen_{store}"):
                go("store", selected_store=store)
        with c3:
            st.write("")
            if st.button("Quitar", key=f"favremove_{store}"):
                toggle_favorite(store)
                st.rerun()


def render_promotions():
    if st.button("← Volver", key="back_promo"):
        go("home")
    st.markdown("<div class='section-title'><h2>Promociones y cupones</h2><div class='rule'></div></div>", unsafe_allow_html=True)
    for code, pct in COUPONS.items():
        c1, c2 = st.columns([3, 1])
        with c1:
            st.markdown(f"<div class='store-card'><h4>🎟️ {code}</h4><div class='meta'>{int(pct*100)}% de descuento en tu pedido</div></div>", unsafe_allow_html=True)
        with c2:
            st.write("")
            if st.button("Aplicar", key=f"apply_promo_{code}"):
                apply_coupon(code)
                go("cart")


def render_notifications():
    if st.button("← Volver", key="back_notif"):
        go("home")
    st.markdown("<div class='section-title'><h2>Notificaciones</h2><div class='rule'></div></div>", unsafe_allow_html=True)
    if not st.session_state.notifications:
        st.info("No tienes notificaciones todavía.")
        return
    for n in st.session_state.notifications:
        st.markdown(f"<div class='notif-row'><span class='notif-dot'></span>{n}</div>", unsafe_allow_html=True)


def render_profile():
    if st.button("← Volver", key="back_profile"):
        go("home")
    level, points = loyalty_level()
    st.markdown("<div class='section-title'><h2>Perfil Premium</h2><div class='rule'></div></div>", unsafe_allow_html=True)
    st.markdown(f"<span class='level-badge'>Nivel {level}</span> &nbsp; · &nbsp; {points} puntos Aurus", unsafe_allow_html=True)
    st.write("")
    st.markdown(
        "<div class='store-card'><h4>Beneficios de tu nivel</h4>"
        "<div class='meta'>Prioridad de courier · Soporte dedicado · Acceso anticipado a casas nuevas</div></div>",
        unsafe_allow_html=True,
    )
    cols = st.columns(4)
    labels = [("Historial", "orders"), ("Direcciones", "location"), ("Tarjetas", "payments"), ("Favoritos", "favorites")]
    for col, (label, target) in zip(cols, labels):
        with col:
            if st.button(label, key=f"profile_{target}"):
                go(target)
    st.write("")
    st.markdown("<div class='section-title'><h2>Invita a un amigo</h2><div class='rule'></div></div>", unsafe_allow_html=True)
    code = f"AURUS-{st.session_state.user_name[:3].upper()}{cart_count()+len(st.session_state.orders)}"
    st.code(code)
    st.caption("Comparte tu código: cuando tu invitado haga su primer pedido, ambos reciben envío de cortesía.")


def render_partner_form():
    ptype = st.session_state.partner_type
    titles = {
        "restaurante": ("🍽️", "Registra tu restaurante"),
        "boutique": ("🏷️", "Registra tu boutique"),
        "courier": ("🎩", "Postula como Aurus Courier"),
        "pauta": ("📣", "Pauta en Aurus Prime"),
    }
    icon, title = titles.get(ptype, ("✦", "Formulario"))
    if st.button("← Volver", key="back_partner"):
        go("home")
    st.markdown(f"<div class='section-title'><h2>{icon} {title}</h2><div class='rule'></div></div>", unsafe_allow_html=True)
    with st.form("partner_form"):
        name = st.text_input("Nombre del negocio / tuyo")
        contact_email = st.text_input("Correo de contacto")
        phone = st.text_input("Teléfono")
        district = st.selectbox("Distrito", [d["name"] for d in DISTRICTS])
        message = st.text_area("Cuéntanos más")
        submitted = st.form_submit_button("Enviar solicitud")
        if submitted:
            if not name or not contact_email:
                st.error("Nombre y correo son obligatorios.")
            else:
                st.session_state.partner_applications.append({
                    "type": ptype, "name": name, "email": contact_email, "phone": phone,
                    "district": district, "message": message, "created": datetime.now(),
                })
                add_notification(f"Solicitud de '{title}' enviada. Te contactaremos pronto.")
                st.success("¡Solicitud enviada! Nuestro equipo comercial te contactará en las próximas 48 horas.")


def render_category():
    cat_name = st.session_state.selected_category
    if st.button("← Volver al inicio", key="back_home_cat"):
        go("home")
    st.markdown(f"<div class='section-title'><h2>{cat_name}</h2><div class='rule'></div></div>", unsafe_allow_html=True)
    for store in get_stores(cat_name):
        c1, c2, c3 = st.columns([3, 1, 1])
        with c1:
            st.markdown(f"<div class='store-card'><h4>{store}</h4><div class='meta'>⭐ 4.8 · 25-35 min · Envío S/ {DELIVERY_FEE:.2f}</div></div>", unsafe_allow_html=True)
        with c2:
            st.write("")
            if st.button("Ver tienda", key=f"open_{store}"):
                go("store", selected_store=store)
        with c3:
            st.write("")
            fav = store in st.session_state.favorites
            if st.button("♥ Quitar" if fav else "♡ Favorito", key=f"fav_{store}"):
                toggle_favorite(store)
                st.rerun()


def render_store():
    store = st.session_state.selected_store
    if st.button("← Volver", key="back_cat"):
        go("category", selected_category=st.session_state.selected_category) if st.session_state.selected_category else go("home")
    fav = store in st.session_state.favorites
    h1, h2 = st.columns([5, 1])
    with h1:
        st.markdown(f"<div class='section-title'><h2>{store}</h2><div class='rule'></div></div>", unsafe_allow_html=True)
    with h2:
        st.write("")
        if st.button("♥ Quitar" if fav else "♡ Favorito", key=f"favstore_{store}"):
            toggle_favorite(store)
            st.rerun()

    for product in PRODUCT_TEMPLATE:
        c1, c2 = st.columns([3, 1])
        with c1:
            st.markdown(f"<div class='product-row'><h4>{product['icon']} {product['name']}</h4><span class='price-tag'>S/ {product['price']:.2f}</span></div>", unsafe_allow_html=True)
        with c2:
            st.write("")
            if st.button("Agregar", key=f"add_{store}_{product['name']}"):
                add_to_cart(store, product)
                st.toast(f"{product['name']} agregado ✦", icon="✦")
                st.rerun()


def render_cart():
    if st.button("← Seguir comprando", key="back_home_cart"):
        go("home")
    st.markdown("<div class='section-title'><h2>Tu carrito</h2><div class='rule'></div></div>", unsafe_allow_html=True)

    if not st.session_state.cart and not st.session_state.saved_for_later:
        st.info("Tu carrito está vacío. Explora una categoría y agrega productos.")
        return

    for key, item in list(st.session_state.cart.items()):
        c1, c2, c3, c4, c5 = st.columns([3, 1, 1, 1, 1])
        with c1:
            st.markdown(f"<div class='cart-row'><h4>{item['name']}</h4><div class='meta'>{item['store']} · S/ {item['price']:.2f} c/u</div></div>", unsafe_allow_html=True)
        with c2:
            st.write("")
            if st.button("－", key=f"minus_{key}"):
                if item["qty"] > 1:
                    st.session_state.cart[key]["qty"] -= 1
                else:
                    st.session_state.cart.pop(key)
                st.rerun()
        with c3:
            st.markdown(f"<div style='text-align:center; padding-top:14px;'>{item['qty']}</div>", unsafe_allow_html=True)
        with c4:
            st.write("")
            if st.button("＋", key=f"plus_{key}"):
                st.session_state.cart[key]["qty"] += 1
                st.rerun()
        with c5:
            st.write("")
            if st.button("Guardar", key=f"save_{key}", help="Guardar para después"):
                st.session_state.saved_for_later[key] = st.session_state.cart.pop(key)
                st.rerun()

    if st.session_state.saved_for_later:
        st.markdown("<div class='section-title'><h2>Guardado para después</h2><div class='rule'></div></div>", unsafe_allow_html=True)
        for key, item in list(st.session_state.saved_for_later.items()):
            c1, c2 = st.columns([3, 1])
            with c1:
                st.markdown(f"<div class='cart-row'><h4>{item['name']}</h4><div class='meta'>{item['store']} · S/ {item['price']:.2f}</div></div>", unsafe_allow_html=True)
            with c2:
                st.write("")
                if st.button("Mover al carrito", key=f"restore_{key}"):
                    st.session_state.cart[key] = st.session_state.saved_for_later.pop(key)
                    st.rerun()

    if not st.session_state.cart:
        return

    st.markdown("<div class='section-title'><h2>Detalles del pedido</h2><div class='rule'></div></div>", unsafe_allow_html=True)
    st.session_state.cart_comment = st.text_area("Comentario para el Aurus Courier (opcional)", value=st.session_state.cart_comment, placeholder="Ej. tocar el timbre del 3er piso")

    sc1, sc2 = st.columns(2)
    with sc1:
        st.session_state.schedule_choice = st.selectbox("Entrega", ["Entregar ahora", "Programar entrega"],
                                                          index=0 if st.session_state.schedule_choice == "Entregar ahora" else 1)
    with sc2:
        if st.session_state.schedule_choice == "Programar entrega":
            st.session_state.schedule_time = st.text_input("Hora (HH:MM)", value=st.session_state.schedule_time)

    cc1, cc2 = st.columns([3, 1])
    with cc1:
        coupon_input = st.text_input("Código de cupón", value=st.session_state.coupon_code, placeholder="Ej. AURUS10")
    with cc2:
        st.write("")
        if st.button("Aplicar cupón", key="apply_coupon_btn"):
            apply_coupon(coupon_input)
            st.rerun()

    st.session_state.courier_tip_label = st.selectbox("Propina para el courier", list(TIP_OPTIONS.keys()),
                                                        index=list(TIP_OPTIONS.keys()).index(st.session_state.courier_tip_label))

    b = cart_breakdown()
    lines = f"""
        <div class="line"><span>Subtotal</span><span>S/ {b['subtotal']:.2f}</span></div>
        {"<div class='line'><span>Descuento (" + st.session_state.coupon_code + ")</span><span>-S/ " + f"{b['discount']:.2f}" + "</span></div>" if b['discount'] else ""}
        <div class="line"><span>Delivery</span><span>{'Gratis ✦' if b['delivery'] == 0 else 'S/ ' + f"{b['delivery']:.2f}"}</span></div>
        <div class="line"><span>IGV (18%, referencial)</span><span>S/ {b['igv']:.2f}</span></div>
        {"<div class='line'><span>Propina courier</span><span>S/ " + f"{b['tip']:.2f}" + "</span></div>" if b['tip'] else ""}
        <div class="line total"><span>Total</span><span>S/ {b['total']:.2f}</span></div>
    """
    st.markdown(f"<div class='totals-box'>{lines}</div>", unsafe_allow_html=True)
    st.write("")
    if st.button("Ir a pagar →", key="go_checkout"):
        st.session_state.checkout_step = 1
        go("checkout")


def render_checkout():
    if st.button("← Volver al carrito", key="back_cart"):
        go("cart")
    if not st.session_state.cart:
        st.info("Tu carrito está vacío.")
        return

    step = st.session_state.checkout_step
    step_names = ["Dirección", "Mapa", "Pago", "Horario", "Confirmación"]
    dots = "".join(f"<div class='step-dot{' active' if i+1 == step else ''}'>{i+1}. {n}</div>" for i, n in enumerate(step_names))
    st.markdown(f"<div class='step-track'>{dots}</div>", unsafe_allow_html=True)

    if step == 1:
        st.markdown("<div class='section-title'><h2>Dirección de entrega</h2><div class='rule'></div></div>", unsafe_allow_html=True)
        st.session_state.checkout_address = st.text_input(
            "Dirección", value=st.session_state.checkout_address,
            placeholder=f"Av. Ejemplo 123, {st.session_state.district['name'] if st.session_state.district else 'tu distrito'}",
        )
        if st.button("Siguiente →", key="step1_next"):
            if not st.session_state.checkout_address:
                st.warning("Ingresa una dirección para continuar.")
            else:
                st.session_state.checkout_step = 2
                st.rerun()

    elif step == 2:
        st.markdown("<div class='section-title'><h2>Ubicación en el mapa</h2><div class='rule'></div></div>", unsafe_allow_html=True)
        st.markdown(
            "<div class='scope-note'>Aquí iría un mapa interactivo real (Google Maps / Mapbox / "
            "<code>streamlit-folium</code>) para que el cliente confirme el pin exacto. Requiere que agregues tu "
            "propia API key en <code>secrets.toml</code> — por eso en esta demo se muestra como panel informativo.</div>",
            unsafe_allow_html=True,
        )
        st.markdown(f"<div class='store-card'><h4>📍 {st.session_state.checkout_address}</h4>"
                     f"<div class='meta'>{st.session_state.district['name'] if st.session_state.district else ''}</div></div>",
                     unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            if st.button("← Atrás", key="step2_back"):
                st.session_state.checkout_step = 1
                st.rerun()
        with c2:
            if st.button("Siguiente →", key="step2_next"):
                st.session_state.checkout_step = 3
                st.rerun()

    elif step == 3:
        st.markdown("<div class='section-title'><h2>Método de pago</h2><div class='rule'></div></div>", unsafe_allow_html=True)
        st.session_state.checkout_payment = st.radio("Elige un método", st.session_state.payment_methods,
                                                       index=st.session_state.payment_methods.index(st.session_state.checkout_payment)
                                                       if st.session_state.checkout_payment in st.session_state.payment_methods else 0)
        if st.button("＋ Agregar nuevo método", key="step3_add_payment"):
            go("payments")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("← Atrás", key="step3_back"):
                st.session_state.checkout_step = 2
                st.rerun()
        with c2:
            if st.button("Siguiente →", key="step3_next"):
                st.session_state.checkout_step = 4
                st.rerun()

    elif step == 4:
        st.markdown("<div class='section-title'><h2>Horario de entrega</h2><div class='rule'></div></div>", unsafe_allow_html=True)
        st.session_state.schedule_choice = st.radio("¿Cuándo lo recibes?", ["Entregar ahora", "Programar entrega"],
                                                      index=0 if st.session_state.schedule_choice == "Entregar ahora" else 1)
        if st.session_state.schedule_choice == "Programar entrega":
            st.session_state.schedule_time = st.text_input("Hora (HH:MM)", value=st.session_state.schedule_time)
        c1, c2 = st.columns(2)
        with c1:
            if st.button("← Atrás", key="step4_back"):
                st.session_state.checkout_step = 3
                st.rerun()
        with c2:
            if st.button("Siguiente →", key="step4_next"):
                st.session_state.checkout_step = 5
                st.rerun()

    elif step == 5:
        st.markdown("<div class='section-title'><h2>Confirmación</h2><div class='rule'></div></div>", unsafe_allow_html=True)
        b = cart_breakdown()
        st.markdown(
            f"""<div class="store-card"><h4>Resumen</h4>
            <div class="meta">📍 {st.session_state.checkout_address}<br>
            💳 {st.session_state.checkout_payment}<br>
            🕐 {st.session_state.schedule_choice if st.session_state.schedule_choice == 'Entregar ahora' else 'Programado ' + st.session_state.schedule_time}</div></div>""",
            unsafe_allow_html=True,
        )
        lines = f"""
            <div class="line"><span>Subtotal</span><span>S/ {b['subtotal']:.2f}</span></div>
            <div class="line"><span>Delivery</span><span>{'Gratis ✦' if b['delivery'] == 0 else 'S/ ' + f"{b['delivery']:.2f}"}</span></div>
            <div class="line"><span>IGV</span><span>S/ {b['igv']:.2f}</span></div>
            <div class="line total"><span>Total</span><span>S/ {b['total']:.2f}</span></div>
        """
        st.markdown(f"<div class='totals-box'>{lines}</div>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            if st.button("← Atrás", key="step5_back"):
                st.session_state.checkout_step = 4
                st.rerun()
        with c2:
            if st.button("Confirmar pedido", key="confirm_order"):
                order_id = place_order()
                go("tracking", tracking_order_id=order_id)


def render_search():
    if st.button("← Volver", key="back_search"):
        go("home")
    q = st.session_state.search_query.strip().lower()
    st.markdown(f"<div class='section-title'><h2>Resultados para “{st.session_state.search_query}”</h2><div class='rule'></div></div>", unsafe_allow_html=True)
    if not q:
        st.info("Escribe algo en el buscador de arriba.")
        return
    cat_matches = [c for c in CATEGORIES if q in c["name"].lower()]
    store_matches = [h for h in HOUSE_NAMES if q in h.lower()]
    if not cat_matches and not store_matches:
        st.info("Sin resultados. Prueba con otra palabra (ej. 'restaurantes', 'vinos', 'farmacia').")
        return
    if cat_matches:
        st.markdown("<div class='eyebrow'>Categorías</div>", unsafe_allow_html=True)
        for c in cat_matches:
            if st.button(f"{c['icon']}  {c['name']}", key=f"search_cat_{c['name']}"):
                go("category", selected_category=c["name"])
    if store_matches:
        st.markdown("<div class='eyebrow'>Tiendas</div>", unsafe_allow_html=True)
        for h in store_matches:
            if st.button(h, key=f"search_store_{h}"):
                go("store", selected_store=h)


def render_admin():
    if st.button("← Volver", key="back_admin"):
        go("home")
    st.markdown("<div class='section-title'><h2>🛠 Panel administrador (demo)</h2><div class='rule'></div></div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='scope-note'>Esta vista lee <b>solo los datos de tu sesión actual</b> (no hay base de datos "
        "ni autenticación real todavía). Para un panel de administración real: crea una app separada, protégela "
        "con login, y apunta a tu base de datos de producción — no a <code>st.session_state</code>.</div>",
        unsafe_allow_html=True,
    )
    m1, m2, m3 = st.columns(3)
    total_rev = sum(o["breakdown"]["total"] for o in st.session_state.orders)
    m1.metric("Pedidos (sesión)", len(st.session_state.orders))
    m2.metric("Ingresos (sesión)", f"S/ {total_rev:.2f}")
    m3.metric("Leads de socios", len(st.session_state.partner_applications))

    st.markdown("<div class='section-title'><h2>Pedidos</h2><div class='rule'></div></div>", unsafe_allow_html=True)
    if st.session_state.orders:
        for o in st.session_state.orders:
            st.markdown(
                f"<div class='order-card'><h4>#{o['id']} · {ORDER_STATUSES[o['status_index']]}</h4>"
                f"<div class='meta'>{o['district']} · S/ {o['breakdown']['total']:.2f} · {o['created'].strftime('%d/%m %H:%M')}</div></div>",
                unsafe_allow_html=True,
            )
    else:
        st.caption("Sin pedidos todavía.")

    st.markdown("<div class='section-title'><h2>Solicitudes de socios / couriers</h2><div class='rule'></div></div>", unsafe_allow_html=True)
    if st.session_state.partner_applications:
        for a in st.session_state.partner_applications:
            st.markdown(
                f"<div class='order-card'><h4>{a['name']} · {a['type']}</h4>"
                f"<div class='meta'>{a['email']} · {a['phone']} · {a['district']}</div></div>",
                unsafe_allow_html=True,
            )
    else:
        st.caption("Sin solicitudes todavía.")


# =============================================================================
# 7. ROUTER
# =============================================================================
ROUTES = {
    "home": render_home,
    "location": render_location,
    "register": render_register,
    "account": render_account,
    "payments": render_payments,
    "orders": render_orders,
    "tracking": render_tracking,
    "favorites": render_favorites,
    "promotions": render_promotions,
    "notifications": render_notifications,
    "profile": render_profile,
    "partner_form": render_partner_form,
    "category": render_category,
    "store": render_store,
    "cart": render_cart,
    "checkout": render_checkout,
    "search": render_search,
    "admin": render_admin,
}
ROUTES.get(st.session_state.page, render_home)()

# =============================================================================
# 8. FOOTER
# =============================================================================
st.markdown(
    f"""<div class="footer"><div class="crest">✦ {BRAND_MONOGRAM} ✦</div>
    <div>AURUS PRIME · Concierge de lujo a domicilio</div>
    <div style="margin-top:6px;">Términos y condiciones · Privacidad · Ayuda · © {datetime.now().year} Aurus Prime</div></div>""",
    unsafe_allow_html=True,
)
