import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. Configuración de la página
st.set_page_config(page_title="Control Hand Over VN", layout="wide", page_icon="✅")

st.title("🚗 Gestión de Hand Over - Unidades Entregadas")

# 2. Conexión a Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)
url_base = "https://docs.google.com/spreadsheets/d/1-ziHRIEWQZUxFUBGqoweX6PvY6sDgoaXGcueSUd9370/edit#gid=1482583153"

try:
    # Lectura de datos (usando el GID de la URL para evitar errores de nombre de hoja)
    df = conn.read(spreadsheet=url_base)
    df = df.dropna(how='all')

    # --- NORMALIZACIÓN DE COLUMNAS ---
    # Pasamos todo a MAYÚSCULAS y quitamos espacios para que el código no falle
    df.columns = [str(c).strip().upper() for c in df.columns]

    # Identificamos las columnas clave dinámicamente
    col_estado = next((c for c in df.columns if "ESTADO" in c), None)
    col_ho = next((c for c in df.columns if "HAND OVER" in c or "HANDOVER" in c), None)

    if not col_estado:
        st.error(f"❌ No se encontró la columna 'Estado'. Columnas detectadas: {list(df.columns)}")
        st.stop()

    # Formateamos la fecha de Hand Over
    if col_ho:
        df[col_ho] = pd.to_datetime(df[col_ho], errors='coerce')
    else:
        df[col_ho] = pd.NA

    # --- LÓGICA DE NEGOCIO ---
    # Unidades con estado 'ENTREGADO'
    es_entregado = df[col_estado].astype(str).str.upper().str.contains('ENTREGADO', na=False)
    # Unidades que ya tienen fecha cargada
    tiene_ho = df[col_ho].notna()

    # Definimos los grupos
    pendientes = df[es_entregado & ~tiene_ho]
    completados = df[es_entregado & tiene_ho]

    # --- DASHBOARD DE MÉTRICAS ---
    st.subheader("📊 Resumen de Gestión")
    m1, m2, m3 = st.columns(3)
    
    total_entregados = len(df[es_entregado])
    m1.metric("Total Entregados", total_entregados)
    m2.metric("Pendientes HO", len(pendientes), delta="- Acción Requerida", delta_color="inverse")
    
    eficiencia = (len(completados) / total_entregados * 100) if total_entregados > 0 else 0
    m3.metric("Cumplimiento HO", f"{eficiencia:.1f}%")

    # --- FILTROS REACTIVOS ---
    st.divider()
    st.subheader("🔍 Filtros de Visualización")
    
    # Botones de selección rápida
    opciones = ["Todas", "Solo Pendientes ⚠️", "Completados ✅"]
    vista = st.pills("Seleccioná qué unidades querés revisar:", opciones, default="Todas")

    # Lógica de filtrado de la tabla
    if vista == "Solo Pendientes ⚠️":
        df_final = pendientes
        st.info(f"Mostrando {len(pendientes)} unidades entregadas que esperan Hand Over.")
    elif vista == "Completados ✅":
        df_final = completados
        st.success(f"Mostrando {len(completados)} unidades con Hand Over finalizado.")
    else:
        df_final = df
        st.caption(f"Mostrando base completa ({len(df)} unidades).")

    # Buscador manual extra
    busqueda = st.text_input("Buscar por Chasis, Cliente o Vendedor:")
    if busqueda:
        mask = df_final.apply(lambda row: row.astype(str).str.contains(busqueda, case=False).any(), axis=1)
        df_final = df_final[mask]

    # --- TABLA FINAL ---
    st.dataframe(df_final, use_container_width=True, hide_index=True)

except Exception as e:
    st.error("Hubo un error al procesar la información.")
    st.write("Detalle técnico:", e)
