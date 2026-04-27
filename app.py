import streamlit as st
from streamlit.connections import GSheetsConnection
import pandas as pd

# Configuración de la página (Título y disposición ancha)
st.set_page_config(page_title="Portal Análisis DUV WG", layout="wide", page_icon="📊")

st.title("🚗 Seguimiento de Unidades - Análisis DUV")

# 1. Establecer conexión con Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. URL de la planilla y nombre de la hoja
url = "https://docs.google.com/spreadsheets/d/1-ziHRIEWQZUxFUBGqoweX6PvY6sDgoaXGcueSUd9370/edit#gid=1482583153"
nombre_hoja = "ANALISIS DUV WG"

try:
    # Lectura de los datos
    df = conn.read(spreadsheet=url, worksheet=nombre_hoja)
    
    # Limpiar filas completamente vacías
    df = df.dropna(how='all')

    # --- BARRA LATERAL ---
    st.sidebar.header("Control de Auditoría")
    
    # Opción para escribir el nombre directamente (sin sugerencias)
    operador = st.sidebar.text_input("Operador auditado:", placeholder="Ingresa tu nombre...")
    
    if operador:
        st.sidebar.success(f"Sesión: {operador}")

    st.sidebar.divider()
    st.sidebar.info("Usa el buscador central para filtrar por cualquier columna de la base.")

    # --- CUERPO PRINCIPAL ---
    # Buscador general
    st.subheader("Búsqueda de Datos")
    busqueda = st.text_input("🔍 Buscar por Cliente, Vendedor, Modelo o Chasis:", placeholder="Escribe aquí para filtrar...")
    
    if busqueda:
        # Filtro que busca en todas las columnas
        mask = df.apply(lambda row: row.astype(str).str.contains(busqueda, case=False).any(), axis=1)
        df_mostrar = df[mask]
    else:
        df_mostrar = df

    # Mostrar la tabla de datos
    st.dataframe(
        df_mostrar, 
        use_container_width=True, 
        hide_index=True
    )

    # Indicadores rápidos al final
    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        st.metric("Total Unidades Filtradas", len(df_mostrar))
    with c2:
        if "VENDEDOR" in df.columns:
            st.metric("Vendedores en la lista", df_mostrar["VENDEDOR"].nunique())

except Exception as e:
    st.error(f"No se pudo cargar la hoja '{nombre_hoja}'.")
    st.warning("Verifica que el nombre de la pestaña sea exacto y que el archivo tenga permisos de lectura.")
    with st.expander("Ver detalle técnico"):
        st.write(e)
