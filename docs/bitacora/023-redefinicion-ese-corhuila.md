# 023. Redefinición del proyecto: comparación ESE + CORHUILA

**Fecha:** 24 de noviembre de 2026
**Tipo:** decisión de producto (solo documentación, sin cambios de código)

## Qué cambió

El proyecto deja de analizar un único archivo y pasa a comparar dos pruebas por periodo:

- **ESE**: empresa contratada. Momentos 1, 2 y 3 (semestres 1, 4 y 7).
- **CORHUILA**: prueba institucional. Momento único (semestre 5, mide 5–6).

El detalle está en [00 · Visión y modelo de dominio](../00-vision-y-modelo-de-dominio.md) y el plan en [11 · Plan de refactorización](../11-plan-de-refactorizacion.md).

## Decisiones tomadas

1. Escala única de 4 niveles para las 4 competencias y para ambas pruebas: 0–125, 126–156, 157–198, 199–300. Inglés usa los mismos límites y se muestra como A1–B2.
2. El nivel lo calcula la aplicación. El nivel del Excel de ESE queda solo como auditoría.
3. Comunicación escrita se retira del análisis (CORHUILA no la evalúa ni tiene cursos de ella).
4. Reglas iguales para ambas pruebas: `0` cuenta; vacío, `-` y códigos de texto no cuentan.
5. El estudiante se identifica por correo institucional.
6. El programa de CORHUILA se toma de ESE Momento 2 (semestre 4), cruzando por correo.
7. Dos espacios de carga independientes. El dashboard muestra lo que haya y deja el otro lado "a la espera".
8. Dashboard con filtros comunes Año, Momento y Programa. Sin filtro de semestre.
9. Módulo de Estudiantes por nivel con filtros de semestre y programa, conectado a cursos genéricos (competencia + nivel).

## Por qué

La institución necesita comparar su prueba propia con la de ESE de forma equitativa y organizar el refuerzo por nivel, no por programa.

## Pendiente

- Rangos que mide ESE Momento 2 y Momento 3.
- Fórmula de promedio general (consulta con el superior).

## Análisis del archivo CORHUILA de muestra (2026-2)

439 filas, correos únicos, solo 4 con número de ID. 41 sin ninguna prueba presentada y 14 con alguna competencia sin presentar. Puntajes de 0 a 300 en múltiplos de 12. Con la escala única, la competencia más débil es Razonamiento cuantitativo (promedio 165,1; 35,5 % en Nivel 1).
