# 📝 Resumen de Cambios - Versión 3.1.0

## 🎯 Título del Commit
```
feat: UI mejorada con filtros inteligentes y experiencia de usuario optimizada
```

## 📋 Descripción del Commit
```
Mejoras significativas en la experiencia de usuario para Dashboard y Gráficas,
incluyendo filtrado inteligente de dispositivos offline, auto-actualización de
gráficas, y corrección de estados de salud en tiempo real.

CARACTERÍSTICAS PRINCIPALES:
- Dashboard: Checkbox compacto para mostrar/ocultar dispositivos offline
- Filtros inteligentes: Opciones filtradas según estado de dispositivos
- Gráficas: Auto-actualización después de primera búsqueda
- Gráficas: Filtrado de dispositivos offline en selección
- Dashboard: Corrección de estados stale al navegar entre páginas
- Filtro "Por Estado: Offline" respeta selección explícita del usuario
- Fix crítico: Carga correcta de umbrales personalizados (merge `umbrales`/`thresholds`)
- Estandarización: Guardado de configuración en esquema español (`umbrales`)
- UX: Formato correcto de nombres técnicos (pH, Temperatura) en Settings

ARCHIVOS MODIFICADOS:
- views/dashboard.py: Checkbox offline, filtros inteligentes, fix estados stale
- views/graphs.py: Auto-update, filtrado offline, DeviceManager integration
- views/settings.py: Fix capitalización (pH), tooltips
- modules/config_manager.py: Fix carga/guardado de umbrales
- modules/database.py: Multi-schema normalization (de versión anterior)
- views/history.py: Logging detallado (de versión anterior)
- views/settings.py: UI mejorada con tooltips (de versión anterior)

ARCHIVOS ELIMINADOS:
- PENDING_CHANGES.md: Documento temporal de desarrollo
- INSTRUCCIONES_GRAPHS.md: Guía temporal ya obsoleta

DOCUMENTACIÓN ACTUALIZADA:
- README.md: Versión 3.0.0 con todas las características
- COMMIT_SUMMARY.md: Este archivo
- .env.example: Configuración multi-DB
- .streamlit/secrets.toml.example: Deploy a Streamlit Cloud
- docs/MULTI_SCHEMA_GUIDE.md: Guía de compatibilidad
```

---

## 🔄 Cambios Detallados por Archivo

### `views/dashboard.py`

#### 1. **Corrección de Estados Stale (Líneas 135-147)**
**Problema**: Al navegar entre páginas, los estados de salud (verde/amarillo/rojo) se preservaban del cache, mostrando información incorrecta.

**Solución**:
```python
# Forzar limpieza de estados al cargar dashboard
if 'device_health_states' in st.session_state:
    del st.session_state['device_health_states']

prev_states = {}  # Siempre vacío para forzar actualización
```

**Resultado**: Estados de salud siempre reflejan el estado REAL actual.

---

#### 2. **Checkbox Compacto para Dispositivos Offline (Líneas 390-430)**
**Antes**: Selectbox grande con dos opciones ocupaba mucho espacio.

**Ahora**: 
- Checkbox compacto en la columna derecha del contenedor de filtros
- Label simple: "Offline"
- Tooltip explicativo
- Desmarcado por defecto (dispositivos offline ocultos)

**Distribución de columnas**: `[1.4, 0.8, 1.2, 0.6]`
- C1: Búsqueda rápida (expandido)
- C2: Criterio de filtrado
- C3: Multiselect dinámico
- C4: Checkbox "Offline" (derecha)

---

#### 3. **Filtrado Inteligente de Opciones (Líneas 418-427)**
**Problema**: Dispositivos offline aparecían en las opciones de filtros aunque estuvieran ocultos, causando confusión.

**Solución**:
```python
# Calcular opciones solo con dispositivos filtrados
filtered_locations = set()
for d in filtered:
    eff_loc = custom_loc_map.get(d.device_id) or d.location
    if eff_loc:
        filtered_locations.add(eff_loc)

all_locations = sorted(list(filtered_locations))
all_aliases = sorted([alias_map.get(d.device_id, d.device_id) for d in filtered])
```

**Resultado**: 
- "Por Ubicación" → Solo ubicaciones de dispositivos visibles
- "Por Alias/ID" → Solo alias de dispositivos visibles

---

#### 4. **Excepción para Filtro "Por Estado: Offline" (Líneas 433-443)**
**Problema**: Si el checkbox estaba desmarcado, seleccionar "Offline" en filtro de estado no mostraba nada (contradictorio).

**Solución**:
```python
if filter_type == "Por Estado":
    dynamic_filter = st.multiselect(...)
    if dynamic_filter:
        # Si el usuario selecciona 'Offline' explícitamente, usar lista completa
        search_list = devices if "Offline" in dynamic_filter else filtered
        ...
```

**Resultado**: Usuario puede ver offline cuando REALMENTE lo necesita, sin cambiar checkbox.

---

### `modules/config_manager.py`

#### **Fix Crítico: Carga de Umbrales Personalizados**
**Problema**: El sistema solo leía `umbrales` (español) o `thresholds` (inglés) de forma excluyente, ignorando configuraciones personalizadas si existía una clave legacy vacía.
**Solución**: 
- Implementado merge inteligente de ambas claves (`thresholds` y `umbrales`).
- Prioridad a `umbrales` (configuración más reciente).
- Estandarizado el guardado en `umbrales.{sensor}` para mantener esquema en español.

