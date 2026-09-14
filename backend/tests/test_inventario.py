"""
Pruebas del proceso 'Verificación de inventario para compras digitales'.

Ejecutar con:  pytest -v   (desde la carpeta backend/)

Incluye:
1) Caso feliz: reservar stock disponible.
2) Caso excepcional: reservar más unidades de las disponibles (debe fallar).
3) Caso feliz: confirmar una reserva descuenta el inventario definitivamente.
4) Caso adicional: cancelar una reserva libera el stock reservado.
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import crear_app
from config import Config
from models import db, Producto
from services import ErrorDeInventario, reservar_stock, confirmar_reserva, cancelar_reserva


class ConfigPrueba(Config):
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    TESTING = True
    MINUTOS_RESERVA = 15


@pytest.fixture
def app():
    aplicacion = crear_app(ConfigPrueba)
    with aplicacion.app_context():
        # Partimos de una base de datos limpia y controlada para cada prueba.
        db.drop_all()
        db.create_all()
        producto = Producto(
            sku="TEST-001",
            nombre="Producto de prueba",
            categoria="Test",
            precio=1000,
            stock_disponible=5,
            stock_reservado=0,
        )
        db.session.add(producto)
        db.session.commit()
        yield aplicacion


def test_reservar_stock_disponible_descuenta_inventario(app):
    """Caso feliz: al reservar 3 de 5 unidades, el disponible baja a 2
    y el reservado sube a 3."""
    with app.app_context():
        producto = Producto.query.first()
        reserva = reservar_stock(producto.id, 3, minutos_reserva=15)

        assert reserva.estado == "activa"
        assert reserva.cantidad == 3
        producto_actualizado = Producto.query.get(producto.id)
        assert producto_actualizado.stock_disponible == 2
        assert producto_actualizado.stock_reservado == 3


def test_reservar_mas_stock_del_disponible_lanza_error(app):
    """Caso EXCEPCIONAL: pedir más unidades de las que hay disponibles
    debe rechazarse con ErrorDeInventario y no debe alterar el stock."""
    with app.app_context():
        producto = Producto.query.first()

        with pytest.raises(ErrorDeInventario) as info:
            reservar_stock(producto.id, 999, minutos_reserva=15)

        assert info.value.codigo_http == 409
        # El stock no debe haberse modificado tras el intento fallido.
        producto_sin_cambios = Producto.query.get(producto.id)
        assert producto_sin_cambios.stock_disponible == 5
        assert producto_sin_cambios.stock_reservado == 0


def test_confirmar_reserva_descuenta_definitivamente(app):
    """Al confirmar la compra, el stock reservado desaparece (se vendió)
    y el disponible NO se recupera."""
    with app.app_context():
        producto = Producto.query.first()
        reserva = reservar_stock(producto.id, 2, minutos_reserva=15)

        confirmada = confirmar_reserva(reserva.id)

        assert confirmada.estado == "confirmada"
        producto_final = Producto.query.get(producto.id)
        assert producto_final.stock_disponible == 3  # 5 - 2
        assert producto_final.stock_reservado == 0  # ya se confirmó la venta


def test_cancelar_reserva_libera_stock_disponible(app):
    """Al cancelar una reserva activa, las unidades vuelven a estar
    disponibles para otros clientes."""
    with app.app_context():
        producto = Producto.query.first()
        reserva = reservar_stock(producto.id, 4, minutos_reserva=15)

        cancelada = cancelar_reserva(reserva.id)

        assert cancelada.estado == "cancelada"
        producto_final = Producto.query.get(producto.id)
        assert producto_final.stock_disponible == 5
        assert producto_final.stock_reservado == 0
