# 029. Dashboard comparativo, cruce por nombre completo y programa manual

**Fecha:** 26 de noviembre de 2026
**Fase:** 11
**Rama de código:** `dev`

## Cambio de negocio

El Excel de CORHUILA no se puede modificar (no traerá `Número de ID`) y el correo puede variar. Por eso:

1. **Cruce con ESE en todo su histórico**, en este orden:
   - documento, si algún día viene;
   - **nombre completo** que coincide con una sola persona;
   - si el nombre coincide con varias, el correo desempata;
   - si el nombre no aparece, el correo.
2. **Programa:** el del registro de ESE **más reciente, de cualquier momento**, haya presentado o no. Es el programa en el que el estudiante está ahora: cubre homologaciones y materias adelantadas (caso Gabriela). Deja de usarse el Momento 2.
3. **Programa manual:** se asigna desde la lista "por revisar" de CORHUILA. Se guarda en el estudiante y **manda sobre ESE**. Es un caso excepcional, porque casi siempre el estudiante está en ESE.
4. **Dashboard principal: solo el último periodo cargado.** Si se sube 2026-1, se ve 2026-1 de las dos pruebas; al subir 2026-2, solo 2026-2. Lo que no se haya subido queda "a la espera". El histórico de ESE queda en su módulo.
5. **"Sin programa"** es un subprograma con su propio promedio, que entra en el promedio general. Al abrirlo se listan sus estudiantes con nombre y correo.
6. **Semestre:** ya no es un filtro; el rango de cada momento queda solo como información. El filtro de **momento** se mantiene.
7. **4 competencias** (sin Comunicación escrita), confirmado por el ingeniero, con un aviso en el frontend.

## Qué cambió en el código

- `services/program_resolution.py`:
  - `match_student`: documento → nombre → correo.
  - `choose_current_program`: registro más reciente con programa.
  - Nuevo `assign_student_program` y `ProgramLookup` con `program_source`, `program_period` y `program_moment`.
- `entities/assessment.py`:
  - `ProgramResolution` = `ESE`, `MANUAL`, `SIN_PROGRAMA` (antes `ESE_M2`).
  - `SIN_PROGRAMA_ID = "sin-programa"`.
- `entities/academic.py`: `AcademicStudent.assigned_program_id`, `assigned_program_by_user_id`, `assigned_program_at`.
- `services/dashboard_compare_service.py` (nuevo):
  - periodo actual;
  - bloques ESE y CORHUILA (cualquiera puede venir vacío);
  - programa con peor nivel promedio (sin contar "Sin programa");
  - competencia más baja en común y la más débil de cada prueba.
- `services/dashboard_metrics.py`:
  - `average_level` (nivel promedio 1–4).
  - `unique_students` ("Estudiantes evaluados") cuenta **personas**: el estudiante resuelto; si no hay, el documento; si tampoco, el correo. Antes contaba solo documentos, y en CORHUILA, que casi nunca trae documento, salían 3 estudiantes de 398 presentaciones.
- `entities/dashboard.py`: `DashboardRecord.student_id` y la propiedad `identity`.
- `services/dashboard_data_quality.py`: `identity.documents_with_multiple_programs`.
- `services/dashboard_dataset_loader.py`: las filas sin programa tienen `program_id = "sin-programa"`, así que la tarjeta se puede abrir.
- Filtro de semestre eliminado de `DashboardFilterQuery`, rutas y opciones (`filters.semesters`).
- **Nuevos endpoints** (instructor y superadmin):

| Endpoint | Para qué |
|---|---|
| `GET /excel/dashboard/compare?moment=&program_id=` | Dashboard principal. |
| `GET /excel/dashboard/catalog/programs` | Programas para asignar a mano. |
| `PUT /excel/dashboard/review/students/{student_id}/program` (`{"program_id": n \| null}`) | Asignar o quitar el programa manual. |
| `POST /excel/dashboard/corhuila/resolve` | Volver a cruzar CORHUILA con ESE. |

- `GET /excel/dashboard/program-lookup`: ya no recibe `period`.
- **Migración `0008_manual_program`:** columnas del programa manual; `ESE_M2` → `ESE`.
- **Frontend:** nota de las 4 competencias bajo los KPI; `data.php` ya no reenvía `semester`.

## Cómo aplicarla

```powershell
.\tasks.ps1 backup -Label antes-0008
```

```powershell
.\tasks.ps1 migrate
```

Luego, en Swagger, `POST /excel/dashboard/corhuila/resolve` recalcula con la regla nueva las filas de CORHUILA ya guardadas.

## Verificación

- `python -m unittest discover -s tests`: 121 pruebas OK (antes 108). Las nuevas cubren:
  - estudiantes únicos sin documento (por estudiante resuelto o correo);
  - dashboard vacío, solo ESE del periodo, ambas pruebas, periodo nuevo "a la espera";
  - filtros de momento y programa, y la tarjeta "Sin programa";
  - programa manual: resuelve pendientes, manda sobre ESE y se puede quitar;
  - catálogo de programas y recálculo;
  - estudiantes con varios programas;
  - migración 0008;
  - cruce por nombre con desempate por correo, y programa de un Momento 4.
- `compileall` sin errores; imports sin uso revisados; `php -l` sin errores en `screen.php` y `data.php`.
- Libro real, después de `POST /excel/dashboard/corhuila/resolve`: `changed_rows` 405, `without_program` 31 (antes 55). Coincide con los 31 `SIN_COINCIDENCIA`: todo estudiante encontrado en ESE ya tiene programa.
