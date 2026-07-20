# Release 0.1.0 checklist

Esta lista es el gate de salida para la primera versión local. El coordinador
debe conservar la evidencia de cada comando en `docs/DEVELOPMENT_LOG.md` y no
publicar una versión con tareas sin `committed`.

## Preparación

- [ ] `python3 scripts/harness.py validate` pasa sin tareas activas ni estados inválidos.
- [ ] `python3 scripts/check-skills.sh` confirma skills instaladas y checksums.
- [ ] `git diff --check` y el escaneo de secretos no reportan hallazgos.
- [ ] `.env` no está versionado; copiar `.env.example` y configurar secretos solo localmente.

## Calidad

- [ ] Suite backend, frontend estática y harness pasan; skips opcionales quedan documentados.
- [ ] `python3 -m compileall backend scripts tests` pasa.
- [ ] `npm run build` pasa cuando las dependencias frontend están instaladas; si no,
      registrar el bloqueo de red/dependencias sin ocultarlo.
- [ ] El E2E Playwright se ejecuta con `JOBSCRAPPER_E2E_COMMAND` en un entorno que
      tenga navegador, y conserva logs de navegador/servidor.

## Operación y recuperación

- [ ] `scripts/ops.sh check` pasa con Compose levantado.
- [ ] Se prueba un backup y se valida `tar tzf`; el restore requiere `--yes` y un
      backup previo del estado actual.
- [ ] El cron apunta a `scripts/scheduler.py`, usa el lock compartido y deja logs.
- [ ] Se simulan siete ejecuciones diarias: un fallo transitorio se recupera,
      no hay solapamiento y los límites de CPU, memoria, concurrencia, retries y
      retención de logs quedan registrados.
- [ ] Ollama y Notion pueden estar fuera de servicio sin perder score determinista
      ni resultados ya persistidos; las reparaciones Notion son auditables.

## Publicación

- [ ] SDD y backlog reflejan el comportamiento implementado y sus riesgos.
- [ ] `CHANGELOG.md` contiene `[0.1.0]` y el hash Conventional Commit de release.
- [ ] Crear tag anotado `v0.1.0` únicamente después de registrar el commit final.
- [ ] Guardar el resultado de este checklist junto con el artefacto de release.

Los checks que requieren Docker, npm, Playwright, SQLAlchemy o credenciales reales
son explícitamente dependientes del entorno; nunca se sustituyen por una afirmación
sin evidencia.
