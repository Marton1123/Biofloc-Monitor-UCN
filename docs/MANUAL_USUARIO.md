# Manual de Operación - Biofloc Monitor UCN

Este documento describe el funcionamiento y operación de la plataforma de monitoreo Biofloc.

## 1. Panel de Control Operativo (Dashboard)

El Dashboard es la interfaz principal para la supervisión en tiempo real de las unidades de cultivo.

### Estados de Operación
Cada tarjeta de dispositivo presenta un indicador de color que refleja el estado consolidado de la unidad:

*   **Normal (Verde)**: Todos los parámetros de calidad de agua se encuentran dentro de los rangos óptimos configurados.
*   **Alerta (Amarillo)**: Uno o más parámetros se han desviado del rango óptimo, pero se mantienen dentro de límites seguros de operación. Se recomienda inspección.
*   **Crítico (Rojo)**: Se han detectado valores fuera de los límites de seguridad biológica (riesgo de mortalidad), o el dispositivo ha reportado fallos internos. Requiere acción inmediata.
*   **Offline/Desconectado (Gris)**: El nodo sensor ha dejado de transmitir datos por un periodo superior al umbral de desconexión (por defecto 5 minutos).

### Filtrado y Búsqueda
La barra de herramientas superior permite filtrar los dispositivos visibles por:
*   **Estado**: Mostrar solo unidades en Alerta o Críticas.
*   **Ubicación**: Filtrar por sector (ej: Laboratorio, Invernadero).
*   **Texto**: Búsqueda libre por ID técnico o alias.

## 2. Análisis de Tendencias (Gráficas)

Módulo para la evaluación visual del comportamiento de parámetros en el tiempo.

*   **Rango Temporal**: Permite seleccionar ventanas de observación desde la última hora hasta la última semana o mes.
*   **Comparativa**: Selección múltiple de dispositivos para superponer curvas y comparar comportamientos entre diferentes tanques.
*   **Estadística Descriptiva**: Tabla resumen con valores Mínimo, Máximo, Promedio y Mediana para el periodo y dispositivos seleccionados.

## 3. Gestión de Datos Históricos

Acceso al registro completo de mediciones almacenadas en la base de datos.

*   **Consulta Selectiva**: Filtrado de registros por rango de fechas y dispositivos específicos.
*   **Exportación de Datos**:
    *   **Formato Excel (.xlsx)**: Recomendado para reportes y análisis de conjuntos de datos pequeños a medianos (< 50,000 registros).
    *   **Formato CSV**: Recomendado para copias de seguridad masivas y exportación de grandes volúmenes de datos para procesamiento externo.

## 4. Configuración del Sistema

Panel administrativo para la gestión de metadatos y parámetros de control.

### Gestión de Identidad
Permite asignar nombres amigables (Alias) y ubicaciones físicas a los IDs técnicos de los microcontroladores.
*   **ID Técnico**: Identificador único inmutable del hardware (MAC o Serial).
*   **Alias**: Nombre operativo visible en el Dashboard (ej: Tanque A-01).

### Configuración de Umbrales (Calidad de Agua)
Permite establecer los rangos de operación para cada parámetro (pH, Temperatura, OD, etc.) de forma individual por dispositivo.

El sistema utiliza un modelo de cuatro puntos para definir los estados:
1.  **Mínimo Crítico**: Límite inferior de seguridad biológica.
2.  **Mínimo Óptimo**: Inicio del rango ideal de producción.
3.  **Máximo Óptimo**: Fin del rango ideal de producción.
4.  **Máximo Crítico**: Límite superior de seguridad biológica.

**Interpretación Automática**:
*   Valores entre *Mínimo Óptimo* y *Máximo Óptimo* = **Estado Normal**.
*   Valores entre *Límites Críticos* y *Límites Óptimos* = **Estado de Alerta**.
*   Valores fuera de los *Límites Críticos* = **Estado Crítico**.

---
**Desarrollado por**: [Marton1123](https://github.com/Marton1123)  
**Escuela de Ingeniería Coquimbo - Universidad Católica del Norte (UCN)**
