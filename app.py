import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import urllib.parse

# 1. Configuración de la página
st.set_page_config(page_title="Portal de Gestión VN", layout="wide", page_icon="🚗")

# 2. Conexión a Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# URL Limpia original (Ventas)
url_base = "https://docs.google.com/spreadsheets/d/1-ziHRIEWQZUxFUBGqoweX6PvY6sDgoaXGcueSUd9370/edit#gid=1482583153"

# NUEVA URL (Post Venta)
url_posventa = "https://docs.google.com/spreadsheets/d/1kMzEHI4uuEWdIG7NfjgVkVVqOSw8ga9p_4-1i5ZN5wo/edit#gid=1727842086"

# --- DICCIONARIO DE TELÉFONOS DE LOS ASESORES ---
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

# Columnas exactas solicitadas para la Tabla de Animación (Ventas)
COLUMNAS_ANIMACION = [
    "Canal de Venta",
    "Vendedor",
    "Cliente",
    "Teléfono",
    "E-mail",
    "Encuesta Temprana",
    "Comentario Enc. Temp.",
    "EI - Reco",
    "Comentario de la Encuesta interna",
    "Fecha de invitación Inicial",
    "Primera fecha de recordatorio",
    "Segunda fecha de recordatorio",
    "Fecha de Vencimento Del Trabajo de Campo"
]

