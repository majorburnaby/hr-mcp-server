# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

FastAPI server exposing **HR employee data as MCP tools** for integration with Dify. The server reads from a CSV file on every request (no database), serves a hand-crafted OpenAPI 3.0.3 schema (Dify cannot parse FastAPI's default 3.1.0), and is deployed on Vercel.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
uvicorn app.main:app --reload --port 8000

# Interactive API docs (Swagger UI)
open http://localhost:8000/docs
```

## Architecture

Everything lives in a single file: [app/main.py](app/main.py)

**Key design decisions:**

- **Static OpenAPI schema**: FastAPI's auto-generated schema is disabled (`openapi_url=None`, `docs_url=None`). Instead, `OPENAPI_SCHEMA` is a hand-written `3.0.3` dict served at `GET /openapi.json`. When adding a new tool, you must add its path entry to `OPENAPI_SCHEMA` **and** add it to the manifest list in `GET /`.

- **CSV as data source**: `load_df()` reads `data/employee_data.csv` on every request using pandas. The CSV must be committed to the repo (Vercel has no persistent filesystem). No caching — if the dataset grows large, consider adding Redis.

- **MCP manifest at `GET /`**: Returns a JSON manifest that Dify uses to discover tools. The `tools` list here must stay in sync with the actual `OPENAPI_SCHEMA` paths and the `@app.get("/tools/...")` route definitions.

**Tool groups (31 tools total):**
1. **Headcount & Summary** — `total_active_employees`, `employee_summary`, `headcount_per_outlet`, `headcount_per_level`, `headcount_per_branch`
2. **Contracts & Lifecycle** — `contracts_expiring`, `contracts_missing_enddate`, `probation_employees`, `new_hires`
3. **Resign & Turnover** — `resigned_employees`, `resign_by_position`, `turnover_per_outlet`
4. **Search & Roster** — `search_employee`, `list_by_department`, `list_by_outlet`, `list_all_employees`, `list_active_by_status`, `list_employees_by_join_year`
5. **Assignment Gaps** — `unassigned_employees`, `outlets_without_leader`
6. **Training** (from `all_employee_training_data.csv`) — `training_wajib_not_completed`, `training_completion_by_outlet`, `certification_not_completed`, `training_not_started`, `training_low_score`, `training_most_failed`, `role_certification_not_completed`, `training_not_started_3months`, `leader_training_not_completed`, `safety_training_not_completed`, `sop_training_not_completed`

**Training data** (`data/all_employee_training_data.csv`) — each row = one employee × one module assignment:

| Column | Notes |
|---|---|
| `id_employee`, `full_name`, `outlet_name`, `brand_name` | identity fields |
| `module_id`, `module_name`, `type` | training module (`course`/`webinar`) |
| `join_date` | employee's company join date |
| `pre_test_grade`, `post_test_grade` | numeric scores; `post_test_grade` only non-null for `status_training_wajib=done` |
| `status_training_wajib` | `done` / `not yet` — **employee-level flag** (same value across all rows for a given employee) |
| `status_training_optional` | `done` / `not yet` — optional training status |

Module keyword constants for categorisation (defined near `SPV_PATTERN`): `SAFETY_MODULE_PATTERN`, `SOP_MODULE_PATTERN`, `LEADER_MODULE_PATTERN`, `CERT_MODULE_PATTERN`, `ROLE_CERT_MODULE_PATTERN`.

**CSV column contract** (`data/employee_data.csv`):

| Column | Values |
|---|---|
| `full_name`, `employee_id`, `department`, `outlet`, `job_position`, `branch` | strings |
| `job_level` | integer |
| `join_date`, `resign_date`, `end_employment_date` | `YYYY-MM-DD` or empty |
| `employee_data_status` | `Active` / `Inactive` |
| `employment_status` | `Permanent` / `Contract` |

**SPV detection regex** (used by `outlets_without_leader` and `unassigned_employees`):
```python
SPV_PATTERN = "manager|supervisor|spv|head|lead|chief|director|koordinator|captain"
```

## Adding a New Tool

1. Add the route handler `@app.get("/tools/<tool_name>")` in [app/main.py](app/main.py)
2. Add the path entry to `OPENAPI_SCHEMA["paths"]` (keep OpenAPI 3.0.3 compatible — no `nullable: true` on required fields)
3. Add an entry to the `"tools"` list in the `manifest()` function

## Deployment

Deployed via Vercel using `@vercel/python`. Config in [vercel.json](vercel.json) routes all traffic to `app/main.py`. The `data/` folder must be committed — it is the live data source.

To update employee data: replace `data/employee_data.csv` and redeploy.

## Dify Integration

Dify imports tools from `GET /openapi.json`. The server URL in `OPENAPI_SCHEMA["servers"]` must match the deployed Vercel URL. All tool descriptions (in the schema) are written in Bahasa Indonesia to guide Dify's LLM routing. Every tool response includes a `"summary"` field in Bahasa Indonesia.
