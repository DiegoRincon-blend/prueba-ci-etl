# Ingestión para el agente cognitivo

Paquete inicial independiente para el futuro pipeline de ingestión. Sus fuentes, transformaciones, destino, frecuencia y arquitectura aún no están definidos. No hay integración con S3, base de datos, motor vectorial ni despliegue AWS en esta carpeta.

## Desarrollo

Se requiere Python 3.12. Desde este directorio:

```bash
python -m pip install -e '.[test]'
python -m pytest tests/unit
agente-cognitivo-ingestion --help
```

La ejecución sin `--help` termina con error para evitar señalar éxito antes de implementar la ingestión. El Dockerfile empaqueta este mismo punto de entrada y presenta el mismo comportamiento; no debe programarse como tarea de producción todavía.

## Próximas decisiones

Definir fuentes, formatos, control de acceso, destino, estrategia de actualización, reglas de calidad, volumen y manejo de datos sensibles. Con esa información se implementarán configuración, dependencias, pruebas de integración e infraestructura.
