"""
Mercado VIVA · MVP de Verificación de inventario para compras digitales
--------------------------------------------------------------------
Backend en Flask que expone una API REST consumida por el frontend
(HTML/CSS/JS) para consultar disponibilidad de productos, reservar stock
al agregar al carrito, y confirmar o cancelar una compra digital.
"""
from functools import wraps
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from config import Config
from models import db, Producto, Reserva
from seed import sembrar_datos
from services import (
    ErrorDeInventario,
    consultar_disponibilidad,
    reservar_stock,
    confirmar_reserva,
    cancelar_reserva,
    actualizar_stock_admin,
    liberar_reservas_expiradas,
)

FRONTEND_DIR = "../frontend"


def crear_app(config_class=Config):
    app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")
    app.config.from_object(config_class)
    CORS(app)
    db.init_app(app)

    with app.app_context():
        db.create_all()
        sembrar_datos(db)

    registrar_rutas(app)
    return app


# ---------------------------------------------------------------------------
# Autenticación básica para el actor "Administrador de tienda"
# ---------------------------------------------------------------------------
def requiere_api_key(f):
    @wraps(f)
    def decorado(*args, **kwargs):
        clave = request.headers.get("X-API-Key")
        from flask import current_app

        if clave != current_app.config["ADMIN_API_KEY"]:
            return jsonify(error="No autorizado. Se requiere X-API-Key válida."), 401
        return f(*args, **kwargs)

    return decorado


def registrar_rutas(app):

    @app.errorhandler(ErrorDeInventario)
    def manejar_error_negocio(err):
        return jsonify(error=err.mensaje), err.codigo_http

    @app.errorhandler(404)
    def manejar_404(err):
        return jsonify(error="Recurso no encontrado."), 404

    @app.errorhandler(400)
    def manejar_400(err):
        return jsonify(error="Solicitud inválida. Revisa el formato del JSON enviado."), 400

    @app.errorhandler(500)
    def manejar_500(err):
        return jsonify(error="Error interno del servidor."), 500

    # -- Frontend estático -------------------------------------------------
    @app.route("/")
    def servir_index():
        return send_from_directory(app.static_folder, "index.html")

    # -- Salud del servicio --------------------------------------------------
    @app.get("/api/salud")
    def salud():
        return jsonify(estado="ok", servicio="inventario-mercado-viva")

    # -- Catálogo / consulta de disponibilidad -----------------------------
    @app.get("/api/productos")
    def listar_productos():
        liberar_reservas_expiradas()
        busqueda = request.args.get("q", "").strip().lower()
        query = Producto.query
        if busqueda:
            query = query.filter(Producto.nombre.ilike(f"%{busqueda}%"))
        productos = query.order_by(Producto.categoria, Producto.nombre).all()
        return jsonify([p.a_dict() for p in productos])

    @app.get("/api/productos/<int:producto_id>/disponibilidad")
    def ver_disponibilidad(producto_id):
        producto = consultar_disponibilidad(producto_id)
        return jsonify(producto.a_dict())

    # -- Reservas (carrito de compra digital) -------------------------------
    @app.post("/api/reservas")
    def crear_reserva():
        datos = request.get_json(silent=True) or {}
        producto_id = datos.get("producto_id")
        cantidad = datos.get("cantidad")

        if not isinstance(producto_id, int):
            raise ErrorDeInventario("Debes indicar 'producto_id' (entero).", 400)
        if not isinstance(cantidad, int):
            raise ErrorDeInventario("Debes indicar 'cantidad' (entero).", 400)

        from flask import current_app

        reserva = reservar_stock(
            producto_id, cantidad, current_app.config["MINUTOS_RESERVA"]
        )
        return jsonify(reserva.a_dict()), 201

    @app.get("/api/reservas")
    def listar_reservas():
        liberar_reservas_expiradas()
        reservas = Reserva.query.order_by(Reserva.creada_en.desc()).all()
        return jsonify([r.a_dict() for r in reservas])

    @app.post("/api/reservas/<int:reserva_id>/confirmar")
    def confirmar(reserva_id):
        reserva = confirmar_reserva(reserva_id)
        return jsonify(reserva.a_dict())

    @app.post("/api/reservas/<int:reserva_id>/cancelar")
    def cancelar(reserva_id):
        reserva = cancelar_reserva(reserva_id)
        return jsonify(reserva.a_dict())

    # -- Administración de stock (actor: Administrador de tienda) ----------
    @app.post("/api/admin/productos/<int:producto_id>/stock")
    @requiere_api_key
    def actualizar_stock(producto_id):
        datos = request.get_json(silent=True) or {}
        nuevo_stock = datos.get("stock_disponible")
        if not isinstance(nuevo_stock, int):
            raise ErrorDeInventario("Debes indicar 'stock_disponible' (entero).", 400)
        producto = actualizar_stock_admin(producto_id, nuevo_stock)
        return jsonify(producto.a_dict())


app = crear_app()

if __name__ == "__main__":
    import os

    puerto = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=puerto, debug=True)
