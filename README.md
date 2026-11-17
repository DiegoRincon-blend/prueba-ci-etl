# Portal de Transparencia: pipelines de datos

Repositorio de pipelines de datos desarrollados para iniciativas de la Alcaldía de Cali, incluyendo MapaInversiones y futuras fuentes para agentes cognitivos. Cada pipeline debe poder probarse, configurarse y desplegarse de forma independiente.

## Estado actual

`pipelines/mapainversiones-cali/` contiene una copia del pipeline existente. **La migración a AWS aún no está implementada:** la configuración en `config/config.yaml` todavía referencia archivos de Windows, los resultados se escriben localmente y no hay infraestructura ni despliegue automatizado. No ejecutar contra producción sin revisar los riesgos documentados.

- [Pipeline MapaInversiones Cali](pipelines/mapainversiones-cali/README.md)
- [Ingestión del agente cognitivo](pipelines/agente-cognitivo-ingestion/README.md): paquete inicial sin lógica de ingestión.
- [Plan de migración y riesgos](docs/architecture/migracion-aws.md)
- [Procedencia y licencia del código existente](provenance/README.md)
- [Instrucciones para agentes](AGENTS.md)

Los archivos de datos y las credenciales no pertenecen al repositorio. La ubicación de los datos y los permisos para cada entorno se definirán al implementar AWS. No se ha seleccionado una licencia general para código nuevo.
