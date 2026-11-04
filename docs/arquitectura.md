# Arquitectura — RutaSegura

## 1. Resumen

RutaSegura es una PWA web, móvil-first, que ayuda a mujeres a planear desplazamientos a pie
más seguros en horario nocturno. Combina datos abiertos de rutas (OSRM) y geocodificación
(Nominatim) con reportes ciudadanos y una base de puntos seguros (CAI, farmacias 24h, tiendas,
gasolineras) para calcular un **Índice de Seguridad Nocturna (ISN)** por ruta, con
desglose explicado en lenguaje natural.

## 2. Diagrama de arquitectura

```
┌──────────────────────────────────────────────────────────┐
│  Navegador (móvil)                                        │
│  Jinja2 (HTML) + Tailwind (CDN) + Leaflet + JS vanilla     │
│  localStorage: JWT                                         │
└───────────────────────────┬────────────────────────────────┘
                            │ fetch() JSON / HTML
                            ▼
┌──────────────────────────────────────────────────────────┐
│  FastAPI (Uvicorn, Python 3.12)                            │
│  ┌────────────┐   ┌────────────┐   ┌───────────────────┐  │
│  │ routers/   │──▶│ services/  │──▶│ models/ (SQLAlchemy)│ │
│  │ (Controller)│   │ (lógica)   │   └─────────┬──────────┘ │
│  └─────┬──────┘   └─────┬──────┘             │             │
│        │  schemas/      │ httpx               │             │
│        │  (Pydantic)    ▼                     ▼             │
│        │           OSRM / Nominatim      PostgreSQL 16      │
│        ▼           (APIs externas)                          │
│  templates/ (Jinja2 - View)                                 │
└──────────────────────────────────────────────────────────┘
```

Es una arquitectura **MVC por capas**: `routers` actúan como *Controller* (reciben la
petición HTTP, validan con `schemas` y delegan), `services` contiene la lógica de negocio
pura (ISN, geocodificación, ruteo), `models` es la capa de persistencia (SQLAlchemy ORM) y
`templates` es la *View* renderizada en el servidor.

## 3. Decisiones técnicas y por qué

| Decisión | Alternativa descartada | Justificación |
|---|---|---|
| **FastAPI + Jinja2**, sin SPA (React/Vue) | React/Vue + build con Node | El reto tiene <2 h de implementación. Un solo servicio, sin paso de build, reduce puntos de fallo y tiempo de arranque. Jinja2 + `fetch()` es suficiente para la interactividad requerida (mapa, modales, formularios). |
| **PostgreSQL sin PostGIS** | PostGIS | No hay tiempo para instalar/depurar extensiones geoespaciales. Con <20 puntos seguros y reportes recientes, un prefiltro por *bounding box* (`lat`/`lng` como `DOUBLE PRECISION` con índice compuesto) + distancia exacta por **Haversine** en Python es suficientemente preciso y rápido para esta escala. |
| **SQLAlchemy 2.x síncrono** | SQLAlchemy async | El modo síncrono es más simple de depurar bajo presión de tiempo; con `psycopg[binary]` (v3) el rendimiento es adecuado para el volumen esperado en una demo. |
| **`Base.metadata.create_all()`**, sin Alembic | Alembic | No se requieren migraciones versionadas para un prototipo de una sola sesión; `create_all()` es idempotente y evita configurar un sistema de migraciones completo en minutos. |
| **`pwdlib[argon2]`** para contraseñas | `passlib` + bcrypt | `passlib` está sin mantenimiento activo y tiene incompatibilidades conocidas con versiones recientes de `bcrypt`. `pwdlib` es lo que recomienda hoy la documentación oficial de FastAPI, y Argon2id es el algoritmo de hash de contraseñas recomendado por OWASP (resistente a ataques por GPU/ASIC). |
| **PyJWT** para JWT | `python-jose` | `python-jose` está abandonado (sin commits recientes, con CVEs reportados). PyJWT es mantenido activamente y es la recomendación actual de FastAPI para emitir/verificar JWT. |
| **Reportes NO georreferenciados en vivo para "puntos seguros"**; se cargan con `seed.py` | Un directorio en vivo / API externa de POIs | Evita depender de una API externa adicional y frágil (cuotas, disponibilidad) para un dato que cambia poco. Los puntos de ejemplo cubren Bogotá, Soacha y Fusagasugá. |
| **`slowapi`** para *rate limiting* | Nginx / middleware propio | Mitigación directa de fuerza bruta en login/registro y espamming de reportes (OWASP A04/A07) con una librería ligera, sin infraestructura adicional. |

## 4. Modelo de datos

```
users(id, email UNIQUE, name, password_hash, created_at)
trusted_contacts(id, user_id FK→users, name, phone)
reports(id, user_id FK→users NULL, type, severity 1-5, description ≤280,
        lat, lng, created_at)              -- índice compuesto (lat, lng)
safe_points(id, name, kind, lat, lng, open_24h)
guardian_sessions(id, user_id FK→users, started_at, eta_at, status,
                   last_lat, last_lng)
```

