"""
HR Employee MCP Server — FastAPI v2.0.0
MCP-compatible API server for Dify tool integration.
17 tools covering headcount, contracts, turnover, search, and assignment gaps.
"""

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import pandas as pd
from datetime import date
from typing import Optional
import os

# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="HR Employee MCP Server",
    version="2.0.0",
    # Disable FastAPI's auto /openapi.json — we serve our own below
    openapi_url=None,
    docs_url=None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Hand-crafted OpenAPI 3.0.3 schema (Dify-compatible) ──────────────────────
# FastAPI defaults to 3.1.0 which Dify cannot parse.
# We serve a fully static, manually written 3.0.3 schema instead.

OPENAPI_SCHEMA = {
  "openapi": "3.0.3",
  "info": {
    "title": "HR Employee MCP Server",
    "description": "17 HR tools for Dify: headcount, contracts, turnover, probation, search, and assignment gaps.",
    "version": "2.0.0"
  },
  "servers": [{"url": "https://hr-mcp-server.vercel.app"}],
  "paths": {
    "/tools/total_active_employees": {"get": {
      "operationId": "total_active_employees",
      "summary": "Total karyawan aktif",
      "description": "Mengembalikan total, aktif, dan tidak aktif karyawan. Jawab: Berapa total karyawan aktif?",
      "parameters": [],
      "responses": {"200": {"description": "OK", "content": {"application/json": {"schema": {"type": "object"}}}}}
    }},
    "/tools/employee_summary": {"get": {
      "operationId": "employee_summary",
      "summary": "Ringkasan statistik karyawan",
      "description": "Snapshot lengkap workforce: total, aktif, tipe kontrak, top department. Jawab: Ringkasan data karyawan, Berapa permanent vs kontrak?",
      "parameters": [],
      "responses": {"200": {"description": "OK", "content": {"application/json": {"schema": {"type": "object"}}}}}
    }},
    "/tools/headcount_per_outlet": {"get": {
      "operationId": "headcount_per_outlet",
      "summary": "Jumlah karyawan per outlet",
      "description": "Jumlah karyawan dikelompokkan per outlet. Jawab: Berapa karyawan per outlet?",
      "parameters": [
        {"name": "active_only", "in": "query", "required": False, "schema": {"type": "boolean", "default": True}, "description": "Hanya karyawan aktif"}
      ],
      "responses": {"200": {"description": "OK", "content": {"application/json": {"schema": {"type": "object"}}}}}
    }},
    "/tools/headcount_per_level": {"get": {
      "operationId": "headcount_per_level",
      "summary": "Jumlah karyawan per job level",
      "description": "Distribusi karyawan per level jabatan. Jawab: Berapa karyawan per level?",
      "parameters": [
        {"name": "active_only", "in": "query", "required": False, "schema": {"type": "boolean", "default": True}, "description": "Hanya karyawan aktif"}
      ],
      "responses": {"200": {"description": "OK", "content": {"application/json": {"schema": {"type": "object"}}}}}
    }},
    "/tools/headcount_per_branch": {"get": {
      "operationId": "headcount_per_branch",
      "summary": "Jumlah karyawan per branch/brand",
      "description": "Jumlah karyawan per perusahaan/brand. Jawab: Brand mana paling banyak karyawan?",
      "parameters": [
        {"name": "active_only", "in": "query", "required": False, "schema": {"type": "boolean", "default": True}, "description": "Hanya karyawan aktif"}
      ],
      "responses": {"200": {"description": "OK", "content": {"application/json": {"schema": {"type": "object"}}}}}
    }},
    "/tools/contracts_expiring": {"get": {
      "operationId": "contracts_expiring",
      "summary": "Kontrak habis bulan/tahun tertentu",
      "description": "Karyawan kontrak yang habis pada bulan/tahun atau dalam N hari. Jawab: Siapa kontrak habis bulan ini?, Kontrak habis dalam 30 hari?",
      "parameters": [
        {"name": "month",       "in": "query", "required": False, "schema": {"type": "integer", "nullable": True}, "description": "Bulan 1-12. Kosong = bulan ini."},
        {"name": "year",        "in": "query", "required": False, "schema": {"type": "integer", "nullable": True}, "description": "Tahun, contoh 2026. Kosong = tahun ini."},
        {"name": "within_days", "in": "query", "required": False, "schema": {"type": "integer", "nullable": True}, "description": "Habis dalam N hari ke depan. Mengabaikan month/year."}
      ],
      "responses": {"200": {"description": "OK", "content": {"application/json": {"schema": {"type": "object"}}}}}
    }},
    "/tools/contracts_missing_enddate": {"get": {
      "operationId": "contracts_missing_enddate",
      "summary": "Kontrak aktif tanpa tanggal akhir",
      "description": "Karyawan kontrak aktif tanpa tanggal akhir kontrak (proxy belum tanda tangan). Jawab: Siapa belum tanda tangan kontrak?",
      "parameters": [],
      "responses": {"200": {"description": "OK", "content": {"application/json": {"schema": {"type": "object"}}}}}
    }},
    "/tools/probation_employees": {"get": {
      "operationId": "probation_employees",
      "summary": "Karyawan masih masa probasi",
      "description": "Karyawan aktif yang bergabung dalam N bulan terakhir. Jawab: Siapa masih probation?",
      "parameters": [
        {"name": "probation_months", "in": "query", "required": False, "schema": {"type": "integer", "default": 3}, "description": "Durasi probasi dalam bulan (default 3)"}
      ],
      "responses": {"200": {"description": "OK", "content": {"application/json": {"schema": {"type": "object"}}}}}
    }},
    "/tools/new_hires": {"get": {
      "operationId": "new_hires",
      "summary": "Karyawan baru dalam periode tertentu",
      "description": "Karyawan yang baru bergabung. Jawab: Siapa karyawan baru bulan ini?",
      "parameters": [
        {"name": "month",       "in": "query", "required": False, "schema": {"type": "integer", "nullable": True}, "description": "Bulan bergabung. Kosong = bulan ini."},
        {"name": "year",        "in": "query", "required": False, "schema": {"type": "integer", "nullable": True}, "description": "Tahun bergabung. Kosong = tahun ini."},
        {"name": "within_days", "in": "query", "required": False, "schema": {"type": "integer", "nullable": True}, "description": "Bergabung dalam N hari terakhir."}
      ],
      "responses": {"200": {"description": "OK", "content": {"application/json": {"schema": {"type": "object"}}}}}
    }},
    "/tools/resigned_employees": {"get": {
      "operationId": "resigned_employees",
      "summary": "Daftar karyawan yang resign",
      "description": "Karyawan tidak aktif atau sudah resign. Jawab: Siapa yang sudah resign?, Berapa yang resign bulan ini?",
      "parameters": [
        {"name": "month", "in": "query", "required": False, "schema": {"type": "integer", "nullable": True}, "description": "Filter bulan resign (1-12)"},
        {"name": "year",  "in": "query", "required": False, "schema": {"type": "integer", "nullable": True}, "description": "Filter tahun resign"}
      ],
      "responses": {"200": {"description": "OK", "content": {"application/json": {"schema": {"type": "object"}}}}}
    }},
    "/tools/resign_by_position": {"get": {
      "operationId": "resign_by_position",
      "summary": "Posisi paling banyak resign",
      "description": "Ranking jabatan berdasarkan jumlah resign. Jawab: Posisi apa paling banyak resign?",
      "parameters": [
        {"name": "top_n", "in": "query", "required": False, "schema": {"type": "integer", "default": 10}, "description": "Tampilkan N posisi teratas"},
        {"name": "year",  "in": "query", "required": False, "schema": {"type": "integer", "nullable": True}, "description": "Filter tahun resign"}
      ],
      "responses": {"200": {"description": "OK", "content": {"application/json": {"schema": {"type": "object"}}}}}
    }},
    "/tools/turnover_per_outlet": {"get": {
      "operationId": "turnover_per_outlet",
      "summary": "Tingkat turnover per outlet",
      "description": "Jumlah resign dan persentase turnover per outlet. Jawab: Outlet mana turnover tinggi?",
      "parameters": [
        {"name": "year", "in": "query", "required": False, "schema": {"type": "integer", "nullable": True}, "description": "Filter tahun resign. Kosong = semua tahun."}
      ],
      "responses": {"200": {"description": "OK", "content": {"application/json": {"schema": {"type": "object"}}}}}
    }},
    "/tools/search_employee": {"get": {
      "operationId": "search_employee",
      "summary": "Cari karyawan berdasarkan nama",
      "description": "Cari karyawan dengan nama partial match. Jawab: Cari data karyawan Andi",
      "parameters": [
        {"name": "name", "in": "query", "required": True, "schema": {"type": "string"}, "description": "Nama karyawan, partial match"}
      ],
      "responses": {"200": {"description": "OK", "content": {"application/json": {"schema": {"type": "object"}}}}}
    }},
    "/tools/list_by_department": {"get": {
      "operationId": "list_by_department",
      "summary": "Daftar karyawan per department",
      "description": "Daftar karyawan berdasarkan department partial match. Jawab: Siapa karyawan di department Operations?",
      "parameters": [
        {"name": "department", "in": "query", "required": True,  "schema": {"type": "string"}, "description": "Nama department, partial match"},
        {"name": "active_only","in": "query", "required": False, "schema": {"type": "boolean", "default": True}, "description": "Hanya karyawan aktif"}
      ],
      "responses": {"200": {"description": "OK", "content": {"application/json": {"schema": {"type": "object"}}}}}
    }},
    "/tools/list_by_outlet": {"get": {
      "operationId": "list_by_outlet",
      "summary": "Daftar karyawan per outlet",
      "description": "Daftar karyawan berdasarkan outlet partial match. Jawab: Siapa yang kerja di Gandaria?",
      "parameters": [
        {"name": "outlet",     "in": "query", "required": True,  "schema": {"type": "string"}, "description": "Nama outlet, partial match"},
        {"name": "active_only","in": "query", "required": False, "schema": {"type": "boolean", "default": True}, "description": "Hanya karyawan aktif"}
      ],
      "responses": {"200": {"description": "OK", "content": {"application/json": {"schema": {"type": "object"}}}}}
    }},
    "/tools/unassigned_employees": {"get": {
      "operationId": "unassigned_employees",
      "summary": "Karyawan belum assign outlet/jabatan/SPV",
      "description": "Karyawan tanpa outlet, tanpa jabatan, atau outlet tanpa SPV. Jawab: Siapa belum assign outlet?, Siapa belum assign jabatan?, Siapa belum assign SPV?",
      "parameters": [
        {"name": "check",      "in": "query", "required": False, "schema": {"type": "string",  "default": "outlet"}, "description": "Yang dicek: outlet atau job_position atau supervisor"},
        {"name": "active_only","in": "query", "required": False, "schema": {"type": "boolean", "default": True}, "description": "Hanya karyawan aktif"}
      ],
      "responses": {"200": {"description": "OK", "content": {"application/json": {"schema": {"type": "object"}}}}}
    }},
    "/tools/outlets_without_leader": {"get": {
      "operationId": "outlets_without_leader",
      "summary": "Outlet belum ada leader/manager",
      "description": "Outlet tanpa karyawan di posisi leader atau manager. Jawab: Outlet mana belum ada leader?",
      "parameters": [],
      "responses": {"200": {"description": "OK", "content": {"application/json": {"schema": {"type": "object"}}}}}
    }},
    "/tools/list_all_employees": {"get": {
      "operationId": "list_all_employees",
      "summary": "Daftar semua karyawan beserta detail lengkap",
      "description": "Return semua karyawan aktif dengan detail lengkap tanpa filter wajib. Jawab: Siapa saja karyawan aktif? Tampilkan semua karyawan. Detailkan karyawan aktif. List semua karyawan permanent.",
      "parameters": [
        {"name": "active_only",        "in": "query", "required": False, "schema": {"type": "boolean", "default": True},  "description": "True = hanya aktif, False = semua termasuk resign"},
        {"name": "employment_status",  "in": "query", "required": False, "schema": {"type": "string",  "nullable": True}, "description": "Filter: Permanent atau Contract"}
      ],
      "responses": {"200": {"description": "OK", "content": {"application/json": {"schema": {"type": "object"}}}}}
    }},
    "/tools/list_active_by_status": {"get": {
      "operationId": "list_active_by_status",
      "summary": "Karyawan aktif dikelompokkan per status kepegawaian",
      "description": "Karyawan aktif dikelompokkan Permanent vs Contract beserta nama lengkap. Jawab: Berapa permanent vs kontrak dan siapa saja? Detail karyawan permanent. Detail karyawan kontrak aktif.",
      "parameters": [],
      "responses": {"200": {"description": "OK", "content": {"application/json": {"schema": {"type": "object"}}}}}
    }},
    "/tools/list_employees_by_join_year": {"get": {
      "operationId": "list_employees_by_join_year",
      "summary": "Karyawan berdasarkan tahun bergabung",
      "description": "Daftar karyawan yang bergabung pada tahun tertentu. Jawab: Berapa karyawan join tahun 2003? Siapa yang masuk tahun X? Karyawan yang bergabung tahun X.",
      "parameters": [
        {"name": "year",        "in": "query", "required": True,  "schema": {"type": "integer"}, "description": "Tahun bergabung, contoh: 2003"},
        {"name": "active_only", "in": "query", "required": False, "schema": {"type": "boolean", "default": False}, "description": "True = hanya aktif, False = semua termasuk resign"}
      ],
      "responses": {"200": {"description": "OK", "content": {"application/json": {"schema": {"type": "object"}}}}}
    }},
    "/tools/training_wajib_not_completed": {"get": {
      "operationId": "training_wajib_not_completed",
      "summary": "Karyawan belum selesai training wajib",
      "description": "Daftar karyawan yang status_training_wajib masih 'not yet'. Jawab: Siapa belum training wajib? Siapa yang belum menyelesaikan training mandatory?",
      "parameters": [
        {"name": "outlet_name", "in": "query", "required": False, "schema": {"type": "string",  "nullable": True}, "description": "Filter nama outlet (partial match)"},
        {"name": "brand_name",  "in": "query", "required": False, "schema": {"type": "string",  "nullable": True}, "description": "Filter nama brand (partial match)"},
        {"name": "limit",       "in": "query", "required": False, "schema": {"type": "integer", "default": 100},   "description": "Maks jumlah baris dikembalikan"}
      ],
      "responses": {"200": {"description": "OK", "content": {"application/json": {"schema": {"type": "object"}}}}}
    }},
    "/tools/training_completion_by_outlet": {"get": {
      "operationId": "training_completion_by_outlet",
      "summary": "Tingkat penyelesaian training wajib per outlet",
      "description": "Outlet diurutkan dari tingkat penyelesaian training wajib terendah. Jawab: Outlet mana training rendah? Outlet mana yang paling sedikit menyelesaikan training?",
      "parameters": [
        {"name": "top_n",      "in": "query", "required": False, "schema": {"type": "integer", "default": 10},   "description": "Tampilkan N outlet terendah"},
        {"name": "brand_name", "in": "query", "required": False, "schema": {"type": "string",  "nullable": True}, "description": "Filter nama brand (partial match)"}
      ],
      "responses": {"200": {"description": "OK", "content": {"application/json": {"schema": {"type": "object"}}}}}
    }},
    "/tools/certification_not_completed": {"get": {
      "operationId": "certification_not_completed",
      "summary": "Karyawan belum selesai sertifikasi",
      "description": "Karyawan yang modul-nya adalah sertifikasi/assessment tapi belum selesai training wajib. Jawab: Siapa belum sertifikasi? Siapa yang belum lulus assessment?",
      "parameters": [
        {"name": "outlet_name", "in": "query", "required": False, "schema": {"type": "string", "nullable": True}, "description": "Filter nama outlet (partial match)"},
        {"name": "limit",       "in": "query", "required": False, "schema": {"type": "integer", "default": 100},  "description": "Maks jumlah baris dikembalikan"}
      ],
      "responses": {"200": {"description": "OK", "content": {"application/json": {"schema": {"type": "object"}}}}}
    }},
    "/tools/training_not_started": {"get": {
      "operationId": "training_not_started",
      "summary": "Karyawan belum mulai training sama sekali",
      "description": "Karyawan yang sudah bekerja tapi status training wajib masih 'not yet'. Jawab: Siapa belum training tapi sudah kerja? Siapa yang belum pernah training?",
      "parameters": [
        {"name": "outlet_name", "in": "query", "required": False, "schema": {"type": "string",  "nullable": True}, "description": "Filter nama outlet (partial match)"},
        {"name": "limit",       "in": "query", "required": False, "schema": {"type": "integer", "default": 100},   "description": "Maks jumlah baris dikembalikan"}
      ],
      "responses": {"200": {"description": "OK", "content": {"application/json": {"schema": {"type": "object"}}}}}
    }},
    "/tools/training_low_score": {"get": {
      "operationId": "training_low_score",
      "summary": "Karyawan dengan nilai post-test rendah",
      "description": "Karyawan yang sudah selesai training tapi post_test_grade di bawah ambang batas. Jawab: Siapa training score rendah? Siapa yang nilai ujian training-nya rendah?",
      "parameters": [
        {"name": "threshold",   "in": "query", "required": False, "schema": {"type": "integer", "default": 70},   "description": "Batas nilai rendah (default 70)"},
        {"name": "outlet_name", "in": "query", "required": False, "schema": {"type": "string",  "nullable": True}, "description": "Filter nama outlet (partial match)"},
        {"name": "limit",       "in": "query", "required": False, "schema": {"type": "integer", "default": 100},   "description": "Maks jumlah baris dikembalikan"}
      ],
      "responses": {"200": {"description": "OK", "content": {"application/json": {"schema": {"type": "object"}}}}}
    }},
    "/tools/training_most_failed": {"get": {
      "operationId": "training_most_failed",
      "summary": "Modul training paling sering tidak diselesaikan",
      "description": "Ranking modul training berdasarkan jumlah karyawan yang belum menyelesaikannya. Jawab: Training apa paling sering gagal? Modul mana yang paling banyak tidak selesai?",
      "parameters": [
        {"name": "top_n", "in": "query", "required": False, "schema": {"type": "integer", "default": 10}, "description": "Tampilkan N modul teratas"}
      ],
      "responses": {"200": {"description": "OK", "content": {"application/json": {"schema": {"type": "object"}}}}}
    }},
    "/tools/role_certification_not_completed": {"get": {
      "operationId": "role_certification_not_completed",
      "summary": "Karyawan belum sertifikasi sesuai role",
      "description": "Karyawan yang modul-nya adalah sertifikasi role/jabatan spesifik (leadership, wine assessment) tapi belum selesai. Jawab: Siapa belum sertifikasi role? Siapa yang belum dapat sertifikasi jabatan?",
      "parameters": [
        {"name": "outlet_name", "in": "query", "required": False, "schema": {"type": "string", "nullable": True}, "description": "Filter nama outlet (partial match)"},
        {"name": "limit",       "in": "query", "required": False, "schema": {"type": "integer", "default": 100},  "description": "Maks jumlah baris dikembalikan"}
      ],
      "responses": {"200": {"description": "OK", "content": {"application/json": {"schema": {"type": "object"}}}}}
    }},
    "/tools/training_not_started_3months": {"get": {
      "operationId": "training_not_started_3months",
      "summary": "Karyawan belum training padahal sudah N bulan kerja",
      "description": "Karyawan yang bergabung lebih dari N bulan lalu tapi belum menyelesaikan training wajib. Jawab: Siapa belum training tapi sudah 3 bulan kerja? Karyawan lama yang belum training?",
      "parameters": [
        {"name": "months",      "in": "query", "required": False, "schema": {"type": "integer", "default": 3},    "description": "Minimal masa kerja dalam bulan (default 3)"},
        {"name": "outlet_name", "in": "query", "required": False, "schema": {"type": "string",  "nullable": True}, "description": "Filter nama outlet (partial match)"},
        {"name": "limit",       "in": "query", "required": False, "schema": {"type": "integer", "default": 100},   "description": "Maks jumlah baris dikembalikan"}
      ],
      "responses": {"200": {"description": "OK", "content": {"application/json": {"schema": {"type": "object"}}}}}
    }},
    "/tools/leader_training_not_completed": {"get": {
      "operationId": "leader_training_not_completed",
      "summary": "Leader/manager yang belum selesai training kepemimpinan",
      "description": "Karyawan yang ditugaskan modul kepemimpinan (leadership) tapi belum menyelesaikannya. Jawab: Siapa leader belum training leader? Siapa manajer yang belum training kepemimpinan?",
      "parameters": [
        {"name": "outlet_name", "in": "query", "required": False, "schema": {"type": "string", "nullable": True}, "description": "Filter nama outlet (partial match)"},
        {"name": "limit",       "in": "query", "required": False, "schema": {"type": "integer", "default": 100},  "description": "Maks jumlah baris dikembalikan"}
      ],
      "responses": {"200": {"description": "OK", "content": {"application/json": {"schema": {"type": "object"}}}}}
    }},
    "/tools/safety_training_not_completed": {"get": {
      "operationId": "safety_training_not_completed",
      "summary": "Karyawan belum selesai training safety",
      "description": "Karyawan yang ditugaskan modul keselamatan kerja (WSE, Food Safety) tapi belum menyelesaikannya. Jawab: Siapa belum training safety? Siapa belum training K3?",
      "parameters": [
        {"name": "outlet_name", "in": "query", "required": False, "schema": {"type": "string", "nullable": True}, "description": "Filter nama outlet (partial match)"},
        {"name": "limit",       "in": "query", "required": False, "schema": {"type": "integer", "default": 100},  "description": "Maks jumlah baris dikembalikan"}
      ],
      "responses": {"200": {"description": "OK", "content": {"application/json": {"schema": {"type": "object"}}}}}
    }},
    "/tools/sop_training_not_completed": {"get": {
      "operationId": "sop_training_not_completed",
      "summary": "Karyawan belum selesai training SOP",
      "description": "Karyawan yang ditugaskan modul SOP/prosedur operasional tapi belum menyelesaikannya. Jawab: Siapa belum training SOP? Siapa belum training prosedur outlet?",
      "parameters": [
        {"name": "outlet_name", "in": "query", "required": False, "schema": {"type": "string", "nullable": True}, "description": "Filter nama outlet (partial match)"},
        {"name": "limit",       "in": "query", "required": False, "schema": {"type": "integer", "default": 100},  "description": "Maks jumlah baris dikembalikan"}
      ],
      "responses": {"200": {"description": "OK", "content": {"application/json": {"schema": {"type": "object"}}}}}
    }}
  }
}


