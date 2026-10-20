# Preparación del repositorio

La publicación incluye código, interfaz, contratos normativos y escenarios. `.gitignore` permite explícitamente esos directorios y excluye datos de ejecución, entornos instalados, credenciales y respaldos.

En la instalación original, los scripts, instaladores y reportes sueltos de la raíz sin referencias en las fuentes mantenidas se retiraron a `.evalia-private/cleanup_20261019/archive/`. También se apartaron directorios de respaldos antiguos sin referencias. El movimiento conserva los archivos y dispone de un inventario local en `plan.json` y un registro en `completed.json`, dentro de `.evalia-private/cleanup_20261019/`.

No se eliminaron las bases ni las calificaciones y no se cambiaron los algoritmos, las rúbricas ni las decisiones de evaluación. Los evaluadores versionados y los recursos con referencias activas se conservaron.

Para recuperar un archivo apartado, consulta su `source` y `target` en el registro local y cópialo desde el archivo a su ubicación original, comprobando antes que no exista ya un archivo en el destino. No es necesario restaurarlos para el arranque normal.

Los archivos privados y el inventario de limpieza no se publican. El historial local de investigación se mantiene separado del código que se incorpora a GitHub.
