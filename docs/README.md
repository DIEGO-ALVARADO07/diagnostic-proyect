# Documentación del proyecto

Esta documentación describe la API que actualmente se encuentra en `code/api-reader-excel`. El archivo [`../documentation.md`](../documentation.md) conserva el planteamiento académico inicial del proyecto; los documentos de esta carpeta describen el software implementado y distinguen las capacidades actuales de las funcionalidades propuestas.

## Guía de lectura

1. [Propósito y alcance](01-proposito-y-alcance.md)
2. [Arquitectura y flujo de datos](02-arquitectura.md)
3. [Instalación, inicialización y ejecución](03-instalacion-y-operacion.md)
4. [API y contratos](04-api.md)
5. [Tecnologías, dependencias y bases de datos](05-tecnologias-y-datos.md)
6. [Seguridad y migraciones](06-seguridad-y-migraciones.md)
7. [Pruebas y desarrollo](07-pruebas-y-desarrollo.md)

## Estado documentado

- API FastAPI con módulos de seguridad y lectura de Excel.
- Monolito modular organizado en rutas, servicios, repositorios, entidades, DTOs y migraciones.
- Base de datos MySQL para usuarios y tokens de acceso.
- Procesamiento de Excel en memoria; los archivos y resultados no se persisten.
- No incluye todavía clasificación pedagógica, recomendación de cursos ni interfaz frontend.
