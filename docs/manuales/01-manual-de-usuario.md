# Manual de usuario

**Sistema:** Diagnóstico académico — comparación ESE + CORHUILA
**Para:** instructores (y superadmin en su uso diario)
**Versión:** 27 de noviembre de 2026

---

## 1. ¿Para qué sirve el sistema?

El sistema reúne los resultados de dos pruebas de los estudiantes y los convierte en información para decidir cursos de refuerzo:

| Prueba | Qué es | Cómo llega |
|---|---|---|
| **ESE** | Simulacros por momentos de la carrera. | Un Excel con **todo el histórico** (hojas `BD GEN` y `TD PROGRAMAS`). |
| **CORHUILA** | Prueba institucional de un periodo. | Un Excel **por periodo** (hoja `Calificaciones` exportada de Moodle). |

Con esos archivos puedes:

- **comparar** ESE y CORHUILA en el mismo periodo, por programa y por competencia;
- ver a **cada estudiante en un nivel** (N1 a N4) y encontrar quiénes necesitan refuerzo;
- **crear cursos** por nivel y materia, y agregarles de una vez a los estudiantes que tienen ese nivel.

Los estudiantes **no se crean a mano**: aparecen solos al subir los Excel.

El administrador sube además, en cada periodo, el **archivo de matriculados** de la institución. De ahí salen el **programa**, el **documento** y el **semestre** de los estudiantes de CORHUILA, que el Excel de Moodle no trae.

## 2. Conceptos básicos

**Periodo.** El año se divide en dos periodos: `AAAA-1` (primer semestre) y `AAAA-2` (segundo semestre). Ejemplo: `2026-2`.

**Momento (solo ESE).** ESE se aplica en momentos de la carrera:

| Momento | Semestres que mide |
|---|---|
| Momento 1 | 1 a 3 |
| Momento 2 | 4 a 6 |
| Momento 3 | 7 en adelante |
| Momento 4 | 8 a 10 (solo en el histórico de 2024) |

CORHUILA tiene un único momento (semestres 5 y 6).

**Competencias (materias).** Se comparan las **4 comunes** a las dos pruebas: Lectura crítica, Competencias ciudadanas, Razonamiento cuantitativo e Inglés.

**Niveles.** Cada puntaje de competencia (0 a 300) se ubica en una escala común:

| Nivel | Puntaje | Inglés |
|---|---|---|
| Nivel 1 | 0 a 125 | A1 |
| Nivel 2 | 126 a 156 | A2 |
| Nivel 3 | 157 a 198 | B1 |
| Nivel 4 | 199 a 300 | B2 |

**Nivel general de un estudiante.** Es el promedio de sus niveles en las 4 competencias, **redondeado hacia abajo**. Ejemplo: niveles 2, 3, 2 y 3 dan 2,5, así que queda en **Nivel 2**. "Sin resultado" quiere decir que no presentó o no tiene puntajes.

## 3. Entrar y salir

1. Abre la dirección que te dio el administrador (por ejemplo, `http://127.0.0.1:8081/front/login.php`).
2. Escribe tu **usuario** y tu **contraseña**, y pulsa **Entrar**.
3. Para salir, pulsa **Cerrar sesión**, abajo en el menú de la izquierda. Si el menú es largo, desplázalo con la rueda del mouse; "Cerrar sesión" siempre queda visible abajo.

La sesión dura 8 horas. Si vence, el sistema te devuelve a la pantalla de ingreso.

**Menú del instructor:** Dashboard, ESE, CORHUILA, Importar Excel, Estudiantes, Cursos y Mi perfil.

En el celular o en una ventana angosta, el menú se abre con el botón **☰** de arriba.

## 4. Importar Excel

Úsalo cada vez que llegue un archivo nuevo.

1. Entra a **Importar Excel**.
2. **Prueba:** elige **ESE** o **CORHUILA**.
3. **Periodo de la carga:** solo aparecen el periodo **actual** y el **anterior**, para no mezclar archivos de otros años.
4. **Archivo de Excel:** `.xlsx`, `.xlsm`, `.xls` u `.ods`, de hasta 30 MB.
5. Pulsa **Importar resultados** y espera; el botón dice "Procesando archivo…".

Qué tener en cuenta:

- **ESE** debe tener las hojas `BD GEN` y `TD PROGRAMAS`. Trae todo el histórico, así que cada carga nueva reemplaza a la anterior, que queda guardada como histórica.
- **CORHUILA** es la hoja `Calificaciones` de Moodle. Cada periodo tiene su propio archivo.
- **Si subes el mismo archivo dos veces**, no se duplica.
- **Si el sistema dice que el archivo está desactivado**, pídele al administrador que lo restaure; no sirve subirlo de nuevo.

## 5. Dashboard (inicio)

Muestra **ESE a la izquierda y CORHUILA a la derecha**, en el mismo periodo.

**Filtros:**

