# Visión y modelo de dominio

> Documento núcleo del proyecto. Definido el 24 de noviembre de 2026. Si otro documento contradice a este, manda este. Los puntos marcados **(pendiente)** todavía no están decididos.

## En una frase

La aplicación recibe, cada periodo académico, dos archivos de resultados —la prueba de **ESE** y la prueba propia de **CORHUILA**—, los lleva a una **escala común de 4 niveles** y permite compararlos por momento, programa y año, para luego agrupar a los estudiantes por nivel y asignarles **cursos genéricos** de refuerzo.

## 1. Las dos pruebas

### ESE (empresa contratada por Corhuila)

ESE separa sus pruebas por **momentos**. Un momento no es una fecha: es la etapa de la carrera en la que se aplica la prueba y el rango de semestres que mide.

| Momento | Se aplica en | Mide los semestres |
|---|---|---|
| Momento 1 | Semestre 1 | 1 a 3 |
| Momento 2 | Semestre 4 | 4 a 6 |
| Momento 3 | Semestre 7 | 7 en adelante |
| Momento 4 (solo 2024) | — | 8 a 10 |

Aplicar los tres momentos permite seguir el crecimiento de una misma cohorte. Cada archivo de ESE trae varios programas.

### CORHUILA (prueba institucional)

- Tiene **un solo momento**: se aplica en el semestre 5 y mide los semestres **5 y 6**.
- El archivo es una exportación de calificaciones de Moodle (hoja `Calificaciones`).
- **No trae programa, semestre ni periodo.** El programa se toma de ESE (ver sección 4) y el periodo se indica al subir el archivo.

### Cuándo se cargan

El año tiene dos periodos: `AAAA-1` (antes de junio) y `AAAA-2` (después de junio). En **cada periodo** se cargan **dos archivos**: uno de ESE y uno de CORHUILA.

El periodo del año y el momento de la carrera son independientes: un Momento 1 puede aplicarse en `2026-1` o en `2026-2`.

## 2. Glosario

| Término | Significado |
|---|---|
| **Prueba / fuente** | `ESE` o `CORHUILA`. Todo resultado guardado indica de cuál viene. |
| **Periodo** | `AAAA-1` o `AAAA-2`. Es el momento del año en que se presentó la prueba. |
| **Año** | Parte `AAAA` del periodo. Es el filtro que se muestra en el dashboard. |
| **Momento** | Etapa de la carrera (ESE: 1, 2, 3; CORHUILA: único). |
| **Programa** | Carrera del estudiante. Se unifica por nombre normalizado (sin tildes, mayúsculas ni espacios extra). |
| **Competencia** | Área evaluada. Se comparan 4 (sección 3). |
| **Nivel** | Clasificación 1–4 de un puntaje según la escala común. |
| **Curso genérico** | Curso por competencia y nivel, no por programa. |
| **Importación** | Una carga de un archivo. Se identifica por fuente, periodo y huella SHA-256. |

## 3. Competencias y escala común de niveles

### Competencias comparadas

| Competencia | ESE | CORHUILA | Se compara |
|---|:---:|:---:|:---:|
| Lectura crítica | Sí | Sí | **Sí** |
| Razonamiento cuantitativo | Sí | Sí | **Sí** |
| Competencias ciudadanas | Sí | Sí | **Sí** |
| Inglés | Sí | Sí | **Sí** |
| Comunicación escrita | Sí | No | **No** |

Comunicación escrita se sigue importando desde ESE para no perder el dato de origen, pero **no se muestra, no se compara y no tiene cursos**. Corhuila no la evalúa ni ofrece cursos de ella.

### Escala única (las 4 competencias, ambas pruebas)

| Nivel | Puntaje | Inglés |
|---|---|---|
| Nivel 1 | 0 – 125 | A1 |
| Nivel 2 | 126 – 156 | A2 |
| Nivel 3 | 157 – 198 | B1 |
| Nivel 4 | 199 – 300 | B2 |

- La escala es la misma en ESE y en CORHUILA. El máximo es 300 en ambas.
- **Inglés usa los mismos límites.** Solo cambia la etiqueta que se muestra: A1 = Nivel 1, A2 = Nivel 2, B1 = Nivel 3, B2 = Nivel 4.
- Internamente el nivel siempre se guarda como número del 1 al 4. La etiqueta A1–B2 solo se usa en pantalla.
- **El nivel lo calcula la aplicación** a partir del puntaje, con esta tabla, en las dos pruebas. El nivel que trae el Excel de ESE (columnas Q:U) se guarda solo como referencia de auditoría.
- Límite: un puntaje igual al tope del rango pertenece a ese nivel (125 → Nivel 1; 126 → Nivel 2).

