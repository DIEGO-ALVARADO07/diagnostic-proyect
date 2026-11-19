# Propósito y alcance

## Contexto del proyecto

El planteamiento inicial, recogido en [`documentation.md`](../documentation.md), propone analizar resultados de pruebas diagnósticas de estudiantes para identificar áreas y niveles de desempeño y, en una etapa futura, orientar actividades o cursos de refuerzo.

## Qué hace actualmente el software

La implementación actual consta de la API REST **Diagnostic API** (versión declarada `1.0.0`) y una interfaz web PHP. La API proporciona:

- Inicio y cierre de sesión mediante tokens Bearer.
- Administración de cuentas con roles `superadmin`, `instructor` y `estudiante`.
- Lectura de archivos Excel y entrega de las filas de una hoja como JSON.
- Documentación interactiva de endpoints mediante OpenAPI en `/docs`.

La API recibe el Excel y responde con los datos leídos; no guarda el archivo ni los resultados. El módulo tampoco clasifica estudiantes, calcula niveles de desempeño ni asigna cursos automáticamente.

El frontend ofrece una pantalla de inicio con un espacio reservado para futuros gráficos y vistas separadas para administrar cuentas, consultar estudiantes, leer reportes de Excel y editar el perfil. Los gráficos aún no muestran métricas porque el backend no persiste los resultados de los archivos.

## A quién sirve

- El superadmin dispone de vistas para listar, crear y desactivar cuentas.
- El instructor dispone de vistas para consultar estudiantes y procesar archivos Excel.
- El estudiante dispone de vistas para consultar y actualizar su propio perfil.

## Objetivo arquitectónico

El sistema se construyó como un **monolito modular**: seguridad y lectura Excel están aislados en módulos con responsabilidades propias, pero se ejecutan como una sola aplicación y proceso. Así se mantiene una solución sencilla para el alcance actual y una separación que permite evolucionar módulos sin introducir microservicios prematuramente.

## Alcance futuro, no implementado

La propuesta académica puede evolucionar hacia validación de plantillas de resultados, clasificación por áreas y niveles, recomendaciones de cursos y persistencia de reportes. Esas capacidades no deben considerarse disponibles hasta que se implementen y documenten expresamente.
