#!/usr/bin/env python3
"""
Script para probar el sistema de autenticación JWT
"""

from app.schemas.auth import LoginRequest
from app.services.user_service import UserService
from app.services.auth_service import AuthService
from app.database import SessionLocal
from sqlalchemy.orm import Session
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_authentication():
    """Probar el sistema de autenticación"""

    print("🔐 Probando sistema de autenticación JWT...")

    db = SessionLocal()
    auth_service = AuthService()
    user_service = UserService()

    try:
        # 1. Probar autenticación con usuario existente
        print("\n1️⃣ Probando login con usuario admin...")

        # Crear datos de login
        login_data = LoginRequest(
            email="admin@example.com",
            password="admin123"
        )

        # Autenticar usuario
        user = auth_service.authenticate_user(
            db, login_data.email, login_data.password)

        if user:
            print(f"✅ Usuario autenticado: {user.email}")

            # 2. Generar token JWT
            print("\n2️⃣ Generando token JWT...")

            access_token = auth_service.create_access_token(
                data={"sub": user.email}
            )

            print(f"✅ Token generado: {access_token[:50]}...")

            # 3. Verificar token
            print("\n3️⃣ Verificando token...")

            token_data = auth_service.verify_token(access_token)

            if token_data:
                print(f"✅ Token verificado para usuario: {token_data.email}")

                # 4. Obtener usuario desde token
                print("\n4️⃣ Obteniendo usuario desde token...")

                current_user = auth_service.get_current_user(db, access_token)

                if current_user:
                    print(
                        f"✅ Usuario obtenido desde token: {current_user.email}")
                else:
                    print("❌ No se pudo obtener usuario desde token")
            else:
                print("❌ Token no válido")
        else:
            print("❌ Usuario no autenticado")

        # 5. Probar con credenciales incorrectas
        print("\n5️⃣ Probando con credenciales incorrectas...")

        wrong_login = LoginRequest(
            email="admin@example.com",
            password="wrongpassword"
        )

        wrong_user = auth_service.authenticate_user(
            db, wrong_login.email, wrong_login.password)

        if not wrong_user:
            print("✅ Correctamente rechazó credenciales incorrectas")
        else:
            print("❌ Aceptó credenciales incorrectas")

        print("\n🎉 ¡Pruebas de autenticación completadas!")

    except Exception as e:
        print(f"❌ Error durante las pruebas: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    test_authentication()
