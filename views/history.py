import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from io import BytesIO

from modules.database import DatabaseConnection
from modules.config_manager import ConfigManager

# ICONOS SVG
ICON_SEARCH = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>'
ICON_SETTINGS = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>'
ICON_INFO = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>'
ICON_DOWNLOAD = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>'

def show_view():
    # Header limpio
    c1, c2 = st.columns([5, 2])
    with c1:
        st.subheader("Base de Datos Histórica")
    with c2:
        if st.button("Actualizar Tabla", type="primary"):
            st.rerun()

    # --- 1. CARGA INICIAL ---
    try:
        db = DatabaseConnection()
        config_manager = ConfigManager(db)
        sensor_config = config_manager.get_all_configured_sensors()
    except Exception as e:
        st.error(f"Error de conexión: {str(e)}")
        return

    # --- 2. FILTROS GENERALES ---
    with st.container(border=True):
        st.markdown(f"<div style='margin-bottom: 10px; font-weight: 600; color: #475569; display:flex; align-items:center; gap:8px;'>{ICON_SEARCH} Configuración de Búsqueda</div>", unsafe_allow_html=True)
        
        fc1, fc2, fc3 = st.columns(3)
        
        with fc1:
            time_opts = {
                "Últimas 24 Horas": timedelta(hours=24),
                "Última Semana": timedelta(weeks=1),
                "Último Mes": timedelta(days=30),
                "Últimos 3 Meses": timedelta(days=90),
                "Todo (Lim. 50k)": timedelta(days=3650) 
            }
            sel_range = st.selectbox("Rango Temporal", list(time_opts.keys()), index=1)
            delta = time_opts[sel_range]
            
        end_time = datetime.now()
        start_time = end_time - delta
        
        with st.spinner("Recuperando registros..."):
            df = db.fetch_data(start_date=start_time, end_date=end_time, limit=50000)
            
        if df is None or df.empty:
            st.info("No hay registros en este periodo.")
            return

        # Preprocesamiento
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
            df = df.dropna(subset=['timestamp'])
            if not df.empty and df['timestamp'].dt.tz is not None:
                df['timestamp'] = df['timestamp'].dt.tz_localize(None)

        devices = sorted(df['device_id'].unique().tolist())
        with fc2:
            sel_devices = st.multiselect("Dispositivos", devices, default=devices)

        numeric_cols = [c for c in df.select_dtypes(include=['number']).columns 
                        if c not in ['lat', 'lon', '_id']]
        
        with fc3:
             text_search = st.text_input("Búsqueda Texto (ID/Ubicación)", placeholder="Escribe para buscar...")

    # Aplicar Filtros Básicos
    if sel_devices:
        df = df[df['device_id'].isin(sel_devices)]
    if text_search:
        s = text_search.lower()
        if 'location' not in df.columns: df['location'] = ""
        df = df[df['device_id'].astype(str).str.lower().str.contains(s) | df['location'].astype(str).str.lower().str.contains(s)]

    # --- 3. FILTROS NUMÉRICOS ---
    with st.expander("Filtros Numéricos Avanzados", expanded=False):
        c_p, c_op, c_val = st.columns([2, 1, 2])
        
        if not numeric_cols:
            st.info("Sin parámetros numéricos filtrables.")
        else:
            with c_p:
                target_param = st.selectbox("Parámetro", numeric_cols)
            with c_op:
                operator = st.selectbox("Condición", ["=", ">", "<", ">=", "<="])
            with c_val:
                target_val = st.number_input(f"Valor Referencia", value=0.0, step=0.1)
                
            apply_num_filter = st.checkbox("Activar filtro numérico", value=False)
            
            if apply_num_filter:
                if operator == "=":
                    df = df[abs(df[target_param] - target_val) < 0.01]
                elif operator == ">":
                    df = df[df[target_param] > target_val]
                elif operator == "<":
                    df = df[df[target_param] < target_val]
                elif operator == ">=":
                    df = df[df[target_param] >= target_val]
                elif operator == "<=":
                    df = df[df[target_param] <= target_val]

    if df.empty:
        st.warning("Sin resultados tras aplicar filtros.")
        return

    st.markdown("<br>", unsafe_allow_html=True)

    # --- 4. TABLA ---
    st.markdown(f"**Registros encontrados:** {len(df)}")
    
    column_config = {
        "timestamp": st.column_config.DatetimeColumn("Fecha/Hora", format="DD/MM/YYYY HH:mm:ss"),
        "device_id": "Dispositivo",
        "location": "Ubicación",
    }
    
    for col in numeric_cols:
        label = sensor_config.get(col, {}).get('label', col.title())
        unit = sensor_config.get(col, {}).get('unit', '')
        column_config[col] = st.column_config.NumberColumn(f"{label} ({unit})", format="%.2f")
            
    st.dataframe(
        df,
        width='stretch',
        column_config=column_config,
        height=500,
        hide_index=True
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # --- 5. EXPORTACIÓN (Prioridad Excel) ---
    with st.container(border=True):
        st.subheader("Exportar Datos")
        
        col_dl1, col_dl2 = st.columns(2)
        filename_base = f"biofloc_{datetime.now().strftime('%Y%m%d_%H%M')}"
        
        # EXCEL PRIMERO
        with col_dl1:
            try:
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name='Historial')
                
                st.download_button(
                    label="Descargar Excel (.xlsx)",
                    data=output.getvalue(),
                    file_name=f"{filename_base}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary",
                    width="stretch"
                )
            except:
                st.error("Error generando Excel. Contacte soporte.")

        # CSV SECUNDARIO
        with col_dl2:
            csv_data = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Descargar CSV",
                data=csv_data,
                file_name=f"{filename_base}.csv",
                mime="text/csv",
                width="stretch"
            )

    # Backup Masivo
    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("Descarga Masiva (Backup Completo)", expanded=False):
        st.markdown(f"""
        <div style="display:flex; align-items:center; gap:8px; margin-bottom:10px; color:#3b82f6; background:#eff6ff; padding:10px; border-radius:6px; font-size:0.9rem;">
            {ICON_INFO} <span>Para bases de datos grandes (>100k registros), el formato CSV es el estándar seguro y rápido. Excel puede quedarse sin memoria.</span>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("Generar Backup CSV", width="stretch"):
            with st.spinner("Generando archivo CSV masivo..."):
                try:
                    df_full = db.fetch_data(limit=100000)
                    if not df_full.empty:
                        if 'timestamp' in df_full.columns:
                            df_full['timestamp'] = pd.to_datetime(df_full['timestamp'], errors='coerce')
                        
                        # Generar CSV
                        csv_full = df_full.to_csv(index=False).encode('utf-8')
                            
                        st.download_button(
                            label="Descargar Backup (.csv)",
                            data=csv_full,
                            file_name=f"FULL_BACKUP_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                            mime="text/csv",
                            type="primary",
                            width="stretch"
                        )
                    else:
                        st.warning("La base de datos parece vacía o no retornó registros.")
                except Exception as e:
                    st.error(f"Error generando backup: {str(e)}")