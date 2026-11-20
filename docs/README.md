# Documentación del proyecto

Esta documentación cubre el backend FastAPI de `back/api-reader-excel` y el frontend PHP ubicado en `front/`. El archivo [`../documentation.md`](../documentation.md) conserva el planteamiento académico inicial del proyecto; los documentos de esta carpeta describen el software implementado y distinguen las capacidades actuales de las funcionalidades propuestas.

## Guía de lectura

1. [Propósito y alcance](01-proposito-y-alcance.md)
2. [Arquitectura y flujo de datos](02-arquitectura.md)
3. [Instalación, inicialización y ejecución](03-instalacion-y-operacion.md)
4. [API y contratos](04-api.md)
5. [Tecnologías, dependencias y bases de datos](05-tecnologias-y-datos.md)
6. [Seguridad y migraciones](06-seguridad-y-migraciones.md)
7. [Pruebas y desarrollo](07-pruebas-y-desarrollo.md)
8. [Frontend PHP](08-frontend.md)
9. [Flujo completo del dashboard académico](09-flujo-dashboard-academico.md)

## Estado documentado

- API FastAPI con módulos de seguridad, lectura de Excel y persistencia del dashboard académico.
- Monolito modular organizado en rutas, servicios, repositorios, entidades, DTOs y migraciones.
- Aplicación PHP con navegación y pantallas separadas según el rol autenticado.
- Base de datos MySQL para usuarios, tokens y snapshots históricos del dashboard.
- `POST /excel/read` procesa y devuelve una hoja sin persistirla; `POST /excel/dashboard/import` guarda los resultados de `BD GEN` y la referencia visible de `TD PROGRAMAS`, pero no el archivo binario.
- La API expone consultas escalonadas para el snapshot activo, programas y estudiantes. El frontend PHP aún no consume esos endpoints desde su panel.
- No incluye todavía clasificación pedagógica ni recomendación automática de cursos.
