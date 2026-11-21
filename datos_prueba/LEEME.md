# Datos de prueba

Datos ficticios para probar el sistema y grabar la demostración. Ningún RUT ni nombre corresponde a empresas reales.

## 1. Crear la corredora (Administrador de TI, en `/admin/` → Corredoras)

| Código | Nombre |
|---|---|
| CORR01 | Corredora Demo Uno |

## 2. Crear emisores e instrumentos (Administrador de TI, en `/catalogo/` o `/admin/`)

| RUT emisor | Razón social | Mercado |
|---|---|---|
| 96500001-1 | Emisora Demo Acciones S.A. | ACN |
| 76500003-3 | Fondo Demo Inversión | CFI |

| Código nemotécnico | Descripción | Emisor |
|---|---|---|
| DEMOACN1 | Acción demo serie A | 96500001-1 |
| DEMOACN2 | Acción demo serie B | 96500001-1 |
| DEMOCFI1 | Cuota fondo demo | 76500003-3 |

Para mostrar la validación del RUT, intentar crear un emisor con `96500002-1` (dígito incorrecto; el correcto es `96500002-K`).

## 3. Crear usuarios (Administrador de TI, en `/registro/`)

| Usuario | Rol | Corredora |
|---|---|---|
| corredor1 | Corredor de bolsa | CORR01 |
| supervisor1 | Supervisor | — |
| auditor1 | Auditor | — |

Cada integrante define su propia contraseña. No subir contraseñas al repositorio.

## 4. Archivos CSV (botones CARGA X MONTO / CARGA X FACTOR del mantenedor)

| Archivo | Botón | Resultado esperado |
|---|---|---|
| `carga_montos_ejemplo.csv` | CARGA X MONTO | 3 filas válidas; el sistema calcula los factores |
| `carga_factores_ejemplo.csv` | CARGA X FACTOR | 3 filas válidas |
| `carga_con_errores_ejemplo.csv` | CARGA X FACTOR | 5 filas rechazadas, cada una con columna y motivo |

Formato: 38 columnas separadas por `;`, fecha `DD-MM-AAAA`, secuencia mayor a 10.000, decimales con coma, factores entre 0 y 1 y suma de columnas 8 a 19 ≤ 1.