@app.get("/openapi.json", include_in_schema=False)
def openapi_schema():
    """Serve hand-crafted OpenAPI 3.0.3 schema — always Dify-compatible."""
    return JSONResponse(content=OPENAPI_SCHEMA)


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

TRAINING_DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "all_employee_training_data.csv")

def load_training_df() -> pd.DataFrame:
    """Load and normalise training CSV on every request."""
    df = pd.read_csv(TRAINING_DATA_PATH, dtype=str)
    df.columns = [c.strip().lower() for c in df.columns]
    df["join_date"] = pd.to_datetime(df["join_date"], errors="coerce")
    df["pre_test_grade"]  = pd.to_numeric(df["pre_test_grade"],  errors="coerce")
    df["post_test_grade"] = pd.to_numeric(df["post_test_grade"], errors="coerce")
    df["status_training_wajib"]    = df["status_training_wajib"].str.strip().str.lower()
    df["status_training_optional"] = df["status_training_optional"].str.strip().str.lower()
    return df

# Keyword patterns for training module categorisation
SAFETY_MODULE_PATTERN   = r"safety|Safety|WSE|wse|Work-Safe|K3|HACCP|FSH|Food.Safety"
SOP_MODULE_PATTERN      = r"SOP|sop|Procedure|procedure|Sequence-of-Service|Closing-Outlet|Opening-Outlet"
LEADER_MODULE_PATTERN   = r"Leadership|leadership|Conscious-Leadership|MMDP|Way-of-Semaja-Leadership"
CERT_MODULE_PATTERN     = r"Assesment|Assessment|assesment|assessment|Sertif|sertif|Certif|certif"
ROLE_CERT_MODULE_PATTERN = r"Assesment|Assessment|assesment|assessment|Wine|SJPH|Halal|GMP|Good-Manufacturing"

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
            {"name": "list_all_employees",        "endpoint": "/tools/list_all_employees",        "method": "GET", "description": "Daftar semua karyawan aktif beserta detail lengkap — untuk pertanyaan 'siapa saja karyawan aktif?' tanpa filter spesifik"},
            {"name": "list_active_by_status",        "endpoint": "/tools/list_active_by_status",        "method": "GET", "description": "Karyawan aktif dikelompokkan per status kepegawaian (Permanent vs Contract) beserta nama lengkap"},
            {"name": "list_employees_by_join_year", "endpoint": "/tools/list_employees_by_join_year", "method": "GET", "description": "Daftar karyawan yang bergabung pada tahun tertentu. Jawab: Berapa karyawan join tahun X? Siapa yang masuk tahun X?"},
            # Group 6 — Training
            {"name": "training_wajib_not_completed",    "endpoint": "/tools/training_wajib_not_completed",    "method": "GET", "description": "Karyawan yang belum menyelesaikan training wajib (mandatory)"},
            {"name": "training_completion_by_outlet",   "endpoint": "/tools/training_completion_by_outlet",   "method": "GET", "description": "Outlet dengan tingkat penyelesaian training wajib terendah"},
            {"name": "certification_not_completed",     "endpoint": "/tools/certification_not_completed",     "method": "GET", "description": "Karyawan yang belum menyelesaikan modul sertifikasi/assessment"},
            {"name": "training_not_started",            "endpoint": "/tools/training_not_started",            "method": "GET", "description": "Karyawan yang sudah bekerja tapi belum mulai training sama sekali"},
            {"name": "training_low_score",              "endpoint": "/tools/training_low_score",              "method": "GET", "description": "Karyawan yang sudah selesai training tapi nilai post-test rendah"},
            {"name": "training_most_failed",            "endpoint": "/tools/training_most_failed",            "method": "GET", "description": "Modul training yang paling banyak tidak diselesaikan karyawan"},
            {"name": "role_certification_not_completed","endpoint": "/tools/role_certification_not_completed","method": "GET", "description": "Karyawan yang belum mendapat sertifikasi role/jabatan spesifik"},
            {"name": "training_not_started_3months",    "endpoint": "/tools/training_not_started_3months",    "method": "GET", "description": "Karyawan yang sudah bekerja lebih dari N bulan tapi belum selesai training"},
            {"name": "leader_training_not_completed",   "endpoint": "/tools/leader_training_not_completed",   "method": "GET", "description": "Karyawan dengan modul kepemimpinan yang belum menyelesaikan training leader"},
            {"name": "safety_training_not_completed",   "endpoint": "/tools/safety_training_not_completed",   "method": "GET", "description": "Karyawan yang belum menyelesaikan training keselamatan kerja (safety/K3)"},
            {"name": "sop_training_not_completed",      "endpoint": "/tools/sop_training_not_completed",      "method": "GET", "description": "Karyawan yang belum menyelesaikan training SOP/prosedur operasional"},
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


