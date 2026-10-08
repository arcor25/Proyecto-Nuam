import { useState, useEffect } from 'react';

const FormularioModificarModal = ({ show, datosFila, onCerrar, onGuardar }) => {
    const [formData, setFormData] = useState({
        mercado: '', instrumento: '', valorHistorico: '0,00000000', fechaPago: '', eventoCapital: '0',
        descripcion: '', secuencia: '', anio: '', f08: '0,00000000', f09: '0,00000000', f10: '0,00000000',
        f11: '0,00000000', f12: '0,00000000', f13: '0,00000000', f14: '0,00000000', f15: '0,00000000',
        f16: '0,00000000', f17: '0,00000000', f18: '0,00000000', f19: '0,00000000', f19b: '0,00000000',
        f20: '0,00000000', f21: '0,00000000', f22: '0,00000000', f23: '0,00000000', f24: '0,00000000',
        f25: '0,00000000', f26: '0,00000000', f27: '0,00000000', f28: '0,00000000', f29: '0,00000000',
        f30: '0,00000000', f31: '0,00000000', f32: '0,00000000', f33: '0,00000000', f34: '0,00000000',
        f35: '0,00000000', f36: '0,00000000', f37: '0,00000000'
    });

    useEffect(() => {
        if (datosFila) {
            setFormData({
                mercado: datosFila.mercado || 'AC',
                instrumento: datosFila.instrumento || datosFila.nemotecnico || '',
                valorHistorico: datosFila.valorHistorico || '0,00000000',
                fechaPago: datosFila.fechaPago || '',
                eventoCapital: datosFila.eventoCapital || '0',
                descripcion: datosFila.descripcion || '',
                secuencia: datosFila.secuencia || '',
                anio: datosFila.ejercicio || '',
                f08: datosFila.f08 || '0,00000000', f09: datosFila.f09 || '0,00000000', f10: datosFila.f10 || '0,00000000',
                f11: datosFila.f11 || '0,00000000', f12: datosFila.f12 || '0,00000000', f13: datosFila.f13 || '0,00000000',
                f14: datosFila.f14 || '0,00000000', f15: datosFila.f15 || '0,00000000', f16: datosFila.f16 || '0,00000000',
                f17: datosFila.f17 || '0,00000000', f18: datosFila.f18 || '0,00000000', f19: datosFila.f19 || '0,00000000',
                f19b: datosFila.f19b || '0,00000000', f20: datosFila.f20 || '0,00000000', f21: datosFila.f21 || '0,00000000',
                f22: datosFila.f22 || '0,00000000', f23: datosFila.f23 || '0,00000000', f24: datosFila.f24 || '0,00000000',
                f25: datosFila.f25 || '0,00000000', f26: datosFila.f26 || '0,00000000', f27: datosFila.f27 || '0,00000000',
                f28: datosFila.f28 || '0,00000000', f29: datosFila.f29 || '0,00000000', f30: datosFila.f30 || '0,00000000',
                f31: datosFila.f31 || '0,00000000', f32: datosFila.f32 || '0,00000000', f33: datosFila.f33 || '0,00000000',
                f34: datosFila.f34 || '0,00000000', f35: datosFila.f35 || '0,00000000', f36: datosFila.f36 || '0,00000000',
                f37: datosFila.f37 || '0,00000000'
            });
        }
    }, [datosFila]);

    if (!show) return null;

    const handleChange = (campo, valor) => setFormData({ ...formData, [campo]: valor });

    const handleGuardar = (e) => {
        e.preventDefault();
        onGuardar({
            ...datosFila,
            ejercicio: formData.anio,
            instrumento: formData.instrumento,
            fechaPago: formData.fechaPago,
            descripcion: formData.descripcion,
            secuencia: formData.secuencia,
            mercado: formData.mercado,
            valorHistorico: formData.valorHistorico,
            eventoCapital: formData.eventoCapital,
            f08: formData.f08, f09: formData.f09, f10: formData.f10, f11: formData.f11, f12: formData.f12,
            f13: formData.f13, f14: formData.f14, f15: formData.f15, f16: formData.f16, f17: formData.f17,
            f18: formData.f18, f19: formData.f19, f19b: formData.f19b, f20: formData.f20, f21: formData.f21,
            f22: formData.f22, f23: formData.f23, f24: formData.f24, f25: formData.f25, f26: formData.f26,
            f27: formData.f27, f28: formData.f28, f29: formData.f29, f30: formData.f30, f31: formData.f31,
            f32: formData.f32, f33: formData.f33, f34: formData.f34, f35: formData.f35, f36: formData.f36, f37: formData.f37
        });
        onCerrar();
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
                        <div className="row g-2 mb-3 bg-light p-2 border rounded">
                            <div className="col-md-4">
                                <div className="d-flex align-items-center mb-1"><span className="w-40 fw-semibold">Mercado:</span><input type="text" className="form-control form-control-sm" value={formData.mercado} onChange={(e) => handleChange('mercado', e.target.value)} /></div>
                                <div className="d-flex align-items-center mb-1"><span className="w-40 fw-semibold">Fecha Pago:</span><input type="text" className="form-control form-control-sm" value={formData.fechaPago} onChange={(e) => handleChange('fechaPago', e.target.value)} /></div>
                                <div className="d-flex align-items-center"><span className="w-40 fw-semibold">Secuencia Evento:</span><input type="text" className="form-control form-control-sm" value={formData.secuencia} onChange={(e) => handleChange('secuencia', e.target.value)} /></div>
                            </div>
                            <div className="col-md-4">
                                <div className="d-flex align-items-center mb-1"><span className="w-40 fw-semibold">Instrumento:</span><input type="text" className="form-control form-control-sm" value={formData.instrumento} onChange={(e) => handleChange('instrumento', e.target.value)} /></div>
                                <div className="d-flex align-items-center mb-1"><span className="w-40 fw-semibold">Evento Capital:</span><input type="text" className="form-control form-control-sm" value={formData.eventoCapital} onChange={(e) => handleChange('eventoCapital', e.target.value)} /></div>
                                <div className="d-flex align-items-center"><span className="w-40 fw-semibold">Año:</span><input type="text" className="form-control form-control-sm" value={formData.anio} onChange={(e) => handleChange('anio', e.target.value)} /></div>
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
                        <button type="button" className="btn btn-sm btn-outline-primary px-4" onClick={handleGuardar}>GUARDAR</button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default FormularioModificarModal;