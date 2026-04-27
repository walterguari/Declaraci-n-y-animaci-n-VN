import streamlit as st
from streamlit.connections import GSheetsConnection
import pandas as pd

# 1. Configuración de pantalla
st.set_page_config(page_title="Control Hand Over VN", layout="wide", page_icon="✅")

st.title("🚗 Gestión de Hand Over - Unidades Entregadas")

# 2. Conexión a la base
conn = st.connection("gsheets", type=GSheetsConnection)
url = "https://docs.google.com/spreadsheets/d/1-ziHRIEWQZUxFUBGqoweX6PvY6sDgoaXGcueSUd9370/edit#gid=1482583153"

try:
    df = conn.read(spreadsheet=url)
    df = df.dropna(how='all')

    # --- LIMPIEZA AUTOMÁTICA DE COLUMNAS ---
    # Convertimos todos los nombres de columnas a MAYÚSCULAS y quitamos espacios
    df.columns = [str(c).strip().upper() for c in df.columns]

    # Ahora buscamos las columnas por su nombre en mayúsculas
    col_estado = 'ESTADO'
    col_handover = 'FECHA DE HAND OVER'

    if col_estado not in df.columns:
        st.error(f"⚠️ No encuentro la columna 'Estado'. Las columnas detectadas son: {list(df.columns)}")
        st.stop()
    
    # Si no encuentra la de fecha, la crea vacía para que no de error
    if col_handover not in df.columns:
        df[col_handover] = pd.NA

    # Convertimos a formato fecha
    df[col_handover] = pd.to_datetime(df[col_handover], errors='coerce')

    # --- LÓGICA DE NEGOCIO ---
    # Buscamos la palabra "ENTREGADO" en la columna de estado
    es_entregado = df[col_estado].astype(str).str.upper().str.contains('ENTREGADO', na=False)
    tiene_ho = df[col_handover].notna()

    # Segmentos
    pendientes_ho = df[es_entregado & ~tiene_ho]
    realizados_ho = df[es_entregado & tiene_ho]

    # --- TABLERO DE INDICADORES ---
    st.subheader("📊 Resumen de Hand Over")
    m1, m2, m3 = st.columns(3)
    
    total_entregados = len(df[es_entregado])
    m1.metric("Total Entregados", total_entregados)
    m2.metric("Pendientes de HO", len(pendientes_ho), delta="- Acción urgente", delta_color="inverse")
    
    porcentaje = (len(realizados_ho) / total_entregados * 100) if total_entregados > 0 else 0
    m3.metric("Eficiencia", f"{porcentaje:.1f}%")

    # --- TABLA Y FILTROS ---
    st.divider()
    opcion = st.radio("Filtrar unidades:", ["Ver Todas", "⚠️ Pendientes de Hand Over", "✅ Hand Over Listos"], horizontal=True)

    if opcion == "⚠️ Pendientes de Hand Over":
        df_final = pendientes_ho
    elif opcion == "✅ Hand Over Listos":
        df_final = realizados_ho
    else:
        df_final = df

    st.dataframe(df_final, use_container_width=True, hide_index=True)

except Exception as e:
    st.error("Ocurrió un error al cargar los datos.")
    st.write("Detalle:", e)
