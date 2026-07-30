import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime
import urllib.parse

# 1. Configuración de la página
st.set_page_config(page_title="Portal de Gestión VN", layout="wide", page_icon="🚗")

# 2. Conexión a Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# URL Limpia original
url_base = "https://docs.google.com/spreadsheets/d/1-ziHRIEWQZUxFUBGqoweX6PvY6sDgoaXGcueSUd9370/edit#gid=1482583153"

# --- DICCIONARIO DE TELÉFONOS DE LOS ASESORES ---
# Podés agregar más vendedores siguiendo exactamente este formato: "NOMBRE EN SHEETS": "NUMERO CON CODIGO DE PAIS Y AREA"
TELEFONOS_ASESORES = {
    "MARCELO CISNEROS": "5493886868562",
    "OLMOS MARIO": "5493874854123"
}

# Columnas para la pestaña de Hand Over
COLUMNAS_HO = [
    "Marca", "Vendedor", "Cliente", "Teléfono", 
    "Chasis", "VIN", "Fecha de Patentamiento", "Patente", 
    "Estado Administrativo", "Observacion de la Documentación", 
    "Estado", "Fecha de confirmacion de entrega", "ESTADO INTERNO", "Fecha de Hand over"
]

# Columnas exactas solicitadas para la Tabla de Animación (Sin Chasis y Sin Marca)
COLUMNAS_ANIMACION = [
    "Canal de Venta", 
    "Vendedor", 
    "Cliente", 
    "Teléfono", 
    "E-mail", 
    "Encuesta Temprana", 
    "Comentario Enc. Temp.", 
    "EI - Reco", 
    "Comentario de la Encuesta interna"
]

