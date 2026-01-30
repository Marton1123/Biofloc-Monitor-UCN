
import os
import sys
import pandas as pd
from dotenv import load_dotenv

# Add root to pythonpath
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.database import DatabaseConnection

def debug_database():
    print("--- INICIANDO DEBUG DE BASE DE DATOS ---")
    
    # Identificar ruta raiz y .env explícitamente
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_path = os.path.join(root_dir, '.env')
    print(f"Buscando .env en: {env_path}")
    
    if os.path.exists(env_path):
        print("  -> Archivo .env encontrado.")
        load_dotenv(dotenv_path=env_path, override=True)
    else:
        print("  -> ALERTA: Archivo .env NO encontrado.")

    # Safe prints
    uri = os.getenv('MONGO_URI')
    print(f"MONGO_URI: {uri[:20] + '...' if uri else 'NO DEFINIDO'}")
    
    uri2 = os.getenv('MONGO_URI_2')
    print(f"MONGO_URI_2: {uri2[:20] + '...' if uri2 else 'NO DEFINIDO'}")
    
    if not uri:
        print("CRITICAL: No se pudo cargar MONGO_URI. Abortando test de conexión.")
        return

    try:
        db = DatabaseConnection()
        print(f"Fuentes configuradas: {len(db.sources)}")
        for i, s in enumerate(db.sources):
            print(f"\n[FUENTE {i+1}: {s['name']}]")
            print(f"Info: DB={s['db']} | Telemetría={s['coll_telemetry']} | Devices={s['coll_devices']}")
            
            try:
                client = s['client']
                database = client[s['db']]
                
                # 1. Analizar Metadatos (Devices)
                if s['coll_devices']:
                    coll_dev = database[s['coll_devices']]
                    dev_count = coll_dev.count_documents({})
                    print(f"  -> Docs en colección de DISPOSITIVOS ({s['coll_devices']}): {dev_count}")
                    
                    if dev_count > 0:
                        print("     Listado de dispositivos registrados:")
                        for d in coll_dev.find():
                            print(f"       * ID: {d.get('_id')} | Nombre: {d.get('nombre') or d.get('alias')}")
                
                # 2. Analizar Telemetría
                coll_tel = database[s['coll_telemetry']]
                tel_count = coll_tel.count_documents({})
                print(f"  -> Docs en colección de TELEMETRÍA ({s['coll_telemetry']}): {tel_count}")
                
                if tel_count > 0:
                    # Buscar IDs únicos recent
                    print("     Buscando IDs únicos en últimos 5000 registros...")
                    pipeline = [
                        {"$sort": {"timestamp": -1}},
                        {"$limit": 5000},
                        {"$project": {"device_id": 1, "dispositivo_id": 1, "_id": 0}}
                    ]
                    results = list(coll_tel.aggregate(pipeline))
                    
                    found_ids = set()
                    for r in results:
                        if "device_id" in r: found_ids.add(r['device_id'])
                        if "dispositivo_id" in r: found_ids.add(r['dispositivo_id'])
                    
                    print(f"     IDs detectados en telemetría reciente: {found_ids}")
                    
            except Exception as e:
                print(f"  -> Error consultando fuente: {e}")

        print("\n--- TEST FINAL: get_latest_by_device (Lo que ve el Dashboard) ---")
        df = db.get_latest_by_device()
        print(df)

    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_database()
