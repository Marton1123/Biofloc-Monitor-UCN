from typing import Dict, Any, Optional
from modules.database import DatabaseConnection
from modules.sensor_registry import SensorRegistry


class ConfigManager:
    
    CONFIG_ID = "sensor_thresholds"
    
    def __init__(self, db: DatabaseConnection):
        self.db = db
        self._cached_config = None
        # Cache para metadatos de dispositivos para evitar queries constantes en bucles
        self._cached_devices_meta = None
    
    def get_sensor_config(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Obtiene la configuración GLOBAL de sensores (defaults)."""
        if self._cached_config is not None and not force_refresh:
            return self._cached_config
        
        # Intentar leer de DB (opcional)
        config = self.db.get_config(self.CONFIG_ID)
        
        # Si NO existe configuración en DB, usar defaults de código sin escribir en DB
        # Esto permite al usuario borrar la colección 'system_config' si lo desea.
        if config is None or not config.get("sensors"):
            SensorRegistry._ensure_loaded()
            default_sensors = {k: v.to_dict() for k, v in SensorRegistry._defaults.items()}
            
            # Construir objeto de config en memoria
            config = {
                "_id": self.CONFIG_ID,
                "sensors": default_sensors,
                "_is_default": True # Flag interno para saber que es default
            }
            # NOTA: Ya no guardamos esto en DB automáticamente para mantenerla limpia.
        
        self._cached_config = config
        return config
    
    def _create_initial_config(self) -> Dict[str, Any]:
        # DEPRECATED: Ya no se usa para evitar ensuciar la DB
        initial_config = {
            "_id": self.CONFIG_ID,
            "sensors": {}
        }
        return initial_config
    
    def get_threshold_for_sensor(self, sensor_name: str) -> Optional[Dict[str, Any]]:
        config = self.get_sensor_config()
        sensors = config.get("sensors", {})
        
        return sensors.get(sensor_name)
    
    def update_sensor_threshold(self, sensor_name: str, threshold_data: Dict[str, Any]) -> bool:
        if not SensorRegistry.validate_sensor_config(threshold_data):
            raise ValueError(f"Configuración inválida para sensor {sensor_name}")
        
        config = self.get_sensor_config(force_refresh=True)
        
        if "sensors" not in config:
            config["sensors"] = {}
        
        config["sensors"][sensor_name] = threshold_data
        
        # Al guardar, si persistimos en DB.
        # Si la colección no existe, se creará solo cuando el usuario edite algo explícitamente.
        success = self.db.save_config(self.CONFIG_ID, config)
        
        if success:
            self._cached_config = None
        
        return success
    
    def update_multiple_thresholds(self, thresholds: Dict[str, Dict[str, Any]]) -> bool:
        for sensor_name, threshold_data in thresholds.items():
            if not SensorRegistry.validate_sensor_config(threshold_data):
                raise ValueError(f"Configuración inválida para sensor {sensor_name}")
        
        config = self.get_sensor_config(force_refresh=True)
        
        if "sensors" not in config:
            config["sensors"] = {}
        
        config["sensors"].update(thresholds)
        
        success = self.db.save_config(self.CONFIG_ID, config)
        
        if success:
            self._cached_config = None
        
        return success
    
    def delete_sensor_threshold(self, sensor_name: str) -> bool:
        config = self.get_sensor_config(force_refresh=True)
        
        if "sensors" not in config or sensor_name not in config["sensors"]:
            return False
        
        del config["sensors"][sensor_name]
        
        success = self.db.save_config(self.CONFIG_ID, config)
        
        if success:
            self._cached_config = None
        
        return success
    
    def reset_to_defaults(self, detected_sensors: set) -> bool:
        # Esto borrara la config personalizada en DB
        return self.db.delete_config(self.CONFIG_ID)
    
    def sync_with_detected_sensors(self, detected_sensors: set) -> bool:
        # Solo sincronizamos si YA existe una config en DB que queramos mantener al día.
        # Si estamos usando defaults en memoria, no hay nada que sincronizar (read-only).
        config = self.get_sensor_config(force_refresh=True)
        
        if config.get("_is_default"):
            return True # No hacer nada si estamos en modo default
            
        updated_config = SensorRegistry.merge_configs(config, detected_sensors)
        
        success = self.db.save_config(self.CONFIG_ID, updated_config)
        
        if success:
            self._cached_config = None
        
        return success
    
    def get_all_configured_sensors(self) -> Dict[str, Dict[str, Any]]:
        config = self.get_sensor_config()
        return config.get("sensors", {})
    
    # --- MÉTODOS DE METADATOS Y DISPOSITIVOS (NUEVO ESQUEMA) ---

    def get_device_metadata(self) -> Dict[str, Dict[str, Any]]:
        """
        Recupera metadatos de la colección 'devices'.
        Retorna un dict: {device_id: {alias: ..., location: ..., thresholds: ...}}
        """
        raw_devices = self.db.get_all_registered_devices()
        meta_map = {}
        for d in raw_devices:
            d_id = d.get("_id")
            if d_id:
                # Normalizar umbrales
                raw_umbrales = d.get("umbrales", {})
                norm_thresholds = self._normalize_thresholds(raw_umbrales)
                
                meta_map[d_id] = {
                    "alias": d.get("alias", ""),
                    "location": d.get("location", ""),
                    "thresholds": norm_thresholds
                }
        return meta_map

    def _normalize_thresholds(self, raw: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Convierte formato plano (ph_min) a anidado ({ph: {min: ...}}) si es necesario."""
        normalized = {}
        for k, v in raw.items():
            # Si ya es un dict, asumimos formato correcto (nested)
            if isinstance(v, dict):
                normalized[k] = v
                continue
            
            # Intentar parsear keys planas: ph_min, temp_max, etc.
            parts = k.split('_')
            if len(parts) >= 2:
                # Caso: ph_min -> sensor=ph, param=min
                param = parts[-1] # min, max, offset
                sensor = "_".join(parts[:-1]) # ph, temp, dissolved_oxygen
                
                # Normalizar nombres de sensores comunes
                if sensor in ['temp', 'temperatura']: sensor = 'temperature'
                
                if sensor not in normalized: normalized[sensor] = {}
                
                # Mapear params comunes a keys que DeviceManager entiende
                # DeviceManager entiende: min, max, optimal_min, optimal_max, critical_min...
                if param == 'min': normalized[sensor]['min'] = v
                elif param == 'max': normalized[sensor]['max'] = v
                else: normalized[sensor][param] = v
        
        # Si no se encontró nada plano, puede que sea un dict vacio o llaves desconocidas
        # Si normalized esta vacio pero raw no, y no eran dicts, devolvemos raw por si acaso
        if not normalized and raw:
             return raw 
             
        return normalized

    def update_device_metadata(self, device_id: str, alias: str, location: str) -> bool:
        """Actualiza el alias y ubicación de un dispositivo específico en 'devices'."""
        update_data = {
            "alias": alias,
            "location": location
        }
        return self.db.update_device_doc(device_id, update_data)

    def get_device_info(self, device_id: str) -> Dict[str, str]:
        """Obtiene la info enriquecida de un dispositivo."""
        doc = self.db.get_device_doc(device_id)
        if doc:
            return {
                "alias": doc.get("alias", device_id),
                "location": doc.get("location", "Desconocido")
            }
        return {"alias": device_id, "location": "Desconocido"}
        
    def get_device_thresholds(self, device_id: str) -> Dict[str, Any]:
        """Obtiene umbrales específicos de un dispositivo (campo 'umbrales')."""
        doc = self.db.get_device_doc(device_id)
        if doc:
            return self._normalize_thresholds(doc.get("umbrales", {}))
        return {}

    def update_device_threshold(self, device_id: str, sensor_name: str, threshold_data: Dict[str, Any]) -> bool:
        """Guarda umbrales específicos para un sensor de un dispositivo en 'devices'."""
        # Se requiere "dot notation" para actualizar un campo anidado en Mongo sin borrar el resto
        # Ej: "umbrales.temperatura" = {...}
        key = f"umbrales.{sensor_name}"
        return self.db.update_device_doc(device_id, {key: threshold_data})