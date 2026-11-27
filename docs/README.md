# Documentación del proyecto

> Actualizada el 27 de noviembre de 2026. El código está en la rama `dev` (HEAD `a914c58`); esta rama `docs` solo contiene documentación.

> El proyecto compara dos pruebas, **ESE** (histórico por momentos) y **CORHUILA** (un archivo por periodo), con una escala común de niveles, y arma **cursos por nivel y materia** a partir de los estudiantes de los Excel. Para empezar, lee los [**manuales**](manuales/README.md).


Esta documentación cubre el backend FastAPI de `back/api-reader-excel` y el frontend PHP ubicado en `front/`. El archivo [`../documentation.md`](../documentation.md) conserva el planteamiento académico inicial del proyecto; los documentos de esta carpeta describen el software implementado y distinguen las capacidades actuales de las funcionalidades propuestas.

## Guía de lectura
- [**Manuales**](manuales/README.md): de usuario, de instalación, de administrador y técnico. ← empieza aquí
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
13. [Diseño de pantallas (bocetos)](12-diseno-de-pantallas.md)

## Estado documentado

- **Pruebas:** ESE (libro con `BD GEN` y `TD PROGRAMAS`, todo el histórico, momentos M1–M4) y CORHUILA (hoja `Calificaciones` de Moodle, un archivo por periodo). La carga solo permite el periodo actual y el anterior.
- **Comparación:** dashboard con ESE y CORHUILA lado a lado en un periodo. Solo se comparan las 4 competencias comunes, con una escala común de niveles 1–4.
- **Cruce de estudiantes:** el programa de cada estudiante de CORHUILA se busca en ESE (documento, luego nombre completo, luego correo). Los que no aparecen quedan "Sin programa" y se les asigna a mano.
- **Estudiantes por nivel:** todos los de los Excel (sin crearlos a mano), en N1–N4 y Sin resultado, con filtro por periodo.
- **Cursos:** Nivel → Curso (materia, nombre, descripción y metodología) → Estudiantes, con inscripción en bloque por el nivel en la materia.
- **Auditoría:** eliminación lógica con quién y cuándo, en cursos e importaciones. Solo el superadmin restaura.
- **Operación:** `tasks.ps1` (instalar, migrar, crear el superadmin, arrancar, probar, respaldar, respaldo diario programado y vaciar la base).
- **Base de datos:** migraciones `0001`–`0011`. 146 pruebas automáticas en SQLite.
- **Pendiente:** exportar los estudiantes para la plataforma oficial de CORHUILA (13c), crecimiento por programa (12c), y seguridad y CI (fase 6).
