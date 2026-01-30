# 🌊 Core-IoT-Monitor

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.36+-red?logo=streamlit&logoColor=white)
![MongoDB](https://img.shields.io/badge/MongoDB-Atlas-green?logo=mongodb&logoColor=white)
![ROS 2](https://img.shields.io/badge/ROS_2-Jazzy-22314E?logo=ros&logoColor=white)

**Arquitectura base modular y escalable para monitoreo IoT en acuicultura, integrando ROS 2, MongoDB y Dashboards en tiempo real**

[Demo en Vivo](#) · [Documentación](docs/MANUAL_USUARIO.md) · [Reportar Bug](https://github.com/Marton1123/Core-IoT-Monitor/issues)

</div>

---

## 📋 Descripción

**Core-IoT-Monitor** es una plataforma base de código abierto diseñada para acelerar el desarrollo de soluciones de monitoreo en la industria de la acuicultura. Proporciona una arquitectura robusta y desacoplada para la supervisión remota de parámetros fisicoquímicos críticos (pH, oxígeno disuelto, temperatura, etc.) en diversos entornos de cultivo (Biofloc, RAS, estanques tradicionales).

El sistema actúa como el núcleo de visualización y gestión, procesando datos de telemetría provenientes de nodos IoT (basados en ROS 2 / Micro-ROS) almacenados en MongoDB Atlas.

### 🚀 Uso como Plantilla (Quick Start)

Este repositorio está diseñado para ser **bifurcado (Forked)** y utilizado como punto de partida para tu propio proyecto de monitoreo.

1. **Fork & Rename**: Crea un fork de este repositorio y renómbralo a tu proyecto (ej. `Salmon-Monitor-X`).
2. **Personaliza**: Edita `modules/styles.py` para adaptar la paleta de colores a tu marca.
3. **Configura**: Ajusta `config/sensor_defaults.json` con los sensores específicos de tu sistema.
4. **Despliega**: Conecta tu propia base de datos MongoDB y despliega en Streamlit Cloud o Docker.

---

### ✨ Funcionalidades Principales

| Función | Descripción |
|---------|-------------|
| **📊 Dashboard Modular** | Interfaz unificada capaz de renderizar dinámicamente cualquier sensor detectado en la DB |
| **🚦 Sistema de Alertas** | Semaforización automática (Normal/Alerta/Crítico) y lógica de alertas extensible |
| **📈 Gráficas Interactivas** | Análisis de tendencias con Plotly, independiente del tipo de sensor monitoreado |
| **📥 Exportación Universal** | Descarga de históricos en formato Excel (.xlsx) y CSV normalizado |
| **⚙️ Configuración Dinámica** | Ajuste de umbrales y metadatos de dispositivos en tiempo de ejecución (Hot-Reload) |
| **Bajo Acoplamiento** | Separación estricta entre Lógica de Datos (Modules) y Presentación (Views) |

---

## 🏗️ Arquitectura

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Nodos ROS 2    │────▶│  MongoDB Atlas   │◀────│  Core IoT App   │
│  (Micro-ROS)    │     │  (Data Lake)     │     │  (Streamlit)    │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

**Stack Tecnológico:**
- **Frontend**: Streamlit 1.36+ (Components-based Architecture)
- **Backend**: Python 3.10+, PyMongo
- **Base de Datos**: MongoDB Atlas (Schema-less)
- **Visualización**: Plotly Express
- **Procesamiento**: Pandas, NumPy

---

## 📁 Estructura del Proyecto

```
Core-IoT-Monitor/
├── Home.py                    # Punto de entrada y navegación
├── requirements.txt           # Dependencias del proyecto
├── .env                       # Variables de entorno (NO en git)
├── .streamlit/
│   └── secrets.toml          # Secretos para Streamlit Cloud
│
├── views/                     # Vistas de la aplicación
│   ├── dashboard.py          # Dashboard principal con tarjetas
│   ├── graphs.py             # Gráficas interactivas
│   ├── history.py            # Historial y exportación de datos
│   └── settings.py           # Configuración de sensores y dispositivos
│
├── modules/                   # Lógica de negocio
│   ├── database.py           # Conexión y queries a MongoDB
│   ├── device_manager.py     # Evaluación de estado de dispositivos
│   ├── config_manager.py     # Gestión de configuración
│   ├── sensor_registry.py    # Registro de sensores detectados
│   └── styles.py             # Estilos CSS globales
│
├── scripts/                   # Scripts de utilidad
│   └── mock_data_generator.py # Generador de datos de prueba
│
├── config/                    # Configuración estática
│   └── sensor_defaults.json  # Valores por defecto de sensores
│
├── assets/                    # Recursos estáticos
│   ├── logo_acui.png
│   └── logo_eic.png
│
└── docs/                      # Documentación
    └── MANUAL_USUARIO.md
```

---

## 🚀 Instalación Local

### Prerrequisitos

- [Anaconda](https://www.anaconda.com/download) o Python 3.10+
- Cuenta en [MongoDB Atlas](https://www.mongodb.com/cloud/atlas) (gratis)

### 1. Clonar el Repositorio

```bash
git clone https://github.com/Marton1123/Core-IoT-Monitor.git
cd Core-IoT-Monitor
```

### 2. Crear Entorno Virtual (Anaconda)

```bash
conda create --name biofloc_env python=3.10 -y
conda activate biofloc_env
```

### 3. Instalar Dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar Variables de Entorno

Crea un archivo `.env` en la raíz del proyecto. El sistema soporta múltiples fuentes de datos de forma modular:

```ini
# --- BD PRINCIPAL (Escritura/Lectura) ---
MONGO_URI=mongodb+srv://<usuario>:<password>@<cluster>.mongodb.net/
MONGO_DB=BioflocDB
MONGO_COLLECTION=telemetria           # Colección de datos de sensores
MONGO_DEVICES_COLLECTION=devices      # Colección de metadatos de dispositivos

# --- BD SECUNDARIA (Opcional - Solo Lectura) ---
# Útil para integrar datos de partners o sensores externos
MONGO_URI_2=...
MONGO_DB_2=...
MONGO_COLLECTION_2=...
MONGO_DEVICES_COLLECTION_2=...
```

### 5. Ejecutar la Aplicación

```bash
streamlit run Home.py
```

Accede a `http://localhost:8501` en tu navegador.

---

## 🧪 Generar Datos de Prueba

El proyecto incluye un generador de datos mock para testing:

```bash
python scripts/mock_data_generator.py
```

**Opciones del generador:**
- Genera lecturas para múltiples dispositivos simulados
- Incluye variaciones realistas en los parámetros
- Simula escenarios de alerta y condiciones críticas
- Los datos se insertan directamente en MongoDB

---

## ☁️ Deploy en Streamlit Cloud

### 1. Preparar el Repositorio

Asegúrate de que tu repositorio tenga:
- `requirements.txt` actualizado
- `.gitignore` con `.env` excluido

### 2. Crear Secrets en Streamlit Cloud

En la configuración de tu app en Streamlit Cloud, añade estos secretos (formato TOML):

```toml
# BD Principal
MONGO_URI = "mongodb+srv://..."
MONGO_DB = "BioflocDB"
MONGO_COLLECTION = "telemetria"
MONGO_DEVICES_COLLECTION = "devices"

# BD Secundaria (Opcional)
MONGO_URI_2 = "mongodb+srv://..."
MONGO_DB_2 = "ExternalDB"
MONGO_COLLECTION_2 = "sensor_data"
MONGO_DEVICES_COLLECTION_2 = "devices_data"
```

### 3. Desplegar

1. Ve a [share.streamlit.io](https://share.streamlit.io)
2. Conecta tu repositorio de GitHub
3. Selecciona `Home.py` como archivo principal
4. ¡Deploy!

---

## 📊 Vistas de la Aplicación

### 🏠 Dashboard (Inicio)

Vista principal con tarjetas de dispositivos. Cada tarjeta muestra:
- Estado del dispositivo (Normal/Alerta/Crítico/Offline)
- Últimas lecturas de sensores (hasta 4)
- Botón de **Actualización Parcial** (solo recarga esa tarjeta)
- Acceso directo a gráficas del dispositivo

### 📈 Gráficas

Visualización interactiva de datos históricos:
- Selector de dispositivo y rango de fechas
- Gráficas multi-sensor con Plotly
- Zoom, pan y exportación de imágenes

### 📥 Datos (Historial)

Tabla con historial completo de lecturas:
- Filtros por dispositivo, fecha y sensor
- Paginación de resultados
- **Exportación a Excel y CSV**

### ⚙️ Configuración

Gestión del sistema:
- Umbrales de alerta por sensor (mínimo/máximo)
- Metadatos de dispositivos (alias, ubicación)
- Configuración persistente en MongoDB

---

## 🔧 Características Técnicas

### Actualización Parcial con @fragment

Las tarjetas del dashboard usan el decorador `@fragment` de Streamlit para actualizaciones parciales:

```python
@fragment
def render_live_device_card(device, thresholds, config):
    # Solo esta tarjeta se re-renderiza al hacer clic
    if st.button("Actualizar"):
        # Consulta solo este dispositivo
        fresh_data = db.get_latest_for_single_device(device.device_id)
```

### Conexión Resiliente a MongoDB

El sistema implementa reconexión automática con reintentos:

```python
def get_latest_by_device(self, max_retries=3):
    for attempt in range(max_retries):
        try:
            # Query a MongoDB
        except Exception as e:
            time.sleep(0.5 * (attempt + 1))
```

### Sistema de Caché en Session State

Los datos se cachean en `st.session_state` para evitar consultas innecesarias:

```python
if f"live_data_{device_id}" not in st.session_state:
    st.session_state[f"live_data_{device_id}"] = fetch_from_db()
```

---

## 📝 Changelog

### v2.0.0 (Enero 2025)
- ✅ Nuevo sistema de actualización parcial por dispositivo
- ✅ Botón de refresh integrado en tarjetas del dashboard
- ✅ Generador de datos mock para testing
- ✅ Exportación de datos a Excel/CSV
- ✅ Rediseño visual de tarjetas con iconos SVG
- ✅ Navegación mejorada con iconos Material
- ✅ Soporte para Streamlit Cloud

### v1.0.0 (Diciembre 2024)
- Dashboard inicial con tarjetas de dispositivos
- Gráficas interactivas con Plotly
- Configuración de umbrales
- Conexión a MongoDB Atlas

---

## 🤝 Contribuir

1. Fork el proyecto
2. Crea una rama (`git checkout -b feature/nueva-funcionalidad`)
3. Commit tus cambios (`git commit -m 'Añadir nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Abre un Pull Request

---

<div align="center">

**Desarrollado con 🦐 por [Marton1123](https://github.com/Marton1123)**

**Escuela de Ingeniería Coquimbo - Universidad Católica del Norte (UCN)**

</div>