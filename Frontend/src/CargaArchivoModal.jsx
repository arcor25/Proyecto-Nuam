import { useState } from 'react';
import { procesarCarga, subirCarga, validarCarga } from './api';

// Formato que exige el backend (cargas/models.py): 38 columnas, separador ; o ,
const CAMPOS_FIJOS = ['EJERCICIO', 'MERCADO', 'NEMOTECNICO', 'FEC_PAGO', 'SEC_EVE', 'NUM_DIVIDENDO', 'TIPO_SOCIEDAD', 'VALOR_HISTORICO'];
const COLUMNAS_FACTOR = Array.from({ length: 30 }, (_, i) => `F${i + 8}`);
const ENCABEZADO = [...CAMPOS_FIJOS, ...COLUMNAS_FACTOR];
const COLUMNAS_VISIBLES = 6; // F8 a F13 en la tabla

function descargarPlantilla(tipo) {
    const ejemplo = tipo === 'MONTOS'
        ? ['2025', 'ACN', 'NEMO_EJEMPLO', '02-01-2025', '10001', '1', 'A', '0', '1000', '500', ...Array(28).fill('0')]
        : ['2025', 'ACN', 'NEMO_EJEMPLO', '02-01-2025', '10001', '1', 'A', '0', '0,5', '0,25', ...Array(28).fill('0')];
    const contenido = `${ENCABEZADO.join(';')}\n${ejemplo.join(';')}\n`;
    const url = URL.createObjectURL(new Blob([contenido], { type: 'text/csv;charset=utf-8' }));
    const enlace = document.createElement('a');
    enlace.href = url;
    enlace.download = `plantilla_carga_${tipo.toLowerCase()}.csv`;
    enlace.click();
    URL.revokeObjectURL(url);
}

