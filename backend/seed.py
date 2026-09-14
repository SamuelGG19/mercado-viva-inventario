from models import Producto

PRODUCTOS_INICIALES = [
    dict(sku="VIVA-001", nombre="Leche entera 1L", categoria="Lácteos", precio=4200, stock_disponible=40),
    dict(sku="VIVA-002", nombre="Arroz premium 1kg", categoria="Abarrotes", precio=5300, stock_disponible=60),
    dict(sku="VIVA-003", nombre="Aguacate hass (und)", categoria="Frutas y verduras", precio=1800, stock_disponible=8),
    dict(sku="VIVA-004", nombre="Pechuga de pollo 1kg", categoria="Carnes", precio=14900, stock_disponible=15),
    dict(sku="VIVA-005", nombre="Papel higiénico x12", categoria="Aseo hogar", precio=23500, stock_disponible=0),
    dict(sku="VIVA-006", nombre="Café molido 500g", categoria="Abarrotes", precio=17800, stock_disponible=25),
    dict(sku="VIVA-007", nombre="Detergente líquido 3L", categoria="Aseo hogar", precio=28900, stock_disponible=3),
    dict(sku="VIVA-008", nombre="Manzana verde x kg", categoria="Frutas y verduras", precio=6200, stock_disponible=20),
]


def sembrar_datos(db):
    if Producto.query.first():
        return  # ya hay datos, no duplicar
    for datos in PRODUCTOS_INICIALES:
        db.session.add(Producto(**datos))
    db.session.commit()
