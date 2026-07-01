# Aurus Prime

Concierge de lujo a domicilio — app web construida en **Streamlit**, con diseño
propio en negro obsidiana y dorado antiguo (tipografías Playfair Display /
Cormorant Garamond / Inter).

## Estructura del repositorio

```
aurus-prime/
├── app.py                    # Aplicación principal (todo el front-end)
├── requirements.txt          # Dependencias
├── .streamlit/
│   └── config.toml           # Tema oscuro/dorado nativo de Streamlit
└── README.md
```

## Ejecutar en local

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

La app abrirá en `http://localhost:8501`.

## Subir a GitHub

```bash
git init
git add .
git commit -m "Aurus Prime: home luxury design"
git branch -M main
git remote add origin https://github.com/<tu-usuario>/aurus-prime.git
git push -u origin main
```

## Publicar en Streamlit Community Cloud (streamlit.io)

1. Entra a https://share.streamlit.io e inicia sesión con tu cuenta de GitHub.
2. Clic en **"New app"**.
3. Selecciona el repositorio `aurus-prime`, la rama `main` y el archivo
   principal `app.py`.
4. Clic en **"Deploy"**. En 1–2 minutos tendrás una URL pública tipo
   `https://aurus-prime.streamlit.app`.

Cualquier `git push` posterior a `main` actualiza la app automáticamente.

## Arquitectura (v3 — navegación funcional)

La app ya no es solo una landing decorativa: implementa un **router por
`st.session_state.page`** con pantallas reales y un carrito funcional:

```
Home ──▶ Categoría ──▶ Tienda ──▶ Carrito ──▶ Checkout ──▶ Confirmación
```

- **Capa de datos** (`# 2. DATA LAYER`): `CATEGORIES`, `HOUSE_NAMES` (tiendas),
  `PRODUCT_TEMPLATE` (menú). Reemplázalos por consultas a tu base de datos
  real cuando pases a producción — el resto del código no cambia.
- **Capa de estado** (`# 3. STATE LAYER`): helpers `go()`, `add_to_cart()`,
  `cart_total()`, etc. Todo botón funcional pasa por `go(pagina, **params)`.
- **Pantallas** (`# 6. SCREENS`): una función `render_*()` por pantalla,
  totalmente independiente entre sí.
- **Router** (`# 7. ROUTER`): un diccionario `{nombre: función}` que decide
  qué pantalla dibujar según `st.session_state.page`.

### Para llevarlo a producción real
1. Reemplaza `HOUSE_NAMES` / `PRODUCT_TEMPLATE` por tablas reales (Postgres,
   Supabase, Firebase, o una API propia).
2. Reemplaza el carrito en memoria (`st.session_state.cart`) por un carrito
   persistido por usuario en tu base de datos (así no se pierde al recargar
   o cambiar de dispositivo).
3. Conecta `render_checkout()` a una pasarela de pagos real (Culqi, Niubiz,
   MercadoPago, Stripe) en vez del formulario de demostración.
4. Añade autenticación real (hoy el usuario "GRUPO" es fijo/demo).

