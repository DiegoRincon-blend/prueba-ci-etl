# Instrucciones para colaboradores y agentes

- Lee el README y la documentación del pipeline antes de cambiar su comportamiento. Mantén cada pipeline instalable, comprobable y desplegable de forma independiente.
- Mantén la procedencia y los avisos de licencia del código trasladado. No asumas que los mismos derechos se aplican a todo el repositorio.
- No incluyas secretos, datos reales ni archivos de entrada o salida generados en Git. Usa credenciales temporales y roles IAM en AWS.
- Evita ejecutar cargas, DDL o despliegues contra producción durante el desarrollo. Usa datos sintéticos y entornos de prueba.
- Valida entradas, selección de etapas, dependencias de ejecución y reprocesamiento. No informes éxito cuando se omite trabajo requerido.
- Cualquier cambio en SQL debe considerar transacciones, concurrencia, permisos y datos preexistentes; documenta sus efectos y las pruebas realizadas.
- Ejecuta las pruebas apropiadas para los archivos modificados. Actualiza documentación y contratos de configuración cuando cambie el comportamiento.
- Conserva los cambios ajenos. No incorpores dependencias ni carpetas comunes hasta que sean necesarias.