# ══════════════════════════════════════════════════════════════════
# GROUP 6 — Full roster (no required params)
# ══════════════════════════════════════════════════════════════════

@app.get("/tools/list_all_employees", summary="Daftar semua karyawan aktif beserta detail")
def list_all_employees(
    active_only: bool = Query(True, description="True = hanya aktif, False = semua termasuk resign"),
    employment_status: Optional[str] = Query(None, description="Filter: Permanent atau Contract"),
):
    """
    Return full employee roster with key details. No required parameters.
    Answers: "Siapa saja karyawan aktif?", "Tampilkan semua karyawan",
             "Detailkan karyawan aktif", "List semua karyawan permanent"
    """
    import traceback
    try:
        df = load_df()

        if active_only:
            df = df[df["employee_data_status"].str.lower() == "active"]

        if employment_status:
            df = df[df["employment_status"].str.lower() == employment_status.lower()]

        def safe(v):
            """Convert pandas value to JSON-safe Python type."""
            if v is None: return None
            try:
                if pd.isna(v): return None
            except: pass
            return v

        result = []
        for _, r in df.iterrows():
            result.append({
                "employee_id":          safe(r["employee_id"]),
                "full_name":            safe(r["full_name"]),
                "department":           safe(r["department"]),
                "outlet":               safe(r["outlet"]),
                "job_position":         safe(r["job_position"]),
                "job_level":            int(r["job_level"]) if pd.notna(r["job_level"]) else None,
                "employment_status":    safe(r["employment_status"]),
                "employee_data_status": safe(r["employee_data_status"]),
                "join_date":            r["join_date"].strftime("%Y-%m-%d") if pd.notna(r["join_date"]) else None,
                "end_employment_date":  r["end_employment_date"].strftime("%Y-%m-%d") if pd.notna(r["end_employment_date"]) else None,
            })

        scope = "aktif" if active_only else "semua"
        filter_note = f" ({employment_status})" if employment_status else ""
        return {
            "total":     len(result),
            "scope":     scope + filter_note,
            "employees": result,
            "summary":   f"Total {len(result)} karyawan {scope}{filter_note}.",
        }
    except Exception as e:
        return {"error": str(e), "trace": traceback.format_exc()}


