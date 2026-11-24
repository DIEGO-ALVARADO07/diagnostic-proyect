# Propósito y alcance

> El alcance vigente está en [Visión y modelo de dominio](00-vision-y-modelo-de-dominio.md). Este documento describe lo que hace hoy el código, que solo procesa la prueba de ESE.

## Contexto del proyecto

El planteamiento inicial, recogido en [`documentation.md`](../documentation.md), propone analizar resultados de pruebas diagnósticas de estudiantes para identificar áreas y niveles de desempeño y, en una etapa futura, orientar actividades o cursos de refuerzo.

## Qué hace actualmente el software

La implementación actual consta de la API REST **Diagnostic API** (versión declarada `1.0.0`) y una interfaz web PHP. La API proporciona:

- Inicio y cierre de sesión mediante tokens Bearer.
- Administración de cuentas con roles `superadmin`, `instructor` y `estudiante`.
- Lectura de archivos Excel y entrega de las filas de una hoja como JSON.
- Importación persistente de resultados históricos para el dashboard académico.
- Documentación interactiva de endpoints mediante OpenAPI en `/docs`.

Hay dos operaciones Excel distintas: `POST /excel/read` es una vista previa sin persistencia; `POST /excel/dashboard/import` valida e importa los datos de las hojas `BD GEN` y `TD PROGRAMAS` a MySQL. Ninguna guarda el archivo binario. El dashboard calcula métricas de los resultados importados, pero no asigna cursos ni recomendaciones pedagógicas automáticamente.

El frontend ofrece una pantalla de inicio con un espacio reservado para gráficos y vistas separadas para administrar cuentas, consultar estudiantes, leer reportes y editar el perfil. Aunque la API ya expone el dashboard persistente, el frontend PHP todavía no está conectado a esos endpoints; por eso su pantalla inicial sigue siendo un espacio reservado.

## A quién sirve

- El superadmin dispone de vistas para listar, crear y desactivar cuentas.
- El instructor dispone de vistas para consultar estudiantes y procesar archivos Excel.
- El estudiante dispone de vistas para consultar y actualizar su propio perfil.

## Objetivo arquitectónico

El sistema se construyó como un **monolito modular**: seguridad y lectura Excel están aislados en módulos con responsabilidades propias, pero se ejecutan como una sola aplicación y proceso. Así se mantiene una solución sencilla para el alcance actual y una separación que permite evolucionar módulos sin introducir microservicios prematuramente.

## Alcance futuro, no implementado

La propuesta académica puede evolucionar hacia clasificación pedagógica por áreas y niveles, recomendaciones de cursos e integración del dashboard en la interfaz PHP. Esas capacidades no deben considerarse disponibles hasta que se implementen y documenten expresamente.
