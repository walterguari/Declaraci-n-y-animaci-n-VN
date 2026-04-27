import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. Configuración de la página
st.set_page_config(page_title="Control de Garantías VN", layout="wide", page_icon="🛡️")

st.title("🛡️ Control de Garantías (Hand Over)")

# 2. Conexión a Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)
url_base = "https://docs.google.com/spreadsheets/d/1-ziHRIEWQZUxFUBGqoweX6PvY6sDgoaXGcueSUd9370/edit#gid=1482583153"

try:
    df = conn.read(spreadsheet=url_base)
    df = df.dropna(how='all')

    # --- IDENTIFICACIÓN DE COLUMNAS ---
    cols_mapeo = {str(c).strip().upper(): c for c in df.columns}
    col_ho_real = next((orig for norm, orig in cols_mapeo.items() if "HAND" in norm), None)
    col_estado_real = next((orig for norm, orig in cols_mapeo.items() if "ESTADO" in norm), None)

    if not col_ho_real:
        st.error("No se encontró la columna 'Fecha de Hand over'.")
        st.stop()

    # --- PROCESAMIENTO ---
    # Convertimos a fecha y detectamos quién tiene garantía (fecha NO nula)
    df['TIENE_GARANTIA'] = pd.to_datetime(df[col_ho_real], errors='coerce').notna()
    
    # Identificamos entregados (solo a estos se les exige garantía)
    df['ES_ENTREGADO'] = df[col_estado_real].astype(str).str.upper().str.contains('ENTREGADO', na=False)

    # --- SEGMENTACIÓN ---
    pendientes = df[df['ES_ENTREGADO'] & ~df['TIENE_GARANTIA']]
    con_garantia = df[df['TIENE_GARANTIA']]
    
    # --- DASHBOARD ---
    st.subheader("📊 Resumen de Cobertura")
    m1, m2, m3 = st.columns(3)
    
    m1.metric("Unidades con Garantía", len(con_garantia))
    m2.metric("Pendientes (Entregados sin fecha)", len(pendientes), delta="Acción requerida", delta_color="inverse")
    
    # Eficiencia basada en lo que DEBERÍA tener garantía (los entregados)
    total_a_controlar = len(df[df['ES_ENTREGADO']])
    eficiencia = (len(df[df['ES_ENTREGADO'] & df['TIENE_GARANTIA']]) / total_a_controlar * 100) if total_a_controlar > 0 else 0
    m3.metric("Eficiencia de Carga", f"{eficiencia:.1f}%")

    # --- FILTROS ---
    st.divider()
    vista = st.pills("Filtrar por estado de garantía:", 
                    ["Todos", "Sin Garantía ❌", "Con Garantía ✅"], 
                    default="Todos")

    if vista == "Sin Garantía ❌":
        df_final = df[~df['TIENE_GARANTIA']]
        st.error(f"Mostrando {len(df_final)} unidades que no tienen garantía iniciada.")
    elif vista == "Con Garantía ✅":
        df_final = con_garantia
        st.success(f"Mostrando {len(df_final)} unidades con garantía activa.")
    else:
        df_final = df

    # --- VISUALIZACIÓN ---
    # Limpiamos las columnas auxiliares antes de mostrar
    df_show = df_final.drop(columns=['TIENE_GARANTIA', 'ES_ENTREGADO'])
    
    st.dataframe(
        df_show, 
        use_container_width=True, 
        hide_index=True
    )

except Exception as e:
    st.error("Error al procesar la información.")
    st.write(e)
