import { useEffect, useState } from 'react';
import FormularioIngresoModal from './FormularioIngresoModal';
import FormularioModificarModal from './FormularioModificarModal';
import CargaFactorModal from './CargaFactorModal';
import CargaMontoModal from './CargaMontoModal';
import {
    copiarCalificacion, crearCalificacion, eliminarCalificacion, listarCalificaciones, modificarCalificacion,
} from './api';
import { filaDesdeApi, MERCADOS } from './calificacion';

const TAMANO_PAGINA = 50; // PAGE_SIZE de Django REST Framework
const ANIO_ACTUAL = new Date().getFullYear();
const PERIODOS = Array.from({ length: 6 }, (_, i) => String(ANIO_ACTUAL - i));
const FILTROS_INICIALES = { mercado: '', origen: '', periodo: '', pendiente: false };

const CalificacionesTributarias = ({ usuario }) => {
    const esCorredor = usuario?.rol === 'CORREDOR';

    // Filtros (los del formulario y los aplicados en la última búsqueda)
    const [filtros, setFiltros] = useState(FILTROS_INICIALES);
    const [filtrosAplicados, setFiltrosAplicados] = useState(FILTROS_INICIALES);
    const [pagina, setPagina] = useState(1);

    // Datos
    const [datos, setDatos] = useState([]);
    const [total, setTotal] = useState(0);
    const [cargando, setCargando] = useState(true);
    const [recarga, setRecarga] = useState(0);
    const [mensaje, setMensaje] = useState(null); // { tipo: 'success' | 'danger', texto }
    const [idSeleccionado, setIdSeleccionado] = useState(null);

    // Modales
    const [mostrarModalIngreso, setMostrarModalIngreso] = useState(false);
    const [mostrarModalModificar, setMostrarModalModificar] = useState(false);
    const [mostrarModalCargaFactor, setMostrarModalCargaFactor] = useState(false);
    const [mostrarModalCargaMonto, setMostrarModalCargaMonto] = useState(false);

    const filaSeleccionada = datos.find((f) => f.id === idSeleccionado) || null;
    const esPropia = filaSeleccionada?.origen === 'CORREDOR'; // la API solo muestra las de Bolsa y las de su corredora
    const totalPaginas = Math.max(1, Math.ceil(total / TAMANO_PAGINA));

    // Consulta la API cada vez que cambian los filtros aplicados, la página o se pide recargar
    useEffect(() => {
        let vigente = true; // ignora respuestas de consultas anteriores
        listarCalificaciones({
            mercado: filtrosAplicados.mercado,
            origen: filtrosAplicados.origen,
            ejercicio: filtrosAplicados.periodo,
            pendiente: filtrosAplicados.pendiente ? '1' : '',
            page: pagina,
        })
            .then((respuesta) => {
                if (!vigente) return;
                setDatos(respuesta.results.map(filaDesdeApi));
                setTotal(respuesta.count);
            })
            .catch((err) => {
                if (!vigente) return;
                setDatos([]);
                setTotal(0);
                setMensaje({ tipo: 'danger', texto: `No se pudieron cargar las calificaciones: ${err.message}` });
            })
            .finally(() => {
                if (vigente) setCargando(false);
            });
        return () => {
            vigente = false;
        };
    }, [filtrosAplicados, pagina, recarga]);

    const recargar = () => {
        setCargando(true);
        setRecarga((n) => n + 1);
    };

    const cambiarFiltro = (campo, valor) => setFiltros({ ...filtros, [campo]: valor });

    // Nuevo objeto en cada búsqueda: así el efecto consulta aunque los filtros no hayan cambiado
    const buscar = (nuevosFiltros) => {
        setCargando(true);
        setMensaje(null);
        setIdSeleccionado(null);
        setPagina(1);
        setFiltrosAplicados({ ...nuevosFiltros });
    };

    const handleBuscar = () => buscar(filtros);

    const handleLimpiar = () => {
        setFiltros(FILTROS_INICIALES);
        buscar(FILTROS_INICIALES);
    };

    const irAPagina = (n) => {
        const destino = Math.min(Math.max(1, n), totalPaginas);
        if (destino === pagina) return;
        setCargando(true);
        setIdSeleccionado(null);
        setPagina(destino);
    };

    // Los modales llaman a estas funciones; si la API devuelve error, el modal lo muestra y queda abierto.
    const handleGuardarNuevaFila = async (payload) => {
        const creada = await crearCalificacion(payload);
        setMensaje({ tipo: 'success', texto: `Calificación ${creada.instrumento} (${creada.ejercicio_comercial}, sec. ${creada.secuencia_evento}) ingresada.` });
        setIdSeleccionado(creada.id);
        recargar();
    };

    const handleGuardarFilaModificada = async (payload) => {
        await modificarCalificacion(filaSeleccionada.id, payload);
        setMensaje({ tipo: 'success', texto: 'Calificación modificada.' });
        recargar();
    };

    const handleEliminar = async () => {
        if (!filaSeleccionada) return;
        if (!window.confirm(`¿Eliminar la calificación ${filaSeleccionada.instrumento} (${filaSeleccionada.ejercicio}, sec. ${filaSeleccionada.secuencia})?`)) return;
        try {
            await eliminarCalificacion(filaSeleccionada.id);
            setMensaje({ tipo: 'success', texto: 'Calificación eliminada.' });
            setIdSeleccionado(null);
            recargar();
        } catch (err) {
            setMensaje({ tipo: 'danger', texto: err.message });
        }
    };

    const handleCopiar = async () => {
        if (!filaSeleccionada) return;
        const secuencia = window.prompt('Secuencia de evento para la copia (mayor a 10.000):', filaSeleccionada.secuencia);
        if (secuencia === null) return;
        try {
            const copia = await copiarCalificacion(filaSeleccionada.id, secuencia.trim());
            setMensaje({ tipo: 'success', texto: `Copia creada para su corredora (sec. ${copia.secuencia_evento}).` });
            setIdSeleccionado(copia.id);
            recargar();
        } catch (err) {
            setMensaje({ tipo: 'danger', texto: err.message });
        }
    };

    const handleCargaTerminada = (texto) => {
        setMensaje({ tipo: 'success', texto });
        recargar();
    };

    return (
        <div className="container-fluid bg-white p-3 border rounded shadow-sm">
            {/* HEADER */}
            <div className="d-flex justify-content-between align-items-center mb-3 border-bottom pb-2">
                <h5 className="fw-bold mb-0" style={{ color: '#1B4965' }}>
                    Calificaciones Tributarias
                </h5>
                <div>
                    <button className="btn btn-sm btn-link text-decoration-none text-secondary pe-1">—</button>
                    <button className="btn btn-sm btn-link text-decoration-none text-secondary">✕</button>
                </div>
            </div>

            {/* FILTROS */}
            <div className="row g-2 align-items-center mb-2">
                <div className="col-auto"><label className="form-label mb-0 small">Mercado</label></div>
                <div className="col-md-2">
                    <select className="form-select form-select-sm" value={filtros.mercado} onChange={(e) => cambiarFiltro('mercado', e.target.value)}>
                        <option value="">TODOS</option>
                        {MERCADOS.map((m) => <option key={m.valor} value={m.valor}>{m.nombre.toUpperCase()}</option>)}
                    </select>
                </div>

                <div className="col-auto ms-2"><label className="form-label mb-0 small">Origen</label></div>
                <div className="col-md-2">
                    <select className="form-select form-select-sm" value={filtros.origen} onChange={(e) => cambiarFiltro('origen', e.target.value)}>
                        <option value="">TODOS</option>
                        <option value="CORREDOR">CORREDOR</option>
                        <option value="BOLSA">BOLSA</option>
                    </select>
                </div>

                <div className="col-auto ms-2"><label className="form-label mb-0 small">Periodo Comercial</label></div>
                <div className="col-md-2">
                    <select className="form-select form-select-sm" value={filtros.periodo} onChange={(e) => cambiarFiltro('periodo', e.target.value)}>
                        <option value="">TODOS</option>
                        {PERIODOS.map((p) => <option key={p} value={p}>{p}</option>)}
                    </select>
                </div>

                <div className="col-md-2 ms-auto text-end">
                    <button className="btn btn-sm w-100 mb-1 text-white fw-bold" style={{ backgroundColor: '#1C4E80' }} onClick={handleBuscar} disabled={cargando}>
                        {cargando ? 'BUSCANDO…' : '🔍 BUSCAR'}
                    </button>
                    <button className="btn btn-sm btn-outline-secondary w-100" onClick={handleLimpiar}>
                        LIMPIAR
                    </button>
                </div>
            </div>

            <div className="form-check mb-3">
                <input
                    type="checkbox"
                    className="form-check-input"
                    id="chkPendiente"
                    checked={filtros.pendiente}
                    onChange={(e) => cambiarFiltro('pendiente', e.target.checked)}
                />
                <label className="form-check-label small" htmlFor="chkPendiente">
                    Calificación Pendiente
                </label>
            </div>

            {mensaje && (
                <div className={`alert alert-${mensaje.tipo} py-2 small d-flex justify-content-between align-items-start`}>
                    <span>{mensaje.texto}</span>
                    <button type="button" className="btn-close btn-sm ms-2" onClick={() => setMensaje(null)}></button>
                </div>
            )}

            {/* TABLA DE RESULTADOS */}
            <div className="table-responsive border rounded" style={{ maxHeight: '380px' }}>
                <table className="table table-sm table-bordered table-hover mb-0 text-nowrap align-middle" style={{ fontSize: '0.8rem' }}>
                    <thead className="table-light sticky-top">
                        <tr>
                            <th>Ejercicio</th>
                            <th>Instrumento</th>
                            <th>Origen</th>
                            <th>Fecha Pago</th>
                            <th>Descripción</th>
                            <th>Secuencia Evento</th>
                            <th>Factor de Actuali...</th>
                            <th>Factor-08</th>
                            <th>Factor-09</th>
                            <th>Factor-10</th>
                            <th>Factor-11</th>
                            <th>Factor-12</th>
                        </tr>
                    </thead>
                    <tbody>
                        {datos.length > 0 ? (
                            datos.map((item) => (
                                <tr
                                    key={item.id}
                                    className={idSeleccionado === item.id ? 'table-active' : ''}
                                    onClick={() => setIdSeleccionado(item.id)}
                                    style={{ cursor: 'pointer' }}
                                >
                                    <td className="text-center">{item.ejercicio}</td>
                                    <td className="fw-semibold">{item.instrumento}</td>
                                    <td className="text-center">{item.origen === 'CORREDOR' ? 'Corredor' : 'Bolsa'}</td>
                                    <td className="text-center">{item.fechaPago}</td>
                                    <td>{item.descripcion}</td>
                                    <td className="text-end">{item.secuencia}</td>
                                    <td className="text-end">{item.factorAct}</td>
                                    <td className="text-end">{item.f08}</td>
                                    <td className="text-end">{item.f09}</td>
                                    <td className="text-end">{item.f10}</td>
                                    <td className="text-end">{item.f11}</td>
                                    <td className="text-end">{item.f12}</td>
                                </tr>
                            ))
                        ) : (
                            <tr>
                                <td colSpan="12" className="text-center text-muted py-4">
                                    {cargando ? 'Cargando…' : 'No hay registros disponibles. Utilice la barra de búsqueda o cargue un archivo.'}
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>

            {/* PAGINACIÓN */}
            <div className="d-flex justify-content-between align-items-center mt-2 px-1">
                <div className="btn-group btn-group-sm">
                    <button className="btn btn-outline-secondary" disabled={pagina === 1} onClick={() => irAPagina(1)}>«</button>
                    <button className="btn btn-outline-secondary" disabled={pagina === 1} onClick={() => irAPagina(pagina - 1)}>‹</button>
                    <button className="btn btn-primary active">{pagina} / {totalPaginas}</button>
                    <button className="btn btn-outline-secondary" disabled={pagina >= totalPaginas} onClick={() => irAPagina(pagina + 1)}>›</button>
                    <button className="btn btn-outline-secondary" disabled={pagina >= totalPaginas} onClick={() => irAPagina(totalPaginas)}>»</button>
                </div>
                <span className="text-muted small">
                    Elementos mostrados {datos.length} de {total}
                </span>
            </div>

            {/* BOTONES ACCIONES */}
            <div className="d-flex justify-content-between align-items-center mt-3 pt-2 border-top">
                <div className="d-flex gap-2 flex-wrap">
                    <button
                        className="btn btn-sm text-white px-3 fw-bold"
                        style={{ backgroundColor: '#1C4E80' }}
                        disabled={!esCorredor}
                        onClick={() => setMostrarModalIngreso(true)}
                    >
                        INGRESAR
                    </button>

                    <button
                        className="btn btn-sm btn-outline-secondary px-3"
                        disabled={!esCorredor || !esPropia}
                        title={filaSeleccionada && !esPropia ? 'Las calificaciones de Bolsa no se modifican: use Copiar' : ''}
                        onClick={() => setMostrarModalModificar(true)}
                    >
                        MODIFICAR
                    </button>

                    <button className="btn btn-sm btn-outline-secondary px-3" disabled={!esCorredor || !esPropia} onClick={handleEliminar}>
                        ELIMINAR
                    </button>
                    <button className="btn btn-sm btn-outline-secondary px-3" disabled={!esCorredor || !filaSeleccionada} onClick={handleCopiar}>
                        COPIAR
                    </button>

                    <button
                        className="btn btn-sm btn-outline-primary px-3"
                        disabled={!esCorredor}
                        onClick={() => setMostrarModalCargaFactor(true)}
                    >
                        CARGA X FACTOR
                    </button>

                    <button
                        className="btn btn-sm btn-outline-primary px-3"
                        disabled={!esCorredor}
                        onClick={() => setMostrarModalCargaMonto(true)}
                    >
                        CARGA X MONTO
                    </button>
                </div>

                <div>
                    <button className="btn btn-sm btn-outline-primary px-4">
                        OPCIONES
                    </button>
                </div>
            </div>

            {!esCorredor && (
                <p className="text-muted small mt-2 mb-0">
                    Su rol ({usuario?.rol_nombre}) solo puede consultar. Ingresar, modificar, eliminar, copiar y cargar archivos es exclusivo del Corredor de Bolsa.
                </p>
            )}

            {/* RENDERIZADO DE MODALES */}
            <FormularioIngresoModal
                show={mostrarModalIngreso}
                onCerrar={() => setMostrarModalIngreso(false)}
                onGuardar={handleGuardarNuevaFila}
            />

            {mostrarModalModificar && filaSeleccionada && (
                <FormularioModificarModal
                    key={filaSeleccionada.id}
                    show
                    datosFila={filaSeleccionada}
                    onCerrar={() => setMostrarModalModificar(false)}
                    onGuardar={handleGuardarFilaModificada}
                />
            )}

            <CargaFactorModal
                show={mostrarModalCargaFactor}
                onCerrar={() => setMostrarModalCargaFactor(false)}
                onCargado={handleCargaTerminada}
            />

            <CargaMontoModal
                show={mostrarModalCargaMonto}
                onCerrar={() => setMostrarModalCargaMonto(false)}
                onCargado={handleCargaTerminada}
            />

        </div>
    );
};

export default CalificacionesTributarias;
