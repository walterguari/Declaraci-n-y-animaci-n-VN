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

    # Limpieza de nombres de columnas por si acaso
    df.columns = df.columns.str.strip()

    # Aseguramos formato de fecha para la columna de Hand Over
    if 'Fecha de Hand over' in df.columns:
        df['Fecha de Hand over'] = pd.to_datetime(df['Fecha de Hand over'], errors='coerce')

    # --- LÓGICA DE NEGOCIO ---
    # 1. Unidades que ya están entregadas
    es_entregado = df['Estado'].str.upper().str.contains('ENTREGADO', na=False)
    
    # 2. Unidades que ya tienen Hand Over (tienen fecha)
    tiene_ho = df['Fecha de Hand over'].notna()

    # Definimos los segmentos
    pendientes_criticos = df[es_entregado & ~tiene_ho]  # Entregado pero sin fecha de HO
    completados = df[es_entregado & tiene_ho]          # Entregado con fecha de HO
    otros_estados = df[~es_entregado]                  # Stock, Reservados, etc.

    # --- TABLERO DE CONTROL ---
    st.subheader("📊 Indicadores de Gestión")
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.metric("Total Entregados", len(df[es_entregado]))
    with c2:
        # Usamos delta para resaltar el número de pendientes
        st.metric("Pendientes de Hand Over", len(pendientes_criticos), delta="- Acción Requerida", delta_color="inverse")
    with c3:
        # Porcentaje de eficiencia
        eficiencia = (len(completados) / len(df[es_entregado]) * 100) if len(df[es_entregado]) > 0 else 0
        st.metric("Eficiencia Hand Over", f"{eficiencia:.1f}%")

    # --- ALERTAS ---
    if len(pendientes_criticos) > 0:
        st.error(f"🚨 CRÍTICO: Hay {len(pendientes_criticos)} unidades entregadas sin fecha de Hand Over registrada.")

    # --- FILTROS DE VISTA ---
    st.divider()
    vista = st.radio("Filtrar por prioridad:", 
                     ["Todas las Unidades", "⚠️ Solo Pendientes (Acción Inmediata)", "✅ Hand Over Completados"],
                     horizontal=True)

    if vista == "⚠️ Solo Pendientes (Acción Inmediata)":
        df_final = pendientes_criticos
    elif vista == "✅ Hand Over Completados":
        df_final = completados
    else:
        df_final = df

    # Buscador adicional
    busqueda = st.text_input("🔍 Buscar por Chasis, Cliente o Vendedor:")
    if busqueda:
        df_final = df_final[df_final.apply(lambda row: row.astype(str).str.contains(busqueda, case=False).any(), axis=1)]

    # Mostrar tabla
    st.dataframe(df_final, use_container_width=True, hide_index=True)

    # --- VALIDACIÓN DE ERRORES DE CARGA ---
    error_carga = df[~es_entregado & tiene_ho]
    if not error_carga.empty:
        with st.expander("⚠️ Ver posibles errores de carga (Tienen fecha de HO pero no estado 'Entregado')"):
            st.warning("Estas unidades tienen fecha de Hand Over pero su estado NO es 'Entregado'. Revisar planilla.")
            st.table(error_carga[['VENDEDOR', 'UNIDAD', 'Estado', 'Fecha de Hand over']])

except Exception as e:
    st.error("Error al procesar las reglas de Hand Over.")
    st.write(e)
