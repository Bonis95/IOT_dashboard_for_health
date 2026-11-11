# Vitals explorer

Pick a date and time range and some of ten body-sensor parameters, and see the readings as time-aligned charts, a table, and a CSV download.

- **Backend:** Python, FastAPI, MySQL (via PyMySQL)
- **Frontend:** plain HTML/CSS/JS served by the same app (Chart.js for charts, flatpickr for the calendar)
- **Data:** 721 sample readings, one per minute, from 20.09.2026 20:10 to 21.09.2026 08:10, for ten parameters: heart rate, systolic and diastolic blood pressure, SpO2, respiratory rate, body temperature, blood glucose, HRV, skin conductance, stress level.

## Run it

You need Python 3.9 or newer and a running MySQL 8 (or MariaDB) server.

```bash
python -m venv .venv
# macOS / Linux:  source .venv/bin/activate
# Windows:        .venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

`main.py` creates the database and table, fills them with sample data on the first run, starts the server and opens http://localhost:8000.

If MySQL rejects the login, `main.py` asks for the password in the terminal. To avoid the prompt, copy `.env.example` to `.env` and set `MYSQL_USER` / `MYSQL_PASSWORD`.

Useful flags: `--reseed` (delete and regenerate the sample data), `--no-browser`, `--port 9000`.

The UI loads Chart.js and flatpickr from a CDN, so the browser needs internet access. Without it the date fields fall back to native pickers and the Table view still works.

## Using the UI

1. Choose **From** and **To** with the calendar and 24-hour time picker (or use *Full range*, *First 3 hours*, *Last 3 hours*), then press **Show data**.
2. Toggle parameters on or off. The view updates immediately.
3. **Charts:** one panel per parameter, all on the same time axis. Move the pointer over any panel: a vertical line appears in every panel and one readout shows all values at that minute. Each panel header shows min, average and max for the selected range.
4. **Table** shows every reading; **Download CSV** exports the current selection.

## API

| Endpoint | Purpose |
|---|---|
| `GET /api/data?start=2026-09-20T20:10&end=2026-09-21T08:10&params=heart_rate,spo2` | Readings in the range (`params` optional, default all ten) |
| `GET /api/parameters` | Parameter keys, labels, units |
| `GET /api/bounds` | First reading, last reading, row count |
| `GET /api/health` | Service and database status |
| `GET /docs` | Interactive API documentation |

## Project layout

```
main.py              start here
app/
  api.py             FastAPI routes
  database.py        MySQL connection, schema, seeding, queries
  sql.py             SQL text (column names checked against a whitelist)
  logic.py           request parsing and response shaping
  generator.py       random but plausible sample data
  parameters.py      the ten parameters, defined once
  config.py          settings from environment / .env
static/              index.html, style.css, app.js
tests/test_logic.py  tests that need no database
```

Run the tests with `python -m unittest discover -s tests -v`.

## Design notes

- One table, one row per minute (`recorded_at DATETIME` primary key), one `DOUBLE` column per parameter. Range queries use the primary-key index.
- Column names are never taken from user input directly; they are checked against the fixed parameter list, and all values go through query placeholders.
- Timestamps are stored and shown as wall-clock time with no timezone, so what you pick in the calendar is exactly what is queried.
- A query returns at most `MAX_ROWS` rows (default 50,000) and says so when it was cut off.
- Each request opens its own short-lived MySQL connection. That is simple and fine for one analyst; use a connection pool for many concurrent users.
- To add or change a parameter, edit `app/parameters.py` and `app/generator.py`, then run `python main.py --reseed` (the table schema is created from the parameter list).

## Troubleshooting

- **Access denied for user:** set the right `MYSQL_USER` / `MYSQL_PASSWORD` in `.env`. If you prefer a dedicated account:
  `CREATE USER 'vitals'@'localhost' IDENTIFIED BY 'choose-a-password'; GRANT ALL PRIVILEGES ON vitals_db.* TO 'vitals'@'localhost';`
- **Can't connect to MySQL server:** start the MySQL service and check `MYSQL_HOST` / `MYSQL_PORT`.
- **Port already in use:** run `python main.py --port 8001`.
