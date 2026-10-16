/* Mantenedor de calificaciones tributarias (nuam)
   Base común, búsqueda, grilla, selección y paginación. */
(function () {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const COLUMNAS_FACTOR = Array.from({ length: 30 }, (_, i) => i + 8); // columnas 8 a 37
  const NUM_COLUMNAS = 8 + COLUMNAS_FACTOR.length;

  const estado = { anterior: null, siguiente: null, seleccionada: null };

  // ---------- Base común ----------
  function csrfToken() {
    const campo = document.querySelector("input[name=csrfmiddlewaretoken]");
    if (campo) return campo.value;
    const m = document.cookie.match(/csrftoken=([^;]+)/);
    return m ? m[1] : "";
  }

  async function api(ruta, { metodo = "GET", cuerpo } = {}) {
    const cabeceras = { Accept: "application/json" };
    let body;
    if (cuerpo instanceof FormData) {
      body = cuerpo;
    } else if (cuerpo !== undefined) {
      cabeceras["Content-Type"] = "application/json";
      body = JSON.stringify(cuerpo);
    }
    if (metodo !== "GET") cabeceras["X-CSRFToken"] = csrfToken();

    const resp = await fetch(ruta, { method: metodo, headers: cabeceras, body, credentials: "same-origin" });
    if (resp.status === 401) {
      window.location.href = "/login/?next=" + encodeURIComponent(window.location.pathname + window.location.search);
      throw new Error("sesion_expirada");
    }
    if (resp.status === 204) return null;
    const datos = await resp.json().catch(() => ({}));
    if (!resp.ok) {
      const error = new Error("error_api");
      error.datos = datos;
      throw error;
    }
    return datos;
  }

  function textoDeError(datos) {
    if (!datos) return "Ocurrió un error inesperado.";
    if (typeof datos === "string") return datos;
    if (Array.isArray(datos)) return datos.join(" ");
    if (datos.detail) return datos.detail;
    return Object.entries(datos)
      .map(([campo, msg]) => `${campo}: ${Array.isArray(msg) ? msg.join(" ") : msg}`)
      .join(" · ");
  }

  function mostrarMensaje(texto, tipo = "danger") {
    const caja = $("mensajeMantenedor");
    caja.className = `alert alert-${tipo} py-2 small`;
    caja.textContent = texto;
  }

  function ocultarMensaje() {
    $("mensajeMantenedor").className = "alert d-none py-2 small";
  }

  // ---------- Grilla ----------
  function construirCabecera() {
    const titulos = ["Ejercicio", "Instrumento", "Fecha pago", "Descripción", "Secuencia",
                     "Valor histórico", "ISFUT", "Origen",
                     ...COLUMNAS_FACTOR.map((c) => `Factor-${String(c).padStart(2, "0")}`)];
    const tr = document.createElement("tr");
    titulos.forEach((t) => {
      const th = document.createElement("th");
      th.textContent = t;
      tr.appendChild(th);
    });
    $("cabeceraResultados").replaceChildren(tr);
  }

  function filaMensaje(texto) {
    const tr = document.createElement("tr");
    const td = document.createElement("td");
    td.colSpan = NUM_COLUMNAS;
    td.className = "text-center text-muted py-4";
    td.textContent = texto;
    tr.appendChild(td);
    return tr;
  }

  function celda(texto, clase = "") {
    const td = document.createElement("td");
    if (clase) td.className = clase;
    td.textContent = texto ?? "";
    return td;
  }

  function pintarFilas(calificaciones) {
    const cuerpo = $("tablaDatosBody");
    cuerpo.replaceChildren();
    if (calificaciones.length === 0) {
      cuerpo.appendChild(filaMensaje("No hay registros para los filtros seleccionados."));
      return;
    }
    calificaciones.forEach((c) => {
      const tr = document.createElement("tr");
      tr.style.cursor = "pointer";
      tr.dataset.id = c.id;
      tr.appendChild(celda(c.ejercicio_comercial, "text-center"));
      tr.appendChild(celda(c.instrumento, "fw-semibold"));
      tr.appendChild(celda(c.fecha_pago, "text-center"));
      tr.appendChild(celda(c.descripcion || "-"));
      tr.appendChild(celda(c.secuencia_evento, "text-end"));
      tr.appendChild(celda(c.valor_historico, "text-end"));
      tr.appendChild(celda(c.is_fut ? "Sí" : "No", "text-center"));
      tr.appendChild(celda(c.origen === "CORREDOR" ? "Corredor" : "Bolsa", "text-center"));
      COLUMNAS_FACTOR.forEach((col) => tr.appendChild(celda(c.factores[String(col)] ?? "0", "text-end")));
      tr.addEventListener("click", () => seleccionar(tr, c));
      cuerpo.appendChild(tr);
      actualizarBotonRect();
    });
  }

  // ---------- Selección ----------
  function seleccionar(tr, calificacion) {
    document.querySelectorAll("#tablaDatosBody tr").forEach((f) => f.classList.remove("table-active"));
    tr.classList.add("table-active");
    estado.seleccionada = calificacion;
    $("btnModificar").disabled = false;
    $("btnEliminar").disabled = false;
    $("btnCopiar").disabled = false;
    $("btnSolicitarRect").disabled = true;
  }

  function deseleccionar() {
    estado.seleccionada = null;
    $("btnModificar").disabled = true;
    $("btnEliminar").disabled = true;
    $("btnCopiar").disabled = true;
  }

  // ---------- Búsqueda y paginación ----------
  function filtros() {
    const p = new URLSearchParams();
    if ($("filtroMercado").value) p.set("mercado", $("filtroMercado").value);
    if ($("filtroOrigen").value) p.set("origen", $("filtroOrigen").value);
    if ($("filtroPeriodo").value) p.set("ejercicio", $("filtroPeriodo").value);
    if ($("chkPendiente").checked) p.set("pendiente", "1");
    return p.toString();
  }

  function rutaRelativa(url) {
    const u = new URL(url, window.location.origin);
    return u.pathname + u.search;
  }

  function pintarPaginacion(datos) {
    estado.siguiente = datos.next ? rutaRelativa(datos.next) : null;
    estado.anterior = datos.previous ? rutaRelativa(datos.previous) : null;
    $("btnAnterior").disabled = !estado.anterior;
    $("btnSiguiente").disabled = !estado.siguiente;
    $("contadorElementos").textContent = `Elementos mostrados ${datos.results.length} de ${datos.count}`;
  }

  async function cargar(ruta) {
    ocultarMensaje();
    try {
      const datos = await api(ruta);
      pintarFilas(datos.results);
      pintarPaginacion(datos);
      deseleccionar();
    } catch (error) {
      if (error.message === "sesion_expirada") return;
      mostrarMensaje(error.datos ? textoDeError(error.datos) : "No se pudieron cargar las calificaciones.");
    }
  }

  function buscar() {
    const q = filtros();
    cargar("/api/calificaciones/" + (q ? "?" + q : ""));
  }

  function limpiar() {
    $("filtroMercado").value = "ACN";
    $("filtroOrigen").value = "";
    $("filtroPeriodo").value = String(new Date().getFullYear());
    $("chkPendiente").checked = false;
    $("tablaDatosBody").replaceChildren(filaMensaje("No hay registros disponibles. Utilice la barra de búsqueda o cargue un archivo."));
    $("contadorElementos").textContent = "Elementos mostrados 0 de 0";
    estado.anterior = null;
    estado.siguiente = null;
    $("btnAnterior").disabled = true;
    $("btnSiguiente").disabled = true;
    deseleccionar();
    ocultarMensaje();
  }

  // ---------- Inicio ----------
  document.addEventListener("DOMContentLoaded", () => {
    construirCabecera();
    $("tablaDatosBody").replaceChildren(filaMensaje("No hay registros disponibles. Utilice la barra de búsqueda o cargue un archivo."));
    $("btnBuscar").addEventListener("click", buscar);
    $("btnLimpiar").addEventListener("click", limpiar);
    $("btnAnterior").addEventListener("click", () => estado.anterior && cargar(estado.anterior));
    $("btnSiguiente").addEventListener("click", () => estado.siguiente && cargar(estado.siguiente));
  });

  // ---------- Modal de ingreso (parte A) ----------
  const FACTORES_ID = COLUMNAS_FACTOR.map((c) => `f${String(c).padStart(2, "0")}`);
  const MONTOS_ID = COLUMNAS_FACTOR.map((c) => `m${String(c).padStart(2, "0")}`);

  function datosIngreso() {
    const form = $("formIngreso");
    const datos = {};
    form.querySelectorAll("input[name], select[name]").forEach((el) => {
      if (el.type === "checkbox") datos[el.name] = el.checked;
      else datos[el.name] = el.value.trim();
    });
    return datos;
  }

  function limpiarErroresIngreso() {
    document.querySelectorAll("#formIngreso .is-invalid").forEach((el) => el.classList.remove("is-invalid"));
    document.querySelectorAll("#formIngreso .invalid-feedback").forEach((el) => el.remove());
    $("ingMensajes").classList.add("d-none");
    $("ingMensajes").textContent = "";
  }

  function marcarErrorEnCampo(nombre, texto) {
    const el = document.querySelector(`#formIngreso [name="${nombre}"]`);
    if (!el) return false;
    el.classList.add("is-invalid");
    const aviso = document.createElement("div");
    aviso.className = "invalid-feedback";
    aviso.textContent = texto;
    el.insertAdjacentElement("afterend", aviso);
    return true;
  }

  function mostrarErroresIngreso(datos) {
    const sinCampo = [];
    if (datos && typeof datos === "object" && !Array.isArray(datos)) {
      Object.entries(datos).forEach(([campo, msg]) => {
        const texto = Array.isArray(msg) ? msg.join(" ") : String(msg);
        if (campo === "factores") { sinCampo.push(texto); return; }
        if (!marcarErrorEnCampo(campo, texto)) sinCampo.push(`${campo}: ${texto}`);
      });
    } else {
      sinCampo.push(textoDeError(datos));
    }
    if (sinCampo.length) {
      $("ingMensajes").textContent = sinCampo.join(" · ");
      $("ingMensajes").classList.remove("d-none");
    }
  }

  let verFactoresCalculados = false;

  function aplicarVista() {
    const porMontos = $("ingPorMontos").checked;
    // Modo montos: al calcular, se muestran los factores (de solo lectura) para revisarlos
    const verMontos = porMontos && !verFactoresCalculados;
    $("btnCalcularIngreso").disabled = !porMontos;
    document.querySelectorAll("#formIngreso .campo-monto").forEach((el) => el.classList.toggle("d-none", !verMontos));
    document.querySelectorAll("#formIngreso .campo-factor").forEach((el) => el.classList.toggle("d-none", verMontos));
    FACTORES_ID.forEach((id) => { $(id).readOnly = porMontos; });
  }

  function alternarMontos() {
    verFactoresCalculados = false;
    aplicarVista();
  }
  async function calcularIngreso() {
    limpiarErroresIngreso();
    const datos = datosIngreso();
    const montos = {};
    COLUMNAS_FACTOR.forEach((c) => {
      const num = String(c).padStart(2, "0");
      montos[`f${num}`] = datos[`m${num}`] || "0";
    });
    try {
      const resp = await api("/api/calificaciones/calcular/", { metodo: "POST", cuerpo: montos });
      Object.entries(resp.factores).forEach(([col, valor]) => {
        const id = `f${String(col).padStart(2, "0")}`;
        if ($(id)) $(id).value = valor;
      });
      verFactoresCalculados = true;
      aplicarVista();
      if (resp.errores && resp.errores.length) {
        $("ingMensajes").textContent = resp.errores.join(" · ");
        $("ingMensajes").classList.remove("d-none");
      }
    } catch (error) {
      if (error.message === "sesion_expirada") return;
      mostrarErroresIngreso(error.datos);
    }
  }

  async function grabarIngreso() {
    limpiarErroresIngreso();
    const datos = datosIngreso();
    // En modo montos, los factores ya fueron calculados y se envían como montos
    if (datos.ingreso_montos) {
      FACTORES_ID.forEach((id) => { datos[id] = datos[id] || "0"; });
    }
    try {
      await api("/api/calificaciones/", { metodo: "POST", cuerpo: datos });
      bootstrap.Modal.getInstance($("modalIngreso")).hide();
      $("formIngreso").reset();
      alternarMontos();
      buscar();
      mostrarMensaje("Calificación ingresada correctamente.", "success");
    } catch (error) {
      if (error.message === "sesion_expirada") return;
      mostrarErroresIngreso(error.datos);
    }
  }

  function iniciarModalIngreso() {
    $("ingPorMontos").addEventListener("change", alternarMontos);
    $("btnCalcularIngreso").addEventListener("click", calcularIngreso);
    $("btnGrabarIngreso").addEventListener("click", grabarIngreso);
    $("modalIngreso").addEventListener("hidden.bs.modal", () => {
      limpiarErroresIngreso();
      alternarMontos();
    });
    alternarMontos();
  }

  document.addEventListener("DOMContentLoaded", iniciarModalIngreso);

  // ---------- Modificar, eliminar y copiar (parte B) ----------
  const CAMPOS_MOD = ["modMercado", "modInstrumento", "modSecuencia", "modDividendo", "modFechaPago",
                      "modEjercicio", "modValorHistorico", "modTipoSociedad", "modDescripcion",
                      "modFactorAct", "modIsfut", "modPorMontos"];

  function limpiarErroresModificar() {
    document.querySelectorAll("#formModificar .is-invalid").forEach((el) => el.classList.remove("is-invalid"));
    document.querySelectorAll("#formModificar .invalid-feedback").forEach((el) => el.remove());
    $("modMensajes").classList.add("d-none");
    $("modMensajes").textContent = "";
  }

  function mostrarErroresModificar(datos) {
    const sinCampo = [];
    if (datos && typeof datos === "object" && !Array.isArray(datos)) {
      Object.entries(datos).forEach(([campo, msg]) => {
        const texto = Array.isArray(msg) ? msg.join(" ") : String(msg);
        const el = document.querySelector(`#formModificar [name="${campo}"]`);
        if (el) {
          el.classList.add("is-invalid");
          const aviso = document.createElement("div");
          aviso.className = "invalid-feedback";
          aviso.textContent = texto;
          el.insertAdjacentElement("afterend", aviso);
        } else {
          sinCampo.push(`${campo}: ${texto}`);
        }
      });
    } else {
      sinCampo.push(textoDeError(datos));
    }
    if (sinCampo.length) {
      $("modMensajes").textContent = sinCampo.join(" · ");
      $("modMensajes").classList.remove("d-none");
    }
  }

  // Carga los datos de la calificación seleccionada en el modal de modificar
  async function abrirModificar() {
    if (!estado.seleccionada) return;
    limpiarErroresModificar();
    try {
      const c = await api(`/api/calificaciones/${estado.seleccionada.id}/`);
      $("modId").value = c.id;
      $("modMercado").value = c.mercado_codigo;
      $("modInstrumento").value = c.instrumento;
      $("modSecuencia").value = c.secuencia_evento;
      $("modDividendo").value = c.numero_dividendo;
      $("modFechaPago").value = c.fecha_pago;
      $("modEjercicio").value = c.ejercicio_comercial;
      $("modValorHistorico").value = c.valor_historico;
      $("modTipoSociedad").value = c.tipo_sociedad || "";
      $("modDescripcion").value = c.descripcion || "";
      $("modFactorAct").value = c.factor_actualizacion;
      $("modIsfut").checked = !!c.is_fut;
      $("modPorMontos").checked = false;
      COLUMNAS_FACTOR.forEach((col) => {
        const num = String(col).padStart(2, "0");
        $(`mod_f${num}`).value = c.factores[String(col)] ?? "0";
      });
      alternarModificar();
      bootstrap.Modal.getOrCreateInstance($("modalModificar")).show();
    } catch (error) {
      if (error.message === "sesion_expirada") return;
      mostrarMensaje(textoDeError(error.datos) || "No se pudo abrir la calificación.");
    }
  }

  function alternarModificar() {
    const porMontos = $("modPorMontos").checked;
    $("btnCalcularModificar").disabled = !porMontos;
    COLUMNAS_FACTOR.forEach((col) => {
      const num = String(col).padStart(2, "0");
      $(`mod_f${num}`).readOnly = porMontos;
    });
  }

  async function guardarModificar() {
    limpiarErroresModificar();
    const id = $("modId").value;
    const datos = {
      mercado: $("modMercado").value,
      descripcion: $("modDescripcion").value.trim(),
      fecha_pago: $("modFechaPago").value,
      numero_dividendo: $("modDividendo").value,
      tipo_sociedad: $("modTipoSociedad").value,
      valor_historico: $("modValorHistorico").value.trim(),
      factor_actualizacion: $("modFactorAct").value.trim(),
      is_fut: $("modIsfut").checked,
      ingreso_montos: $("modPorMontos").checked,
    };
    COLUMNAS_FACTOR.forEach((col) => {
      const num = String(col).padStart(2, "0");
      datos[`f${num}`] = $(`mod_f${num}`).value.trim() || "0";
    });
    try {
      await api(`/api/calificaciones/${id}/`, { metodo: "PATCH", cuerpo: datos });
      bootstrap.Modal.getInstance($("modalModificar")).hide();
      buscar();
      mostrarMensaje("Calificación modificada correctamente.", "success");
    } catch (error) {
      if (error.message === "sesion_expirada") return;
      mostrarErroresModificar(error.datos);
    }
  }

  function calcularModificar() {
    const montos = {};
    COLUMNAS_FACTOR.forEach((col) => {
      const num = String(col).padStart(2, "0");
      montos[`f${num}`] = $(`mod_f${num}`).value.trim() || "0";
    });
    api("/api/calificaciones/calcular/", { metodo: "POST", cuerpo: montos }).then((resp) => {
      Object.entries(resp.factores).forEach(([col, valor]) => {
        const num = String(col).padStart(2, "0");
        $(`mod_f${num}`).value = valor;
      });
    }).catch((error) => {
      if (error.message === "sesion_expirada") return;
      mostrarErroresModificar(error.datos);
    });
  }

  async function eliminarSeleccionada() {
    if (!estado.seleccionada) return;
    if (!confirm(`¿Eliminar la calificación ${estado.seleccionada.instrumento} (sec. ${estado.seleccionada.secuencia_evento})?`)) return;
    try {
      await api(`/api/calificaciones/${estado.seleccionada.id}/`, { metodo: "DELETE" });
      mostrarMensaje("Calificación eliminada.", "success");
      buscar();
    } catch (error) {
      if (error.message === "sesion_expirada") return;
      mostrarMensaje(textoDeError(error.datos) || "No se pudo eliminar la calificación.");
    }
  }

  function copiarSeleccionada() {
    if (!estado.seleccionada) return;
    $("copiaSecuencia").value = estado.seleccionada.secuencia_evento;
    $("copiaMensaje").classList.add("d-none");
    bootstrap.Modal.getOrCreateInstance($("modalCopiar")).show();
  }

  async function confirmarCopia() {
    const secuencia = Number($("copiaSecuencia").value);
    try {
      await api(`/api/calificaciones/${estado.seleccionada.id}/copiar/`, { metodo: "POST", cuerpo: { secuencia_evento: secuencia } });
      bootstrap.Modal.getInstance($("modalCopiar")).hide();
      mostrarMensaje("Calificación copiada a su corredora.", "success");
      buscar();
    } catch (error) {
      if (error.message === "sesion_expirada") return;
      $("copiaMensaje").textContent = textoDeError(error.datos) || "No se pudo copiar la calificación.";
      $("copiaMensaje").classList.remove("d-none");
    }
  }

  function iniciarModificarEliminarCopiar() {
    $("btnModificar").addEventListener("click", abrirModificar);
    $("btnEliminar").addEventListener("click", eliminarSeleccionada);
    $("btnCopiar").addEventListener("click", copiarSeleccionada);
    $("btnGuardarModificacion").addEventListener("click", guardarModificar);
    $("btnCalcularModificar").addEventListener("click", calcularModificar);
    $("modPorMontos").addEventListener("change", alternarModificar);
    $("modalModificar").addEventListener("hidden.bs.modal", limpiarErroresModificar);
    $("btnConfirmarCopia").addEventListener("click", confirmarCopia);
  }

  document.addEventListener("DOMContentLoaded", iniciarModificarEliminarCopiar);

  // ---------- Cargas CSV (parte C) ----------
  let cargaActual = { id: null, modo: null };

  function pintarVistaPrevia(modal, datos) {
    const cuerpo = document.getElementById(modal.tabla);
    cuerpo.replaceChildren();
    if (!datos.previsualizacion || !datos.previsualizacion.filas.length) {
      cuerpo.appendChild(filaVacia(modal.columnas, "No hay filas para mostrar."));
      return;
    }
    datos.previsualizacion.filas.forEach((fila, i) => {
      const tr = document.createElement("tr");
      tr.appendChild(celdaTexto("Pendiente", "text-center text-muted"));
      fila.forEach((v) => tr.appendChild(celdaTexto(v)));
      cuerpo.appendChild(tr);
    });
    $(modal.badge).textContent = `${datos.total_filas ?? datos.previsualizacion.filas.length}`;
    $(modal.estado).textContent = datos.formato_valido ? "Archivo válido. Revise la vista previa." : "El formato no es válido: revise las 38 columnas.";
  }

  function pintarResultadoValidacion(modal, datos) {
    const cuerpo = document.getElementById(modal.tabla);
    cuerpo.replaceChildren();
    datos.filas.forEach((f) => {
      const tr = document.createElement("tr");
      const estadoTxt = f.estado === "OK" ? "OK" : `ERROR: ${f.motivo}`;
      const td = celdaTexto(estadoTxt, f.estado === "OK" ? "text-success" : "text-danger");
      tr.appendChild(td);
      (f.datos || []).forEach((v) => tr.appendChild(celdaTexto(v)));
      cuerpo.appendChild(tr);
    });
    $(modal.estado).textContent = `Válidas: ${datos.validas} · Rechazadas: ${datos.rechazadas}`;
    $(modal.btnGrabar).disabled = datos.validas === 0;
    mostrarErroresCarga(modal, datos.filas.filter((f) => f.estado === "ERROR"));
  }

  function mostrarErroresCarga(modal, errores) {
    const caja = document.getElementById(modal.errores);
    const lista = document.getElementById(modal.lista);
    lista.replaceChildren();
    errores.forEach((f) => {
      const li = document.createElement("li");
      li.textContent = `Fila ${f.fila}: ${f.motivo}`;
      lista.appendChild(li);
    });
    caja.classList.toggle("d-none", errores.length === 0);
  }

  function celdaTexto(texto, clase = "") {
    const td = document.createElement("td");
    if (clase) td.className = clase;
    td.textContent = texto ?? "";
    return td;
  }

  function filaVacia(columnas, texto) {
    const tr = document.createElement("tr");
    const td = document.createElement("td");
    td.colSpan = columnas;
    td.className = "text-center text-muted py-4";
    td.textContent = texto;
    tr.appendChild(td);
    return tr;
  }

  const MODAL_MONTO = {
    input: "inputFileMonto", tabla: "tablaCargaMontoBody", badge: "badgeTotalMonto", estado: "textoEstadoMonto",
    btnCalcular: "btnCalcularFactores", btnGrabar: "btnGrabarMonto", errores: "erroresMonto", lista: "listaErroresMonto",
    tipo: "MONTOS", modal: "modalCargaMonto", columnas: 39,
  };
  const MODAL_FACTOR = {
    input: "inputFileFactor", tabla: "tablaCargaFactorBody", badge: "badgeTotalFactor", estado: "textoEstadoFactor",
    btnCalcular: null, btnGrabar: "btnGrabarFactor", errores: "erroresFactor", lista: "listaErroresFactor",
    tipo: "FACTORES", modal: "modalCargaFactor", columnas: 39,
  };

  async function subirArchivo(modal) {
    const input = $(modal.input);
    if (!input.files.length) return;
    const form = new FormData();
    form.append("archivo", input.files[0]);
    form.append("formato_tipo", modal.tipo);
    ocultarMensaje();
    try {
      const datos = await api("/api/cargas/", { metodo: "POST", cuerpo: form });
      cargaActual = { id: datos.id, modo: modal };
      pintarVistaPrevia(modal, { ...datos, total_filas: datos.total_filas });
      $(modal.btnGrabar).disabled = true;
      if (modal.btnCalcular) $(modal.btnCalcular).disabled = false;
      else $(modal.btnGrabar).disabled = !datos.formato_valido;
    } catch (error) {
      if (error.message === "sesion_expirada") return;
      mostrarErroresCarga(modal, [{ fila: "-", motivo: textoDeError(error.datos) }]);
    }
  }

  async function validarCarga(modal) {
    if (!cargaActual.id) return;
    try {
      const datos = await api(`/api/cargas/${cargaActual.id}/validar/`, { metodo: "POST" });
      pintarResultadoValidacion(modal, datos);
    } catch (error) {
      if (error.message === "sesion_expirada") return;
      mostrarErroresCarga(modal, [{ fila: "-", motivo: textoDeError(error.datos) }]);
    }
  }

  async function grabarCarga(modal) {
    if (!cargaActual.id) return;
    try {
      const datos = await api(`/api/cargas/${cargaActual.id}/procesar/`, { metodo: "POST" });
      const r = datos.resumen || {};
      bootstrap.Modal.getInstance(document.getElementById(modal.modal)).hide();
      mostrarMensaje(`Carga procesada: ${r.validas ?? datos.filas_validas} válidas, ${r.rechazadas ?? datos.filas_rechazadas} rechazadas.`, "success");
      cargaActual = { id: null, modo: null };
      buscar();
    } catch (error) {
      if (error.message === "sesion_expirada") return;
      mostrarErroresCarga(modal, [{ fila: "-", motivo: textoDeError(error.datos) }]);
    }
  }

  function reiniciarModalCarga(modal) {
    $(modal.input).value = "";
    cargaActual = { id: null, modo: null };
    document.getElementById(modal.tabla).replaceChildren(filaVacia(modal.columnas, "No hay registros."));
    $(modal.estado).textContent = "No hay registros.";
    $(modal.badge).textContent = "0";
    $(modal.btnGrabar).disabled = true;
    if (modal.btnCalcular) $(modal.btnCalcular).disabled = true;
    document.getElementById(modal.errores).classList.add("d-none");
  }

  function iniciarCargas() {
    [MODAL_MONTO, MODAL_FACTOR].forEach((modal) => {
      $(modal.input).addEventListener("change", () => subirArchivo(modal));
      $(modal.btnGrabar).addEventListener("click", () => grabarCarga(modal));
      if (modal.btnCalcular) $(modal.btnCalcular).addEventListener("click", () => validarCarga(modal));
      document.getElementById(modal.modal).addEventListener("hidden.bs.modal", () => reiniciarModalCarga(modal));
    });
  }

  document.addEventListener("DOMContentLoaded", iniciarCargas);

  // ---------- Rectificaciones: corredor (R2) ----------
  let factoresRect = {};

  const ESTADO_CLASE = { PENDIENTE: "warning", APROBADA: "success", RECHAZADA: "danger" };

  function actualizarBotonRect() {
    const c = estado.seleccionada;
    // Solo se puede solicitar en calificaciones de período cerrado de la corredora del usuario
    const ok = !!c && c.estado_periodo === "CERRADO" && c.origen === "CORREDOR";
    $("btnSolicitarRect").disabled = !ok;
  }

  function pintarFactoresRect() {
    const lista = $("rectListaFactores");
    lista.replaceChildren();
    Object.entries(factoresRect).forEach(([col, valor]) => {
      const li = document.createElement("li");
      li.textContent = `Columna ${col}: ${valor}`;
      lista.appendChild(li);
    });
  }

  function abrirSolicitudRect() {
    const c = estado.seleccionada;
    if (!c) return;
    factoresRect = {};
    pintarFactoresRect();
    $("rectMotivo").value = "";
    $("rectCol").value = "";
    $("rectFactor").value = "";
    $("rectMensajes").classList.add("d-none");
    $("rectResumen").textContent = `${c.instrumento} · ejercicio ${c.ejercicio_comercial} · secuencia ${c.secuencia_evento}`;
    bootstrap.Modal.getOrCreateInstance($("modalSolicitarRect")).show();
  }

  function agregarFactorRect() {
    const col = $("rectCol").value.trim();
    const valor = $("rectFactor").value.trim();
    if (!col || !valor) return;
    factoresRect[col] = valor;
    pintarFactoresRect();
    $("rectCol").value = "";
    $("rectFactor").value = "";
  }

  async function enviarSolicitudRect() {
    const c = estado.seleccionada;
    const motivo = $("rectMotivo").value.trim();
    if (!motivo) {
      $("rectMensajes").textContent = "Debe escribir el motivo de la rectificación.";
      $("rectMensajes").classList.remove("d-none");
      return;
    }
    if (Object.keys(factoresRect).length === 0) {
      $("rectMensajes").textContent = "Agregue al menos un factor propuesto.";
      $("rectMensajes").classList.remove("d-none");
      return;
    }
    try {
      await api("/api/rectificaciones/", { metodo: "POST", cuerpo: {
        calificacion: c.id, motivo_rectificacion: motivo, valores_propuestos: factoresRect } });
      bootstrap.Modal.getInstance($("modalSolicitarRect")).hide();
      mostrarMensaje("Solicitud enviada: queda pendiente de aprobación.", "success");
    } catch (error) {
      if (error.message === "sesion_expirada") return;
      const d = error.datos;
      $("rectMensajes").textContent = d && d.detail ? (Array.isArray(d.detail) ? d.detail.join(" ") : d.detail) : textoDeError(d);
      $("rectMensajes").classList.remove("d-none");
    }
  }

  async function abrirMisRect() {
    try {
      const datos = await api("/api/rectificaciones/");
      const cuerpo = $("tablaMisRect");
      cuerpo.replaceChildren();
      if (datos.results.length === 0) {
        cuerpo.appendChild(filaVacia(6, "No tiene solicitudes."));
      }
      datos.results.forEach((r) => {
        const tr = document.createElement("tr");
        tr.appendChild(celdaTexto(new Date(r.fecha_solicitud).toLocaleDateString("es-CL")));
        tr.appendChild(celdaTexto(r.calificacion_detalle.instrumento));
        tr.appendChild(celdaTexto(r.calificacion_detalle.secuencia_evento));
        tr.appendChild(celdaTexto(r.motivo_rectificacion));
        const badge = document.createElement("td");
        const span = document.createElement("span");
        span.className = `badge bg-${ESTADO_CLASE[r.estado_solicitud] || "secondary"}`;
        span.textContent = r.estado_nombre;
        badge.appendChild(span);
        tr.appendChild(badge);
        tr.appendChild(celdaTexto(r.observacion_supervisor || "-"));
        cuerpo.appendChild(tr);
      });
      bootstrap.Modal.getOrCreateInstance($("modalMisRect")).show();
    } catch (error) {
      if (error.message === "sesion_expirada") return;
      mostrarMensaje(textoDeError(error.datos) || "No se pudo cargar tus solicitudes.");
    }
  }

  function iniciarRectificacionesCorredor() {
    $("btnSolicitarRect").addEventListener("click", abrirSolicitudRect);
    $("btnAgregarFactorRect").addEventListener("click", agregarFactorRect);
    $("btnEnviarRect").addEventListener("click", enviarSolicitudRect);
    $("btnMisRect").addEventListener("click", abrirMisRect);
  }

  document.addEventListener("DOMContentLoaded", iniciarRectificacionesCorredor);

  // ---------- Rectificaciones: supervisor (R3) ----------
  let rectificacionRechazar = null;

  function pintarPendientes(solicitudes) {
    const cuerpo = $("tablaPendientesRect");
    cuerpo.replaceChildren();
    if (solicitudes.length === 0) {
      cuerpo.appendChild(filaVacia(6, "No hay solicitudes pendientes."));
      return;
    }
    solicitudes.forEach((r) => {
      const tr = document.createElement("tr");
      tr.appendChild(celdaTexto(r.solicitante_email));
      tr.appendChild(celdaTexto(`${r.calificacion_detalle.instrumento} · ${r.calificacion_detalle.ejercicio_comercial} · sec. ${r.calificacion_detalle.secuencia_evento}`));
      tr.appendChild(celdaTexto(Object.entries(r.valores_originales).map(([c, v]) => `${c}: ${v}`).join(" · ")));
      tr.appendChild(celdaTexto(Object.entries(r.valores_propuestos).map(([c, v]) => `${c}: ${v}`).join(" · ")));
      tr.appendChild(celdaTexto(r.motivo_rectificacion));

      const acciones = document.createElement("td");
      acciones.className = "text-nowrap";
      const aprobar = document.createElement("button");
      aprobar.className = "btn btn-sm btn-success me-1";
      aprobar.textContent = "APROBAR";
      aprobar.addEventListener("click", () => resolverRect(r.id, true));
      const rechazar = document.createElement("button");
      rechazar.className = "btn btn-sm btn-outline-danger";
      rechazar.textContent = "RECHAZAR";
      rechazar.addEventListener("click", () => abrirRechazo(r.id));
      acciones.append(aprobar, rechazar);
      tr.appendChild(acciones);
      cuerpo.appendChild(tr);
    });
  }

  async function abrirPendientes() {
    try {
      const datos = await api("/api/rectificaciones/?estado=PENDIENTE");
      $("pendientesMensajes").classList.add("d-none");
      pintarPendientes(datos.results);
      bootstrap.Modal.getOrCreateInstance($("modalPendientesRect")).show();
    } catch (error) {
      if (error.message === "sesion_expirada") return;
      mostrarMensaje(textoDeError(error.datos) || "No se pudieron cargar las solicitudes.");
    }
  }

  async function resolverRect(id, aprobada, observacion = "") {
    const accion = aprobada ? "aprobar" : "rechazar";
    try {
      await api(`/api/rectificaciones/${id}/${accion}/`, { metodo: "POST", cuerpo: { observacion } });
      mostrarMensaje(aprobada ? "Solicitud aprobada." : "Solicitud rechazada.", "success");
      abrirPendientes();
    } catch (error) {
      if (error.message === "sesion_expirada") return;
      $("pendientesMensajes").textContent = textoDeError(error.datos) || "No se pudo resolver la solicitud.";
      $("pendientesMensajes").classList.remove("d-none");
    }
  }

  function abrirRechazo(id) {
    rectificacionRechazar = id;
    $("rechazoObservacion").value = "";
    $("rechazoMensaje").classList.add("d-none");
    bootstrap.Modal.getOrCreateInstance($("modalRechazarRect")).show();
  }

  async function confirmarRechazo() {
    const observacion = $("rechazoObservacion").value.trim();
    if (!observacion) {
      $("rechazoMensaje").textContent = "Debe escribir el motivo del rechazo.";
      $("rechazoMensaje").classList.remove("d-none");
      return;
    }
    bootstrap.Modal.getInstance($("modalRechazarRect")).hide();
    await resolverRect(rectificacionRechazar, false, observacion);
  }

  function mostrarBotonSupervisor() {
    const usuario = window.usuarioActual || {};
    // El supervisor ve el botón; los demás roles no
    $("btnPendientesRect").classList.toggle("d-none", usuario.rol !== "SUPERVISOR");
  }

  function iniciarRectificacionesSupervisor() {
    $("btnPendientesRect").addEventListener("click", abrirPendientes);
    $("btnConfirmarRechazo").addEventListener("click", confirmarRechazo);
    mostrarBotonSupervisor();
  }

  document.addEventListener("DOMContentLoaded", iniciarRectificacionesSupervisor);

  // Lo que usarán los pasos siguientes (modales de ingreso, modificar y cargas)
  window.mantenedor = { api, textoDeError, mostrarMensaje, ocultarMensaje, cargar, filtros, estado, csrfToken };
})();