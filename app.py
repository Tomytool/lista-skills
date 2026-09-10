import io
import re
import requests
import streamlit as st
import pandas as pd

# 1. Configuración de la página
st.set_page_config(
    page_title="Explorador de Skills & Herramientas",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilo personalizado CSS para mejorar la interfaz visual
st.markdown("""
    <style>
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    .stMetric {
        background-color: rgba(255, 255, 255, 0.05);
        padding: 12px;
        border-radius: 10px;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    .skill-card {
        background-color: rgba(255, 255, 255, 0.03);
        border-radius: 8px;
        padding: 16px;
        border-left: 4px solid #FF4B4B;
        margin-bottom: 12px;
    }
    .help-box {
        background-color: rgba(255, 193, 7, 0.1);
        border-left: 4px solid #FFC107;
        padding: 14px;
        border-radius: 6px;
        margin-top: 10px;
        margin-bottom: 15px;
    }
    </style>
""", unsafe_allow_html=True)

# URL constante del Google Sheet en formato CSV por defecto
CSV_URL_DEFAULT = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR3z_hlX_WkRK2sAfZZkqUOii4teKxls4jCIUU0QDO-1mZ2zDfWt_ZowiRFmLRCfUW8t80J4Z2AVN0F/pub?gid=1796871755&single=true&output=csv"

def transformar_url_google_sheets(url: str) -> str:
    """
    Transforma enlaces comunes de Google Sheets en enlaces de exportación CSV válidos.
    """
    url = url.strip()
    # Si es una URL estándar de edición o vista de Google Sheets
    match_edit = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', url)
    if match_edit and not url.startswith("https://docs.google.com/spreadsheets/d/e/"):
        sheet_id = match_edit.group(1)
        gid_match = re.search(r'[#&?]gid=(\d+)', url)
        gid_param = f"&gid={gid_match.group(1)}" if gid_match else ""
        return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv{gid_param}"
    
    # Si es una URL de publicación en la web (/pub) pero falta output=csv
    if "/pub" in url and "output=csv" not in url:
        sep = "&" if "?" in url else "?"
        return f"{url}{sep}output=csv"
        
    return url

# 2. Función en caché para cargar los datos desde la URL
@st.cache_data(ttl=600)
def cargar_datos(url: str) -> pd.DataFrame:
    url_procesada = transformar_url_google_sheets(url)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(url_procesada, headers=headers, timeout=12)
        
        if response.status_code == 400:
            st.error("❌ **HTTP Error 400: Bad Request al conectar con Google Sheets**")
            st.markdown("""
            <div class="help-box">
                <h4>⚠️ ¿Por qué ocurre este error y cómo solucionarlo?</h4>
                <p>Google Sheets devuelve un error <strong>400 Bad Request</strong> debido a una de las siguientes razones:</p>
                <ul>
                    <li><strong>No publicado como CSV:</strong> La hoja fue publicada en la web como <em>"Página web" (HTML)</em> en lugar de <em>"Valores separados por comas (.csv)"</em>.</li>
                    <li><strong>GID o pestaña inválida:</strong> El ID de pestaña (<code>gid=...</code>) no existe o la hoja fue despublicada.</li>
                </ul>
                <hr>
                <h4>📋 Pasos para publicar correctamente la Hoja en Google Sheets:</h4>
                <ol>
                    <li>Abre tu hoja de cálculo en Google Sheets.</li>
                    <li>Ve al menú superior: <strong>Archivo ➔ Compartir ➔ Publicar en la web</strong>.</li>
                    <li>En la ventana emergente, selecciona la pestaña correspondiente (o todo el documento).</li>
                    <li>En el segundo desplegable, cambia <em>"Página web"</em> por <strong>"Valores separados por comas (.csv)"</strong>.</li>
                    <li>Haz clic en <strong>Publicar</strong> y copia el enlace generado.</li>
                    <li>Copia ese enlace y pégalo en el panel lateral (Sidebar) en <strong>"🔗 Cambiar URL de Google Sheets"</strong>.</li>
                </ol>
                <p>💡 <em>Alternativa rápida:</em> Puedes hacer pública la hoja (<em>"Cualquier persona con el enlace puede ver"</em>) y pegar aquí la URL normal del navegador (ej: <code>https://docs.google.com/spreadsheets/d/.../edit</code>).</p>
            </div>
            """, unsafe_allow_html=True)
            return pd.DataFrame()

        response.raise_for_status()
        
        # Leer el contenido CSV obtenido
        df = pd.read_csv(io.StringIO(response.text))
        
        # Limpieza básica de espacios y minúsculas en nombres de columnas
        df.columns = df.columns.str.strip().str.lower()
        
        # Mapeo de variaciones de nombres de columnas a nombres estándar esperados
        column_mapping = {
            'nombre_skills': 'nombre_skill',
            'llamada_skills': 'como_llamar',
            'uso_skills': 'usos_posibles',
            'formato_salida': 'formatos_entrega',
            'formatos_de_entrega': 'formatos_entrega',
            'usos': 'usos_posibles',
        }
        df = df.rename(columns=column_mapping)
        
        # Garantizar presencia de columnas requeridas para evitar KeyErrors
        columnas_requeridas = ['nombre_skill', 'como_llamar', 'descripcion', 'formatos_entrega', 'usos_posibles']
        for col in columnas_requeridas:
            if col not in df.columns:
                df[col] = ""

        # Asegurar que los valores nulos se traten como cadenas vacías para evitar errores en búsquedas
        df = df.fillna("")
        return df

    except requests.exceptions.RequestException as e:
        st.error(f"Error de red o conexión al intentar obtener los datos: {e}")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error al procesar los datos desde la URL: {e}")
        return pd.DataFrame()


# 3. Menú Lateral (Sidebar) con Filtros y Fuente de Datos
st.sidebar.image("https://streamlit.io/images/brand/streamlit-mark-color.png", width=50)
st.sidebar.title("🎛️ Configuración y Filtros")
st.sidebar.markdown("---")

with st.sidebar.expander("🔗 Fuente de Datos (Google Sheets / CSV)", expanded=False):
    url_input = st.text_input(
        "URL de Google Sheets",
        value=CSV_URL_DEFAULT,
        help="Pega aquí la URL de tu Google Sheet (enlace de publicación CSV o enlace normal de edición/vista)."
    )
    uploaded_file = st.file_uploader("O sube un archivo CSV local", type=["csv"])

# Cargar los datos desde archivo subido o URL
if uploaded_file is not None:
    try:
        df_raw = pd.read_csv(uploaded_file)
        df_raw.columns = df_raw.columns.str.strip().str.lower()
        column_mapping = {
            'nombre_skills': 'nombre_skill',
            'llamada_skills': 'como_llamar',
            'uso_skills': 'usos_posibles',
            'formato_salida': 'formatos_entrega',
            'formatos_de_entrega': 'formatos_entrega',
            'usos': 'usos_posibles',
        }
        df_raw = df_raw.rename(columns=column_mapping)
        for col in ['nombre_skill', 'como_llamar', 'descripcion', 'formatos_entrega', 'usos_posibles']:
            if col not in df_raw.columns:
                df_raw[col] = ""
        df_raw = df_raw.fillna("")
        st.sidebar.success("✅ Datos cargados desde archivo CSV local.")
    except Exception as e:
        st.sidebar.error(f"Error al leer CSV subido: {e}")
        df_raw = pd.DataFrame()
else:
    target_url = url_input if url_input.strip() else CSV_URL_DEFAULT
    df_raw = cargar_datos(target_url)

if df_raw.empty:
    st.warning("⚠️ No se pudieron cargar los datos desde la fuente especificada. Revisa las instrucciones en pantalla o cambia la URL en el panel lateral.")
    st.stop()


# Obtener lista única de formatos de entrega
todos_formatos = set()
for items in df_raw["formatos_entrega"].dropna():
    if isinstance(items, str):
        # Separar formatos si vienen delimitados por comas o diagonales
        formatos = [f.strip() for f in items.replace("/", ",").split(",") if f.strip()]
        todos_formatos.update(formatos)
lista_formatos = sorted(list(todos_formatos))

# Selector 1: Formatos de entrega (Multiselect)
formatos_seleccionados = st.sidebar.multiselect(
    "📦 Formatos de Entrega",
    options=lista_formatos,
    default=[],
    help="Filtra las habilidades que contengan al menos uno de los formatos seleccionados."
)

# Selector 2: Nombre de la Skill (Selectbox / Multiselect)
lista_nombres = sorted(df_raw["nombre_skill"].unique().tolist())
nombres_seleccionados = st.sidebar.multiselect(
    "🔍 Nombre de la Skill",
    options=lista_nombres,
    default=[],
    help="Filtra por nombre(s) específico(s) de skill."
)

# Opción extra de búsqueda por palabra clave en la descripción
busqueda_texto = st.sidebar.text_input(
    "🔎 Buscar por palabra clave",
    placeholder="Ej. Python, API, PDF...",
    help="Filtra por coincidencias en cualquier campo de texto."
)

# Botón para limpiar filtros
if st.sidebar.button("🔄 Restablecer Filtros"):
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.info("💡 **Tip:** Deja los selectores vacíos para ver el listado completo.")

# 4. Lógica de Filtrado de Datos
df_filtrado = df_raw.copy()

# Filtrar por Nombre
if nombres_seleccionados:
    df_filtrado = df_filtrado[df_filtrado["nombre_skill"].isin(nombres_seleccionados)]

# Filtrar por Formatos de Entrega
if formatos_seleccionados:
    def contiene_formato(cadena_formatos):
        if not isinstance(cadena_formatos, str):
            return False
        return any(fmt.lower() in cadena_formatos.lower() for fmt in formatos_seleccionados)
    
    df_filtrado = df_filtrado[df_filtrado["formatos_entrega"].apply(contiene_formato)]

# Filtrar por texto libre
if busqueda_texto:
    query = busqueda_texto.lower()
    df_filtrado = df_filtrado[
        df_filtrado["nombre_skill"].astype(str).str.lower().str.contains(query) |
        df_filtrado["descripcion"].astype(str).str.lower().str.contains(query) |
        df_filtrado["usos_posibles"].astype(str).str.lower().str.contains(query)
    ]

# 5. Encabezado Principal y Métricas
st.title("🚀 Catálogo Interactivo de Skills de Streamlit")
st.caption("Visualizador de catálogo en tiempo real alimentado desde Google Sheets CSV.")

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total de Skills", len(df_raw))
with col2:
    st.metric("Skills Filtradas", len(df_filtrado))
with col3:
    st.metric("Formatos Disponibles", len(lista_formatos))

st.markdown("---")

# 6. Muestra del DataFrame en pantalla
st.subheader("📊 Tabla de Datos")

if df_filtrado.empty:
    st.info("No se encontraron habilidades que coincidan con los filtros seleccionados.")
else:
    # Configuración de columnas interactivas de Streamlit
    st.dataframe(
        df_filtrado,
        use_container_width=True,
        hide_index=True,
        column_config={
            "nombre_skill": st.column_config.TextColumn("Nombre de Skill", width="medium"),
            "como_llamar": st.column_config.TextColumn("Comando / Invocación", width="medium"),
            "descripcion": st.column_config.TextColumn("Descripción", width="large"),
            "formatos_entrega": st.column_config.TextColumn("Formatos de Entrega", width="medium"),
            "usos_posibles": st.column_config.TextColumn("Usos Posibles", width="large")
        }
    )

    # 7. Vista Detallada opcional
    with st.expander("📌 Ver Detalle Individual de una Skill"):
        skill_seleccionada = st.selectbox(
            "Selecciona una skill para examinar:",
            options=df_filtrado["nombre_skill"].unique()
        )
        if skill_seleccionada:
            fila = df_filtrado[df_filtrado["nombre_skill"] == skill_seleccionada].iloc[0]
            st.markdown(f"### {fila['nombre_skill']}")
            st.markdown(f"**Invocación:** `{fila['como_llamar']}`")
            st.markdown(f"**Formatos de Entrega:** `{fila['formatos_entrega']}`")
            st.markdown(f"**Descripción:** {fila['descripcion']}")
            st.markdown(f"**Usos Posibles:** {fila['usos_posibles']}")

    # 8. Descarga de datos filtrados
    csv_data = df_filtrado.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Descargar Datos Filtrados (CSV)",
        data=csv_data,
        file_name="skills_filtradas.csv",
        mime="text/csv"
    )