try:
    # --- CARGA DE DATOS ---
    df_raw = conn.read(spreadsheet=url_base)
    df_base = df_raw.dropna(how='all')
    
    # NORMALIZACIÓN AVANZADA: Limpieza de nombres de columnas
    df_base.columns = [str(c).replace('\n', ' ').replace('\r', ' ').strip() for c in df_base.columns]
    df_base.columns = [" ".join(c.split()) for c in df_base.columns]

    # --- SIDEBAR: FILTROS GLOBALES ---
    st.sidebar.header("Filtros Globales")
    
    marcas = sorted(df_base["Marca"].dropna().unique()) if "Marca" in df_base.columns else []
    filtro_marca = st.sidebar.multiselect("Seleccionar Marca", options=marcas)

    canales = sorted(df_base["Canal de Venta"].dropna().unique()) if "Canal de Venta" in df_base.columns else []
    filtro_canal = st.sidebar.multiselect("Canal de Venta", options=canales)

    # --- APLICACIÓN DEL FILTRO GLOBAL ---
    df = df_base.copy()
    if filtro_marca:
        df = df[df["Marca"].isin(filtro_marca)]
    if filtro_canal:
        df = df[df["Canal de Venta"].isin(filtro_canal)]

    # --- PROCESAMIENTO GLOBAL DE FECHAS ---
    cols_a_fecha = [
        "Fecha de Patentamiento", "Fecha de Hand over", "Fecha de Facturacion",
        "Fecha que el Gestor Retira Doc", "Fecha Disponibilidad Papeles",
        "Fecha de confirmacion de entrega", "Fecha de Pedido de Preparacion" 
    ]
    for c in cols_a_fecha:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors='coerce')

    # Auxiliares globales
    df['TIENE_HO'] = df["Fecha de Hand over"].notna()
    df["Mes_Display"] = df["Fecha de Patentamiento"].dt.strftime('%b %Y')
    
    # Estandarización de ESTADO INTERNO
    col_ei = "ESTADO INTERNO"
    if col_ei in df.columns:
        df[col_ei] = df[col_ei].fillna("SIN ESTADO").astype(str).str.strip()
    else:
        columna_encontrada = [c for c in df.columns if "ESTADO" in c.upper() and "INTERNO" in c.upper()]
        if columna_encontrada:
            col_ei = columna_encontrada[0]
            df[col_ei] = df[col_ei].fillna("SIN ESTADO").astype(str).str.strip()
        else:
            st.error(f"❌ No se detecta la columna ESTADO INTERNO. Columnas disponibles: {list(df.columns)}")
            df[col_ei] = "SIN ESTADO"

    # --- CREACIÓN DE PESTAÑAS ---
    tab_ho, tab_animacion, tab_tiempos, tab_graficos = st.tabs([
        "🛡️ Gestión de Hand Over y Garantías", 
        "📣 Animación de Encuestas", 
        "⏱️ Análisis de Tiempos", 
        "📈 Análisis Visual"
    ])
    # ---------------------------------------------------------
    # PESTAÑA 1: GESTIÓN DE HAND OVER Y GARANTÍAS (DASHBOARD EJECUTIVO)
    # ---------------------------------------------------------
    with tab_ho:
        st.header("🛡️ Gestión de Hand Over y Garantías")
        
        # NORMALIZACIÓN INTERNA DE CATEGORÍAS (Para evitar duplicados tipo PROMOTOR / Promotor)
        df_ho = df.copy()
        if col_ei in df_ho.columns:
            df_ho[col_ei] = df_ho[col_ei].astype(str).str.strip().str.upper()
            df_ho[col_ei] = df_ho[col_ei].replace({"NAN": "SIN ESTADO", "NONE": "SIN ESTADO", "": "SIN ESTADO"})
        
        # 1. TARJETAS DE MÉTRICAS (KPIs GLOBALES)
        pat_v = df_ho[df_ho["Fecha de Patentamiento"].notna()]
        ent_v = df_ho[df_ho["Estado"].astype(str).str.upper().str.contains('ENTREGADO', na=False)]
        fal_v = pat_v[~pat_v['TIENE_HO']]
        eficacia = (len(pat_v[pat_v['TIENE_HO']]) / len(pat_v) * 100) if len(pat_v) > 0 else 0
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("🚗 Patentados", len(pat_v))
        m2.metric("🤝 Entregados", len(ent_v))
        m3.metric("⚠️ Faltan Hand Over", len(fal_v), delta="Atención requerida" if len(fal_v)>0 else "Al día", delta_color="inverse")
        m4.metric("📈 % Eficacia", f"{eficacia:.1f}%")
        
        st.divider()
        
        # 2. FILTRO DE AÑO PARA LOS GRÁFICOS
        y_pat = pat_v["Fecha de Patentamiento"].dt.year.dropna()
        y_ent = df_ho["Fecha de confirmacion de entrega"].dt.year.dropna()
        anios_reales = sorted(list(set(y_pat.tolist() + y_ent.tolist())), reverse=True)
        anios_validos = [int(a) for a in anios_reales if 2020 <= a <= 2030]
        
        c_tit, c_anio = st.columns([3, 1])
        c_tit.write("### 📊 Evolución Mensual Operativa")
        anio_sel_g = c_anio.selectbox("📅 Año del Gráfico:", ["Todos"] + (anios_validos if anios_validos else [2026]), key="ho_anio_g")
        
        col_g1, col_g2 = st.columns(2)
        
        # DICCIONARIO DE TRADUCCIÓN DE MESES AL ESPAÑOL
        MESES_ESP = {
            1: "Ene", 2: "Feb", 3: "Mar", 4: "Abr", 5: "May", 6: "Jun",
            7: "Jul", 8: "Ago", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dic"
        }

        col_g1, col_g2 = st.columns(2)
        
        # GRÁFICO 1: PATENTAMIENTOS POR MES (EN ESPAÑOL)
        with col_g1:
            df_pat_g = pat_v.copy()
            df_pat_g = df_pat_g[(df_pat_g["Fecha de Patentamiento"].dt.year >= 2020) & (df_pat_g["Fecha de Patentamiento"].dt.year <= 2030)]
            if anio_sel_g != "Todos":
                df_pat_g = df_pat_g[df_pat_g["Fecha de Patentamiento"].dt.year == int(anio_sel_g)]
                
            if not df_pat_g.empty:
                df_pat_g["Mes_Num"] = df_pat_g["Fecha de Patentamiento"].dt.month
                df_pat_g["Anio_Num"] = df_pat_g["Fecha de Patentamiento"].dt.year
                df_pat_g["Mes_Nom"] = df_pat_g["Mes_Num"].map(MESES_ESP) + " " + df_pat_g["Anio_Num"].astype(str)
                
                res_pat = df_pat_g.groupby(["Mes_Num", "Mes_Nom"]).size().reset_index(name="Cantidad").sort_values("Mes_Num")
                
                fig_pat = px.bar(
                    res_pat, x="Mes_Nom", y="Cantidad",
                    title=f"🚗 Patentamientos por Mes ({anio_sel_g})",
                    text_auto=True,
                    color_discrete_sequence=['#3498db'],
                    template="plotly_white"
                )
                fig_pat.update_layout(
                    xaxis_title="Mes", 
                    yaxis_title="Cantidad", 
                    height=320,
                    xaxis=dict(tickangle=-30)  # Inclinación para que no se choquen los nombres
                )
                st.plotly_chart(fig_pat, use_container_width=True)
            else:
                st.info(f"No hay datos de Patentamientos válidos para {anio_sel_g}.")
        
        # GRÁFICO 2: ENTREGAS POR MES (EN ESPAÑOL - CORTE A FECHA HOY)
        with col_g2:
            df_ent_g = df_ho[df_ho["Fecha de confirmacion de entrega"].notna()].copy()
            
            # 1. Filtro de años válidos (2020 a 2030)
            df_ent_g = df_ent_g[(df_ent_g["Fecha de confirmacion de entrega"].dt.year >= 2020) & (df_ent_g["Fecha de confirmacion de entrega"].dt.year <= 2030)]
            
            # 2. FILTRO CLAVE: Excluir fechas futuras que no hayan ocurrido aún (corte a hoy)
            hoy_actual = pd.to_datetime(datetime.now().date())
            df_ent_g = df_ent_g[df_ent_g["Fecha de confirmacion de entrega"] <= hoy_actual]
            
            # 3. Filtro según el año seleccionado en el desplegable
            if anio_sel_g != "Todos":
                df_ent_g = df_ent_g[df_ent_g["Fecha de confirmacion de entrega"].dt.year == int(anio_sel_g)]
                
            if not df_ent_g.empty:
                df_ent_g["Mes_Num"] = df_ent_g["Fecha de confirmacion de entrega"].dt.month
                df_ent_g["Anio_Num"] = df_ent_g["Fecha de confirmacion de entrega"].dt.year
                df_ent_g["Mes_Nom"] = df_ent_g["Mes_Num"].map(MESES_ESP) + " " + df_ent_g["Anio_Num"].astype(str)
                
                res_ent = df_ent_g.groupby(["Mes_Num", "Mes_Nom"]).size().reset_index(name="Cantidad").sort_values("Mes_Num")
                
                fig_ent = px.bar(
                    res_ent, x="Mes_Nom", y="Cantidad",
                    title=f"🤝 Entregas por Mes ({anio_sel_g}) - Efectivas",
                    text_auto=True,
                    color_discrete_sequence=['#2ecc71'],
                    template="plotly_white"
                )
                fig_ent.update_layout(
                    xaxis_title="Mes", 
                    yaxis_title="Cantidad", 
                    height=320,
                    xaxis=dict(tickangle=-30)
                )
                st.plotly_chart(fig_ent, use_container_width=True)
            else:
                st.info(f"No hay datos de Entregas efectivos válidos para {anio_sel_g}.")
        
        st.divider()
        
        # 3. GRÁFICO INTEGRADO: AUDITORÍA DE CUELLOS DE BOTELLA (SEMÁFORO)
        st.write("### 🚨 Auditoría de Cuellos de Botella (Pendientes de Hand Over)")
        df_criticos = fal_v.copy()
        if not df_criticos.empty:
            conteo_ei = df_criticos[col_ei].value_counts().reset_index()
            conteo_ei.columns = ["Estado Interno", "Cantidad"]
            
            fig_sem = px.bar(
                conteo_ei, x="Cantidad", y="Estado Interno", 
                orientation="h", text_auto=True,
                title=f"Motivos de retraso en los {len(df_criticos)} casos pendientes",
                color="Cantidad", color_continuous_scale="Reds",
                template="plotly_white"
            )
            fig_sem.update_layout(showlegend=False, height=260)
            st.plotly_chart(fig_sem, use_container_width=True)
        else:
            st.success("✅ ¡Excelente! No hay vehículos patentados pendientes de Hand Over.")
            
        st.divider()
        
        # 4. BARRA DE FILTROS COMPACTA PARA LA TABLA
        st.write("### 📋 Detalle y Gestión de Unidades")
        f_col1, f_col2, f_col3, f_col4 = st.columns([2, 2, 2, 2])
        
        meses_pendientes = pat_v[~pat_v['TIENE_HO']].dropna(subset=["Fecha de Patentamiento"]).sort_values("Fecha de Patentamiento")
        opciones_meses = meses_pendientes["Mes_Display"].unique().tolist()
        mes_sel_ex = f_col1.selectbox("📅 Mes con Pendientes:", ["Todos"] + opciones_meses, key="ex_mes")
        
        est_disponibles = sorted([e for e in df_ho[col_ei].unique() if e not in ["NAN", ""]])
        ei_sel_ex = f_col2.selectbox("🏷️ Estado Interno:", ["Todos"] + est_disponibles, key="ex_ei")
        
        modo_ex = f_col3.radio("📌 Vista de Tabla:", ["Solo Pendientes ⚠️", "Todos"], horizontal=True, key="ex_modo")
        busq_ex = f_col4.text_input("🔍 Búsqueda rápida:", key="ex_busq", placeholder="Cliente, chasis, patente...")
        
        # 5. APLICACIÓN DE FILTROS Y TABLA
        df_final_ex = df_ho.copy()
        if mes_sel_ex != "Todos":
            df_final_ex = df_final_ex[df_final_ex["Mes_Display"] == mes_sel_ex]
        if ei_sel_ex != "Todos":
            df_final_ex = df_final_ex[df_final_ex[col_ei] == ei_sel_ex]
            
        df_mostrar_ex = df_final_ex[~df_final_ex['TIENE_HO']] if modo_ex == "Solo Pendientes ⚠️" else df_final_ex
        
        if busq_ex:
            mask = df_mostrar_ex.apply(lambda row: row.astype(str).str.contains(busq_ex, case=False).any(), axis=1)
            df_mostrar_ex = df_mostrar_ex[mask]
            
        cols_ok_ex = [c for c in COLUMNAS_HO if c in df_mostrar_ex.columns]
        st.dataframe(df_mostrar_ex[cols_ok_ex], use_container_width=True, hide_index=True, height=450)
    # ---------------------------------------------------------
    # PESTAÑA 2: ANIMACIÓN DE ENCUESTAS (EN ESPERA)
    # ---------------------------------------------------------
    with tab_animacion:
        st.header("📣 Animación de Encuesta de la Marca")
        st.write("Listado de clientes con estado **En Espera** para seguimiento y animación de respuestas.")
        
        # 1. Búsqueda y normalización de la columna Estado de la marca
        col_em = "Estado de la marca"
        if col_em not in df.columns:
            col_encontrada = [c for c in df.columns if c.upper().strip() == "ESTADO DE LA MARCA"]
            if col_encontrada:
                col_em = col_encontrada[0]
            else:
                st.error("❌ No se encontró la columna 'Estado de la marca' en la hoja de Google Sheets.")
        
        df_anim = pd.DataFrame()
        
        if col_em in df.columns:
            # Filtro estricto para casos en espera
            df_anim = df[df[col_em].astype(str).str.strip().str.upper() == "EN ESPERA"].copy()
            
            # --- SECCIÓN DE LOS 3 FILTROS SOLICITADOS ---
            st.divider()
            f_col1, f_col2, f_col3 = st.columns(3)
            
            marcas_anim = sorted(df_anim["Marca"].dropna().unique()) if "Marca" in df_anim.columns else []
            sel_marca = f_col1.multiselect("📌 Filtrar por Marca", options=marcas_anim, key="anim_marca")
            
            canales_anim = sorted(df_anim["Canal de Venta"].dropna().unique()) if "Canal de Venta" in df_anim.columns else []
            sel_canal = f_col2.multiselect("📌 Filtrar por Canal de Venta", options=canales_anim, key="anim_canal")
            
            vendedores_anim = sorted(df_anim["Vendedor"].dropna().unique()) if "Vendedor" in df_anim.columns else []
            sel_vend = f_col3.multiselect("📌 Filtrar por Vendedor", options=vendedores_anim, key="anim_vend")
            
            # Aplicamos los filtros seleccionados
            if sel_marca:
                df_anim = df_anim[df_anim["Marca"].isin(sel_marca)]
            if sel_canal:
                df_anim = df_anim[df_anim["Canal de Venta"].isin(sel_canal)]
            if sel_vend:
                df_anim = df_anim[df_anim["Vendedor"].isin(sel_vend)]
                
            # --- MÉTRICA DE RESULTADOS Y BUSCADOR RÁPIDO ---
            st.divider()
            m_col1, m_col2 = st.columns([1, 3])
            m_col1.metric("🔔 Total a Animar", f"{len(df_anim)} clientes")
            
            with m_col2:
                busq_anim = st.text_input("🔍 Búsqueda rápida por Cliente, Teléfono o E-mail:", key="busq_anim")
                if busq_anim:
                    mask_anim = df_anim.apply(lambda row: row.astype(str).str.contains(busq_anim, case=False).any(), axis=1)
                    df_anim = df_anim[mask_anim]

            # --- GENERACIÓN DE LINK INTELIGENTE DE WHATSAPP WEB ---
            def crear_link_whatsapp(row):
                asesor = str(row.get("Vendedor", "")).strip().upper()
                cliente = str(row.get("Cliente", "el cliente")).strip()
                telefono = str(row.get("Teléfono", "-")).strip()
                canal = str(row.get("Canal de Venta", "-")).strip()
                marca = str(row.get("Marca", "")).strip().upper()
                email = str(row.get("E-mail", "-")).strip()
                
                # Función auxiliar para que los "nan", nulos o vacíos se muestren como "Sin comentarios"
                def limpiar_texto(val):
                    txt = str(val).strip()
                    return "Sin comentarios" if txt.lower() in ["nan", "none", "", "null", "-"] else txt
                
                com_temp = limpiar_texto(row.get("Comentario Enc. Temp."))
                com_int = limpiar_texto(row.get("Comentario de la Encuesta interna"))
                
                # Buscamos en el diccionario si tenemos el teléfono del asesor
                numero_asesor = TELEFONOS_ASESORES.get(asesor)
                
                if not numero_asesor:
                    return None  # Si no hay número cargado para ese vendedor, dejamos vacío
                
                # Speech exacto sin las líneas de Encuesta Temprana y EI-Reco
                mensaje = (
                    f"Hola, {asesor}! Tenes al cliente {canal} - {cliente} - (Tel: {telefono}) "
                    f"está pendiente de responder la encuesta de la marca de {marca} que le llego "
                    f"por email {email}. Por favor, de animarlo a que la responda.\n\n"
                    f"A continuación te dejo todas las respuestas de las preguntas que se realizo:\n"
                    f"• Comentario Enc. Temp.: {com_temp}\n"
                    f"• Comentario Encuesta Interna: {com_int}"
                )
                texto_encoded = urllib.parse.quote(mensaje)
                
                # Link directo a WhatsApp Web
                return f"https://web.whatsapp.com/send?phone={numero_asesor}&text={texto_encoded}"

            # Creamos la columna de link por fila
            df_anim["📲 WhatsApp"] = df_anim.apply(crear_link_whatsapp, axis=1)

            # --- PREPARACIÓN DE TABLA ---
            cols_anim_ok = [c for c in COLUMNAS_ANIMACION if c in df_anim.columns]
            
            # Agregamos "📲 WhatsApp" en primer lugar visual y "Marca" oculta para colorear
            cols_con_marca = ["Marca", "📲 WhatsApp"] + [c for c in cols_anim_ok if c != "Marca"]
            df_tabla = df_anim[cols_con_marca].fillna("-").copy()
            
            # Función para pintar la celda de "Canal de Venta" según el valor de la marca en esa fila
            def resaltar_canal(row):
                estilos = [''] * len(row)
                if "Canal de Venta" in row.index and "Marca" in row.index:
                    idx_canal = row.index.get_loc("Canal de Venta")
                    marca = str(row["Marca"]).upper()
                    if "PEUGEOT" in marca:
                        # Azul clarito
                        estilos[idx_canal] = 'background-color: #d0e1fd; color: #0c326f; font-weight: bold;'
                    elif "CITRO" in marca:  # Cubre Citroen o Citroën
                        # Naranja clarito
                        estilos[idx_canal] = 'background-color: #fde2c4; color: #78350f; font-weight: bold;'
                return estilos

            # Aplicamos estilo y OCULTAMOS EXPLÍCITAMENTE la columna "Marca" de la vista
            df_estilizado = df_tabla.style.apply(resaltar_canal, axis=1).hide(axis="index").hide(subset=["Marca"], axis="columns")
            
            # Mostramos la tabla con configuración especial para los links y los comentarios
            st.dataframe(
                df_estilizado,
                use_container_width=True,
                height=450,
                column_config={
                    "📲 WhatsApp": st.column_config.LinkColumn(
                        "📲 Avisar",
                        help="Hacé clic para enviar un WhatsApp automático al vendedor",
                        display_text="Avisar a Vendedor"
                    ),
                    "Comentario Enc. Temp.": st.column_config.TextColumn(
                        "Comentario Enc. Temp.",
                        width="medium"
                    ),
                    "Comentario de la Encuesta interna": st.column_config.TextColumn(
                        "Comentario Encuesta Interna",
                        width="large"
                    )
                }
            )
            
            # Alerta si hay columnas pedidas que no existan en el sheet
            cols_faltantes = set(COLUMNAS_ANIMACION) - set(cols_anim_ok)
            if cols_faltantes:
                st.caption(f"⚠️ Nota: Las siguientes columnas solicitadas no fueron encontradas con ese nombre exacto en el archivo original: {', '.join(cols_faltantes)}")

    # ---------------------------------------------------------
    # PESTAÑA 3: ANÁLISIS DE TIEMPOS
    # ---------------------------------------------------------
    with tab_tiempos:
        st.header("⏱️ Análisis de Tiempos Operativos (Días Hábiles)")
        
        v1, v2 = st.columns(2)
        v1.metric("Cantidad de Facturaciones", f"{df['Fecha de Facturacion'].notna().sum()} Unid." if 'Fecha de Facturacion' in df.columns else "0 Unid.")
        v2.metric("Cantidad de Patentamientos", f"{df['Fecha de Patentamiento'].notna().sum()} Unid." if 'Fecha de Patentamiento' in df.columns else "0 Unid.")

        st.divider()
        st.subheader("📊 Evolución Mensual e Interactividad")
        st.info("💡 Hacé clic en una barra para filtrar las demoras y la tabla detallada.")
        
        g_col1, g_col2 = st.columns(2)
        
        y_fact = df["Fecha de Facturacion"].dt.year.dropna().unique() if 'Fecha de Facturacion' in df.columns else []
        y_pat = df["Fecha de Patentamiento"].dt.year.dropna().unique() if 'Fecha de Patentamiento' in df.columns else []
        años = sorted(list(set(y_fact) | set(y_pat)), reverse=True)
        
        año_sel = g_col1.selectbox("Año:", años if años else [2026], key="sel_año_t")
        tipo_g = g_col2.pills("Evolución Mensual de:", ["Facturación", "Patentamiento"], default="Facturación", key="pill_tipo_t")

        col_f = "Fecha de Facturacion" if tipo_g == "Facturación" else "Fecha de Patentamiento"
        
        mes_click = None
        if col_f in df.columns and not df.empty:
            df_g = df[df[col_f].dt.year == año_sel].copy()
            if not df_g.empty:
                df_g["Mes_Num"] = df_g[col_f].dt.month
                df_g["Mes_Nom"] = df_g[col_f].dt.strftime('%B')
                resumen = df_g.groupby(["Mes_Num", "Mes_Nom"]).size().reset_index(name="Cant")
                
                fig_v = px.bar(resumen.sort_values("Mes_Num"), x="Mes_Nom", y="Cant", text_auto=True, 
                               title=f"Volumen de {tipo_g} - {año_sel}", 
                               color_discrete_sequence=['#3498db' if tipo_g == "Facturación" else '#2ecc71'],
                               template="plotly_white")
                
                evento_clic = st.plotly_chart(fig_v, use_container_width=True, on_select="rerun")
                
                if evento_clic and "selection" in evento_clic and evento_clic["selection"]["points"]:
                    mes_click = evento_clic["selection"]["points"][0]["x"]
                    st.success(f"🔎 Auditando {tipo_g}: **{mes_click} {año_sel}**")

        df_t = df[df[col_f].dt.year == año_sel].copy() if col_f in df.columns else pd.DataFrame()
        if mes_click and not df_t.empty:
            df_t["Mes_Nom"] = df_t[col_f].dt.strftime('%B')
            df_t = df_t[df_t["Mes_Nom"] == mes_click]

        hoy_np = np.datetime64(datetime.now().date())

        def calc_working_days(start, end):
            if pd.isna(start): return None
            f_inicio = np.datetime64(start, 'D')
            f_final = np.datetime64(end, 'D') if pd.notna(end) else hoy_np
            if f_inicio > f_final: return 0
            dias = int(np.busday_count(f_inicio, f_final))
            return dias if dias < 365 else None 

        if not df_t.empty:
            df_t["Facturación a Gestor"] = df_t.apply(lambda r: calc_working_days(r.get("Fecha de Facturacion"), r.get("Fecha que el Gestor Retira Doc")), axis=1)
            df_t["Prep a Retiro"] = df_t.apply(lambda r: calc_working_days(r.get("Fecha de Pedido de Preparacion"), r.get("Fecha que el Gestor Retira Doc")), axis=1)
            df_t["Gestoría"] = df_t.apply(lambda r: calc_working_days(r.get("Fecha que el Gestor Retira Doc"), r.get("Fecha Disponibilidad Papeles")), axis=1)
            df_t["Papeles a Entrega"] = df_t.apply(lambda r: calc_working_days(r.get("Fecha Disponibilidad Papeles"), r.get("Fecha de confirmacion de entrega")), axis=1)
            df_t["Demora Total"] = df_t.apply(lambda r: calc_working_days(r.get("Fecha de Facturacion"), r.get("Fecha de confirmacion de entrega")), axis=1)

            st.divider()
            st.subheader(f"⏳ Promedios Días Hábiles - {mes_click if mes_click else 'Anual'}")
            
            mt1, mt_prep, mt2, mt3, mt4 = st.columns(5)
            
            OBJ1, OBJ_PREP, OBJ2, OBJ3 = 2, 1, 3, 3 
            p1, p_prep, p2, p3, p4 = df_t["Facturación a Gestor"].mean(), df_t["Prep a Retiro"].mean(), df_t["Gestoría"].mean(), df_t["Papeles a Entrega"].mean(), df_t["Demora Total"].mean()

            mt1.metric("Fact. a Gestor", f"{p1:.1f} d" if pd.notna(p1) else "0.0 d", 
                       delta=f"{p1-OBJ1:.1f} vs Obj" if pd.notna(p1) else None, delta_color="inverse")
            mt_prep.metric("Prep. a Retiro", f"{p_prep:.1f} d" if pd.notna(p_prep) else "0.0 d", 
                       delta=f"{p_prep-OBJ_PREP:.1f} vs Obj" if pd.notna(p_prep) else None, delta_color="inverse")
            mt2.metric("Gestión Gestor", f"{p2:.1f} d" if pd.notna(p2) else "0.0 d", 
                       delta=f"{p2-OBJ2:.1f} vs Obj" if pd.notna(p2) else None, delta_color="inverse")
            mt3.metric("Papeles a Entrega", f"{p3:.1f} d" if pd.notna(p3) else "0.0 d", 
                       delta=f"{p3-OBJ3:.1f} vs Obj" if pd.notna(p3) else None, delta_color="inverse")
            mt4.metric("Ciclo Total", f"{p4:.1f} d" if pd.notna(p4) else "0.0 d")

            st.subheader(f"📋 Detalle de Unidades ({tipo_g} en el periodo)")
            
            columnas_detalle = [
                "Marca", "Vendedor", "Cliente", "Chasis", 
                "Facturación a Gestor", "Prep a Retiro", "Gestoría", "Papeles a Entrega", 
                "Demora Total", "Fecha de confirmacion de entrega", "Estado"
            ]
            
            cols_det_ok = [c for c in columnas_detalle if c in df_t.columns]
            st.dataframe(
                df_t[cols_det_ok], 
                use_container_width=True, 
                hide_index=True,
                column_config={
                    "Facturación a Gestor": st.column_config.NumberColumn(help="Cálculo: [Fecha que el Gestor Retira Doc] - [Fecha de Facturación]"),
                    "Prep a Retiro": st.column_config.NumberColumn(help="Cálculo: [Fecha que el Gestor Retira Doc] - [Fecha de Pedido de Preparacion]"),
                    "Gestoría": st.column_config.NumberColumn(help="Cálculo: [Fecha Disponibilidad Papeles] - [Fecha que el Gestor Retira Doc]"),
                    "Papeles a Entrega": st.column_config.NumberColumn(help="Cálculo: [Fecha de confirmacion de entrega] - [Fecha Disponibilidad Papeles]"),
                    "Demora Total": st.column_config.NumberColumn(help="Cálculo: [Fecha de confirmacion de entrega] - [Fecha de Facturación]"),
                    "Fecha de confirmacion de entrega": st.column_config.DateColumn("Fecha Entrega")
                }
            )
        else:
            st.info("No hay datos disponibles para el periodo seleccionado.")

    # ---------------------------------------------------------
    # PESTAÑA 4: ANÁLISIS VISUAL
    # ---------------------------------------------------------
    with tab_graficos:
        st.header("Análisis Visual de Gestión")
        if not df.empty:
            g1, g2 = st.columns(2)
            with g1:
                st.write("### Unidades por Marca")
                if "Marca" in df.columns:
                    st.plotly_chart(px.bar(df["Marca"].value_counts().reset_index(), x="Marca", y="count", color="Marca", template="plotly_white"), use_container_width=True)
            with g2:
                st.write("### Estado Interno de los Pendientes")
                if col_ei in df.columns:
                    st.plotly_chart(px.pie(df[df['TIENE_HO']==False], names=col_ei, hole=0.4), use_container_width=True)

except Exception as e:
    st.error(f"Error al cargar el portal: {e}")
