# Biofloc Monitor UCN

## Descripción del Proyecto

Sistema de monitoreo y control de calidad de agua para acuicultura Biofloc. Esta plataforma permite la supervisión remota de parámetros fisicoquímicos críticos (pH, oxígeno disuelto, temperatura, entre otros) mediante una interfaz web centralizada.

El sistema está diseñado para operar en entornos de red local o nube, procesando datos de telemetría provenientes de múltiples nodos sensores IoT almacenados en una base de datos NoSQL.

## Funcionalidades Principales

*   **Monitoreo en Tiempo Real**: Visualización del estado operativo de cada unidad de cultivo (En línea, Desconectado, Alerta, Crítico).
*   **Gestión de Alarmas**: Sistema de semaforización automática basado en rangos biológicos configurables por el usuario.
*   **Análisis Histórico**: Herramientas de graficación interactiva para el análisis de tendencias y exportación de datos (Excel/CSV).
*   **Configuración Dinámica**: Interfaz para el ajuste de umbrales de sensores y gestión de metadatos de dispositivos sin interrupción del servicio.
*   **Resiliencia de Conexión**: Arquitectura tolerante a fallos de red con reconexión automática a base de datos.

## Arquitectura Tecnológica

*   **Interfaz de Usuario**: Streamlit (Python 3.10+)
*   **Base de Datos**: MongoDB Atlas (MongoDB 5.0+)
*   **Procesamiento de Datos**: Pandas, NumPy
*   **Visualización**: Plotly Express, Altair

## Instalación y Despliegue

Instrucciones para desplegar el entorno de desarrollo en un sistema Windows utilizando Anaconda.

### 1. Configuración del Entorno

Abra **Anaconda Prompt** y navegue al directorio raíz del proyecto:

```cmd
cd Biofloc-Monitor-UCN
```
*(Asegúrese de estar en la carpeta correcta antes de continuar)*

Cree y active el entorno virtual dedicado:

```cmd
conda create --name biofloc_env python=3.10 -y
conda activate biofloc_env
```

### 2. Instalación de Dependencias

Ejecute el siguiente comando para instalar las librerías requeridas:

```cmd
pip install -r requirements.txt
```

### 3. Configuración de Credenciales

El sistema requiere acceso a la base de datos MongoDB. Cree un archivo llamado `.env` en la raíz del proyecto y configure las variables de entorno:

```ini
MONGO_URI=mongodb+srv://<usuario>:<password>@<cluster>.mongodb.net/
MONGO_DB=BioflocDB
MONGO_COLLECTION=SensorReadings
```

### 4. Ejecución del Sistema

Inicie la aplicación mediante el comando:

```cmd
streamlit run Home.py
```

La interfaz web estará disponible en `http://localhost:8501`.

## Estructura del Repositorio

*   **Home.py**: Punto de entrada de la aplicación.
*   **views/**: Módulos de interfaz gráfica (Dashboard, Gráficos, Historial, Configuración).
*   **modules/**: Núcleo lógico (Conexión a BD, Evaluación de Estado, Gestión de Configuración).
*   **config/**: Archivos de configuración estática y valores por defecto.
*   **docs/**: Documentación extendida y manuales de usuario.

---
**Desarrollado por**: [Marton1123](https://github.com/Marton1123)  
**Escuela de Ingeniería Coquimbo - Universidad Católica del Norte (UCN)**