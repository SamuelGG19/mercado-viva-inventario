from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Producto(db.Model):
    """Representa un producto del catálogo digital de Mercado VIVA."""

    __tablename__ = "productos"

    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(20), unique=True, nullable=False)
    nombre = db.Column(db.String(120), nullable=False)
    categoria = db.Column(db.String(60), nullable=False)
    precio = db.Column(db.Float, nullable=False)

    # Unidades que un cliente puede reservar en este momento.
    stock_disponible = db.Column(db.Integer, nullable=False, default=0)
    # Unidades ya apartadas por reservas activas (aún no confirmadas).
    stock_reservado = db.Column(db.Integer, nullable=False, default=0)

    reservas = db.relationship("Reserva", backref="producto", lazy=True)

    def a_dict(self):
        return {
            "id": self.id,
            "sku": self.sku,
            "nombre": self.nombre,
            "categoria": self.categoria,
            "precio": self.precio,
            "stock_disponible": self.stock_disponible,
            "stock_reservado": self.stock_reservado,
            "stock_total": self.stock_disponible + self.stock_reservado,
        }


class Reserva(db.Model):
    """Representa la reserva temporal de inventario que se crea cuando un
    cliente agrega un producto al carrito de una compra digital."""

    __tablename__ = "reservas"

    ESTADOS = ("activa", "confirmada", "cancelada", "expirada")

    id = db.Column(db.Integer, primary_key=True)
    producto_id = db.Column(db.Integer, db.ForeignKey("productos.id"), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    estado = db.Column(db.String(20), nullable=False, default="activa")
    creada_en = db.Column(db.DateTime, default=datetime.utcnow)
    expira_en = db.Column(db.DateTime, nullable=False)

    def esta_expirada(self, ahora=None):
        ahora = ahora or datetime.utcnow()
        return self.estado == "activa" and self.expira_en < ahora

    def a_dict(self):
        ahora = datetime.utcnow()
        segundos_restantes = max(0, int((self.expira_en - ahora).total_seconds()))
        return {
            "id": self.id,
            "producto_id": self.producto_id,
            "producto_nombre": self.producto.nombre if self.producto else None,
            "cantidad": self.cantidad,
            "estado": self.estado,
            "creada_en": self.creada_en.isoformat() + "Z",
            "expira_en": self.expira_en.isoformat() + "Z",
            "segundos_restantes": segundos_restantes,
        }


def nueva_fecha_expiracion(minutos):
    return datetime.utcnow() + timedelta(minutes=minutos)