try:
    # =========================================================
    # CARGA DE DATOS: VENTAS (Original)
    # =========================================================
    df_raw = conn.read(spreadsheet=url_base)
    df_base = df_raw.dropna(how='all')

    # NORMALIZACIÓN AVANZADA: Limpieza de nombres de columnas
    df_base.columns = [str(c).replace('\n', ' ').replace('\r', ' ').strip() for c in df_base.columns]
    df_base.columns = [" ".join(c.split()) for c in df_base.columns]

    # --- APLICACIÓN DE DATOS (Sin filtros globales) ---
    df = df_base.copy()

    # --- PROCESAMIENTO GLOBAL DE FECHAS ---
    cols_a_fecha = [
        "Fecha de Patentamiento", "Fecha de Hand over", "Fecha de Facturacion",
        "Fecha que el Gestor Retira Doc", "Fecha Disponibilidad Papeles",
        "Fecha de confirmacion de entrega", "Fecha de Pedido de Preparación",
        "Fecha de invitación Inicial", "Primera fecha de recordatorio",
        "Segunda fecha de recordatorio", "Fecha de Vencimento Del Trabajo de Campo"
    ]
    for c in cols_a_fecha:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c].astype(str).str.strip(), dayfirst=True, format="mixed", errors='coerce')

    # --- Auxiliares globales ---
    if "Fecha de Hand over" in df.columns:
        df['TIENE_HO'] = df["Fecha de Hand over"].notna()
    else:
        df['TIENE_HO'] = False
        st.warning("⚠️ No se encontró la columna 'Fecha de Hand over' en la base de datos.")

    if "Fecha de Patentamiento" in df.columns:
        df["Mes_Display"] = df["Fecha de Patentamiento"].dt.strftime('%b %Y')
    else:
        df["Mes_Display"] = "Sin Fecha"

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

    # =========================================================
    # CARGA DE DATOS: POST VENTA (NUEVO)
    # =========================================================
    df_raw_pv = conn.read(spreadsheet=url_posventa, worksheet="1727842086", ttl=0)
    df_pv = df_raw_pv.dropna(how='all').copy()

    # Normalización rápida de columnas para Post Venta
    df_pv.columns = [str(c).replace('\n', ' ').replace('\r', ' ').strip() for c in df_pv.columns]
    df_pv.columns = [" ".join(c.split()) for c in df_pv.columns]

    # --- CREACIÓN DE PESTAÑAS (Ahora son 4) ---
    tab_ho, tab_animacion_v, tab_animacion_pv, tab_tiempos = st.tabs([
        "🛡️ Gestión de Hand Over",
        "📣 Animación de clientes VN",
        "🔧 Animación de clientes PVT",
        "⏱️ Análisis de Tiempos"
    ])

    # ---------------------------------------------------------
    # PESTAÑA 1: GESTIÓN DE HAND OVER Y GARANTÍAS (Intacta)
    # ---------------------------------------------------------
    with tab_ho:
        st.header("🛡️ Gestión de Hand Over")

        df_ho = df.copy()
        if col_ei in df_ho.columns:
            df_ho[col_ei] = df_ho[col_ei].astype(str).str.strip().str.upper()
            df_ho[col_ei] = df_ho[col_ei].replace({"NAN": "SIN ESTADO", "NONE": "SIN ESTADO", "": "SIN ESTADO"})

        MESES_ESP = {
            1: "Ene", 2: "Feb", 3: "Mar", 4: "Abr", 5: "May", 6: "Jun",
            7: "Jul", 8: "Ago", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dic"
        }

        def normalizar_marca(df_input):
            if "Marca" not in df_input.columns:
                df_input["Marca_Graf"] = "OTRA"
                return df_input
            marca_limpia = df_input["Marca"].astype(str).str.strip().str.upper()
            df_input["Marca_Graf"] = np.where(marca_limpia.str.contains("PEUGEOT", na=False), "PEUGEOT",
                                     np.where(marca_limpia.str.contains("CITRO", na=False), "CITROËN", "OTRA"))
            return df_input

        MAPA_COLORES_MARCA = {
            "PEUGEOT": "#1e3d59",
            "CITROËN": "#ff6e40",
            "OTRA": "#b0bec5"
        }

        def procesar_datos_grafico(df_input, col_fecha, anio_sel):
            if col_fecha not in df_input.columns:
                return pd.DataFrame()

            df_temp = df_input.copy()
            df_temp[col_fecha] = pd.to_datetime(df_temp[col_fecha].astype(str).str.strip(), dayfirst=True, format="mixed", errors='coerce')
            df_temp = df_temp[df_temp[col_fecha].notna()].copy()
            df_temp = normalizar_marca(df_temp)

            if "Canal de Venta" in df_temp.columns:
                df_temp["Canal de Venta"] = df_temp["Canal de Venta"].fillna("Sin Canal").astype(str).str.strip()
            else:
                df_temp["Canal de Venta"] = "Sin Canal"

            if anio_sel != "Todos":
                df_temp = df_temp[df_temp[col_fecha].dt.year == int(anio_sel)]

            if df_temp.empty:
                return pd.DataFrame()

            df_temp["Mes_Num"] = df_temp[col_fecha].dt.month
            df_temp["Anio_Num"] = df_temp[col_fecha].dt.year
            df_temp["Mes_Nom"] = df_temp["Mes_Num"].map(MESES_ESP) + " " + df_temp["Anio_Num"].astype(str)

            list_res = []
            for (m_num, m_nom, marca), group in df_temp.groupby(["Mes_Num", "Mes_Nom", "Marca_Graf"]):
                cant_total = len(group)
                conteo_canales = group["Canal de Venta"].value_counts()
                detalle_txt = "<br>".join([f"• {canal}: {cant} unid." for canal, cant in conteo_canales.items()])
                list_res.append({
                    "Mes_Num": m_num,
                    "Mes_Nom": m_nom,
                    "Marca_Graf": marca,
                    "Cantidad": cant_total,
                    "Detalle_Canales": detalle_txt
                })

            res_df = pd.DataFrame(list_res)
            if not res_df.empty:
                res_df = res_df.sort_values("Mes_Num")
            return res_df

        with st.expander("📊 Evolución Mensual Operativa (Patentamientos y Entregas)", expanded=True):

            y_pat = pd.to_datetime(df_base["Fecha de Patentamiento"].astype(str).str.strip(), dayfirst=True, format="mixed", errors='coerce').dt.year.dropna()
            y_ent = pd.to_datetime(df_base["Fecha de confirmacion de entrega"].astype(str).str.strip(), dayfirst=True, format="mixed", errors='coerce').dt.year.dropna()
            anios_reales = sorted(list(set(y_pat.tolist() + y_ent.tolist())), reverse=True)
            anios_validos = [int(a) for a in anios_reales if 2020 <= a <= 2030]

            c_tit, c_anio = st.columns([3, 1])
            c_tit.subheader("📈 Comparativo por Marca y Canal de Venta")
            anio_sel_g = c_anio.selectbox("📅 Año del Gráfico:", ["Todos"] + (anios_validos if anios_validos else [2026]), key="ho_anio_g")

            col_g1, col_g2 = st.columns(2)

            with col_g1:
                res_pat = procesar_datos_grafico(df_base, "Fecha de Patentamiento", anio_sel_g)
                if not res_pat.empty:
                    fig_pat = px.bar(
                        res_pat,
                        x="Mes_Nom",
                        y="Cantidad",
                        color="Marca_Graf",
                        barmode="group",
                        custom_data=["Detalle_Canales"],
                        title=f"🚗 Patentamientos por Mes y Marca ({anio_sel_g})",
                        text_auto=True,
                        color_discrete_map=MAPA_COLORES_MARCA,
                        template="plotly_white"
                    )
                    fig_pat.update_traces(
                        hovertemplate="<b>%{x} - %{data.name}</b><br>Total Patentados: <b>%{y}</b><br><br><b>Detalle por Canal:</b><br>%{customdata[0]}<extra></extra>"
                    )
                    fig_pat.update_layout(
                        xaxis_title="Mes",
                        yaxis_title="Unidades Patentadas",
                        height=350,
                        xaxis=dict(tickangle=-30),
                        legend_title="Marca",
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                    )
                    st.plotly_chart(fig_pat, use_container_width=True, key="g_pat_ho")
                else:
                    st.info(f"No hay patentamientos cargados para el año {anio_sel_g}.")

            with col_g2:
                res_ent = procesar_datos_grafico(df_base, "Fecha de confirmacion de entrega", anio_sel_g)
                if not res_ent.empty:
                    fig_ent = px.bar(
                        res_ent,
                        x="Mes_Nom",
                        y="Cantidad",
                        color="Marca_Graf",
                        barmode="group",
                        custom_data=["Detalle_Canales"],
                        title=f"🤝 Entregas por Mes y Marca ({anio_sel_g})",
                        text_auto=True,
                        color_discrete_map=MAPA_COLORES_MARCA,
                        template="plotly_white"
                    )
                    fig_ent.update_traces(
                        hovertemplate="<b>%{x} - %{data.name}</b><br>Total Entregados: <b>%{y}</b><br><br><b>Detalle por Canal:</b><br>%{customdata[0]}<extra></extra>"
                    )
                    fig_ent.update_layout(
                        xaxis_title="Mes",
                        yaxis_title="Unidades Entregadas",
                        height=350,
                        xaxis=dict(tickangle=-30),
                        legend_title="Marca",
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                    )
                    st.plotly_chart(fig_ent, use_container_width=True, key="g_ent_ho")
                else:
                    st.info(f"No hay entregas cargadas para el año {anio_sel_g}.")

        st.divider()
        pat_v = df_ho[df_ho["Fecha de Patentamiento"].notna()]

        if "Estado" in df_ho.columns:
            ent_v = df_ho[df_ho["Estado"].astype(str).str.upper().str.contains('ENTREGADO', na=False)]
        else:
            ent_v = df_ho[df_ho["Fecha de confirmacion de entrega"].notna()]

        fal_v = pat_v[~pat_v['TIENE_HO']]
        eficacia = (len(pat_v[pat_v['TIENE_HO']]) / len(pat_v) * 100) if len(pat_v) > 0 else 0

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("🚗 Patentados", len(pat_v))
        m2.metric("🤝 Entregados", len(ent_v))
        m3.metric("⚠️ Faltan Hand Over", len(fal_v), delta="Atención requerida" if len(fal_v) > 0 else "Al día", delta_color="inverse")
        m4.metric("📈 % Eficacia", f"{eficacia:.1f}%")

        st.divider()

        st.write("### 📌 Seguimiento Operativo: Pendientes de Hand Over")

        col_entrega_ho = "Fecha de confirmacion de entrega"
        col_ho_fecha = "Fecha de Hand over"

        df_entregados_real = df_ho.copy()
        if "Estado" in df_entregados_real.columns:
            df_entregados_real = df_entregados_real[
                df_entregados_real["Estado"].astype(str).str.strip().str.upper() == "ENTREGADO"
            ].copy()

        if col_entrega_ho in df_entregados_real.columns:
            df_entregados_real[col_entrega_ho] = pd.to_datetime(
                df_entregados_real[col_entrega_ho].astype(str).str.strip(),
                dayfirst=True, format="mixed", errors='coerce'
            )
            df_entregados_real = df_entregados_real[df_entregados_real[col_entrega_ho].notna()].copy()

            hoy = pd.Timestamp.now()
            fechas_futuras = df_entregados_real[df_entregados_real[col_entrega_ho] > hoy]

            if not fechas_futuras.empty:
                st.warning(
                    f"⚠️ **Atención:** Se detectaron **{len(fechas_futuras)} registros** con 'Fecha de confirmacion de entrega' "
                    f"posterior a hoy ({hoy.strftime('%d/%m/%Y')}). Han sido excluidos de la matriz operativa."
                )
                df_entregados_real = df_entregados_real[df_entregados_real[col_entrega_ho] <= hoy].copy()

            anios_ent = df_entregados_real[col_entrega_ho].dt.year.dropna().unique()
            anios_validos_sem = sorted([int(a) for a in anios_ent if 2020 <= a <= 2030], reverse=True)
        else:
            anios_validos_sem = [2026]

        c_tit_sem, c_anio_sem = st.columns([3, 1])
        anio_sel_sem = c_anio_sem.selectbox(
            "📅 Año (según Confirmación de Entrega):",
            ["Todos"] + (anios_validos_sem if anios_validos_sem else [2026]),
            key="ho_anio_sem"
        )

        if anio_sel_sem != "Todos" and col_entrega_ho in df_entregados_real.columns:
            df_entregados_real = df_entregados_real[df_entregados_real[col_entrega_ho].dt.year == int(anio_sel_sem)]

        if col_ho_fecha in df_entregados_real.columns:
            ho_limpio = df_entregados_real[col_ho_fecha].astype(str).str.strip().str.lower()
            mascara_vacios = ho_limpio.isin(["nan", "none", "nat", "", "-", "null"]) | df_entregados_real[col_ho_fecha].isna()
            df_criticos = df_entregados_real[mascara_vacios].copy()
        else:
            df_criticos = df_entregados_real[~df_entregados_real['TIENE_HO']].copy()

        estado_clickeado = None

        if not df_criticos.empty:
            df_criticos["Mes_Num_Ent"] = df_criticos[col_entrega_ho].dt.month.fillna(0).astype(int)
            df_criticos["Mes_Nom_Ent"] = df_criticos["Mes_Num_Ent"].map(MESES_ESP).fillna("Sin Fecha")

            col_tabla_matriz, col_graf_sem = st.columns([3, 2])

            with col_tabla_matriz:
                st.write("#### 📋 Matriz Mensual por Estado Interno")
                tabla_cruzada = pd.crosstab(
                    index=df_criticos[col_ei],
                    columns=df_criticos["Mes_Nom_Ent"],
                    margins=True,
                    margins_name="TOTAL"
                )

                orden_meses = [MESES_ESP[m] for m in sorted(MESES_ESP.keys()) if MESES_ESP[m] in tabla_cruzada.columns]
                extras = [c for c in tabla_cruzada.columns if c not in orden_meses and c != "TOTAL"]
                if "TOTAL" in tabla_cruzada.columns:
                    orden_final = orden_meses + extras + ["TOTAL"]
                else:
                    orden_final = orden_meses + extras

                tabla_cruzada = tabla_cruzada[orden_final]
                st.dataframe(tabla_cruzada, use_container_width=True, height=280)

            with col_graf_sem:
                st.write("#### 📊 Distribución Visual (💡 Hacé clic para filtrar abajo)")
                conteo_ei = df_criticos[col_ei].value_counts().reset_index()
                conteo_ei.columns = ["Estado Interno", "Cantidad"]

                fig_sem = px.bar(
                    conteo_ei, x="Cantidad", y="Estado Interno",
                    orientation="h", text_auto=True,
                    title=f"Pendientes ({anio_sel_sem}) - Total: {len(df_criticos)}",
                    color="Cantidad", color_continuous_scale="Reds",
                    template="plotly_white"
                )
                fig_sem.update_layout(showlegend=False, height=280, margin=dict(t=40, l=10, r=10, b=10))

                evento_grafico = st.plotly_chart(fig_sem, use_container_width=True, on_select="rerun", key="g_sem_ho_int")

                if evento_grafico and "selection" in evento_grafico and evento_grafico["selection"]["points"]:
                    estado_clickeado = evento_grafico["selection"]["points"][0]["y"]
        else:
            st.success(f"✅ ¡Excelente! No hay vehículos pendientes de Hand Over para el periodo seleccionado ({anio_sel_sem}).")

        st.divider()

        st.write("### 📋 Detalle y Gestión de Unidades")

        c_aviso, c_boton, c_busq = st.columns([3, 1, 2])

        if estado_clickeado:
            c_aviso.info(f"🔎 Filtrando por la barra seleccionada en el gráfico: **{estado_clickeado}**")
            if c_boton.button("❌ Quitar filtro de barra", use_container_width=True):
                st.rerun()
        else:
            c_aviso.caption("💡 Mostrando todos los casos de la matriz. Hacé clic en una barra del gráfico superior para filtrar por estado.")

        busq_ex = c_busq.text_input("🔍 Búsqueda rápida:", key="ex_busq", placeholder="Cliente, chasis, patente...")

        df_mostrar_ex = df_criticos.copy()

        if estado_clickeado:
            df_mostrar_ex = df_mostrar_ex[df_mostrar_ex[col_ei] == estado_clickeado]

        if busq_ex:
            mask = df_mostrar_ex.apply(lambda row: row.astype(str).str.contains(busq_ex, case=False).any(), axis=1)
            df_mostrar_ex = df_mostrar_ex[mask]

        cols_ok_ex = [c for c in COLUMNAS_HO if c in df_mostrar_ex.columns]
        st.dataframe(df_mostrar_ex[cols_ok_ex], use_container_width=True, hide_index=True, height=450)

    # ---------------------------------------------------------
    # PESTAÑA 2: ANIMACIÓN DE CLIENTES DE VENTA (Intacta)
    # ---------------------------------------------------------
    with tab_animacion_v:
        st.header("📣 Animación de clientes VN")
        st.write("Listado de clientes con estado **En Espera** para seguimiento y animación de respuestas.")

        col_em = "Estado de la marca"
        if col_em not in df.columns:
            col_encontrada = [c for c in df.columns if c.upper().strip() == "ESTADO DE LA MARCA"]
            if col_encontrada:
                col_em = col_encontrada[0]
            else:
                st.error("❌ No se encontró la columna 'Estado de la marca' en la hoja de Google Sheets.")

        df_anim = pd.DataFrame()

        if col_em in df.columns:
            df_anim = df[df[col_em].astype(str).str.strip().str.upper() == "EN ESPERA"].copy()

            st.divider()
            f_col1, f_col2, f_col3 = st.columns(3)

            marcas_anim = sorted(df_anim["Marca"].dropna().unique()) if "Marca" in df_anim.columns else []
            sel_marca = f_col1.multiselect("📌 Filtrar por Marca", options=marcas_anim, key="anim_marca")

            canales_anim = sorted(df_anim["Canal de Venta"].dropna().unique()) if "Canal de Venta" in df_anim.columns else []
            sel_canal = f_col2.multiselect("📌 Filtrar por Canal de Venta", options=canales_anim, key="anim_canal")

            vendedores_anim = sorted(df_anim["Vendedor"].dropna().unique()) if "Vendedor" in df_anim.columns else []
            sel_vend = f_col3.multiselect("📌 Filtrar por Vendedor", options=vendedores_anim, key="anim_vend")

            if sel_marca:
                df_anim = df_anim[df_anim["Marca"].isin(sel_marca)]
            if sel_canal:
                df_anim = df_anim[df_anim["Canal de Venta"].isin(sel_canal)]
            if sel_vend:
                df_anim = df_anim[df_anim["Vendedor"].isin(sel_vend)]

            st.divider()
            m_col1, m_col2 = st.columns([1, 3])
            m_col1.metric("🔔 Total a Animar", f"{len(df_anim)} clientes")

            with m_col2:
                busq_anim = st.text_input("🔍 Búsqueda rápida por Cliente, Teléfono o E-mail:", key="busq_anim")
                if busq_anim:
                    mask_anim = df_anim.apply(lambda row: row.astype(str).str.contains(busq_anim, case=False).any(), axis=1)
                    df_anim = df_anim[mask_anim]

            def crear_link_whatsapp(row):
                asesor = str(row.get("Vendedor", "")).strip().upper()
                cliente = str(row.get("Cliente", "el cliente")).strip()
                telefono = str(row.get("Teléfono", "-")).strip()
                canal = str(row.get("Canal de Venta", "-")).strip()
                marca = str(row.get("Marca", "")).strip().upper()
                email = str(row.get("E-mail", "-")).strip()

                def limpiar_texto(val):
                    txt = str(val).strip()
                    return "Sin comentarios" if txt.lower() in ["nan", "none", "", "null", "-"] else txt

                def formatear_fecha(val):
                    if pd.isna(val) or str(val).lower() in ["nan", "none", "", "nat", "null"]:
                        return "Sin fecha"
                    if isinstance(val, pd.Timestamp):
                        return val.strftime("%d/%m/%Y")
                    return str(val)

                com_temp = limpiar_texto(row.get("Comentario Enc. Temp."))
                com_int = limpiar_texto(row.get("Comentario de la Encuesta interna"))

                f_inv = formatear_fecha(row.get("Fecha de invitación Inicial"))
                f_r1 = formatear_fecha(row.get("Primera fecha de recordatorio"))
                f_r2 = formatear_fecha(row.get("Segunda fecha de recordatorio"))
                f_venc = formatear_fecha(row.get("Fecha de Vencimento Del Trabajo de Campo"))

                numero_asesor = TELEFONOS_ASESORES.get(asesor)

                if not numero_asesor:
                    return None

                mensaje = (
                    f"Hola, {asesor}! Tenes al cliente {canal} - {cliente} - (Tel: {telefono}) "
                    f"está pendiente de responder la encuesta de la marca de {marca} que le llego "
                    f"por email {email}. Por favor, de animarlo a que la responda.\n\n"
                    f"📅 *Fechas Clave:*\n"
                    f"• Invitación Inicial: {f_inv}\n"
                    f"• 1° Recordatorio: {f_r1}\n"
                    f"• 2° Recordatorio: {f_r2}\n"
                    f"• Vencimiento Trabajo de Campo: {f_venc}\n\n"
                    f"📝 *A continuación te dejo todas las respuestas previas:*\n"
                    f"• Comentario Enc. Temp.: {com_temp}\n"
                    f"• Comentario Encuesta Interna: {com_int}"
                )
                texto_encoded = urllib.parse.quote(mensaje)
                return f"https://web.whatsapp.com/send?phone={numero_asesor}&text={texto_encoded}"

            df_anim["📲 WhatsApp"] = df_anim.apply(crear_link_whatsapp, axis=1)

            cols_anim_ok = [c for c in COLUMNAS_ANIMACION if c in df_anim.columns]
            cols_con_marca = ["Marca", "📲 WhatsApp"] + [c for c in cols_anim_ok if c != "Marca"]

            df_tabla = df_anim[cols_con_marca].copy()

            cols_notas = ["Encuesta Temprana", "EI - Reco"]
            for col_n in cols_notas:
                if col_n in df_tabla.columns:
                    s_num = pd.to_numeric(df_tabla[col_n], errors='coerce')
                    df_tabla[col_n] = s_num.apply(lambda x: f"{int(round(x))}" if pd.notna(x) else "-")

            columnas_fecha = [
                "Fecha de invitación Inicial",
                "Primera fecha de recordatorio",
                "Segunda fecha de recordatorio",
                "Fecha de Vencimento Del Trabajo de Campo"
            ]

            for col in df_tabla.columns:
                if col not in columnas_fecha and col not in cols_notas:
                    df_tabla[col] = df_tabla[col].fillna("-")

            def resaltar_canal(row):
                estilos = [''] * len(row)
                if "Canal de Venta" in row.index and "Marca" in row.index:
                    idx_canal = row.index.get_loc("Canal de Venta")
                    marca = str(row["Marca"]).upper()
                    if "PEUGEOT" in marca:
                        estilos[idx_canal] = 'background-color: #d0e1fd; color: #0c326f; font-weight: bold;'
                    elif "CITRO" in marca:
                        estilos[idx_canal] = 'background-color: #fde2c4; color: #78350f; font-weight: bold;'
                return estilos

            df_estilizado = df_tabla.style.apply(resaltar_canal, axis=1).hide(axis="index").hide(subset=["Marca"], axis="columns")

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
                    "Encuesta Temprana": st.column_config.TextColumn("Encuesta Temprana", width="small"),
                    "EI - Reco": st.column_config.TextColumn("EI - Reco", width="small"),
                    "Comentario Enc. Temp.": st.column_config.TextColumn("Comentario Enc. Temp.", width="medium"),
                    "Comentario de la Encuesta interna": st.column_config.TextColumn("Comentario Encuesta Interna", width="large"),
                    "Fecha de invitación Inicial": st.column_config.DateColumn("Invitación Inicial", format="DD/MM/YYYY"),
                    "Primera fecha de recordatorio": st.column_config.DateColumn("1° Recordatorio", format="DD/MM/YYYY"),
                    "Segunda fecha de recordatorio": st.column_config.DateColumn("2° Recordatorio", format="DD/MM/YYYY"),
                    "Fecha de Vencimento Del Trabajo de Campo": st.column_config.DateColumn("Vencimiento", format="DD/MM/YYYY")
                }
            )

            cols_faltantes = set(COLUMNAS_ANIMACION) - set(cols_anim_ok)
            if cols_faltantes:
                st.caption(f"⚠️ Nota: Las siguientes columnas solicitadas no fueron encontradas con ese nombre exacto en el archivo original: {', '.join(cols_faltantes)}")

    # ---------------------------------------------------------
    # PESTAÑA 3: ANIMACIÓN DE CLIENTES PVT (Intacta)
    # ---------------------------------------------------------
    with tab_animacion_pv:
        st.header("🔧 Animación de clientes PVT")
        st.write("Seguimiento y métricas de encuestas de clientes en la base PVT ROAR.")

        posibles_cols = [c for c in df_pv.columns if "ESTADO DE LA ENCUESTA" in str(c).upper()]
        col_estado_real = None
        for col in posibles_cols:
            if df_pv[col].astype(str).str.contains('Descartado|Caducada|Contestada|En espera', case=False, na=False).any():
                col_estado_real = col
                break
        if not col_estado_real and posibles_cols:
            col_estado_real = posibles_cols[-1]

        col_importacion = next((c for c in df_pv.columns if "IMPORTACI" in str(c).upper() and "FECHA" in str(c).upper()), None)
        if col_importacion:
            df_pv[col_importacion] = pd.to_datetime(df_pv[col_importacion].astype(str).str.strip(), dayfirst=True, format="mixed", errors="coerce")

        if not col_estado_real:
            st.error("❌ No se encontró la columna 'Estado de la Encuesta' con los datos correctos.")
        else:
            estados_unicos = sorted(df_pv[col_estado_real].dropna().astype(str).unique())
            estados_limpios = [e for e in estados_unicos if e.strip() != "" and not any(char.isdigit() for char in str(e))]

            st.divider()

            c_anio, c_filtro, c_marcas, c_t, c_asesores = st.columns([1, 1.5, 2.2, 1, 3.8])

            with c_anio:
                if col_importacion:
                    anios_disp = sorted(df_pv[col_importacion].dt.year.dropna().astype(int).unique(), reverse=True)
                    anio_sel = st.selectbox("📅 Año:", ["Todos"] + anios_disp)
                else:
                    anio_sel = "Todos"
                    st.selectbox("📅 Año:", ["Todos"], disabled=True)

            df_pv_anio = df_pv.copy()
            if anio_sel != "Todos" and col_importacion:
                df_pv_anio = df_pv_anio[df_pv_anio[col_importacion].dt.year == int(anio_sel)]

            with c_filtro:
                opciones_filtro = ["Todos"] + estados_limpios
                idx_default = next((i for i, opc in enumerate(opciones_filtro) if opc.strip().lower() == "en espera"), 0)
                estado_seleccionado = st.selectbox("📌 Estado:", opciones_filtro, index=idx_default)

            col_asesor = "Nombre del asesor"
            dict_tr_asesores = {}

            if col_asesor in df_pv_anio.columns:
                for asesor, group in df_pv_anio.groupby(col_asesor):
                    estados_asesor = group[col_estado_real].astype(str).str.strip().str.lower()

                    contestada = (estados_asesor == "contestada").sum()
                    caducada = (estados_asesor == "caducada").sum()
                    en_espera = (estados_asesor == "en espera").sum()

                    denominador = contestada + caducada + en_espera
                    tr = (contestada / denominador * 100) if denominador > 0 else 0

                    dict_tr_asesores[str(asesor).strip()] = f"{tr:.1f}%"

            df_pv_filtrado = df_pv_anio.copy()
            if estado_seleccionado != "Todos":
                df_pv_filtrado = df_pv_filtrado[df_pv_filtrado[col_estado_real].astype(str) == estado_seleccionado]

            with c_marcas:
                if "Marca" in df_pv_filtrado.columns:
                    df_pv_filtrado["Marca_Norm"] = df_pv_filtrado["Marca"].astype(str).str.upper()
                    cant_peugeot = len(df_pv_filtrado[df_pv_filtrado["Marca_Norm"].str.contains("PEUGEOT", na=False)])
                    cant_citroen = len(df_pv_filtrado[df_pv_filtrado["Marca_Norm"].str.contains("CITRO", na=False)])

                    opciones_marcas = []
                    mapa_marcas = {}

                    if cant_peugeot > 0:
                        lbl_p = f"🦁 Peugeot ({cant_peugeot})"
                        opciones_marcas.append(lbl_p)
                        mapa_marcas[lbl_p] = "PEUGEOT"
                    if cant_citroen > 0:
                        lbl_c = f"⚙️ Citroën ({cant_citroen})"
                        opciones_marcas.append(lbl_c)
                        mapa_marcas[lbl_c] = "CITRO"

                    if opciones_marcas:
                        marca_seleccionada = st.pills("🏷️ Filtrar por Marca:", options=opciones_marcas, key="pills_marca_pv")

                        if marca_seleccionada:
                            marca_real = mapa_marcas[marca_seleccionada]
                            df_pv_filtrado = df_pv_filtrado[df_pv_filtrado["Marca_Norm"].str.contains(marca_real, na=False)]
                else:
                    st.warning("⚠️ Sin columna Marca")

            with c_t:
                st.metric("📊 Total", len(df_pv_filtrado))

            with c_asesores:
                if col_asesor in df_pv_filtrado.columns:
                    conteo_asesores = df_pv_filtrado[col_asesor].value_counts()
                    opciones_pills = []
                    mapa_asesores = {}

                    for asesor, cant in conteo_asesores.items():
                        asesor_str = str(asesor).strip()
                        if asesor_str and asesor_str.lower() not in ['nan', 'none', '']:
                            tr_actual = dict_tr_asesores.get(asesor_str, "0.0%")
                            label_boton = f"{asesor_str} ({cant}) | TR: {tr_actual}"
                            opciones_pills.append(label_boton)
                            mapa_asesores[label_boton] = asesor_str

                    if opciones_pills:
                        asesor_seleccionado_label = st.pills(
                            "👥 Filtro Rápido por Asesor (TR = Tasa de Respuesta):",
                            options=opciones_pills,
                            key="pills_asesor_pv"
                        )
                        if asesor_seleccionado_label:
                            asesor_real = mapa_asesores[asesor_seleccionado_label]
                            df_pv_filtrado = df_pv_filtrado[df_pv_filtrado[col_asesor].astype(str).str.strip() == asesor_real]

            st.divider()

            c_tit_tabla, c_busq_tabla = st.columns([3, 1])
            c_tit_tabla.write("### 📋 Detalle de Clientes")
            busq_pv = c_busq_tabla.text_input("🔍 Búsqueda rápida:", placeholder="Nombre, correo...", key="busq_pv_unica")

            if busq_pv:
                mask_pv = df_pv_filtrado.apply(lambda row: row.astype(str).str.contains(busq_pv, case=False).any(), axis=1)
                df_pv_filtrado = df_pv_filtrado[mask_pv]

            columnas_deseadas_pv = [
                "Marca",
                "Nombre del cliente",
                "Correo electrónico del cliente",
                "Fecha del evento",
                "Estado de la Encuesta",
                "Fecha de invitación Inicial",
                "Primera fecha de recordatorio",
                "Segunda fecha de recordatorio",
                "Fecha de Vencimento Del Trabajo de Campo",
                "Encuesta interna"
            ]

            cols_mostrar_pv = []
            for col_deseada in columnas_deseadas_pv:
                match = next((c for c in df_pv_filtrado.columns if c.lower().strip() == col_deseada.lower().strip()), None)
                if not match:
                    match = next((c for c in df_pv_filtrado.columns if col_deseada.lower().strip() in c.lower().strip()), None)
                if match and match not in cols_mostrar_pv:
                    cols_mostrar_pv.append(match)

            if col_estado_real and col_estado_real not in cols_mostrar_pv:
                cols_mostrar_pv.insert(4, col_estado_real)

            if cols_mostrar_pv:
                df_final = df_pv_filtrado[cols_mostrar_pv].copy()

                nombres_cortos = {
                    col_estado_real: "Estado",
                    next((c for c in cols_mostrar_pv if "invitación" in c.lower()), "N/A"): "Invitación",
                    next((c for c in cols_mostrar_pv if "primera" in c.lower()), "N/A"): "1° Recordatorio",
                    next((c for c in cols_mostrar_pv if "segunda" in c.lower()), "N/A"): "2° Recordatorio",
                    next((c for c in cols_mostrar_pv if "vencimento" in c.lower() or "vencimiento" in c.lower()), "N/A"): "Vencimiento",
                    next((c for c in cols_mostrar_pv if "correo" in c.lower()), "N/A"): "Correo"
                }

                nombres_cortos = {k: v for k, v in nombres_cortos.items() if k != "N/A" and k in df_final.columns}
                df_final = df_final.rename(columns=nombres_cortos)

                def estilizar_marca(row):
                    estilos = [''] * len(row)
                    if "Marca" in row.index:
                        idx_marca = row.index.get_loc("Marca")
                        marca_val = str(row["Marca"]).upper()
                        if "PEUGEOT" in marca_val:
                            estilos[idx_marca] = 'background-color: #1e3d59; color: white; font-weight: bold;'
                        elif "CITRO" in marca_val:
                            estilos[idx_marca] = 'background-color: #ff6e40; color: white; font-weight: bold;'
                    return estilos

                df_final_estilizado = df_final.style.apply(estilizar_marca, axis=1).hide(axis="index")

                st.dataframe(df_final_estilizado, use_container_width=True, height=450)
            else:
                st.warning("⚠️ No se detectó ninguna de las columnas solicitadas.")

    # ---------------------------------------------------------
    # PESTAÑA 4: ANÁLISIS DE TIEMPOS (INTERACTIVO BIDIRECCIONAL)
    # ---------------------------------------------------------
    with tab_tiempos:
        st.header("⏱️ Análisis de Tiempos")

        MESES_TIEMPOS = {
            1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
            7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
        }

        # 1. EXPANDER PARA GRÁFICO ORIGINAL
        with st.expander("📊 Evolución Mensual e Interactividad (Clic para expandir)"):
            st.info("💡 Visualizá la evolución mensual de volumen por Facturación o Patentamiento.")

            g_col1, g_col2 = st.columns(2)

            y_fact = df["Fecha de Facturacion"].dt.year.dropna().unique() if 'Fecha de Facturacion' in df.columns else []
            y_pat = df["Fecha de Patentamiento"].dt.year.dropna().unique() if 'Fecha de Patentamiento' in df.columns else []
            años_crudos = list(set(y_fact) | set(y_pat))
            años_limpios_graf = sorted([int(a) for a in años_crudos if pd.notna(a)], reverse=True)

            año_sel_graf = g_col1.selectbox("Año (Gráfico):", años_limpios_graf if años_limpios_graf else [datetime.now().year], key="sel_año_graf")
            tipo_g = g_col2.pills("Evolución Mensual de:", ["Facturación", "Patentamiento"], default="Facturación", key="pill_tipo_graf")

            col_f_graf = "Fecha de Facturacion" if tipo_g == "Facturación" else "Fecha de Patentamiento"

            if col_f_graf in df.columns and not df.empty:
                df_g = df[df[col_f_graf].dt.year == año_sel_graf].copy()
                if not df_g.empty:
                    df_g["Mes_Num"] = df_g[col_f_graf].dt.month
                    df_g["Mes_Nom"] = df_g["Mes_Num"].map(MESES_TIEMPOS)
                    resumen = df_g.groupby(["Mes_Num", "Mes_Nom"]).size().reset_index(name="Cant")

                    fig_v = px.bar(
                        resumen.sort_values("Mes_Num"), x="Mes_Nom", y="Cant", text_auto=True,
                        title=f"Volumen de {tipo_g} - {año_sel_graf}",
                        color_discrete_sequence=['#3498db' if tipo_g == "Facturación" else '#2ecc71'],
                        template="plotly_white", height=300
                    )
                    fig_v.update_traces(
                        hovertemplate="<b>%{x}</b><br>Volumen: <b>%{y} unid.</b><extra></extra>"
                    )
                    st.plotly_chart(fig_v, use_container_width=True, key="g_evol_mensual_tiempos")

        st.divider()

        # 2. PANEL DE CONTROL DE GERENCIA (ÚNICAMENTE FILTROS DE AÑO, MES Y MARCA)
        st.write("### 🎯 Panel de Control de Tiempos por Línea de Tiempo")
        st.caption("Se analizan exclusivamente **Venta Tradicional (T)** y **Plan de Ahorro (PDA)**. Operaciones de Mayorista y Autopatentado quedan excluidas.")

        y_entrega = df["Fecha de confirmacion de entrega"].dt.year.dropna().unique() if "Fecha de confirmacion de entrega" in df.columns else []
        años_limpios_entrega = sorted([int(a) for a in y_entrega if pd.notna(a)], reverse=True)
        marcas_disponibles = sorted(df["Marca"].dropna().astype(str).str.strip().unique()) if "Marca" in df.columns else []

        col_filtro_y, col_filtro_m, col_filtro_mar = st.columns([1, 1.5, 2])

        año_panel = col_filtro_y.selectbox("📅 Seleccione Año (Entrega):", ["Todos"] + años_limpios_entrega, key="año_panel_tiempos")
        mes_panel = col_filtro_m.selectbox("📅 Seleccione Mes (Entrega):", ["Todos"] + list(MESES_TIEMPOS.values()), key="mes_panel_tiempos")
        marca_panel = col_filtro_mar.multiselect("🏷️ Seleccione Marca:", options=marcas_disponibles, placeholder="Todas las marcas...", key="marca_panel_tiempos")

        df_t_base = df.copy()

        if "Fecha de confirmacion de entrega" in df_t_base.columns:
            if año_panel != "Todos":
                df_t_base = df_t_base[df_t_base["Fecha de confirmacion de entrega"].dt.year == int(año_panel)]
            if mes_panel != "Todos":
                mes_num_reves = {v: k for k, v in MESES_TIEMPOS.items()}
                df_t_base = df_t_base[df_t_base["Fecha de confirmacion de entrega"].dt.month == mes_num_reves[mes_panel]]

        if "Marca" in df_t_base.columns and len(marca_panel) > 0:
            df_t_base = df_t_base[df_t_base["Marca"].astype(str).str.strip().isin(marca_panel)]

        # 3. FUNCIONES DE CÁLCULO DE DÍAS HÁBILES (LUNES A VIERNES)
        def calcular_dias_habiles(start, end):
            if pd.isna(start) or pd.isna(end): return np.nan
            try:
                s, e = pd.to_datetime(start), pd.to_datetime(end)
                if s > e: return 0
                return max(0, len(pd.bdate_range(s, e)) - 1)
            except: return np.nan

        def calcular_dias_legajo(start, end):
            if pd.isna(start) or pd.isna(end): return np.nan
            try:
                s, e = pd.to_datetime(start), pd.to_datetime(end)
                if s <= e:
                    return max(0, len(pd.bdate_range(s, e)) - 1)
                else:
                    return max(0, len(pd.bdate_range(e, s)) - 1)
            except: return np.nan

        def auditar_carga_administrativa(start, end):
            if pd.isna(start) or pd.isna(end): return "Sin datos"
            try:
                s, e = pd.to_datetime(start), pd.to_datetime(end)
                if s == e: return "⚡ En el día"
                elif s < e: return "✅ Normal"
                else: return "🚨 Carga Atrasada"
            except: return "Sin datos"

        def fmt_fecha_corta(val):
            if pd.isna(val): return "Sin fecha"
            try:
                return pd.to_datetime(val).strftime("%d/%m/%Y")
            except:
                return "Sin fecha"

        # 4. CONFIGURACIONES DE LÍNEA DE TIEMPO POR CANAL (CON FECHAS DE REFERENCIA PARA TOOLTIP)
        SLA_CONFIG_T = {
            "T. Adm desde FF": {
                "sla": 2, "icon": "🧾", "label": "Adm. desde FF (FF ➔ FPP)",
                "f_ini": "Fecha de Facturacion", "f_fin": "Fecha de Pedido de Preparación",
                "desc": "Mide el tiempo desde la Fecha de Facturación (FF) hasta el Pedido de Preparación (FPP)."
            },
            "T. Adm desde FPP": {
                "sla": 2, "icon": "📁", "label": "Adm. desde FPP (FPP ➔ FGRD)",
                "f_ini": "Fecha de Pedido de Preparación", "f_fin": "Fecha que el Gestor Retira Doc",
                "desc": "Mide los días hábiles entre el Pedido de Preparación (FPP) y el Retiro de Documentación (FGRD). Si FPP es posterior a FGRD, mide los días de atraso de carga."
            },
            "T. Adm Total": {
                "sla": 4, "icon": "🗂️", "label": "Total Administrativo (FF ➔ FGRD)",
                "f_ini": "Fecha de Facturacion", "f_fin": "Fecha que el Gestor Retira Doc",
                "desc": "Mide el tiempo administrativo acumulado desde la Fecha de Facturación (FF) hasta que el Gestor retira la documentación (FGRD)."
            },
            "Días Inscripción": {
                "sla": 1, "icon": "📝", "label": "Gestoría: Inscripción (FGRD ➔ FDP)",
                "f_ini": "Fecha que el Gestor Retira Doc", "f_fin": "Fecha de Patentamiento",
                "desc": "Mide el tiempo desde que el Gestor retira la documentación (FGRD) hasta el Patentamiento (FDP)."
            },
            "Días Papeles": {
                "sla": 2, "icon": "📄", "label": "Gestoría: Disp. Papeles (FDP ➔ Disp.)",
                "f_ini": "Fecha de Patentamiento", "f_fin": "Fecha Disponibilidad Papeles",
                "desc": "Mide el tiempo desde el Patentamiento (FDP) hasta la Disponibilidad de Papeles en sucursal."
            },
            "Lead Time Gestoría": {
                "sla": 3, "icon": "📊", "label": "Total Gestoría (FGRD ➔ Disp.)",
                "f_ini": "Fecha que el Gestor Retira Doc", "f_fin": "Fecha Disponibilidad Papeles",
                "desc": "Mide el tiempo total en gestoría externa, desde el retiro de documentación (FGRD) hasta la disponibilidad de papeles."
            },
            "Días USI": {
                "sla": 2, "icon": "🚗", "label": "Sector USI / Entrega (Disp. ➔ Entrega)",
                "f_ini": "Fecha Disponibilidad Papeles", "f_fin": "Fecha de confirmacion de entrega",
                "desc": "Mide el tiempo desde la Disponibilidad de Papeles hasta la Confirmación de Entrega al cliente."
            },
            "Lead Time Total": {
                "sla": 9, "icon": "🏁", "label": "Lead Time Total (FF ➔ Entrega)",
                "f_ini": "Fecha de Facturacion", "f_fin": "Fecha de confirmacion de entrega",
                "desc": "Mide el ciclo completo del canal Tradicional desde la Facturación (FF) hasta la Confirmación de Entrega (Objetivo acumulado: 9 días)."
            }
        }

        SLA_CONFIG_PDA = {
            "T. Adm desde FPP": {
                "sla": 2, "icon": "📁", "label": "Gestión Administrativa (FPP ➔ FGRD)",
                "f_ini": "Fecha de Pedido de Preparación", "f_fin": "Fecha que el Gestor Retira Doc",
                "desc": "Mide los días hábiles entre el Pedido de Preparación (FPP) y el Retiro de Documentación (FGRD). Si FPP es posterior a FGRD, mide los días de atraso de carga."
            },
            "Días Inscripción": {
                "sla": 1, "icon": "📝", "label": "Gestoría: Inscripción (FGRD ➔ FDP)",
                "f_ini": "Fecha que el Gestor Retira Doc", "f_fin": "Fecha de Patentamiento",
                "desc": "Mide el tiempo desde que el Gestor retira la documentación (FGRD) hasta el Patentamiento (FDP)."
            },
            "Días Papeles": {
                "sla": 2, "icon": "📄", "label": "Gestoría: Disp. Papeles (FDP ➔ Disp.)",
                "f_ini": "Fecha de Patentamiento", "f_fin": "Fecha Disponibilidad Papeles",
                "desc": "Mide el tiempo desde el Patentamiento (FDP) hasta la Disponibilidad de Papeles en sucursal."
            },
            "Lead Time Gestoría": {
                "sla": 3, "icon": "📊", "label": "Total Gestoría (FGRD ➔ Disp.)",
                "f_ini": "Fecha que el Gestor Retira Doc", "f_fin": "Fecha Disponibilidad Papeles",
                "desc": "Mide el tiempo total en gestoría externa, desde el retiro de documentación (FGRD) hasta la disponibilidad de papeles."
            },
            "Días USI": {
                "sla": 2, "icon": "🚗", "label": "Sector USI / Entrega (Disp. ➔ Entrega)",
                "f_ini": "Fecha Disponibilidad Papeles", "f_fin": "Fecha de confirmacion de entrega",
                "desc": "Mide el tiempo desde la Disponibilidad de Papeles hasta la Confirmación de Entrega al cliente."
            },
            "Lead Time Total": {
                "sla": 7, "icon": "🏁", "label": "Lead Time Total (FPP ➔ Entrega)",
                "f_ini": "Fecha de Pedido de Preparación", "f_fin": "Fecha de confirmacion de entrega",
                "desc": "Mide el ciclo completo de Plan de Ahorro desde el Pedido de Preparación (FPP) hasta la Confirmación de Entrega (Objetivo acumulado: 7 días)."
            }
        }

        # 5. FUNCIÓN REUTILIZABLE PARA RENDERIZAR CADA TABLERO DE CANAL
        def renderizar_tablero_canal(df_canal, sla_config, prefijo_key, es_tradicional):
            if df_canal.empty:
                st.info("No hay operaciones registradas para este canal con los filtros seleccionados.")
                return

            df_c = df_canal.copy()

            # Cálculos comunes
            df_c["T. Adm desde FPP"] = df_c.apply(lambda r: calcular_dias_legajo(r.get("Fecha de Pedido de Preparación"), r.get("Fecha que el Gestor Retira Doc")), axis=1)
            df_c["Auditoría Carga Legajo"] = df_c.apply(lambda r: auditar_carga_administrativa(r.get("Fecha de Pedido de Preparación"), r.get("Fecha que el Gestor Retira Doc")), axis=1)
            df_c["Días Inscripción"] = df_c.apply(lambda r: calcular_dias_habiles(r.get("Fecha que el Gestor Retira Doc"), r.get("Fecha de Patentamiento")), axis=1)
            df_c["Días Papeles"] = df_c.apply(lambda r: calcular_dias_habiles(r.get("Fecha de Patentamiento"), r.get("Fecha Disponibilidad Papeles")), axis=1)
            df_c["Lead Time Gestoría"] = df_c.apply(lambda r: calcular_dias_habiles(r.get("Fecha que el Gestor Retira Doc"), r.get("Fecha Disponibilidad Papeles")), axis=1)
            df_c["Días USI"] = df_c.apply(lambda r: calcular_dias_habiles(r.get("Fecha Disponibilidad Papeles"), r.get("Fecha de confirmacion de entrega")), axis=1)

            # Cálculos diferenciales por canal
            if es_tradicional:
                df_c["T. Adm desde FF"] = df_c.apply(lambda r: calcular_dias_habiles(r.get("Fecha de Facturacion"), r.get("Fecha de Pedido de Preparación")), axis=1)
                df_c["T. Adm Total"] = df_c.apply(lambda r: calcular_dias_habiles(r.get("Fecha de Facturacion"), r.get("Fecha que el Gestor Retira Doc")), axis=1)
                df_c["Lead Time Total"] = df_c.apply(lambda r: calcular_dias_habiles(r.get("Fecha de Facturacion"), r.get("Fecha de confirmacion de entrega")), axis=1)
                tramos_secuenciales = [
                    ("1. Adm. FF ➔ FPP", "T. Adm desde FF", "#5dade2"),
                    ("2. Adm. FPP ➔ FGRD", "T. Adm desde FPP", "#2e86c1"),
                    ("3. Inscripción (FGRD ➔ FDP)", "Días Inscripción", "#f5b041"),
                    ("4. Disp. Papeles (FDP ➔ Disp.)", "Días Papeles", "#eb984e"),
                    ("5. Sector USI (Disp. ➔ Entrega)", "Días USI", "#e74c3c")
                ]
                flujo_texto = "**Línea de Tiempo Tradicional:** `FF` ➔ `FPP` ➔ `FGRD` ➔ `FDP` ➔ `Disp. Papeles` ➔ `Conf. Entrega`"
            else:
                df_c["Lead Time Total"] = df_c.apply(lambda r: calcular_dias_habiles(r.get("Fecha de Pedido de Preparación"), r.get("Fecha de confirmacion de entrega")), axis=1)
                tramos_secuenciales = [
                    ("1. Gestión Adm. (FPP ➔ FGRD)", "T. Adm desde FPP", "#2e86c1"),
                    ("2. Inscripción (FGRD ➔ FDP)", "Días Inscripción", "#f5b041"),
                    ("3. Disp. Papeles (FDP ➔ Disp.)", "Días Papeles", "#eb984e"),
                    ("4. Sector USI (Disp. ➔ Entrega)", "Días USI", "#e74c3c")
                ]
                flujo_texto = "**Línea de Tiempo Plan de Ahorro (PDA):** `FPP` ➔ `FGRD` ➔ `FDP` ➔ `Disp. Papeles` ➔ `Conf. Entrega`"

            # Aseguramos tipo numérico limpio para evitar que se imprima "None" en la tabla
            for col_m in sla_config.keys():
                if col_m in df_c.columns:
                    df_c[col_m] = pd.to_numeric(df_c[col_m], errors="coerce")

            # --- A. BARRA VISUAL DE COMPOSICIÓN DE LA LÍNEA DE TIEMPO (CON HOVER ENRIQUECIDO) ---
            st.markdown(f"{flujo_texto} &nbsp; | &nbsp; **Unidades evaluadas:** `{len(df_c)}`")

            datos_timeline = []
            mapa_colores_tl = {}
            for nombre_etapa, col_etapa, color_hex in tramos_secuenciales:
                serie_ok = df_c[col_etapa].dropna()
                if not serie_ok.empty and serie_ok.mean() > 0:
                    prom_val = serie_ok.mean()
                    sla_et = sla_config[col_etapa]["sla"]
                    estado_et = "✅ En objetivo" if prom_val <= sla_et else f"🚨 +{prom_val - sla_et:.1f} d sobre SLA"
                    datos_timeline.append({
                        "Proceso": "Promedio del Ciclo",
                        "Etapa": nombre_etapa,
                        "Días": round(prom_val, 1),
                        "SLA": sla_et,
                        "Unidades": len(serie_ok),
                        "Estado": estado_et
                    })
                    mapa_colores_tl[nombre_etapa] = color_hex

            if datos_timeline:
                df_tl = pd.DataFrame(datos_timeline)
                fig_tl = px.bar(
                    df_tl, x="Días", y="Proceso", color="Etapa", orientation="h",
                    text="Días", custom_data=["Etapa", "SLA", "Unidades", "Estado"],
                    color_discrete_map=mapa_colores_tl,
                    title="🧭 Radiografía del Ciclo Promedio (Pasá el cursor por cada etapa)",
                    template="plotly_white"
                )
                fig_tl.update_traces(
                    texttemplate="%{text:.1f} d",
                    textposition="inside",
                    hovertemplate="<b>%{customdata[0]}</b><br>Promedio real: <b>%{x:.1f} días</b><br>Objetivo SLA: %{customdata[1]} días<br>Unidades medidas: %{customdata[2]}<br>Estado: <b>%{customdata[3]}</b><extra></extra>"
                )
                fig_tl.update_layout(
                    barmode="stack", height=185,
                    margin=dict(t=40, b=10, l=10, r=10),
                    yaxis_title="", xaxis_title="Días Hábiles Acumulados",
                    legend=dict(orientation="h", yanchor="top", y=-0.35, xanchor="center", x=0.5, title="")
                )
                st.plotly_chart(fig_tl, use_container_width=True, key=f"g_timeline_{prefijo_key}")

            st.divider()

            # --- B. BOTONES INTERACTIVOS (PILLS) ---
            st.caption("💡 Hacé clic en un tramo para auditar su % de cumplimiento y habilitá el cruce interactivo entre gráficos y clientes.")

            opciones_pills = []
            mapa_pills_a_columna = {}

            for col, datos in sla_config.items():
                promedio = df_c[col].mean()
                texto_prom = f"{promedio:.1f}d" if pd.notna(promedio) else "S/D"
                alerta = " 🔴" if pd.notna(promedio) and promedio > datos["sla"] else ""
                label_completo = f"{datos['icon']} {datos['label']} (Prom: {texto_prom}){alerta}"

                opciones_pills.append(label_completo)
                mapa_pills_a_columna[label_completo] = col

            texto_ayuda_tooltip = "Definiciones de Tramos:\n\n" + "\n\n".join([f"• {v['label']}: {v['desc']}" for v in sla_config.values()])

            kpi_seleccionado_label = st.pills(
                "Selecciona un Tramo a Analizar:",
                options=opciones_pills,
                default=opciones_pills[-1],
                help=texto_ayuda_tooltip,
                key=f"pills_kpi_{prefijo_key}"
            )
            col_kpi = mapa_pills_a_columna.get(kpi_seleccionado_label, "Lead Time Total")
            sla_actual = sla_config[col_kpi]["sla"]
            desc_actual = sla_config[col_kpi]["desc"]

            st.info(f"ℹ️ **¿Qué calcula este tramo?** {desc_actual}")

            # --- C. DASHBOARD GERENCIAL INTERACTIVO (HOVER + CLIC PARA FILTRAR) ---
            st.write(f"#### Análisis Detallado: **{sla_config[col_kpi]['label']}** (Objetivo: {sla_actual} días)")

            df_kpi = df_c[df_c[col_kpi].notna()].copy()
            status_click = None
            marca_click = None

            if not df_kpi.empty:
                df_kpi["Status SLA"] = np.where(df_kpi[col_kpi] <= sla_actual, "✅ En Término", "🚨 Demorado")
                if "Marca" in df_kpi.columns:
                    df_kpi["Marca_Lim"] = np.where(df_kpi["Marca"].astype(str).str.upper().str.contains("PEUGEOT"), "Peugeot",
                                          np.where(df_kpi["Marca"].astype(str).str.upper().str.contains("CITRO"), "Citroën", "Otra"))
                else:
                    df_kpi["Marca_Lim"] = "Otra"

                # Métricas especiales de higiene de carga para Gestión Administrativa (FPP -> FGRD)
                if col_kpi == "T. Adm desde FPP":
                    conteo_aud = df_kpi["Auditoría Carga Legajo"].value_counts(normalize=True) * 100
                    pct_dia = conteo_aud.get("⚡ En el día", 0)
                    pct_atrasada = conteo_aud.get("🚨 Carga Atrasada", 0)

                    c_aud1, c_aud2, _ = st.columns([2, 2, 4])
                    c_aud1.success(f"⚡ **Gestión en el Día:** {pct_dia:.1f}%")
                    c_aud2.error(f"🚨 **Cargas Atrasadas:** {pct_atrasada:.1f}%")
                    st.markdown("<br>", unsafe_allow_html=True)

                col_chart1, col_chart2 = st.columns(2)

                # --- Gráfico 1: Tasa de Cumplimiento (Donut Interactivo) ---
                res_sla_list = []
                for status_val, grp in df_kpi.groupby("Status SLA"):
                    prom_grp = grp[col_kpi].mean()
                    top_clis = grp.sort_values(by=col_kpi, ascending=False).head(3)
                    txt_clis = "<br>".join([f"• {str(r.get('Cliente', '-'))[:28]}: <b>{int(round(r[col_kpi]))}d</b>" for _, r in top_clis.iterrows()])
                    detalle_h = f"Promedio del grupo: <b>{prom_grp:.1f} días</b><br><br><b>Casos destacados:</b><br>{txt_clis}"
                    res_sla_list.append({"Status": status_val, "Cantidad": len(grp), "Detalle_Hover": detalle_h})

                conteo_sla = pd.DataFrame(res_sla_list)
                colores_sla = {"✅ En Término": "#2ecc71", "🚨 Demorado": "#e74c3c"}

                fig_donut = go.Figure(data=[go.Pie(
                    labels=conteo_sla["Status"],
                    values=conteo_sla["Cantidad"],
                    hole=0.5,
                    marker=dict(colors=[colores_sla.get(s, "#95a5a6") for s in conteo_sla["Status"]]),
                    textinfo="percent+value",
                    customdata=conteo_sla["Detalle_Hover"],
                    hovertemplate="<b>%{label}</b><br>Unidades: <b>%{value}</b> (%{percent})<br>%{customdata}<extra></extra>"
                )])
                fig_donut.update_layout(
                    title="Tasa de Cumplimiento (💡 Clic para filtrar tabla)",
                    height=330, margin=dict(t=45, b=10, l=10, r=10),
                    template="plotly_white"
                )
                evento_donut = col_chart1.plotly_chart(fig_donut, use_container_width=True, on_select="rerun", key=f"g_donut_{prefijo_key}")
                if evento_donut and "selection" in evento_donut and evento_donut["selection"]["points"]:
                    pt_d = evento_donut["selection"]["points"][0]
                    status_click = pt_d.get("label")
                    if not status_click and "point_number" in pt_d:
                        idx_pt = pt_d["point_number"]
                        if 0 <= idx_pt < len(conteo_sla):
                            status_click = conteo_sla.iloc[idx_pt]["Status"]

                # --- Gráfico 2: Comparativa por Marca (Barras Interactivas) ---
                res_marca_list = []
                for m_val, grp in df_kpi.groupby("Marca_Lim"):
                    prom_m = grp[col_kpi].mean()
                    pct_ok_m = (grp[col_kpi] <= sla_actual).mean() * 100
                    peor = grp.sort_values(by=col_kpi, ascending=False).iloc[0]
                    peor_txt = f"{str(peor.get('Cliente', '-'))[:26]} ({int(round(peor[col_kpi]))}d)"
                    res_marca_list.append({
                        "Marca_Lim": m_val,
                        "Promedio": prom_m,
                        "Unidades": len(grp),
                        "Pct_OK": pct_ok_m,
                        "Peor_Caso": peor_txt
                    })

                promedios_marca = pd.DataFrame(res_marca_list)
                fig_bar = px.bar(
                    promedios_marca, x="Marca_Lim", y="Promedio", text_auto=".1f",
                    custom_data=["Unidades", "Pct_OK", "Peor_Caso"],
                    title="Promedio por Marca (💡 Clic para filtrar tabla)",
                    color="Marca_Lim",
                    color_discrete_map={"Peugeot": "#1e3d59", "Citroën": "#ff6e40", "Otra": "#b0bec5"},
                    template="plotly_white"
                )
                fig_bar.update_traces(
                    hovertemplate=(
                        "<b>%{x}</b><br>"
                        "Promedio: <b>%{y:.1f} días hábiles</b><br>"
                        "Objetivo SLA: " + f"{sla_actual} días<br>"
                        "Unidades: <b>%{customdata[0]}</b> | En término: <b>%{customdata[1]:.1f}%</b><br>"
                        "Mayor demora: %{customdata[2]}<extra></extra>"
                    )
                )
                fig_bar.add_hline(y=sla_actual, line_dash="dot", line_color="red", annotation_text="Objetivo SLA")
                fig_bar.update_layout(height=330, margin=dict(t=45, b=10, l=10, r=10), showlegend=False, xaxis_title="", yaxis_title="Días Hábiles")
                evento_bar = col_chart2.plotly_chart(fig_bar, use_container_width=True, on_select="rerun", key=f"g_bar_{prefijo_key}")
                if evento_bar and "selection" in evento_bar and evento_bar["selection"]["points"]:
                    marca_click = evento_bar["selection"]["points"][0].get("x")
            else:
                st.info("No hay registros suficientes para graficar este KPI en el período seleccionado.")

            # --- RESERVAMOS ESPACIO PARA EL GRÁFICO INTERACTIVO DEL CLIENTE SELECCIONADO ---
            contenedor_cliente = st.container()

            # --- D. MATRIZ DE AUDITORÍA OPERATIVA (CON SELECCIÓN DE CLIENTE) ---
            st.write("### 📋 Matriz de Auditoría Operativa (Rojo = SLA Incumplido)")

            df_kpi_mostrar = df_kpi.copy()
            filtros_activos = []
            if status_click:
                df_kpi_mostrar = df_kpi_mostrar[df_kpi_mostrar["Status SLA"] == status_click]
                filtros_activos.append(f"Estado: **{status_click}**")
            if marca_click:
                df_kpi_mostrar = df_kpi_mostrar[df_kpi_mostrar["Marca_Lim"] == marca_click]
                filtros_activos.append(f"Marca: **{marca_click}**")

            c_info_f, c_btn_f = st.columns([4, 1])
            if filtros_activos:
                c_info_f.info(f"🔎 Filtrando matriz desde gráficos ➔ {' | '.join(filtros_activos)} ({len(df_kpi_mostrar)} unid.)")
                if c_btn_f.button("❌ Limpiar filtros", key=f"btn_limpiar_{prefijo_key}", use_container_width=True):
                    st.rerun()
            else:
                c_info_f.caption("💡 **Tip interactivo:** Hacé clic en la casilla/fila de cualquier **Cliente** para desplegar arriba su gráfico interactivo de tiempos y fechas exactas.")

            if not df_kpi_mostrar.empty:
                df_kpi_mostrar = df_kpi_mostrar.sort_values(by=col_kpi, ascending=False).reset_index(drop=True)

                cols_id = ["Vendedor", "Cliente", "Marca", "Chasis", "Auditoría Carga Legajo"]
                cols_metricas = list(sla_config.keys())
                cols_ok = [c for c in cols_id + cols_metricas if c in df_kpi_mostrar.columns]

                mapeo_columnas_tabla = {c_name: c_data["label"] for c_name, c_data in sla_config.items()}
                mapeo_columnas_tabla["Auditoría Carga Legajo"] = "Estado de Carga"
                mapeo_columnas_tabla["Vendedor"] = "Asesor"
                df_kpi_renombrado = df_kpi_mostrar[cols_ok].rename(columns=mapeo_columnas_tabla)

                label_lead_total = sla_config["Lead Time Total"]["label"]

                def resaltar_demoras_canal(row):
                    estilos = [''] * len(row)

                    for c_name, c_data in sla_config.items():
                        col_renombrada = c_data["label"]
                        if col_renombrada in row.index:
                            idx = row.index.get_loc(col_renombrada)
                            val = row[col_renombrada]
                            if col_renombrada == label_lead_total:
                                if pd.notna(val) and val > c_data["sla"]:
                                    estilos[idx] = 'background-color: #e74c3c; color: white; font-weight: bold;'
                                elif pd.notna(val) and val <= c_data["sla"]:
                                    estilos[idx] = 'background-color: #ccffcc; color: #006600;'
                            else:
                                if pd.notna(val) and val > c_data["sla"]:
                                    estilos[idx] = 'background-color: #ffcccc; color: #990000; font-weight: bold;'
                                elif pd.notna(val) and val <= c_data["sla"]:
                                    estilos[idx] = 'background-color: #ccffcc; color: #006600;'

                    if "Estado de Carga" in row.index:
                        idx_aud = row.index.get_loc("Estado de Carga")
                        val_aud = str(row["Estado de Carga"])
                        if "Atrasada" in val_aud:
                            estilos[idx_aud] = 'background-color: #ffebcc; color: #cc6600; font-weight: bold;'
                        elif "En el día" in val_aud:
                            estilos[idx_aud] = 'color: #006600; font-weight: bold;'

                    return estilos

                cols_numericas_formato = [c for c in df_kpi_renombrado.columns if c in [d["label"] for d in sla_config.values()]]
                df_estilizado = df_kpi_renombrado.style.apply(resaltar_demoras_canal, axis=1).format(
                    lambda x: f"{int(round(x))}" if pd.notna(x) else "-",
                    subset=cols_numericas_formato
                )

                evento_tabla = st.dataframe(
                    df_estilizado,
                    use_container_width=True,
                    hide_index=True,
                    height=420,
                    on_select="rerun",
                    selection_mode="single-row",
                    key=f"tabla_aud_{prefijo_key}"
                )

                # --- E. FICHA Y GRÁFICO INTERACTIVO AL HACER CLIC EN UN CLIENTE ---
                if evento_tabla and "selection" in evento_tabla and evento_tabla["selection"]["rows"]:
                    idx_sel = evento_tabla["selection"]["rows"][0]
                    if 0 <= idx_sel < len(df_kpi_mostrar):
                        row_cli = df_kpi_mostrar.iloc[idx_sel]
                        nom_cli = str(row_cli.get("Cliente", "Sin Nombre")).strip()
                        asesor_cli = str(row_cli.get("Vendedor", "-")).strip()
                        marca_cli = str(row_cli.get("Marca", "-")).strip()
                        chasis_cli = str(row_cli.get("Chasis", "-")).strip()
                        estado_carga_cli = str(row_cli.get("Auditoría Carga Legajo", "Sin datos"))

                        with contenedor_cliente:
                            st.divider()
                            st.markdown(f"#### 🔍 Radiografía Individual del Cliente: **{nom_cli}**")
                            st.caption(f"👤 **Asesor:** {asesor_cli} &nbsp;|&nbsp; 🏷️ **Marca:** {marca_cli} &nbsp;|&nbsp; 🔑 **Chasis:** `{chasis_cli}` &nbsp;|&nbsp; 📂 **Carga Legajo:** {estado_carga_cli}")

                            datos_cli = []
                            for c_name, c_data in sla_config.items():
                                val_d = row_cli.get(c_name)
                                if pd.notna(val_d):
                                    sla_v = c_data["sla"]
                                    f_i = fmt_fecha_corta(row_cli.get(c_data["f_ini"]))
                                    f_f = fmt_fecha_corta(row_cli.get(c_data["f_fin"]))
                                    desvio = int(round(val_d)) - sla_v
                                    estado_txt = "✅ En Término" if desvio <= 0 else f"🚨 Demorado (+{desvio} d)"
                                    color_bar = "#2ecc71" if desvio <= 0 else ("#c0392b" if c_name == "Lead Time Total" else "#e74c3c")
                                    datos_cli.append({
                                        "Tramo": c_data["label"],
                                        "Días": int(round(val_d)),
                                        "SLA": sla_v,
                                        "Color": color_bar,
                                        "F_Ini": f_i,
                                        "F_Fin": f_f,
                                        "Estado": estado_txt
                                    })

                            if datos_cli:
                                df_cli_graf = pd.DataFrame(datos_cli)
                                fig_cli = go.Figure()

                                fig_cli.add_trace(go.Bar(
                                    x=df_cli_graf["Tramo"],
                                    y=df_cli_graf["Días"],
                                    name="Días del Cliente",
                                    marker_color=df_cli_graf["Color"],
                                    text=df_cli_graf["Días"].astype(str) + " d",
                                    textposition="outside",
                                    customdata=np.stack((df_cli_graf["F_Ini"], df_cli_graf["F_Fin"], df_cli_graf["SLA"], df_cli_graf["Estado"]), axis=-1),
                                    hovertemplate=(
                                        "<b>%{x}</b><br>"
                                        "Fechas: <b>%{customdata[0]} ➔ %{customdata[1]}</b><br>"
                                        "Demora real: <b>%{y} días hábiles</b><br>"
                                        "Objetivo SLA: %{customdata[2]} días<br>"
                                        "Resultado: <b>%{customdata[3]}</b><extra></extra>"
                                    )
                                ))

                                fig_cli.add_trace(go.Scatter(
                                    x=df_cli_graf["Tramo"],
                                    y=df_cli_graf["SLA"],
                                    name="Objetivo SLA",
                                    mode="markers+lines",
                                    line=dict(color="#1e3d59", dash="dot", width=2),
                                    marker=dict(size=9, symbol="diamond", color="#1e3d59"),
                                    hovertemplate="<b>%{x}</b><br>Objetivo SLA: <b>%{y} días</b><extra></extra>"
                                ))

                                fig_cli.update_layout(
                                    title=f"Comparativa Etapa por Etapa vs. Objetivo SLA — {nom_cli} (Pasá el cursor para ver fechas exactas)",
                                    yaxis_title="Días Hábiles",
                                    xaxis_title="",
                                    height=340,
                                    template="plotly_white",
                                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                                    margin=dict(t=55, b=20, l=10, r=10)
                                )
                                st.plotly_chart(fig_cli, use_container_width=True, key=f"g_cliente_{prefijo_key}")
                            else:
                                st.info("Este cliente no tiene fechas completas para graficar sus etapas.")
                            st.divider()
            else:
                st.warning("Selecciona otro mes, tramo o limpiá los filtros del gráfico. No hay datos para mostrar en la matriz.")

        # 6. SEGMENTACIÓN EXCLUSIVA DE CANALES (SOLO TRADICIONAL Y PLAN DE AHORRO)
        if "Canal de Venta" in df_t_base.columns and not df_t_base.empty:
            canal_norm = df_t_base["Canal de Venta"].fillna("").astype(str).str.strip().str.upper()

            # Excluimos explícitamente Mayorista y Autopatentado
            mask_excluir = canal_norm.str.contains("MAYORISTA|AUTOPATENT", na=False)

            df_tradicional = df_t_base[(~mask_excluir) & (canal_norm.str.contains("TRADICIONAL|CONVENCIONAL", na=False))].copy()
            df_pda = df_t_base[(~mask_excluir) & (canal_norm.str.contains("PLAN|PDA|AHORRO", na=False))].copy()

            subtab_trad, subtab_pda = st.tabs([
                f"🚗 Canal Tradicional - T ({len(df_tradicional)} unid.)",
                f"📋 Plan de Ahorro - PDA ({len(df_pda)} unid.)"
            ])

            with subtab_trad:
                renderizar_tablero_canal(df_tradicional, SLA_CONFIG_T, prefijo_key="trad", es_tradicional=True)

            with subtab_pda:
                renderizar_tablero_canal(df_pda, SLA_CONFIG_PDA, prefijo_key="pda", es_tradicional=False)
        else:
            st.info("No hay datos disponibles o falta la columna 'Canal de Venta' para separar Tradicional y Plan de Ahorro.")

except Exception as e:
    st.error(f"❌ Ocurrió un error al cargar o procesar los datos: {e}")
