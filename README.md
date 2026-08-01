# JobScrapper

JobScrapper es una aplicación local para descubrir ofertas de trabajo en México,
Estados Unidos y otras regiones, compararlas con un perfil profesional y
priorizarlas mediante un porcentaje de compatibilidad explicable.

Cada oferta puede conservar título, empresa, región, modalidad (remota,
híbrida u on-site), descripción, enlace de descripción, enlace de aplicación,
salario, coincidencias, brechas y recomendaciones. Los resultados se guardan
localmente en SQLite y pueden sincronizarse con Notion.

> **Desarrollo asistido por IA**
>
> Este proyecto fue creado y documentado con asistencia de IA (Codex) dentro de
> un arnés multiagente. La IA ayudó a implementar, probar y revisar cambios; las
> decisiones de producto, aceptación de términos de fuentes, configuración de
> secretos y aprobación de commits siguen siendo responsabilidad humana.

## Características

- Ingesta desde APIs y feeds JSON públicos, Greenhouse, Lever y Ashby.
- Fuentes con aceptación explícita de términos, validación de URLs, `robots.txt`,
  límites de velocidad, reintentos y aislamiento de errores por fuente.
- Clasificación regional: CDMX, Guadalajara, resto de México, USA y otras
  regiones.
- Deduplicación por URL canónica y huella de contenido.
- Compatibilidad determinista de 0 a 100 con desglose por skills, experiencia,
  idioma, ubicación, modalidad, salario y autorización laboral.
- Análisis narrativo opcional con Ollama; el scoring no depende del modelo local.
- Perfil editable y carga de CV PDF/DOCX con extracción local.
- Dashboard React para ofertas, perfil, preferencias, fuentes y operaciones.
- Sincronización opcional con Notion y vistas regionales.
- Cron diario, bloqueo contra ejecuciones concurrentes, logs JSON y backup/restore.
- Arnés de entrega `coder → tester → reviewer → coordinator → commit` con
  Conventional Commits.

## Arquitectura

```text
React + TypeScript + Vite
            │ HTTP /api/v1
            ▼
FastAPI ── servicios de dominio ── MatchingService
   │              │                         │
   │              ├── conectores de fuentes  └── Ollama opcional
   │              ├── SQLite + SQLAlchemy
   │              └── sincronización Notion opcional
   ▼
Docker Compose: backend · frontend · Ollama opcional
```

### Componentes técnicos

| Capa | Tecnología | Responsabilidad |
| --- | --- | --- |
| Frontend | React 19, TypeScript, Vite 7 | Dashboard y formularios accesibles |
| API | Python 3.11+, FastAPI, Uvicorn | Contratos HTTP versionados y OpenAPI |
| Dominio | Python, SQLAlchemy 2, Alembic | Perfil, fuentes, normalización, scoring y ejecuciones |
| Persistencia | SQLite | Fuente de verdad local, evaluaciones, snapshots y logs de ejecución |
| IA local | Ollama | Explicaciones narrativas opcionales; nunca es requisito para puntuar |
| Integración | Notion REST API | Sincronización opcional de ofertas y vistas regionales |
| Operación | Docker Compose, cron, scripts Bash/Python | Arranque, refresh, backup, restore y recuperación |
| Calidad | `unittest`, Playwright, harness multiagente | Pruebas unitarias, integración, E2E y gates de entrega |

## Requisitos

