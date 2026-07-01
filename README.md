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

## Personalización rápida

Todo el contenido (categorías, marcas destacadas, textos de las tarjetas de
adhesión, ciudades disponibles) vive en la sección **`# 2. DATA`** al inicio
de `app.py`, separada del código de layout — puedes editar el catálogo sin
tocar el diseño.

Los tokens de color y tipografía están centralizados en el bloque
`CUSTOM_CSS` (sección **`# 4. DESIGN SYSTEM`**) mediante variables CSS
(`--bg`, `--gold`, `--ivory`, etc.), por lo que puedes ajustar la paleta
completa cambiando unos pocos valores hexadecimales.
