"""Servicio de inventario: contiene toda la lógica de negocio del proceso
'Verificación de inventario para compras digitales'. Se mantiene separado
de las rutas HTTP (app.py) para que las reglas de negocio sean reutilizables
y fáciles de probar (ver tests/test_inventario.py).
"""
from datetime import datetime

from models import db, Producto, Reserva, nueva_fecha_expiracion


class ErrorDeInventario(Exception):
    """Excepción de negocio: se traduce a una respuesta HTTP 4xx en app.py."""

    def __init__(self, mensaje, codigo_http=400):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.codigo_http = codigo_http


def liberar_reservas_expiradas():
    """Regla de negocio: toda reserva 'activa' cuyo tiempo expiró debe
    devolver sus unidades al stock disponible automáticamente.
    Se ejecuta de forma perezosa antes de cada consulta/operación relevante,
    lo cual es suficiente para el alcance de este MVP."""
    ahora = datetime.utcnow()
    expiradas = Reserva.query.filter(
        Reserva.estado == "activa", Reserva.expira_en < ahora
    ).all()
    for reserva in expiradas:
        reserva.producto.stock_disponible += reserva.cantidad
        reserva.producto.stock_reservado -= reserva.cantidad
        reserva.estado = "expirada"
    if expiradas:
        db.session.commit()
    return len(expiradas)


def consultar_disponibilidad(producto_id):
    liberar_reservas_expiradas()
    producto = Producto.query.get(producto_id)
    if producto is None:
        raise ErrorDeInventario("El producto no existe.", 404)
    return producto


def reservar_stock(producto_id, cantidad, minutos_reserva):
    """Reserva 'cantidad' unidades de un producto para una compra digital.

    Reglas de negocio aplicadas:
    - La cantidad debe ser un entero positivo.
    - No se puede reservar más unidades que el stock disponible actual.
    - El stock nunca puede quedar en un valor negativo.
    """
    liberar_reservas_expiradas()

    if not isinstance(cantidad, int) or cantidad <= 0:
        raise ErrorDeInventario("La cantidad debe ser un entero mayor a cero.", 400)

    producto = Producto.query.get(producto_id)
    if producto is None:
        raise ErrorDeInventario("El producto no existe.", 404)

    if cantidad > producto.stock_disponible:
        raise ErrorDeInventario(
            f"Stock insuficiente para '{producto.nombre}'. "
            f"Disponible: {producto.stock_disponible}, solicitado: {cantidad}.",
            409,
        )

    producto.stock_disponible -= cantidad
    producto.stock_reservado += cantidad

    reserva = Reserva(
        producto_id=producto.id,
        cantidad=cantidad,
        estado="activa",
        expira_en=nueva_fecha_expiracion(minutos_reserva),
    )
    db.session.add(reserva)
    db.session.commit()
    return reserva


def confirmar_reserva(reserva_id):
    """Confirma la compra de una reserva activa y vigente, descontando
    definitivamente el inventario reservado."""
    liberar_reservas_expiradas()

    reserva = Reserva.query.get(reserva_id)
    if reserva is None:
        raise ErrorDeInventario("La reserva no existe.", 404)

    if reserva.estado != "activa":
        raise ErrorDeInventario(
            f"La reserva no puede confirmarse porque su estado es '{reserva.estado}'.",
            409,
        )

    reserva.producto.stock_reservado -= reserva.cantidad
    reserva.estado = "confirmada"
    db.session.commit()
    return reserva


def cancelar_reserva(reserva_id):
    """Cancela una reserva activa y libera las unidades al stock disponible."""
    liberar_reservas_expiradas()

    reserva = Reserva.query.get(reserva_id)
    if reserva is None:
        raise ErrorDeInventario("La reserva no existe.", 404)

    if reserva.estado != "activa":
        raise ErrorDeInventario(
            f"La reserva no puede cancelarse porque su estado es '{reserva.estado}'.",
            409,
        )

    reserva.producto.stock_disponible += reserva.cantidad
    reserva.producto.stock_reservado -= reserva.cantidad
    reserva.estado = "cancelada"
    db.session.commit()
    return reserva


def actualizar_stock_admin(producto_id, nuevo_stock):
    """Permite al actor 'Administrador de tienda' corregir el stock físico
    disponible de un producto (por ejemplo tras un conteo de bodega)."""
    if not isinstance(nuevo_stock, int) or nuevo_stock < 0:
        raise ErrorDeInventario("El stock debe ser un entero mayor o igual a cero.", 400)

    producto = Producto.query.get(producto_id)
    if producto is None:
        raise ErrorDeInventario("El producto no existe.", 404)

    producto.stock_disponible = nuevo_stock
    db.session.commit()
    return producto
