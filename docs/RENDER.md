# Publicación gratuita en Render

La instalación web separa el archivo de resultados de investigación, de solo lectura, de una base temporal donde se crean experimentos nuevos. No utiliza las bases SQLite originales. Los nuevos experimentos y sus planes de ejecución pueden perderse al reiniciar el servicio gratuito, incluso si una evaluación está en curso. Descarga los resultados nuevos que necesites conservar. Las notas originales vuelven a cargarse desde el archivo verificado.

## Preparar los resultados

En la instalación de investigación se ejecuta:

```powershell
python scripts/prepare_render_results.py --config .evalia-private/governed_joint_install_20261017/config.json
```

Se genera `exports/render/EvalIA_resultados.zip` y un manifiesto con su SHA-256. El ZIP incluye los 38 experimentos oficiales con conversaciones simuladas, calificaciones y justificaciones; las comparaciones globales; y los certificados y archivos históricos que el servidor necesita para comprobar la integridad de sus dependencias. Estos últimos no se exponen en la interfaz pública. No incluye claves, bases originales, registros de facturación ni recibos API. Se excluyen los datos de identidad de quienes registraron las revisiones. No se publica automáticamente y está excluido del repositorio de código.

## Alojar el archivo en GitHub de forma privada

1. Usa un repositorio **privado** de tu cuenta. Puede ser el mismo repositorio de código si sigue privado; si es público, crea otro privado para los datos.
2. En **Releases**, crea una publicación con etiqueta `resultados-v1` y adjunta `EvalIA_resultados.zip`. No añadas el ZIP al árbol del código.
3. Crea un token de acceso de GitHub con permiso **Contents Read only**, limitado exclusivamente a ese repositorio privado. El token se configura en Render; nunca se escribe en el código ni en mensajes públicos.
4. La URL de Render será `https://api.github.com/repos/USUARIO/REPOSITORIO/releases/tags/resultados-v1`. El servidor busca el archivo por su nombre y comprueba su SHA-256 antes de cargarlo. Si el token caduca, hay que renovarlo para que los siguientes reinicios puedan descargar los resultados.

## Configurar el servicio

En **New Web Service**, conecta el repositorio de código y utiliza:

| Campo | Valor |
| --- | --- |
| Language | Python 3 |
| Branch | main |
| Root Directory | Vacío |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn backend.render_app:create_app --factory --host 0.0.0.0 --port $PORT --workers 1` |
| Instance Type | Free |
| Health Check Path | `/healthz` |

Variables de entorno:

- `PYTHON_VERSION`: `3.11.11`.
- `EVALIA_RESULTS_URL`: la URL de la publicación privada indicada arriba.
- `EVALIA_RESULTS_SHA256`: el valor exacto del manifiesto generado.
- `EVALIA_RESULTS_TOKEN`: el token de lectura de GitHub.
- `OPENAI_API_KEY`: solo si se quieren ejecutar evaluaciones nuevas con gasto API. No es necesaria para consultar los resultados originales. La clave cifrada localmente en Windows no se puede trasladar a Render.

Render proporciona `RENDER_EXTERNAL_URL`. Las confirmaciones desde navegador se admiten únicamente desde esa dirección o la interfaz local; se conserva la confirmación de costo por experimento. El servicio no realiza llamadas pagadas al arrancar, descargar resultados, consultar notas o preparar un presupuesto. Sin credencial y saldo API no se pueden completar evaluaciones nuevas.

Se conserva el lector y sus comprobaciones de calificación; no se fabrican certificados ni se convierten desacuerdos o comprobaciones no calificadas en notas definitivas. La portabilidad de evidencia de calificación enlazada a rutas locales puede dejar indicadores en revisión. Las nuevas ejecuciones deben revisarse por su estado y cobertura; la preparación sin gasto no certifica una ejecución API completa en Render.

## Verificar la publicación

Tras desplegar, `/healthz` debe informar 38 experimentos originales. Comprueba las notas y justificaciones de un escenario, las siete vistas globales y la protección contra cambios. Un experimento nuevo debe recibir un identificador separado y mostrar el aviso de datos temporales. Reiniciar no debe alterar los resultados originales. Las ejecuciones API reales no forman parte de las comprobaciones sin gasto y necesitan la confirmación explícita del costo en la interfaz.
