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
    DEVICES_COLLECTION = "devices"

    def __init__(self):
        self.sources = []
        
        # 1. Fuente Principal
        uri1 = os.getenv("MONGO_URI")
        db1 = os.getenv("MONGO_DB")
        coll1 = os.getenv("MONGO_COLLECTION")
        
        if uri1 and db1 and coll1:
            client1 = get_mongo_client(uri1)
            if client1:
                self.sources.append({
                    "name": "Primary",
                    "client": client1,
                    "db": db1,
                    "coll": coll1
                })
        
        # 2. Fuente Secundaria (Partner)
        uri2 = os.getenv("MONGO_URI_2")
        db2 = os.getenv("MONGO_DB_2")
        coll2 = os.getenv("MONGO_COLLECTION_2")
        
        if uri2 and db2 and coll2:
            client2 = get_mongo_client(uri2)
            if client2:
                self.sources.append({
                    "name": "Secondary",
                    "client": client2,
                    "db": db2,
                    "coll": coll2
                })

    # --- MÉTODOS ADAPTER (Normalización) ---
    def _normalize_document(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """ADAPTER: Normaliza documentos de diferentes esquemas a un formato unificado."""
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
                # Forzar interpretation como UTC
                if raw_ts > 1e11: 
                    final_ts = pd.to_datetime(raw_ts, unit='ms', utc=True).to_pydatetime()
                else:
                    final_ts = pd.to_datetime(raw_ts, unit='s', utc=True).to_pydatetime()
            elif isinstance(raw_ts, str):
                # Soporte para ISO8601 con offset (e.g., 2026-01-30T11:01:56-0300)
                try:
                    # Intento directo first (es mas rapido)
                    final_ts = datetime.fromisoformat(raw_ts)
                except ValueError:
                    final_ts = pd.to_datetime(raw_ts, errors='coerce', utc=True)
                    if pd.isna(final_ts): final_ts = None
                    else: final_ts = final_ts.to_pydatetime()

            elif isinstance(raw_ts, datetime):
                final_ts = raw_ts
                # Si pymongo nos da naive, asumimos UTC manualmente (caso raro con tz_aware=True)
                if final_ts.tzinfo is None:
                    final_ts = final_ts.replace(tzinfo=timezone.utc)
        except Exception:
            final_ts = None
        
        if final_ts is not None:
             if final_ts.tzinfo is not None:
                 # Si viene con zona horaria (UTC de Mongo o Offset), convertir a Chile (UTC-3)
                 chile_tz = timezone(timedelta(hours=-3))
                 final_ts = final_ts.astimezone(chile_tz)
                 final_ts = final_ts.replace(tzinfo=None) # Hacer naive para compatibilidad interna
        
        # Normalizar ID de config/mongo para evitar conflictos si se usa como key
        oid = str(doc.get("_id", ""))
        
        # 4. Normalizar nombres de sensores y extraer valores
        # Soporta dos formatos:
        # - Plano: {"temperature": 19.85}
        # - Anidado: {"temperature": {"value": 19.85, "unit": "C", "valid": true}}
        normalized_sensors = {}
        for key, value in sensors.items():
            norm_key = key.lower().strip()
            
            # Manejar aliases comunes
            if norm_key in ["temp", "temperatura"]:
                norm_key = "temperature"
            elif norm_key in ["oxigeno", "od", "do"]:
                norm_key = "oxygen"
            
            # Extraer el valor numérico
            final_value = None
            if isinstance(value, dict):
                # Formato anidado: {"value": 19.85, "unit": "C", ...}
                final_value = value.get("value")
            elif isinstance(value, (int, float)) and not isinstance(value, bool):
                # Formato plano: 19.85
                final_value = value
            
            # Solo agregar si es un valor numérico válido
            if final_value is not None: 
                try:
                    normalized_sensors[norm_key] = float(final_value)
                except (ValueError, TypeError):
                    pass  # Ignorar valores no convertibles
            
        return {
            "device_id": dev_id,
            "timestamp": final_ts,
            "location": doc.get("location", "Sin Asignar"),
            "sensors": normalized_sensors,
            "alerts": doc.get("alerts", []),
            "_source_id": oid 
        }

    # --- MÉTODO PARA DASHBOARD (Multi-DB) ---
    def get_latest_by_device(self, retries: int = 2) -> pd.DataFrame:
        if not self.sources: return pd.DataFrame()
        
        all_docs = []
        seen_devices = set()
        
        # Iterar sobre todas las fuentes configuradas
        for source in self.sources:
            try:
                db = source["client"][source["db"]]
                collection = db[source["coll"]]
                
                cursor = collection.find({}).sort("timestamp", -1).limit(1000) # Limitamos por fuente
                documents = list(cursor)
                
                for raw_doc in documents:
                    norm_doc = self._normalize_document(raw_doc)
                    dev_id = norm_doc["device_id"]
                    
                    if dev_id and dev_id != "unknown" and dev_id not in seen_devices:
                        seen_devices.add(dev_id)
                        all_docs.append(norm_doc)
                        
            except Exception as e:
                print(f"Error fetching from source {source['name']}: {str(e)}")
                continue

        return self._rows_to_dataframe(all_docs)

    def get_latest_for_single_device(self, device_id: str) -> pd.DataFrame:
        """Busca el dispositivo en todas las fuentes hasta encontrarlo."""
        if not self.sources: return pd.DataFrame()
        
        for source in self.sources:
            try:
                db = source["client"][source["db"]]
                collection = db[source["coll"]]
                
                query = {
                    "$or": [
                        {"device_id": device_id},
                        {"dispositivo_id": device_id}
                    ]
                }
                
                doc = collection.find_one(query, sort=[("timestamp", -1)])
                if doc:
                    norm_doc = self._normalize_document(doc)
                    return self._rows_to_dataframe([norm_doc])
                    
            except Exception:
                continue
                
        return pd.DataFrame()

    # --- METODOS PARA HISTORIAL Y GRAFICOS (Multi-DB Aggregation) ---
    def fetch_data(self, start_date=None, end_date=None, device_ids=None, limit=5000) -> pd.DataFrame:
        if not self.sources: return pd.DataFrame()
        
        all_norm_docs = []
        
        # Distribuir limite entre fuentes
        limit_per_source = limit // len(self.sources) + 100
        
        for idx, source in enumerate(self.sources):
            try:
                db = source["client"][source["db"]]
                collection = db[source["coll"]]
                
                mongo_query = {}
                
                if device_ids:
                    mongo_query["$or"] = [
                        {"device_id": {"$in": device_ids}},
                        {"dispositivo_id": {"$in": device_ids}}
                    ]
                
                raw_documents = []
                
                # Intentar con sort primero (obtiene datos recientes)
                try:
                    # Usar mismo limite para todas las fuentes
                    cursor = collection.find(mongo_query).sort("timestamp", -1).limit(limit_per_source)
                    raw_documents = list(cursor)
                except Exception as sort_error:
                    # Si falla el sort (memory limit), intentar sin sort
                    if "memory" in str(sort_error).lower() or "Sort" in str(sort_error):
                        # Cargar sin ordenar - se ordenara en Python despues
                        cursor = collection.find(mongo_query).limit(limit_per_source)
                        raw_documents = list(cursor)
                    else:
                        raise sort_error
                
                for d in raw_documents:
                    all_norm_docs.append(self._normalize_document(d))
                    
            except Exception as e:
                st.warning(f"Error parcial en {source['name']}: {str(e)[:100]}")
                continue
        
        if not all_norm_docs:
            return pd.DataFrame()
            
        # Ordenar todo lo combinado por fecha descendente
        all_norm_docs.sort(key=lambda x: x["timestamp"] or datetime.min, reverse=True)
        
        # Convertir a DataFrame historial plano
        df = self._parse_historical_flat(all_norm_docs)
        
        # Filtro de fechas en memoria (Pandas)
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

    # --- MÉTODOS DE CONFIGURACIÓN & DISPOSITIVOS ---
    
    def _get_primary_db(self):
        if not self.sources: return None
        return self.sources[0]["client"][self.sources[0]["db"]]

    def _get_collection(self, coll_name):
        db = self._get_primary_db()
        if db is not None:
             return db[coll_name]
        return None

    def get_config(self, config_id: str) -> Optional[Dict[str, Any]]:
        coll = self._get_collection(self.CONFIG_COLLECTION)
        if coll is None: return None
        try:
            return coll.find_one({"_id": config_id})
        except Exception:
            return None

    def save_config(self, config_id: str, config_data: Dict[str, Any]) -> bool:
        coll = self._get_collection(self.CONFIG_COLLECTION)
        if coll is None: return False
        try:
            config_data["_id"] = config_id
            config_data["last_updated"] = datetime.now().isoformat()
            result = coll.replace_one({"_id": config_id}, config_data, upsert=True)
            return result.acknowledged
        except Exception as e:
            st.error(f"Error al guardar config: {str(e)}")
            return False
            
    # --- MÉTODOS PARA COLECCIÓN DE DISPOSITIVOS (NUEVO ESQUEMA) ---
    
    def get_all_registered_devices(self) -> List[Dict[str, Any]]:
        """Recupera todos los documentos de la colección 'devices'."""
        coll = self._get_collection(self.DEVICES_COLLECTION)
        if coll is None: return []
        try:
            return list(coll.find({}))
        except Exception as e:
            print(f"Error fetching devices metadata: {e}")
            return []

    def get_device_doc(self, device_id: str) -> Optional[Dict[str, Any]]:
        coll = self._get_collection(self.DEVICES_COLLECTION)
        if coll is None: return None
        try:
            return coll.find_one({"_id": device_id})
        except Exception:
            return None

    def update_device_doc(self, device_id: str, update_data: Dict[str, Any]) -> bool:
        """Actualiza campos específicos de un dispositivo (partial update)."""
        coll = self._get_collection(self.DEVICES_COLLECTION)
        if coll is None: return False
        try:
            # Asegurar que se haga un set para no borrar otros campos
            result = coll.update_one(
                {"_id": device_id},
                {"$set": update_data},
                upsert=True
            )
            return result.acknowledged
        except Exception as e:
            st.error(f"Error actualizando dispositivo {device_id}: {e}")
            return False

    def delete_config(self, config_id: str) -> bool:
        coll = self._get_collection(self.CONFIG_COLLECTION)
        if coll is None: return False
        try:
            result = coll.delete_one({"_id": config_id})
            return result.deleted_count > 0
        except Exception:
            return False

    # --- HELPERS DE DATAFRAME ---
    
    def _rows_to_dataframe(self, norm_docs: List[Dict[str, Any]]) -> pd.DataFrame:
        """Convierte docs YA normalizados a DataFrame para Dashboard."""
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

    def _parse_historical_flat(self, norm_docs: List[Dict[str, Any]]) -> pd.DataFrame:
        """Convierte docs YA normalizados a estructura plana para Historial/Gráficas."""
        flat_data = []
        for doc in norm_docs:
            row = {
                "timestamp": doc["timestamp"],
                "device_id": doc["device_id"],
                "location": doc["location"],
            }
            # Aplanar sensores
            sensors = doc["sensors"]
            for name, val in sensors.items():
                # Manejar si el sensor es un objeto {value: ...} o valor directo
                if isinstance(val, dict):
                    row[name] = val.get("value")
                elif isinstance(val, (int, float)):
                    row[name] = val
                    
            flat_data.append(row)
        
        df = pd.DataFrame(flat_data)
        
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"], errors='coerce')
            
        # Asegurar tipos numéricos para columnas de sensores
        cols = df.columns.drop(['timestamp', 'device_id', 'location'], errors='ignore')
        for col in cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
        return df