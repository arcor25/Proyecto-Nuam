import { useState } from 'react';
import { COLUMNAS, clave, factoresParaApi, fechaParaApi, numeroParaApi } from './calificacion';

// Formulario a partir de la fila seleccionada; guarda los 30 factores aunque la pantalla muestre solo algunos
function formularioDesdeFila(fila) {
    const form = {
        mercado: fila?.mercado || '',
        instrumento: fila?.instrumento || '',
        valorHistorico: fila?.valorHistorico ?? '0',
        fechaPago: fila?.fechaPago || '',
        descripcion: fila?.descripcion || '',
        secuencia: fila?.secuencia ?? '',
        anio: fila?.ejercicio ?? '',
        factorActualizacion: fila?.factorAct ?? '0',
    };
    COLUMNAS.forEach((col) => {
        form[clave(col)] = fila?.[clave(col)] ?? '0';
    });
    return form;
}

// El padre lo monta con key = id de la fila, así cada apertura parte de los datos de esa fila
const FormularioModificarModal = ({ show, datosFila, onCerrar, onGuardar }) => {
    const [formData, setFormData] = useState(() => formularioDesdeFila(datosFila));
    const [error, setError] = useState('');
    const [guardando, setGuardando] = useState(false);

    if (!show || !datosFila) return null;

    const handleChange = (campo, valor) => setFormData({ ...formData, [campo]: valor });

    const handleGuardar = async (e) => {
        e.preventDefault();
        setError('');
        setGuardando(true);
        try {
            // Mercado, instrumento, año y secuencia forman la llave: el backend no permite cambiarlos
            await onGuardar({
                fecha_pago: fechaParaApi(formData.fechaPago),
                valor_historico: numeroParaApi(formData.valorHistorico),
                factor_actualizacion: numeroParaApi(formData.factorActualizacion),
                descripcion: formData.descripcion.trim(),
                ...factoresParaApi(formData),
            });
            onCerrar();
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
                    <div className="modal-header py-2 bg-light">
                        <h6 className="modal-title text-primary fw-bold mb-0">Modificar Calificación Tributaria</h6>
                        <button type="button" className="btn-close" onClick={onCerrar}></button>
                    </div>
                    <div className="modal-body p-3" style={{ fontSize: '0.78rem' }}>
                        {error && <div className="alert alert-danger py-2 small">{error}</div>}
                        <div className="row g-2 mb-3 bg-light p-2 border rounded">
                            <div className="col-md-4">
                                <div className="d-flex align-items-center mb-1"><span className="w-40 fw-semibold">Mercado:</span><input type="text" className="form-control form-control-sm" value={formData.mercado} disabled /></div>
                                <div className="d-flex align-items-center mb-1"><span className="w-40 fw-semibold">Fecha Pago:</span><input type="text" className="form-control form-control-sm" placeholder="DD-MM-AAAA" value={formData.fechaPago} onChange={(e) => handleChange('fechaPago', e.target.value)} /></div>
                                <div className="d-flex align-items-center"><span className="w-40 fw-semibold">Secuencia Evento:</span><input type="text" className="form-control form-control-sm" value={formData.secuencia} disabled /></div>
                            </div>
                            <div className="col-md-4">
                                <div className="d-flex align-items-center mb-1"><span className="w-40 fw-semibold">Instrumento:</span><input type="text" className="form-control form-control-sm" value={formData.instrumento} disabled /></div>
                                <div className="d-flex align-items-center mb-1"><span className="w-40 fw-semibold">Factor Actualización:</span><input type="text" className="form-control form-control-sm" value={formData.factorActualizacion} onChange={(e) => handleChange('factorActualizacion', e.target.value)} /></div>
                                <div className="d-flex align-items-center"><span className="w-40 fw-semibold">Año:</span><input type="text" className="form-control form-control-sm" value={formData.anio} disabled /></div>
                            </div>
                            <div className="col-md-4">
                                <div className="d-flex align-items-center mb-1"><span className="w-40 fw-semibold">Valor Histórico:</span><input type="text" className="form-control form-control-sm" value={formData.valorHistorico} onChange={(e) => handleChange('valorHistorico', e.target.value)} /></div>
                                <div className="d-flex align-items-center"><span className="w-40 fw-semibold">Descripción:</span><input type="text" className="form-control form-control-sm" value={formData.descripcion} onChange={(e) => handleChange('descripcion', e.target.value)} /></div>
                            </div>
                        </div>

                        <div className="row g-2">
                            <div className="col-md-4">
                                <div className="mb-1"><label className="form-label mb-0 small">Factor-08: Con crédito IDPC post 01.01.2017</label><input type="text" className="form-control form-control-sm" value={formData.f08} onChange={(e) => handleChange('f08', e.target.value)} /></div>
                                <div className="mb-1"><label className="form-label mb-0 small">Factor-11: Sin derecho a crédito</label><input type="text" className="form-control form-control-sm" value={formData.f11} onChange={(e) => handleChange('f11', e.target.value)} /></div>
                                <div className="mb-1"><label className="form-label mb-0 small">Factor-14 Impto 1ra Categ. Exento GI Comp. Sin Devolución</label><input type="text" className="form-control form-control-sm" value={formData.f14} onChange={(e) => handleChange('f14', e.target.value)} /></div>
                                <div className="mb-1"><label className="form-label mb-0 small">Factor-17 No Constitutiva de Renta Devolución Capital</label><input type="text" className="form-control form-control-sm" value={formData.f17} onChange={(e) => handleChange('f17', e.target.value)} /></div>
                                <div className="mb-1"><label className="form-label mb-0 small">Factor-20: Sin Derecho a Devolucion</label><input type="text" className="form-control form-control-sm" value={formData.f20} onChange={(e) => handleChange('f20', e.target.value)} /></div>
                            </div>
                            <div className="col-md-4">
                                <div className="mb-1"><label className="form-label mb-0 small">Factor-09: Con crédito IDPC acum. al 31.12.2016</label><input type="text" className="form-control form-control-sm" value={formData.f09} onChange={(e) => handleChange('f09', e.target.value)} /></div>
                                <div className="mb-1"><label className="form-label mb-0 small">Factor-12 Impto 1ra Categ. Exento GI Comp. Con Devolución</label><input type="text" className="form-control form-control-sm" value={formData.f12} onChange={(e) => handleChange('f12', e.target.value)} /></div>
                                <div className="mb-1"><label className="form-label mb-0 small">Factor-15 Impto. Créditos pro Impuestos Externos</label><input type="text" className="form-control form-control-sm" value={formData.f15} onChange={(e) => handleChange('f15', e.target.value)} /></div>
                                <div className="mb-1"><label className="form-label mb-0 small">Factor-18: Rentas Exentas Impto. GC / Adicional</label><input type="text" className="form-control form-control-sm" value={formData.f18} onChange={(e) => handleChange('f18', e.target.value)} /></div>
                                <div className="mb-1"><label className="form-label mb-0 small">Factor-21: Con Derecho a Devolucion</label><input type="text" className="form-control form-control-sm" value={formData.f21} onChange={(e) => handleChange('f21', e.target.value)} /></div>
                            </div>
                            <div className="col-md-4">
                                <div className="mb-1"><label className="form-label mb-0 small">Factor-10: Con crédito IDPC Voluntario</label><input type="text" className="form-control form-control-sm" value={formData.f10} onChange={(e) => handleChange('f10', e.target.value)} /></div>
                                <div className="mb-1"><label className="form-label mb-0 small">Factor-13 Impto 1ra Categ. Afecto GI Comp. Sin Devolución</label><input type="text" className="form-control form-control-sm" value={formData.f13} onChange={(e) => handleChange('f13', e.target.value)} /></div>
                                <div className="mb-1"><label className="form-label mb-0 small">Factor-16 No Constitutiva Renta Acogida a Impto.</label><input type="text" className="form-control form-control-sm" value={formData.f16} onChange={(e) => handleChange('f16', e.target.value)} /></div>
                                <div className="mb-1"><label className="form-label mb-0 small">Factor-19: Ingreso no Constitutivos de Renta</label><input type="text" className="form-control form-control-sm" value={formData.f19} onChange={(e) => handleChange('f19', e.target.value)} /></div>
                                <div className="mb-1"><label className="form-label mb-0 small">Factor-22: Sin Derecho a Devolucion</label><input type="text" className="form-control form-control-sm" value={formData.f22} onChange={(e) => handleChange('f22', e.target.value)} /></div>
                            </div>
                        </div>
                    </div>
                    <div className="modal-footer justify-content-end py-2">
                        <button type="button" className="btn btn-sm btn-outline-primary px-4" onClick={handleGuardar} disabled={guardando}>{guardando ? 'GUARDANDO…' : 'GUARDAR'}</button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default FormularioModificarModal;