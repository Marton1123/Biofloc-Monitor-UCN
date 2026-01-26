import streamlit as st
import pandas as pd
from datetime import datetime
from typing import List, Dict

from modules.database import DatabaseConnection
from modules.config_manager import ConfigManager
from modules.sensor_registry import SensorRegistry
from modules.device_manager import DeviceManager, ConnectionStatus, HealthStatus, DeviceInfo

# --- SVGs CONSTANTS ---
ICON_LOC = '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: text-bottom; margin-right: 2px;"><path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="3"/></svg>'
ICON_ALERT = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: sub;"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><path d="M12 9v4"/><path d="M12 17h.01"/></svg>'
ICON_CLOCK = '<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>'
ICON_WIFI_OFF = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="2" x2="22" y1="2" y2="22"/><path d="M8.5 8.5A6 6 0 0 1 12 8c.7 0 1.4.11 2.06.31"/><path d="M5 5A10 10 0 0 1 12 2c1.7 0 3.33.42 4.8 1.16"/><path d="M2.5 13.5a10 10 0 0 1 .63-1.07"/><path d="M2 2l20 20"/><path d="M12 22a2 2 0 0 1-2-2"/></svg>'


def initialize_dashboard_state():
    if 'dashboard_page' not in st.session_state:
        st.session_state.dashboard_page = 0


def show_view():
    initialize_dashboard_state()
    
    # --- Toolbar ---
    c1, c2 = st.columns([6, 1])
    with c1:
        st.subheader("Vista General de Dispositivos")
    with c2:
        if st.button("Actualizar", type="primary"):
            st.rerun()
    
    # --- Data Loading ---
    db = None
    config_manager = None
    all_devices = []
    thresholds = {}
    
    try:
        db = DatabaseConnection()
        df = db.get_latest_by_device()
        
        config_manager = ConfigManager(db)
        thresholds = config_manager.get_all_configured_sensors()
        prev_states = st.session_state.get('device_health_states', {})
        device_manager = DeviceManager(thresholds, prev_states)
        
        if df is None or df.empty:
            all_devices = []
        else:
            try:
                detected = SensorRegistry.discover_sensors_from_dataframe(df)
                config_manager.sync_with_detected_sensors(detected)
                
                # Cargar Configuración Global y Específica
                global_thresholds = config_manager.get_all_configured_sensors()
                
                # Extraer Configs Específicas {dev_id: {sensor: conf}}
                all_meta = config_manager.get_device_metadata()
                dev_specifics = {k: v.get('thresholds', {}) for k, v in all_meta.items()}
                
                device_manager = DeviceManager(global_thresholds, prev_states, dev_specifics)
            except: 
                # Fallback simple
                device_manager = DeviceManager(thresholds, prev_states)
            
            all_devices = device_manager.get_all_devices_info(df)
            st.session_state['device_health_states'] = device_manager.get_health_states()

    except Exception as e:
        st.error(f"Error Database: {str(e)}")
        return
    
    # --- KPI Cards Section ---
    # Necesitamos device_manager para las métricas, si no existe lo creamos vacío
    if 'device_manager' not in locals():
        device_manager = DeviceManager({}, {})
        
    render_summary_metrics(device_manager, all_devices)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # --- Filters Section ---
    with st.container(border=True):
        st.markdown("<div style='margin-bottom: 10px; font-weight: 600; color: #64748b; font-size: 0.9rem; display: flex; align-items: center; gap: 6px;'><svg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><circle cx='11' cy='11' r='8'/><path d='m21 21-4.3-4.3'/></svg> Filtros y Búsqueda</div>", unsafe_allow_html=True)
   
        filtered_devices = render_filters(all_devices, config_manager)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # --- Device Grid ---
    if not all_devices and not filtered_devices:
         render_empty_state()
         return
         
    if not filtered_devices and all_devices:
        st.info("No se encontraron dispositivos con los filtros actuales.")
        return
        
    render_device_grid(filtered_devices, thresholds, config_manager)




def render_empty_state():
    st.markdown("""
<div style="text-align: center; padding: 4rem; background: white; border-radius: 20px; border: 1px dashed #cbd5e1; box-shadow: 0 4px 6px -2px rgba(0,0,0,0.05);">
<div style="color: #cbd5e1; margin-bottom: 1.5rem;">
<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2v20"/><path d="M2 12h20"/><path d="M12 12a5 5 0 0 1 5 5"/></svg>
</div>
<h3 style="color: #64748b; margin: 0; font-weight: 700;">Esperando Datos</h3>
<p style="color: #94a3b8; margin-top: 0.5rem;">El sistema está escuchando conexiones activas...</p>
</div>
    """, unsafe_allow_html=True)


