# Diseño de pantallas (bocetos)

> Bocetos entregados el 25 de noviembre de 2026. Se implementan en las fases 11 (API) y 12 (frontend) del [plan](11-plan-de-refactorizacion.md). Complementan la sección 5 de [Visión y modelo de dominio](00-vision-y-modelo-de-dominio.md).

## Estructura general

- **Barra lateral izquierda:** nombre de la app, módulos (Dashboard, ESE, CORHUILA, Niveles, Cursos, Importaciones…) y, abajo, **perfil y cerrar sesión**.
- **Arriba a la derecha:** avatar del usuario.
- **Arriba, en el contenido:** **filtros globales** (F): Año, Momento y Programa. Al entrar al panel de ESE o de CORHUILA aparecen además los filtros propios de ese panel.

## Boceto 1: ESE frente a CORHUILA

![ESE frente a CORHUILA](diseno/boceto-1-ese-vs-corhuila.png)

- El contenido se divide en dos columnas: **ESE** a la izquierda y **CORHUILA (CRH)** a la derecha.
- Los filtros globales afectan a las dos columnas.
- Cada columna se abre como su propio panel, con sus filtros adicionales, su detalle por programa y sus estudiantes.
- Si una prueba no tiene archivo cargado, su columna muestra "A la espera del archivo".

## Boceto 2: comparativa de crecimiento

![Dashboard comparativo](diseno/boceto-2-dashboard-comparativo.png)

Bajo los filtros globales hay un recuadro de **estados en común**: la evolución del puntaje **por programa** (no por estudiante) a lo largo del recorrido de la carrera:

```text
ESE Momento 1  →  ESE Momento 2  →  CORHUILA  →  ESE Momento 3
 (sem. 1–3)        (sem. 4–6)       (sem. 5–6)     (sem. 7 en adelante)
```

- **Medida:** puntaje promedio del programa en las 4 competencias comunes. Cuando el superior defina el promedio general, se usará esa fórmula.
- **Por tramo:** crecimiento o decrecimiento entre cada paso (M1→M2, M2→CRH, CRH→M3), en puntos y con flecha o color de mejora/retroceso.
- **Detalle:** también por competencia.
- **Filtros:** responde a Año y Programa.

## Historial del estudiante

En la ficha del estudiante se registra qué pruebas presentó y cuándo:

- ESE Momento 1, 2 y 3, con su periodo (`2026-1`) y el rango de semestres que mide.
- CORHUILA, si la presentó.
- Su semestre exacto solo se muestra si el archivo lo trae (desde 2025 ESE casi no envía `SEMESTRE`).

## Datos que lo alimentan (fase 8, ya disponibles)

- `period` y `moment` en cada resultado (de `SIM`, confirmado con `GRUPO`).
- `semester_range` en el historial y en la lista de estudiantes del programa.
- Filtros `period` y `moment` en la API.

Ejemplo del Excel de ESE con `SIM` y `GRUPO`:

![SIM y GRUPO en ESE](diseno/ejemplo-sim-grupo-ese.png)