@app.get("/tools/list_active_by_status", summary="Daftar karyawan aktif dikelompokkan per status kepegawaian")
def list_active_by_status():
    """
    Return active employees grouped by employment_status (Permanent / Contract).
    Answers: "Berapa karyawan permanent vs kontrak dan siapa saja?",
             "Detail karyawan permanent", "Detail karyawan kontrak aktif"
    """
    df     = load_df()
    active = df[df["employee_data_status"].str.lower() == "active"]

    groups = {}
    for status, grp in active.groupby("employment_status", dropna=False):
        def safe(v):
            if v is None: return None
            try:
                if pd.isna(v): return None
            except: pass
            return v

        label = str(status) if pd.notna(status) else "Tidak diketahui"
        groups[label] = [
            {
                "employee_id":         safe(r["employee_id"]),
                "full_name":           safe(r["full_name"]),
                "department":          safe(r["department"]),
                "outlet":              safe(r["outlet"]),
                "job_position":        safe(r["job_position"]),
                "join_date":           r["join_date"].strftime("%Y-%m-%d") if pd.notna(r["join_date"]) else None,
                "end_employment_date": r["end_employment_date"].strftime("%Y-%m-%d") if pd.notna(r["end_employment_date"]) else None,
            }
            for _, r in grp.iterrows()
        ]

    summary_parts = [f"{k}: {len(v)} orang" for k, v in groups.items()]
    return {
        "total_active": len(active),
        "by_status":    groups,
        "summary":      f"Karyawan aktif: {', '.join(summary_parts)}.",
    }


