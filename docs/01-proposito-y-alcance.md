# Propósito y alcance

## Contexto del proyecto

El planteamiento inicial, recogido en [`documentation.md`](../documentation.md), propone analizar resultados de pruebas diagnósticas de estudiantes para identificar áreas y niveles de desempeño y, en una etapa futura, orientar actividades o cursos de refuerzo.

## Qué hace actualmente el software

La implementación actual es una API REST denominada **Diagnostic API** (versión declarada `1.0.0`). Proporciona:

- Inicio y cierre de sesión mediante tokens Bearer.
- Administración de cuentas con roles `superadmin`, `instructor` y `estudiante`.
- Lectura de archivos Excel y entrega de las filas de una hoja como JSON.
- Documentación interactiva de endpoints mediante OpenAPI en `/docs`.

La API recibe el Excel y responde con los datos leídos; no guarda el archivo ni los resultados. El módulo tampoco clasifica estudiantes, calcula niveles de desempeño ni asigna cursos automáticamente.

## A quién sirve

- El frontend puede autenticar usuarios, administrar perfiles según permisos y solicitar la lectura de una hoja de un Excel.
- Los instructores y superadmins pueden usar el endpoint de lectura Excel.
- Los estudiantes pueden consultar y editar solo la información permitida de su propio perfil.
- El superadmin administra las cuentas.

## Objetivo arquitectónico

El sistema se construyó como un **monolito modular**: seguridad y lectura Excel están aislados en módulos con responsabilidades propias, pero se ejecutan como una sola aplicación y proceso. Así se mantiene una solución sencilla para el alcance actual y una separación que permite evolucionar módulos sin introducir microservicios prematuramente.

## Alcance futuro, no implementado

La propuesta académica puede evolucionar hacia validación de plantillas de resultados, clasificación por áreas y niveles, recomendaciones de cursos y persistencia de reportes. Esas capacidades no deben considerarse disponibles hasta que se implementen y documenten expresamente.
