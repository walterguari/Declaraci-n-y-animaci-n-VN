import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. Configuración de pantalla
st.set_page_config(page_title="Control Hand Over VN", layout="wide", page_icon="✅")

st.title("🚗 Gestión de Hand Over - Unidades Entregadas")

# 2. Conexión a la base
conn = st.connection("gsheets", type=GSheetsConnection)
url = "https://docs.google.com/spreadsheets/d/1-ziHRIEWQZUxFUBGqoweX6PvY6sDgoaXGcueSUd9370/edit#gid=1482583153"

try:
    # Lectura de datos
    df = conn.read(spreadsheet=url)
    df = df.dropna(how='all')

    # Limpieza de nombres de columnas (Quita espacios y pasa a MAYÚSCULAS)
    df.columns = [str(c).strip().upper() for c in df.columns]

    # Identificar columnas dinámicamente
    col_estado = next((c for c in df.columns if "ESTADO" in c), None)
    col_ho = next((c for c in df.columns if "HAND OVER" in c or "HANDOVER" in c), None)

    if not col_estado:
        st.error(f"❌ No encuentro la columna 'Estado'. Columnas detectadas: {list(df.columns)}")
        st.stop()

    # Asegurar que la columna de fecha sea reconocida
    if col_ho:
        df[col_ho] = pd.to_datetime(df[col_ho], errors='coerce')
    else:
        df[col_ho] = pd.NA

    # --- LÓGICA DE NEGOCIO ---
    # Unidades entregadas
    es_entregado = df[col_estado].astype(str).str.upper().str.contains('ENTREGADO', na=False)
    # Tienen fecha de Hand Over
    tiene_ho = df[col_ho].notna()

    pendientes = df[es_entregado & ~tiene_ho]
    completados = df[es_entregado & tiene_ho]

    # --- DASHBOARD ---
    st.subheader("📊 Resumen de Gestión")
    m1, m2, m3 = st.columns(3)
    
    total_entregados = len(df[es_entregado])
    m1.metric("Total Entregados", total_entregados)
    m2.metric("Pendientes HO", len(pendientes), delta="- Acción Urgente", delta_color="inverse")
    
    eficiencia = (len(completados) / total_entregados * 100) if total_entregados > 0 else 0
    m3.metric("Eficiencia Hand Over", f"{eficiencia:.1f}%")

    # --- TABLA Y FILTROS ---
    st.divider()
    vista = st.radio("Filtrar por prioridad:", ["Todas", "Solo Pendientes ⚠️", "Completados ✅"], horizontal=True)

    if vista == "Solo Pendientes ⚠️":
        df_final = pendientes
    elif vista == "Completados ✅":
        df_final = completados
    else:
        df_final = df

    st.dataframe(df_final, use_container_width=True, hide_index=True)

except Exception as e:
    st.error("Hubo un problema al procesar los datos.")
    st.write("Error técnico:", e)
