# -*- coding: utf-8 -*-
"""
Factories para testing.

Este archivo contiene todos los factories necesarios para crear
objetos de prueba en los tests.

Uso:
    from tests.factories import ClientFactory, ProductFactory

    # En tu test con el fixture factories:
    def test_something(self, factories, db_session):
        client = factories.ClientFactory.create(name="Test Client")
"""

import factory
from faker import Faker
from app.models.client import Client
from app.models.product import Product
from app.models.route import Route
from app.models.order import Order, OrderItem, OrderStatus
from app.models.user import User, UserRole

faker = Faker('es_ES')


class ClientFactory(factory.alchemy.SQLAlchemyModelFactory):
    """Factory para crear clientes de prueba."""

    class Meta:
        model = Client
        sqlalchemy_session_persistence = "commit"

    name = factory.LazyAttribute(lambda _: faker.company())
    email = factory.LazyAttribute(lambda _: faker.email())
    phone = factory.LazyAttribute(lambda _: faker.phone_number())
    address = factory.LazyAttribute(lambda _: faker.address())
    nit = factory.LazyAttribute(lambda _: faker.bothify(text='########-#'))
    is_active = True


class ProductFactory(factory.alchemy.SQLAlchemyModelFactory):
    """Factory para crear productos de prueba."""

    class Meta:
        model = Product
        sqlalchemy_session_persistence = "commit"

    name = factory.LazyAttribute(lambda _: faker.word().capitalize())
    description = factory.LazyAttribute(lambda _: faker.text(max_nb_chars=200))
    price = factory.LazyAttribute(
        lambda _: round(
            faker.random.uniform(
                10, 1000), 2))
    stock = factory.LazyAttribute(lambda _: faker.random_int(min=0, max=100))
    sku = factory.LazyAttribute(lambda _: faker.bothify(text='SKU-????-####'))
    is_active = True


class RouteFactory(factory.alchemy.SQLAlchemyModelFactory):
    """Factory para crear rutas de prueba."""

    class Meta:
        model = Route
        sqlalchemy_session_persistence = "commit"

    name = factory.Sequence(lambda n: f"Ruta {n}")
    is_active = True


class UserFactory(factory.alchemy.SQLAlchemyModelFactory):
    """Factory para crear usuarios de prueba."""

    class Meta:
        model = User
        sqlalchemy_session_persistence = "commit"

    username = factory.LazyAttribute(lambda _: faker.user_name())
    email = factory.LazyAttribute(lambda _: faker.email())
    full_name = factory.LazyAttribute(lambda _: faker.name())
    hashed_password = factory.LazyAttribute(
        lambda _: "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqYqYqYqYq"  # password: "test"
    )
    role = UserRole.EMPLOYEE
    is_active = True
    is_superuser = False


class OrderFactory(factory.alchemy.SQLAlchemyModelFactory):
    """Factory para crear órdenes de prueba."""

    class Meta:
        model = Order
        sqlalchemy_session_persistence = "commit"

    order_number = factory.LazyAttribute(
        lambda _: faker.bothify(text='ORD-########'))
    client = factory.SubFactory(ClientFactory)
    route = factory.SubFactory(RouteFactory)
    status = OrderStatus.PENDING
    total_amount = factory.LazyAttribute(
        lambda _: round(
            faker.random.uniform(
                100, 5000), 2))
    discount_amount = 0.0
    notes = factory.LazyAttribute(lambda _: faker.text(max_nb_chars=100))


class OrderItemFactory(factory.alchemy.SQLAlchemyModelFactory):
    """Factory para crear items de orden de prueba."""

    class Meta:
        model = OrderItem
        sqlalchemy_session_persistence = "commit"

    order = factory.SubFactory(OrderFactory)
    product = factory.SubFactory(ProductFactory)
    quantity = factory.LazyAttribute(lambda _: faker.random_int(min=1, max=10))
    unit_price = factory.LazyAttribute(
        lambda _: round(
            faker.random.uniform(
                10, 500), 2))
    subtotal = factory.LazyAttribute(lambda obj: obj.quantity * obj.unit_price)


def configure_factories(session):
    """
    Configura todos los factories para usar la sesión proporcionada.

    Args:
        session: SQLAlchemy session a usar
    """
    factories = [
        ClientFactory,
        ProductFactory,
        RouteFactory,
        UserFactory,
        OrderFactory,
        OrderItemFactory,
    ]

    for factory_class in factories:
        factory_class._meta.sqlalchemy_session = session
