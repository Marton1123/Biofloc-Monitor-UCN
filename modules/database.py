
import os
import time
import pandas as pd
import streamlit as st
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
import certifi
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timedelta, timezone

# Cargar variables de entorno
load_dotenv()

# --- PATRÓN SINGLETON (CONEXIÓN ROBUSTA) ---
# Ahora soporta cachear multiples clientes por URI
@st.cache_resource(ttl=3600, show_spinner=False)
def get_mongo_client(uri: str) -> Optional[MongoClient]:
    if not uri: return None
    try:
        client = MongoClient(
            uri,
            connectTimeoutMS=30000,
            retryWrites=True,
            tls=True,
            tlsCAFile=certifi.where(),
            tz_aware=True
        )
        # Ping rapido para validar
        client.admin.command('ping')
        return client
    except Exception as e:
        st.error(f"Error conexión MongoDB ({uri[:20]}...): {str(e)}")
        return None

class DatabaseConnection:
    CONFIG_COLLECTION = "system_config"

    def __init__(self):
        self.sources = []
        
        # Cargar fuentes dinámicamente (1 y 2, y escalable a N si se quisiera)
        # Fuente 1
        self._add_source(
            uri=os.getenv("MONGO_URI"),
            db_name=os.getenv("MONGO_DB"),
            telem_coll=os.getenv("MONGO_COLLECTION"),
            dev_coll=os.getenv("MONGO_DEVICES_COLLECTION"),
            name="Primary",
            is_writable=True # Solo la principal es editable por defecto para seguridad
        )
        
        # Fuente 2
        self._add_source(
            uri=os.getenv("MONGO_URI_2"),
            db_name=os.getenv("MONGO_DB_2"),
            telem_coll=os.getenv("MONGO_COLLECTION_2"),
            dev_coll=os.getenv("MONGO_DEVICES_COLLECTION_2"),
            name="Secondary",
            is_writable=True # Habilitamos escritura para corregir datos del Partner 
        )

    def _add_source(self, uri, db_name, telem_coll, dev_coll, name, is_writable=False):
        """Helper para registrar fuentes de datos de forma modular."""
        if uri and db_name:
            client = get_mongo_client(uri)
            if client is not None:
                self.sources.append({
                    "name": name,
                    "client": client,
                    "db": db_name,
                    "coll_telemetry": telem_coll,
                    "coll_devices": dev_coll,
                    "writable": is_writable
                })

    # --- MÉTODOS ADAPTER (Normalización) ---
    def _normalize_document(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """ADAPTER: Normaliza documentos de TELEMETRÍA de diferentes esquemas."""
        if not doc: return {}
        
        # 1. Normalizar ID de Dispositivo
        dev_id = doc.get("device_id")
        if not dev_id:
            dev_id = doc.get("dispositivo_id")
        if not dev_id:
            dev_id = doc.get("metadata", {}).get("device_id", "unknown")
            
        # 2. Normalizar Sensores
        sensors = doc.get("sensors", {})
        if not sensors:
            sensors = doc.get("datos", {})
            
        # 3. Normalizar Timestamp
        raw_ts = doc.get("timestamp")
        final_ts = None
        
        try:
            if isinstance(raw_ts, dict) and "$date" in raw_ts:
                raw_ts = raw_ts["$date"]
                
            if isinstance(raw_ts, (int, float)):
                if raw_ts > 1e11: 
                    final_ts = pd.to_datetime(raw_ts, unit='ms', utc=True).to_pydatetime()
                else:
                    final_ts = pd.to_datetime(raw_ts, unit='s', utc=True).to_pydatetime()
            elif isinstance(raw_ts, str):
                try:
                    final_ts = datetime.fromisoformat(raw_ts)
                except ValueError:
                    final_ts = pd.to_datetime(raw_ts, errors='coerce', utc=True)
                    if pd.isna(final_ts): final_ts = None
                    else: final_ts = final_ts.to_pydatetime()
            elif isinstance(raw_ts, datetime):
                final_ts = raw_ts
                if final_ts.tzinfo is None:
                    final_ts = final_ts.replace(tzinfo=timezone.utc)
        except Exception:
            final_ts = None
        
        if final_ts is not None:
             if final_ts.tzinfo is not None:
                 chile_tz = timezone(timedelta(hours=-3))
                 final_ts = final_ts.astimezone(chile_tz)
                 final_ts = final_ts.replace(tzinfo=None)
        
        oid = str(doc.get("_id", ""))
        
        # 4. Normalizar Sensores (Flattening)
        normalized_sensors = {}
        for key, value in sensors.items():
            norm_key = key.lower().strip()
            
            if norm_key in ["temp", "temperatura"]: norm_key = "temperature"
            elif norm_key in ["oxigeno", "od", "do"]: norm_key = "oxygen"
            
            final_value = None
            if isinstance(value, dict):
                final_value = value.get("value")
            elif isinstance(value, (int, float)) and not isinstance(value, bool):
                final_value = value
            
            if final_value is not None: 
                try:
                    normalized_sensors[norm_key] = float(final_value)
                except (ValueError, TypeError):
                    pass
            
        # 5. Normalizar Location (puede venir como 'location' o 'ubicacion')
        loc = doc.get("location")
        if not loc:
            loc = doc.get("ubicacion", "Sin Asignar")
        
        return {
            "device_id": dev_id,
            "timestamp": final_ts,
            "location": loc,
            "sensors": normalized_sensors,
            "alerts": doc.get("alerts", []),
            "_source_id": oid 
        }

    def _normalize_device_doc(self, raw_doc: Dict[str, Any]) -> Dict[str, Any]:
        """ADAPTER: Normaliza metadatos de DISPOSITIVOS de diferentes esquemas (Propio vs Partner)."""
        if not raw_doc: return {}
        
        # ID es clave siempre
        d_id = raw_doc.get("_id")
        
        # 1. Alias / Nombre (soporta ambos esquemas)
        # Schema Propio: 'alias'
        # Schema Partner: 'nombre'
        alias = raw_doc.get("alias") or raw_doc.get("nombre")
        if not alias:
            alias = d_id  # Fallback al ID si no hay nombre ni alias
            
        # 2. Location / Ubicación (soporta ambos esquemas)
        # Schema Propio: 'location'
        # Schema Partner: 'ubicacion'
        loc = raw_doc.get("location") or raw_doc.get("ubicacion")
        if not loc:
            loc = "Desconocido"
            
        # 3. Umbrales
        # Ambos parecen usar 'umbrales' o 'config' -> mapping directo
        # Si Partner usa estructura plana en 'umbrales', ConfigManager ya lo maneja (normalize_thresholds)
        umbrales = raw_doc.get("umbrales", {})
        
        # Construir doc unificado
        return {
            "_id": d_id,
            "alias": alias,
            "location": loc,
            "umbrales": umbrales,
            "original_source": raw_doc # Guardar original por si acaso
        }

    # --- MÉTODO PARA DASHBOARD (Multi-DB Telemetría + Registro + Historical Fallback) ---
    def get_latest_by_device(self, retries: int = 2) -> pd.DataFrame:
        """
        Obtiene el estado más reciente de TODOS los dispositivos.
        Estrategia 'Registry-Historical': 
        1. Obtiene la lista maestra de dispositivos registrados (Metadata).
        2. Obtiene la telemetría reciente (Live).
        3. Para los faltantes, busca su ÚLTIMO dato histórico.
        """
        if not self.sources: return pd.DataFrame()
        
        # 1. Obtener Universo de Dispositivos Registrados (Master List)
        registered_devices = self.get_all_registered_devices()
        known_map = {d["_id"]: d for d in registered_devices}
        
        all_docs = []
        seen_devices = set()
        
        # 2. Obtener Telemetría Reciente (Live Data)
        for source in self.sources:
            if not source["coll_telemetry"]: continue
            try:
                db = source["client"][source["db"]]
                collection = db[source["coll_telemetry"]]
                
                # Limitamos a 2000 para tener más chance de encontrar dispositivos "lentos"
                cursor = collection.find({}).sort("timestamp", -1).limit(2000)
                documents = list(cursor)
                
                for raw_doc in documents:
                    norm_doc = self._normalize_document(raw_doc)
                    dev_id = norm_doc["device_id"]
                    
                    if dev_id and dev_id != "unknown" and dev_id not in seen_devices:
                        # Si tenemos metadata registrada para este ID, enriquecemos la location
                        if dev_id in known_map:
                            meta = known_map[dev_id]
                            reg_loc = meta.get("location")
                            reg_alias = meta.get("alias")
                            if reg_loc: norm_doc["location"] = reg_loc
                            if reg_alias: norm_doc["external_alias"] = reg_alias

                        seen_devices.add(dev_id)
                        all_docs.append(norm_doc)
                        
            except Exception as e:
                print(f"Error fetching telemetry from {source['name']}: {str(e)}")
                continue

        # 3. Recuperar Dispositivos Faltantes (Historical Fetch)
        for dev_id, meta in known_map.items():
            if dev_id not in seen_devices:
                # Buscar el último dato real en la historia
                last_known_df = self.get_latest_for_single_device(dev_id)
                reg_alias = meta.get("alias")
                
                if not last_known_df.empty:
                    # Usar el último estado conocido
                    rec = last_known_df.iloc[0].to_dict()
                    
                    # Asegurar ubicación de metadata si existe
                    reg_loc = meta.get("location")
                    if reg_loc: rec["location"] = reg_loc
                    
                    # Re-estructurar para all_docs
                    doc_struct = {
                        "device_id": rec["device_id"],
                        "timestamp": rec["timestamp"],
                        "location": rec["location"],
                        "sensors": rec["sensor_data"], 
                        "alerts": rec["alerts"], 
                        "_source_id": "historical_fetch"
                    }
                    if reg_alias: doc_struct["external_alias"] = reg_alias
                    all_docs.append(doc_struct)
                else:
                    # Solo falla a gris si NUNCA ha enviado datos
                    doc_struct = {
                        "device_id": dev_id,
                        "timestamp": None,
                        "location": meta.get("location", "Desconocido"),
                        "sensors": {},
                        "alerts": [],
                        "_source_id": "registry_fallback"
                    }
                    if reg_alias: doc_struct["external_alias"] = reg_alias
                    all_docs.append(doc_struct)

        return self._rows_to_dataframe_mixed(all_docs)

    def get_latest_for_single_device(self, device_id: str) -> pd.DataFrame:
        """Busca el dispositivo en todas las fuentes hasta encontrarlo."""
        if not self.sources: return pd.DataFrame()
        
        for source in self.sources:
            if not source["coll_telemetry"]: continue
            try:
                db = source["client"][source["db"]]
                collection = db[source["coll_telemetry"]]
                
                query = {"$or": [{"device_id": device_id}, {"dispositivo_id": device_id}]}
                
                # Buscar solo el ultimo
                doc = collection.find_one(query, sort=[("timestamp", -1)])
                if doc:
                    norm_doc = self._normalize_document(doc)
                    return self._rows_to_dataframe([norm_doc])
            except Exception:
                continue
        return pd.DataFrame()

    # --- METODOS PARA HISTORIAL (Multi-DB) ---
    def fetch_data(self, start_date=None, end_date=None, device_ids=None, limit=5000) -> pd.DataFrame:
        if not self.sources: return pd.DataFrame()
        
        all_norm_docs = []
        limit_per_source = limit // len(self.sources) + 100
        
        for source in self.sources:
            if not source["coll_telemetry"]: continue
            try:
                db = source["client"][source["db"]]
                collection = db[source["coll_telemetry"]]
                
                mongo_query = {}
                if device_ids:
                    mongo_query["$or"] = [{"device_id": {"$in": device_ids}}, {"dispositivo_id": {"$in": device_ids}}]
                
                raw_documents = []
                try:
                    cursor = collection.find(mongo_query).sort("timestamp", -1).limit(limit_per_source)
                    raw_documents = list(cursor)
                except Exception as sort_error:
                    if "memory" in str(sort_error).lower() or "Sort" in str(sort_error):
                        cursor = collection.find(mongo_query).limit(limit_per_source)
                        raw_documents = list(cursor)
                    else:
                        raise sort_error
                
                for d in raw_documents:
                    all_norm_docs.append(self._normalize_document(d))
            except Exception as e:
                st.warning(f"Error fetching history from {source['name']}: {str(e)[:100]}")
                continue
        
        if not all_norm_docs: return pd.DataFrame()
            
        all_norm_docs.sort(key=lambda x: x["timestamp"] or datetime.min, reverse=True)
        df = self._parse_historical_flat(all_norm_docs)
        
        if not df.empty and (start_date or end_date):
            if df['timestamp'].dt.tz is not None:
                    df['timestamp'] = df['timestamp'].dt.tz_localize(None)
            if start_date:
                if not isinstance(start_date, datetime): start_date = pd.to_datetime(start_date)
                df = df[df['timestamp'] >= start_date]
            if end_date:
                if not isinstance(end_date, datetime): end_date = pd.to_datetime(end_date)
                df = df[df['timestamp'] <= end_date]
        
        return df

    # --- MÉTODOS DE CONFIGURACIÓN & DISPOSITIVOS (Global / Multi-DB) ---
    
    def get_all_registered_devices(self) -> List[Dict[str, Any]]:
        """Recupera dispositivos de TODAS las fuentes configuradas."""
        all_devices = {} # Dict para de-duplicar por ID
        
        for source in self.sources:
            if not source["coll_devices"]: continue
            try:
                db = source["client"][source["db"]]
                coll = db[source["coll_devices"]]
                
                raw_list = list(coll.find({}))
                for raw in raw_list:
                    norm = self._normalize_device_doc(raw)
                    d_id = norm["_id"]
                    if d_id and d_id not in all_devices:
                        all_devices[d_id] = norm
                        
            except Exception as e:
                print(f"Error fetching devices from {source['name']}: {e}")
                
        return list(all_devices.values())

    def get_device_doc(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Busca metadata de un dispositivo específico en todas las fuentes."""
        for source in self.sources:
            if not source["coll_devices"]: continue
            try:
                db = source["client"][source["db"]]
                coll = db[source["coll_devices"]]
                
                doc = coll.find_one({"_id": device_id})
                if doc:
                    return self._normalize_device_doc(doc)
            except Exception:
                continue
        return None

    def update_device_doc(self, device_id: str, update_data: Dict[str, Any]) -> bool:
        """
        Intenta actualizar el dispositivo en la fuente donde 'vive'.
        Si no existe, lo crea en la fuente PRIMARIA (Writeable).
        """
        
        # 1. Buscar dónde existe este ID
        target_source = None
        for source in self.sources:
            if not source["coll_devices"]: continue
            # Check existencia (sin traer todo el doc para ser eficiente)
            try:
                if source["client"][source["db"]][source["coll_devices"]].count_documents({"_id": device_id}, limit=1) > 0:
                    if source["writable"]:
                        target_source = source
                        break
                    else:
                        st.warning(f"El dispositivo {device_id} pertenece a una BD externa de solo lectura.")
                        return False
            except: continue
        
        # 2. Si no existe en ninguna, usar la Principal (si es writable)
        if not target_source:
            for source in self.sources:
                if source["writable"] and source["coll_devices"]:
                    target_source = source
                    break
        
        if not target_source:
            st.error("No hay base de datos de escritura configurada.")
            return False
            
        # 3. Ejecutar Update
        try:
            coll = target_source["client"][target_source["db"]][target_source["coll_devices"]]
            
            final_update_data = {}
            for k, v in update_data.items():
                if k == "location" and "nombre" in target_source.get("mapping", []): 
                    pass
                final_update_data[k] = v
            
            result = coll.update_one(
                {"_id": device_id},
                {"$set": final_update_data},
                upsert=True
            )
            return result.acknowledged
        except Exception as e:
            st.error(f"Error updating device {device_id}: {e}")
            return False

    # --- CONFIG LEGACY / GLOBAL ---
    def get_config(self, config_id: str) -> Optional[Dict[str, Any]]:
        db = self._get_primary_db()
        if db is None: return None
        try:
            return db[self.CONFIG_COLLECTION].find_one({"_id": config_id})
        except: return None

    def save_config(self, config_id: str, config_data: Dict[str, Any]) -> bool:
        db = self._get_primary_db()
        if db is None: return False
        try:
            config_data["_id"] = config_id
            config_data["last_updated"] = datetime.now().isoformat()
            return db[self.CONFIG_COLLECTION].replace_one({"_id": config_id}, config_data, upsert=True).acknowledged
        except Exception: return False
        
    def delete_config(self, config_id: str) -> bool:
        db = self._get_primary_db()
        if db is None: return False
        try:
            return db[self.CONFIG_COLLECTION].delete_one({"_id": config_id}).deleted_count > 0
        except: return False

    # --- HELPERS ---
    def _get_primary_db(self):
        for s in self.sources:
            if s["name"] == "Primary":
                return s["client"][s["db"]]
        return None

    def _rows_to_dataframe(self, norm_docs: List[Dict[str, Any]]) -> pd.DataFrame:
        processed = []
        for doc in norm_docs:
            processed.append({
                "device_id": doc["device_id"],
                "timestamp": doc["timestamp"],
                "location": doc["location"],
                "sensor_data": doc["sensors"], 
                "alerts": doc["alerts"]
            })
        df = pd.DataFrame(processed)
        if "timestamp" in df.columns and not df.empty:
             df["timestamp"] = pd.to_datetime(df["timestamp"], errors='coerce')
        return df

    def _rows_to_dataframe_mixed(self, mixed_docs: List[Dict[str, Any]]) -> pd.DataFrame:
        """Helper para all_docs que puede contener docs frescos o recuperados de historia."""
        processed = []
        for doc in mixed_docs:
            # Detectar si viene de live scan (sensors) o fallback (sensor_data)
            s_data = doc.get("sensors") if "sensors" in doc else doc.get("sensor_data", {})
            
            # Alias externo
            ext_alias = doc.get("external_alias")
            
            processed.append({
                "device_id": doc["device_id"],
                "timestamp": doc["timestamp"],
                "location": doc["location"],
                "sensor_data": s_data, 
                "alerts": doc.get("alerts", []),
                "external_alias": ext_alias # Pasamos al dataframe
            })
        df = pd.DataFrame(processed)
        if "timestamp" in df.columns and not df.empty:
             df["timestamp"] = pd.to_datetime(df["timestamp"], errors='coerce')
        return df

    def _parse_historical_flat(self, norm_docs: List[Dict[str, Any]]) -> pd.DataFrame:
        flat_data = []
        for doc in norm_docs:
            row = {"timestamp": doc["timestamp"], "device_id": doc["device_id"], "location": doc["location"]}
            for name, val in doc["sensors"].items():
                if isinstance(val, dict): row[name] = val.get("value")
                elif isinstance(val, (int, float)): row[name] = val
            flat_data.append(row)
        
        df = pd.DataFrame(flat_data)
        if "timestamp" in df.columns: df["timestamp"] = pd.to_datetime(df["timestamp"], errors='coerce')
        cols = df.columns.drop(['timestamp', 'device_id', 'location'], errors='ignore')
        for col in cols: df[col] = pd.to_numeric(df[col], errors='coerce')
        return df