| Filtro | Qué hace |
|---|---|
| Año | Al elegirlo, se pone solo el periodo más reciente de ese año. |
| Periodo | Periodo 1 o 2 del año elegido. |
| Momento (solo ESE) | Solo ofrece los momentos que existen en ese periodo. |
| Programa | Filtra las dos pruebas por programa, incluido "Sin programa". |

**Volver al último periodo** regresa al periodo más reciente. Al entrar, siempre se ve el último periodo cargado.

**Cada mitad** muestra:
- el promedio, el nivel promedio, los estudiantes evaluados y las presentaciones;
- las barras de las 4 competencias, con la más baja marcada;
- la tabla de programas.

**Si una prueba no tiene archivo en ese periodo**, su mitad dice **"A la espera del archivo"** y, si el periodo se puede cargar, ofrece el botón para subirlo.

**Abajo** aparecen el **programa con el nivel más bajo** y la **competencia más baja en común**.

**Ver módulo** abre ESE o CORHUILA con los mismos filtros que tenías. Ejemplo: si estabas en 2026 · Periodo 1 · Momento 2, ESE abre así.

## 6. Módulo ESE (histórico)

- **Filtros:** Año, Periodo ("Todo el año" para ver el año completo), Momento y Asignatura (Global, todas o una competencia).
  - Al entrar se ve el periodo más reciente.
  - Al cambiar de año se elige su periodo más reciente.
  - Al cambiar de año o de periodo, el momento vuelve a "Todos".
  - **Restablecer** vuelve al último periodo.
- **Vista global:** indicadores y tarjetas de los programas, seis por página. El selector **Programa** muestra el detalle de uno.
- **Abrir un programa:** muestra sus estudiantes, con búsqueda por nombre.
- **Abrir un estudiante:** muestra su historial (último intento, evolución y puntaje por asignatura), con los filtros que estén activos.

## 7. Módulo CORHUILA

### Filtros

| Filtro | Qué hace |
|---|---|
| Periodo con archivo de CORHUILA | Solo ofrece los periodos que tienen archivo. Al entrar se ve el más reciente. |
| Programa | Deja un programa. Cada opción dice cuántas filas tiene, por ejemplo "INGENIERIA DE SISTEMAS (45)". |
| Semestre | El semestre en el que está el estudiante (sale de matriculados). "Sin semestre" son los que no están en matriculados. |
| Buscar estudiante | Por **nombre**, **documento**, **correo** o **programa**. Cada palabra puede estar en un dato distinto: "ana sistemas" encuentra a Ana en Ingeniería de Sistemas. |

**Restablecer** quita el programa, el semestre y la búsqueda. Debajo de los filtros se ve un resumen de lo que está activo.

### Vista general

- Los indicadores del periodo: promedio, nivel promedio, estudiantes evaluados y presentaciones.
- Las barras de las 4 competencias, con la más baja marcada.
- **Promedio por programa:** pulsa el nombre de un programa para entrar a su detalle.

### Detalle de un programa

Se abre al pulsar un programa o al elegirlo en el filtro **Programa**. Muestra:
- sus indicadores;
- su gráfica por competencia;
- la tabla con **solo sus estudiantes**.

Para volver, pulsa **← Todos los programas** o el botón **Atrás** del navegador.

### Resultados por estudiante

Una fila por estudiante y programa, de 25 en 25, con **Anterior** y **Siguiente**:
- nombre y correo;
- documento con su tipo (por ejemplo `C 1075…`), programa y semestre;
- nivel general;
- puntaje de Lectura, Ciudadanas, Cuantitativo e Inglés, y su promedio.

Quien está en **dos programas** aparece una vez por cada uno: su resultado cuenta en los dos.

La búsqueda solo cambia la tabla. Los indicadores y la gráfica siguen el programa y el semestre elegidos.

### Sin programa

Son estudiantes de CORHUILA que no se encontraron en **matriculados** del periodo (ni por documento, ni por nombre completo con uno de sus correos) ni en ESE. Para asignarles el programa:
1. Elige el programa en la fila del estudiante.
2. Pulsa **Guardar**.
3. El estudiante sale de la lista y sus resultados pasan a ese programa.

La asignación manual **manda sobre todo lo demás**.

- **Recalcular cruce:** vuelve a buscar a todos en matriculados y en ESE. Úsalo después de subir un ESE nuevo. Al subir matriculados se recalcula solo.
- **Subir Excel de CORHUILA:** te lleva a Importar Excel con la prueba ya elegida.

## 8. Estudiantes

Lista a **todos los estudiantes de los Excel** (ESE y CORHUILA juntos), en **5 grupos**: Nivel 1, Nivel 2, Nivel 3, Nivel 4 y Sin resultado.

- **Periodo:** Año → Periodo. Al entrar se ve el periodo actual.
  - En ese modo, cada estudiante aparece con el nivel que tuvo **en ese periodo**.
  - La opción **"Todo el histórico"** (al final de la lista de años) muestra a todos, cada uno con el nivel de su periodo más reciente con puntajes.
