# Documentación del proyecto

Esta documentación cubre el backend FastAPI de `code/api-reader-excel` y el frontend PHP ubicado en `front/`. El archivo [`../documentation.md`](../documentation.md) conserva el planteamiento académico inicial del proyecto; los documentos de esta carpeta describen el software implementado y distinguen las capacidades actuales de las funcionalidades propuestas.

## Guía de lectura

1. [Propósito y alcance](01-proposito-y-alcance.md)
2. [Arquitectura y flujo de datos](02-arquitectura.md)
3. [Instalación, inicialización y ejecución](03-instalacion-y-operacion.md)
4. [API y contratos](04-api.md)
5. [Tecnologías, dependencias y bases de datos](05-tecnologias-y-datos.md)
6. [Seguridad y migraciones](06-seguridad-y-migraciones.md)
7. [Pruebas y desarrollo](07-pruebas-y-desarrollo.md)
8. [Frontend PHP](08-frontend.md)

## Estado documentado

- API FastAPI con módulos de seguridad y lectura de Excel.
- Monolito modular organizado en rutas, servicios, repositorios, entidades, DTOs y migraciones.
- Aplicación PHP con navegación y pantallas separadas según el rol autenticado.
- Base de datos MySQL para usuarios y tokens de acceso.
- Procesamiento de Excel en memoria; los archivos y resultados no se persisten.
- El panel principal reserva un espacio para gráficos futuros; todavía no consume datos persistidos para generarlos.
- No incluye todavía clasificación pedagógica ni recomendación automática de cursos.