- Docker Desktop con Compose v2 (recomendado para el entorno completo).
- Python 3.11 o superior para desarrollo local.
- Node.js 20+ y [pnpm](https://pnpm.io/) para el frontend.
- Ollama instalado en el host o el perfil Compose `local-ollama` (opcional).
- Una integración de Notion y un database ID (opcional).

## Puesta en marcha con Docker

```sh
git clone <URL-DE-TU-REPOSITORIO>
cd JobScrapper
cp .env.example .env
```

Edita `.env` antes de arrancar. Para Ollama instalado en el host, Docker
Desktop usa `http://host.docker.internal:11434`:

```dotenv
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=gemma3:1b
DATABASE_URL=sqlite:///./data/jobscrapper.db
```

Arranca API y dashboard:

```sh
docker compose up --build -d
```

URLs principales:

- Dashboard: <http://127.0.0.1:5173>
- Health: <http://127.0.0.1:8000/health>
- Operaciones: <http://127.0.0.1:8000/api/v1/operations/health>
- OpenAPI: <http://127.0.0.1:8000/api/v1/docs>

Para ejecutar Ollama dentro de Compose:

```sh
docker compose --profile local-ollama up --build -d
set -a
. ./.env
set +a
docker compose exec ollama ollama pull "$OLLAMA_MODEL"
```

En ese caso usa `OLLAMA_BASE_URL=http://ollama:11434` en `.env`. El volumen
`jobscrapper_ollama` conserva los modelos; `jobscrapper_data` conserva SQLite,
CVs y logs.

## Desarrollo local sin Docker

### Backend

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e backend
cd backend
python -m app
```

### Frontend

En otra terminal:

```sh
cd frontend
pnpm install
pnpm dev
```

El frontend espera la API en `http://127.0.0.1:8000`. Para una compilación de
producción:

```sh
pnpm build
pnpm preview --host 127.0.0.1 --port 4173
```

## Configuración de Notion y Ollama

### Notion

1. Crea una integración en Notion.
2. Crea una base de datos de ofertas y comparte esa base con la integración.
3. Copia el ID de la base de datos a `.env`.
4. Configura `NOTION_API_TOKEN` y `NOTION_DATABASE_ID`.

La configuración y el mapeo de propiedades están documentados en
[`docs/NOTION.md`](docs/NOTION.md). Los secretos se leen en tiempo de ejecución
y no se persisten en fuentes, ofertas ni logs.

### Ollama

Comprueba el modelo local:

```sh
ollama list
ollama pull gemma3:1b
curl http://127.0.0.1:11434/api/tags
```

El endpoint de health reporta el modelo configurado. Si Ollama no está
disponible, JobScrapper conserva el porcentaje determinista y marca el análisis
narrativo como pendiente o fallback.

## Fuentes y refresh

Las fuentes se crean desde el dashboard o mediante `POST /api/v1/sources`. Cada
fuente debe tener un adaptador y términos revisados; la URL base es obligatoria
en modo red y `allow_network=true` habilita la consulta remota. En modo fixture
puede omitirse la URL base. El repositorio no preconfigura fuentes remotas:
agrega tus endpoints permitidos y acepta sus términos antes de activarlos.

Después de activar una fuente:

```sh
curl -X POST http://127.0.0.1:8000/api/v1/operations/refresh
```

El resultado incluye ofertas encontradas, fuentes con error, evaluaciones
creadas y errores de scoring. Un fallo de una fuente no descarta las demás.

## Cron y operaciones

Instala el cron después de adaptar la ruta absoluta del checkout:

```sh
crontab scripts/jobscrapper.cron.example
```

El scheduler usa el mismo pipeline y bloqueo que el refresh manual. Para
operación diaria, backup y recuperación:

```sh
scripts/ops.sh check
scripts/ops.sh restart
scripts/ops.sh backup backups
scripts/ops.sh restore backups/jobscrapper-data-YYYYMMDDTHHMMSSZ.tar.gz --yes
```

Consulta [`docs/OPERATIONS.md`](docs/OPERATIONS.md) antes de restaurar o
actualizar un entorno con datos.

## Pruebas y calidad

```sh
# Arnés y validación de tareas
python3 scripts/harness.py validate

# Backend (con el entorno virtual activado)
python -m unittest discover -s tests/backend -p 'test_*.py' -v

# Frontend (tests Python + build TypeScript/Vite)
python3 -m unittest discover -s tests/frontend -p 'test_*.py' -v
(cd frontend && pnpm build)

# E2E opcional con Playwright
JOBSCRAPPER_E2E_COMMAND="pnpm preview --host 127.0.0.1 --port 4173" \
JOBSCRAPPER_E2E_URL="http://127.0.0.1:4173" \
python3 -m unittest tests.e2e.test_ingestion_dashboard -v
```

Los fallos dependientes del entorno (Chromium, Docker, credenciales Notion o
Ollama) deben registrarse como evidencia, no ocultarse.

## Seguridad y cumplimiento

- No se evaden CAPTCHA, autenticación, controles de acceso ni `robots.txt`.
- Las fuentes requieren revisión de términos y límites configurables.
- Las URLs se validan como HTTP(S); no se usan fallbacks `example.com`.
- Los tokens se mantienen en variables de entorno y se redactan de los logs.
- No subas `.env`, bases SQLite, backups, CVs ni volúmenes al repositorio.

## Estructura del repositorio

```text
backend/       FastAPI, dominio, conectores y persistencia
frontend/      React, TypeScript, Vite y dashboard
tests/         pruebas backend, frontend, harness y E2E
scripts/       scheduler, operaciones, instalación y harness
docs/          SDD, Notion, operaciones, skills y log incremental
.agents/       contratos de coder, tester y reviewer
.harness/      backlog, estados, configuración y skills allowlisted
```

## Flujo de contribución

1. Revisa `AGENTS.md` y `.harness/backlog.json`.
2. Trabaja una sola tarea activa.
3. Completa el flujo `coder → tester → reviewer → coordinator → commit`.
4. Usa Conventional Commits (`feat`, `fix`, `test`, `docs`, `chore`, etc.).
5. Actualiza `docs/DEVELOPMENT_LOG.md` y `CHANGELOG.md`.
6. Nunca incluyas secretos ni artefactos temporales en un commit.

## Publicar en GitHub

Antes de publicar, confirma que `.env`, bases SQLite, backups, CVs, logs y
volúmenes no estén en el índice:

```sh
git status --short
git diff --check
python3 scripts/harness.py validate
```

Crea un repositorio vacío en GitHub y publica la rama `main`:

```sh
git remote add origin https://github.com/<USUARIO>/<REPOSITORIO>.git
git push -u origin main
```

No subas tokens de Notion, cookies, CVs ni archivos `.env`. Configúralos como
secretos o variables del entorno de ejecución del despliegue.

## Documentación adicional

- [SDD y requisitos](docs/SDD.md)
- [Operaciones, backup y restore](docs/OPERATIONS.md)
- [Fuentes y cumplimiento](docs/SOURCES.md)
- [Integración con Notion](docs/NOTION.md)
- [Política de skills](docs/SKILLS.md)
- [Log de desarrollo](docs/DEVELOPMENT_LOG.md)
- [Backend](backend/README.md)

## Licencia

Este repositorio no declara todavía una licencia pública. Añade un archivo
`LICENSE` antes de distribuirlo públicamente en GitHub.
