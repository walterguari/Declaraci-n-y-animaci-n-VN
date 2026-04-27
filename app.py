import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. Configuración de la página
st.set_page_config(page_title="Control de Garantías VN", layout="wide", page_icon="🛡️")

st.title("🛡️ Gestión de Hand Over y Garantías")

# 2. Conexión a Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)
url_base = "https://docs.google.com/spreadsheets/d/1-ziHRIEWQZUxFUBGqoweX6PvY6sDgoaXGcueSUd9370/edit#gid=1482583153"

# Definición de las columnas que pediste (en orden)
COLUMNAS_MOSTRAR = [
    "Canal de Venta", "Vendedor", "Cliente", "Teléfono", "E-mail", 
    "Chasis", "Marca", "Modelo", "Fecha de Patentamiento", "Patente", 
    "Estado Administrativo", "Observacion de la Documentación", 
    "Estado de Unidad por Administración/Mayorista", "Estado", 
    "Fecha de confirmacion de entrega", "Encuesta Temprana", 
    "Comentario Enc. Temp.", "EI - Reco", "Comentario de la Encuesta interna", 
    "EI - CSI", "ESTADO INTERNO", "Fecha de Hand over" # Agregamos la de control al final
]

try:
    df_raw = conn.read(spreadsheet=url_base)
    df = df_raw.dropna(how='all')

    # --- NORMALIZACIÓN DE NOMBRES ---
    # Limpiamos espacios para asegurar que coincidan con tu lista
    df.columns = [str(c).strip() for c in df.columns]

    # Verificamos cuáles de las columnas pedidas existen realmente en el Excel
    cols_presentes = [c for c in COLUMNAS_MOSTRAR if c in df.columns]
    
    # --- PROCESAMIENTO DE LÓGICA ---
    # Hand Over: Fecha cargada = Garantía OK / Vacío = Sin Garantía
    if "Fecha de Hand over" in df.columns:
        df['FECHA_HO_DT'] = pd.to_datetime(df["Fecha de Hand over"], errors='coerce')
        df['TIENE_GARANTIA'] = df['FECHA_HO_DT'].notna()
    else:
        df['TIENE_GARANTIA'] = False

    # Estado Entregado
    if "Estado" in df.columns:
        df['ES_ENTREGADO'] = df["Estado"].astype(str).str.upper().str.contains('ENTREGADO', na=False)
    else:
        df['ES_ENTREGADO'] = False

    # --- MÉTRICAS ---
    st.subheader("📊 Resumen de Estado")
    m1, m2, m3 = st.columns(3)
    
    entregados = df[df['ES_ENTREGADO']]
    pendientes = entregados[~entregados['TIENE_GARANTIA']]
    
    m1.metric("Total Entregados", len(entregados))
    m2.metric("Pendientes de Garantía", len(pendientes), delta="- Acción Crítica" if len(pendientes) > 0 else "Al día", delta_color="inverse")
    
    eficiencia = (len(entregados[entregados['TIENE_GARANTIA']]) / len(entregados) * 100) if len(entregados) > 0 else 0
    m3.metric("Eficacia Hand Over", f"{eficiencia:.1f}%")

    # --- FILTROS ---
    st.divider()
    vista = st.pills("Seleccionar Vista:", ["Todas las Unidades", "⚠️ Solo Pendientes de Hand Over", "✅ Garantías Declaradas"], default="Todas las Unidades")

    if vista == "⚠️ Solo Pendientes de Hand Over":
        df_final = pendientes
    elif vista == "✅ Garantías Declaradas":
        df_final = df[df['TIENE_GARANTIA']]
    else:
        df_final = df

    # Buscador por texto
    busqueda = st.text_input("🔍 Buscar por Cliente, Chasis o Vendedor:")
    if busqueda:
        mask = df_final.apply(lambda row: row.astype(str).str.contains(busqueda, case=False).any(), axis=1)
        df_final = df_final[mask]

    # --- MOSTRAR TABLA CON TUS COLUMNAS ---
    # Solo mostramos las columnas que pediste y que existen en el archivo
    df_mostrar = df_final[cols_presentes]
    
    st.dataframe(
        df_mostrar,
        use_container_width=True,
        hide_index=True
    )

except Exception as e:
    st.error("Error al cargar la tabla con las columnas especificadas.")
    st.write("Asegúrate de que los nombres de las columnas en el Excel coincidan exactamente.")
    with st.expander("Ver detalle técnico"):
        st.write(e)
