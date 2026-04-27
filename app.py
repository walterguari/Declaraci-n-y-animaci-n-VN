import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import urllib.parse  # Importante para limpiar los espacios

# Configuración
st.set_page_config(page_title="Portal Análisis DUV WG", layout="wide", page_icon="🚗")

st.title("🚗 Control de Unidades - Análisis DUV")

# Conexión
conn = st.connection("gsheets", type=GSheetsConnection)

# URL y Nombre de hoja
url_base = "https://docs.google.com/spreadsheets/d/1-ziHRIEWQZUxFUBGqoweX6PvY6sDgoaXGcueSUd9370/edit#gid=1482583153"
nombre_hoja = "ANALISIS DUV WG"

try:
    # --- LA SOLUCIÓN AL ERROR ---
    # Limpiamos el nombre de la hoja para que la URL sea válida (cambia espacios por %20)
    hoja_limpia = urllib.parse.quote(nombre_hoja)
    
    # Leemos los datos pasando el nombre ya procesado
    df = conn.read(spreadsheet=url_base, worksheet=nombre_hoja) 
    # Si sigue fallando, intenta quitar 'worksheet=nombre_hoja' y deja que lea la primera por defecto
    
    df = df.dropna(how='all')

    # --- RESTO DEL CÓDIGO (Buscador, Tabla, etc.) ---
    busqueda = st.text_input("🔍 Buscar por cualquier campo:")
    if busqueda:
        mask = df.apply(lambda row: row.astype(str).str.contains(busqueda, case=False).any(), axis=1)
        df_display = df[mask]
    else:
        df_display = df

    st.dataframe(df_display, use_container_width=True, hide_index=True)

except Exception as e:
    st.error("Error al cargar los datos por caracteres especiales en el nombre de la hoja.")
    # Intento de emergencia: leer sin especificar hoja (lee la primera pestaña)
    try:
        df_emergencia = conn.read(spreadsheet=url_base)
        st.warning("⚠️ Cargando la primera pestaña por defecto debido al error de nombre.")
        st.dataframe(df_emergencia.dropna(how='all'), use_container_width=True)
    except:
        st.write("Detalle técnico del error:", e)
