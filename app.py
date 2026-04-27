import streamlit as st
from streamlit.connections import GSheetsConnection
import pandas as pd

# 1. Configuración
st.set_page_config(page_title="Control Hand Over VN", layout="wide", page_icon="✅")

st.title("🚗 Control de Garantías y Hand Over")

# 2. Conexión
conn = st.connection("gsheets", type=GSheetsConnection)
url = "https://docs.google.com/spreadsheets/d/1-ziHRIEWQZUxFUBGqoweX6PvY6sDgoaXGcueSUd9370/edit#gid=1482583153"

try:
    df = conn.read(spreadsheet=url)
    df = df.dropna(how='all')

    # Convertir columna de fecha a formato fecha por si viene como texto
    if 'Fecha de Hand over' in df.columns:
        df['Fecha de Hand over'] = pd.to_datetime(df['Fecha de Hand over'], errors='coerce')

    # --- LÓGICA DE NEGOCIO ---
    # Unidades aptas: Estado es Entregado
    df_entregados = df[df['Estado'].str.upper() == 'ENTREGADO'] if 'Estado' in df.columns else pd.DataFrame()
    
    # Pendientes de Hand Over: Están entregados pero NO tienen fecha
    pendientes_ho = df_entregados[df_entregados['Fecha de Hand over'].isna()]
    
    # Realizados: Tienen fecha
    realizados_ho = df[df['Fecha de Hand over'].notna()]

    # --- INDICADORES ---
    st.subheader("📊 Estado del Proceso (Hand Over)")
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.metric("Total Entregados", len(df_entregados))
    with c2:
        st.metric("Hand Over Pendientes", len(pendientes_ho), delta_color="inverse")
    with c3:
        progreso = (len(realizados_ho) / len(df_entregados) * 100) if len(df_entregados) > 0 else 0
        st.metric("Cumplimiento", f"{progreso:.1f}%")

    # --- ALERTAS CRÍTICAS ---
    if len(pendientes_ho) > 0:
        st.warning(f"⚠️ Atención: Hay {len(pendientes_ho)} unidades entregadas que aún no tienen fecha de Hand Over.")

    # --- FILTROS Y TABLA ---
    st.divider()
    modo_vista = st.radio("Ver unidades:", ["Todas", "Solo Pendientes de Hand Over", "Solo Realizados"])

    if modo_vista == "Solo Pendientes de Hand Over":
        df_display = pendientes_ho
    elif modo_vista == "Solo Realizados":
        df_display = realizados_ho
    else:
        df_display = df

    st.dataframe(df_display, use_container_width=True, hide_index=True)

except Exception as e:
    st.error("Error al procesar las reglas de Hand Over.")
    st.write(e)
