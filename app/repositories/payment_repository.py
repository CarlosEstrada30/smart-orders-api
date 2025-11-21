from typing import Optional, List, Union
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, func
from datetime import datetime, date
from .base import BaseRepository
from ..models.payment import Payment, PaymentStatus
from ..schemas.payment import PaymentCreate


class PaymentRepository(BaseRepository[Payment, PaymentCreate, dict]):
    def __init__(self):
        super().__init__(Payment)

    def get_by_payment_number(
        self,
        db: Session,
        *,
        payment_number: str
    ) -> Optional[Payment]:
        """Obtener pago por número de pago"""
        return db.query(Payment).options(
            joinedload(Payment.order),
            joinedload(Payment.created_by)
        ).filter(Payment.payment_number == payment_number).first()

    def get_payments_by_order(
        self,
        db: Session,
        *,
        order_id: int,
        only_confirmed: bool = True
    ) -> List[Payment]:
        """Obtener todos los pagos de una orden"""
        query = db.query(Payment).options(
            joinedload(Payment.order),
            joinedload(Payment.created_by)
        ).filter(Payment.order_id == order_id)

        if only_confirmed:
            query = query.filter(Payment.status == PaymentStatus.CONFIRMED)

        return query.order_by(Payment.payment_date.desc()).all()

    def get_multi(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        only_confirmed: bool = True
    ) -> List[Payment]:
        """Obtener múltiples pagos con filtro opcional de confirmados"""
        query = db.query(Payment).options(
            joinedload(Payment.order),
            joinedload(Payment.created_by)
        )

        if only_confirmed:
            query = query.filter(Payment.status == PaymentStatus.CONFIRMED)

        return query.order_by(Payment.payment_date.desc()).offset(skip).limit(limit).all()

    def get(
        self,
        db: Session,
        id: int
    ) -> Optional[Payment]:
        """Obtener pago por ID"""
        return db.query(Payment).options(
            joinedload(Payment.order),
            joinedload(Payment.created_by)
        ).filter(Payment.id == id).first()

    def create_payment(
        self,
        db: Session,
        *,
        payment_data: PaymentCreate,
        created_by_user_id: Optional[int] = None
    ) -> Payment:
        """Crear nuevo pago con número único"""
        import uuid

        # Generate unique payment number
        payment_number = f"PAY-{uuid.uuid4().hex[:8].upper()}"

        # Create payment
        payment = Payment(
            payment_number=payment_number,
            order_id=payment_data.order_id,
            amount=payment_data.amount,
            payment_method=payment_data.payment_method,
            status=PaymentStatus.CONFIRMED,  # Por defecto es CONFIRMED
            notes=payment_data.notes,
            created_by_user_id=created_by_user_id
        )
        db.add(payment)
        db.flush()  # Get the payment ID

        db.commit()
        db.refresh(payment)

        # Load relationships
        return payment

    def cancel_payment(
        self,
        db: Session,
        *,
        payment_id: int
    ) -> Optional[Payment]:
        """Cancelar un pago (cambiar status a CANCELLED)"""
        payment = self.get(db, payment_id)
        if payment and payment.status == PaymentStatus.CONFIRMED:
            payment.status = PaymentStatus.CANCELLED
            db.commit()
            db.refresh(payment)
            return payment
        return None

    def get_payments_with_filters(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        order_id: Optional[int] = None,
        payment_method: Optional[str] = None,
        status: Optional[PaymentStatus] = None,
        date_from: Optional[Union[date, datetime]] = None,
        date_to: Optional[Union[date, datetime]] = None,
        only_confirmed: bool = True
    ) -> List[Payment]:
        """Obtener pagos con filtros opcionales"""
        query = db.query(Payment).options(
            joinedload(Payment.order),
            joinedload(Payment.created_by)
        )

        # Build filters
        filters = []

        if order_id is not None:
            filters.append(Payment.order_id == order_id)

        if payment_method is not None:
            filters.append(Payment.payment_method == payment_method)

        if status is not None:
            filters.append(Payment.status == status)
        elif only_confirmed:
            filters.append(Payment.status == PaymentStatus.CONFIRMED)

        if date_from is not None:
            if isinstance(date_from, date):
                filters.append(
                    Payment.payment_date >= datetime.combine(
                        date_from, datetime.min.time())
                )
            else:
                filters.append(Payment.payment_date >= date_from)

        if date_to is not None:
            if isinstance(date_to, date):
                filters.append(
                    Payment.payment_date <= datetime.combine(
                        date_to, datetime.max.time())
                )
            else:
                filters.append(Payment.payment_date <= date_to)

        # Apply filters
        if filters:
            query = query.filter(and_(*filters))

        return query.order_by(Payment.payment_date.desc()).offset(skip).limit(limit).all()

    def calculate_order_payment_summary(
        self,
        db: Session,
        *,
        order_id: int
    ) -> dict:
        """Calcular resumen de pagos de una orden (solo pagos confirmados)"""
        result = db.query(
            func.sum(Payment.amount).label('total_paid'),
            func.count(Payment.id).label('payment_count')
        ).filter(
            Payment.order_id == order_id,
            Payment.status == PaymentStatus.CONFIRMED
        ).first()

        total_paid = float(result.total_paid or 0.0)
        payment_count = int(result.payment_count or 0)

        return {
            'total_paid': total_paid,
            'payment_count': payment_count
        }
