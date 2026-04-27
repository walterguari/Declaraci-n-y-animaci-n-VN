import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px # Librería para gráficos

# Configuración
st.set_page_config(page_title="Portal Análisis DUV WG", layout="wide", page_icon="🚗")

st.title("🚗 Control de Unidades - Análisis DUV")

# Conexión
conn = st.connection("gsheets", type=GSheetsConnection)
url = "https://docs.google.com/spreadsheets/d/1-ziHRIEWQZUxFUBGqoweX6PvY6sDgoaXGcueSUd9370/edit#gid=1482583153"

try:
    df = conn.read(spreadsheet=url, worksheet="ANALISIS DUV WG")
    df = df.dropna(how='all')

    # --- BARRA LATERAL ---
    st.sidebar.header("Control de Auditoría")
    operador = st.sidebar.text_input("Operador auditado:")
    if operador:
        st.sidebar.success(f"Sesión: {operador}")

    # --- BUSCADOR ---
    busqueda = st.text_input("🔍 Buscar por cualquier campo:")
    if busqueda:
        mask = df.apply(lambda row: row.astype(str).str.contains(busqueda, case=False).any(), axis=1)
        df_display = df[mask]
    else:
        df_display = df

    # --- SECCIÓN DE ESTADÍSTICAS ---
    st.subheader("📊 Resumen de Gestión")
    col_a, col_b = st.columns([1, 2])
    
    with col_a:
        st.metric("Total Unidades", len(df_display))
        # Botón para descargar lo que se ve en pantalla
        csv = df_display.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Descargar Reporte (CSV)", data=csv, file_name="reporte_duv.csv", mime="text/csv")

    with col_b:
        if "VENDEDOR" in df_display.columns:
            # Gráfico rápido de unidades por vendedor
            fig = px.bar(df_display['VENDEDOR'].value_counts(), title="Unidades por Vendedor", labels={'value':'Cantidad', 'index':'Vendedor'})
            st.plotly_chart(fig, use_container_width=True)

    # --- TABLA PRINCIPAL ---
    st.subheader("Detalle de Unidades")
    st.dataframe(df_display, use_container_width=True, hide_index=True)

except Exception as e:
    st.error("Error al cargar los datos.")
    st.write(e)