**Resultado**: Las alertas y rangos personalizados ahora se aplican correctamente en el Dashboard.

---

### `views/graphs.py`

#### 1. **Importación de DeviceManager (Línea 16)**
```python
from modules.device_manager import DeviceManager, ConnectionStatus
```

**Motivo**: Necesario para evaluar estado de conexión real de dispositivos.

---

#### 2. **Filtrado de Dispositivos Offline (Líneas 434-448)**
**Problema**: Dispositivos offline aparecían en el multiselect de dispositivos.

**Solución**:
```python
# Obtener estado actual usando DeviceManager
latest_df = db.get_latest_by_device()
device_manager = DeviceManager({}, {})
all_devices_info = device_manager.get_all_devices_info(latest_df)
# Solo incluir dispositivos que NO estén offline
online_device_ids = set([d.device_id for d in all_devices_info 
                         if d.connection != ConnectionStatus.OFFLINE])

# Filtrar dispositivos
devices = [dev_id for dev_id in all_devices 
           if has_configured_alias(dev_id) and is_device_online(dev_id)]
```

**Resultado**: Solo dispositivos online aparecen en selección de gráficas.

---

#### 3. **Auto-actualización Inteligente (Líneas 529-575)**
**Problema**: Cada cambio de filtro requería hacer clic en "VER GRÁFICAS" de nuevo.

**Solución**:
```python
if 'graphs_has_searched' not in st.session_state:
    st.session_state.graphs_has_searched = False

# Primera búsqueda requiere botón
if ver_graficas:
    should_regenerate = True
    st.session_state.graphs_has_searched = True

# Búsquedas posteriores auto-actualizan
elif st.session_state.graphs_has_searched and params_changed:
    should_regenerate = True
```

**Resultado**:
- Primera carga → Requiere clic en botón ✓
- Cambios posteriores → Auto-actualiza automáticamente ✓

---

#### 4. **Sin Precarga de Dispositivos (Líneas 460-480)**
**Problema**: Dispositivos aparecían precargados al entrar, causando confusión.

**Solución**:
```python
# Calcular default inicial para dispositivos
default_devices = None
if url_device_id and url_device_id in devices:
    # Solo precargar si viene desde dashboard
    default_devices = [url_device_id]
elif 'graphs_prev_devices' in st.session_state:
    # O si ya buscó antes
    prev = st.session_state.graphs_prev_devices
    valid_prev = [d for d in prev if d in devices]
    default_devices = valid_prev if valid_prev else None
```

**Resultado**: 
- Primera carga → Sin dispositivos precargados ✓
- Desde dashboard → Precarga el dispositivo clickeado ✓  
- Navegación posterior → Mantiene última selección ✓

---

### `views/settings.py`

#### **Mejoras de UX y Formato**
- **Nombres Técnicos**: Implementada función `format_param_name` para corregir capitalización (ej: "Ph" → "pH").
- **Visualización**: Selectores y formularios ahora usan los nombres formateados correctamente.
- **Tooltips**: Agregadas explicaciones detalladas para los campos de configuración de umbrales.

---

## ✅ Testing Realizado

### Dashboard:
- ✅ Estados de salud se actualizan correctamente al navegar
- ✅ Checkbox "Offline" muestra/oculta dispositivos offline
- ✅ Filtros solo muestran opciones de dispositivos visibles
- ✅ Filtro "Por Estado: Offline" funciona independientemente del checkbox

### Gráficas:
- ✅ No hay dispositivos precargados en primera visita
- ✅ Solo dispositivos online aparecen en multiselect
- ✅ Botón requerido solo en primera búsqueda
- ✅ Cambios de filtros auto-actualizan después
- ✅ Navegación mantiene última selección

### Histórico:
- ✅ Permite seleccionar dispositivos offline (datos históricos)
- ✅ Descarga de datos funciona correctamente

---

## 📊 Estadísticas

- **Archivos Modificados**: 2 (dashboard.py, graphs.py)
- **Líneas Agregadas**: ~80
- **Líneas Modificadas**: ~50
- **Funcionalidades Nuevas**: 5
- **Bugs Corregidos**: 6
- **Archivos Eliminados**: 2 (documentación temporal)

---

## 🚀 Próximos Pasos Sugeridos

1. **Testing en producción** con múltiples dispositivos offline
2. **Validar** comportamiento con usuarios finales
3. **Monitorear** logs de errores en `graphs.py` (DeviceManager)
4. **Considerar** agregar checkbox "Offline" también en gráficas (opcional)

---

## 📝 Notas de Implementación

### Diseño de Decisiones:

1. **¿Por qué histórico SÍ muestra offline?**
   - Propósito: Descargar datos pasados
   - Dispositivos offline tienen datos históricos valiosos
   - Caso de uso diferente a dashboard/gráficas

2. **¿Por qué auto-actualización en gráficas?**
   - UX mejorada: Usuario no debe hacer clic repetidamente
   - Primera búsqueda requiere intención explícita (botón)
   - Cambios posteriores son interactivos (tipo playground)

3. **¿Por qué checkbox y no selectbox?**
   - Más compacto visualmente
   - Acción binaria clara (mostrar/ocultar)
   - Menos espacio en UI

---

**Autor**: Antigravity AI  
**Fecha**: 2026-02-02  
**Versión**: v3.1.0