- **Pulsar un grupo** deja la lista solo con ese nivel, **sin cambiar el periodo**. Pulsarlo otra vez muestra todos; también sirve **Ver todos los niveles**.
- **Búsqueda** por nombre, documento o correo, y filtro por **Programa**.
- **Cada fila** trae el nombre y correo, documento con su tipo (por ejemplo `C 1075…`), programa, nivel general, nivel por competencia, promedio y "Según" (el periodo y la prueba de los que sale el nivel).
- Quien está matriculado en **dos programas** aparece **dos veces**, con los mismos datos y el mismo nivel; solo cambia el programa.
- La lista va de 50 en 50, con **Anterior** y **Siguiente**.

## 9. Cursos

La estructura es **Nivel → Curso → Estudiantes**. Cada nivel puede tener un curso para cada materia.

### Crear un curso

1. Completa: **Nivel**, **Materia evaluada**, **Nombre del curso**, **Descripción** (qué se trabaja) y **Metodología** (cómo se trabaja). La descripción y la metodología necesitan al menos 10 caracteres.
2. Pulsa **Crear curso**. El nivel del curso se abre solo.

No se puede repetir el mismo nombre en el mismo nivel y materia. El mismo nombre sí vale en otra materia o en otro nivel.

### Agregar estudiantes

1. Arriba, en **"Agregar estudiantes según el nivel del periodo"**, elige el periodo. Por defecto es el último; también está "Todo el histórico".
2. En el curso, pulsa **Agregar estudiantes**. Se inscriben **todos los que tienen el nivel del curso en su materia**.
   - Ejemplo: **Inglés de Nivel 1** recibe a los que tienen **A1 en Inglés**, aunque su nivel general sea otro.
   - Si lo pulsas otra vez, solo agrega a los que falten.
3. Al abrir un nivel ves cuántos estudiantes tienen ese nivel en cada materia, así sabes cuántos va a recibir cada curso.

### Ver y ajustar los estudiantes

- **Ver estudiantes** muestra nombre, correo, documento, programa, el nivel y periodo con los que se inscribió, y su nivel actual en la materia.
- **Quitar** saca a un estudiante del curso. El sistema pide confirmación.

### Eliminar un curso

- **Eliminar** pide confirmación en una ventana que muestra el curso, la materia, el nivel y los estudiantes.
- La eliminación es **lógica**: el curso se guarda con sus estudiantes y queda registrado quién lo eliminó.
- **Solo el administrador** puede habilitarlo de nuevo. Si necesitas recuperarlo, pídeselo.

## 10. Mi perfil

Puedes cambiar tu **nombre completo**, tu **correo** y tu **contraseña**. La contraseña es opcional y, si la cambias, debe tener al menos 12 caracteres. Pulsa **Guardar cambios**.

## 11. Confirmaciones

Antes de eliminar o quitar algo, el sistema muestra una ventana con los datos de lo que vas a cambiar:

| Botón | Significado |
|---|---|
| **Rojo** | Eliminar o quitar. |
| **Verde** | Habilitar o restaurar (solo administrador). |
| **Cancelar**, **Esc** o un clic fuera de la ventana | Cierra sin hacer nada. |

## 12. Preguntas frecuentes

| Pregunta | Respuesta |
|---|---|
| En Importar Excel no aparece un periodo viejo (por ejemplo, 2025-1). | Es a propósito: solo se puede subir el periodo actual o el anterior, para no mezclar archivos de otros años. |
| Una mitad del dashboard dice "A la espera del archivo". | Esa prueba aún no tiene archivo en ese periodo. |
| Un estudiante de CORHUILA aparece "Sin programa". | No se encontró en matriculados del periodo ni en ESE. Asígnale el programa en el módulo CORHUILA, o pulsa "Recalcular cruce" después de subir un ESE nuevo. Si falta el archivo de matriculados del periodo, pídeselo al administrador. |
| Un estudiante aparece dos veces en Estudiantes o en CORHUILA. | Está matriculado en dos programas. Su resultado cuenta en los dos; los registros solo difieren en el programa. |
| No encuentro a un estudiante en CORHUILA. | Escribe solo una parte: el documento, el correo o el nombre y un apellido. Revisa también que el filtro de Programa o Semestre no lo esté dejando fuera, o pulsa **Restablecer**. |
| ¿Por qué un estudiante está en Nivel 2 si en Inglés tiene B2? | El nivel general es el promedio de las 4 competencias. Para cursos de una materia se usa el nivel de esa materia. |
| Eliminé un curso por error. | Pídele al administrador que lo habilite en "Cursos eliminados". Vuelve con sus estudiantes. |
| El sistema me sacó a la pantalla de ingreso. | La sesión venció (8 horas). Entra de nuevo. |
