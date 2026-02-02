# 🔄 Guía de Compatibilidad Multi-Schema

Esta guía explica cómo **Core-IoT-Monitor** maneja automáticamente diferentes estructuras de bases de datos, permitiendo la integración transparente de múltiples fuentes.

---

## 📌 Conceptos Clave

El sistema implementa un **patrón de adaptador** que normaliza diferentes esquemas de datos en tiempo de ejecución, permitiendo:

- ✅ Integrar datos de partners/colaboradores sin modificar su BD
- ✅ Migrar sistemas heredados sin reescribir toda la base de datos
- ✅ Fusionar múltiples proyectos IoT en un único dashboard
- ✅ Mantener nombres de campos legibles en diferentes idiomas

---

## 🔀 Estructuras Soportadas

### 1. Colección de Telemetría (Datos de Sensores)

El sistema acepta **dos estructuras principales**:

#### Estructura A: Nested Sensors
```json
{
  "_id": "507f1f77bcf86cd799439011",
  "device_id": "esp32_001",
  "timestamp": "2026-02-02T10:30:00",
  "location": "Tanque 1",
  "sensors": {
    "temperature": 24.5,
    "ph": 7.2,
    "oxygen": 6.8
  }
}
```

#### Estructura B: Flat Data (con normalización)
```json
{
  "_id": "507f1f77bcf86cd799439012",
  "dispositivo_id": "esp32_002",
  "timestamp": "2026-02-02T10:30:00",
  "ubicacion": "Biorreactor 2",
  "datos": {
    "temperatura": {"value": 23.1},
    "ph": {"value": 7.5},
    "oxigeno": {"value": 7.2}
  }
}
```

**Normalización Automática:**
- `device_id` o `dispositivo_id` → `device_id`
- `sensors` o `datos` → `sensors`
- `location` o `ubicacion` → `location`
- `temperature`, `temperatura`, `temp` → `temperature`
- `oxygen`, `oxigeno`, `od`, `do` → `oxygen`

---

### 2. Colección de Dispositivos (Metadatos)

El sistema soporta **dos esquemas** para metadatos de dispositivos:

#### Schema Propio (Recomendado)
```json
{
  "_id": "biofloc_esp32_c8e0",
  "alias": "Esp-32 MicroAlgas Martin",
  "location": "Biorreactor Izq",
  "estado": "activo",
  "auto_registrado": false,
  "firmware_version": "v1.2.3",
  "intervalo_lectura_seg": 4,
  "sensores_habilitados": ["ph", "temperature"],
  "umbrales": {
    "ph": {
      "min_value": 6.5,
      "max_value": 8.0,
      "critical_min": 6.0,
      "critical_max": 9.0
    }
  },
  "unidades": {
    "temperature": "°C",
    "ph": "pH"
  },
  "conexion": {
    "primera": "2026-01-21T15:48:38",
    "ultima": "2026-02-02T12:00:00",
    "total_lecturas": 159278
  }
}
```

#### Schema Partner (Alternativo)
```json
{
  "_id": "34865D46A848",
  "nombre": "ESP de prueba con datos fake",
  "ubicacion": "Cuarto piso - escuela de ingeniería",
  "estado": "pendiente",
  "auto_registrado": true,
  "firmware_version": "desconocido",
  "intervalo_lectura_seg": 60,
  "sensores_habilitados": ["ph", "temperatura"],
  "calibracion": {
    "ph_offset": 0,
    "temp_offset": 0
  },
  "umbrales": {
    "ph_min": 6.0,
    "ph_max": 8.5,
    "temp_max": 30
  },
  "unidades": {
    "temperatura": "°C",
    "ph": "pH"
  },
  "conexion": {
    "primera": "2026-01-20T20:41:04",
    "ultima": "2026-01-26T18:38:45",
    "total_lecturas": 126
  }
}
```

**Normalización Automática:**
- `alias` o `nombre` → `alias`
- `location` o `ubicacion` → `location`
- Umbrales planos (`ph_min`, `ph_max`) → estructura anidada (`ph: {min_value, max_value}`)

---

## 🛠️ Cómo Funciona la Normalización

### 1. En `modules/database.py`

```python
def _normalize_device_doc(self, raw_doc: Dict[str, Any]) -> Dict[str, Any]:
    """Normaliza metadatos de dispositivos de diferentes esquemas."""
    
    # Priorizar campos con 'or' para flexibilidad
    alias = raw_doc.get("alias") or raw_doc.get("nombre")
    loc = raw_doc.get("location") or raw_doc.get("ubicacion")
    
    return {
        "_id": raw_doc.get("_id"),
        "alias": alias or raw_doc["_id"],  # Fallback al ID
        "location": loc or "Desconocido",
        "umbrales": raw_doc.get("umbrales", {}),
        "original_source": raw_doc  # Guardar para debugging
    }
```