# ══════════════════════════════════════════════════════════════════
# GROUP 7 — Historical / date-based filters
# ══════════════════════════════════════════════════════════════════

@app.get("/tools/list_employees_by_join_year", summary="Karyawan berdasarkan tahun bergabung")
def list_employees_by_join_year(
    year:        int           = Query(...,  description="Tahun bergabung, contoh: 2003"),
    active_only: bool          = Query(False, description="True = hanya yang masih aktif, False = semua termasuk resign"),
):
    """
    List employees who joined in a specific year.
    Answers: "Berapa karyawan yang join tahun 2003?", "Siapa yang bergabung tahun 2020?",
             "Karyawan yang masuk tahun X"
    """
    def safe(v):
        if v is None: return None
        try:
            if pd.isna(v): return None
        except: pass
        return v

    df = load_df()

    if active_only:
        df = df[df["employee_data_status"].str.lower() == "active"]

    filtered = df[df["join_date"].dt.year == year]

    result = []
    for _, r in filtered.iterrows():
        result.append({
            "employee_id":          safe(r["employee_id"]),
            "full_name":            safe(r["full_name"]),
            "department":           safe(r["department"]),
            "outlet":               safe(r["outlet"]),
            "job_position":         safe(r["job_position"]),
            "employment_status":    safe(r["employment_status"]),
            "employee_data_status": safe(r["employee_data_status"]),
            "join_date":            r["join_date"].strftime("%Y-%m-%d") if pd.notna(r["join_date"]) else None,
        })

    scope = "masih aktif" if active_only else "aktif maupun resign"
    return {
        "year":      year,
        "total":     len(result),
        "scope":     scope,
        "employees": result,
        "summary":   f"Ada {len(result)} karyawan yang bergabung pada tahun {year} ({scope}).",
    }


