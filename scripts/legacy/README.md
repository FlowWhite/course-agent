# Legacy utilities

`sqlite/` contains the SQLite-era initialization, import, backup and data-access helpers. The production FastAPI service now uses PostgreSQL and does not import these modules.

They are retained only for historical data inspection or migration work. Run them as modules from the project root, for example:

```powershell
python -m scripts.legacy.sqlite.init_db
python -m scripts.legacy.sqlite.import_data
```

Do not use these commands against the production PostgreSQL workflow.
