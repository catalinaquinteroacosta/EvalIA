# EvalIA

Aplicación local para registrar conversaciones y evaluar respuestas de IA en escenarios de ansiedad, depresión y crisis. Incluye rúbricas, banco de 38 escenarios, interfaz web, exportación de resultados y herramientas de revisión manual.

## Instalación

Requiere Python 3.11 o 3.12 y Git. Desde la carpeta del proyecto:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\python run_evalia.py
```

En Windows también puedes abrir `ABRIR_EVALIA_VALIDACION.cmd` después de instalar las dependencias. En macOS o Linux, utiliza `.venv/bin/python` en los comandos anteriores.

La dirección predeterminada es `http://127.0.0.1:8879`. Para elegir otro puerto o evitar abrir el navegador:

```powershell
.venv\Scripts\python run_evalia.py --port 8880 --no-browser
```

En una instalación nueva se crea una base separada en `.evalia-private/local/application.db`, con modelos, rúbricas y los 38 escenarios; las conversaciones comienzan vacías. Si ya existe la configuración local de investigación, el lanzador la utiliza y conserva sus bases y calificaciones. `--fresh` permite abrir la instalación base separada incluso cuando hay una configuración de investigación.

## Datos y evaluaciones

Las bases SQLite, conversaciones, calificaciones, exportaciones, credenciales, certificados de ejecución y resultados históricos son archivos locales excluidos de Git. Un clon nuevo no contiene los experimentos de la instalación original.

La interfaz base permite organizar y registrar conversaciones. Los flujos de evaluación semántica calificados necesitan la configuración y los certificados de investigación correspondientes. Si no existen esos certificados, la aplicación impide preparar una evaluación en lugar de tratar el clon como una instalación calificada. Abrir la aplicación no autoriza llamadas pagadas.

Las credenciales se configuran localmente mediante `CONFIGURAR_CREDENCIAL_LUNA.cmd` en Windows o las variables de entorno que utiliza el proveedor. No añadas archivos privados al repositorio con `git add -f`.

## Estructura

| Carpeta | Contenido |
|---|---|
| `backend/` | Aplicación, almacenamiento, exportaciones y evaluadores |
| `frontend/` | Interfaz HTML, CSS y JavaScript |
| `governed/` | Coordinación, límites, recuperación y revisión manual |
| `database/` | Rúbricas y bancos de escenarios versionados |
| `docs/` | Contratos normativos necesarios para el código |
| `tests/`, `fixtures/` | Pruebas y casos de validación |
| `scripts/` | Comprobaciones del repositorio |

Se conservan los evaluadores y contratos versionados: sus nombres o antigüedad no indican que puedan borrarse. Algunos se importan indirectamente o se verifican mediante huellas criptográficas.

## Verificación

La página principal permite elegir resultados por escenario o abrir `/resultados-globales`.
Las siete vistas globales comparan las cinco IA por escenario, familia y turno para ansiedad,
depresión, trastornos combinados, cada tipo de crisis y crisis combinadas. Incluyen
evolución longitudinal, seguridad consolidada y síntesis de las cinco categorías. Usan las notas consolidadas del lote local;
una instalación nueva sin ese lote muestra el estado sin datos.

El porcentaje se calcula primero por familia, después por respuesta y finalmente
por escenario, con pesos iguales en cada nivel. N/A no se transforma en cero y
una comparación con respuestas pendientes no publica un promedio incompleto.
El Excel incluye método, denominadores, escenarios excluidos y datos de auditoría.
Estos resúmenes son descriptivos; no realizan pruebas de significación estadística.

```powershell
.venv\Scripts\python scripts/check_repository.py
.venv\Scripts\python -m pytest tests/test_public_install.py tests/test_luna_budget.py tests/test_luna_application.py governed/test_direct_recovery.py governed/test_monetary_policy.py tests/test_json_export.py tests/test_export_audit.py -q
```

Las pruebas históricas que requieren recibos, documentos fuente o bases de campañas anteriores necesitan esos archivos locales. Dentro de la selección anterior, dos casos históricos se omiten explícitamente cuando falta su evidencia original; los demás son portables. No se necesitan credenciales ni llamadas a servicios externos.

Consulta [la organización del repositorio](docs/REPOSITORIO.md) para conocer la función de los archivos y los límites entre código y datos locales.
