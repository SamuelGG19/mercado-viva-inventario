// ---------------------------------------------------------------------------
// Mercado VIVA · Frontend del proceso "Verificación de inventario"
// Se comunica con el backend Flask a través de la API REST en /api/*.
// ---------------------------------------------------------------------------

const API_BASE = ""; // mismo origen; cambiar si el backend se publica aparte

const elLista = document.getElementById("lista-productos");
const elReservas = document.getElementById("lista-reservas");
const elCarritoVacio = document.getElementById("carrito-vacio");
const elBusqueda = document.getElementById("campo-busqueda");
const elNotificacion = document.getElementById("notificacion");

let temporizador = null;

// --------------------------- Utilidades ------------------------------------

function mostrarNotificacion(mensaje, tipo = "info") {
  elNotificacion.textContent = mensaje;
  elNotificacion.dataset.tipo = tipo;
  elNotificacion.classList.add("visible");
  clearTimeout(mostrarNotificacion._t);
  mostrarNotificacion._t = setTimeout(() => {
    elNotificacion.classList.remove("visible");
  }, 3200);
}

async function solicitar(ruta, opciones = {}) {
  const respuesta = await fetch(API_BASE + ruta, {
    headers: { "Content-Type": "application/json" },
    ...opciones,
  });
  const datos = await respuesta.json().catch(() => ({}));
  if (!respuesta.ok) {
    throw new Error(datos.error || "Ocurrió un error inesperado.");
  }
  return datos;
}

function nivelDeStock(producto) {
  if (producto.stock_disponible <= 0) return "agotado";
  if (producto.stock_disponible <= 5) return "bajo";
  return "alto";
}

function formatearPrecio(valor) {
  return valor.toLocaleString("es-CO", { style: "currency", currency: "COP", maximumFractionDigits: 0 });
}

function formatearTiempo(segundos) {
  const m = Math.floor(segundos / 60).toString().padStart(2, "0");
  const s = Math.floor(segundos % 60).toString().padStart(2, "0");
  return `${m}:${s}`;
}

// --------------------------- Catálogo ---------------------------------------

async function cargarProductos(busqueda = "") {
  try {
    const productos = await solicitar(`/api/productos?q=${encodeURIComponent(busqueda)}`);
    pintarProductos(productos);
  } catch (err) {
    mostrarNotificacion("No se pudo cargar el catálogo: " + err.message, "error");
  }
}

function pintarProductos(productos) {
  elLista.innerHTML = "";
  if (productos.length === 0) {
    elLista.innerHTML = `<p style="color:var(--texto-suave)">No encontramos productos con ese nombre.</p>`;
    return;
  }

  for (const producto of productos) {
    const nivel = nivelDeStock(producto);
    const tarjeta = document.createElement("article");
    tarjeta.className = "tarjeta-producto";
    tarjeta.dataset.nivel = nivel;

    const textoStock =
      nivel === "agotado"
        ? "Sin unidades disponibles ahora mismo"
        : `<strong>${producto.stock_disponible}</strong> unidades disponibles`;

    tarjeta.innerHTML = `
      <span class="tarjeta-producto__categoria">${producto.categoria}</span>
      <h3 class="tarjeta-producto__nombre">${producto.nombre}</h3>
      <span class="tarjeta-producto__precio">${formatearPrecio(producto.precio)}</span>
      <span class="tarjeta-producto__stock">${textoStock}</span>
      <div class="tarjeta-producto__acciones">
        ${
          nivel === "agotado"
            ? `<button class="boton boton--agotado" disabled>Sin stock</button>`
            : `<input type="number" min="1" max="${producto.stock_disponible}" value="1" aria-label="Cantidad" />
               <button class="boton boton--primario">Agregar al carrito</button>`
        }
      </div>
    `;

    if (nivel !== "agotado") {
      const input = tarjeta.querySelector("input");
      const boton = tarjeta.querySelector("button.boton--primario");
      boton.addEventListener("click", () => agregarAlCarrito(producto, input, boton));
    }

    elLista.appendChild(tarjeta);
  }
}

