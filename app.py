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
    # Lectura de datos
    df = conn.read(spreadsheet=url_base)
    df = df.dropna(how='all')

    # --- IDENTIFICACIÓN ULTRA-FLEXIBLE DE COLUMNAS ---
    # Normalizamos nombres de columnas para encontrarlas sin errores
    cols_mapeo = {str(c).strip().upper(): c for c in df.columns}
    
    # Buscamos la columna de Estado (que contenga 'ESTADO')
    col_estado_real = next((orig for norm, orig in cols_mapeo.items() if "ESTADO" in norm), None)
    # Buscamos la de Hand Over (que contenga 'HAND')
    col_ho_real = next((orig for norm, orig in cols_mapeo.items() if "HAND" in norm), None)

    if not col_estado_real:
        st.error(f"❌ No se encontró la columna de 'Estado'. Columnas detectadas: {list(df.columns)}")
        st.stop()

    # --- PROCESAMIENTO DE DATOS ---
    # Creamos columnas auxiliares internas (no se ven en la tabla)
    df['_ESTADO_LIMPIO'] = df[col_estado_real].astype(str).str.strip().str.upper()
    
    if col_ho_real:
        df['_FECHA_HO_LIMPIA'] = pd.to_datetime(df[col_ho_real], errors='coerce')
    else:
        df['_FECHA_HO_LIMPIA'] = pd.NA

    # --- LÓGICA DE NEGOCIO ---
    # Filtramos: debe contener 'ENTREGADO' y NO tener fecha de Hand Over
    es_entregado = df['_ESTADO_LIMPIO'].str.contains('ENTREGADO', na=False)
    tiene_ho = df['_FECHA_HO_LIMPIA'].notna()

    df_pendientes = df[es_entregado & ~tiene_ho].drop(columns=['_ESTADO_LIMPIO', '_FECHA_HO_LIMPIA'])
    df_completados = df[es_entregado & tiene_ho].drop(columns=['_ESTADO_LIMPIO', '_FECHA_HO_LIMPIA'])
    df_entregados_total = df[es_entregado].drop(columns=['_ESTADO_LIMPIO', '_FECHA_HO_LIMPIA'])

    # --- PANEL DE MÉTRICAS ---
    st.subheader("📊 Resumen de Gestión")
    m1, m2, m3 = st.columns(3)
    
    total = len(df_entregados_total)
    pendientes_n = len(df_pendientes)
    cumplidos_n = len(df_completados)
    
    m1.metric("Total Entregados", total)
    m2.metric("Pendientes HO", pendientes_n, delta="- Acción Requerida" if pendientes_n > 0 else "Al día", delta_color="inverse")
    
    porcentaje = (cumplidos_n / total * 100) if total > 0 else 0
    m3.metric("Cumplimiento HO", f"{porcentaje:.1f}%")

    # --- INTERFAZ DE FILTROS ---
    st.divider()
    vista = st.pills("Seleccioná qué unidades querés revisar:", 
                    ["Todas", "Solo Pendientes ⚠️", "Completados ✅"], 
                    default="Todas")

    # Selección del dataframe a mostrar
    if vista == "Solo Pendientes ⚠️":
        df_final = df_pendientes
        st.warning(f"Mostrando {len(df_pendientes)} unidades entregadas sin fecha de Hand Over.")
    elif vista == "Completados ✅":
        df_final = df_completados
        st.success(f"Mostrando {len(df_completados)} unidades con proceso finalizado.")
    else:
        df_final = df.drop(columns=['_ESTADO_LIMPIO', '_FECHA_HO_LIMPIA'])
        st.info(f"Mostrando base completa ({len(df_final)} unidades).")

    # Buscador adicional
    busqueda = st.text_input("🔍 Buscar por Chasis, Cliente o Vendedor:")
    if busqueda:
        mask = df_final.apply(lambda row: row.astype(str).str.contains(busqueda, case=False).any(), axis=1)
        df_final = df_final[mask]

    # --- TABLA FINAL ---
    st.dataframe(df_final, use_container_width=True, hide_index=True)

except Exception as e:
    st.error("Error al procesar la planilla.")
    st.write("Detalle:", e)
