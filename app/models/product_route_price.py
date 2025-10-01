from sqlalchemy import Column, Integer, Float, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from ..database import Base


class ProductRoutePrice(Base):
    __tablename__ = "product_route_prices"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    route_id = Column(Integer, ForeignKey("routes.id"), nullable=False)
    price = Column(Float, nullable=False)

    # Relationships
    product = relationship("Product", back_populates="route_prices")
    route = relationship("Route")

    # Ensure unique combination of product and route
    __table_args__ = (
        UniqueConstraint('product_id', 'route_id', name='_product_route_uc'),
    )


