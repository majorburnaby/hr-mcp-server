"""
HR Employee MCP Server — FastAPI v2.0.0
MCP-compatible API server for Dify tool integration.
17 tools covering headcount, contracts, turnover, search, and assignment gaps.
"""

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
import pandas as pd
from datetime import date
from typing import Optional
import os, copy

# ── App ───────────────────────────────────────────────────────────────────────

SERVER_URL = os.getenv("SERVER_URL", "https://hr-mcp-server.vercel.app")

app = FastAPI(
    title="HR Employee MCP Server",
    description=(
        "MCP-compatible FastAPI server for Dify. "
        "17 tools to answer HR questions about employees in Bahasa Indonesia."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _to_openapi30(obj):
    """Recursively convert OpenAPI 3.1 constructs → 3.0 so Dify can parse them."""
    if isinstance(obj, dict):
        # anyOf: [{type:X},{type:null}]  →  type:X + nullable:true
        if "anyOf" in obj:
            non_null = [s for s in obj["anyOf"] if s.get("type") != "null"]
            has_null  = len(non_null) < len(obj["anyOf"])
            if non_null:
                merged = {k: v for k, v in obj.items() if k != "anyOf"}
                merged.update(non_null[0])
                if has_null:
                    merged["nullable"] = True
                obj = merged
        return {k: _to_openapi30(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_to_openapi30(i) for i in obj]
    return obj


@app.get("/openapi.json", include_in_schema=False)
def custom_openapi_endpoint():
    """OpenAPI 3.0.3 schema — compatible with Dify's Custom Tool importer."""
    raw    = get_openapi(title=app.title, version=app.version,
                         description=app.description, routes=app.routes)
    schema = _to_openapi30(copy.deepcopy(raw))
    schema["openapi"] = "3.0.3"
    schema["servers"] = [{"url": SERVER_URL}]
    return schema

# ── Data loader ───────────────────────────────────────────────────────────────

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "employee_data.csv")

def load_df() -> pd.DataFrame:
    """Load and normalise employee CSV on every request."""
    df = pd.read_csv(DATA_PATH, dtype=str)
    df.columns = [c.strip().lower() for c in df.columns]
    for col in ["join_date", "resign_date", "end_employment_date"]:
        df[col] = df[col].replace({"0000-00-00": None, "nan": None, "NaN": None})
        df[col] = pd.to_datetime(df[col], errors="coerce")
    df["job_level"] = pd.to_numeric(df["job_level"], errors="coerce")
    df["employee_data_status"] = df["employee_data_status"].str.strip()
    df["employment_status"]    = df["employment_status"].str.strip()
    return df

SPV_PATTERN = "manager|supervisor|spv|head|lead|chief|director|koordinator|captain"

# ── MCP manifest ──────────────────────────────────────────────────────────────

@app.get("/", summary="MCP tool manifest")
def manifest():
    """MCP manifest — Dify reads this to discover available tools."""
    return {
        "schema_version": "v1",
        "name_for_human": "HR Employee Database",
        "name_for_model": "hr_employee_db",
        "description_for_human": "Query employee data: headcount, contract expiry, turnover, probation, and more.",
        "description_for_model": (
            "Use this server to answer HR questions about employees. "
            "Capabilities: count active/inactive employees, list expiring contracts, check probation, "
            "analyse turnover by outlet or position, find employees missing outlet/jabatan/SPV, "
            "headcount by outlet/level/branch, search by name. "
            "Every response includes a 'summary' field in Bahasa Indonesia."
        ),
        "contact_email": "admin@example.com",
        "api": {"type": "openapi", "url": "/openapi.json"},
        "tools": [
            # Group 1 — Headcount & summary
            {"name": "total_active_employees",   "endpoint": "/tools/total_active_employees",    "method": "GET", "description": "Jumlah total karyawan aktif vs tidak aktif"},
            {"name": "employee_summary",          "endpoint": "/tools/employee_summary",          "method": "GET", "description": "Ringkasan statistik: total, tipe kontrak, top department"},
            {"name": "headcount_per_outlet",      "endpoint": "/tools/headcount_per_outlet",      "method": "GET", "description": "Jumlah karyawan per outlet"},
            {"name": "headcount_per_level",       "endpoint": "/tools/headcount_per_level",       "method": "GET", "description": "Distribusi karyawan per job level"},
            {"name": "headcount_per_branch",      "endpoint": "/tools/headcount_per_branch",      "method": "GET", "description": "Jumlah karyawan per branch/brand/perusahaan"},
            # Group 2 — Contracts & lifecycle
            {"name": "contracts_expiring",        "endpoint": "/tools/contracts_expiring",        "method": "GET", "description": "Karyawan kontrak yang habis pada bulan/tahun atau dalam N hari"},
            {"name": "contracts_missing_enddate", "endpoint": "/tools/contracts_missing_enddate", "method": "GET", "description": "Kontrak aktif tanpa tanggal akhir (proxy belum ttd kontrak)"},
            {"name": "probation_employees",       "endpoint": "/tools/probation_employees",       "method": "GET", "description": "Karyawan masih dalam masa probasi"},
            {"name": "new_hires",                 "endpoint": "/tools/new_hires",                 "method": "GET", "description": "Karyawan baru yang bergabung dalam periode tertentu"},
            # Group 3 — Resign & turnover
            {"name": "resigned_employees",        "endpoint": "/tools/resigned_employees",        "method": "GET", "description": "Daftar karyawan yang sudah resign / tidak aktif"},
            {"name": "resign_by_position",        "endpoint": "/tools/resign_by_position",        "method": "GET", "description": "Posisi/jabatan paling banyak resign"},
            {"name": "turnover_per_outlet",       "endpoint": "/tools/turnover_per_outlet",       "method": "GET", "description": "Tingkat resign/turnover per outlet"},
            # Group 4 — Search & roster
            {"name": "search_employee",           "endpoint": "/tools/search_employee",           "method": "GET", "description": "Cari karyawan berdasarkan nama (partial match)"},
            {"name": "list_by_department",        "endpoint": "/tools/list_by_department",        "method": "GET", "description": "Daftar karyawan berdasarkan department"},
            {"name": "list_by_outlet",            "endpoint": "/tools/list_by_outlet",            "method": "GET", "description": "Daftar karyawan berdasarkan outlet/lokasi"},
            # Group 5 — Assignment gaps
            {"name": "unassigned_employees",      "endpoint": "/tools/unassigned_employees",      "method": "GET", "description": "Karyawan belum assign outlet, jabatan, atau outlet tanpa SPV"},
            {"name": "outlets_without_leader",    "endpoint": "/tools/outlets_without_leader",    "method": "GET", "description": "Outlet yang belum memiliki leader atau manager"},
        ],
    }


# ══════════════════════════════════════════════════════════════════
# GROUP 1 — Headcount & summary
# ══════════════════════════════════════════════════════════════════

@app.get("/tools/total_active_employees", summary="Total karyawan aktif")
def total_active_employees():
    """
    Total, active, and inactive employee counts.
    Answers: "Berapa total karyawan aktif?"
    """
    df       = load_df()
    active   = df[df["employee_data_status"].str.lower() == "active"]
    inactive = df[df["employee_data_status"].str.lower() == "inactive"]
    return {
        "total_employees":    len(df),
        "active_employees":   len(active),
        "inactive_employees": len(inactive),
        "summary": (
            f"Total karyawan: {len(df)} orang. "
            f"Aktif: {len(active)} orang. "
            f"Tidak aktif / resign: {len(inactive)} orang."
        ),
    }


@app.get("/tools/employee_summary", summary="Ringkasan statistik karyawan")
def employee_summary():
    """
    Full workforce snapshot: total, active, employment type breakdown, top departments.
    Answers: "Berikan ringkasan data karyawan", "Berapa karyawan permanent vs kontrak?"
    """
    df      = load_df()
    active  = df[df["employee_data_status"].str.lower() == "active"]
    by_type = active["employment_status"].value_counts().to_dict()
    by_dept = active["department"].value_counts().head(10).to_dict()
    return {
        "total_all":          len(df),
        "total_active":       len(active),
        "total_inactive":     len(df) - len(active),
        "by_employment_type": by_type,
        "top_departments":    by_dept,
        "summary": (
            f"Total karyawan: {len(df)}. "
            f"Aktif: {len(active)}, Tidak aktif: {len(df) - len(active)}. "
            f"Tipe kepegawaian: {', '.join([f'{v} {k}' for k, v in by_type.items()])}."
        ),
    }


@app.get("/tools/headcount_per_outlet", summary="Jumlah karyawan per outlet")
def headcount_per_outlet(
    active_only: bool = Query(True, description="Hanya karyawan aktif"),
):
    """
    Employee count grouped by outlet, sorted descending.
    Answers: "Berapa karyawan per outlet?", "Outlet mana paling banyak karyawan?"
    """
    df = load_df()
    if active_only:
        df = df[df["employee_data_status"].str.lower() == "active"]
    counts = (
        df.groupby("outlet", dropna=False).size()
        .reset_index(name="total").sort_values("total", ascending=False)
    )
    result = [
        {"outlet": r["outlet"] if pd.notna(r["outlet"]) else "(Belum assign)", "total": int(r["total"])}
        for _, r in counts.iterrows()
    ]
    top = result[0] if result else {}
    return {
        "total_outlets": len(result),
        "outlets":       result,
        "summary":       f"Terdapat {len(result)} outlet. Terbanyak: {top.get('outlet')} ({top.get('total')} orang).",
    }


@app.get("/tools/headcount_per_level", summary="Jumlah karyawan per job level")
def headcount_per_level(
    active_only: bool = Query(True, description="Hanya karyawan aktif"),
):
    """
    Employee count grouped by job level, sorted ascending.
    Answers: "Berapa karyawan per level?", "Distribusi level jabatan?"
    """
    df = load_df()
    if active_only:
        df = df[df["employee_data_status"].str.lower() == "active"]
    counts = (
        df.groupby("job_level", dropna=False).size()
        .reset_index(name="total").sort_values("job_level")
    )
    result = [
        {"job_level": int(r["job_level"]) if pd.notna(r["job_level"]) else None, "total": int(r["total"])}
        for _, r in counts.iterrows()
    ]
    return {
        "total_levels": len(result),
        "levels":       result,
        "summary": (
            f"Karyawan tersebar di {len(result)} level jabatan. "
            + " | ".join([f"Level {r['job_level']}: {r['total']} orang" for r in result if r["job_level"] is not None])
        ),
    }


@app.get("/tools/headcount_per_branch", summary="Jumlah karyawan per branch/brand")
def headcount_per_branch(
    active_only: bool = Query(True, description="Hanya karyawan aktif"),
):
    """
    Employee count grouped by branch (legal entity / brand), sorted descending.
    Answers: "Brand mana paling banyak karyawan?", "Berapa karyawan per perusahaan?"
    """
    df = load_df()
    if active_only:
        df = df[df["employee_data_status"].str.lower() == "active"]
    counts = (
        df.groupby("branch", dropna=False).size()
        .reset_index(name="total").sort_values("total", ascending=False)
    )
    result = [
        {"branch": r["branch"] if pd.notna(r["branch"]) else "(Tidak diketahui)", "total": int(r["total"])}
        for _, r in counts.iterrows()
    ]
    top = result[0] if result else {}
    return {
        "total_branches": len(result),
        "branches":       result,
        "summary":        f"Terdapat {len(result)} branch. Terbanyak: {top.get('branch')} ({top.get('total')} orang).",
    }


# ══════════════════════════════════════════════════════════════════
# GROUP 2 — Contracts & lifecycle
# ══════════════════════════════════════════════════════════════════

@app.get("/tools/contracts_expiring", summary="Kontrak habis bulan/tahun tertentu")
def contracts_expiring(
    month:       Optional[int] = Query(None, description="Bulan 1-12. Kosong = bulan ini."),
    year:        Optional[int] = Query(None, description="Tahun, e.g. 2026. Kosong = tahun ini."),
    within_days: Optional[int] = Query(None, description="Habis dalam N hari ke depan. Mengabaikan month/year."),
):
    """
    List employees whose contracts expire in a given month/year or within N days.
    Answers: "Siapa kontrak habis bulan ini?", "Kontrak habis dalam 30 hari?"
    """
    df    = load_df()
    today = date.today()
    contracts = df[
        (df["employment_status"].str.lower() == "contract") &
        (df["end_employment_date"].notna())
    ].copy()

    if within_days is not None:
        cutoff    = pd.Timestamp(today) + pd.Timedelta(days=within_days)
        contracts = contracts[contracts["end_employment_date"] <= cutoff]
        label     = f"dalam {within_days} hari ke depan"
    else:
        tm = month or today.month
        ty = year  or today.year
        contracts = contracts[
            (contracts["end_employment_date"].dt.month == tm) &
            (contracts["end_employment_date"].dt.year  == ty)
        ]
        label = f"bulan {tm}/{ty}"

    result = [
        {
            "employee_id":         r.get("employee_id"),
            "full_name":           r.get("full_name"),
            "department":          r.get("department"),
            "outlet":              r.get("outlet"),
            "job_position":        r.get("job_position"),
            "end_employment_date": r["end_employment_date"].strftime("%Y-%m-%d") if pd.notna(r["end_employment_date"]) else None,
        }
        for _, r in contracts.iterrows()
    ]
    return {
        "period":    label,
        "count":     len(result),
        "employees": result,
        "summary": (
            f"Ada {len(result)} karyawan kontrak yang habis {label}."
            if result else f"Tidak ada karyawan kontrak yang habis {label}."
        ),
    }


@app.get("/tools/contracts_missing_enddate", summary="Kontrak aktif tanpa tanggal akhir")
def contracts_missing_enddate():
    """
    Active contract employees with no end_employment_date — proxy for unsigned/incomplete contract.
    Answers: "Siapa belum tanda tangan kontrak?", "Kontrak mana yang belum lengkap?"
    """
    df      = load_df()
    active  = df[df["employee_data_status"].str.lower() == "active"]
    missing = active[
        (active["employment_status"].str.lower() == "contract") &
        (active["end_employment_date"].isna())
    ]
    result = [
        {
            "employee_id":  r.get("employee_id"),
            "full_name":    r.get("full_name"),
            "department":   r.get("department"),
            "outlet":       r.get("outlet"),
            "job_position": r.get("job_position"),
            "join_date":    r["join_date"].strftime("%Y-%m-%d") if pd.notna(r["join_date"]) else None,
        }
        for _, r in missing.iterrows()
    ]
    return {
        "count":     len(result),
        "employees": result,
        "summary": (
            f"Ada {len(result)} karyawan kontrak aktif yang belum memiliki tanggal akhir kontrak."
            if result else "Semua karyawan kontrak sudah memiliki tanggal akhir kontrak."
        ),
    }


@app.get("/tools/probation_employees", summary="Karyawan masih masa probasi")
def probation_employees(
    probation_months: int = Query(3, description="Durasi probasi dalam bulan (default: 3)"),
):
    """
    Active employees still within their probation period (joined within last N months).
    Answers: "Siapa yang masih probation?", "Berapa karyawan masa percobaan?"
    """
    df     = load_df()
    today  = pd.Timestamp(date.today())
    cutoff = today - pd.DateOffset(months=probation_months)
    active = df[df["employee_data_status"].str.lower() == "active"]
    prob   = active[active["join_date"] >= cutoff].copy()
    prob["days_since_join"] = (today - prob["join_date"]).dt.days

    result = [
        {
            "employee_id":     r.get("employee_id"),
            "full_name":       r.get("full_name"),
            "department":      r.get("department"),
            "outlet":          r.get("outlet"),
            "job_position":    r.get("job_position"),
            "join_date":       r["join_date"].strftime("%Y-%m-%d") if pd.notna(r["join_date"]) else None,
            "days_since_join": int(r["days_since_join"]) if pd.notna(r["days_since_join"]) else None,
        }
        for _, r in prob.sort_values("join_date").iterrows()
    ]
    return {
        "probation_period_months": probation_months,
        "count":                   len(result),
        "employees":               result,
        "summary":                 f"Ada {len(result)} karyawan aktif masih dalam masa probasi ({probation_months} bulan terakhir).",
    }


@app.get("/tools/new_hires", summary="Karyawan baru dalam periode tertentu")
def new_hires(
    month:       Optional[int] = Query(None, description="Bulan bergabung. Kosong = bulan ini."),
    year:        Optional[int] = Query(None, description="Tahun bergabung. Kosong = tahun ini."),
    within_days: Optional[int] = Query(None, description="Bergabung dalam N hari terakhir. Mengabaikan month/year."),
):
    """
    Recently hired employees.
    Answers: "Siapa karyawan baru bulan ini?", "Siapa join 30 hari terakhir?"
    """
    df    = load_df()
    today = pd.Timestamp(date.today())

    if within_days is not None:
        hires = df[df["join_date"] >= today - pd.Timedelta(days=within_days)]
        label = f"dalam {within_days} hari terakhir"
    else:
        tm    = month or today.month
        ty    = year  or today.year
        hires = df[(df["join_date"].dt.month == tm) & (df["join_date"].dt.year == ty)]
        label = f"bulan {tm}/{ty}"

    result = [
        {
            "employee_id":       r.get("employee_id"),
            "full_name":         r.get("full_name"),
            "department":        r.get("department"),
            "job_position":      r.get("job_position"),
            "employment_status": r.get("employment_status"),
            "join_date":         r["join_date"].strftime("%Y-%m-%d") if pd.notna(r["join_date"]) else None,
        }
        for _, r in hires.iterrows()
    ]
    return {
        "period":    label,
        "count":     len(result),
        "employees": result,
        "summary":   f"Ada {len(result)} karyawan baru yang bergabung {label}.",
    }


# ══════════════════════════════════════════════════════════════════
# GROUP 3 — Resign & turnover
# ══════════════════════════════════════════════════════════════════

@app.get("/tools/resigned_employees", summary="Daftar karyawan yang resign")
def resigned_employees(
    month: Optional[int] = Query(None, description="Filter bulan resign (1-12)"),
    year:  Optional[int] = Query(None, description="Filter tahun resign"),
):
    """
    Inactive (resigned) employees, optionally filtered by month/year.
    Answers: "Siapa yang sudah resign?", "Berapa yang resign bulan ini?"
    """
    df      = load_df()
    resigned = df[df["employee_data_status"].str.lower() == "inactive"].copy()
    if month:
        resigned = resigned[resigned["resign_date"].dt.month == month]
    if year:
        resigned = resigned[resigned["resign_date"].dt.year  == year]

    result = [
        {
            "employee_id":  r.get("employee_id"),
            "full_name":    r.get("full_name"),
            "department":   r.get("department"),
            "job_position": r.get("job_position"),
            "outlet":       r.get("outlet"),
            "resign_date":  r["resign_date"].strftime("%Y-%m-%d") if pd.notna(r["resign_date"]) else None,
        }
        for _, r in resigned.iterrows()
    ]
    return {
        "count":     len(result),
        "employees": result,
        "summary":   f"Total {len(result)} karyawan tidak aktif / sudah resign.",
    }


@app.get("/tools/resign_by_position", summary="Posisi paling banyak resign")
def resign_by_position(
    top_n: int           = Query(10, description="Tampilkan N posisi teratas"),
    year:  Optional[int] = Query(None, description="Filter tahun resign"),
):
    """
    Job positions ranked by resign count.
    Answers: "Posisi apa paling banyak resign?", "Jabatan mana paling tinggi turnovernya?"
    """
    df      = load_df()
    resigned = df[df["employee_data_status"].str.lower() == "inactive"].copy()
    if year:
        resigned = resigned[resigned["resign_date"].dt.year == year]

    counts = (
        resigned.groupby("job_position", dropna=False).size()
        .reset_index(name="resign_count")
        .sort_values("resign_count", ascending=False)
        .head(top_n)
    )
    result = [
        {
            "rank":         rank,
            "job_position": r["job_position"] if pd.notna(r["job_position"]) else "(Tidak ada jabatan)",
            "resign_count": int(r["resign_count"]),
        }
        for rank, (_, r) in enumerate(counts.iterrows(), 1)
    ]
    top = result[0] if result else {}
    return {
        "top_n":     top_n,
        "positions": result,
        "summary":   f"Posisi resign terbanyak: {top.get('job_position')} ({top.get('resign_count')} orang).",
    }


@app.get("/tools/turnover_per_outlet", summary="Tingkat turnover per outlet")
def turnover_per_outlet(
    year: Optional[int] = Query(None, description="Filter tahun resign. Kosong = semua tahun."),
):
    """
    Resign count and turnover rate grouped by outlet, sorted by resign count descending.
    Answers: "Outlet mana turnover tinggi?", "Di mana paling banyak resign?"
    """
    df      = load_df()
    resigned = df[df["employee_data_status"].str.lower() == "inactive"].copy()
    if year:
        resigned = resigned[resigned["resign_date"].dt.year == year]

    resign_counts = resigned.groupby("outlet", dropna=False).size().reset_index(name="resign_count")
    total_counts  = df.groupby("outlet", dropna=False).size().reset_index(name="total_ever")

    merged = total_counts.merge(resign_counts, on="outlet", how="left").fillna({"resign_count": 0})
    merged["resign_count"] = merged["resign_count"].astype(int)
    merged["turnover_pct"] = (merged["resign_count"] / merged["total_ever"] * 100).round(1)
    merged = merged.sort_values("resign_count", ascending=False)

    result = [
        {
            "outlet":          r["outlet"] if pd.notna(r["outlet"]) else "(Belum assign)",
            "total_employees": int(r["total_ever"]),
            "resign_count":    int(r["resign_count"]),
            "turnover_pct":    float(r["turnover_pct"]),
        }
        for _, r in merged.iterrows()
    ]
    top          = result[0] if result else {}
    period_label = f"tahun {year}" if year else "semua periode"
    return {
        "period":  period_label,
        "outlets": result,
        "summary": (
            f"Outlet turnover tertinggi ({period_label}): "
            f"{top.get('outlet')} — {top.get('resign_count')} resign "
            f"({top.get('turnover_pct')}%)."
        ),
    }


# ══════════════════════════════════════════════════════════════════
# GROUP 4 — Search & roster
# ══════════════════════════════════════════════════════════════════

@app.get("/tools/search_employee", summary="Cari karyawan berdasarkan nama")
def search_employee(
    name: str = Query(..., description="Nama karyawan, partial match"),
):
    """
    Case-insensitive partial-match employee search by name.
    Answers: "Cari data karyawan Andi", "Profil karyawan bernama Sari"
    """
    df       = load_df()
    filtered = df[df["full_name"].str.contains(name, case=False, na=False)]

    result = [
        {
            "employee_id":          r.get("employee_id"),
            "full_name":            r.get("full_name"),
            "department":           r.get("department"),
            "outlet":               r.get("outlet"),
            "job_position":         r.get("job_position"),
            "job_level":            int(r["job_level"]) if pd.notna(r.get("job_level")) else None,
            "employment_status":    r.get("employment_status"),
            "employee_data_status": r.get("employee_data_status"),
            "join_date":            r["join_date"].strftime("%Y-%m-%d")            if pd.notna(r["join_date"])            else None,
            "end_employment_date":  r["end_employment_date"].strftime("%Y-%m-%d")  if pd.notna(r["end_employment_date"])  else None,
            "resign_date":          r["resign_date"].strftime("%Y-%m-%d")          if pd.notna(r["resign_date"])          else None,
        }
        for _, r in filtered.iterrows()
    ]
    return {
        "query":     name,
        "count":     len(result),
        "employees": result,
        "summary":   f"Ditemukan {len(result)} karyawan dengan nama mengandung '{name}'.",
    }


@app.get("/tools/list_by_department", summary="Daftar karyawan per department")
def list_by_department(
    department:  str  = Query(..., description="Nama department, partial match"),
    active_only: bool = Query(True,  description="Hanya karyawan aktif"),
):
    """
    List employees in a department (case-insensitive partial match).
    Answers: "Siapa saja karyawan di department Operations?"
    """
    df = load_df()
    if active_only:
        df = df[df["employee_data_status"].str.lower() == "active"]
    filtered = df[df["department"].str.contains(department, case=False, na=False)]

    result = [
        {
            "employee_id":       r.get("employee_id"),
            "full_name":         r.get("full_name"),
            "job_position":      r.get("job_position"),
            "job_level":         int(r["job_level"]) if pd.notna(r.get("job_level")) else None,
            "outlet":            r.get("outlet"),
            "employment_status": r.get("employment_status"),
            "join_date":         r["join_date"].strftime("%Y-%m-%d") if pd.notna(r["join_date"]) else None,
        }
        for _, r in filtered.iterrows()
    ]
    return {
        "department_query": department,
        "count":            len(result),
        "employees":        result,
        "summary":          f"Ditemukan {len(result)} karyawan di department '{department}'.",
    }


@app.get("/tools/list_by_outlet", summary="Daftar karyawan per outlet")
def list_by_outlet(
    outlet:      str  = Query(..., description="Nama outlet, partial match"),
    active_only: bool = Query(True,  description="Hanya karyawan aktif"),
):
    """
    List employees at a specific outlet (case-insensitive partial match).
    Answers: "Siapa saja yang kerja di Gandaria?"
    """
    df = load_df()
    if active_only:
        df = df[df["employee_data_status"].str.lower() == "active"]
    filtered = df[df["outlet"].str.contains(outlet, case=False, na=False)]

    result = [
        {
            "employee_id":       r.get("employee_id"),
            "full_name":         r.get("full_name"),
            "department":        r.get("department"),
            "job_position":      r.get("job_position"),
            "employment_status": r.get("employment_status"),
        }
        for _, r in filtered.iterrows()
    ]
    return {
        "outlet_query": outlet,
        "count":        len(result),
        "employees":    result,
        "summary":      f"Ditemukan {len(result)} karyawan di outlet '{outlet}'.",
    }


# ══════════════════════════════════════════════════════════════════
# GROUP 5 — Assignment gaps
# ══════════════════════════════════════════════════════════════════

@app.get("/tools/unassigned_employees", summary="Karyawan belum assign outlet/jabatan/SPV")
def unassigned_employees(
    check:       str  = Query("outlet", description="Yang dicek: 'outlet' | 'job_position' | 'supervisor'"),
    active_only: bool = Query(True, description="Hanya karyawan aktif"),
):
    """
    Find employees missing an outlet, job position, or whose outlet has no supervisor.
    Answers: "Siapa belum assign outlet?", "Siapa belum assign jabatan?", "Siapa belum assign SPV?"
    """
    df = load_df()
    if active_only:
        df = df[df["employee_data_status"].str.lower() == "active"]

    if check == "outlet":
        unassigned = df[df["outlet"].isna() | (df["outlet"].str.strip() == "")]
        label = "outlet"
    elif check == "job_position":
        unassigned = df[df["job_position"].isna() | (df["job_position"].str.strip() == "")]
        label = "jabatan"
    elif check == "supervisor":
        has_leader = df[df["job_position"].str.contains(SPV_PATTERN, case=False, na=False)]["outlet"].dropna().unique()
        unassigned = df[~df["outlet"].isin(has_leader) & df["outlet"].notna()]
        label = "SPV / leader"
    else:
        return {"error": f"Nilai check='{check}' tidak dikenal. Gunakan: outlet, job_position, supervisor"}

    result = [
        {
            "employee_id":  r.get("employee_id"),
            "full_name":    r.get("full_name"),
            "outlet":       r.get("outlet"),
            "department":   r.get("department"),
            "job_position": r.get("job_position"),
        }
        for _, r in unassigned.iterrows()
    ]
    return {
        "check":     check,
        "count":     len(result),
        "employees": result,
        "summary": (
            f"Ada {len(result)} karyawan yang belum memiliki {label}."
            if result else f"Semua karyawan sudah memiliki {label}."
        ),
    }


@app.get("/tools/outlets_without_leader", summary="Outlet belum ada leader/manager")
def outlets_without_leader():
    """
    Outlets where no active employee holds a leadership/manager position.
    Answers: "Outlet mana belum ada leader?", "Outlet yang tidak punya manager?"
    """
    df     = load_df()
    active = df[df["employee_data_status"].str.lower() == "active"]

    all_outlets      = active["outlet"].dropna().unique()
    outlets_w_leader = active[
        active["job_position"].str.contains(SPV_PATTERN, case=False, na=False)
    ]["outlet"].dropna().unique()

    result = [
        {
            "outlet":      outlet,
            "total_staff": int(len(active[active["outlet"] == outlet])),
            "positions":   active[active["outlet"] == outlet]["job_position"].dropna().tolist(),
        }
        for outlet in sorted(o for o in all_outlets if o not in outlets_w_leader)
    ]
    return {
        "count":   len(result),
        "outlets": result,
        "summary": (
            f"Ada {len(result)} outlet yang belum memiliki posisi leader/manager."
            if result else "Semua outlet sudah memiliki leader."
        ),
    }