const CargaArchivoModal = ({ show, titulo, tipo, onCerrar, onCargado }) => {
    const [carga, setCarga] = useState(null);            // respuesta de POST /api/cargas/
    const [validacion, setValidacion] = useState(null);  // respuesta de /validar/
    const [resultado, setResultado] = useState(null);    // respuesta de /procesar/
    const [error, setError] = useState('');
    const [ocupado, setOcupado] = useState(false);
    const [verFormato, setVerFormato] = useState(false);

    if (!show) return null;

    const reiniciar = () => {
        setCarga(null);
        setValidacion(null);
        setResultado(null);
        setError('');
        setVerFormato(false);
    };

    const handleCerrar = () => {
        reiniciar();
        onCerrar();
    };

    const ejecutar = async (accion) => {
        setError('');
        setOcupado(true);
        try {
            await accion();
        } catch (err) {
            setError(err.message);
        } finally {
            setOcupado(false);
        }
    };

    const handleFileChange = (e) => {
        const archivo = e.target.files[0];
        e.target.value = ''; // permite volver a elegir el mismo archivo
        if (!archivo) return;
        reiniciar();
        ejecutar(async () => {
            const respuesta = await subirCarga(archivo, tipo);
            setCarga(respuesta);
            if (!respuesta.formato_valido) {
                setError(`El archivo no tiene el formato esperado: cada fila debe tener ${ENCABEZADO.length} columnas (use VER FORMATO).`);
            }
        });
    };

    const handleCalcular = () => ejecutar(async () => {
        setValidacion(await validarCarga(carga.id));
    });

    const handleGrabar = () => ejecutar(async () => {
        const respuesta = await procesarCarga(carga.id);
        setResultado(respuesta);
        const r = respuesta.resumen || {};
        if (r.validas) {
            await onCargado(`Carga "${respuesta.nombre_archivo.split('/').pop()}":${r.creadas ?? 0} creadas, ${r.actualizadas ?? 0} actualizadas, ${r.rechazadas ?? 0} rechazadas.`);
        }
    });

    // Filas a mostrar: resultado de la validación si existe; si no, la previsualización del archivo
    const filasValidacion = validacion?.filas || [];
    const filasPrevias = carga?.previsualizacion?.filas || [];
    const hayFilas = validacion ? filasValidacion.length > 0 : filasPrevias.length > 0;
    const yaGrabado = Boolean(resultado);

    return (
        <div className="modal show d-block bg-dark bg-opacity-50" tabIndex="-1">
            <div className="modal-dialog modal-xl">
                <div className="modal-content border-secondary shadow-lg">
                    <div className="modal-header py-2 bg-light border-top border-4 border-warning">
                        <h6 className="modal-title text-primary fw-bold mb-0">{titulo}</h6>
                        <button type="button" className="btn-close" onClick={handleCerrar}></button>
                    </div>
                    <div className="modal-body p-3" style={{ fontSize: '0.8rem' }}>
                        <ul className="nav nav-tabs mb-2">
                            <li className="nav-item">
                                <span className="nav-link active bg-primary text-white py-1 px-3 fw-bold" style={{ backgroundColor: '#1C4E80' }}>
                                    Archivo{carga ? `: ${carga.nombre_archivo.split('/').pop()}` : ''}
                                </span>
                            </li>
                        </ul>

                        {error && <div className="alert alert-danger py-2 small">{error}</div>}

                        {verFormato && (
                            <div className="alert alert-info py-2 small">
                                Archivo <strong>.csv</strong> con encabezado y <strong>{ENCABEZADO.length} columnas</strong> separadas por <code>;</code> o <code>,</code>:
                                <div className="mt-1"><code>{CAMPOS_FIJOS.join(' ; ')} ; F8 … F37</code></div>
                                <div className="mt-1">
                                    Fecha en formato DD-MM-AAAA, secuencia mayor a 10.000, tipo de sociedad A o C (o vacío), decimales con coma o punto y sin separador de miles.
                                    {tipo === 'MONTOS'
                                        ? ' Las columnas F8 a F37 son montos: los factores se calculan dividiendo cada monto por la suma de F8 a F19.'
                                        : ' Las columnas F8 a F37 son factores entre 0 y 1 (hasta 8 decimales); la suma de F8 a F19 no puede superar 1.'}
                                </div>
                                <button className="btn btn-sm btn-outline-primary mt-2" onClick={() => descargarPlantilla(tipo)}>Descargar plantilla</button>
                            </div>
                        )}

                        {resultado && (
                            <div className={`alert py-2 small ${resultado.errores?.length ? 'alert-warning' : 'alert-success'}`}>
                                <strong>{resultado.estado_carga_nombre}.</strong>{' '}
                                {resultado.resumen && `Creadas: ${resultado.resumen.creadas ?? 0} · Actualizadas: ${resultado.resumen.actualizadas ?? 0} · Rechazadas: ${resultado.resumen.rechazadas ?? 0}`}
                                {resultado.errores?.length > 0 && (
                                    <ul className="mb-0 mt-1">
                                        {resultado.errores.slice(0, 20).map((e, i) => <li key={i}>{e}</li>)}
                                        {resultado.errores.length > 20 && <li>… y {resultado.errores.length - 20} más</li>}
                                    </ul>
                                )}
                            </div>
                        )}

                        <div className="table-responsive border rounded" style={{ minHeight: '200px', maxHeight: '300px' }}>
                            <table className="table table-sm table-bordered table-striped mb-0 text-nowrap" style={{ fontSize: '0.75rem' }}>
                                <thead className="table-light sticky-top">
                                    <tr>
                                        {validacion && <><th>FILA</th><th>ESTADO</th></>}
                                        <th>EJERCICIO</th><th>MERCADO</th><th>NEMO...</th><th>FEC_PAGO</th><th>SEC_EVE</th><th>TIPO_SOC</th>
                                        {COLUMNAS_FACTOR.slice(0, COLUMNAS_VISIBLES).map((c) => <th key={c}>{validacion ? `${c} factor` : c}</th>)}
                                    </tr>
                                </thead>
                                <tbody>
                                    {!hayFilas && (
                                        <tr><td colSpan={validacion ? 14 : 12} className="text-center text-muted py-5">
                                            {ocupado ? 'Procesando…' : 'No hay registros. Seleccione un archivo .csv.'}
                                        </td></tr>
                                    )}
                                    {validacion
                                        ? filasValidacion.map((f) => (
                                            <tr key={f.fila} className={f.estado === 'OK' ? '' : 'table-danger'}>
                                                <td>{f.fila}</td>
                                                <td title={f.motivo || ''}>{f.estado === 'OK' ? 'OK' : `ERROR: ${f.motivo}`}</td>
                                                {f.datos.slice(0, 5).map((v, i) => <td key={i}>{v}</td>)}
                                                <td>{f.datos[6]}</td>
                                                {Array.from({ length: COLUMNAS_VISIBLES }, (_, i) => <td key={i}>{f.factores?.[String(i + 8)] ?? ''}</td>)}
                                            </tr>
                                        ))
                                        : filasPrevias.map((fila, idx) => (
                                            <tr key={idx}>
                                                {fila.slice(0, 5).map((v, i) => <td key={i}>{v}</td>)}
                                                <td>{fila[6]}</td>
                                                {fila.slice(8, 8 + COLUMNAS_VISIBLES).map((v, i) => <td key={i}>{v}</td>)}
                                            </tr>
                                        ))}
                                </tbody>
                            </table>
                        </div>
                        <div className="d-flex justify-content-between align-items-center bg-light border border-top-0 p-1 px-2 text-muted" style={{ fontSize: '0.75rem' }}>
                            <span className="badge bg-secondary">{validacion ? validacion.total : carga?.total_filas ?? 0}</span>
                            <span>
                                {validacion
                                    ? `${validacion.validas} válidas · ${validacion.rechazadas} con errores`
                                    : carga ? `${carga.total_filas} registros (se muestran los primeros 10)` : 'No hay registros.'}
                            </span>
                        </div>
                    </div>
                    <div className="modal-footer justify-content-between py-2 bg-light">
                        <label className={`btn btn-sm btn-outline-primary fw-bold ${ocupado ? 'disabled' : ''}`}>
                            Seleccionar Archivo
                            <input type="file" accept=".csv" onChange={handleFileChange} hidden disabled={ocupado} />
                        </label>
                        <div className="d-flex gap-2">
                            <button className="btn btn-sm text-white px-3 fw-bold" style={{ backgroundColor: '#1C4E80' }}
                                onClick={handleCalcular} disabled={!carga?.formato_valido || ocupado || yaGrabado}>
                                {tipo === 'MONTOS' ? 'CALCULAR FACTORES' : 'VALIDAR'}
                            </button>
                            <button className="btn btn-sm text-white px-4 fw-bold" style={{ backgroundColor: '#1C4E80' }}
                                onClick={handleGrabar} disabled={!carga?.formato_valido || ocupado || yaGrabado}>
                                {ocupado ? 'PROCESANDO…' : 'GRABAR'}
                            </button>
                            <button className="btn btn-sm btn-outline-secondary px-3" onClick={handleCerrar}>{yaGrabado ? 'CERRAR' : 'CANCELAR'}</button>
                            <button className="btn btn-sm btn-outline-primary px-3" onClick={() => setVerFormato(!verFormato)}>VER FORMATO</button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default CargaArchivoModal;