### Significado pedagógico de cada nivel

- **Nivel 1:** desempeño deficiente. Debe fortalecer los temas con mayores dificultades.
- **Nivel 2:** ligeramente superior al deficiente. Aún necesita fortalecer temas.
- **Nivel 3:** buen desempeño, con margen de mejora.
- **Nivel 4:** desempeño sobresaliente. Perfecciona aspectos para mantener el nivel.

> Aunque el estudiante obtenga 300/300, debe hacer al menos el curso de su nivel (Nivel 4).

## 4. Reglas de datos (iguales para ESE y CORHUILA)

### Puntajes vacíos, códigos y ceros

| Valor en la celda | Tratamiento |
|---|---|
| Número (incluido `0`) | **Cuenta.** Entra en promedios y niveles. Un `0` es un puntaje real (Nivel 1). |
| Vacío, `-`, `N`, `N/A`, `P` u otro texto | **No cuenta.** Es "sin puntaje": no entra en promedios ni niveles, y se informa en la auditoría de calidad de datos. |

### Quién "presentó" la prueba

- **ESE:** la columna `APLICA SIMULACRO = Si`, como se hace hoy.
- **CORHUILA:** tiene al menos un puntaje numérico en las 4 competencias.
- En ambos casos, quien no presentó aparece en las listas como **"No presentó"**, pero no entra en métricas.
- Si alguien presentó pero tiene una competencia sin puntaje, esa competencia queda fuera solo para esa persona.

### Identidad del estudiante

- **La identidad es el documento.** Todos los correos del estudiante (institucional y personal) se guardan como alias; se muestra el institucional más reciente.
- En CORHUILA, el estudiante se busca primero en **matriculados** del periodo (por documento, o por nombre completo y uno de sus dos correos). Si no está, se busca en ESE por **documento → nombre completo → correo** (el nombre solo si coincide con una sola persona; si hay varias, el correo desempata).
- El **tipo de documento** (`C`, `T`, `E`, `P`, `PPT`…) sale de matriculados y queda en el estudiante.

### Programa de los estudiantes de CORHUILA

El Excel de CORHUILA no trae el programa. Desde la fase 14 (27/11/2026), la fuente principal es el **archivo de matriculados** del mismo periodo:

1. **Manual:** si se asignó a mano, siempre manda.
2. **Matriculados:** la fila es de un matriculado si trae su **documento**, o si su **nombre completo** y **uno de sus dos correos** (personal o institucional) coinciden con la **misma** persona. Toma de ahí el programa, el semestre y el documento.
3. **ESE:** si no está en matriculados, el programa de su registro de ESE **más reciente**, de cualquier momento.
4. **Sin programa:** si no aparece en ninguno, queda por revisar y se asigna a mano.

- **Doble programa:** si el estudiante está matriculado en dos programas, el **mismo resultado cuenta en los dos**, porque la prueba se presenta por estudiante y no por programa. En las listas individuales aparece dos veces, y los dos registros solo difieren en el programa.
- El resultado del cruce **se guarda** en la fila de CORHUILA; el dashboard no lo repite en cada consulta. Se recalcula al importar CORHUILA, al subir matriculados, al activar un ESE nuevo, al asignar un programa a mano y con "Recalcular cruce".
- El orden de carga no importa: si CORHUILA se sube antes que matriculados, el cruce se repite al subir matriculados.

### Semestre

- ESE: desde 2025 casi no envía `SEMESTRE`. El semestre se trabaja por el **rango del momento** (M1 1–3, M2 4–6, M3 7 en adelante). El semestre exacto solo se muestra al consultar al estudiante, si el archivo lo trae.
- El **periodo del año** (`2026-1`) se toma de `SIM`; el **momento**, de `SIM`, confirmado con `GRUPO`.
- CORHUILA no trae semestre. Se toma de **matriculados** (el semestre en el que está el estudiante en ese periodo). Si la persona no está en matriculados, queda sin semestre; el rango que mide la prueba es 5–6.

### Promedio general

