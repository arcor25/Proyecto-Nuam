import { useState } from 'react';
import { factoresParaApi, fechaParaApi, MERCADOS, numeroParaApi } from './calificacion';

const FormularioIngresoModal = ({ show, onCerrar, onGuardar }) => {
    // Estado con todos los campos de la pantalla
    const [formData, setFormData] = useState({
        mercado: 'ACN',
        instrumento: '',
        valorHistorico: '',
        fechaPago: '',
        eventoCapital: '',
        descripcion: '',
        secuencia: '',
        anio: String(new Date().getFullYear()),
        factorActualizacion: '0',
        isFut: false,
        ingresoMontos: false,
        f08: '', f09: '', f10: '', f11: '', f12: '', f13: '', f14: '', f15: '',
        f16: '', f17: '', rentasExentas: '', f19a: '', f20: '', f21: '', f22: '',
        f23: '', f24: '', f25: '', f26: '', f27: '', f28: '', f29: '', f30: '',
        f31: '', f32: '', f33: '', f34: '', f35: '', f36: '', f37: ''
    });
    const [error, setError] = useState('');
    const [guardando, setGuardando] = useState(false);

    if (!show) return null;

    const handleChange = (campo, valor) => {
        setFormData({ ...formData, [campo]: valor });
    };

    const handleCerrar = () => {
        setError('');
        onCerrar();
    };

    const handleGrabar = async (e) => {
        e.preventDefault();
        setError('');

        // "Rentas Exentas" es el factor 18 y "Factor-19A" el 19
        const factores = factoresParaApi({ ...formData, f18: formData.rentasExentas, f19: formData.f19a });

        // Formato que espera POST /api/calificaciones/
        const payload = {
            mercado: formData.mercado.trim().toUpperCase(),
            instrumento: formData.instrumento.trim().toUpperCase(),
            ejercicio_comercial: formData.anio.trim(),
            secuencia_evento: formData.secuencia.trim(),
            fecha_pago: fechaParaApi(formData.fechaPago),
            valor_historico: numeroParaApi(formData.valorHistorico),
            factor_actualizacion: numeroParaApi(formData.factorActualizacion),
            descripcion: formData.descripcion.trim(),
            is_fut: formData.isFut,
            ingreso_montos: formData.ingresoMontos,
            ...factores,
        };

        setGuardando(true);
        try {
            await onGuardar(payload);
            handleCerrar();
        } catch (err) {
            setError(err.message);
        } finally {
            setGuardando(false);
        }
    };

    return (
        <div className="modal show d-block bg-dark bg-opacity-50" tabIndex="-1">
            <div className="modal-dialog modal-xl modal-dialog-scrollable">
                <div className="modal-content border-secondary shadow-lg">

                    {/* HEADER DEL MODAL */}
                    <div className="modal-header py-2 bg-light">
                        <h6 className="modal-title text-primary fw-bold mb-0">
                            UI_INGRESO_CALIFICACIONES_TRIBUTARIAS
                        </h6>
                        <button type="button" className="btn-close" onClick={handleCerrar}></button>
                    </div>

                    {/* CUERPO DEL FORMULARIO */}
                    <div className="modal-body p-3 fs-7" style={{ fontSize: '0.78rem' }}>

                        {error && <div className="alert alert-danger py-2 small">{error}</div>}

                        {/* CABECERA (3 COLUMNAS) */}
                        <div className="row g-2 mb-3 bg-light p-2 border rounded">
                            <div className="col-md-4">
                                <div className="d-flex align-items-center mb-1">
                                    <span className="w-40 fw-semibold">Mercado:</span>
                                    <select className="form-select form-select-sm" value={formData.mercado} onChange={(e) => handleChange('mercado', e.target.value)}>
                                        {MERCADOS.map((m) => <option key={m.valor} value={m.valor}>{m.valor} - {m.nombre}</option>)}
                                    </select>
                                </div>
                                <div className="d-flex align-items-center mb-1">
                                    <span className="w-40 fw-semibold">Fecha Pago:</span>
                                    <input type="text" className="form-control form-control-sm" placeholder="DD-MM-AAAA" value={formData.fechaPago} onChange={(e) => handleChange('fechaPago', e.target.value)} />
                                </div>
                                <div className="d-flex align-items-center">
                                    <span className="w-40 fw-semibold">Secuencia Evento:</span>
                                    <input type="text" className="form-control form-control-sm" placeholder="mayor a 10000" value={formData.secuencia} onChange={(e) => handleChange('secuencia', e.target.value)} />
                                </div>
                            </div>

                            <div className="col-md-4">
                                <div className="d-flex align-items-center mb-1">
                                    <span className="w-40 fw-semibold">Instrumento:</span>
                                    <input type="text" className="form-control form-control-sm" value={formData.instrumento} onChange={(e) => handleChange('instrumento', e.target.value)} />
                                </div>
                                <div className="d-flex align-items-center mb-1">
                                    <span className="w-40 fw-semibold">Evento Capital:</span>
                                    <input type="text" className="form-control form-control-sm" value={formData.eventoCapital} onChange={(e) => handleChange('eventoCapital', e.target.value)} />
                                </div>
                                <div className="d-flex align-items-center mb-1">
                                    <span className="w-40 fw-semibold">Año:</span>
                                    <input type="text" className="form-control form-control-sm" value={formData.anio} onChange={(e) => handleChange('anio', e.target.value)} />
                                </div>
                                <div className="d-flex align-items-center">
                                    <span className="w-40 fw-semibold">Factor Actualización:</span>
                                    <input type="text" className="form-control form-control-sm" value={formData.factorActualizacion} onChange={(e) => handleChange('factorActualizacion', e.target.value)} />
                                </div>
                            </div>

                            <div className="col-md-4">
                                <div className="d-flex align-items-center mb-1">
                                    <span className="w-40 fw-semibold">Valor Histórico:</span>
                                    <input type="text" className="form-control form-control-sm" value={formData.valorHistorico} onChange={(e) => handleChange('valorHistorico', e.target.value)} />
                                </div>
                                <div className="d-flex align-items-center mb-1">
                                    <span className="w-40 fw-semibold">Descripción:</span>
                                    <input type="text" className="form-control form-control-sm" value={formData.descripcion} onChange={(e) => handleChange('descripcion', e.target.value)} />
                                </div>
                                <div className="d-flex align-items-center mb-1">
                                    <span className="w-40 fw-semibold">Ingreso por Montos:</span>
                                    <input type="checkbox" className="form-check-input ms-2" checked={formData.ingresoMontos} onChange={(e) => handleChange('ingresoMontos', e.target.checked)} />
                                </div>
                                <div className="d-flex align-items-center">
                                    <span className="w-40 fw-semibold">FUT:</span>
                                    <input type="checkbox" className="form-check-input ms-2" checked={formData.isFut} onChange={(e) => handleChange('isFut', e.target.checked)} />
                                </div>
                            </div>
                        </div>

                        {/* GRILLA DE FACTORES (3 COLUMNAS) */}
                        <div className="row g-2">
                            {/* Columna 1 */}
                            <div className="col-md-4">
                                <div className="mb-1"><label className="form-label mb-0 small">Factor-08 No Constitutiva Renta No Acogido Impto.</label><input type="text" className="form-control form-control-sm" value={formData.f08} onChange={(e) => handleChange('f08', e.target.value)} /></div>
                                <div className="mb-1"><label className="form-label mb-0 small">Factor-11 Incremento Impuesto 1ra Categoría</label><input type="text" className="form-control form-control-sm" value={formData.f11} onChange={(e) => handleChange('f11', e.target.value)} /></div>
                                <div className="mb-1"><label className="form-label mb-0 small">Factor-14 Impto. 1ra Categ. Exento GI. Comp. Sin Devolución</label><input type="text" className="form-control form-control-sm" value={formData.f14} onChange={(e) => handleChange('f14', e.target.value)} /></div>
                                <div className="mb-1"><label className="form-label mb-0 small">Factor-17 No Constitutiva Renta Devolución Capital Art.17</label><input type="text" className="form-control form-control-sm" value={formData.f17} onChange={(e) => handleChange('f17', e.target.value)} /></div>
                                <div className="mb-1"><label className="form-label mb-0 small">Factor-20 Sin Derecho a Devolución</label><input type="text" className="form-control form-control-sm" value={formData.f20} onChange={(e) => handleChange('f20', e.target.value)} /></div>
                                <div className="mb-1"><label className="form-label mb-0 small">Factor-23 Con Derecho a Devolución</label><input type="text" className="form-control form-control-sm" value={formData.f23} onChange={(e) => handleChange('f23', e.target.value)} /></div>
                                <div className="mb-1"><label className="form-label mb-0 small">Factor-26 Sin Derecho a Devolución</label><input type="text" className="form-control form-control-sm" value={formData.f26} onChange={(e) => handleChange('f26', e.target.value)} /></div>
                                <div className="mb-1"><label className="form-label mb-0 small">Factor-29 Sin Derecho a Devolución</label><input type="text" className="form-control form-control-sm" value={formData.f29} onChange={(e) => handleChange('f29', e.target.value)} /></div>
                                <div className="mb-1"><label className="form-label mb-0 small">Factor-32 Con Derecho a Devolución</label><input type="text" className="form-control form-control-sm" value={formData.f32} onChange={(e) => handleChange('f32', e.target.value)} /></div>
                                <div className="mb-1"><label className="form-label mb-0 small">Factor-35 Tasa Efectiva Del Cred. Del FUT (TEF)</label><input type="text" className="form-control form-control-sm" value={formData.f35} onChange={(e) => handleChange('f35', e.target.value)} /></div>                            </div>

                            {/* Columna 2 */}
                            <div className="col-md-4">
                                <div className="mb-1"><label className="form-label mb-0 small">Factor-09 Impto. 1ra Categ. Afecto GI. Comp. Con Devolución</label><input type="text" className="form-control form-control-sm" value={formData.f09} onChange={(e) => handleChange('f09', e.target.value)} /></div>
                                <div className="mb-1"><label className="form-label mb-0 small">Factor-12 Impto. 1ra Categ. Exento GI. Comp. Con Devolución</label><input type="text" className="form-control form-control-sm" value={formData.f12} onChange={(e) => handleChange('f12', e.target.value)} /></div>
                                <div className="mb-1"><label className="form-label mb-0 small">Factor-15 Impto. Créditos pro Impuestos Externos</label><input type="text" className="form-control form-control-sm" value={formData.f15} onChange={(e) => handleChange('f15', e.target.value)} /></div>
                                <div className="mb-1"><label className="form-label mb-0 small">Rentas Exentas de Impto. GC Y/O Impto Adicional</label><input type="text" className="form-control form-control-sm" value={formData.rentasExentas} onChange={(e) => handleChange('rentasExentas', e.target.value)} /></div>
                                <div className="mb-1"><label className="form-label mb-0 small">Factor-21 Con Derecho a Devolución</label><input type="text" className="form-control form-control-sm" value={formData.f21} onChange={(e) => handleChange('f21', e.target.value)} /></div>
                                <div className="mb-1"><label className="form-label mb-0 small">Factor-24 Sin Derecho a Devolución</label><input type="text" className="form-control form-control-sm" value={formData.f24} onChange={(e) => handleChange('f24', e.target.value)} /></div>
                                <div className="mb-1"><label className="form-label mb-0 small">Factor-27 Con Derecho a Devolución</label><input type="text" className="form-control form-control-sm" value={formData.f27} onChange={(e) => handleChange('f27', e.target.value)} /></div>
                                <div className="mb-1"><label className="form-label mb-0 small">Factor-30 Con Derecho a Devolución</label><input type="text" className="form-control form-control-sm" value={formData.f30} onChange={(e) => handleChange('f30', e.target.value)} /></div>
                                <div className="mb-1"><label className="form-label mb-0 small">Factor-33 Crédito por IPE</label><input type="text" className="form-control form-control-sm" value={formData.f33} onChange={(e) => handleChange('f33', e.target.value)} /></div>
                                <div className="mb-1"><label className="form-label mb-0 small">Factor-36 Tasa Efectiva Del Cred. Del FUNT (TEX)</label><input type="text" className="form-control form-control-sm" value={formData.f36} onChange={(e) => handleChange('f36', e.target.value)} /></div>
                            </div>

                            {/* Columna 3 */}
                            <div className="col-md-4">
                                <div className="mb-1"><label className="form-label mb-0 small">Factor-10 Impuesto Tasa Adicional Exento Art. 21</label><input type="text" className="form-control form-control-sm border-primary" value={formData.f10} onChange={(e) => handleChange('f10', e.target.value)} /></div>
                                <div className="mb-1"><label className="form-label mb-0 small">Factor-13 Impto. 1ra Categ. Afecto GI. Comp. Sin Devolución</label><input type="text" className="form-control form-control-sm" value={formData.f13} onChange={(e) => handleChange('f13', e.target.value)} /></div>
                                <div className="mb-1"><label className="form-label mb-0 small">Factor-16 No Constitutiva Renta Acogida Impto.</label><input type="text" className="form-control form-control-sm" value={formData.f16} onChange={(e) => handleChange('f16', e.target.value)} /></div>
                                <div className="mb-1"><label className="form-label mb-0 small">Factor-19A Ingreso no Constitutivos de Renta</label><input type="text" className="form-control form-control-sm" value={formData.f19a} onChange={(e) => handleChange('f19a', e.target.value)} /></div>
                                <div className="mb-1"><label className="form-label mb-0 small">Factor-22 Sin Derecho a Devolución</label><input type="text" className="form-control form-control-sm" value={formData.f22} onChange={(e) => handleChange('f22', e.target.value)} /></div>
                                <div className="mb-1"><label className="form-label mb-0 small">Factor-25 Con Derecho a Devolución</label><input type="text" className="form-control form-control-sm" value={formData.f25} onChange={(e) => handleChange('f25', e.target.value)} /></div>
                                <div className="mb-1"><label className="form-label mb-0 small">Factor-28 Crédito por IPE</label><input type="text" className="form-control form-control-sm" value={formData.f28} onChange={(e) => handleChange('f28', e.target.value)} /></div>
                                <div className="mb-1"><label className="form-label mb-0 small">Factor-31 Sin Derecho a Devolución</label><input type="text" className="form-control form-control-sm" value={formData.f31} onChange={(e) => handleChange('f31', e.target.value)} /></div>
                                <div className="mb-1"><label className="form-label mb-0 small">Factor-34 Cred. Por Impto. Tasa Adicional, Ex Art. 21 LIR</label><input type="text" className="form-control form-control-sm" value={formData.f34} onChange={(e) => handleChange('f34', e.target.value)} /></div>
                                <div className="mb-1"><label className="form-label mb-0 small">Factor-37 Devolución Capital Art. 17 num 7 LIR</label><input type="text" className="form-control form-control-sm" value={formData.f37} onChange={(e) => handleChange('f37', e.target.value)} /></div>
                            </div>
                        </div>

                    </div>

                    {/* PIE DE PÁGINA (BOTONES DE ACCIÓN) */}
                    <div className="modal-footer justify-content-end gap-2 py-2">
                        <button type="button" className="btn btn-sm btn-outline-primary px-4" onClick={handleGrabar} disabled={guardando}>
                            {guardando ? 'GRABANDO…' : 'GRABAR'}
                        </button>
                        <button type="button" className="btn btn-sm btn-outline-secondary px-4" onClick={handleCerrar}>
                            CANCELAR
                        </button>
                    </div>

                </div>
            </div>
        </div>
    );
};

export default FormularioIngresoModal;