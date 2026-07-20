# Operación, mantenimiento y recuperación

Estas instrucciones son para la instalación Docker Compose de JobScrapper. Los
comandos son deliberadamente explícitos: nunca se eliminan volúmenes ni se
restaura una copia sin `--yes`. Antes de cualquier cambio, conserva el archivo
`.env` fuera de Git y valida el estado del repositorio.

## Reinicio tras reboot

Desde el checkout, ejecuta:

```sh
scripts/ops.sh restart
```

El comando recrea los servicios en segundo plano y comprueba `/health`. Para
arranque automático en Linux, habilita un servicio systemd que ejecute
`docker compose up -d` después de `docker.service`; en macOS/Windows, inicia
Docker Desktop y usa el mismo comando. El scheduler diario se instala aparte
con `scripts/jobscrapper.cron.example` y no debe lanzarse hasta que `check` pase.

## Backup y restore

`scripts/ops.sh backup [directorio]` crea una copia con timestamp del árbol
`/app/data` (SQLite, WAL, logs y CVs) y, si existe, un segundo archivo para el
volumen persistente de Ollama. Copia los artefactos a almacenamiento externo y
prueba periódicamente que puedan listarse con `tar tzf`.

Para restaurar, detén servicios y exige confirmación explícita:

```sh
scripts/ops.sh restore backups/jobscrapper-data-YYYYMMDDTHHMMSSZ.tar.gz --yes
scripts/ops.sh check
```

La restauración reemplaza únicamente el contenido del volumen de datos. Haz un
backup del estado actual antes de restaurar y conserva la copia original; nunca
uses `docker compose down --volumes` como paso de recuperación.

Si también necesitas recuperar modelos locales, detén Compose y restaura el
archivo de Ollama en su volumen (después de inspeccionar su contenido):

```sh
docker run --rm -i -v "${OLLAMA_DATA_VOLUME:-jobscrapper_ollama}:/target" \
  alpine:3.20 sh -c 'tar xzf - -C /target' < backups/jobscrapper-ollama-YYYYMMDDTHHMMSSZ.tar.gz
```

La copia de Ollama es opcional; si no existe, el backend continúa funcionando
sin el modelo y deja el análisis narrativo en estado pendiente.

## Actualización y rollback

Con un working tree limpio:

```sh
scripts/ops.sh update
scripts/ops.sh rollback <known-good-tag-or-commit> --yes
```

`update` usa `git pull --ff-only`, reconstruye imágenes y verifica salud. El
rollback cambia el checkout a un commit conocido, reconstruye y vuelve a
verificar. Registra el ref usado, el hash resultante y el resultado de `check`
en el registro operativo antes de reactivar el cron.

## Fallos y diagnóstico

Ante un contenedor no saludable:

```sh
scripts/ops.sh recover
docker compose logs --since=30m --tail=200
docker compose ps
```

`recover` intenta recrear servicios sin borrar datos y falla si `/health` sigue
sin responder. Si hay errores de esquema, restaura una copia y revisa la última
migración; si Ollama falla, deja el perfil `local-ollama` desactivado: el scoring
determinista y la cola `narrative_pending` siguen siendo utilizables.

## Checks reproducibles

Ejecuta `scripts/ops.sh check` después de reboot, restore, update y rollback.
El check valida el archivo Compose y consulta el endpoint local con timeout de
cinco segundos. Guarda la salida junto al backup para auditoría. No contiene
tokens ni imprime valores de secretos.