def render_summary_metrics(manager, devices):
    with st.container():
        metrics = manager.calculate_summary_metrics(devices)
        
        total = metrics.get('total', 0)
        online_count = metrics.get('online', 0)
        offline_count = metrics.get('offline', 0)
        ok = metrics.get('ok', 0)
        warning = metrics.get('warning', 0)
        critical = metrics.get('critical', 0)
        
        # Ahora usamos 6 columnas para incluir Offline separado
        cols = st.columns(6)
        with cols[0]:
            st.markdown(build_kpi_html("Total", total, "#e0f2fe", "#0369a1"), unsafe_allow_html=True)
        with cols[1]:
            st.markdown(build_kpi_html("En Línea", online_count, "#dcfce7", "#15803d"), unsafe_allow_html=True)
        with cols[2]:
            st.markdown(build_kpi_html("Offline", offline_count, "#f1f5f9", "#475569"), unsafe_allow_html=True)
        with cols[3]:
            st.markdown(build_kpi_html("OK", ok, "#dcfce7", "#15803d"), unsafe_allow_html=True)
        with cols[4]:
            st.markdown(build_kpi_html("Alerta", warning, "#fef3c7", "#b45309"), unsafe_allow_html=True)
        with cols[5]:
            st.markdown(build_kpi_html("Crítico", critical, "#fee2e2", "#b91c1c"), unsafe_allow_html=True)


def build_kpi_html(label, value, bg_color, text_color):
    return f"""
<div style="background: {bg_color}; border-radius: 12px; padding: 0.8rem; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.05); border: 1px solid rgba(0,0,0,0.05); min-width: 0;">
<div style="color: {text_color}; font-size: 0.7rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; opacity: 0.8; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{label}</div>
<div style="color: {text_color}; font-size: 1.6rem; font-weight: 800; line-height: 1.1;">{value}</div>
</div>
"""


def render_filters(devices, config_manager=None):
    # Pre-procesar datos
    alias_map = {}
    custom_loc_map = {}
    if config_manager:
        meta = config_manager.get_device_metadata()
        for dev_id, info in meta.items():
            alias_map[dev_id] = info.get("alias", "")
            custom_loc_map[dev_id] = info.get("location", "")

    # Lógica de Ubicación Canónica (Preferir Custom > Raw)
    canonical_locations = set()
    device_canon_map = {}
    
    for d in devices:
        # Si hay custom configurada, úsala. Si no, usa la raw.
        # Esto evita que aparezca 'tanque_01' si ya fue renombrado a 'Tanque Izq'
        eff_loc = custom_loc_map.get(d.device_id)
        if not eff_loc:
             eff_loc = d.location
             
        if eff_loc:
             canonical_locations.add(eff_loc)
             device_canon_map[d.device_id] = eff_loc

    all_locations = sorted(list(canonical_locations))
    all_aliases = sorted([alias_map.get(d.device_id, d.device_id) for d in devices])
    
    with st.container(border=True):
        c1, c2, c3 = st.columns([1.5, 1, 1.5])
        
        # 1. Búsqueda Texto Libre
        with c1:
            search = st.text_input("Búsqueda Rápida", placeholder="Escribe para buscar...", label_visibility="collapsed")
            
        # 2. Selector de Criterio
        with c2:
            filter_type = st.selectbox("Criterio de Filtrado", ["-- Selección Rápida --", "Por Estado", "Por Ubicación", "Por Alias/ID"], label_visibility="collapsed")
            
        # 3. Selector Dinámico
        filtered = devices
        with c3:
            dynamic_filter = []
            
            if filter_type == "Por Estado":
                status_opts = ["Normal", "Alerta", "Crítico", "Offline"]
                dynamic_filter = st.multiselect("Estado", status_opts, placeholder="Selecciona estados...", label_visibility="collapsed")
                
                if dynamic_filter:
                    res = []
                    for d in filtered:
                        s_str = "Normal"
                        if d.connection == ConnectionStatus.OFFLINE: s_str = "Offline"
                        elif d.health == HealthStatus.CRITICAL: s_str = "Crítico"
                        elif d.health == HealthStatus.WARNING: s_str = "Alerta"
                        if s_str in dynamic_filter: res.append(d)
                    filtered = res

            elif filter_type == "Por Ubicación":
                dynamic_filter = st.multiselect("Ubicación", all_locations, placeholder="Selecciona ubicación...", label_visibility="collapsed")
                
                if dynamic_filter:
                    # Filtrar usando el mapa canónico
                    filtered = [d for d in filtered if device_canon_map.get(d.device_id) in dynamic_filter]

            elif filter_type == "Por Alias/ID":
                dynamic_filter = st.multiselect("ID o Alias", all_aliases, placeholder="Selecciona dispositivos...", label_visibility="collapsed")
                
                if dynamic_filter:
                    filtered = [d for d in filtered if alias_map.get(d.device_id, d.device_id) in dynamic_filter]
            
            else:
                 # Espacio vacío o mensaje si no hay criterio seleccionado
                 st.markdown("<div style='color:#cbd5e1; font-size:0.8rem; padding-top:10px; text-align:center;'>Seleccione un criterio</div>", unsafe_allow_html=True)


        # Aplicar Búsqueda de Texto (si existe) sobre el resultado del filtro dinámico
        if search:
            s = search.lower()
            results = []
            for d in filtered:
                in_id = s in d.device_id.lower()
                in_raw_loc = s in d.location.lower()
                in_alias = s in alias_map.get(d.device_id, "").lower()
                in_custom_loc = s in custom_loc_map.get(d.device_id, "").lower()
                if in_id or in_raw_loc or in_alias or in_custom_loc: results.append(d)
            filtered = results

        # Ordenamiento por defecto (Alfabético por Alias)
        filtered.sort(key=lambda x: alias_map.get(x.device_id, x.device_id.lower()))
            
        return filtered


