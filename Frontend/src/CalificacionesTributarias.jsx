import { useState } from 'react';
import FormularioIngresoModal from './FormularioIngresoModal';
import FormularioModificarModal from './FormularioModificarModal';
import CargaFactorModal from './CargaFactorModal';
import CargaMontoModal from './CargaMontoModal';

const CalificacionesTributarias = () => {
    // Filtros
    const [mercado, setMercado] = useState('ACCIONES');
    const [origen, setOrigen] = useState('CORREDOR');
    const [periodo, setPeriodo] = useState('2025');
    const [pendiente, setPendiente] = useState(false);

    // Estado de Datos y Selección
    const [datos, setDatos] = useState([]);
    const [filaSeleccionada, setFilaSeleccionada] = useState(null);

    // Modales
    const [mostrarModalIngreso, setMostrarModalIngreso] = useState(false);
    const [mostrarModalModificar, setMostrarModalModificar] = useState(false);
    const [mostrarModalCargaFactor, setMostrarModalCargaFactor] = useState(false);
    const [mostrarModalCargaMonto, setMostrarModalCargaMonto] = useState(false);

    const handleLimpiar = () => {
        setMercado('ACCIONES');
        setOrigen('CORREDOR');
        setPeriodo('2025');
        setPendiente(false);
    };

    const handleGuardarNuevaFila = (nuevaFila) => {
        setDatos([...datos, nuevaFila]);
    };

    const handleGuardarFilaModificada = (filaEditada) => {
        const nuevosDatos = [...datos];
        nuevosDatos[filaSeleccionada] = filaEditada;
        setDatos(nuevosDatos);
    };

    const handleGuardarCargaMasiva = (nuevasFilas) => {
        setDatos([...datos, ...nuevasFilas]);
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
                    <select className="form-select form-select-sm" value={mercado} onChange={(e) => setMercado(e.target.value)}>
                        <option value="ACCIONES">ACCIONES</option>
                        <option value="BONOS">BONOS</option>
                    </select>
                </div>

                <div className="col-auto ms-2"><label className="form-label mb-0 small">Origen</label></div>
                <div className="col-md-2">
                    <select className="form-select form-select-sm" value={origen} onChange={(e) => setOrigen(e.target.value)}>
                        <option value="CORREDOR">CORREDOR</option>
                        <option value="BOLSA">BOLSA</option>
                    </select>
                </div>

                <div className="col-auto ms-2"><label className="form-label mb-0 small">Periodo Comercial</label></div>
                <div className="col-md-2">
                    <select className="form-select form-select-sm" value={periodo} onChange={(e) => setPeriodo(e.target.value)}>
                        <option value="2025">2025</option>
                        <option value="2024">2024</option>
                    </select>
                </div>

                <div className="col-md-2 ms-auto text-end">
                    <button className="btn btn-sm w-100 mb-1 text-white fw-bold" style={{ backgroundColor: '#1C4E80' }}>
                        🔍 BUSCAR
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
                    checked={pendiente}
                    onChange={(e) => setPendiente(e.target.checked)}
                />
                <label className="form-check-label small" htmlFor="chkPendiente">
                    Calificación Pendiente
                </label>
            </div>

            {/* TABLA DE RESULTADOS */}
            <div className="table-responsive border rounded" style={{ maxHeight: '380px' }}>
                <table className="table table-sm table-bordered table-hover mb-0 text-nowrap align-middle" style={{ fontSize: '0.8rem' }}>
                    <thead className="table-light sticky-top">
                        <tr>
                            <th>Ejercicio</th>
                            <th>Instrumento ⚙️</th>
                            <th>Fecha Pago 📅</th>
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
                            datos.map((item, index) => (
                                <tr
                                    key={index}
                                    className={filaSeleccionada === index ? "table-active" : ""}
                                    onClick={() => setFilaSeleccionada(index)}
                                    style={{ cursor: 'pointer' }}
                                >
                                    <td className="text-center">{item.ejercicio}</td>
                                    <td className="fw-semibold">{item.instrumento || item.nemotecnico}</td>
                                    <td className="text-center">{item.fechaPago}</td>
                                    <td>{item.descripcion}</td>
                                    <td className="text-end">{item.secuencia}</td>
                                    <td className="text-end">{item.factorAct || 0}</td>
                                    <td className="text-end">{item.f08}</td>
                                    <td className="text-end">{item.f09}</td>
                                    <td className="text-end">{item.f10}</td>
                                    <td className="text-end">{item.f11}</td>
                                    <td className="text-end">{item.f12}</td>
                                </tr>
                            ))
                        ) : (
                            <tr>
                                <td colSpan="11" className="text-center text-muted py-4">
                                    No hay registros disponibles. Utilice la barra de búsqueda o cargue un archivo.
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>

            {/* PAGINACIÓN */}
            <div className="d-flex justify-content-between align-items-center mt-2 px-1">
                <div className="btn-group btn-group-sm">
                    <button className="btn btn-outline-secondary">«</button>
                    <button className="btn btn-outline-secondary">‹</button>
                    <button className="btn btn-primary active">1</button>
                    <button className="btn btn-outline-secondary">›</button>
                    <button className="btn btn-outline-secondary">»</button>
                </div>
                <span className="text-muted small">
                    Elementos mostrados {datos.length} de {datos.length}
                </span>
            </div>

            {/* BOTONES ACCIONES */}
            <div className="d-flex justify-content-between align-items-center mt-3 pt-2 border-top">
                <div className="d-flex gap-2">
                    <button
                        className="btn btn-sm text-white px-3 fw-bold"
                        style={{ backgroundColor: '#1C4E80' }}
                        onClick={() => setMostrarModalIngreso(true)}
                    >
                        INGRESAR
                    </button>

                    <button
                        className="btn btn-sm btn-outline-secondary px-3"
                        disabled={filaSeleccionada === null}
                        onClick={() => setMostrarModalModificar(true)}
                    >
                        MODIFICAR
                    </button>

                    <button className="btn btn-sm btn-outline-secondary px-3" disabled>
                        ELIMINAR
                    </button>
                    <button className="btn btn-sm btn-outline-secondary px-3" disabled>
                        COPIAR
                    </button>

                    <button
                        className="btn btn-sm btn-outline-primary px-3"
                        onClick={() => setMostrarModalCargaFactor(true)}
                    >
                        CARGA X FACTOR
                    </button>

                    <button
                        className="btn btn-sm btn-outline-primary px-3"
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

            {/* RENDERIZADO DE MODALES */}
            <FormularioIngresoModal
                show={mostrarModalIngreso}
                onCerrar={() => setMostrarModalIngreso(false)}
                onGuardar={handleGuardarNuevaFila}
            />

            <FormularioModificarModal
                show={mostrarModalModificar}
                datosFila={datos[filaSeleccionada]}
                onCerrar={() => setMostrarModalModificar(false)}
                onGuardar={handleGuardarFilaModificada}
            />

            <CargaFactorModal
                show={mostrarModalCargaFactor}
                onCerrar={() => setMostrarModalCargaFactor(false)}
                onGuardar={handleGuardarCargaMasiva}
            />

            <CargaMontoModal
                show={mostrarModalCargaMonto}
                onCerrar={() => setMostrarModalCargaMonto(false)}
                onGuardar={handleGuardarCargaMasiva}
            />

        </div>
    );
};

export default CalificacionesTributarias;