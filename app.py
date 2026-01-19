import streamlit as st
import pandas as pd
import plotly.express as px
import os
import io
import time
import numpy as np
from datetime import datetime, timedelta
from dotenv import load_dotenv
from pymongo import MongoClient
import certifi

# --- CONFIGURACION DE ENTORNO ---
USAR_SIMULACION = False 

st.set_page_config(
    page_title="Sistema de Gestion Biofloc",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- ESTILOS CSS ---
st.markdown("""
    <style>
        .stApp { background-color: #F4F6F8; }
        .block-container { padding-top: 3rem; padding-bottom: 3rem; }
        [data-testid="stSidebar"] { display: none; }
        #MainMenu { visibility: hidden; }
        footer { visibility: hidden; }
        
        .login-card {
            background-color: white; padding: 40px; border-radius: 8px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }
        
        /* SEMAFOROS */
        .cabecera-verde { background-color: #27AE60; color: white; padding: 15px; border-radius: 8px 8px 0 0; text-align: center; font-weight: 700; font-size: 1.2rem; }
        .cabecera-amarillo { background-color: #F39C12; color: white; padding: 15px; border-radius: 8px 8px 0 0; text-align: center; font-weight: 700; font-size: 1.2rem; }
        .cabecera-rojo { background-color: #C0392B; color: white; padding: 15px; border-radius: 8px 8px 0 0; text-align: center; font-weight: 700; font-size: 1.2rem; }
        
        .cuerpo-tarjeta {
            background-color: white; padding: 20px; border-radius: 0 0 8px 8px;
            border: 1px solid #ddd; border-top: none;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 25px;
        }
        
        .estado-texto { text-align: center; font-weight: bold; margin-bottom: 10px; font-size: 0.9rem; text-transform: uppercase; }
        
        div.stButton > button { width: 100%; border-radius: 4px; font-weight: 600; border: 1px solid #ccc; }
        div.stButton > button:hover { border-color: #00A6ED; color: #00A6ED; }
    </style>
""", unsafe_allow_html=True)

# --- GESTION DE SESION ---
if 'pagina_actual' not in st.session_state: st.session_state['pagina_actual'] = 'tablero_principal'
if 'estanque_objetivo' not in st.session_state: st.session_state['estanque_objetivo'] = None
if 'usuario_autenticado' not in st.session_state: st.session_state['usuario_autenticado'] = False

def cambiar_ruta(ruta, param=None):
    st.session_state['pagina_actual'] = ruta
    st.session_state['estanque_objetivo'] = param
    st.rerun()

def login(u, p):
    if u == "admin" and p == "biofloc2026":
        st.session_state['usuario_autenticado'] = True
        st.rerun()
    else: st.error("Credenciales invalidas")

if not st.session_state['usuario_autenticado']:
    c1, c2, c3 = st.columns([1, 1, 1])
    with c2:
        st.markdown("<div style='height: 15vh;'></div>", unsafe_allow_html=True)
        with st.container(border=True):
            if os.path.exists("EIC.png"):
                cl1, cl2, cl3 = st.columns([1, 2, 1])
                with cl2: st.image("EIC.png", use_container_width=True)
            st.markdown("<h3 style='text-align: center; color: #444;'>Sistema Biofloc</h3>", unsafe_allow_html=True)
            with st.form("login_form"):
                u = st.text_input("Usuario")
                p = st.text_input("Contraseña", type="password")
                st.write("")
                if st.form_submit_button("Ingresar", type="primary", use_container_width=True):
                    login(u, p)
            st.markdown("<div style='text-align: center; margin-top: 15px; font-size: 0.8rem; color: #888;'>UCN Coquimbo</div>", unsafe_allow_html=True)
    st.stop()

# --- CONEXION MONGODB ADAPTADA A TU JSON ---
def conectar_bd_mongo(limite):
    load_dotenv()
    uri = os.getenv("MONGO_URI")
    if not uri:
        st.error("Falta MONGO_URI en .env")
        return pd.DataFrame()
    
    try:
        # Usamos certifi para evitar errores SSL comunes
        cliente = MongoClient(uri, tlsCAFile=certifi.where())
        col = cliente[os.getenv("MONGO_DB")][os.getenv("MONGO_COLLECTION")]
        
        cursor = col.find().sort("timestamp", -1).limit(limite)
        docs = list(cursor)
        
        if not docs: return pd.DataFrame()
        
        data = []
        for d in docs:
            # 1. LOGICA DE NOMBRE: Si tu JSON no tiene ID, asi que asignamos uno por defecto
            # Si en el futuro agregas mas sensores, deberas agregar un campo 'id' al JSON
            meta = d.get("metadata", {})
            if isinstance(meta, dict) and "microcontrolador_id" in meta:
                id_n = meta["microcontrolador_id"]
            else:
                id_n = "Biofloc Principal" # Nombre por defecto

            # 2. LOGICA DE EXTRACCION SEGURA
            def val(key):
                v = d.get(key)
                return v.get("valor") if isinstance(v, dict) else v
            
            data.append({
                "fecha_hora": d.get("timestamp"),
                "id_nodo": id_n,
                "temperatura": val("temperatura"),
                "ph": val("ph"),
                "oxigeno": val("oxigeno"),   # Sera None si no viene
                "saturacion": val("saturacion") # Sera None si no viene
            })
            
        df = pd.DataFrame(data)
        df["fecha_hora"] = pd.to_datetime(df["fecha_hora"])
        for c in ["temperatura", "ph", "oxigeno", "saturacion"]:
            if c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce')
            
        return df.sort_values("fecha_hora")
    except Exception as e:
        st.error(f"Error Conexion: {e}")
        return pd.DataFrame()

# Carga Datos
df_global = pd.DataFrame()
if USAR_SIMULACION: st.warning("Modo Simulacion")
else: df_global = conectar_bd_mongo(5000)

if df_global.empty:
    st.warning("Conexion exitosa pero sin datos recientes.")
    if st.button("Reintentar"): st.rerun()
    st.stop()

# --- REGLAS SEMAFORO ---
REGLAS = {
    'oxigeno': {'rojo_min': 4.0, 'ama_min': 5.0, 'ama_max': 12.0, 'rojo_max': 15.0, 'lbl': 'Oxigeno'},
    'temperatura': {'rojo_min': 18.0, 'ama_min': 20.0, 'ama_max': 28.0, 'rojo_max': 32.0, 'lbl': 'Temp'},
    'ph': {'rojo_min': 6.0, 'ama_min': 6.8, 'ama_max': 8.2, 'rojo_max': 9.0, 'lbl': 'pH'}
}

def diagnostico(fila):
    estado = 'verde'
    msgs = []
    
    for p, r in REGLAS.items():
        # Solo evaluamos si el dato existe
        if p in fila and pd.notna(fila[p]):
            val = fila[p]
            if val < r['rojo_min'] or val > r['rojo_max']:
                estado = 'rojo'
                msgs.append(f"{r['lbl']} CRITICO ({val:.2f})")
            elif (val < r['ama_min'] or val > r['ama_max']) and estado != 'rojo':
                estado = 'amarillo'
                msgs.append(f"{r['lbl']} ALERTA ({val:.2f})")
    
    if not msgs: msgs.append("Parametros Normales")
    return estado, msgs

# --- HEADER ---
c_log, c_txt = st.columns([1, 5], vertical_alignment="center")
with c_log:
    if os.path.exists("EIC.png"): st.image("EIC.png", width=130)
with c_txt:
    st.markdown("<h1 style='margin:0; font-size: 2.2rem; color: #2C3E50;'>Panel de Control Biofloc</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='margin:0; color: #7F8C8D;'>Ultima lectura: {df_global['fecha_hora'].max().strftime('%H:%M:%S')}</p>", unsafe_allow_html=True)
st.divider()

# --- VISTA PRINCIPAL ---
if st.session_state['pagina_actual'] == 'tablero_principal':
    col_t, col_b = st.columns([6, 1])
    with col_t: st.subheader("Estado de Cultivos")
    with col_b: 
        if st.button("Actualizar"): st.rerun()
    
    st.write("")
    nodos = df_global['id_nodo'].unique()
    cols = st.columns(3)
    
    for i, nodo in enumerate(nodos):
        df_n = df_global[df_global['id_nodo'] == nodo]
        if df_n.empty: continue
        last = df_n.iloc[-1]
        color, msgs = diagnostico(last)
        
        with cols[i%3]:
            st.markdown(f"<div class='cabecera-{color}'>{nodo}</div>", unsafe_allow_html=True)
            st.markdown("<div class='cuerpo-tarjeta'>", unsafe_allow_html=True)
            
            txt_color = "#27AE60"
            txt_est = "OPERATIVO"
            if color == 'rojo': txt_color, txt_est = "#C0392B", "CRITICO"
            elif color == 'amarillo': txt_color, txt_est = "#F39C12", "REVISION"
            
            st.markdown(f"<div class='estado-texto' style='color:{txt_color}'>{txt_est}</div>", unsafe_allow_html=True)
            for m in msgs:
                st.markdown(f"<div style='text-align:center; font-size:0.85rem; color:#555;'>{m}</div>", unsafe_allow_html=True)
            
            st.markdown("<hr style='margin:15px 0; border-top:1px solid #eee;'>", unsafe_allow_html=True)
            
            # Mostramos Temperatura y pH (que son los que se tienen actualmente)
            m1, m2 = st.columns(2)
            with m1:
                v = last.get('temperatura')
                st.metric("Temp", f"{v:.1f} C" if pd.notna(v) else "--")
            with m2:
                v = last.get('ph')
                st.metric("pH", f"{v:.2f}" if pd.notna(v) else "--")
            
            # Oxigeno opcional (si llega a aparecer en el futuro)
            if 'oxigeno' in last and pd.notna(last['oxigeno']):
                st.metric("Oxigeno", f"{last['oxigeno']:.2f} mg/L")

            st.write("")
            if st.button("Ver Detalles", key=f"b_{nodo}"):
                cambiar_ruta('detalle', nodo)
            st.markdown("</div>", unsafe_allow_html=True)

    st.write("")
    if st.button("Cerrar Sesion"):
        st.session_state['usuario_autenticado'] = False
        st.rerun()

# --- VISTA DETALLE ---
elif st.session_state['pagina_actual'] == 'detalle':
    nodo = st.session_state['estanque_objetivo']
    c_b, c_tit = st.columns([1, 6])
    with c_b:
        if st.button("Volver"): cambiar_ruta('tablero_principal')
    with c_tit: st.markdown(f"## {nodo}")
    
    df_n = df_global[df_global['id_nodo'] == nodo]
    curr = df_n.iloc[-1]
    
    st.markdown("#### Lecturas Actuales")
    # Adaptamos las columnas segun los datos que existan
    cols_kpi = st.columns(3)
    cols_kpi[0].metric("Temperatura", f"{curr.get('temperatura'):.2f} C")
    cols_kpi[1].metric("pH", f"{curr.get('ph'):.2f}")
    if pd.notna(curr.get('oxigeno')):
        cols_kpi[2].metric("Oxigeno", f"{curr.get('oxigeno'):.2f}")
    
    st.divider()
    st.markdown("#### Graficos")
    
    # Solo mostramos opciones disponibles en los datos
    opts = ['temperatura', 'ph']
    if 'oxigeno' in df_n.columns and df_n['oxigeno'].notna().any(): opts.append('oxigeno')
    
    param = st.selectbox("Parametro:", opts)
    
    # Grafico
    t_lim = df_n['fecha_hora'].max() - timedelta(hours=24)
    df_g = df_n[df_n['fecha_hora'] >= t_lim]
    
    fig = px.line(df_g, x="fecha_hora", y=param, markers=True)
    color = "#3498DB"
    if param == 'temperatura': color = "#E67E22"
    elif param == 'ph': color = "#27AE60"
    fig.update_traces(line_color=color)
    fig.update_layout(height=350, plot_bgcolor="white", xaxis_title="", yaxis_title=param)
    fig.update_yaxes(showgrid=True, gridcolor='#eee')
    st.plotly_chart(fig, use_container_width=True)
    
    with st.expander("Datos y Descarga"):
        st.dataframe(df_n.sort_values("fecha_hora", ascending=False), use_container_width=True)
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine='openpyxl') as w: df_n.to_excel(w, index=False)
        st.download_button("Descargar Excel", buf.getvalue(), f"{nodo}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")