# Guion de sustentación — RutaSegura (10 minutos)

## 0. Antes de empezar
- Tener `docker compose up --build` ya corriendo y probado.
- Tener abiertas dos pestañas: el mapa (`http://localhost:8000`) y `http://localhost:8000/docs` (OpenAPI).
- Tener dos direcciones de ejemplo en Bogotá ya verificadas con Nominatim/OSRM (probarlas antes del jurado).

## 1. Problema (1.5 min)
"Para muchas mujeres, decidir qué calle tomar de noche no es un detalle menor: es una
decisión de seguridad. Hoy esa decisión se toma con información informal —el consejo de
una amiga, la intuición— sin datos. RutaSegura responde a un reto concreto de los ODS 5
(igualdad de género) y 11 (ciudades y comunidades sostenibles): **convertir el conocimiento
colectivo sobre el espacio público nocturno en una herramienta de decisión, sin pedirle a
nadie que se exponga más de lo necesario para usarla.**"

## 2. Demo en vivo (3.5 min)
Guion paso a paso:
1. Abrir el mapa → señalar los puntos seguros (CAI, farmacias 24h) ya cargados en Bogotá/Soacha/Fusagasugá.
2. Registrarse/iniciar sesión en 10 segundos.
3. Buscar una ruta entre dos direcciones reales → mostrar que aparecen 2-3 alternativas,
   cada una coloreada por su ISN (verde/ámbar/rojo) con el desglose explicado en español.
4. Hacer un reporte (p. ej. "poca luz") cerca de la ruta "más segura" → repetir la búsqueda
   y mostrar **en vivo** cómo baja el ISN de esa ruta y cambia la explicación.
5. Activar el Modo Guardián con 1 minuto para forzar visualmente el estado "alerta" sin
   hacer check-in (opcional si el tiempo apremia).
6. Mostrar el botón SOS (mantener presionado 1 s) y el mensaje simulado a contactos.

## 3. Arquitectura (1.5 min)
"Es una arquitectura MVC clásica: FastAPI como backend (routers → services → models), con
PostgreSQL y SQLAlchemy. El frontend es deliberadamente simple —Jinja2, Tailwind y Leaflet,
sin build de JavaScript— porque con menos de dos horas de implementación, cada pieza de
infraestructura adicional es un riesgo de que la demo no arranque. El núcleo del producto es
el Índice de Seguridad Nocturna: una función pura, auditable, que combina reportes
ciudadanos recientes y puntos seguros conocidos, sin IA en tiempo de ejecución."

## 4. Seguridad y privacidad (1.5 min)
"Autenticación con JWT y contraseñas con Argon2id, que es el algoritmo recomendado por OWASP
hoy. Todo el acceso a la base de datos pasa por el ORM, sin SQL concatenado. Limitamos la
tasa de peticiones en login y en creación de reportes para mitigar abuso. Y en privacidad:
los reportes pueden ser anónimos, las coordenadas se redondean antes de guardarse, y la
ubicación del Modo Guardián solo existe mientras la sesión está activa — alineado con la
Ley 1581."

## 5. Uso de IA (1 min)
"Usamos Claude, a través de Claude Code, para implementar esta especificación técnica que
el equipo diseñó: el stack, el modelo de datos y, sobre todo, la fórmula del ISN, fueron
decisiones humanas. La IA no decide qué es seguro: ejecuta una fórmula transparente que
nosotros definimos y que documentamos junto con sus riesgos de sesgo —por ejemplo, que zonas
con menos usuarias activas van a tener menos reportes, lo que no significa que sean más
seguras—. Esto está documentado en `docs/uso_ia.md`."

## 6. Impacto y cierre (1 min)
"RutaSegura no reemplaza la labor del Estado en seguridad pública, pero le da a cada mujer
una herramienta de decisión basada en datos abiertos y en la memoria colectiva del espacio
público, hoy mismo, con lo que ya existe: calles, farmacias, CAI y la experiencia de quienes
caminan esas calles todas las noches."

---

## Preguntas probables del jurado y respuestas

**1. "¿Qué pasa si no hay reportes en una zona? ¿La marcan como segura por defecto?"**
No. Sin reportes cercanos, el ISN depende solo de la distancia a puntos seguros conocidos
(refugio); si tampoco hay puntos seguros cerca, el modelo aplica la penalización máxima por
falta de refugio (ver `refugio_m` en el desglose). Nunca se asume "segura" por ausencia de
datos: lo dejamos explícito en `docs/uso_ia.md` como un riesgo de sesgo conocido (zonas con
menor cobertura de usuarias pueden parecer más seguras de lo que son).

**2. "¿Cómo evitan que alguien reporte cosas falsas para manipular una ruta?"**
Limitamos la tasa de creación de reportes (10/min por IP) y aplicamos decadencia temporal, así
que un reporte aislado pesa poco frente al promedio. No implementamos moderación humana ni
verificación de reportes en esta versión por el tiempo disponible; es la limitación más
importante que señalamos para una siguiente iteración (p. ej. reputación de usuarias
verificadas o corroboración por múltiples reportes).

**3. "¿Por qué no usaron PostGIS si están trabajando con geolocalización?"**
Con el volumen de datos de un prototipo (decenas de puntos seguros, cientos de reportes),
un prefiltro por *bounding box* más distancia exacta por Haversine en Python da resultados
correctos sin la complejidad operativa de instalar y mantener una extensión geoespacial bajo
presión de tiempo. Si el volumen de datos creciera en producción (miles de reportes por
ciudad), ahí sí migraríamos a PostGIS con índices espaciales.

**4. "¿Qué tan dependientes son de OSRM y Nominatim? ¿Qué pasa si esos servicios caen?"**
Son servidores públicos de uso razonable, sin garantía de disponibilidad (SLA). El backend
hace esas llamadas con timeout de 8 segundos y devuelve un mensaje de error claro en vez de
un 500 sin controlar (`GeocodingError`/`RoutingError` en `app/services/`). Para producción
real, recomendamos una instancia propia de OSRM o un proveedor con SLA.

**5. "El ISN usa reportes de 'acoso'. ¿No es sensible procesar ese tipo de datos?"**
Sí, y por eso el reporte es intencionalmente mínimo: tipo, severidad (1-5) y una descripción
corta opcional, sin exigir identidad (puede ser anónimo) y sin pedir detalles del incidente
ni datos de la persona reportante. El ISN agrega esos reportes a nivel de *lugar*, nunca
construye un perfil de ninguna persona —ni de quien reporta ni de quien es reportada—, y las
coordenadas se redondean antes de guardarse para no exponer ubicaciones exactas como una
vivienda.
