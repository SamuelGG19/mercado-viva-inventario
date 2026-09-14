import os


class Config:
    """Configuración base. Los valores se pueden sobrescribir con variables
    de entorno, lo que permite usar SQLite en local y Postgres/otro motor
    en la plataforma de publicación (Render, Railway, etc.)."""

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "sqlite:///" + os.path.join(os.path.dirname(__file__), "inventario.db")
    )
    # Render/Heroku entregan la URL como "postgres://", SQLAlchemy 2.x requiere "postgresql://"
    if SQLALCHEMY_DATABASE_URI.startswith("postgres://"):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace(
            "postgres://", "postgresql://", 1
        )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Clave simple para simular autenticación del actor "Administrador de tienda"
    # en los endpoints que modifican inventario manualmente.
    ADMIN_API_KEY = os.environ.get("ADMIN_API_KEY", "admin-viva-2026")

    # Minutos que dura una reserva de stock antes de liberarse automáticamente.
    MINUTOS_RESERVA = int(os.environ.get("MINUTOS_RESERVA", "15"))
