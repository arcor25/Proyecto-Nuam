import { useEffect, useState } from 'react'
import CalificacionesTributarias from './CalificacionesTributarias'
import Login from './Login'
import { alCerrarSesion, logout, obtenerUsuario } from './api'

function App() {
  const [usuario, setUsuario] = useState(obtenerUsuario())

  // Si el token expira y no se puede renovar, vuelve al login
  useEffect(() => alCerrarSesion(() => setUsuario(null)), [])

  const handleSalir = async () => {
    try {
      await logout()
    } finally {
      setUsuario(null)
    }
  }

  return (
    <div className="container-fluid p-4 bg-secondary-subtle min-vh-100">
      {usuario ? (
        <>
          <div className="d-flex justify-content-end align-items-center gap-3 mb-2 small">
            <span className="text-muted">
              {usuario.nombre_completo} · <strong>{usuario.rol_nombre}</strong>
              {usuario.corredora_nombre ? ` · ${usuario.corredora_nombre}` : ''}
            </span>
            <button className="btn btn-sm btn-outline-secondary" onClick={handleSalir}>Cerrar sesión</button>
          </div>
          <CalificacionesTributarias usuario={usuario} />
        </>
      ) : (
        <Login onIngreso={setUsuario} />
      )}
    </div>
  )
}

export default App
