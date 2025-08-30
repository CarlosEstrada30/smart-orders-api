#!/usr/bin/env python3
"""
Script para agregar roles a usuarios existentes
Usar después de agregar la columna 'role' al modelo User
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.database import engine, get_db
from app.models.user import User, UserRole


def assign_roles():
    """Asignar roles a usuarios existentes"""
    
    db = next(get_db())
    
    try:
        # Obtener todos los usuarios
        users = db.query(User).all()
        
        if not users:
            print("❌ No se encontraron usuarios en la base de datos")
            return
        
        print(f"📋 Encontrados {len(users)} usuarios")
        print("\n🔧 Asignando roles...")
        
        for user in users:
            # Si ya tiene rol, no cambiar
            if user.role:
                print(f"✅ {user.full_name} ({user.email}) ya tiene rol: {user.role.value}")
                continue
            
            # Lógica para asignar roles basada en is_superuser
            if user.is_superuser:
                user.role = UserRole.ADMIN
                print(f"👨‍💻 {user.full_name} ({user.email}) → ADMIN (era superuser)")
            else:
                # Por defecto, usuarios normales son EMPLOYEE
                user.role = UserRole.EMPLOYEE
                print(f"👷 {user.full_name} ({user.email}) → EMPLOYEE")
        
        # Guardar cambios
        db.commit()
        print("\n✅ Roles asignados correctamente!")
        
        # Mostrar resumen
        print("\n📊 Resumen de roles:")
        role_counts = {}
        for user in users:
            role = user.role.value
            role_counts[role] = role_counts.get(role, 0) + 1
        
        for role, count in role_counts.items():
            print(f"   - {role.upper()}: {count} usuarios")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()


def create_sample_users():
    """Crear usuarios de ejemplo para cada rol"""
    
    db = next(get_db())
    
    try:
        # Usuarios de ejemplo
        sample_users = [
            {
                "email": "admin@empresa.com",
                "username": "admin",
                "full_name": "Administrador Sistema",
                "role": UserRole.ADMIN,
                "is_superuser": True
            },
            {
                "email": "gerente@empresa.com", 
                "username": "gerente",
                "full_name": "Juan Pérez - Gerente",
                "role": UserRole.MANAGER,
                "is_superuser": False
            },
            {
                "email": "supervisor@empresa.com",
                "username": "supervisor", 
                "full_name": "María García - Supervisora",
                "role": UserRole.SUPERVISOR,
                "is_superuser": False
            },
            {
                "email": "vendedor@empresa.com",
                "username": "vendedor",
                "full_name": "Ana Rodríguez - Vendedora",
                "role": UserRole.SALES,
                "is_superuser": False
            },
            {
                "email": "repartidor@empresa.com",
                "username": "repartidor",
                "full_name": "José Martínez - Repartidor",
                "role": UserRole.DRIVER,
                "is_superuser": False
            },
            {
                "email": "empleado@empresa.com",
                "username": "empleado",
                "full_name": "Carlos López - Empleado",
                "role": UserRole.EMPLOYEE,
                "is_superuser": False
            }
        ]
        
        print("👥 Creando usuarios de ejemplo...")
        
        for user_data in sample_users:
            # Verificar si ya existe
            existing_user = db.query(User).filter(User.email == user_data["email"]).first()
            if existing_user:
                print(f"⚠️  Usuario {user_data['email']} ya existe")
                continue
            
            # Crear usuario (necesitarías un servicio para hashear la contraseña)
            # Por ahora solo mostramos lo que se crearía
            print(f"➕ Se crearía: {user_data['full_name']} ({user_data['role'].value})")
        
        print("\n💡 Para crear estos usuarios, usa el endpoint de registro o un script específico")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    print("🚀 Configurando roles de usuario")
    print("=" * 50)
    
    print("\n1. Asignando roles a usuarios existentes...")
    assign_roles()
    
    print("\n" + "=" * 50)
    print("2. Mostrando usuarios de ejemplo que podrías crear...")
    create_sample_users()
    
    print("\n🎉 ¡Proceso completado!")
    print("\n📝 Próximos pasos:")
    print("   1. Crear usuarios para cada rol según tu empresa")
    print("   2. Probar los endpoints con diferentes roles")
    print("   3. Verificar permisos en el frontend")
