# Organización del repositorio

El repositorio contiene la aplicación, sus instrumentos, los controles de evaluación y las pruebas. Las bases con conversaciones y calificaciones, las credenciales, los entornos instalados y los informes generados permanecen en la instalación local y están excluidos de Git.

## Archivos de la raíz

| Archivo | Función |
| --- | --- |
| `.gitignore` | Evita publicar datos locales, credenciales, dependencias instaladas y respaldos. |
| `.gitattributes` | Mantiene el formato de los archivos y los bytes de contratos y evaluadores con verificaciones de integridad. |
| `README.md` | Explica la instalación, el inicio y la estructura de la aplicación. |
| `requirements.txt` | Declara las dependencias de Python del proyecto. |
| `requirements-dev.txt` | Añade las dependencias utilizadas para las comprobaciones del repositorio. |
| `run_evalia.py` | Inicia la instalación existente o prepara una instalación base separada. |
| `ABRIR_EVALIA_VALIDACION.cmd` | Facilita iniciar la aplicación en Windows. |
| `CONFIGURAR_CREDENCIAL_LUNA.cmd` | Abre la configuración local de la credencial del lector semántico. |
| `PUNTAJES EVALUADORES ANSIEDAD(20261008-000023).docx` | Fuente normativa de los 81 indicadores de ansiedad y depresión. Su contenido y su huella son comprobados por evaluadores y pruebas. |
| `casos_adversariales_ce2_ce10.json` | Casos de comprobación de los evaluadores CE2 a CE10. |
| `ce_adversarial_preflight.py` | Comprueba esos casos y sus interfaces sin realizar llamadas a servicios externos. |
| `export_anxiety_conversations.py` | Genera el PDF local de conversaciones de ansiedad sin calificaciones. Requiere la base de la instalación de investigación. |

## Carpetas

`backend/` contiene el servidor, la persistencia, los evaluadores y las exportaciones; `frontend/`, las páginas y gráficos. `database/` aporta las rúbricas y los bancos de escenarios versionados. `governed/` contiene la coordinación de evaluaciones, la recuperación de pendientes y la revisión manual. `tests/` y `fixtures/` permiten comprobar su comportamiento; `scripts/` reúne comprobaciones y utilidades. `.github/` ejecuta las comprobaciones portables del repositorio.

Los contratos conservados en `docs/` son recursos de evaluación, además de documentación. Los nombres `candidate`, `isolated` o las versiones históricas no prueban que un archivo sea prescindible: algunos se importan activamente o forman parte de verificaciones con huellas digitales. Retirarlos requiere comprobar sus referencias y las pruebas correspondientes.

## Datos de una instalación existente

Las carpetas `.evalia-private/`, `exports/`, los registros históricos y los entornos locales no forman parte del código publicado. Pueden contener las conversaciones, las calificaciones, evidencia de evaluación o herramientas necesarias en esa instalación. No deben borrarse como si fueran archivos sobrantes del repositorio.

Una copia nueva del código crea escenarios vacíos y no incorpora las notas de la instalación original. Las credenciales y las autorizaciones de ejecución tampoco se transfieren por Git.