**(Pendiente: decisión del superior.)** Mientras tanto, la comparación usa el **promedio por competencia** y la **distribución por nivel** de las 4 competencias comunes. No se usa el GLOBAL de ESE para comparar, porque incluye Comunicación escrita.

## 5. Pantallas (rol instructor y superadmin)

### 5.1 Carga de archivos

En la pantalla de importación actual hay **dos espacios**: **ESE** y **CORHUILA**. El **archivo de matriculados** de cada periodo se sube aparte, en el módulo **Matriculados**, y solo lo sube el superadmin.

- ESE: el periodo se toma del archivo.
- CORHUILA: el periodo se elige al subir, y se sugiere a partir del nombre del archivo (por ejemplo `2026B` → `2026-2`).
- Las cargas son **independientes**. Si solo hay ESE, el dashboard muestra ESE y el lado de CORHUILA muestra "A la espera del archivo de CORHUILA para este periodo" (y al revés).

### 5.2 Dashboard comparativo (pantalla principal)

```
┌──────────── Filtros comunes: Año · Momento · Programa ────────────┐
├───────────────── ESE ─────────────┬──────────── CORHUILA ─────────┤
│ Tarjetas, niveles por competencia │ Tarjetas, niveles por compet. │
│ (o "a la espera del archivo")     │ (o "a la espera del archivo") │
├───────────────────────────────────┴───────────────────────────────┤
│ Resumen general:                                                  │
│ · Programa con peor nivel promedio (ambas pruebas)                │
│ · Competencia más baja en común entre ESE y CORHUILA              │
└───────────────────────────────────────────────────────────────────┘
```

- **Año:** se aplica a los dos lados.
- **Momento:** en ESE es 1, 2 o 3. En CORHUILA siempre es el único y no se puede cambiar.
- **Programa:** se aplica a los dos lados. En CORHUILA es el programa que viene de ESE Momento 2.
- **No hay filtro de semestre** en el dashboard: los momentos ya representan los ciclos.

### 5.3 Módulo ESE y módulo CORHUILA

Al hacer clic en uno de los lados se abre su módulo completo:

1. Resumen de la prueba con la **competencia más débil** de esa prueba.
2. Detalle por **programa**.
3. Lista de **estudiantes** del programa y su historial.

En **CORHUILA** (fase 15) hay además filtros de programa y semestre, búsqueda por nombre, documento, correo o programa, y una tabla con todos los estudiantes del periodo, con su nivel y sus puntajes.

### 5.4 Módulo de Estudiantes / Niveles

Reemplaza la pantalla actual de "Estudiantes" (que hoy lista cuentas de usuario).

- Lista **unificada** con los resultados de ESE y de CORHUILA.
- **Búsqueda** por nombre o correo.
- Agrupación por **nivel** en cada competencia.
- Filtros: **competencia, nivel, semestre, programa, prueba y año**.
- El estudiante lleva consigo su programa como dato, pero no se organiza por programa.
- Desde aquí se pasa a los cursos de cada nivel.

### 5.5 Módulo de Cursos genéricos

- Un curso = **competencia + nivel** (por ejemplo, "Razonamiento cuantitativo – Nivel 1"). Son 4 competencias × 4 niveles = 16 cursos base.
- La asignación es **automática**: cada estudiante entra al curso de su nivel en cada competencia, según su resultado más reciente.
- La vista del curso muestra a sus estudiantes con programa, semestre y prueba de origen, con los mismos filtros.

## 6. Fuera del alcance actual (futuro)

- Vista del rol **estudiante** con sus cursos asignados. Las cuentas se crearán a partir del archivo de matriculados.
- Etapas institucionales posteriores al Reconocimiento: Fortalecimiento, Profundización, Aceleración y Resultados Saber.
- Promedio general unificado (pendiente de decisión).

## 7. Decisiones pendientes

| # | Tema | Estado |
|---|---|---|
| 1 | Rangos que mide ESE Momento 2 y Momento 3 | Confirmado (25/11/2026): M2 = 4–6, M3 = 7 en adelante.|
| 2 | Fórmula de promedio general entre ESE y CORHUILA | Consulta con el superior |
| 3 | Curso "más reciente" si un estudiante tiene ESE y CORHUILA en el mismo periodo | Por definir |
| 4 | Significado de los códigos `N` y `P` en ESE | Pendiente con la institución (ya no afecta: Comunicación escrita sale del análisis) |
