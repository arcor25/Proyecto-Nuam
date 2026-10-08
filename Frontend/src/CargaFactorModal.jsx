import { useState } from 'react';
import * as XLSX from 'xlsx';

const CargaFactorModal = ({ show, onCerrar, onGuardar }) => {
    const [registrosCargados, setRegistrosCargados] = useState([]);

    if (!show) return null;

    const handleFileChange = (e) => {
        const file = e.target.files[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = (evt) => {
            const bstr = evt.target.result;
            const workbook = XLSX.read(bstr, { type: 'binary' });
            const ws = workbook.Sheets[workbook.SheetNames[0]];
            const data = XLSX.utils.sheet_to_json(ws);

            const mapeados = data.map((row) => ({
                ejercicio: row.EJERCICIO || row.ejercicio || '',
                mercado: row.MERCADO || row.mercado || 'AC',
                nemotecnico: row.NEMOTECNICO || row.NE || row.instrumento || '',
                fechaPago: row.FEC_PAGO || row.fechaPago || '',
                secuencia: row.SEC_EVE || row.secuencia || '',
                descripcion: row.DESCRIPCION || row.descripcion || '',
                f08: row.F8 || row.f08 || '0,00000000',
                f09: row.F9 || row.f09 || '0,00000000',
                f10: row.F10 || row.f10 || '0,00000000',
                f11: row.F11 || row.f11 || '0,00000000',
                f12: row.F12 || row.f12 || '0,00000000',
                f13: row.F13 || row.f13 || '0,00000000',
                instrumento: row.NEMOTECNICO || row.instrumento || ''
            }));

            setRegistrosCargados(mapeados);
        };
        reader.readAsBinaryString(file);
    };

    const handleGrabar = () => {
        if (registrosCargados.length === 0) return alert("No hay registros.");
        onGuardar(registrosCargados);
        onCerrar();
    };

    return (
        <div className="modal show d-block bg-dark bg-opacity-50" tabIndex="-1">
            <div className="modal-dialog modal-xl">
                <div className="modal-content border-secondary shadow-lg">
                    <div className="modal-header py-2 bg-light border-top border-4 border-warning">
                        <h6 className="modal-title text-primary fw-bold mb-0">Cargar Archivo Carga X Factor</h6>
                        <button type="button" className="btn-close" onClick={onCerrar}></button>
                    </div>
                    <div className="modal-body p-3" style={{ fontSize: '0.8rem' }}>
                        <ul className="nav nav-tabs mb-2">
                            <li className="nav-item">
                                <span className="nav-link active bg-primary text-white py-1 px-3 fw-bold" style={{ backgroundColor: '#1C4E80' }}>Archivo</span>
                            </li>
                        </ul>
                        <div className="table-responsive border rounded" style={{ minHeight: '200px', maxHeight: '300px' }}>
                            <table className="table table-sm table-bordered table-striped mb-0 text-nowrap" style={{ fontSize: '0.75rem' }}>
                                <thead className="table-light sticky-top">
                                    <tr>
                                        <th>EJERCICIO</th><th>MERCADO</th><th>NEMO...</th><th>FEC_PAGO</th><th>SEC_EVE</th><th>DESCRIPCION</th>
                                        <th>F8-Monto Impt...</th><th>F9-Monto Impt...</th><th>F10-Monto Im...</th><th>F11-Monto Im...</th><th>F12- REX con ...</th><th>F13- REX cc</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {registrosCargados.length > 0 ? (
                                        registrosCargados.map((item, idx) => (
                                            <tr key={idx}>
                                                <td>{item.ejercicio}</td><td>{item.mercado}</td><td>{item.nemotecnico}</td><td>{item.fechaPago}</td><td>{item.secuencia}</td><td>{item.descripcion}</td>
                                                <td>{item.f08}</td><td>{item.f09}</td><td>{item.f10}</td><td>{item.f11}</td><td>{item.f12}</td><td>{item.f13}</td>
                                            </tr>
                                        ))
                                    ) : (
                                        <tr><td colSpan="12" className="text-center text-muted py-5">No hay registros.</td></tr>
                                    )}
                                </tbody>
                            </table>
                        </div>
                        <div className="d-flex justify-content-between align-items-center bg-light border border-top-0 p-1 px-2 text-muted" style={{ fontSize: '0.75rem' }}>
                            <span className="badge bg-secondary">{registrosCargados.length}</span>
                            <span>{registrosCargados.length > 0 ? `${registrosCargados.length} registros listos` : 'No hay registros.'}</span>
                        </div>
                    </div>
                    <div className="modal-footer justify-content-between py-2 bg-light">
                        <label className="btn btn-sm btn-outline-primary fw-bold">
                            Seleccionar Archivo
                            <input type="file" accept=".csv, .xlsx, .xls" onChange={handleFileChange} hidden />
                        </label>
                        <div className="d-flex gap-2">
                            <button className="btn btn-sm text-white px-4 fw-bold" style={{ backgroundColor: '#1C4E80' }} onClick={handleGrabar}>GRABAR</button>
                            <button className="btn btn-sm btn-outline-secondary px-3" onClick={onCerrar}>CANCELAR</button>
                            <button className="btn btn-sm btn-outline-primary px-3">VER FORMATO</button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default CargaFactorModal;