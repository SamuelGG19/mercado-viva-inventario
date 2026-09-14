# Mercado VIVA — MVP: Verificación de inventario para compras digitales

MVP del proceso **"Verificación de inventario para compras digitales"**
del taller de arquitectura e implementación de Mercado VIVA.

## 1. Proceso

**Problema concreto:** los clientes agregan productos a su carrito digital
sin saber si realmente hay unidades disponibles, lo que genera pedidos
cancelados y mala experiencia cuando el stock mostrado no coincide con el
inventario real.

**Actores:**
- **Cliente:** navega el catálogo digital y reserva productos para comprar.
- **Sistema de inventario (backend):** valida y controla la disponibilidad.
- **Administrador de tienda:** corrige el stock disponible cuando hay
  diferencias con el inventario físico.

**Inicio del proceso:** el cliente busca o navega un producto en el
catálogo digital.
**Fin del proceso:** el cliente confirma la compra (se descuenta el stock
de forma definitiva) o la reserva se cancela/expira (el stock se libera).

**Reglas de negocio principales:**
1. El stock disponible nunca puede quedar en un valor negativo.
2. Al agregar un producto al carrito se crea una **reserva temporal** de
   15 minutos que descuenta esas unidades del stock disponible general.
3. Si la reserva expira sin confirmarse, el sistema libera automáticamente
   las unidades reservadas.
4. Una compra solo puede confirmarse si la reserva sigue activa y vigente.

**Restricciones del caso:**
1. El MVP cubre un único canal de venta digital (no diferencia web vs. app).
2. No se implementa pasarela de pagos real: "confirmar compra" simula el
   pago aprobado para efectos de este taller.

**Objetivo medible del MVP:** 0% de reservas confirmadas con stock
insuficiente (verificado mediante pruebas automatizadas) y liberación de
reservas expiradas en menos de 1 segundo tras la siguiente consulta.

## 2. Requisitos

### Historias de usuario
1. Como cliente, quiero ver el stock disponible de cada producto para
   saber si puedo comprarlo. **Criterio de aceptación:** cada tarjeta de
   producto muestra unidades disponibles o "sin stock" cuando es 0.
2. Como cliente, quiero reservar un producto al agregarlo al carrito para
   asegurar que nadie más lo agote mientras decido comprar. **Criterio:**
   al reservar, el stock disponible del catálogo baja de inmediato para
   todos los usuarios.
3. Como cliente, quiero que mi reserva expire si no compro a tiempo, para
   no bloquear inventario que otros necesitan. **Criterio:** una reserva
   sin confirmar tras 15 minutos vuelve a estar disponible automáticamente.
4. Como cliente, quiero confirmar mi compra y tener la certeza de que el
   producto quedó apartado. **Criterio:** al confirmar, la reserva pasa a
   estado "confirmada" y el stock reservado se descuenta en forma definitiva.
5. Como administrador de tienda, quiero corregir el stock disponible de un
   producto, para reflejar el inventario físico real. **Criterio:** el
   endpoint de actualización de stock requiere una clave de administrador
   y rechaza valores negativos.

### Requisitos no funcionales
1. **Seguridad:** los endpoints que modifican el stock manualmente
   (actor administrador) requieren una clave `X-API-Key` válida.
2. **Disponibilidad/consistencia:** toda operación de reserva, confirmación
   o cancelación se ejecuta en una única transacción de base de datos para
   evitar condiciones de sobreventa.
3. **Usabilidad:** el catálogo indica visualmente (color e indicador de
   texto) el nivel de stock — alto, bajo o agotado — sin que el cliente
   tenga que interpretar números.

## 3. Arquitectura

Ver el diagrama en formato Draw.io: `arquitectura/mercado-viva-inventario.drawio`.

Componentes:
- **Frontend (HTML/CSS/JS):** catálogo de productos y carrito de reservas
  con temporizador. Consume la API vía `fetch`/JSON sobre HTTPS.
- **Backend (Python/Flask):** expone la API REST `/api/*`, contiene la
  lógica de negocio (`services.py`) separada de las rutas HTTP (`app.py`).
- **Base de datos:** SQLite en desarrollo local; compatible con PostgreSQL
  en producción (Render/Railway) mediante la variable `DATABASE_URL`.
- **Autenticación:** clave `X-API-Key` para operaciones administrativas.
- **Publicación:** backend en Render/Railway (sirve también el frontend
  como archivos estáticos desde la misma app Flask).

## 4. Tecnologías

- Backend: Python 3.11+, Flask, Flask-SQLAlchemy, Flask-Cors, Gunicorn.
- Persistencia: SQLite (local) / PostgreSQL (producción).
- Frontend: HTML5, CSS3, JavaScript (sin frameworks).
- Pruebas: Pytest.

## 5. Cómo ejecutar el proyecto localmente

```bash
cd backend
python3 -m venv venv
source venv/bin/activate        # En Windows: venv\Scripts\activate
pip install -r requirements.txt

python3 app.py
```

La aplicación queda disponible en `http://localhost:5000` (el backend sirve
también el frontend).

### Ejecutar las pruebas

```bash
cd backend
pytest -v
```

### Probar el endpoint de administrador

```bash
curl -X POST http://localhost:5000/api/admin/productos/1/stock \
  -H "Content-Type: application/json" \
  -H "X-API-Key: TU_ADMIN_API_KEY" \
  -d '{"stock_disponible": 100}'
```

## 6. Despliegue (Render, Railway u otra plataforma equivalente)

1. Sube este repositorio a GitHub.
2. En Render/Railway, crea un nuevo servicio web apuntando a la carpeta
   `backend/`, con:
   - **Comando de build:** `pip install -r requirements.txt`
   - **Comando de inicio:** `gunicorn app:app` (ya incluido en `Procfile`)
3. Configura las variables de entorno:
   - `DATABASE_URL` (si usas Postgres administrado, por ejemplo Neon o el
     Postgres del propio Render).
   - `ADMIN_API_KEY` (clave de administrador en producción).
4. Una vez desplegado, la URL pública asignada por la plataforma sirve
   tanto el frontend como la API.

**URL de la aplicación publicada:** _mercado-viva-inventario.onrender.com_

## 7. Integrantes del equipo

- Samuel Gil Gil
