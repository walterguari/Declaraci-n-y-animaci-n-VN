import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime

# 1. Configuración de la página
st.set_page_config(page_title="Portal de Gestión VN", layout="wide", page_icon="🚗")

# 2. Conexión a Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# URL Limpia original
url_base = "https://docs.google.com/spreadsheets/d/1-ziHRIEWQZUxFUBGqoweX6PvY6sDgoaXGcueSUd9370/edit#gid=1482583153"

# Columnas para la pestaña de Hand Over
COLUMNAS_HO = [
    "Marca", "Vendedor", "Cliente", "Teléfono", 
    "Chasis", "VIN", "Fecha de Patentamiento", "Patente", 
    "Estado Administrativo", "Observacion de la Documentación", 
    "Estado", "Fecha de confirmacion de entrega", "ESTADO INTERNO", "Fecha de Hand over"
]

try:
    # --- CARGA DE DATOS ---
    df_raw = conn.read(spreadsheet=url_base)
    df_base = df_raw.dropna(how='all')
    
    # NORMALIZACIÓN AVANZADA
    df_base.columns = [str(c).replace('\n', ' ').replace('\r', ' ').strip() for c in df_base.columns]
    df_base.columns = [" ".join(c.split()) for c in df_base.columns]

    # --- PROCESAMIENTO GLOBAL DE FECHAS ---
    cols_a_fecha = [
        "Fecha de Patentamiento", "Fecha de Hand over", "Fecha de Facturacion",
        "Fecha que el Gestor Retira Doc", "Fecha Disponibilidad Papeles",
        "Fecha de confirmacion de entrega", "Fecha de Pedido de Preparacion" 
    ]
    for c in cols_a_fecha:
        if c in df_base.columns:
            df_base[c] = pd.to_datetime(df_base[c], errors='coerce')

    # Auxiliares globales
    df_base['TIENE_HO'] = df_base["Fecha de Hand over"].notna()
    df_base["Mes_Display"] = df_base["Fecha de Patentamiento"].dt.strftime('%b %Y')
    
    # Estandarización de ESTADO INTERNO
    col_ei = "ESTADO INTERNO"
    if col_ei in df_base.columns:
        df_base[col_ei] = df_base[col_ei].fillna("SIN ESTADO").astype(str).str.strip()
    else:
        columna_encontrada = [c for c in df_base.columns if "ESTADO" in c.upper() and "INTERNO" in c.upper()]
        if columna_encontrada:
            col_ei = columna_encontrada[0]
            df_base[col_ei] = df_base[col_ei].fillna("SIN ESTADO").astype(str).str.strip()
        else:
            st.error(f"❌ No se detecta la columna ESTADO INTERNO. Columnas disponibles: {list(df_base.columns)}")
            df_base[col_ei] = "SIN ESTADO"

    # --- LÓGICA DE CLASIFICACIÓN: A ANIMAR vs PARA DECLARAR ---
    def clasificar_accion(row):
        # 1. Si ya se declaró/realizó el Hand Over, se da por cerrado el ciclo activo
        if row['TIENE_HO']:
            return "Cerrado / Declarado"
        
        estado = str(row.get('Estado', '')).upper()
        pat_listo = pd.notna(row.get('Fecha de Patentamiento'))
        
        # 2. PARA DECLARAR: Vehículos entregados y patentados pendientes de declarar/cierre oficial
        if 'ENTREGADO' in estado and pat_listo:
            return "Para Declarar"
        
        # 3. A ANIMAR: En proceso de entrega, documentación pendiente o en gestión operativa
        return "A Animar"

    df_base["ACCIÓN OPERATIVA"] = df_base.apply(clasificar_accion, axis=1)

    # --- SIDEBAR ---
    st.sidebar.header("Filtros Globales")
    
    marcas = sorted(df_base["Marca"].dropna().unique()) if "Marca" in df_base.columns else []
    filtro_marca = st.sidebar.multiselect("Seleccionar Marca", options=marcas)

    canales = sorted(df_base["Canal de Venta"].dropna().unique()) if "Canal de Venta" in df_base.columns else []
    filtro_canal = st.sidebar.multiselect("Canal de Venta", options=canales)

    acciones_ops = sorted(df_base["ACCIÓN OPERATIVA"].unique())
    filtro_accion = st.sidebar.multiselect("Acción Requerida", options=acciones_ops, default=None)

    # --- APLICACIÓN DEL FILTRO GLOBAL ---
    df = df_base.copy()
    if filtro_marca:
        df = df[df["Marca"].isin(filtro_marca)]
    if filtro_canal:
        df = df[df["Canal de Venta"].isin(filtro_canal)]
    if filtro_accion:
        df = df[df["ACCIÓN OPERATIVA"].isin(filtro_accion)]

    # --- CREACIÓN DE PESTAÑAS (Agregada Pestaña 4 de Animación y Declaración) ---
    tab_ho, tab_acciones, tab_tiempos, tab_graficos = st.tabs([
        "🛡️ Gestión de Hand Over", 
        "📣 Animación y Declaración",
        "⏱️ Análisis de Tiempos", 
        "📈 Análisis Visual"
    ])

    # ---------------------------------------------------------
    # PESTAÑA 1: GESTIÓN DE HAND OVER Y GARANTÍAS
    # ---------------------------------------------------------
    with tab_ho:
        st.header("Gestión de Hand Over y Garantías")
        st.write("### 📅 1. Seleccioná el Mes con Pendientes")
        meses_pendientes = df[~df['TIENE_HO']].dropna(subset=["Fecha de Patentamiento"]).sort_values("Fecha de Patentamiento")
        opciones_meses = meses_pendientes["Mes_Display"].unique().tolist()
        mes_sel = st.pills("Meses detectados:", ["Todos"] + opciones_meses, default="Todos", key="p_mes")

        st.write("### 🏷️ 2. Filtrar por Estado Interno")
        df_temp_ei = df.copy()
        if mes_sel != "Todos":
            df_temp_ei = df_temp_ei[df_temp_ei["Mes_Display"] == mes_sel]
        
        est_disponibles = sorted([e for e in df_temp_ei[col_ei].unique() if e.upper() not in ["NAN", "", "NONE"]])
        ei_sel = st.pills("Categorías detectadas en el periodo:", ["Todos"] + est_disponibles, default="Todos", key="p_ei")

        df_f_ho = df.copy()
        if mes_sel != "Todos": df_f_ho = df_f_ho[df_f_ho["Mes_Display"] == mes_sel]
        if ei_sel != "Todos": df_f_ho = df_f_ho[df_f_ho[col_ei] == ei_sel]

        st.divider()
        c1, c2, c3, c4 = st.columns(4)
        pat_v = df_f_ho[df_f_ho["Fecha de Patentamiento"].notna()]
        ent_v = df_f_ho[df_f_ho["Estado"].astype(str).str.upper().str.contains('ENTREGADO', na=False)]
        fal_v = pat_v[~pat_v['TIENE_HO']]
        
        c1.metric("Patentados", len(pat_v))
        c2.metric("Entregados", len(ent_v))
        c3.metric("Faltan Hand Over", len(fal_v), delta_color="inverse")
        eficacia = (len(pat_v[pat_v['TIENE_HO']]) / len(pat_v) * 100) if len(pat_v) > 0 else 0
        c4.metric("% Eficacia", f"{eficacia:.1f}%")

        modo = st.radio("Filtro tabla:", ["Solo Pendientes ⚠️", "Todos"], horizontal=True)
        df_final = fal_v if modo == "Solo Pendientes ⚠️" else df_f_ho
        
        busq = st.text_input("🔍 Búsqueda rápida:", key="busq_ho")
        if busq:
            mask = df_final.apply(lambda row: row.astype(str).str.contains(busq, case=False).any(), axis=1)
            df_final = df_final[mask]

        df_final = df_final.rename(columns={col_ei: "ESTADO INTERNO"})
        cols_ok = [c for c in COLUMNAS_HO if c in df_final.columns]
        st.dataframe(df_final[cols_ok], use_container_width=True, hide_index=True)

    # ---------------------------------------------------------
    # PESTAÑA 2: ANIMACIÓN Y DECLARACIÓN (NUEVA PESTAÑA OPERATIVA)
    # ---------------------------------------------------------
    with tab_acciones:
        st.header("📣 Panel Operativo: Clientes a Animar vs. Para Declarar")
        st.write("Seguimiento segmentado para impulsar respuestas y gestionar cierres/declaraciones oficiales.")
        
        # Resumen Rápido
        tot_animar = len(df[df["ACCIÓN OPERATIVA"] == "A Animar"])
        tot_declarar = len(df[df["ACCIÓN OPERATIVA"] == "Para Declarar"])
        tot_cerrados = len(df[df["ACCIÓN OPERATIVA"] == "Cerrado / Declarado"])

        m1, m2, m3 = st.columns(3)
        m1.metric("🟢 A Animar (Seguimiento / Contacto)", f"{tot_animar} casos")
        m2.metric("🔵 Para Declarar (Listos para Oficializar)", f"{tot_declarar} casos")
        m3.metric("✅ Cerrados / Declarados", f"{tot_cerrados} casos")

        st.divider()

        # Selector de Enfoque Operativo
        enfoque = st.radio(
            "📌 Seleccionar frente de gestión:",
            ["Todos los pendientes", "🟢 Solo A Animar", "🔵 Solo Para Declarar"],
            horizontal=True
        )

        df_acc = df.copy()
        if enfoque == "🟢 Solo A Animar":
            df_acc = df_acc[df_acc["ACCIÓN OPERATIVA"] == "A Animar"]
        elif enfoque == "🔵 Solo Para Declarar":
            df_acc = df_acc[df_acc["ACCIÓN OPERATIVA"] == "Para Declarar"]
        else:
            df_acc = df_acc[df_acc["ACCIÓN OPERATIVA"].isin(["A Animar", "Para Declarar"])]

        busq_acc = st.text_input("🔍 Buscar cliente, vendedor o chasis:", key="busq_acc")
        if busq_acc:
            mask_acc = df_acc.apply(lambda row: row.astype(str).str.contains(busq_acc, case=False).any(), axis=1)
            df_acc = df_acc[mask_acc]

        cols_acciones = [
            "ACCIÓN OPERATIVA", "Marca", "Cliente", "Teléfono", "Vendedor",
            "Chasis", "Estado", "ESTADO INTERNO", "Fecha de Patentamiento", "Fecha de confirmacion de entrega"
        ]
        cols_acciones_ok = [c for c in cols_acciones if c in df_acc.columns]

        st.dataframe(
            df_acc[cols_acciones_ok],
            use_container_width=True,
            hide_index=True,
            column_config={
                "ACCIÓN OPERATIVA": st.column_config.TextColumn("Frente de Acción", width="medium"),
                "Fecha de Patentamiento": st.column_config.DateColumn("Patentado"),
                "Fecha de confirmacion de entrega": st.column_config.DateColumn("Entrega Conf.")
            }
        )

        # Gráfico complementario de gestión por vendedor
        if not df_acc.empty and "Vendedor" in df_acc.columns:
            st.write("### 📊 Carga de trabajo pendiente por Vendedor")
            resumen_vend = df_acc.groupby(["Vendedor", "ACCIÓN OPERATIVA"]).size().reset_index(name="Cantidad")
            fig_vend = px.bar(
                resumen_vend, x="Vendedor", y="Cantidad", color="ACCIÓN OPERATIVA",
                color_discrete_map={"A Animar": "#2ecc71", "Para Declarar": "#3498db"},
                title="Distribución de casos pendientes por Vendedor", template="plotly_white", text_auto=True
            )
            st.plotly_chart(fig_vend, use_container_width=True)

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
            
            # Nuevo gráfico opcional para el estado operativo en general
            st.write("### Distribución Global de Acción Operativa")
            st.plotly_chart(px.pie(df, names="ACCIÓN OPERATIVA", color="ACCIÓN OPERATIVA",
                                   color_discrete_map={"A Animar": "#2ecc71", "Para Declarar": "#3498db", "Cerrado / Declarado": "#95a5a6"},
                                   hole=0.4), use_container_width=True)

except Exception as e:
    st.error(f"Error al cargar el portal: {e}")