# ══════════════════════════════════════════════════════════════════
# GROUP 6 — Training (from all_employee_training_data.csv)
# ══════════════════════════════════════════════════════════════════

def _training_rows_by_employee(df: pd.DataFrame, outlet_name: Optional[str], limit: int) -> list:
    """Deduplicate by full_name, return one row per unique employee."""
    df = df.drop_duplicates(subset="full_name")
    if outlet_name:
        df = df[df["outlet_name"].str.contains(outlet_name, case=False, na=False)]
    result = []
    for _, r in df.head(limit).iterrows():
        result.append({
            "full_name":   r["full_name"],
            "outlet_name": r["outlet_name"],
            "brand_name":  r["brand_name"],
            "join_date":   r["join_date"].strftime("%Y-%m-%d") if pd.notna(r["join_date"]) else None,
            "status_training_wajib":    r["status_training_wajib"],
            "status_training_optional": r["status_training_optional"],
        })
    return result


def _training_rows_by_module(df: pd.DataFrame, outlet_name: Optional[str], limit: int) -> list:
    """Deduplicate by full_name + module_name, return one row per employee-module pair."""
    df = df.drop_duplicates(subset=["full_name", "module_name"])
    if outlet_name:
        df = df[df["outlet_name"].str.contains(outlet_name, case=False, na=False)]
    result = []
    for _, r in df.head(limit).iterrows():
        result.append({
            "full_name":   r["full_name"],
            "outlet_name": r["outlet_name"],
            "brand_name":  r["brand_name"],
            "module_name": r["module_name"],
            "join_date":   r["join_date"].strftime("%Y-%m-%d") if pd.notna(r["join_date"]) else None,
            "status_training_wajib":    r["status_training_wajib"],
            "status_training_optional": r["status_training_optional"],
        })
    return result


@app.get("/tools/training_wajib_not_completed", summary="Karyawan belum selesai training wajib")
def training_wajib_not_completed(
    outlet_name: Optional[str] = Query(None, description="Filter nama outlet (partial match)"),
    brand_name:  Optional[str] = Query(None, description="Filter nama brand (partial match)"),
    limit:       int           = Query(100,  description="Maks jumlah baris dikembalikan"),
):
    """
    List employees whose status_training_wajib is 'not yet'. Deduplicated by full_name.
    Answers: "Siapa belum training wajib?"
    """
    df = load_training_df()
    df = df[df["status_training_wajib"] == "not yet"]
    if brand_name:
        df = df[df["brand_name"].str.contains(brand_name, case=False, na=False)]
    df = df.drop_duplicates(subset="full_name")
    if outlet_name:
        df = df[df["outlet_name"].str.contains(outlet_name, case=False, na=False)]
    total  = len(df)
    result = _training_rows_by_employee(df, outlet_name=None, limit=limit)
    return {
        "total":     total,
        "returned":  len(result),
        "employees": result,
        "summary":   f"Ada {total} karyawan (unik) yang belum menyelesaikan training wajib.",
    }


