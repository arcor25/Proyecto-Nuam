// Conversión entre el formato de la API (CalificacionSerializer) y el que usan las pantallas.

export const COLUMNAS = Array.from({ length: 30 }, (_, i) => i + 8); // factores 8 a 37
export const clave = (columna) => `f${String(columna).padStart(2, '0')}`;

export const MERCADOS = [
    { valor: 'ACN', nombre: 'Acciones' },
    { valor: 'CFI', nombre: 'Cuotas de fondos de inversión' },
    { valor: 'FM', nombre: 'Fondos mutuos' },
];

/** '2025-01-02' -> '02-01-2025' */
export function fechaParaMostrar(iso) {
    if (!iso) return '';
    const [a, m, d] = iso.split('-');
    return `${d}-${m}-${a}`;
}

/** Acepta 'DD-MM-AAAA', 'DD/MM/AAAA' o 'AAAA-MM-DD' y devuelve 'AAAA-MM-DD' (o el texto tal cual, para que el backend informe el error). */
export function fechaParaApi(texto) {
    const limpio = String(texto || '').trim();
    const dma = limpio.match(/^(\d{1,2})[-/](\d{1,2})[-/](\d{4})$/);
    if (dma) return `${dma[3]}-${dma[2].padStart(2, '0')}-${dma[1].padStart(2, '0')}`;
    return limpio;
}

/** Números con coma o punto decimal; vacío = 0. */
export const numeroParaApi = (texto) => String(texto ?? '').trim().replace(',', '.') || '0';

/** Calificación de la API -> fila de la tabla (incluye los 30 factores). */
export function filaDesdeApi(c) {
    const fila = {
        id: c.id,
        ejercicio: c.ejercicio_comercial,
        instrumento: c.instrumento,
        mercado: c.mercado_codigo,
        emisor: c.emisor,
        fechaPago: fechaParaMostrar(c.fecha_pago),
        descripcion: c.descripcion,
        secuencia: c.secuencia_evento,
        factorAct: c.factor_actualizacion,
        valorHistorico: c.valor_historico,
        isFut: c.is_fut,
        origen: c.origen,
        origenDato: c.origen_dato_nombre,
        estadoPeriodo: c.estado_periodo,
    };
    COLUMNAS.forEach((col) => {
        fila[clave(col)] = c.factores?.[String(col)] ?? '0.00000000';
    });
    return fila;
}

/** Toma f08..f37 de un formulario y los deja listos para la API. */
export function factoresParaApi(formData) {
    const salida = {};
    COLUMNAS.forEach((col) => {
        salida[clave(col)] = numeroParaApi(formData[clave(col)]);
    });
    return salida;
}
