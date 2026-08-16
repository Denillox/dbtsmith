# dbtsmith

Turns a natural-language description of a data transformation into a working, validated **dbt project** — staging models, a mart, schema tests — instead of requiring someone to hand-write dbt SQL and YAML from scratch. Usable as a CLI or through a Streamlit web UI.

```
Input:  source = a Postgres table (or CSV file), instruction = "dedupe
        by email, join with customers and with products, aggregate
        order totals by month and by product"

Output: a scaffolded dbt project (staging model, mart, schema.yml with
        tests) that has actually been run against the real data and
        confirmed to pass — not just plausible-looking generated text.
```

## Why this isn't just an LLM wrapper

Asking an LLM to freely generate a dbt project from a prompt is unreliable — it hallucinates column names, references tables that don't exist, and produces SQL that may not run. This project avoids that failure mode in three ways:

1. **Structured intermediate representation first.** Natural language is parsed into a validated, typed structure (source, transformation steps, output shape) *before* any SQL is generated — not freeform text-to-code.
2. **Schema-grounded generation.** The tool introspects the real source's actual columns and types and grounds every step in that — an LLM can't invent a column that doesn't exist without it failing validation.
3. **Deterministic generation, real validation.** Once the structure is known, the actual SQL/YAML generation step is template-based, not LLM-generated — same input always produces the same output. The result is then run for real: `dbt run` and `dbt test` against real data, with pass/fail reported back.

## Architecture

```
Natural language input (source table/CSV, instruction, output name, join targets)
    ↓
Schema introspection (real column names/types — Postgres or CSV)
    ↓
LLM parses instruction → structured TransformationIR, grounded in real schema
    ↓
Deterministic generation (no LLM) → staging model, mart, schema.yml
    ↓
Validation: dbt seed (if CSV) + dbt run + dbt test against real data
    ↓
Pass/fail reported, generated project handed back
```

## Quickstart (Docker)

The fastest way to see it work — no local Python/dbt/Postgres setup required.

```bash
git clone https://github.com/Denillox/dbtsmith.git
cd dbtsmith
cp .env.example .env
# add your GROQ_API_KEY to .env

docker compose up -d postgres
docker compose run --rm dbtsmith \
  --source orders \
  --instruction "dedupe by email, join with customers, aggregate order totals by month" \
  --output monthly_customer_orders \
  --join customers \
  --output-dir /app/output
```

Generated output lands in `./docker_output` on your machine.

Multiple joins and multiple group-by columns both work — pass `--join` more than once, and describe more than one grouping dimension in the instruction:

```bash
docker compose run --rm dbtsmith \
  --source orders \
  --instruction "dedupe by email, join with customers and with products, aggregate order totals by month and by product" \
  --output monthly_product_orders \
  --join customers \
  --join products \
  --output-dir /app/output
```

A CSV file works the same way — just point `--source` at a `.csv` path instead of a table name (source type is inferred automatically from the extension):

```bash
docker compose run --rm dbtsmith \
  --source /app/tests/fixtures/sample_orders.csv \
  --instruction "dedupe by email, aggregate order totals by month" \
  --output monthly_orders \
  --output-dir /app/output
```

## Local development setup

```bash
python -m venv .venv
.venv\Scripts\activate      # Windows
pip install -e ".[dev]"

docker compose up -d postgres   # still needed for a real Postgres instance
cp .env.example .env            # add your GROQ_API_KEY

dbtsmith --source orders --instruction "..." --output ... --join customers
```

Add `--allow-retry` to enable the self-correction loop: on validation failure, the failure is fed back to the LLM for a corrected structured plan, then regenerated and revalidated (up to 2 total attempts). Off by default.

## Streamlit UI

A form-based web UI, as an alternative to the CLI — same underlying pipeline, with live step-by-step progress and the generated SQL/schema.yml displayed with syntax highlighting.

```bash
pip install -e ".[ui]"     # installs Streamlit, not included by default
streamlit run src/dbtsmith/ui/app.py
```

Opens automatically in your browser (usually `http://localhost:8501`). Fill in the same fields as the CLI (source, instruction, output name, join targets, output directory) and click Generate.

## Tech stack

- **Language:** Python 3.13+
- **LLM orchestration:** LangChain, using Groq (Llama 3.3 70B); LangGraph for the self-correction loop
- **Transformation target:** dbt Core (Postgres adapter)
- **Sources:** Postgres tables, or CSV files (loaded via `dbt seed`)
- **Validation:** pydantic for the structured IR, pytest for the test suite
- **CLI:** click
- **UI:** Streamlit (optional)
- **Containerization:** Docker + Docker Compose

## Project structure

```
src/dbtsmith/
├── ir/             # structured intermediate representation + NL parsing
├── introspect/      # real schema introspection (Postgres, CSV)
├── generate/        # deterministic dbt project generation
├── validate/        # dbt seed/run/test execution + pass/fail reporting
├── correct/         # LangGraph self-correction loop
├── dbt_templates/   # Jinja templates used by generate/
├── ui/              # Streamlit web UI
└── cli.py           # CLI entrypoint
```

## Testing

```bash
pytest
```

Some tests require the local Postgres container running (`docker compose up -d postgres`); tests involving LLM calls (instruction parsing, self-correction) require `GROQ_API_KEY` and are skipped automatically if it's not set. The Streamlit UI is tested via `streamlit.testing.v1.AppTest` and requires the `ui` extras installed (`pip install -e ".[ui,dev]"`). CI runs the deterministic subset of the suite on every push, including a real Postgres service container for schema-introspection and multi-join tests.

## v1 scope

Deliberately narrow, to prove the core pipeline end-to-end before broadening:

- Postgres table or CSV file as the main source; join targets are Postgres-only (no CSV-to-CSV or CSV-to-Postgres joins yet)
- Joins are star-schema only — every join connects back to the staging model directly, not to another join's table (no chained joins)
- Aggregations and group-by columns can only reference the staging model's own columns, not a joined table's columns (e.g. summing or grouping by a column from `customers` isn't supported yet)
- Basic generated tests only (`not_null`, `unique`) — scoped to what the IR structurally guarantees, not general data-quality heuristics
- Self-correction only ever produces a corrected structured plan, never edits generated SQL directly — generation stays fully deterministic even on retry
- CSV date-like columns are inferred as `text`, not `date` — works in practice (Postgres casts leniently in `DATE_TRUNC(...)`), but not a fully correct inference; documented rather than silently accepted

## Possible future improvements

- Aggregations and group-by referencing joined-table columns, not just the staging model
- Chained joins (joining against a previously-joined table, not just the staging model)
- Proper CSV date-column detection
- Richer Streamlit UI — per-test pass/fail breakdown, zip download of the generated project, general layout/UX polish
- Looser, more freeform natural-language input, once the structured-input pipeline is well-proven
