# Mantenedor de Calificaciones Tributarias – nuam

Aplicación web para que las corredoras de bolsa ingresen, modifiquen, eliminen y consulten calificaciones tributarias (DJ 1948), en forma manual o mediante carga masiva de archivos CSV, con control de acceso por roles y bitácora de auditoría.

Proyecto de la asignatura **Ingeniería de Software (TI3043)** – INACAP, Grupo 2.

## Equipo

| Integrante | Rol |
|---|---|
| Sebastián Basoalto | Líder de proyecto / Scrum Master |
| Tomás Troncoso | Analista |
| Pablo Hormázabal | Programador |
| Manuel Toloza | Tester |

## Tecnologías

- **Backend:** Python 3 + Django 5.2, Django REST Framework, JWT (simplejwt)
- **Frontend:** plantillas Django con HTML, CSS, JavaScript y Bootstrap
- **Bases de datos:** MySQL 8 (datos transaccionales) y MongoDB 7 (datos documentales)
- **Servidor de base de datos:** máquina virtual Ubuntu en VirtualBox

## Funcionalidades

- Inicio de sesión con bloqueo tras 5 intentos fallidos (15 minutos) y cierre de sesión por inactividad (30 minutos).
- Mantenedor de calificaciones: ingresar, modificar, eliminar (borrado lógico), copiar y consultar con filtros (mercado, origen, período) y paginación.
- Carga masiva por **monto** (el sistema calcula los factores) y por **factor**, con validación por fila indicando columna y motivo.
- Catálogo de emisores (RUT validado con módulo 11) e instrumentos.
- Solicitudes de rectificación: el corredor solicita y el supervisor aprueba o rechaza.
- Registro de usuarios solo por el Administrador de TI.
- Bitácora de auditoría encadenada con HMAC-SHA256.

## Roles

| Rol | Permisos principales |
|---|---|
| Corredor de bolsa | Gestiona las calificaciones de su corredora y solicita rectificaciones |
| Supervisor | Aprueba o rechaza rectificaciones |
| Auditor | Consulta las calificaciones (solo lectura) |
| Administrador de TI | Registra usuarios y administra el sistema |

## Instalación

Requisitos: Python 3.11+, MySQL 8 y MongoDB 7 en ejecución (en la VM Ubuntu o en el mismo equipo).

1. Clonar el repositorio:
   ```bash
   git clone https://github.com/arcor25/Proyecto-Nuam.git
   cd Proyecto-Nuam/backend
   ```
2. Crear y activar un entorno virtual:
   ```bash
   python -m venv venv
   venv\Scripts\activate        # Windows
   source venv/bin/activate     # Linux
   ```
3. Instalar dependencias:
   ```bash
   pip install -r requirements.txt
   ```
4. Crear la base de datos y el usuario en MySQL:
   ```sql
   CREATE DATABASE nuam CHARACTER SET utf8mb4;
   CREATE USER 'nuam_app'@'%' IDENTIFIED BY 'tu_contraseña';
   GRANT ALL PRIVILEGES ON nuam.* TO 'nuam_app'@'%';
   ```
5. Copiar `.env.example` como `.env` y completar `SECRET_KEY`, `DB_PASSWORD`, `DB_HOST` (IP de la VM), `AUDITORIA_HMAC_KEY` y `MONGO_URI`.
6. Crear las tablas, los índices de MongoDB y el administrador:
   ```bash
   python manage.py migrate
   python manage.py crear_indices_mongo
   python manage.py createsuperuser
   ```
7. Iniciar el servidor:
   ```bash
   python manage.py runserver
   ```
8. Abrir <http://localhost:8000>.

> El archivo `.env` contiene credenciales y **no se sube** al repositorio.

## Rutas principales

| Ruta | Descripción |
|---|---|
| `/` | Página de inicio |
| `/login/` | Inicio de sesión |
| `/calificaciones/` | Mantenedor de calificaciones |
| `/catalogo/` | Emisores e instrumentos |
| `/registro/` | Registro de usuarios (solo Administrador de TI) |
| `/admin/` | Panel de administración de Django |
| `/api/` | API REST (requiere autenticación) |

## Datos de prueba

La carpeta [`datos_prueba`](datos_prueba/LEEME.md) contiene los emisores, instrumentos y usuarios a crear, y archivos CSV de ejemplo para la carga por monto, por factor y con errores.

## Formato del archivo CSV

- 38 columnas separadas por `;` o `,`, con fila de encabezado.
- Columnas: Ejercicio, Mercado (ACN, CFI o FM), Instrumento, Fecha (DD-MM-AAAA), Secuencia (> 10.000), N.º dividendo, Tipo sociedad (A, C o vacío), Valor histórico y columnas 8 a 37.
- Codificación UTF-8 o Latin-1, máximo 10 MB.
- Factores entre 0 y 1, hasta 8 decimales; la suma de las columnas 8 a 19 no puede superar 1.

## Seguridad (Ley 21.459 de delitos informáticos)

- Acceso solo con usuario y contraseña; contraseñas almacenadas con hash.
- Bloqueo por intentos fallidos y límite de peticiones al login.
- Control de acceso por rol: cada corredor solo ve los datos de la Bolsa y los de su propia corredora.
- Protección CSRF en formularios y sesiones con expiración.
- Bitácora que registra quién hizo cada acción, cuándo y desde qué IP, incluidos los accesos denegados.
- Credenciales fuera del código (archivo `.env`).
