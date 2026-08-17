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
    </style>
""", unsafe_allow_html=True)

# URL constante del Google Sheet en formato CSV
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR3z_hlX_WkRK2sAfZZkqUOii4teKxls4jCIUU0QDO-1mZ2zDfWt_ZowiRFmLRCfUW8t80J4Z2AVN0F/pub?gid=1796871755&single=true&output=csv"

# 2. Función en caché para cargar los datos desde la URL
@st.cache_data(ttl=600)
def cargar_datos(url: str) -> pd.DataFrame:
    try:
        df = pd.read_csv(url)
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
    except Exception as e:
        st.error(f"Error al cargar los datos desde la URL: {e}")
        return pd.DataFrame()

# Cargar los datos
df_raw = cargar_datos(CSV_URL)

if df_raw.empty:
    st.warning("No se pudieron cargar datos desde la fuente especificada.")
    st.stop()

# 3. Menú Lateral (Sidebar) con Filtros
st.sidebar.image("https://streamlit.io/images/brand/streamlit-mark-color.png", width=50)
st.sidebar.title("🎛️ Filtros y Controles")
st.sidebar.markdown("---")

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
