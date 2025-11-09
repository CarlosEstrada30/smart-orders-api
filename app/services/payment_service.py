from typing import Optional, List, Union
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy.orm import Session
from ..repositories.payment_repository import PaymentRepository
from ..repositories.order_repository import OrderRepository
from ..schemas.payment import (
    PaymentCreate, PaymentResponse, OrderPaymentSummary
)
from ..models.payment import Payment, PaymentStatus, OrderPaymentStatus
from ..models.order import Order


class PaymentService:
    def __init__(self):
        self.payment_repository = PaymentRepository()
        self.order_repository = OrderRepository()

    def _process_payment_response(self, payment: Payment) -> PaymentResponse:
        """Procesar pago y crear respuesta con datos completos"""
        payment_data = {
            "id": payment.id,
            "payment_number": payment.payment_number,
            "order_id": payment.order_id,
            "amount": float(payment.amount),
            "payment_method": payment.payment_method,
            "status": payment.status,
            "payment_date": payment.payment_date,
            "notes": payment.notes,
            "created_by_user_id": payment.created_by_user_id,
            "created_at": payment.created_at,
            "updated_at": payment.updated_at
        }
        return PaymentResponse(**payment_data)

    def _calculate_order_balance(self, db: Session, order: Order) -> dict:
        """Calcular saldo pendiente de una orden (solo pagos confirmados)"""
        summary = self.payment_repository.calculate_order_payment_summary(
            db, order_id=order.id
        )

        total_paid = summary['total_paid']
        total_amount = float(order.total_amount)
        balance_due = total_amount - total_paid

        return {
            'paid_amount': total_paid,
            'balance_due': balance_due
        }

    def _update_order_payment_status(
        self,
        db: Session,
        order: Order
    ) -> OrderPaymentStatus:
        """Actualizar estado de pago de una orden basado en los pagos"""
        balance_info = self._calculate_order_balance(db, order)

        paid_amount = balance_info['paid_amount']
        balance_due = balance_info['balance_due']
        total_amount = float(order.total_amount)

        # Determinar estado de pago
        if balance_due <= 0:
            payment_status = OrderPaymentStatus.PAID
        elif paid_amount > 0 and balance_due > 0:
            payment_status = OrderPaymentStatus.PARTIAL
        else:
            payment_status = OrderPaymentStatus.UNPAID

        # Actualizar campos en la orden
        order.paid_amount = Decimal(str(paid_amount))
        order.balance_due = Decimal(str(balance_due))
        order.payment_status = payment_status

        db.commit()
        db.refresh(order)

        return payment_status

    def _validate_payment_amount(
        self,
        db: Session,
        order: Order,
        payment_amount: float
    ) -> bool:
        """Validar que el monto del pago no exceda el saldo pendiente"""
        balance_info = self._calculate_order_balance(db, order)
        balance_due = balance_info['balance_due']

        # Permitir pagos hasta el saldo pendiente
        # Si el pago es mayor, se considerará como overpayment (se manejará como PAID)
        return payment_amount > 0

    def _validate_order_for_payment(
        self,
        db: Session,
        order_id: int
    ) -> Order:
        """Validar que la orden existe y está activa"""
        order = self.order_repository.get(db, order_id)
        if not order:
            raise ValueError("Orden no encontrada")

        # No permitir pagos para órdenes canceladas
        from ..models.order import OrderStatus
        if order.status == OrderStatus.CANCELLED:
            raise ValueError("No se pueden registrar pagos para órdenes canceladas")

        return order

    def create_payment(
        self,
        db: Session,
        payment_data: PaymentCreate,
        created_by_user_id: Optional[int] = None
    ) -> PaymentResponse:
        """Crear pago y actualizar orden automáticamente"""
        # Validar orden
        order = self._validate_order_for_payment(db, payment_data.order_id)

        # Validar monto del pago
        if not self._validate_payment_amount(db, order, payment_data.amount):
            raise ValueError("El monto del pago debe ser mayor a 0")

        # Crear pago (status=CONFIRMED por defecto)
        payment = self.payment_repository.create_payment(
            db,
            payment_data=payment_data,
            created_by_user_id=created_by_user_id
        )

        # Actualizar orden: recalcular paid_amount, balance_due y payment_status
        self._update_order_payment_status(db, order)

        return self._process_payment_response(payment)

    def get_payment(
        self,
        db: Session,
        payment_id: int
    ) -> Optional[PaymentResponse]:
        """Obtener pago por ID"""
        payment = self.payment_repository.get(db, payment_id)
        if not payment:
            return None
        return self._process_payment_response(payment)

    def get_payment_by_number(
        self,
        db: Session,
        payment_number: str
    ) -> Optional[PaymentResponse]:
        """Obtener pago por número de pago"""
        payment = self.payment_repository.get_by_payment_number(
            db, payment_number=payment_number
        )
        if not payment:
            return None
        return self._process_payment_response(payment)

    def get_payments_by_order(
        self,
        db: Session,
        order_id: int,
        only_confirmed: bool = True
    ) -> List[PaymentResponse]:
        """Obtener todos los pagos de una orden"""
        payments = self.payment_repository.get_payments_by_order(
            db,
            order_id=order_id,
            only_confirmed=only_confirmed
        )
        return [self._process_payment_response(payment) for payment in payments]

    def get_payments(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100,
        only_confirmed: bool = True
    ) -> List[PaymentResponse]:
        """Obtener múltiples pagos"""
        payments = self.payment_repository.get_multi(
            db,
            skip=skip,
            limit=limit,
            only_confirmed=only_confirmed
        )
        return [self._process_payment_response(payment) for payment in payments]

    def get_payments_with_filters(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100,
        order_id: Optional[int] = None,
        payment_method: Optional[str] = None,
        status: Optional[PaymentStatus] = None,
        date_from: Optional[Union[date, datetime]] = None,
        date_to: Optional[Union[date, datetime]] = None,
        only_confirmed: bool = True
    ) -> List[PaymentResponse]:
        """Obtener pagos con filtros"""
        payments = self.payment_repository.get_payments_with_filters(
            db,
            skip=skip,
            limit=limit,
            order_id=order_id,
            payment_method=payment_method,
            status=status,
            date_from=date_from,
            date_to=date_to,
            only_confirmed=only_confirmed
        )
        return [self._process_payment_response(payment) for payment in payments]

    def cancel_payment(
        self,
        db: Session,
        payment_id: int
    ) -> Optional[PaymentResponse]:
        """Cancelar pago y recalcular orden"""
        # Obtener pago
        payment = self.payment_repository.get(db, payment_id)
        if not payment:
            return None

        # Validar que el pago está confirmado
        if payment.status != PaymentStatus.CONFIRMED:
            raise ValueError("Solo se pueden cancelar pagos confirmados")

        # Cancelar pago
        cancelled_payment = self.payment_repository.cancel_payment(
            db, payment_id=payment_id
        )
        if not cancelled_payment:
            return None

        # Obtener orden y recalcular
        order = self.order_repository.get(db, payment.order_id)
        if order:
            self._update_order_payment_status(db, order)

        return self._process_payment_response(cancelled_payment)

    def get_order_payment_summary(
        self,
        db: Session,
        order_id: int
    ) -> Optional[OrderPaymentSummary]:
        """Obtener resumen completo de pagos de una orden"""
        # Obtener orden
        order = self.order_repository.get(db, order_id)
        if not order:
            return None

        # Obtener pagos confirmados
        payments = self.get_payments_by_order(db, order_id, only_confirmed=True)

        # Calcular resumen
        balance_info = self._calculate_order_balance(db, order)

        return OrderPaymentSummary(
            order_id=order.id,
            order_number=order.order_number,
            total_amount=float(order.total_amount),
            paid_amount=balance_info['paid_amount'],
            balance_due=balance_info['balance_due'],
            payment_status=order.payment_status or OrderPaymentStatus.UNPAID,
            payment_count=len(payments),
            payments=payments
        )

    def calculate_order_balance(
        self,
        db: Session,
        order_id: int
    ) -> dict:
        """Calcular saldo pendiente de una orden"""
        order = self.order_repository.get(db, order_id)
        if not order:
            raise ValueError("Orden no encontrada")

        return self._calculate_order_balance(db, order)