@app.get("/tools/training_completion_by_outlet", summary="Tingkat penyelesaian training wajib per outlet")
def training_completion_by_outlet(
    top_n:      int           = Query(10,  description="Tampilkan N outlet terendah"),
    brand_name: Optional[str] = Query(None, description="Filter nama brand (partial match)"),
):
    """
    Outlets sorted by mandatory-training completion rate (ascending = lowest first).
    Counts unique employees (by full_name) per outlet.
    Answers: "Outlet mana training rendah?"
    """
    df = load_training_df()
    if brand_name:
        df = df[df["brand_name"].str.contains(brand_name, case=False, na=False)]
    # Deduplicate by full_name so each employee is counted once per outlet
    deduped = df.drop_duplicates(subset=["full_name", "outlet_name"])
    grp = deduped.groupby("outlet_name")["status_training_wajib"].apply(
        lambda x: (x == "done").sum() / len(x) * 100 if len(x) else 0
    ).reset_index()
    grp.columns = ["outlet_name", "completion_rate_pct"]
    counts = deduped.groupby("outlet_name").agg(
        total  =("full_name", "count"),
        done   =("status_training_wajib", lambda x: (x == "done").sum()),
    ).reset_index()
    grp = grp.merge(counts, on="outlet_name")
    grp["not_yet"] = grp["total"] - grp["done"]
    grp = grp.sort_values("completion_rate_pct").head(top_n)
    result = [
        {
            "outlet_name":         r["outlet_name"],
            "total_employees":     int(r["total"]),
            "done":                int(r["done"]),
            "not_yet":             int(r["not_yet"]),
            "completion_rate_pct": round(float(r["completion_rate_pct"]), 1),
        }
        for _, r in grp.iterrows()
    ]
    worst = result[0] if result else {}
    return {
        "outlets": result,
        "summary": (
            f"Outlet dengan tingkat training terendah: {worst.get('outlet_name')} "
            f"({worst.get('completion_rate_pct')}% selesai dari {worst.get('total_employees')} karyawan)."
        ),
    }


@app.get("/tools/certification_not_completed", summary="Karyawan belum selesai sertifikasi")
def certification_not_completed(
    outlet_name: Optional[str] = Query(None, description="Filter nama outlet (partial match)"),
    limit:       int           = Query(100,  description="Maks jumlah baris dikembalikan"),
):
    """
    Employees assigned to certification/assessment modules but status_training_wajib = 'not yet'.
    Deduplicated by full_name + module_name.
    Answers: "Siapa belum sertifikasi?"
    """
    df = load_training_df()
    df = df[
        df["module_name"].str.contains(CERT_MODULE_PATTERN, case=False, na=False, regex=True) &
        (df["status_training_wajib"] == "not yet")
    ]
    df = df.drop_duplicates(subset=["full_name", "module_name"])
    total  = len(df)
    result = _training_rows_by_module(df, outlet_name, limit)
    return {
        "total":     total,
        "returned":  len(result),
        "employees": result,
        "summary":   f"Ada {total} penugasan sertifikasi/assessment yang belum diselesaikan.",
    }


@app.get("/tools/training_not_started", summary="Karyawan belum mulai training sama sekali")
def training_not_started(
    outlet_name: Optional[str] = Query(None, description="Filter nama outlet (partial match)"),
    limit:       int           = Query(100,  description="Maks jumlah baris dikembalikan"),
):
    """
    Employees who have join_date (are working) but status_training_wajib = 'not yet'.
    Deduplicated by full_name.
    Answers: "Siapa belum training tapi sudah kerja?"
    """
    df = load_training_df()
    df = df[
        df["join_date"].notna() &
        (df["status_training_wajib"] == "not yet")
    ]
    df = df.drop_duplicates(subset="full_name")
    if outlet_name:
        df = df[df["outlet_name"].str.contains(outlet_name, case=False, na=False)]
    total  = len(df)
    result = _training_rows_by_employee(df, outlet_name=None, limit=limit)
    return {
        "total":     total,
        "returned":  len(result),
        "employees": result,
        "summary":   f"Ada {total} karyawan (unik) yang sudah bekerja tapi belum menyelesaikan training wajib.",
    }


@app.get("/tools/training_low_score", summary="Karyawan dengan nilai post-test rendah")
def training_low_score(
    threshold:   int           = Query(70,   description="Batas nilai rendah (default 70)"),
    outlet_name: Optional[str] = Query(None, description="Filter nama outlet (partial match)"),
    limit:       int           = Query(100,  description="Maks jumlah baris dikembalikan"),
):
    """
    Employees who completed training (done) but scored below threshold.
    Deduplicated by full_name + module_name, sorted by score ascending.
    Answers: "Siapa training score rendah?"
    """
    df = load_training_df()
    df = df[
        (df["status_training_wajib"] == "done") &
        df["post_test_grade"].notna() &
        (df["post_test_grade"] < threshold)
    ]
    df = df.drop_duplicates(subset=["full_name", "module_name"]).sort_values("post_test_grade")
    if outlet_name:
        df = df[df["outlet_name"].str.contains(outlet_name, case=False, na=False)]
    total = len(df)
    result = []
    for _, r in df.head(limit).iterrows():
        result.append({
            "full_name":       r["full_name"],
            "outlet_name":     r["outlet_name"],
            "brand_name":      r["brand_name"],
            "module_name":     r["module_name"],
            "post_test_grade": float(r["post_test_grade"]),
            "join_date":       r["join_date"].strftime("%Y-%m-%d") if pd.notna(r["join_date"]) else None,
        })
    return {
        "threshold": threshold,
        "total":     total,
        "returned":  len(result),
        "employees": result,
        "summary":   f"Ada {total} catatan nilai post-test di bawah {threshold} (unik per karyawan per modul).",
    }


@app.get("/tools/training_most_failed", summary="Modul training paling sering tidak diselesaikan")
def training_most_failed(
    top_n: int = Query(10, description="Tampilkan N modul teratas"),
):
    """
    Training modules ranked by number of unique employees (by full_name) who haven't completed them.
    Answers: "Training apa paling sering gagal?"
    """
    df = load_training_df()
    # Count unique employees per module
    grp = df.drop_duplicates(subset=["full_name", "module_name"]).groupby("module_name").agg(
        total    =("full_name", "count"),
        not_yet  =("status_training_wajib", lambda x: (x == "not yet").sum()),
        done     =("status_training_wajib", lambda x: (x == "done").sum()),
        avg_score=("post_test_grade", "mean"),
    ).reset_index()
    grp["failure_rate_pct"] = grp["not_yet"] / grp["total"] * 100
    grp = grp.sort_values("not_yet", ascending=False).head(top_n)
    result = [
        {
            "module_name":      r["module_name"],
            "total_assigned":   int(r["total"]),
            "not_completed":    int(r["not_yet"]),
            "completed":        int(r["done"]),
            "failure_rate_pct": round(float(r["failure_rate_pct"]), 1),
            "avg_score":        round(float(r["avg_score"]), 1) if pd.notna(r["avg_score"]) else None,
        }
        for _, r in grp.iterrows()
    ]
    top = result[0] if result else {}
    return {
        "modules": result,
        "summary": (
            f"Modul paling sering tidak diselesaikan: '{top.get('module_name')}' "
            f"dengan {top.get('not_completed')} karyawan belum selesai dari {top.get('total_assigned')} total."
        ),
    }


