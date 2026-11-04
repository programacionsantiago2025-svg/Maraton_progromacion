# Uso ético de IA — RutaSegura

## 1. Herramientas usadas

- **Claude (Anthropic), a través de Claude Code (CLI)**: generación asistida de la base de
  código completa (backend FastAPI, frontend Jinja2/Leaflet/JS, Docker, pruebas y esta
  documentación) a partir de una especificación técnica detallada escrita por el equipo
  (stack, modelo de datos, endpoints, fórmula del ISN, requisitos de seguridad y
  accesibilidad). La IA no definió el alcance del producto ni los criterios de seguridad:
  ejecutó una especificación ya decidida por personas.
- No se usó ningún modelo de IA en tiempo de ejecución de la aplicación (RutaSegura no hace
  llamadas a un LLM cuando una usuaria la utiliza). El ISN es una función determinista
  (`app/services/safety_score.py`), no un modelo entrenado ni una IA generativa.

## 2. Prompt relevante (resumen)

El prompt de implementación (ver `ARCHITECTURE.md` del repositorio) especificó de forma
exhaustiva y no negociable: stack tecnológico exacto, estructura de carpetas, modelo de
datos, lista de endpoints, la fórmula completa del ISN (incluida la función de decadencia
temporal), requisitos de seguridad (OWASP), de privacidad (Ley 1581) y de accesibilidad
(WCAG 2.1 AA). Se le pidió a la IA **decidir y avanzar** sin pedir confirmaciones, dado el
límite de tiempo de la maratón, trabajando por rebanadas verticales verificables.

## 3. Evaluación crítica de lo generado

- **Lo que la IA aporta bien**: boilerplate correcto y consistente (modelos, esquemas,
  routers), aplicación literal de las fórmulas especificadas, cobertura razonable de
  cabeceras de seguridad y validación de entrada, y documentación consistente con el código.
- **Lo que requiere revisión humana antes de usar en producción real** (no solo en la
  maratón):
  1. El código no fue sometido a una auditoría de seguridad externa ni a pruebas de carga.
  2. Los puntos seguros (`scripts/seed.py`) son datos de ejemplo con coordenadas
     aproximadas, no verificadas sobre el terreno; no deben presentarse como un directorio
     oficial sin validación posterior.
  3. El límite de la API pública de OSRM/Nominatim (uso razonable, sin SLA) hace que
     RutaSegura dependa de la disponibilidad de terceros; para un despliegue real se
     recomienda una instancia propia o un proveedor con SLA.
  4. Cualquier cambio a la fórmula del ISN (pesos, radio de 50 m, umbral de 7 días) debe ser
     decidido y validado por personas con criterio de dominio (seguridad pública, género),
     no delegado a la IA.

## 4. Riesgos de sesgo del ISN

El ISN depende de **reportes ciudadanos**, lo que introduce riesgos conocidos de sesgo:

- **Sesgo de cobertura**: zonas con más usuarias activas en la app generarán más reportes
  (positivos o negativos) que zonas igualmente inseguras pero con menor adopción de la app
  (p. ej. barrios periféricos con menor acceso a smartphones/datos). Esto puede hacer que una
  ruta aparezca como "segura" simplemente por falta de reportes, no por serlo.
- **Sesgo de denuncia**: el acoso y el miedo a no ser creída desincentivan el reporte en
  algunos contextos; la ausencia de reportes de acoso no implica ausencia de acoso.
- **Retroalimentación positiva**: si una ruta se muestra como insegura, menos personas la
  usan, lo que reduce aún más los reportes (positivos o de corrección) sobre esa ruta.
- **Desactualización**: zonas que mejoraron (p. ej. nueva iluminación) pueden seguir
  penalizadas por reportes antiguos hasta que la decadencia temporal los atenúe.

## 5. Mitigaciones aplicadas o recomendadas

- La función de decadencia `decay(h) = max(0.2, 1 − h/168)` evita que reportes antiguos
  dominen el cálculo indefinidamente, pero **nunca los anula por completo** (mínimo 0.2), para
  no borrar de golpe el historial de una zona.
- El desglose (`breakdown`) y la explicación en español se muestran siempre junto al ISN:
  ninguna ruta se oculta ni se bloquea automáticamente; la decisión final de qué ruta tomar
  queda en manos de la usuaria (**responsabilidad humana**, no automatización total).
- Los puntos seguros (CAI, farmacias 24h) actúan como una señal **independiente** de los
  reportes ciudadanos, reduciendo la dependencia exclusiva de datos con sesgo de
  participación.
- Recomendación para una versión futura: ponderar o normalizar reportes por densidad de uso
  de la zona, y habilitar un canal de verificación comunitaria/institucional de puntos
  seguros.

## 6. Alineación con el Marco Ético de IA de Colombia (2021) y la Ley 1581 de 2012

| Principio | Cómo se aplica en RutaSegura |
|---|---|
| **Transparencia y explicabilidad** | El ISN siempre se devuelve con su desglose por factor y una explicación en texto plano (español) de por qué una ruta tiene ese puntaje (`app/services/safety_score.py`). No es una "caja negra". |
| **Privacidad y protección de datos (Ley 1581)** | Reportes anónimos no asocian `user_id`; las coordenadas se redondean a 4 decimales antes de guardarse; la ubicación del Modo Guardián solo persiste mientras la sesión está activa; no se registran contraseñas ni coordenadas en logs. |
| **No discriminación** | El ISN evalúa **lugares**, no personas: no se construye ningún perfil de usuarias ni se usan atributos personales (género, edad, etc.) como variable de riesgo. Se documenta explícitamente el riesgo de sesgo de cobertura (sección 4) en lugar de ocultarlo. |
| **Responsabilidad humana** | La IA no toma decisiones autónomas sobre la seguridad de una persona: solo informa. El Modo Guardián y el botón SOS dependen de acciones explícitas de la usuaria; el paso a estado `alert` es una notificación, no una llamada automática a autoridades. |
| **Uso ético y proporcionado de IA generativa** | La IA se usó para *implementar* una especificación humana, no para generar las reglas de seguridad pública ni para automatizar decisiones sensibles; este documento declara explícitamente su uso y limitaciones. |
