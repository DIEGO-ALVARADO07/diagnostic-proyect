# 018 · Migración `0004_unify_programs`

- **Fase:** 5
- **Fecha:** 2026-11-22

## Por qué hace falta

Tus bases de datos ya tienen programas duplicados, creados por importaciones anteriores. El código nuevo (entrada 017) busca los programas por nombre normalizado, y el índice único no se puede crear mientras existan duplicados.

## Qué hace

Archivo: `migrations/versions/0004_unify_programs_by_normalized_key.py`.

**Upgrade.** Para cada `normalized_key` con más de un programa:

1. conserva el de **menor id**;
2. reasigna a ese programa las filas de `academic_results` y los alias de los duplicados (si un alias ya existe en el que se conserva, lo elimina para no repetirlo);
3. guarda el nombre de cada duplicado como alias y elimina los duplicados.

Después:

- asegura que cada programa tenga un alias con su propio nombre;
- reemplaza el índice `ix_academic_programs_normalized_key` por uno **único**.

**Downgrade.** Solo vuelve al índice no único. **No vuelve a separar** los programas fusionados: esa separación era un error y cada resultado conserva su `program_name_raw`.

## Cómo aplicarla

```powershell
$env:APP_MASTER_KEY = "<clave>"
.\tasks.ps1 migrate
```

**Haz una copia de seguridad de la base antes de aplicarla:** fusiona datos y el downgrade no los separa. En MySQL los cambios de índice (DDL) confirman la transacción de forma implícita. Si fallara la creación del índice, la fusión de datos ya habría quedado aplicada, lo cual no es un problema porque la fusión es correcta por sí misma.

## Pruebas

- `test_migration_chain_matches_models_and_downgrades` aplica ahora `0001` a `0004` sobre SQLite, verifica que el esquema coincide con los modelos y deshace todo.
- **Nuevo:** `test_unify_programs_merges_duplicates_and_keeps_results`. Crea 3 escrituras de un programa y una distinta, con resultados, y aplica `0004`. Verifica que quedan 2 programas, que los 5 resultados apuntan al correcto, que hay 4 alias y que el índice es único.
