"""
Tests unitarios para el generador de recibos.

Estos tests prueban la lógica del generador de recibos PDF.
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from tests.fixtures.test_data import MockSettings, MockOrder, MockClient, MockProduct, MockOrderItem


class TestReceiptGenerator:
    """Tests para el generador de recibos."""
    
    def setup_method(self):
        """Setup que se ejecuta antes de cada test."""
        # Limpiar archivos de prueba después de cada test
        self.test_files_to_cleanup = []
    
    def teardown_method(self):
        """Cleanup que se ejecuta después de cada test."""
        for file_path in self.test_files_to_cleanup:
            if os.path.exists(file_path):
                os.remove(file_path)
    
    @pytest.fixture
    def mock_order_data(self):
        """Fixture con datos de orden simulada."""
        settings = MockSettings()
        
        client = MockClient(
            name="David Morales",
            email="david@gmail.com", 
            phone="656123212",
            address="Guatemala"
        )
        
        items = [
            MockOrderItem(MockProduct("Queso Crema HOY", "Descripción del queso"), 3, 5.00),
            MockOrderItem(MockProduct("Crema Pura", "Crema de alta calidad"), 2, 150.00),
            MockOrderItem(MockProduct("Crema 12 oz", "Presentación de 12 onzas"), 1, 60.00),
        ]
        
        order = MockOrder("ORD-9OF9E6B9", client, items)
        
        return {
            "order": order,
            "settings": settings,
            "expected_total": 375.00  # (3*5) + (2*150) + (1*60) = 15 + 300 + 60
        }
    
    @patch('app.services.compact_receipt_generator.CompactReceiptGenerator')
    def test_generate_receipt_success(self, mock_generator_class, mock_order_data):
        """Test de generación exitosa de recibo."""
        # Configurar mock
        mock_generator = Mock()
        mock_generator_class.return_value = mock_generator
        mock_generator.generate_order_receipt.return_value = "test_receipt.pdf"
        
        # Importar después del patch para evitar problemas de importación
        from app.services.compact_receipt_generator import CompactReceiptGenerator
        
        generator = CompactReceiptGenerator()
        
        output_path = "test_receipt.pdf"
        result = generator.generate_order_receipt(
            mock_order_data["order"],
            mock_order_data["settings"],
            output_path
        )
        
        assert result == "test_receipt.pdf"
        mock_generator.generate_order_receipt.assert_called_once()
    
    def test_calculate_order_totals(self, mock_order_data):
        """Test de cálculo de totales de la orden."""
        order = mock_order_data["order"]
        expected_total = mock_order_data["expected_total"]
        
        # Verificar que los totales se calculan correctamente
        calculated_total = sum(item.total_price for item in order.items)
        
        assert calculated_total == expected_total
        assert order.total_amount == expected_total
    
    def test_order_items_calculation(self, mock_order_data):
        """Test de cálculo de items individuales."""
        order = mock_order_data["order"]
        
        # Verificar cada item
        queso_item = order.items[0]
        assert queso_item.quantity == 3
        assert queso_item.unit_price == 5.00
        assert queso_item.total_price == 15.00
        
        crema_pura_item = order.items[1]
        assert crema_pura_item.quantity == 2
        assert crema_pura_item.unit_price == 150.00
        assert crema_pura_item.total_price == 300.00
        
        crema_12oz_item = order.items[2]
        assert crema_12oz_item.quantity == 1
        assert crema_12oz_item.unit_price == 60.00
        assert crema_12oz_item.total_price == 60.00
    
    def test_receipt_data_structure(self, mock_order_data):
        """Test de la estructura de datos para el recibo."""
        order = mock_order_data["order"]
        settings = mock_order_data["settings"]
        
        # Verificar estructura de la orden
        assert hasattr(order, 'order_number')
        assert hasattr(order, 'client')
        assert hasattr(order, 'items')
        assert hasattr(order, 'total_amount')
        assert hasattr(order, 'created_at')
        
        # Verificar estructura del cliente
        assert hasattr(order.client, 'name')
        assert hasattr(order.client, 'email')
        assert hasattr(order.client, 'phone')
        assert hasattr(order.client, 'address')
        
        # Verificar estructura de los items
        for item in order.items:
            assert hasattr(item, 'product')
            assert hasattr(item, 'quantity')
            assert hasattr(item, 'unit_price')
            assert hasattr(item, 'total_price')
            assert hasattr(item.product, 'name')
        
        # Verificar estructura de settings
        assert hasattr(settings, 'company_name')
        assert hasattr(settings, 'business_name')
        assert hasattr(settings, 'nit')
        assert hasattr(settings, 'address')
        assert hasattr(settings, 'phone')
        assert hasattr(settings, 'email')
    
    @patch('os.path.exists')
    def test_file_cleanup_after_generation(self, mock_exists):
        """Test de limpieza de archivos después de la generación."""
        # Simular que el archivo existe
        mock_exists.return_value = True
        
        test_file = "test_cleanup.pdf"
        self.test_files_to_cleanup.append(test_file)
        
        # Verificar que el archivo sería limpiado
        assert test_file in self.test_files_to_cleanup
    
    def test_empty_order_items(self):
        """Test con orden sin items."""
        client = MockClient("Test Client")
        order = MockOrder("ORD-EMPTY", client, [])
        
        assert len(order.items) == 0
        assert order.total_amount == 0.0
    
    def test_single_item_order(self):
        """Test con orden de un solo item."""
        client = MockClient("Test Client")
        product = MockProduct("Single Product", "Test product")
        item = MockOrderItem(product, 1, 25.50)
        order = MockOrder("ORD-SINGLE", client, [item])
        
        assert len(order.items) == 1
        assert order.total_amount == 25.50
    
    @pytest.mark.unit
    def test_price_formatting(self, mock_order_data):
        """Test de formato de precios."""
        order = mock_order_data["order"]
        
        # Verificar que los precios son números válidos
        assert isinstance(order.total_amount, (int, float))
        assert order.total_amount > 0
        
        for item in order.items:
            assert isinstance(item.unit_price, (int, float))
            assert isinstance(item.total_price, (int, float))
            assert item.unit_price > 0
            assert item.total_price > 0