@app.get("/tools/role_certification_not_completed", summary="Karyawan belum sertifikasi sesuai role")
def role_certification_not_completed(
    outlet_name: Optional[str] = Query(None, description="Filter nama outlet (partial match)"),
    limit:       int           = Query(100,  description="Maks jumlah baris dikembalikan"),
):
    """
    Employees assigned to role-specific certification modules (leadership, wine, halal, GMP)
    but status_training_wajib = 'not yet'. Deduplicated by full_name + module_name.
    Answers: "Siapa belum sertifikasi role?"
    """
    df = load_training_df()
    df = df[
        df["module_name"].str.contains(ROLE_CERT_MODULE_PATTERN, case=False, na=False, regex=True) &
        (df["status_training_wajib"] == "not yet")
    ]
    df = df.drop_duplicates(subset=["full_name", "module_name"])
    total  = len(df)
    result = _training_rows_by_module(df, outlet_name, limit)
    return {
        "total":     total,
        "returned":  len(result),
        "employees": result,
        "summary":   f"Ada {total} penugasan sertifikasi role/jabatan yang belum diselesaikan.",
    }


@app.get("/tools/training_not_started_3months", summary="Karyawan belum training padahal sudah N bulan kerja")
def training_not_started_3months(
    months:      int           = Query(3,    description="Minimal masa kerja dalam bulan (default 3)"),
    outlet_name: Optional[str] = Query(None, description="Filter nama outlet (partial match)"),
    limit:       int           = Query(100,  description="Maks jumlah baris dikembalikan"),
):
    """
    Employees who joined more than N months ago but status_training_wajib = 'not yet'.
    Deduplicated by full_name.
    Answers: "Siapa belum training tapi sudah 3 bulan kerja?"
    """
    df     = load_training_df()
    cutoff = pd.Timestamp(date.today()) - pd.DateOffset(months=months)
    df = df[
        df["join_date"].notna() &
        (df["join_date"] <= cutoff) &
        (df["status_training_wajib"] == "not yet")
    ]
    df = df.drop_duplicates(subset="full_name")
    if outlet_name:
        df = df[df["outlet_name"].str.contains(outlet_name, case=False, na=False)]
    total  = len(df)
    result = _training_rows_by_employee(df, outlet_name=None, limit=limit)
    return {
        "months":      months,
        "cutoff_date": cutoff.strftime("%Y-%m-%d"),
        "total":       total,
        "returned":    len(result),
        "employees":   result,
        "summary": (
            f"Ada {total} karyawan (unik) yang bergabung lebih dari {months} bulan lalu "
            f"(sebelum {cutoff.strftime('%Y-%m-%d')}) tapi belum menyelesaikan training wajib."
        ),
    }


@app.get("/tools/leader_training_not_completed", summary="Leader/manager belum selesai training kepemimpinan")
def leader_training_not_completed(
    outlet_name: Optional[str] = Query(None, description="Filter nama outlet (partial match)"),
    limit:       int           = Query(100,  description="Maks jumlah baris dikembalikan"),
):
    """
    Employees assigned to leadership training modules who haven't completed them.
    Deduplicated by full_name + module_name.
    Answers: "Siapa leader belum training leader?"
    """
    df = load_training_df()
    df = df[
        df["module_name"].str.contains(LEADER_MODULE_PATTERN, case=False, na=False, regex=True) &
        (df["status_training_wajib"] == "not yet")
    ]
    df = df.drop_duplicates(subset=["full_name", "module_name"])
    total  = len(df)
    result = _training_rows_by_module(df, outlet_name, limit)
    return {
        "total":     total,
        "returned":  len(result),
        "employees": result,
        "summary":   f"Ada {total} penugasan modul kepemimpinan yang belum diselesaikan.",
    }


@app.get("/tools/safety_training_not_completed", summary="Karyawan belum selesai training safety")
def safety_training_not_completed(
    outlet_name: Optional[str] = Query(None, description="Filter nama outlet (partial match)"),
    limit:       int           = Query(100,  description="Maks jumlah baris dikembalikan"),
):
    """
    Employees assigned to safety/K3/WSE/Food-Safety modules who haven't completed them.
    Deduplicated by full_name + module_name.
    Answers: "Siapa belum training safety?"
    """
    df = load_training_df()
    df = df[
        df["module_name"].str.contains(SAFETY_MODULE_PATTERN, case=False, na=False, regex=True) &
        (df["status_training_wajib"] == "not yet")
    ]
    df = df.drop_duplicates(subset=["full_name", "module_name"])
    total  = len(df)
    result = _training_rows_by_module(df, outlet_name, limit)
    return {
        "total":     total,
        "returned":  len(result),
        "employees": result,
        "summary":   f"Ada {total} penugasan modul safety/K3 yang belum diselesaikan.",
    }


@app.get("/tools/sop_training_not_completed", summary="Karyawan belum selesai training SOP")
def sop_training_not_completed(
    outlet_name: Optional[str] = Query(None, description="Filter nama outlet (partial match)"),
    limit:       int           = Query(100,  description="Maks jumlah baris dikembalikan"),
):
    """
    Employees assigned to SOP/procedure/sequence-of-service modules who haven't completed them.
    Deduplicated by full_name + module_name.
    Answers: "Siapa belum training SOP?"
    """
    df = load_training_df()
    df = df[
        df["module_name"].str.contains(SOP_MODULE_PATTERN, case=False, na=False, regex=True) &
        (df["status_training_wajib"] == "not yet")
    ]
    df = df.drop_duplicates(subset=["full_name", "module_name"])
    total  = len(df)
    result = _training_rows_by_module(df, outlet_name, limit)
    return {
        "total":     total,
        "returned":  len(result),
        "employees": result,
        "summary":   f"Ada {total} penugasan modul SOP/prosedur yang belum diselesaikan.",
    }