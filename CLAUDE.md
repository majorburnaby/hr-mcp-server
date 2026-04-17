# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

FastAPI server exposing **HR employee data as MCP tools** for integration with Dify. The server reads from CSV files on every request (no database), serves a hand-crafted OpenAPI 3.0.3 schema (Dify cannot parse FastAPI's default 3.1.0), and is deployed on Vercel.

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

- **CSV as data source**: `load_df()` reads `data/employee_data_20260417.csv` and `load_training_df()` reads `data/all_employee_training_data_20260417.csv` on every request using pandas. The CSVs must be committed to the repo (Vercel has no persistent filesystem). No caching — if the dataset grows large, consider adding Redis.

- **MCP manifest at `GET /`**: Returns a JSON manifest that Dify uses to discover tools. The `tools` list here must stay in sync with the actual `OPENAPI_SCHEMA` paths and the `@app.get("/tools/...")` route definitions.

**Tool groups (33 tools total):**
1. **Headcount & Summary** — `total_active_employees`, `employee_summary`, `headcount_per_outlet`, `headcount_per_level`, `headcount_per_branch`
2. **Contracts & Lifecycle** — `contracts_expiring`, `contracts_missing_enddate`, `probation_employees`, `new_hires`
3. **Resign & Turnover** — `resigned_employees`, `resign_by_position`, `turnover_per_outlet`
4. **Search & Roster** — `search_employee`, `list_by_department`, `list_by_outlet`, `list_all_employees`, `list_active_by_status`, `list_employees_by_join_year`
5. **Assignment Gaps** — `unassigned_employees`, `outlets_without_leader`
6. **Training** (from `all_employee_training_data_20260417.csv`) — `training_wajib_not_completed`, `training_completion_by_outlet`, `training_not_started`, `safety_training_not_completed`, `sop_training_not_completed`, `onboarding_not_completed`, `training_incomplete_assigned`, `training_low_score`, `training_most_failed`, `training_prepost_comparison`, `get_employee_training`, `list_training_modules`
7. **Export** — `get_export_link`

**Training data** (`data/all_employee_training_data_20260417.csv`) — each row = one employee × one module assignment:

| Column | Notes |
|---|---|
| `employee_id`, `first_name`, `last_name`, `full_name` | identity fields; dedup key is `employee_id` |
| `outlet_name` | outlet or department name |
| `is_outlet` | `1` = real outlet, `0` = HO / Central Kitchen |
| `brand_name`, `company_code` | org hierarchy |
| `module_type` | format of training: `course` / `webinar` / etc |
| `module_name` | training module name |
| `module_assigned_date` | date the module was assigned to the employee |
| `pre_test_status`, `pre_test_grade` | pre-test taken flag and numeric score (null = not taken) |
| `post_test_status`, `post_test_grade` | post-test taken flag and numeric score (null = not taken) |
| `join_date` | employee's company join date |
| `is_module_mandatory` | `1` = mandatory, `0` = optional |

**Completion threshold:** `post_test_grade >= 90` is used as the pass/completion benchmark across all training tools.

Module keyword constants for categorisation (defined near `SPV_PATTERN`): `SAFETY_MODULE_PATTERN`, `SOP_MODULE_PATTERN`, `ONBOARDING_MODULE_PATTERN`.

**CSV column contract** (`data/employee_data_20260417.csv`):

| Column | Values |
|---|---|
| `role`, `full_name`, `employee_id` | strings |
| `organization_name`, `department`, `outlet`, `job_position`, `branch` | strings |
| `job_level` | integer |
| `join_date`, `resign_date`, `end_employment_date` | `YYYY-MM-DD` or empty |
| `employee_data_status` | `Active` / `Inactive` |
| `employment_status` | `Permanent` / `Contract` |

**SPV detection regex** (used by `outlets_without_leader` and `unassigned_employees`):
```python
SPV_PATTERN = "manager|supervisor|spv|head|lead|chief|director|koordinator|captain"
```

**Export system** — `GET /export` (file download, not MCP) + `GET /tools/get_export_link` (MCP tool):
- Dify calls `get_export_link` with `tool_name` matching the previous tool call and the same filter params
- Returns `download_url` pointing to `/export?tool=...&format=excel&...` — Dify presents this as a clickable link
- User clicks → browser downloads CSV or Excel (via `openpyxl`)
- `TOOL_FUNCTIONS` dict (end of [app/main.py](app/main.py)) maps all 32 tool names → handler functions
- `TOOL_ARRAY_KEY` maps tool names → response list key (`"employees"`, `"outlets"`, `"modules"`, etc.)
- Nested structures auto-flattened: `get_employee_training` (one row/module), `training_incomplete_assigned` (modules joined as CSV string), `list_active_by_status` (groups flattened with `employment_status_group` column)

## Adding a New Tool

1. Add the route handler `@app.get("/tools/<tool_name>")` in [app/main.py](app/main.py)
2. Add the path entry to `OPENAPI_SCHEMA["paths"]` (keep OpenAPI 3.0.3 compatible — no `nullable: true` on required fields)
3. Add an entry to the `"tools"` list in the `manifest()` function

## Deployment

Deployed via Vercel using `@vercel/python`. Config in [vercel.json](vercel.json) routes all traffic to `app/main.py`. The `data/` folder must be committed — it is the live data source.

To update employee data: replace `data/employee_data_20260417.csv` (or update `DATA_PATH` in [app/main.py](app/main.py)) and redeploy.
To update training data: replace `data/all_employee_training_data_20260417.csv` (or update `TRAINING_DATA_PATH`) and redeploy.

## Dify Integration

Dify imports tools from `GET /openapi.json`. The server URL in `OPENAPI_SCHEMA["servers"]` must match the deployed Vercel URL. All tool descriptions (in the schema) are written in Bahasa Indonesia to guide Dify's LLM routing. Every tool response includes a `"summary"` field in Bahasa Indonesia.
