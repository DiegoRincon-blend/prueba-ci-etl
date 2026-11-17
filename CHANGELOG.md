# Changelog

Los cambios relevantes del repositorio se documentan aquí. Los cambios pendientes de publicación se registran en **Sin publicar**; al crear una versión se trasladan a una sección con su versión y fecha.

## Sin publicar

### Agregado

- Estructura inicial del repositorio para pipelines de datos del Portal de Transparencia de Cali.
- Pipeline de MapaInversiones Cali, trasladado desde el proyecto existente junto con sus scripts SQL, documentación y avisos de procedencia y licencia.
- Paquete inicial independiente `agente-cognitivo-ingestion`, con punto de entrada, configuración, Dockerfile y pruebas. La lógica de ingestión está pendiente de definición e implementación.
- Instrucciones compartidas para Codex y Claude Code en `AGENTS.md` y `CLAUDE.md`.
- Pruebas unitarias y flujo de CI para los dos paquetes Python.
- Escaneo de secretos con Gitleaks para archivos e historial Git en GitHub Actions, y guía para gestionar hallazgos.
- Documentación de arquitectura, riesgos y pasos pendientes para migrar a AWS.
- Extractor `xlsx` en MapaInversiones: lee los XLSX de `s3://<bucket>/<prefijo>/<lote>/` con nombres de archivo fijos, una subcarpeta por carga, selección por la variable `PERIODO` y el lote como `periodo` por defecto. Valida todo el lote (archivos y hojas) antes de modificar tablas y falla si falta un archivo o la hoja está vacía. Probado con S3 simulado (moto) y datos sintéticos.

### Cambiado

- `config.yaml` de MapaInversiones usa `source_type: "xlsx"` con los nombres fijos `CUIPO.xlsx`, `CATALOGO_DE_PRODUCTOS.xlsx`, `BASE BID.xlsx` y `REPORTE_RPC.xlsx`; se eliminaron las rutas de Drive y los `periodo` fijos.
- El extractor `xlsx` de MapaInversiones dejó de leer archivos locales: se fusionó con el extractor de S3 (antes `s3_xlsx_extractor.py`, ahora parte de `xlsx_extractor.py`) porque el ETL solo se dispara desde ECS al llegar archivos a S3. Ya no existe un modo de lectura en disco para XLSX; `csv_extractor.py` sigue siendo local.
- Pipeline de MapaInversiones organizado como paquete Python, con configuración en `config/` y dependencias de ejecución bloqueadas para Python 3.12.
- Contenedor y cadena de conexión de MapaInversiones alineados en ODBC Driver 18. La imagen y la conexión a SQL Server siguen pendientes de validación en un entorno real.

### Pendiente

- Implementar escritura de exportaciones en S3, infraestructura y despliegue en AWS, y pruebas de integración con SQL Server y con un bucket real.
- Regenerar `requirements.lock` con pip-compile en Python 3.12: se editó a mano para añadir `boto3` y bajar `python-dateutil` a 2.9.x, requerido por botocore.
- Definir las fuentes, transformaciones y destino del pipeline del agente cognitivo.
- Confirmar los permisos y licencias aplicables al código trasladado y al código nuevo.
