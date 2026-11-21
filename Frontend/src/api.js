// Cliente de la API de Django (JWT). En desarrollo, Vite reenvía /api al backend (ver vite.config.js).
const BASE = import.meta.env.VITE_API_URL || '/api';
const CLAVE_SESION = 'nuam_sesion';

function leerSesion() {
    try {
        return JSON.parse(sessionStorage.getItem(CLAVE_SESION)) || null;
    } catch {
        return null;
    }
}

function guardarSesion(sesion) {
    try {
        if (sesion) sessionStorage.setItem(CLAVE_SESION, JSON.stringify(sesion));
        else sessionStorage.removeItem(CLAVE_SESION);
    } catch {
        // sin almacenamiento: la sesión dura solo mientras la página esté abierta
    }
}

let sesion = leerSesion();
let alExpirar = () => {};

export function obtenerUsuario() {
    return sesion?.usuario || null;
}

export function alCerrarSesion(callback) {
    alExpirar = callback;
}

/** Error con el mensaje del backend listo para mostrar. */
export class ErrorApi extends Error {
    constructor(status, datos) {
        super(mensajeDeError(datos) || `Error ${status}`);
        this.status = status;
        this.datos = datos;
    }
}

// Nombre que ve el usuario para cada campo que devuelve la API
const ETIQUETAS = {
    instrumento: 'Instrumento',
    mercado: 'Mercado',
    ejercicio_comercial: 'Año',
    secuencia_evento: 'Secuencia Evento',
    fecha_pago: 'Fecha Pago',
    valor_historico: 'Valor Histórico',
    factor_actualizacion: 'Factor Actualización',
    descripcion: 'Descripción',
    is_fut: 'FUT',
    numero_dividendo: 'N.º dividendo',
    tipo_sociedad: 'Tipo sociedad',
    archivo: 'Archivo',
    formato_tipo: 'Tipo de carga',
    email: 'Correo',
    password: 'Contraseña',
};

const etiqueta = (campo) => {
    const factor = campo.match(/^f(\d{2})$/); // f08..f37
    if (factor) return `Factor-${factor[1]}`;
    return ETIQUETAS[campo] || campo;
};

/** Convierte las respuestas de error de DRF ({campo: [mensajes]}, {detail}, [..]) en texto. */
export function mensajeDeError(datos) {
    if (!datos) return '';
    if (typeof datos === 'string') return datos;
    if (Array.isArray(datos)) return datos.map(mensajeDeError).join(' ');
    if (datos.detail) return mensajeDeError(datos.detail);
    return Object.entries(datos)
        .map(([campo, valor]) => {
            const texto = mensajeDeError(valor);
            return campo === 'non_field_errors' || campo === 'factores' ? texto : `${etiqueta(campo)}: ${texto}`;
        })
        .join(' · ');
}

async function refrescarToken() {
    if (!sesion?.refresh) return false;
    const resp = await fetch(`${BASE}/auth/refresh/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh: sesion.refresh }),
    });
    if (!resp.ok) return false;
    const datos = await resp.json();
    sesion = { ...sesion, access: datos.access, refresh: datos.refresh || sesion.refresh };
    guardarSesion(sesion);
    return true;
}

async function pedir(ruta, { method = 'GET', body, reintento = true } = {}) {
    const headers = {};
    if (sesion?.access) headers.Authorization = `Bearer ${sesion.access}`;
    const esFormulario = body instanceof FormData;
    if (body !== undefined && !esFormulario) headers['Content-Type'] = 'application/json';

    const resp = await fetch(`${BASE}${ruta}`, {
        method,
        headers,
        body: body === undefined ? undefined : esFormulario ? body : JSON.stringify(body),
    });

    if (resp.status === 401 && reintento && sesion?.refresh) {
        if (await refrescarToken()) return pedir(ruta, { method, body, reintento: false });
        cerrarSesionLocal();
        throw new ErrorApi(401, { detail: 'Su sesión expiró. Inicie sesión nuevamente.' });
    }

    const datos = leerCuerpo(await resp.text());
    if (!resp.ok) throw new ErrorApi(resp.status, datos);
    return datos;
}

function leerCuerpo(texto) {
    if (!texto) return null;
    try {
        return JSON.parse(texto);
    } catch {
        return texto;
    }
}

function cerrarSesionLocal() {
    sesion = null;
    guardarSesion(null);
    alExpirar();
}

// ---------- Autenticación ----------
export async function login(email, password) {
    const datos = await pedir('/auth/login/', { method: 'POST', body: { email, password }, reintento: false });
    sesion = { access: datos.access, refresh: datos.refresh, usuario: datos.usuario };
    guardarSesion(sesion);
    return datos.usuario;
}

export async function logout() {
    try {
        if (sesion?.refresh) await pedir('/auth/logout/', { method: 'POST', body: { refresh: sesion.refresh }, reintento: false });
    } finally {
        sesion = null;
        guardarSesion(null);
    }
}

// ---------- Calificaciones ----------
export function listarCalificaciones(filtros = {}) {
    const params = new URLSearchParams();
    Object.entries(filtros).forEach(([clave, valor]) => {
        if (valor !== '' && valor !== null && valor !== undefined && valor !== false) params.set(clave, valor);
    });
    const consulta = params.toString();
    return pedir(`/calificaciones/${consulta ? `?${consulta}` : ''}`);
}

export const crearCalificacion = (datos) => pedir('/calificaciones/', { method: 'POST', body: datos });
export const modificarCalificacion = (id, datos) => pedir(`/calificaciones/${id}/`, { method: 'PATCH', body: datos });
export const eliminarCalificacion = (id) => pedir(`/calificaciones/${id}/`, { method: 'DELETE' });
export const copiarCalificacion = (id, secuencia) =>
    pedir(`/calificaciones/${id}/copiar/`, { method: 'POST', body: secuencia ? { secuencia_evento: secuencia } : {} });

// ---------- Cargas masivas (CSV) ----------
export function subirCarga(archivo, formatoTipo) {
    const datos = new FormData();
    datos.append('archivo', archivo);
    datos.append('formato_tipo', formatoTipo);
    return pedir('/cargas/', { method: 'POST', body: datos });
}

export const validarCarga = (id) => pedir(`/cargas/${id}/validar/`, { method: 'POST' });
export const procesarCarga = (id) => pedir(`/cargas/${id}/procesar/`, { method: 'POST' });
