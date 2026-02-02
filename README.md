# 🌊 Core-IoT-Monitor

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.36+-red?logo=streamlit&logoColor=white)
![MongoDB](https://img.shields.io/badge/MongoDB-Atlas-green?logo=mongodb&logoColor=white)
![ROS 2](https://img.shields.io/badge/ROS_2-Jazzy-22314E?logo=ros&logoColor=white)

**Arquitectura base modular y escalable para monitoreo IoT en acuicultura, integrando ROS 2, MongoDB y Dashboards en tiempo real**

[Demo en Vivo](#) · [Manual de Usuario](docs/MANUAL_USUARIO.md) · [Guía Multi-DB](docs/MULTI_SCHEMA_GUIDE.md) · [Reportar Bug](https://github.com/Marton1123/Core-IoT-Monitor/issues)

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
| **📊 Dashboard Multi-Fuente** | Integración transparente de múltiples bases de datos (propia + partners) con normalización automática |
| **🚦 Sistema de Alertas Inteligente** | Semaforización automática (Normal/Alerta/Crítico) con umbrales configurables por dispositivo |
| **📈 Gráficas Adaptativas** | Análisis de tendencias con filtrado de outliers y detección automática de sensores |
| **📥 Exportación Universal** | Descarga de históricos en formato Excel (.xlsx) y CSV normalizado |
| **⚙️ Gestión Multi-Esquema** | Soporte para diferentes estructuras de datos (alias/nombre, location/ubicacion) |
| **🔄 Registry-First Strategy** | Visualización de dispositivos inactivos con su último estado conocido |
| **🔌 Bajo Acoplamiento** | Separación estricta entre Lógica de Datos (Modules) y Presentación (Views) |

---

## 🏗️ Arquitectura

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Nodos ROS 2    │────▶│  MongoDB Atlas   │◀────│  Core IoT App   │
│  (Micro-ROS)    │     │  (Multi-Source)  │     │  (Streamlit)    │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                              ▲  ▲
                              │  │
                    ┌─────────┘  └─────────┐
                    │                      │
              BD Principal          BD Secundaria
           (Escritura/Lectura)    (Partner - Lectura)
```

**Stack Tecnológico:**
- **Frontend**: Streamlit 1.36+ (Fragment-based Architecture)
- **Backend**: Python 3.10+, PyMongo
- **Base de Datos**: MongoDB Atlas (Multi-Source Support)
- **Visualización**: Plotly Express
- **Procesamiento**: Pandas, NumPy

---

## 📁 Estructura del Proyecto

```
Core-IoT-Monitor/
├── Home.py                    # Punto de entrada y navegación
├── requirements.txt           # Dependencias del proyecto
├── .env                       # Variables de entorno (NO en git)
├── .env.example              # Plantilla de variables de entorno
├── .gitignore                # Archivos excluidos de git
├── README.md                 # Este archivo
├── COMMIT_SUMMARY.md         # Resumen detallado de cambios
├── .streamlit/
│   ├── config.toml           # Configuración de Streamlit
│   └── secrets.toml.example  # Plantilla de secretos para Streamlit Cloud
│
├── views/                     # Vistas de la aplicación
│   ├── __init__.py           # Inicializador del paquete
│   ├── dashboard.py          # Dashboard principal con tarjetas y filtros
│   ├── graphs.py             # Gráficas interactivas con auto-actualización
│   ├── history.py            # Historial y exportación de datos
│   └── settings.py           # Configuración de sensores y dispositivos
│
├── modules/                   # Lógica de negocio
│   ├── database.py           # Conexión multi-fuente y normalización
│   ├── device_manager.py     # Evaluación de estado de dispositivos
│   ├── config_manager.py     # Gestión de configuración
│   ├── sensor_registry.py    # Registro de sensores detectados
│   └── styles.py             # Estilos CSS globales
│
├── scripts/                   # Scripts de utilidad
│   ├── mock_data_generator.py # Generador de datos de prueba
│   ├── test_normalization.py  # Verificación de normalización multi-esquema
│   ├── debug_db.py            # Herramienta de debugging de MongoDB
│   └── export_to_excel.py     # Script de exportación a Excel
│
├── config/                    # Configuración estática
│   └── sensor_defaults.json  # Valores por defecto de sensores
│
├── assets/                    # Recursos estáticos
│   ├── logo_acui.png         # Logo acuicultura
│   └── logo_eic.png          # Logo EIC-UCN
│
└── docs/                      # Documentación
    ├── MANUAL_USUARIO.md     # Manual de usuario completo
    └── MULTI_SCHEMA_GUIDE.md # Guía de compatibilidad multi-database
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
conda create --name iot_monitor_env python=3.10 -y
conda activate iot_monitor_env
```

### 3. Instalar Dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar Variables de Entorno

Crea un archivo `.env` en la raíz del proyecto. El sistema soporta múltiples fuentes de datos de forma modular:

```ini
# =============================================================================
# BASE DE DATOS PRINCIPAL (Lectura/Escritura)
# =============================================================================
MONGO_URI=mongodb+srv://<usuario>:<password>@<cluster>.mongodb.net/?appName=AppName
MONGO_DB=BioflocDB
MONGO_COLLECTION=telemetria              # Datos de sensores (telemetría)
MONGO_DEVICES_COLLECTION=devices         # Metadatos de dispositivos

# =============================================================================
# BASE DE DATOS SECUNDARIA (Opcional - Solo Lectura o Escritura Controlada)
# =============================================================================
# Útil para integrar datos de partners, laboratorios externos o dispositivos remotos
# Soporta esquemas diferentes (alias/nombre, location/ubicacion) con normalización automática

MONGO_URI_2=mongodb+srv://<usuario2>:<password2>@<cluster2>.mongodb.net/
MONGO_DB_2=PartnerDB
MONGO_COLLECTION_2=sensor_data           # Puede tener estructura diferente
MONGO_DEVICES_COLLECTION_2=devices_data  # Campo 'nombre' en vez de 'alias', etc.
```

**Notas importantes:**
- Las bases secundarias se normalizan automáticamente para compatibilidad
- Soporta campos `alias` o `nombre` indistintamente
- Soporta campos `location` o `ubicacion` indistintamente
- Los dispositivos de todas las fuentes se unifican en un solo dashboard

### 5. Ejecutar la Aplicación

```bash
streamlit run Home.py
```

Accede a `http://localhost:8501` en tu navegador.

---

## 🧪 Generar Datos de Prueba

El proyecto incluye un generador de datos mock para testing:

```bash
python -m scripts.mock_data_generator
```

**Opciones del generador:**
- Genera lecturas para múltiples dispositivos simulados
- Incluye variaciones realistas en los parámetros
- Simula escenarios de alerta y condiciones críticas
- Los datos se insertan directamente en MongoDB

**Verificar normalización multi-esquema:**

```bash
python -m scripts.test_normalization
```

Este script muestra cómo el sistema normaliza diferentes esquemas de bases de datos.

---

## ☁️ Deploy en Streamlit Cloud

### 1. Preparar el Repositorio

Asegúrate de que tu repositorio tenga:
- `requirements.txt` actualizado
- `.gitignore` con `.env` excluido

### 2. Crear Secrets en Streamlit Cloud

En la configuración de tu app en Streamlit Cloud, añade estos secretos (formato TOML):

```toml
# =============================================================================
# BASE DE DATOS PRINCIPAL
# =============================================================================
MONGO_URI = "mongodb+srv://<usuario>:<password>@<cluster>.mongodb.net/?appName=AppName"
MONGO_DB = "BioflocDB"
MONGO_COLLECTION = "telemetria"
MONGO_DEVICES_COLLECTION = "devices"

# =============================================================================
# BASE DE DATOS SECUNDARIA (Opcional)
# =============================================================================
MONGO_URI_2 = "mongodb+srv://<usuario2>:<password2>@<cluster2>.mongodb.net/"
MONGO_DB_2 = "PartnerDB"
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

Vista principal con tarjetas de dispositivos de **todas las fuentes conectadas**:
- Estado del dispositivo (Normal/Alerta/Crítico/Offline)
- Alias personalizables (soporta `alias` o `nombre` según la BD)
- Últimas lecturas de sensores (hasta 4)
- Botón de **Actualización Parcial** (solo recarga esa tarjeta)
- Visualización de dispositivos inactivos con su último estado conocido

**Estrategia Registry-First:**
El sistema prioriza el registro de dispositivos, mostrando incluso aquellos que no han enviado datos recientemente, consultando su último estado histórico.

### 📈 Gráficas

Visualización interactiva de datos históricos con filtrado inteligente:
- Selector de dispositivo multi-fuente y rango de fechas
- Gráficas multi-sensor con Plotly
- **Filtrado automático de outliers** (valores imposibles)
- Zoom, pan y exportación de imágenes
- Detección dinámica de sensores disponibles

### 📥 Datos (Historial)

Tabla con historial completo de lecturas de **todas las fuentes**:
- Filtros por dispositivo, fecha y texto
- Búsqueda por alias, ID o ubicación
- Logs de rendimiento (docs cargados vs. válidos)
- **Exportación a Excel y CSV**
- Estadísticas por dispositivo

### ⚙️ Configuración

Gestión del sistema con UI mejorada:

**Pestaña 1: Identidad Dispositivos**
- Gestión de alias y ubicaciones
- Soporte para escritura en bases secundarias (si está habilitado)
- Visualización clara: `Alias (ID Técnico)`

**Pestaña 2: Umbrales & Alertas**
- Configuración de rangos por dispositivo y parámetro
- Tooltips explicativos en cada campo:
  - **Mínimo Crítico**: Valor de alerta crítica (riesgo de muerte)
  - **Inicio Normalidad**: Límite inferior del rango óptimo
  - **Fin Normalidad**: Límite superior del rango óptimo
  - **Máximo Crítico**: Valor de alerta crítica superior
- Visualización de zona segura en tiempo real
- Validación lógica de rangos

---

## 🔧 Características Técnicas Avanzadas

### Multi-Database Adapter Pattern

El sistema implementa un patrón de adaptador para normalizar diferentes esquemas de bases de datos:

```python
def _normalize_device_doc(self, raw_doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normaliza metadatos de DISPOSITIVOS de diferentes esquemas.
    Soporta: 'alias' o 'nombre', 'location' o 'ubicacion'
    """
    alias = raw_doc.get("alias") or raw_doc.get("nombre")
    loc = raw_doc.get("location") or raw_doc.get("ubicacion")
    # ... normalización automática
```

**📖 Documentación**: Para más detalles sobre compatibilidad de schemas, consulta [docs/MULTI_SCHEMA_GUIDE.md](docs/MULTI_SCHEMA_GUIDE.md)

### Registry-First Strategy

Prioriza el registro de dispositivos sobre los datos en vivo:

```python
def get_latest_by_device(self):
    # 1. Obtener todos los dispositivos registrados
    registered = self.get_all_registered_devices()
    
    # 2. Buscar datos recientes
    live_data = self.fetch_recent_telemetry()
    
    # 3. Para dispositivos sin datos recientes, buscar último histórico
    for device in registered:
        if device not in live_data:
            last_known = self.fetch_last_historical(device)
            # Mostrar con timestamp antiguo (offline pero visible)
```

### Outlier Filtering

Las gráficas filtran automáticamente valores imposibles:

```python
# Temperatura: 0 a 60°C (Biofloc no se congela ni hierve)
if 'temperature' in df.columns:
    df = df[(df['temperature'].isna()) | 
            ((df['temperature'] >= 0) & (df['temperature'] <= 60))]

# pH: 0 a 14 (Rango físico-químico)
if 'ph' in df.columns:
    df = df[(df['ph'].isna()) | ((df['ph'] >= 0) & (df['ph'] <= 14))]
```

### Parallel Data Loading

Carga de datos de múltiples fuentes en paralelo:

```python
with ThreadPoolExecutor(max_workers=len(db.sources)) as executor:
    futures = [executor.submit(load_source, s) for s in db.sources]
    for f in as_completed(futures):
        all_data.extend(f.result())
```

### Fragment-Based Partial Updates

Las tarjetas del dashboard usan el decorador `@fragment` de Streamlit para actualizaciones parciales:

```python
@fragment
def render_live_device_card(device, thresholds, config):
    # Solo esta tarjeta se re-renderiza al hacer clic
    if st.button("Actualizar"):
        fresh_data = db.get_latest_for_single_device(device.device_id)
```

---

## 📝 Changelog

### v3.1.0 (Febrero 2026)
- ✅ **Dashboard: Filtro Inteligente Offline**: Checkbox compacto para mostrar/ocultar dispositivos offline
- ✅ **Dashboard: Filtros Dinámicos**: Opciones filtradas según visibilidad (alias/ubicaciones solo de dispositivos activos)
- ✅ **Dashboard: Corrección Estados Stale**: Estados de salud siempre reflejan datos actuales
- ✅ **Gráficas: Auto-actualización**: Regeneración automática después de primera búsqueda
- ✅ **Gráficas: Filtrado Offline**: Dispositivos offline excluidos del multiselect
- ✅ **Gráficas: Sin Precarga**: Primera visita requiere selección manual
- ✅ **UX: Filtro "Por Estado: Offline"**: Respeta selección explícita del usuario
- ✅ **Histórico: Acceso Completo**: Permite selección de offline para descarga de datos históricos

### v3.0.0 (Febrero 2026)
- ✅ **Soporte Multi-Base de Datos**: Integración transparente de múltiples fuentes
- ✅ **Normalización Multi-Esquema**: Soporta `alias`/`nombre`, `location`/`ubicacion`
- ✅ **Registry-First Strategy**: Visualización de dispositivos inactivos
- ✅ **Filtrado de Outliers**: Eliminación automática de valores imposibles en gráficas
- ✅ **UI Mejorada en Settings**: Tooltips descriptivos y visualización con alias
- ✅ **Logs de Diagnóstico**: Trazabilidad completa de carga de datos por fuente
- ✅ **Script de Verificación**: `test_normalization.py` para debugging

### v2.0.0 (Enero 2025)
- ✅ Nuevo sistema de actualización parcial por dispositivo
- ✅ Botón de refresh integrado en tarjetas del dashboard
- ✅ Generador de datos mock para testing
- ✅ Exportación de datos a Excel/CSV
- ✅ Rediseño visual de tarjetas con iconos SVG
- ✅ Navegación mejorada con iconos Material
- ✅ Soporte para Streamlit Cloud

### v1.0.0 (Enero 2026)
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

## 📄 Licencia

Este proyecto es de código abierto y está disponible bajo la licencia MIT.

---

<div align="center">

**Desarrollado con 🦐 por [Marton1123](https://github.com/Marton1123)**

**Escuela de Ingeniería Coquimbo - Universidad Católica del Norte (UCN)**

</div>