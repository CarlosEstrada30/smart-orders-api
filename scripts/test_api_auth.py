#!/usr/bin/env python3
"""
Script para probar los endpoints de autenticación de la API
"""

import requests
import json
import time

# Configuración de la API
BASE_URL = "http://localhost:8000/api/v1"
LOGIN_URL = f"{BASE_URL}/auth/login"
ME_URL = f"{BASE_URL}/auth/me"
USERS_URL = f"{BASE_URL}/users"

def test_api_authentication():
    """Probar la autenticación de la API"""
    
    print("🌐 Probando endpoints de autenticación de la API...")
    
    # 1. Probar login exitoso
    print("\n1️⃣ Probando login exitoso...")
    
    login_data = {
        "email": "admin@example.com",
        "password": "admin123"
    }
    
    try:
        response = requests.post(LOGIN_URL, json=login_data)
        
        if response.status_code == 200:
            token_data = response.json()
            access_token = token_data["access_token"]
            print(f"✅ Login exitoso. Token: {access_token[:50]}...")
            
            # 2. Probar endpoint /me con token válido
            print("\n2️⃣ Probando endpoint /me con token válido...")
            
            headers = {"Authorization": f"Bearer {access_token}"}
            me_response = requests.get(ME_URL, headers=headers)
            
            if me_response.status_code == 200:
                user_info = me_response.json()
                print(f"✅ Información del usuario obtenida: {user_info['email']}")
            else:
                print(f"❌ Error al obtener información del usuario: {me_response.status_code}")
            
            # 3. Probar endpoint protegido (users) con token válido
            print("\n3️⃣ Probando endpoint protegido (users) con token válido...")
            
            users_response = requests.get(USERS_URL, headers=headers)
            
            if users_response.status_code == 200:
                users = users_response.json()
                print(f"✅ Lista de usuarios obtenida: {len(users)} usuarios")
            else:
                print(f"❌ Error al obtener usuarios: {users_response.status_code}")
            
            # 4. Probar endpoint sin token (debería fallar)
            print("\n4️⃣ Probando endpoint protegido sin token...")
            
            no_token_response = requests.get(USERS_URL)
            
            if no_token_response.status_code == 401:
                print("✅ Correctamente rechazó acceso sin token")
            else:
                print(f"❌ Debería haber rechazado acceso sin token: {no_token_response.status_code}")
            
            # 5. Probar con token inválido
            print("\n5️⃣ Probando con token inválido...")
            
            invalid_headers = {"Authorization": "Bearer invalid_token"}
            invalid_response = requests.get(USERS_URL, headers=invalid_headers)
            
            if invalid_response.status_code == 401:
                print("✅ Correctamente rechazó token inválido")
            else:
                print(f"❌ Debería haber rechazado token inválido: {invalid_response.status_code}")
                
        else:
            print(f"❌ Error en login: {response.status_code}")
            print(f"Respuesta: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ No se pudo conectar a la API. Asegúrate de que esté ejecutándose en http://localhost:8000")
    except Exception as e:
        print(f"❌ Error durante las pruebas: {e}")
    
    print("\n🎉 ¡Pruebas de API completadas!")


if __name__ == "__main__":
    test_api_authentication() 