- `reports.user_id` es nulo para reportes anónimos (requisito de privacidad, Ley 1581).
- `reports.type ∈ {poca_luz, acoso, calle_sola, zona_segura}`.
- `safe_points.kind ∈ {cai, farmacia, tienda, gasolinera}`.
- `guardian_sessions.status ∈ {active, arrived, alert}`; la transición a `alert` se evalúa
  de forma **perezosa** (al leer la sesión, no con un *worker* en segundo plano), lo que evita
  introducir colas o tareas programadas para una demo de corta duración.

## 5. Índice de Seguridad Nocturna (ISN)

Implementado como función pura en `app/services/safety_score.py` (sin efectos secundarios,
100% testeable). Para cada ruta devuelta por OSRM:

1. Se muestrea la polilínea cada ~50 m (`services/geo.py::sample_polyline`).
2. Se buscan reportes cercanos (≤50 m de algún punto muestreado) de tipo `acoso`,
   `calle_sola`, `poca_luz` o `zona_segura`.
3. Se calcula:
   - `riesgo_reportes` = suma de `(severidad/5) · decadencia(edad_horas)` para reportes de
     `acoso`/`calle_sola`, con `decadencia(h) = max(0.2, 1 − h/168)` (un reporte pierde peso
     con el tiempo, pero nunca cae a cero del todo).
   - `penal_luz` = número de reportes de `poca_luz` cercanos.
   - `refugio` = distancia promedio (m) desde los puntos muestreados al `safe_point` más
     cercano.
   - `ISN = clamp(100 − 4·riesgo_reportes − 3·penal_luz − min(25, refugio/40) + 5·n_zona_segura, 0, 100)`.
4. Se devuelve el desglose (`breakdown`) y una explicación en español generada a partir de
   los mismos conteos (sin modelo de lenguaje: es una plantilla determinista, 100%
   explicable y auditable).

Esto resuelve el requisito de **transparencia/explicabilidad**: cualquier valor de ISN puede
rastrearse hasta reportes y puntos seguros concretos. Se documenta explícitamente que el ISN
**no perfila personas**, solo condiciones de *lugares* (ver `docs/uso_ia.md`).

## 6. Seguridad (OWASP Top 10) — qué se implementó y dónde

- **A02 Fallas criptográficas**: contraseñas con Argon2id (`pwdlib`), JWT firmado con
  `SECRET_KEY` desde variable de entorno (`app/core/security.py`). La clave es obligatoria y
  debe tener al menos 32 caracteres (RFC 7518 §3.2); la app no arranca con una más corta
  (`app/core/config.py`).
- **A01 Control de acceso roto**: `get_current_user` (`app/core/deps.py`) exige JWT válido;
  los endpoints de guardián/SOS/contactos comprueban que el recurso pertenezca al
  `user_id` autenticado (`app/routers/guardian.py::_get_session_or_404`).
- **A03 Inyección**: todo acceso a datos vía ORM (SQLAlchemy, sin SQL concatenado); validación
  estricta de entrada con Pydantic (rangos de lat/lng, longitud máxima de descripción, etc.).
- **A04 Diseño inseguro / abuso**: `slowapi` limita `/api/auth/register` y `/api/auth/login`
  a 5/min, y `POST /api/reports` a 10/min por IP.
- **A05 Configuración de seguridad incorrecta**: cabeceras `X-Content-Type-Options`,
  `X-Frame-Options: DENY`, `Referrer-Policy`, y una CSP que solo permite los orígenes
  necesarios (Tailwind CDN, unpkg para Leaflet, tiles de OSM, OSRM y Nominatim); sin CORS
  abierto (mismo origen).
- **A07 Identificación y autenticación**: JWT con expiración (`exp`, 60 min).
- **XSS**: el frontend construye el DOM con `textContent`/`createElement`, nunca `innerHTML`
  con datos provenientes de usuarios o del backend.

## 7. Privacidad (Ley 1581 de 2012)

- Los reportes anónimos no exponen `user_id`; la ubicación enviada se redondea a 4 decimales
  (~11 m) antes de guardarse, suficiente para el análisis agregado sin precisión de vivienda.
- La ubicación del Modo Guardián (`last_lat`/`last_lng`) solo se almacena mientras la sesión
  está `active`; no se registra en logs del servidor.
- No se guardan contraseñas ni coordenadas en texto plano en ningún log de la aplicación.

## 8. Por qué no se usó un SPA ni PostGIS (resumen)

Ambas decisiones comparten la misma motivación: el tiempo de implementación disponible
(<2 h) hace que cualquier pieza adicional de infraestructura (bundler de JS, extensión de
BD) sea un riesgo de que "no arranque a la primera". Se prefirió maximizar la probabilidad
de un `docker compose up --build` exitoso sobre la sofisticación técnica.
