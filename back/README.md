# Backend

El backend de este proyecto es una API FastAPI modular. Su código está en [`api-reader-excel/`](./api-reader-excel/).

## Documentación

- [Guía técnica del backend](./api-reader-excel/IMPLEMENTATION.md): arquitectura, roles y permisos, endpoints, configuración de base de datos, migraciones, ejecución y pruebas.
- [Guía del frontend](../front/README.md): aplicación PHP, pantallas por rol, integración con la API y ejecución local.

La guía técnica es la referencia actual para arrancar esta versión modular de la API. [`note.md`](./note.md) conserva notas previas del entorno y puede mencionar una estructura anterior.

## Módulos principales

- `api-reader-excel/modules/security/`: inicio de sesión, perfiles, usuarios, roles y permisos.
- `api-reader-excel/modules/excel/`: lectura de libros de Excel y selección de hojas.
- `api-reader-excel/core/`: configuración y conexión compartida con la base de datos.
- `api-reader-excel/tests/`: pruebas automatizadas del backend.

La API aplica la autorización en el servidor. La visibilidad de opciones en el frontend no reemplaza estas comprobaciones.
