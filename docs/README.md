# Documentación del proyecto

> Actualizada el 23 de noviembre de 2026. El código está en la rama `dev`; esta rama `docs` solo contiene documentación.

> **24/11/2026:** el proyecto se redefinió para comparar dos pruebas (ESE y CORHUILA). Los documentos 01–10 describen el código actual, que solo maneja ESE. El objetivo y el plan están en [00](00-vision-y-modelo-de-dominio.md) y [11](11-plan-de-refactorizacion.md).

Esta documentación cubre el backend FastAPI de `back/api-reader-excel` y el frontend PHP ubicado en `front/`. El archivo [`../documentation.md`](../documentation.md) conserva el planteamiento académico inicial del proyecto; los documentos de esta carpeta describen el software implementado y distinguen las capacidades actuales de las funcionalidades propuestas.

## Guía de lectura
0. [**Visión y modelo de dominio**](00-vision-y-modelo-de-dominio.md) ← núcleo del proyecto (ESE + CORHUILA)
1. [Propósito y alcance](01-proposito-y-alcance.md)
2. [Arquitectura y flujo de datos](02-arquitectura.md)
3. [**Instalación, uso y operación**](03-instalacion-y-operacion.md) ← empieza aquí
4. [API y contratos](04-api.md)
5. [Tecnologías, dependencias y bases de datos](05-tecnologias-y-datos.md)
6. [Seguridad y migraciones](06-seguridad-y-migraciones.md)
7. [Pruebas y desarrollo](07-pruebas-y-desarrollo.md)
8. [Frontend PHP](08-frontend.md)
9. [Flujo completo del dashboard académico](09-flujo-dashboard-academico.md)
10. [Estado de entrega y continuidad entre sesiones](10-estado-y-continuidad.md)
11. [Bitácora de cambios](bitacora/README.md): qué se cambió, dónde y por qué, en orden (revisión técnica de noviembre de 2026).
12. [Plan de refactorización ESE + CORHUILA](11-plan-de-refactorizacion.md)

## Estado documentado

- API FastAPI con módulos de seguridad, lectura de Excel y persistencia del dashboard académico.
- Monolito modular organizado en rutas, servicios, repositorios, entidades, DTOs y migraciones; configuración, sesión de base de datos y `Base` ORM compartidas en `core/`, migraciones en `migrations/`.
- Operación con `tasks.ps1` (`install`, `migrate`, `bootstrap`, `run`, `test`); `core/.env` no se versiona y se crea desde `core/.env.example`.
- Aplicación PHP con navegación y pantallas separadas según el rol autenticado.
- Base de datos MySQL para usuarios, tokens y snapshots históricos del dashboard.
- `POST /excel/read` procesa y devuelve una hoja sin persistirla; `POST /excel/dashboard/import` guarda los resultados de `BD GEN` y la referencia visible de `TD PROGRAMAS`, pero no el archivo binario.
- El frontend PHP consume el dashboard persistido, con gráficos y consultas escalonadas de resumen, programa y estudiante.
- La vista global distribuye los programas en tarjetas de seis; los filtros de programa siguen el año/simulacro activos y la búsqueda estudiantil actualiza solo su tabla.
- Las tarjetas y el resumen global usan `average_general` (promedio conjunto de competencias no nulas), sin modificar `average_global` ni `simple_competence_average`; la desviación general coincide con la definición muestral de Power BI.
- El módulo **Importaciones** está separado y solo aparece para superadmin. Permite revisar todos los estados y desactivar snapshots de forma lógica; la revisión `0003_soft_delete_excel_imports` añade `deleted_at`.
- Los programas se unifican por nombre normalizado (migración `0004_unify_programs`), los semestres `4`/`SEMESTRE 4` se tratan igual y la auditoría incluye un reporte de calidad de datos.
- Las consultas del dashboard usan una caché en memoria por importación (5–150 ms por consulta con 20.000 filas).
- No incluye todavía clasificación pedagógica ni recomendación automática de cursos.