### 2. En `views/dashboard.py`

El dashboard usa los datos **ya normalizados**:

```python
# Los alias vienen unificados desde la capa de datos
metadata = config_manager.get_device_metadata()

for device_id, meta in metadata.items():
    display_name = meta.get("alias")  # Siempre 'alias', nunca 'nombre'
    ubicacion = meta.get("location")  # Siempre 'location', nunca 'ubicacion'
```

---

## 📋 Checklist de Integración

Al integrar una nueva base de datos, verifica:

- [ ] **Telemetría**: Tiene campo `timestamp` válido
- [ ] **Telemetría**: Tiene campo `device_id` o `dispositivo_id`
- [ ] **Telemetría**: Los datos de sensores están en `sensors` o `datos`
- [ ] **Dispositivos**: Existe colección de metadatos (nombre configurable)
- [ ] **Dispositivos**: Tiene campo `_id` como identificador único
- [ ] **Dispositivos**: Tiene campo `alias` o `nombre` para nombres amigables
- [ ] **Conexión**: El URI de MongoDB permite acceso desde la IP de la app

---

## 🧪 Verificar Normalización

Ejecuta el script de verificación:

```bash
python -m scripts.test_normalization
```

**Salida esperada:**
```
============================================================
VERIFICACIÓN DE NORMALIZACIÓN MULTI-ESQUEMA
============================================================

✓ Total de dispositivos encontrados: 3

Dispositivo: biofloc_esp32_c8e0
  → Alias normalizado: 'Esp-32 MicroAlgas Martin'
  → Location normalizado: 'Biorreactor Izq'
  → Campos fuente: 'alias' | 'location'

Dispositivo: 34865D46A848
  → Alias normalizado: 'ESP de prueba con datos fake'
  → Location normalizado: 'Cuarto piso - escuela de ingeniería'
  → Campos fuente: 'nombre' | 'ubicacion'

============================================================
VERIFICACIÓN COMPLETADA
============================================================
```

---

## 🔒 Permisos de Escritura

Por defecto:
- **Base Principal (MONGO_URI)**: Lectura + Escritura
- **Bases Secundarias (MONGO_URI_2, ...)**: Solo Lectura

Para habilitar escritura en una base secundaria, modifica `modules/database.py`:

```python
# Línea ~60
self.sources.append({
    "name": "Secondary",
    "client": mongo_client_2,
    "db": os.getenv("MONGO_DB_2"),
    "coll_telemetry": os.getenv("MONGO_COLLECTION_2"),
    "coll_devices": os.getenv("MONGO_DEVICES_COLLECTION_2"),
    "writable": True  # Cambiar de False a True
})
```

**⚠️ Precaución:**
Solo habilita escritura si tienes permisos sobre esa base de datos y comprendes las implicaciones de seguridad.

---

## 📊 Ejemplo de Configuración Multi-Fuente

### Caso de Uso: Laboratorio + Partner

**Tu laboratorio (BD Principal):**
- URI: `mongodb+srv://admin:pass@cluster.net/`
- DB: `SistemasLab`
- Schema: Propio (`alias`, `location`)

**Laboratorio Partner (BD Secundaria):**
- URI: `mongodb+srv://partner:secret@remote.net/`
- DB: `Datos_ESP`
- Schema: Diferente (`nombre`, `ubicacion`)

**Configuración `.env`:**
```ini
# Tu laboratorio
MONGO_URI=mongodb+srv://admin:pass@cluster.net/
MONGO_DB=SistemasLab
MONGO_COLLECTION=telemetria
MONGO_DEVICES_COLLECTION=devices

# Partner
MONGO_URI_2=mongodb+srv://partner:secret@remote.net/
MONGO_DB_2=Datos_ESP
MONGO_COLLECTION_2=sensors_data
MONGO_DEVICES_COLLECTION_2=devices_data
```

**Resultado:**
- Dashboard unificado mostrando dispositivos de ambos laboratorios
- Nombres normalizados automáticamente
- Datos históricos fusionados en gráficas y tablas
- Sin necesidad de migrar ni modificar las bases de datos originales

---

## 🤝 Soporte

Si encuentras un esquema de datos que no está soportado, abre un [issue en GitHub](https://github.com/Marton1123/Core-IoT-Monitor/issues) describiendo la estructura.

El sistema está diseñado para ser extensible y agregar nuevos adaptadores es sencillo.

---

**Última actualización:** Febrero 2026  
**Versión del sistema:** v3.0.0
