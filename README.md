# RutaSegura

PWA web móvil-first para planear desplazamientos a pie más seguros en horario nocturno.
Proyecto de maratón de programación — reto "Ruta segura para mujeres en el espacio público
nocturno" (ODS 5 y 11).

## Instalación (3 comandos)

```bash
cp .env.example .env
docker compose up --build
# abrir http://localhost:8000
```

La base de datos se crea e inicializa automáticamente (esquema + ~15 puntos seguros de
ejemplo en Bogotá, Soacha y Fusagasugá) la primera vez que arranca el contenedor `api`.

`.env.example` trae una `SECRET_KEY` de ejemplo para que la demo arranque. Para cualquier uso
real, reemplázala por una aleatoria de al menos 32 caracteres
(`python -c "import secrets; print(secrets.token_urlsafe(32))"`); la app no arranca con una
clave más corta.

## Funcionalidades

- Registro/login con JWT y contraseñas con Argon2id.
- Mapa con puntos seguros (CAI, farmacias 24h, tiendas, gasolineras) y reportes ciudadanos
  recientes (poca luz, acoso, calle sola, zona segura).
- Búsqueda de rutas a pie (OSRM) entre dos direcciones (geocodificadas con Nominatim),
  coloreadas y ordenadas por **Índice de Seguridad Nocturna (ISN)**, con desglose explicado.
- Modo Guardián: temporizador de llegada con check-in; pasa a alerta si no confirmas a
  tiempo.
- Botón SOS (mantener presionado) con contactos de confianza.

## Pruebas

```bash
docker compose exec api pytest
```

## Estructura

Ver [docs/arquitectura.md](docs/arquitectura.md) para el detalle de arquitectura, modelo de
datos y decisiones técnicas. Ver [docs/uso_ia.md](docs/uso_ia.md) para el uso ético de IA en
este proyecto y [docs/guion_sustentacion.md](docs/guion_sustentacion.md) para el guion de
sustentación.

## Variables de entorno

Ver `.env.example`. **Nunca** commitear `.env` (ya está en `.gitignore`).

## Flujo de trabajo (git)

Desarrollo *trunk-based*: `main` siempre funcional. Cada rebanada de `ARCHITECTURE.md` se
implementó en una rama corta `feat/<NN>-<tema>` (o `docs/<NN>-<tema>`), creada desde `main`,
con 2-5 commits en formato [Conventional Commits](https://www.conventionalcommits.org/) en
español (`feat`, `fix`, `test`, `docs`, `chore`) y verificación (`docker compose up --build`,
`curl` o `pytest`) antes de fusionar. Cada rama se integró a `main` con
`git merge --no-ff` (para que cada rebanada quede como una unidad revertible en el
historial) y se eliminó tras el merge. El hito `v0.1-demo` marca el punto de rescate tras la
rebanada 5 (ruta segura); `v1.0-entrega` marca la entrega final.
