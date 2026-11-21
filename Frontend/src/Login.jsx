import { useState } from 'react';
import { login } from './api';

const Login = ({ onIngreso }) => {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [cargando, setCargando] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setCargando(true);
        try {
            const usuario = await login(email.trim(), password);
            onIngreso(usuario);
        } catch (err) {
            setError(err.status === 429 ? 'Demasiados intentos. Espere un minuto.' : err.message);
        } finally {
            setCargando(false);
        }
    };

    return (
        <div className="d-flex justify-content-center align-items-center min-vh-100">
            <form className="bg-white p-4 border rounded shadow-sm" style={{ width: '100%', maxWidth: 380 }} onSubmit={handleSubmit}>
                <h5 className="fw-bold mb-3" style={{ color: '#1B4965' }}>NUAM · Iniciar sesión</h5>

                {error && <div className="alert alert-danger py-2 small">{error}</div>}

                <div className="mb-2">
                    <label className="form-label small mb-0" htmlFor="email">Correo</label>
                    <input id="email" type="email" className="form-control form-control-sm" autoComplete="username"
                        value={email} onChange={(e) => setEmail(e.target.value)} required autoFocus />
                </div>
                <div className="mb-3">
                    <label className="form-label small mb-0" htmlFor="password">Contraseña</label>
                    <input id="password" type="password" className="form-control form-control-sm" autoComplete="current-password"
                        value={password} onChange={(e) => setPassword(e.target.value)} required />
                </div>
                <button type="submit" className="btn btn-sm w-100 text-white fw-bold" style={{ backgroundColor: '#1C4E80' }} disabled={cargando}>
                    {cargando ? 'Ingresando…' : 'INGRESAR'}
                </button>
            </form>
        </div>
    );
};

export default Login;
