"""
Script de verificación de normalización multi-esquema
Verifica que 'alias'/'nombre' y 'location'/'ubicacion' se manejan correctamente.
"""
import os
from dotenv import load_dotenv
from modules.database import DatabaseConnection

load_dotenv()

def test_normalization():
    print("=" * 60)
    print("VERIFICACIÓN DE NORMALIZACIÓN MULTI-ESQUEMA")
    print("=" * 60)
    
    db = DatabaseConnection()
    
    # Obtener todos los dispositivos registrados
    devices = db.get_all_registered_devices()
    
    print(f"\n✓ Total de dispositivos encontrados: {len(devices)}\n")
    
    for device in devices:
        device_id = device.get("_id")
        alias = device.get("alias")
        location = device.get("location")
        
        # Verificar que tenemos datos
        print(f"Dispositivo: {device_id}")
        print(f"  → Alias normalizado: '{alias}'")
        print(f"  → Location normalizado: '{location}'")
        
        # Mostrar qué campo original se usó (debugging)
        original = device.get("original_source", {})
        has_alias = "alias" in original
        has_nombre = "nombre" in original
        has_location = "location" in original
        has_ubicacion = "ubicacion" in original
        
        print(f"  → Campos fuente: ", end="")
        if has_alias: print("'alias'", end=" ")
        if has_nombre: print("'nombre'", end=" ")
        print("|", end=" ")
        if has_location: print("'location'", end=" ")
        if has_ubicacion: print("'ubicacion'", end=" ")
        print("\n")
    
    print("=" * 60)
    print("VERIFICACIÓN COMPLETADA")
    print("=" * 60)

if __name__ == "__main__":
    test_normalization()