def render_device_grid(devices, thresholds, config_manager=None):
    with st.container():
        PER_PAGE = 9
        total_pages = max(1, (len(devices) + PER_PAGE - 1) // PER_PAGE)
        
        if st.session_state.dashboard_page >= total_pages: st.session_state.dashboard_page = 0
        current_page = st.session_state.dashboard_page
        
        start = current_page * PER_PAGE
        end = start + PER_PAGE
        page_items = devices[start:end]
        
        cols = st.columns(3)
        for i, device in enumerate(page_items):
            with cols[i % 3]:
                # Pasamos config_manager aquí
                html_card = build_card_html(device, thresholds, config_manager)
                st.markdown(html_card, unsafe_allow_html=True)
                
        if total_pages > 1:
            st.markdown("<br>", unsafe_allow_html=True)
            c1, c2, c3 = st.columns([1, 2, 1])
            with c1:
                if st.button("←", disabled=current_page==0, key="prev"): st.session_state.dashboard_page -= 1; st.rerun()
            with c2: st.markdown(f"<div style='text-align:center; color:#94a3b8; font-size:0.8rem; margin-top:8px; font-weight:600;'>{current_page+1} / {total_pages}</div>", unsafe_allow_html=True)
            with c3:
                if st.button("→", disabled=current_page >= total_pages-1, key="next"): st.session_state.dashboard_page += 1; st.rerun()


def build_card_html(device: DeviceInfo, thresholds: Dict, config_manager: ConfigManager = None) -> str:
    """Construye el HTML completo de la tarjeta con colores vibrantes y soporte de Alias."""
    
    # --- LOGICA DE ALIAS ---
    display_name = device.device_id
    display_loc = device.location if device.location else "Desconocido"
    
    if config_manager:
        meta = config_manager.get_device_info(device.device_id)
        alias = meta.get("alias")
        custom_loc = meta.get("location")
        
        if alias and alias.strip():
            display_name = alias
        
        # Preferir ubicación custom si existe, sino la reportada, sino 'Desconocido'
        if custom_loc and custom_loc.strip():
            display_loc = custom_loc
    
    is_offline = device.connection == ConnectionStatus.OFFLINE
    
    # Colores Vibrantes
    if is_offline:
        header_grad = "linear-gradient(135deg, #64748b 0%, #475569 100%)" # Slate Deep
        status_txt = "OFFLINE"
        status_bg = "rgba(255,255,255,0.2)"
        opacity_body = "0.7"
        text_color_h = "#94a3b8"
    elif device.health == HealthStatus.CRITICAL:
        header_grad = "linear-gradient(135deg, #dc2626 0%, #b91c1c 100%)" # Red
        status_txt = "CRÍTICO"
        status_bg = "rgba(255,255,255,0.25)"
        opacity_body = "1"
        text_color_h = "#dc2626"
    elif device.health == HealthStatus.WARNING:
        header_grad = "linear-gradient(135deg, #d97706 0%, #b45309 100%)" # Amber
        status_txt = "ALERTA"
        status_bg = "rgba(255,255,255,0.25)"
        opacity_body = "1"
        text_color_h = "#d97706"
    else:
        header_grad = "linear-gradient(135deg, #059669 0%, #047857 100%)" # Emerald
        status_txt = "NORMAL"
        status_bg = "rgba(255,255,255,0.25)"
        opacity_body = "1"
        text_color_h = "#059669"

    # Sensores
    sensors_html = ""
    if not device.sensor_data:
        sensors_html = f"""<div style="text-align: center; padding: 2rem; color: #94a3b8;"><div style="opacity:0.5; margin-bottom:0.5rem;">{ICON_WIFI_OFF}</div><small style="font-weight:600;">Sin datos recientes</small></div>"""
    else:
        sensors_list = list(device.sensor_data.items())[:4]
        sensors_html = '<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; margin-bottom: 0.75rem;">'
        
        for k, v in sensors_list:
            conf = thresholds.get(k, {})
            label = conf.get("label", k.replace("_", " ").title())
            unit = conf.get("unit", "")
            
            sensors_html += f"""
<div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 0.75rem 0.5rem; text-align: center;">
<div style="font-size: 0.65rem; color: #64748b; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 2px;">{label}</div>
<div style="font-size: 1.25rem; color: #1e293b; font-weight: 800; line-height:1.2;">{v:.2f}<span style="font-size: 0.7rem; color: #94a3b8; font-weight: 600; margin-left: 2px;">{unit}</span></div>
</div>"""
        sensors_html += '</div>'

    # Alertas
    alerts_html = ""
    if device.alerts:
        alerts_html = f"""
<div style="background: #fef2f2; border-left: 3px solid #ef4444; border-radius: 6px; padding: 0.75rem; color: #b91c1c; font-size: 0.75rem; display: flex; align-items: start; gap: 8px; margin-bottom: 0.75rem;">
<div style="margin-top:2px;">{ICON_ALERT}</div>
<div style="font-weight: 600; line-height: 1.4;">{device.alerts[0]}</div>
</div>"""

    # Footer
    ts_str = "--"
    if device.last_update:
        dt = device.last_update
        if dt.tzinfo: dt = dt.replace(tzinfo=None)
        now = datetime.now()
        ts_str = dt.strftime("%H:%M:%S") if dt.date() == now.date() else dt.strftime("%d/%m %H:%M")

    # Card
    card = f"""
<div style="
background: white; border-radius: 16px; overflow: hidden; 
box-shadow: 0 10px 15px -3px rgba(0,0,0,0.05), 0 4px 6px -2px rgba(0,0,0,0.025);
border: 1px solid rgba(226, 232, 240, 0.8); 
margin-bottom: 1.5rem; transition: transform 0.2s ease;">
<div style="background: {header_grad}; padding: 1rem 1.25rem; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(0,0,0,0.05);">
<div style="color: white;">
<div style="font-weight: 800; font-size: 1.05rem; letter-spacing: -0.01em; text-shadow: 0 1px 2px rgba(0,0,0,0.1);">{display_name}</div>
<div style="font-size: 0.75rem; opacity: 0.95; display: flex; align-items: center; gap: 4px; font-weight: 500; margin-top:2px;">{ICON_LOC} {display_loc}</div>
</div>
<div style="background: {status_bg}; color: white; border-radius: 99px; padding: 4px 10px; font-size: 0.65rem; font-weight: 700; border: 1px solid rgba(255,255,255,0.3); backdrop-filter: blur(4px); letter-spacing: 0.5px;">{status_txt}</div>
</div>
<div style="padding: 1.25rem; opacity: {opacity_body};">
{sensors_html}
{alerts_html}
<div style="display: flex; justify-content: space-between; align-items: center; margin-top: 0.5rem; color: #94a3b8; font-size: 0.7rem; font-weight: 500;">
    <div title="ID Técnico: {device.device_id}">ID: {device.device_id}</div>
    <div style="display: flex; align-items: center; gap: 6px;">{ICON_CLOCK} Act: {ts_str}</div>
</div>
</div>
</div>
"""
    return card