async function agregarAlCarrito(producto, input, boton) {
  const cantidad = parseInt(input.value, 10);

  if (!Number.isInteger(cantidad) || cantidad <= 0) {
    mostrarNotificacion("Ingresa una cantidad válida.", "error");
    return;
  }

  boton.disabled = true;
  try {
    await solicitar("/api/reservas", {
      method: "POST",
      body: JSON.stringify({ producto_id: producto.id, cantidad }),
    });
    mostrarNotificacion(`Reservaste ${cantidad} × ${producto.nombre}. Tienes 15 min para confirmar.`);
    await Promise.all([cargarProductos(elBusqueda.value), cargarReservas()]);
  } catch (err) {
    mostrarNotificacion(err.message, "error");
  } finally {
    boton.disabled = false;
  }
}

// --------------------------- Carrito / reservas ------------------------------

async function cargarReservas() {
  try {
    const reservas = await solicitar("/api/reservas");
    pintarReservas(reservas.filter((r) => r.estado === "activa" || r.estado === "confirmada"));
  } catch (err) {
    mostrarNotificacion("No se pudieron cargar tus reservas: " + err.message, "error");
  }
}

function pintarReservas(reservas) {
  elReservas.innerHTML = "";
  elCarritoVacio.style.display = reservas.length === 0 ? "block" : "none";

  for (const reserva of reservas) {
    const item = document.createElement("div");
    item.className = "reserva-item" + (reserva.estado === "confirmada" ? " reserva-item--confirmada" : "");
    item.dataset.id = reserva.id;
    item.dataset.expira = reserva.expira_en;

    item.innerHTML = `
      <div class="reserva-item__fila">
        <span class="reserva-item__nombre">${reserva.producto_nombre}</span>
        <span class="reserva-item__cantidad">× ${reserva.cantidad}</span>
      </div>
      <div class="reserva-item__temporizador">
        ${reserva.estado === "confirmada" ? "Compra confirmada" : "Expira en " + formatearTiempo(reserva.segundos_restantes)}
      </div>
      ${
        reserva.estado === "activa"
          ? `<div class="reserva-item__acciones">
               <button class="boton boton--mango" data-accion="confirmar">Confirmar compra</button>
               <button class="boton boton--texto" data-accion="cancelar">Cancelar</button>
             </div>`
          : ""
      }
    `;

    if (reserva.estado === "activa") {
      item.querySelector('[data-accion="confirmar"]').addEventListener("click", () => resolverReserva(reserva.id, "confirmar"));
      item.querySelector('[data-accion="cancelar"]').addEventListener("click", () => resolverReserva(reserva.id, "cancelar"));
    }

    elReservas.appendChild(item);
  }
}

async function resolverReserva(id, accion) {
  try {
    await solicitar(`/api/reservas/${id}/${accion}`, { method: "POST" });
    mostrarNotificacion(accion === "confirmar" ? "¡Compra confirmada!" : "Reserva cancelada.");
    await Promise.all([cargarProductos(elBusqueda.value), cargarReservas()]);
  } catch (err) {
    mostrarNotificacion(err.message, "error");
    await cargarReservas();
  }
}

// --------------------------- Temporizador de expiración ----------------------

function actualizarContadores() {
  const ahora = Date.now();
  let algunoExpiro = false;

  document.querySelectorAll(".reserva-item").forEach((item) => {
    const elTiempo = item.querySelector(".reserva-item__temporizador");
    if (!elTiempo || item.classList.contains("reserva-item--confirmada")) return;

    const expiraEn = new Date(item.dataset.expira).getTime();
    const restante = Math.max(0, Math.floor((expiraEn - ahora) / 1000));

    elTiempo.textContent = "Expira en " + formatearTiempo(restante);
    elTiempo.dataset.urgente = restante <= 60 ? "true" : "false";

    if (restante <= 0) algunoExpiro = true;
  });

  if (algunoExpiro) {
    cargarReservas();
    cargarProductos(elBusqueda.value);
  }
}

// --------------------------- Inicio ------------------------------------------

let debounceBusqueda = null;
elBusqueda.addEventListener("input", () => {
  clearTimeout(debounceBusqueda);
  debounceBusqueda = setTimeout(() => cargarProductos(elBusqueda.value), 250);
});

cargarProductos();
cargarReservas();
temporizador = setInterval(actualizarContadores, 1000);
