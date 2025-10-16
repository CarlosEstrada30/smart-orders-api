#!/usr/bin/env python3
"""
Script para probar la funcionalidad de gestión de usuarios y roles
"""

from app.services.user_service import UserService
from app.schemas.user import UserCreate, UserUpdate
from app.models.user import User, UserRole
from app.database import get_db
from sqlalchemy.orm import Session
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_user_creation_with_roles():
    """Probar creación de usuarios con diferentes roles"""

    db = next(get_db())
    user_service = UserService()

    try:
        print("🧪 Probando creación de usuarios con roles...")

        # Test usuarios con diferentes roles
        test_users = [
            {
                "email": "vendedor.test@empresa.com",
                "username": "vendedor_test",
                "full_name": "Vendedor Test",
                "password": "password123",
                "role": UserRole.SALES
            },
            {
                "email": "repartidor.test@empresa.com",
                "username": "repartidor_test",
                "full_name": "Repartidor Test",
                "password": "password123",
                "role": UserRole.DRIVER
            },
            {
                "email": "supervisor.test@empresa.com",
                "username": "supervisor_test",
                "full_name": "Supervisor Test",
                "password": "password123",
                "role": UserRole.SUPERVISOR
            }
        ]

        created_users = []

        for user_data in test_users:
            # Verificar si ya existe
            existing_user = user_service.get_user_by_email(
                db, user_data["email"])
            if existing_user:
                print(
                    f"⚠️  Usuario {user_data['email']} ya existe, actualizando rol...")
                # Actualizar rol si existe
                user_update = UserUpdate(role=user_data["role"])
                updated_user = user_service.update_user(
                    db, existing_user.id, user_update)
                created_users.append(updated_user)
                print(
                    f"✅ Usuario actualizado: {updated_user.full_name} → {updated_user.role.value}")
            else:
                # Crear nuevo usuario
                user_create = UserCreate(**user_data)
                new_user = user_service.create_user(db, user_create)
                created_users.append(new_user)
                print(
                    f"✅ Usuario creado: {new_user.full_name} → {new_user.role.value}")

        print(
            f"\n📊 Resumen: {len(created_users)} usuarios procesados exitosamente")

        # Mostrar todos los usuarios con roles
        all_users = user_service.get_users(db)
        print(f"\n👥 Usuarios en el sistema ({len(all_users)}):")
        for user in all_users:
            role_display = user.role.value if user.role else "sin_rol"
            superuser_display = " (SUPERUSER)" if user.is_superuser else ""
            print(
                f"   - {user.full_name} ({user.email}) → {role_display}{superuser_display}")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        db.close()


def test_role_updates():
    """Probar actualización de roles"""

    db = next(get_db())
    user_service = UserService()

    try:
        print("\n🔄 Probando actualización de roles...")

        # Buscar un usuario para actualizar
        test_user = user_service.get_user_by_email(
            db, "vendedor.test@empresa.com")
        if not test_user:
            print("❌ No se encontró usuario de prueba")
            return False

        original_role = test_user.role.value if test_user.role else "sin_rol"
        print(f"📋 Usuario actual: {test_user.full_name} → {original_role}")

        # Cambiar a MANAGER
        user_update = UserUpdate(role=UserRole.MANAGER)
        updated_user = user_service.update_user(db, test_user.id, user_update)

        if updated_user:
            new_role = updated_user.role.value
            print(f"✅ Rol actualizado: {original_role} → {new_role}")

            # Revertir cambio
            user_update = UserUpdate(role=UserRole.SALES)
            reverted_user = user_service.update_user(
                db, test_user.id, user_update)
            if reverted_user:
                print(
                    f"✅ Rol revertido: {new_role} → {reverted_user.role.value}")

            return True
        else:
            print("❌ No se pudo actualizar el rol")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        db.close()


def show_role_descriptions():
    """Mostrar descripciones de roles"""
    print("\n📋 Roles disponibles en el sistema:")

    role_descriptions = {
        UserRole.EMPLOYEE: "Empleado básico (almacén/producción)",
        UserRole.SALES: "Vendedor (pedidos y clientes)",
        UserRole.DRIVER: "Repartidor (entregas)",
        UserRole.SUPERVISOR: "Supervisor (aprobaciones)",
        UserRole.MANAGER: "Gerente (reportes y gestión)",
        UserRole.ADMIN: "Administrador (gestión completa del sistema)"
    }

    for role, description in role_descriptions.items():
        print(f"   🏷️  {role.value.upper()}: {description}")


if __name__ == "__main__":
    print("🚀 Test de Sistema de Usuarios y Roles")
    print("=" * 50)

    # Mostrar roles disponibles
    show_role_descriptions()

    # Probar creación/actualización de usuarios
    success1 = test_user_creation_with_roles()

    # Probar actualización de roles
    success2 = test_role_updates()

    print("\n" + "=" * 50)
    if success1 and success2:
        print("🎉 ¡Todos los tests pasaron exitosamente!")
        print("\n💡 Próximos pasos:")
        print("   1. Usa el endpoint POST /api/v1/users/ para crear usuarios")
        print(
            "   2. Usa POST /api/v1/users/{id}/assign-role para asignar roles")
        print("   3. Usa GET /api/v1/users/roles/available para ver roles disponibles")
        print("   4. Solo usuarios ADMIN pueden gestionar usuarios y roles")
    else:
        print("❌ Algunos tests fallaron")
        print("   Revisa los errores y la configuración de la base de datos")
