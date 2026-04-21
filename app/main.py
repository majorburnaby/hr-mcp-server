"""
HR Employee MCP Server — FastAPI v2.0.0
MCP-compatible API server for Dify tool integration.
17 tools covering headcount, contracts, turnover, search, and assignment gaps.
"""

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
import pandas as pd
from datetime import date
from typing import Optional
import os, io, inspect
from urllib.parse import urlencode

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
      "description": "Daftar karyawan unik yang is_module_mandatory=1 dan post_test_grade null atau < 90. Jawab: Siapa belum training wajib? Siapa yang belum menyelesaikan training mandatory?",
      "parameters": [
        {"name": "outlet_name", "in": "query", "required": False, "schema": {"type": "string",  "nullable": True}, "description": "Filter nama outlet (partial match)"},
        {"name": "brand_name",  "in": "query", "required": False, "schema": {"type": "string",  "nullable": True}, "description": "Filter nama brand (partial match)"},
        {"name": "limit",       "in": "query", "required": False, "schema": {"type": "integer", "default": 100},   "description": "Maks jumlah baris dikembalikan"}
      ],
      "responses": {"200": {"description": "OK", "content": {"application/json": {"schema": {"type": "object"}}}}}
    }},
    "/tools/training_completion_by_outlet": {"get": {
      "operationId": "training_completion_by_outlet",
      "summary": "Tingkat penyelesaian training per outlet (nilai >= 90)",
      "description": "Outlet diurutkan dari completion rate terendah. Completion dihitung dari karyawan dengan post_test_grade >= 90. Jawab: Outlet mana training rendah? Outlet mana completion training paling rendah?",
      "parameters": [
        {"name": "top_n",      "in": "query", "required": False, "schema": {"type": "integer", "default": 10},   "description": "Tampilkan N outlet terendah"},
        {"name": "brand_name", "in": "query", "required": False, "schema": {"type": "string",  "nullable": True}, "description": "Filter nama brand (partial match)"}
      ],
      "responses": {"200": {"description": "OK", "content": {"application/json": {"schema": {"type": "object"}}}}}
    }},
    "/tools/training_not_started": {"get": {
      "operationId": "training_not_started",
      "summary": "Karyawan ada di LMS tapi progress = 0",
      "description": "Karyawan yang total post_test_grade-nya = 0 (semua null atau nol) — ada di LMS tapi belum ada progress sama sekali. Jawab: Siapa belum training tapi sudah kerja? Siapa yang progress training masih 0?",
      "parameters": [
        {"name": "outlet_name", "in": "query", "required": False, "schema": {"type": "string",  "nullable": True}, "description": "Filter nama outlet (partial match)"},
        {"name": "brand_name",  "in": "query", "required": False, "schema": {"type": "string",  "nullable": True}, "description": "Filter nama brand (partial match)"},
        {"name": "limit",       "in": "query", "required": False, "schema": {"type": "integer", "default": 100},   "description": "Maks jumlah baris dikembalikan"}
      ],
      "responses": {"200": {"description": "OK", "content": {"application/json": {"schema": {"type": "object"}}}}}
    }},
    "/tools/safety_training_not_completed": {"get": {
      "operationId": "safety_training_not_completed",
      "summary": "Karyawan belum selesai training safety",
      "description": "Karyawan yang ditugaskan modul keselamatan kerja (safety, WSE, K3, HACCP, Food Safety) tapi belum menyelesaikannya. Jawab: Siapa belum training safety? Siapa belum training K3?",
      "parameters": [
        {"name": "outlet_name", "in": "query", "required": False, "schema": {"type": "string", "nullable": True}, "description": "Filter nama outlet (partial match)"},
        {"name": "brand_name",  "in": "query", "required": False, "schema": {"type": "string", "nullable": True}, "description": "Filter nama brand (partial match)"},
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
        {"name": "brand_name",  "in": "query", "required": False, "schema": {"type": "string", "nullable": True}, "description": "Filter nama brand (partial match)"},
        {"name": "limit",       "in": "query", "required": False, "schema": {"type": "integer", "default": 100},  "description": "Maks jumlah baris dikembalikan"}
      ],
      "responses": {"200": {"description": "OK", "content": {"application/json": {"schema": {"type": "object"}}}}}
    }},
    "/tools/onboarding_not_completed": {"get": {
      "operationId": "onboarding_not_completed",
      "summary": "Karyawan belum selesai modul onboarding & sudah > N hari kerja",
      "description": "Karyawan yang sudah bekerja lebih dari N hari tapi modul onboarding/induction belum selesai (post_test_grade null atau < 90). Jawab: Siapa belum selesai onboarding minggu ini? Siapa yang sudah > 7 hari kerja tapi belum onboarding?",
      "parameters": [
        {"name": "days",        "in": "query", "required": False, "schema": {"type": "integer", "default": 7},    "description": "Minimal masa kerja dalam hari (default 7)"},
        {"name": "outlet_name", "in": "query", "required": False, "schema": {"type": "string",  "nullable": True}, "description": "Filter nama outlet (partial match)"},
        {"name": "brand_name",  "in": "query", "required": False, "schema": {"type": "string",  "nullable": True}, "description": "Filter nama brand (partial match)"},
        {"name": "limit",       "in": "query", "required": False, "schema": {"type": "integer", "default": 100},   "description": "Maks jumlah baris dikembalikan"}
      ],
      "responses": {"200": {"description": "OK", "content": {"application/json": {"schema": {"type": "object"}}}}}
    }},
    "/tools/training_incomplete_assigned": {"get": {
      "operationId": "training_incomplete_assigned",
      "summary": "Karyawan belum menyelesaikan training yang sudah di-assign",
      "description": "Karyawan yang masih punya training belum selesai (post_test_grade null atau < 90), beserta daftar modul yang belum diselesaikan, termasuk jumlah modul wajib dan opsional. Jawab: Siapa saja yang belum menyelesaikan training yang sudah di assign?",
      "parameters": [
        {"name": "outlet_name", "in": "query", "required": False, "schema": {"type": "string",  "nullable": True}, "description": "Filter nama outlet (partial match)"},
        {"name": "brand_name",  "in": "query", "required": False, "schema": {"type": "string",  "nullable": True}, "description": "Filter nama brand (partial match)"},
        {"name": "limit",       "in": "query", "required": False, "schema": {"type": "integer", "default": 50},    "description": "Maks jumlah karyawan dikembalikan"}
      ],
      "responses": {"200": {"description": "OK", "content": {"application/json": {"schema": {"type": "object"}}}}}
    }},
    "/tools/training_low_score": {"get": {
      "operationId": "training_low_score",
      "summary": "Karyawan dengan nilai post-test rendah (< threshold atau belum ada nilai)",
      "description": "Karyawan yang post_test_grade-nya null atau di bawah ambang batas. Jawab: Siapa training score rendah? Siapa yang nilai ujian training-nya rendah?",
      "parameters": [
        {"name": "threshold",   "in": "query", "required": False, "schema": {"type": "integer", "default": 90},   "description": "Batas nilai rendah (default 90)"},
        {"name": "outlet_name", "in": "query", "required": False, "schema": {"type": "string",  "nullable": True}, "description": "Filter nama outlet (partial match)"},
        {"name": "brand_name",  "in": "query", "required": False, "schema": {"type": "string",  "nullable": True}, "description": "Filter nama brand (partial match)"},
        {"name": "limit",       "in": "query", "required": False, "schema": {"type": "integer", "default": 100},   "description": "Maks jumlah baris dikembalikan"}
      ],
      "responses": {"200": {"description": "OK", "content": {"application/json": {"schema": {"type": "object"}}}}}
    }},
    "/tools/training_most_failed": {"get": {
      "operationId": "training_most_failed",
      "summary": "Modul training paling sering gagal (post_test_grade < 90)",
      "description": "Top N modul berdasarkan jumlah karyawan yang mendapat post_test_grade < 90. Jawab: Training apa paling sering gagal? Modul mana yang paling banyak tidak lulus?",
      "parameters": [
        {"name": "top_n", "in": "query", "required": False, "schema": {"type": "integer", "default": 5}, "description": "Tampilkan N modul teratas (default 5)"}
      ],
      "responses": {"200": {"description": "OK", "content": {"application/json": {"schema": {"type": "object"}}}}}
    }},
    "/tools/training_prepost_comparison": {"get": {
      "operationId": "training_prepost_comparison",
      "summary": "Perbandingan rata-rata pre-test vs post-test per modul",
      "description": "Membandingkan rata-rata nilai pre_test_grade vs post_test_grade per modul training, diurutkan berdasarkan delta (post - pre) tertinggi. Jawab: Perbandingan pre-test vs post-test per modul? Modul mana yang paling banyak peningkatan nilai?",
      "parameters": [
        {"name": "outlet_name", "in": "query", "required": False, "schema": {"type": "string", "nullable": True}, "description": "Filter nama outlet (partial match)"},
        {"name": "brand_name",  "in": "query", "required": False, "schema": {"type": "string", "nullable": True}, "description": "Filter nama brand (partial match)"}
      ],
      "responses": {"200": {"description": "OK", "content": {"application/json": {"schema": {"type": "object"}}}}}
    }},
    "/tools/get_employee_training": {"get": {
      "operationId": "get_employee_training",
      "summary": "Daftar modul training yang diassign ke karyawan tertentu",
      "description": "Cari semua modul training yang diassign ke karyawan berdasarkan nama atau employee_id. Jawab: Training apa saja yang diassign ke karyawan XX? Modul apa yang sudah/belum dikerjakan si XX?",
      "parameters": [
        {"name": "employee_name", "in": "query", "required": False, "schema": {"type": "string", "nullable": True}, "description": "Nama karyawan (partial match, case-insensitive)"},
        {"name": "employee_id",   "in": "query", "required": False, "schema": {"type": "string", "nullable": True}, "description": "Employee ID (exact match)"}
      ],
      "responses": {"200": {"description": "OK", "content": {"application/json": {"schema": {"type": "object"}}}}}
    }},
    "/tools/list_training_modules": {"get": {
      "operationId": "list_training_modules",
      "summary": "Daftar semua modul training yang tersedia (deduplikasi)",
      "description": "Tampilkan semua nama modul training unik dari data LMS. Jawab: Apa saja modul training yang ada? List semua training yang tersedia? Ada berapa modul wajib?",
      "parameters": [
        {"name": "brand_name",          "in": "query", "required": False, "schema": {"type": "string", "nullable": True}, "description": "Filter nama brand (partial match)"},
        {"name": "is_module_mandatory",  "in": "query", "required": False, "schema": {"type": "string", "nullable": True}, "description": "Filter: '1' = wajib, '0' = opsional"}
      ],
      "responses": {"200": {"description": "OK", "content": {"application/json": {"schema": {"type": "object"}}}}}
    }},
    "/tools/training_completion_by_module": {"get": {
      "operationId": "training_completion_by_module",
      "summary": "Completion rate training per modul",
      "description": "Completion rate per modul training diurutkan dari terendah/tertinggi, dengan breakdown per outlet. Jawab: Berapa % completion rate per modul? Modul mana completion paling rendah? Siapa yang belum di outlet mana?",
      "parameters": [
        {"name": "top_n",      "in": "query", "required": False, "schema": {"type": "integer", "default": 10},   "description": "Tampilkan N modul"},
        {"name": "brand_name", "in": "query", "required": False, "schema": {"type": "string",  "nullable": True}, "description": "Filter nama brand (partial match)"},
        {"name": "sort_by",    "in": "query", "required": False, "schema": {"type": "string",  "default": "asc"}, "description": "'asc' = terendah dulu, 'desc' = tertinggi dulu"}
      ],
      "responses": {"200": {"description": "OK", "content": {"application/json": {"schema": {"type": "object"}}}}}
    }},
    "/tools/competency_gap_by_role": {"get": {
      "operationId": "competency_gap_by_role",
      "summary": "Gap kompetensi berdasarkan role dan modul training",
      "description": "Posisi/jabatan dengan fail rate post-test tertinggi per modul. Jawab: Role apa yang paling banyak fail post-test? Indikasi competency gap per jabatan?",
      "parameters": [
        {"name": "top_n",       "in": "query", "required": False, "schema": {"type": "integer", "default": 10},   "description": "Tampilkan N gap teratas"},
        {"name": "module_name", "in": "query", "required": False, "schema": {"type": "string",  "nullable": True}, "description": "Filter nama modul (partial match)"}
      ],
      "responses": {"200": {"description": "OK", "content": {"application/json": {"schema": {"type": "object"}}}}}
    }},
    "/tools/ld_key_insights": {"get": {
      "operationId": "ld_key_insights",
      "summary": "Key insight L&D: green news dan red news",
      "description": "Insight utama L&D dari data saat ini: green news (hal positif) dan red news (area perlu tindak lanjut). Jawab: Berikan key insight L&D bulan ini. Green news dan red news training.",
      "parameters": [
        {"name": "brand_name", "in": "query", "required": False, "schema": {"type": "string", "nullable": True}, "description": "Filter nama brand (partial match)"}
      ],
      "responses": {"200": {"description": "OK", "content": {"application/json": {"schema": {"type": "object"}}}}}
    }},
    "/tools/weekly_ld_digest": {"get": {
      "operationId": "weekly_ld_digest",
      "summary": "Weekly L&D digest: completion rate, overdue, modul bermasalah",
      "description": "Digest mingguan L&D: completion rate per modul, penugasan overdue, dan modul yang perlu perhatian. Jawab: Generate weekly L&D digest. Training overdue minggu ini. Modul completion turun.",
      "parameters": [
        {"name": "brand_name",   "in": "query", "required": False, "schema": {"type": "string",  "nullable": True}, "description": "Filter nama brand (partial match)"},
        {"name": "overdue_days", "in": "query", "required": False, "schema": {"type": "integer", "default": 14},    "description": "Ambang hari assign dianggap overdue (default 14)"}
      ],
      "responses": {"200": {"description": "OK", "content": {"application/json": {"schema": {"type": "object"}}}}}
    }},
    "/tools/list_employee_training_modules": {"get": {
      "operationId": "list_employee_training_modules",
      "summary": "Daftar modul training yang di-assign ke karyawan tertentu",
      "description": "Ringkasan semua modul training yang diassign ke karyawan: total, selesai, belum selesai, dan status per modul. Jawab: Ada modul apa saja yang diassign ke karyawan X? Berapa modul yang sudah/belum selesai si X?",
      "parameters": [
        {"name": "name_or_id", "in": "query", "required": True, "schema": {"type": "string"}, "description": "Nama atau employee_id karyawan"}
      ],
      "responses": {"200": {"description": "OK", "content": {"application/json": {"schema": {"type": "object"}}}}}
    }},
    "/tools/get_export_link": {"get": {
      "operationId": "get_export_link",
      "summary": "Buat link download ekspor data ke CSV atau Excel",
      "description": "Gunakan tool ini ketika user meminta export data. Panggil dengan tool_name yang sama persis seperti tool sebelumnya, beserta parameter filter yang sama. Jawab: Export ke excel, Download data ini, Simpan sebagai CSV, Ekspor hasilnya.",
      "parameters": [
        {"name": "tool_name",           "in": "query", "required": True,  "schema": {"type": "string"},                   "description": "Nama tool yang sebelumnya digunakan untuk mengambil data"},
        {"name": "format",              "in": "query", "required": False, "schema": {"type": "string", "default": "excel"},"description": "'csv' atau 'excel' (default: excel)"},
        {"name": "outlet_name",         "in": "query", "required": False, "schema": {"type": "string", "nullable": True}, "description": "Sama dengan filter outlet di tool sebelumnya"},
        {"name": "brand_name",          "in": "query", "required": False, "schema": {"type": "string", "nullable": True}, "description": "Sama dengan filter brand di tool sebelumnya"},
        {"name": "limit",               "in": "query", "required": False, "schema": {"type": "integer","default": 500},   "description": "Jumlah baris (default 500 untuk ekspor)"},
        {"name": "top_n",               "in": "query", "required": False, "schema": {"type": "integer","nullable": True}, "description": "Sama dengan top_n di tool sebelumnya"},
        {"name": "months",              "in": "query", "required": False, "schema": {"type": "integer","nullable": True}, "description": "Sama dengan months di tool sebelumnya"},
        {"name": "days",                "in": "query", "required": False, "schema": {"type": "integer","nullable": True}, "description": "Sama dengan days di tool sebelumnya"},
        {"name": "year",                "in": "query", "required": False, "schema": {"type": "integer","nullable": True}, "description": "Sama dengan year di tool sebelumnya"},
        {"name": "name",                "in": "query", "required": False, "schema": {"type": "string", "nullable": True}, "description": "Sama dengan name di tool sebelumnya"},
        {"name": "department",          "in": "query", "required": False, "schema": {"type": "string", "nullable": True}, "description": "Sama dengan department di tool sebelumnya"},
        {"name": "threshold",           "in": "query", "required": False, "schema": {"type": "integer","nullable": True}, "description": "Sama dengan threshold di tool sebelumnya"},
        {"name": "employee_name",       "in": "query", "required": False, "schema": {"type": "string", "nullable": True}, "description": "Sama dengan employee_name di tool sebelumnya"},
        {"name": "employee_id",         "in": "query", "required": False, "schema": {"type": "string", "nullable": True}, "description": "Sama dengan employee_id di tool sebelumnya"},
        {"name": "is_module_mandatory", "in": "query", "required": False, "schema": {"type": "string", "nullable": True}, "description": "Sama dengan is_module_mandatory di tool sebelumnya"},
        {"name": "employment_status",   "in": "query", "required": False, "schema": {"type": "string", "nullable": True}, "description": "Sama dengan employment_status di tool sebelumnya"}
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

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "employee_data_20260417.csv")

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

TRAINING_DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "all_employee_training_data_20260417.csv")

def load_training_df() -> pd.DataFrame:
    """Load and normalise training CSV on every request."""
    df = pd.read_csv(TRAINING_DATA_PATH, dtype=str)
    df.columns = [c.strip().lower() for c in df.columns]
    df["join_date"]            = pd.to_datetime(df["join_date"], errors="coerce")
    df["module_assigned_date"] = pd.to_datetime(df["module_assigned_date"], errors="coerce")
    df["pre_test_grade"]       = pd.to_numeric(df["pre_test_grade"],  errors="coerce")
    df["post_test_grade"]      = pd.to_numeric(df["post_test_grade"], errors="coerce")
    df["is_outlet"]            = df["is_outlet"].str.strip()
    df["is_module_mandatory"]  = df["is_module_mandatory"].str.strip()
    return df

# Keyword patterns for training module categorisation
SAFETY_MODULE_PATTERN      = r"safety|Safety|WSE|wse|Work-Safe|K3|HACCP|FSH|Food.Safety"
SOP_MODULE_PATTERN         = r"SOP|sop|Procedure|procedure|Sequence-of-Service|Closing-Outlet|Opening-Outlet"
ONBOARDING_MODULE_PATTERN  = r"onboarding|Onboarding|induction|Induction|orientasi|Orientasi"

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
            {"name": "training_wajib_not_completed",   "endpoint": "/tools/training_wajib_not_completed",   "method": "GET", "description": "Karyawan yang belum menyelesaikan training wajib (mandatory). Jawab: Siapa belum training wajib?"},
            {"name": "training_completion_by_outlet",  "endpoint": "/tools/training_completion_by_outlet",  "method": "GET", "description": "Outlet dengan completion rate training terendah (dihitung dari post_test_grade >= 90). Jawab: Outlet mana training rendah?"},
            {"name": "training_not_started",           "endpoint": "/tools/training_not_started",           "method": "GET", "description": "Karyawan yang ada di LMS tapi total progress = 0 (semua post_test_grade nol/null). Jawab: Siapa belum training tapi sudah kerja?"},
            {"name": "safety_training_not_completed",  "endpoint": "/tools/safety_training_not_completed",  "method": "GET", "description": "Karyawan yang belum menyelesaikan modul safety/K3/WSE/HACCP/Food Safety. Jawab: Siapa belum training safety?"},
            {"name": "sop_training_not_completed",     "endpoint": "/tools/sop_training_not_completed",     "method": "GET", "description": "Karyawan yang belum menyelesaikan modul SOP/prosedur operasional. Jawab: Siapa belum training SOP?"},
            {"name": "onboarding_not_completed",       "endpoint": "/tools/onboarding_not_completed",       "method": "GET", "description": "Karyawan yang sudah > N hari bekerja tapi belum selesai modul onboarding/induction. Jawab: Siapa belum selesai onboarding minggu ini?"},
            {"name": "training_incomplete_assigned",   "endpoint": "/tools/training_incomplete_assigned",   "method": "GET", "description": "Karyawan yang masih punya training belum selesai beserta daftar modulnya. Jawab: Siapa saja yang belum menyelesaikan training yang sudah di assign?"},
            {"name": "training_low_score",             "endpoint": "/tools/training_low_score",             "method": "GET", "description": "Karyawan dengan post_test_grade null atau di bawah threshold. Jawab: Siapa training score rendah?"},
            {"name": "training_most_failed",           "endpoint": "/tools/training_most_failed",           "method": "GET", "description": "Top 5 modul dengan jumlah karyawan gagal (post_test_grade < 90) terbanyak. Jawab: Training apa paling sering gagal?"},
            {"name": "training_prepost_comparison",    "endpoint": "/tools/training_prepost_comparison",    "method": "GET", "description": "Perbandingan rata-rata pre_test_grade vs post_test_grade per modul. Jawab: Perbandingan pre-test vs post-test per modul?"},
            {"name": "get_employee_training",          "endpoint": "/tools/get_employee_training",          "method": "GET", "description": "Daftar semua modul training yang diassign ke karyawan tertentu. Jawab: Training apa saja yang diassign ke karyawan XX?"},
            {"name": "list_training_modules",          "endpoint": "/tools/list_training_modules",          "method": "GET", "description": "Daftar semua nama modul training unik dari LMS. Jawab: Apa saja modul training yang ada? List semua training yang tersedia?"},
            {"name": "training_completion_by_module",  "endpoint": "/tools/training_completion_by_module",  "method": "GET", "description": "Completion rate per modul training dengan breakdown per outlet. Jawab: Berapa % completion rate per modul? Modul mana paling rendah?"},
            {"name": "competency_gap_by_role",         "endpoint": "/tools/competency_gap_by_role",         "method": "GET", "description": "Gap kompetensi: posisi/jabatan dengan fail rate post-test tertinggi per modul. Jawab: Role apa paling banyak fail post-test? Indikasi competency gap?"},
            {"name": "ld_key_insights",                "endpoint": "/tools/ld_key_insights",                "method": "GET", "description": "Key insight L&D: green news (positif) dan red news (perlu tindak lanjut). Jawab: Key insight L&D bulan ini. Green news dan red news training."},
            {"name": "weekly_ld_digest",               "endpoint": "/tools/weekly_ld_digest",               "method": "GET", "description": "Weekly L&D digest: completion rate, overdue, modul bermasalah. Jawab: Generate weekly L&D digest. Training overdue minggu ini."},
            {"name": "list_employee_training_modules", "endpoint": "/tools/list_employee_training_modules", "method": "GET", "description": "Ringkasan modul training per karyawan: total, selesai, belum selesai. Jawab: Ada modul apa saja yang diassign ke karyawan X?"},
            # Export
            {"name": "get_export_link",                "endpoint": "/tools/get_export_link",                "method": "GET", "description": "Buat link download ekspor data ke CSV/Excel. Panggil dengan tool_name yang sama seperti tool sebelumnya. Jawab: Export ke excel, Download data ini, Simpan sebagai CSV."},
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


def _training_rows_by_module(df: pd.DataFrame, outlet_name: Optional[str], limit: int) -> list:
    """Deduplicate by employee_id + module_name, return one row per employee-module pair."""
    df = df.drop_duplicates(subset=["employee_id", "module_name"])
    if outlet_name:
        df = df[df["outlet_name"].str.contains(outlet_name, case=False, na=False)]
    today = pd.Timestamp(date.today())
    result = []
    for _, r in df.head(limit).iterrows():
        join_dt = r["join_date"] if pd.notna(r["join_date"]) else None
        result.append({
            "employee_id":          r["employee_id"],
            "full_name":            r["full_name"],
            "outlet_name":          r["outlet_name"],
            "is_outlet":            r["is_outlet"],
            "brand_name":           r["brand_name"],
            "module_name":          r["module_name"],
            "module_type":          r["module_type"],
            "is_module_mandatory":  r["is_module_mandatory"],
            "module_assigned_date": r["module_assigned_date"].strftime("%Y-%m-%d") if pd.notna(r["module_assigned_date"]) else None,
            "post_test_grade":      float(r["post_test_grade"]) if pd.notna(r["post_test_grade"]) else None,
            "join_date":            join_dt.strftime("%Y-%m-%d") if join_dt else None,
            "days_since_join":      int((today - join_dt).days) if join_dt else None,
        })
    return result


@app.get("/tools/training_wajib_not_completed", summary="Karyawan belum selesai training wajib")
def training_wajib_not_completed(
    outlet_name: Optional[str] = Query(None, description="Filter nama outlet (partial match)"),
    brand_name:  Optional[str] = Query(None, description="Filter nama brand (partial match)"),
    limit:       int           = Query(50,   description="Maks jumlah baris dikembalikan"),
):
    """
    Employees with at least one incomplete mandatory module (is_module_mandatory=1,
    post_test_grade null or < 90), grouped with a list of their incomplete module names.
    Answers: "Siapa belum training wajib?"
    """
    df = load_training_df()
    df = df[
        (df["is_module_mandatory"] == "1") &
        (df["post_test_grade"].isna() | (df["post_test_grade"] < 90))
    ]
    if brand_name:
        df = df[df["brand_name"].str.contains(brand_name, case=False, na=False)]
    if outlet_name:
        df = df[df["outlet_name"].str.contains(outlet_name, case=False, na=False)]
    df = df.drop_duplicates(subset=["employee_id", "module_name"])
    today = date.today()
    grouped = []
    for emp_id, g in df.groupby("employee_id"):
        join_dt = g["join_date"].iloc[0]
        join_str = join_dt.strftime("%Y-%m-%d") if pd.notna(join_dt) else None
        days_since_join = int((pd.Timestamp(today) - join_dt).days) if pd.notna(join_dt) else None
        grouped.append({
            "employee_id":                emp_id,
            "full_name":                  g["full_name"].iloc[0],
            "outlet_name":                g["outlet_name"].iloc[0],
            "is_outlet":                  g["is_outlet"].iloc[0],
            "brand_name":                 g["brand_name"].iloc[0],
            "join_date":                  join_str,
            "days_since_join":            days_since_join,
            "incomplete_mandatory_modules": sorted(g["module_name"].dropna().tolist())[:5],
            "total_incomplete":           len(g),
        })
    grouped.sort(key=lambda x: x["total_incomplete"], reverse=True)
    total  = len(grouped)
    result = grouped[:limit]
    outlets_affected = len(set(e["outlet_name"] for e in grouped))
    priority = sum(
        1 for e in grouped
        if e["days_since_join"] is not None and e["days_since_join"] > 30
    )
    return {
        "total":     total,
        "returned":  len(result),
        "employees": result,
        "summary": (
            f"Ada {total} karyawan (unik) yang belum menyelesaikan training wajib, "
            f"tersebar di {outlets_affected} outlet. "
            f"Prioritas: {priority} karyawan dengan progress 0% atau bergabung > 30 hari lalu."
        ),
    }


@app.get("/tools/training_completion_by_outlet", summary="Tingkat penyelesaian training per outlet")
def training_completion_by_outlet(
    top_n:      int           = Query(10,   description="Tampilkan N outlet terendah"),
    brand_name: Optional[str] = Query(None, description="Filter nama brand (partial match)"),
):
    """
    Outlets sorted by completion rate ascending (lowest first).
    Completion = employees with post_test_grade >= 90 / employees with post_test_grade not null.
    Deduplicated by employee_id + outlet_name.
    Answers: "Outlet mana training rendah?"
    """
    df = load_training_df()
    df = df[df["is_outlet"] == "1"]
    if brand_name:
        df = df[df["brand_name"].str.contains(brand_name, case=False, na=False)]
    if df.empty:
        return {"outlets": [], "summary": "Tidak ada data outlet yang tercatat."}
    # Total unique employees assigned per outlet
    total_per_outlet = (
        df.drop_duplicates(subset=["employee_id", "outlet_name"])
        .groupby("outlet_name")["employee_id"].count()
        .reset_index().rename(columns={"employee_id": "total_employees"})
    )
    # Completed: employees with at least one post_test_grade >= 90
    completed_per_outlet = (
        df[df["post_test_grade"] >= 90][["employee_id", "outlet_name"]]
        .drop_duplicates()
        .groupby("outlet_name")["employee_id"].count()
        .reset_index().rename(columns={"employee_id": "completed_employees"})
    )
    grp = total_per_outlet.merge(completed_per_outlet, on="outlet_name", how="left")
    grp["completed_employees"] = grp["completed_employees"].fillna(0).astype(int)
    grp["completion_rate_pct"] = (grp["completed_employees"] / grp["total_employees"] * 100).round(1)
    grp = grp.sort_values("completion_rate_pct").head(top_n)
    result = [
        {
            "outlet_name":          r["outlet_name"],
            "total_employees":      int(r["total_employees"]),
            "completed_employees":  int(r["completed_employees"]),
            "completion_rate_pct":  float(r["completion_rate_pct"]),
            "completion_display":   f"{int(r['completed_employees'])} dari {int(r['total_employees'])} karyawan selesai",
        }
        for _, r in grp.iterrows()
    ]
    worst = result[0] if result else {}
    return {
        "outlets": result,
        "summary": (
            f"Outlet dengan completion rate terendah: {worst.get('outlet_name')} "
            f"({worst.get('completion_rate_pct')}% — {worst.get('completion_display')})."
        ),
    }


@app.get("/tools/training_not_started", summary="Karyawan ada di LMS tapi progress = 0")
def training_not_started(
    outlet_name: Optional[str] = Query(None, description="Filter nama outlet (partial match)"),
    brand_name:  Optional[str] = Query(None, description="Filter nama brand (partial match)"),
    limit:       int           = Query(100,  description="Maks jumlah baris dikembalikan"),
):
    """
    Employees whose total post_test_grade is 0 (all null or zero) — in LMS but zero progress.
    Answers: "Siapa belum training tapi sudah kerja (ada di LMS tapi progress = 0)?"
    """
    df = load_training_df()
    if brand_name:
        df = df[df["brand_name"].str.contains(brand_name, case=False, na=False)]
    if outlet_name:
        df = df[df["outlet_name"].str.contains(outlet_name, case=False, na=False)]
    # Sum post_test_grade per employee (treat null as 0); keep employees with sum == 0
    grade_sum = df.groupby("employee_id")["post_test_grade"].sum(min_count=0).fillna(0)
    zero_ids  = grade_sum[grade_sum == 0].index
    df_not_started = df[df["employee_id"].isin(zero_ids)]
    today = pd.Timestamp(date.today())
    grouped = []
    for emp_id, grp in df_not_started.groupby("employee_id"):
        r = grp.iloc[0]
        oldest_assign = grp["module_assigned_date"].dropna().min()
        days_since = int((today - oldest_assign).days) if pd.notna(oldest_assign) else None
        modules_deduped = grp.drop_duplicates(subset="module_name")
        if outlet_name and not pd.Series([r["outlet_name"]]).str.contains(outlet_name, case=False, na=False).iloc[0]:
            continue
        grouped.append({
            "employee_id":              emp_id,
            "full_name":                r["full_name"],
            "outlet_name":              r["outlet_name"],
            "brand_name":               r["brand_name"],
            "join_date":                r["join_date"].strftime("%Y-%m-%d") if pd.notna(r["join_date"]) else None,
            "days_since_oldest_assign": days_since,
            "total_modules_assigned":   len(modules_deduped),
            "modules_not_started":      sorted(modules_deduped["module_name"].dropna().tolist()),
        })
    grouped.sort(key=lambda x: (x["days_since_oldest_assign"] or 0), reverse=True)
    total  = len(grouped)
    result = grouped[:limit]
    return {
        "total":     total,
        "returned":  len(result),
        "employees": result,
        "summary":   f"Ada {total} karyawan yang terdaftar di LMS tapi belum ada progress training sama sekali (total post_test_grade = 0).",
    }


@app.get("/tools/safety_training_not_completed", summary="Karyawan belum selesai training safety")
def safety_training_not_completed(
    outlet_name: Optional[str] = Query(None, description="Filter nama outlet (partial match)"),
    brand_name:  Optional[str] = Query(None, description="Filter nama brand (partial match)"),
    limit:       int           = Query(50,   description="Maks jumlah baris dikembalikan"),
):
    """
    Employees assigned to safety/K3/WSE/Food-Safety modules who haven't completed them.
    Deduplicated by employee_id + module_name.
    Answers: "Siapa belum training safety?"
    """
    df = load_training_df()
    df = df[
        df["module_name"].str.contains(SAFETY_MODULE_PATTERN, case=False, na=False, regex=True) &
        (df["post_test_grade"].isna() | (df["post_test_grade"] < 90))
    ]
    if brand_name:
        df = df[df["brand_name"].str.contains(brand_name, case=False, na=False)]
    df = df.drop_duplicates(subset=["employee_id", "module_name"])
    total  = len(df)
    # by_module aggregation with per-outlet breakdown (top 5 outlets each)
    by_module = []
    for mod_name, mod_grp in df.groupby("module_name"):
        outlets_in_mod = (
            mod_grp.groupby("outlet_name")["employee_id"].count()
            .reset_index().rename(columns={"employee_id": "count"})
            .sort_values("count", ascending=False)
        )
        by_module.append({
            "module_name": mod_name,
            "count": len(mod_grp),
            "top_outlets": [{"outlet_name": r["outlet_name"], "count": int(r["count"])} for _, r in outlets_in_mod.head(5).iterrows()],
        })
    by_module.sort(key=lambda x: x["count"], reverse=True)
    # by_outlet aggregation (top 10)
    by_outlet = (
        df.groupby("outlet_name")["employee_id"].count()
        .reset_index().rename(columns={"employee_id": "count"})
        .sort_values("count", ascending=False)
    )
    total_outlets = len(by_outlet)
    by_outlet_list = [{"outlet_name": r["outlet_name"], "count": int(r["count"])} for _, r in by_outlet.head(10).iterrows()]
    result = _training_rows_by_module(df, outlet_name, limit)
    mod_lines = "; ".join(f"'{m['module_name']}' ({m['count']} karyawan)" for m in by_module[:5])
    outlet_lines = ", ".join(f"{o['outlet_name']} ({o['count']} karyawan)" for o in by_outlet_list[:3])
    return {
        "total":     total,
        "returned":  len(result),
        "employees": result,
        "by_module": by_module,
        "by_outlet": by_outlet_list,
        "summary": (
            f"Ada {total} penugasan modul safety/K3 yang belum diselesaikan, tersebar di {total_outlets} outlet. "
            f"Breakdown per modul: {mod_lines}. "
            f"Outlet dengan gap terbesar: {outlet_lines}. "
            f"Perlu segera ditindaklanjuti — modul safety adalah persyaratan regulasi."
        ),
    }


@app.get("/tools/sop_training_not_completed", summary="Karyawan belum selesai training SOP")
def sop_training_not_completed(
    outlet_name: Optional[str] = Query(None, description="Filter nama outlet (partial match)"),
    brand_name:  Optional[str] = Query(None, description="Filter nama brand (partial match)"),
    limit:       int           = Query(50,   description="Maks jumlah baris dikembalikan"),
):
    """
    Employees assigned to SOP/procedure modules who haven't completed them.
    Deduplicated by employee_id + module_name.
    Answers: "Siapa belum training SOP?"
    """
    df = load_training_df()
    df = df[
        df["module_name"].str.contains(SOP_MODULE_PATTERN, case=False, na=False, regex=True) &
        (df["post_test_grade"].isna() | (df["post_test_grade"] < 90))
    ]
    if brand_name:
        df = df[df["brand_name"].str.contains(brand_name, case=False, na=False)]
    df = df.drop_duplicates(subset=["employee_id", "module_name"])
    total  = len(df)
    # by_module aggregation with per-outlet breakdown (top 5 outlets each)
    by_module = []
    for mod_name, mod_grp in df.groupby("module_name"):
        outlets_in_mod = (
            mod_grp.groupby("outlet_name")["employee_id"].count()
            .reset_index().rename(columns={"employee_id": "count"})
            .sort_values("count", ascending=False)
        )
        by_module.append({
            "module_name": mod_name,
            "count": len(mod_grp),
            "top_outlets": [{"outlet_name": r["outlet_name"], "count": int(r["count"])} for _, r in outlets_in_mod.head(5).iterrows()],
        })
    by_module.sort(key=lambda x: x["count"], reverse=True)
    # by_outlet aggregation (top 10)
    by_outlet = (
        df.groupby("outlet_name")["employee_id"].count()
        .reset_index().rename(columns={"employee_id": "count"})
        .sort_values("count", ascending=False)
    )
    total_outlets = len(by_outlet)
    by_outlet_list = [{"outlet_name": r["outlet_name"], "count": int(r["count"])} for _, r in by_outlet.head(10).iterrows()]
    result = _training_rows_by_module(df, outlet_name, limit)
    # Flag employees who've been employed > 60 days
    long_tenured = sum(1 for e in result if e.get("days_since_join") is not None and e["days_since_join"] > 60)
    return {
        "total":                    total,
        "returned":                 len(result),
        "long_tenured_gt_60_days":  long_tenured,
        "employees":                result,
        "by_module":                by_module,
        "by_outlet":                by_outlet_list,
        "summary": (
            f"Ada {total} penugasan modul SOP/prosedur yang belum diselesaikan, tersebar di {total_outlets} outlet. "
            f"Breakdown per modul: {'; '.join(m['module_name'] + ' (' + str(m['count']) + ' karyawan)' for m in by_module[:5])}. "
            f"Outlet dengan gap terbesar: {', '.join(o['outlet_name'] + ' (' + str(o['count']) + ' karyawan)' for o in by_outlet_list[:3])}. "
            f"{long_tenured} karyawan sudah bekerja > 60 hari belum selesai SOP."
        ),
    }


@app.get("/tools/onboarding_not_completed", summary="Karyawan belum selesai onboarding & sudah > N hari kerja")
def onboarding_not_completed(
    days:        int           = Query(7,    description="Minimal masa kerja dalam hari (default 7)"),
    outlet_name: Optional[str] = Query(None, description="Filter nama outlet (partial match)"),
    brand_name:  Optional[str] = Query(None, description="Filter nama brand (partial match)"),
    limit:       int           = Query(100,  description="Maks jumlah baris dikembalikan"),
):
    """
    Employees who joined more than N days ago, assigned to onboarding/induction modules,
    but post_test_grade is null or < 90. Deduplicated by employee_id + module_name.
    Answers: "Siapa belum selesai modul onboarding minggu ini dan sudah > 7 hari join?"
    """
    df     = load_training_df()
    cutoff = pd.Timestamp(date.today()) - pd.Timedelta(days=days)
    df = df[
        df["join_date"].notna() &
        (df["join_date"] <= cutoff) &
        df["module_name"].str.contains(ONBOARDING_MODULE_PATTERN, case=False, na=False, regex=True) &
        (df["post_test_grade"].isna() | (df["post_test_grade"] < 90))
    ]
    if brand_name:
        df = df[df["brand_name"].str.contains(brand_name, case=False, na=False)]
    df = df.drop_duplicates(subset=["employee_id", "module_name"])
    if outlet_name:
        df = df[df["outlet_name"].str.contains(outlet_name, case=False, na=False)]
    today_ts = pd.Timestamp(date.today())
    # Group by employee to show per-employee module details
    grouped = []
    for emp_id, grp in df.groupby("employee_id"):
        r = grp.iloc[0]
        join_dt = r["join_date"]
        days_since_join = int((today_ts - join_dt).days) if pd.notna(join_dt) else None
        modules = [
            {
                "module_name":     row["module_name"],
                "post_test_grade": float(row["post_test_grade"]) if pd.notna(row["post_test_grade"]) else None,
            }
            for _, row in grp.iterrows()
        ]
        grouped.append({
            "employee_id":    emp_id,
            "full_name":      r["full_name"],
            "outlet_name":    r["outlet_name"],
            "brand_name":     r["brand_name"],
            "join_date":      join_dt.strftime("%Y-%m-%d") if pd.notna(join_dt) else None,
            "days_since_join": days_since_join,
            "modules":        sorted(modules, key=lambda x: x["module_name"]),
        })
    grouped.sort(key=lambda x: (x["days_since_join"] or 0), reverse=True)
    total  = len(grouped)
    result = grouped[:limit]
    return {
        "days":        days,
        "cutoff_date": cutoff.strftime("%Y-%m-%d"),
        "total":       total,
        "returned":    len(result),
        "employees":   result,
        "summary": (
            f"Ada {total} karyawan yang bergabung sebelum {cutoff.strftime('%Y-%m-%d')} "
            f"(lebih dari {days} hari lalu) namun modul onboarding/induction belum selesai."
        ),
    }


@app.get("/tools/training_incomplete_assigned", summary="Karyawan belum menyelesaikan training yang sudah di-assign")
def training_incomplete_assigned(
    outlet_name: Optional[str] = Query(None, description="Filter nama outlet (partial match)"),
    brand_name:  Optional[str] = Query(None, description="Filter nama brand (partial match)"),
    limit:       int           = Query(50,   description="Maks jumlah karyawan dikembalikan"),
):
    """
    Employees with at least one incomplete training assignment (status_training_wajib or
    status_training_optional = 'not yet'), grouped with a list of their incomplete modules.
    Answers: "Siapa saja yang belum menyelesaikan training yang sudah di assign?"
    """
    df = load_training_df()
    df = df[df["post_test_grade"].isna() | (df["post_test_grade"] < 90)]
    if brand_name:
        df = df[df["brand_name"].str.contains(brand_name, case=False, na=False)]
    if outlet_name:
        df = df[df["outlet_name"].str.contains(outlet_name, case=False, na=False)]
    # Deduplicate per employee + module to avoid counting duplicates
    df = df.drop_duplicates(subset=["employee_id", "module_name"])
    def _progress_bucket(g: pd.DataFrame) -> str:
        """Classify employee progress based on their incomplete module states."""
        grades = g["post_test_grade"].dropna()
        pre_grades = g["pre_test_grade"].dropna()
        if len(grades) > 0 and (grades >= 50).any():
            return "high_progress"
        if len(grades) > 0 and (grades > 0).any():
            return "low_progress"
        if len(pre_grades) > 0 and (pre_grades >= 50).any() and len(grades) == 0:
            return "material_done_no_posttest"
        return "not_started"

    # Load full df to get pre_test_grade for bucket logic
    df_full = load_training_df()
    df_full = df_full[df_full["post_test_grade"].isna() | (df_full["post_test_grade"] < 90)]
    if brand_name:
        df_full = df_full[df_full["brand_name"].str.contains(brand_name, case=False, na=False)]
    if outlet_name:
        df_full = df_full[df_full["outlet_name"].str.contains(outlet_name, case=False, na=False)]
    df_full = df_full.drop_duplicates(subset=["employee_id", "module_name"])

    grouped = []
    for emp_id, g in df_full.groupby("employee_id"):
        bucket = _progress_bucket(g)
        grouped.append({
            "employee_id":          emp_id,
            "full_name":            g["full_name"].iloc[0],
            "outlet_name":          g["outlet_name"].iloc[0],
            "brand_name":           g["brand_name"].iloc[0],
            "join_date":            g["join_date"].iloc[0].strftime("%Y-%m-%d") if pd.notna(g["join_date"].iloc[0]) else None,
            "incomplete_modules":   sorted(g["module_name"].dropna().tolist())[:5],
            "mandatory_incomplete": int((g["is_module_mandatory"] == "1").sum()),
            "optional_incomplete":  int((g["is_module_mandatory"] == "0").sum()),
            "total_incomplete":     len(g),
            "progress_bucket":      bucket,
        })
    grouped.sort(key=lambda x: x["total_incomplete"], reverse=True)
    total  = len(grouped)
    result = grouped[:limit]
    # Summaries
    bucket_summary = {}
    for b in ["not_started", "low_progress", "high_progress", "material_done_no_posttest"]:
        bucket_summary[b] = sum(1 for e in grouped if e["progress_bucket"] == b)
    by_outlet_counts = {}
    for e in grouped:
        by_outlet_counts[e["outlet_name"]] = by_outlet_counts.get(e["outlet_name"], 0) + 1
    by_outlet = sorted([{"outlet_name": k, "count": v} for k, v in by_outlet_counts.items()], key=lambda x: x["count"], reverse=True)[:10]
    return {
        "total":          total,
        "returned":       len(result),
        "bucket_summary": bucket_summary,
        "by_outlet":      by_outlet,
        "employees":      result,
        "summary": (
            f"Ada {total} karyawan dari {len(by_outlet)} outlet yang masih memiliki training belum diselesaikan. "
            f"Rincian: {bucket_summary['not_started']} karyawan belum mulai sama sekali, "
            f"{bucket_summary['low_progress']} karyawan progress rendah (belum aktif), "
            f"{bucket_summary['high_progress']} karyawan hampir selesai (perlu dorongan), "
            f"{bucket_summary['material_done_no_posttest']} karyawan selesai materi tapi belum post-test. "
            f"Outlet dengan beban terbesar: {', '.join(o['outlet_name'] + ' (' + str(o['count']) + ' orang)' for o in by_outlet[:3])}."
        ),
    }


@app.get("/tools/training_low_score", summary="Karyawan dengan nilai post-test rendah atau belum ada nilai")
def training_low_score(
    threshold:   int           = Query(90,   description="Batas nilai rendah (default 90)"),
    outlet_name: Optional[str] = Query(None, description="Filter nama outlet (partial match)"),
    brand_name:  Optional[str] = Query(None, description="Filter nama brand (partial match)"),
    limit:       int           = Query(100,  description="Maks jumlah baris dikembalikan"),
):
    """
    Employees with post_test_grade null or below threshold.
    Deduplicated by employee_id + module_name, sorted by score ascending (nulls last).
    Answers: "Siapa training score rendah?"
    """
    df = load_training_df()
    df = df[df["post_test_grade"].isna() | (df["post_test_grade"] < threshold)]
    if brand_name:
        df = df[df["brand_name"].str.contains(brand_name, case=False, na=False)]
    if outlet_name:
        df = df[df["outlet_name"].str.contains(outlet_name, case=False, na=False)]
    df = df.drop_duplicates(subset=["employee_id", "module_name"])
    df = df.sort_values("post_test_grade", ascending=True, na_position="last")
    total = len(df)
    # by_module aggregation to detect systemic issues
    by_module_counts = (
        df.groupby("module_name")["employee_id"].count()
        .reset_index().rename(columns={"employee_id": "count"})
        .sort_values("count", ascending=False)
    )
    by_module = [{"module_name": r["module_name"], "count": int(r["count"])} for _, r in by_module_counts.iterrows()]
    result = []
    for _, r in df.head(limit).iterrows():
        result.append({
            "employee_id":     r["employee_id"],
            "full_name":       r["full_name"],
            "outlet_name":     r["outlet_name"],
            "brand_name":      r["brand_name"],
            "module_name":     r["module_name"],
            "post_test_grade": float(r["post_test_grade"]) if pd.notna(r["post_test_grade"]) else None,
            "join_date":       r["join_date"].strftime("%Y-%m-%d") if pd.notna(r["join_date"]) else None,
        })
    systemic = [m for m in by_module if m["count"] > 3]
    systemic_msg = (
        f" Indikasi masalah sistemik pada modul: {', '.join(m['module_name'] for m in systemic[:3])}."
        if systemic else ""
    )
    return {
        "threshold": threshold,
        "total":     total,
        "returned":  len(result),
        "by_module": by_module,
        "employees": result,
        "summary": (
            f"Ada {total} catatan dengan post_test_grade null atau di bawah {threshold} "
            f"(unik per karyawan per modul).{systemic_msg}"
        ),
    }


@app.get("/tools/training_most_failed", summary="Modul training paling sering gagal")
def training_most_failed(
    top_n: int = Query(5, description="Tampilkan N modul teratas (default 5)"),
):
    """
    Top N modules ranked by number of employees who scored post_test_grade < 90.
    Only counts rows where post_test_grade is not null but < 90.
    Answers: "Training apa paling sering gagal?"
    """
    df = load_training_df()
    failed = df[df["post_test_grade"].notna() & (df["post_test_grade"] < 90)]
    failed = failed.drop_duplicates(subset=["employee_id", "module_name"])
    # Total attempts per module (any non-null post_test_grade)
    all_attempted = df[df["post_test_grade"].notna()].drop_duplicates(subset=["employee_id", "module_name"])
    attempts_by_module = (
        all_attempted.groupby("module_name")["employee_id"].count()
        .reset_index().rename(columns={"employee_id": "total_attempts"})
    )
    grp = (
        failed.groupby("module_name")
        .agg(failed_count=("employee_id", "count"), avg_score=("post_test_grade", "mean"))
        .reset_index()
        .merge(attempts_by_module, on="module_name", how="left")
        .sort_values("failed_count", ascending=False)
        .head(top_n)
    )
    result = [
        {
            "module_name":    r["module_name"],
            "failed_count":   int(r["failed_count"]),
            "total_attempts": int(r["total_attempts"]) if pd.notna(r.get("total_attempts")) else int(r["failed_count"]),
            "fail_rate_pct":  round(r["failed_count"] / r["total_attempts"] * 100, 1) if pd.notna(r.get("total_attempts")) and r["total_attempts"] > 0 else None,
            "avg_score":      round(float(r["avg_score"]), 1) if pd.notna(r["avg_score"]) else None,
        }
        for _, r in grp.iterrows()
    ]
    top = result[0] if result else {}
    module_lines = "; ".join(
        f"'{m['module_name']}' fail rate {m['fail_rate_pct']}% ({m['failed_count']} dari {m['total_attempts']} gagal)"
        for m in result
    )
    return {
        "threshold": 90,
        "modules":   result,
        "summary": (
            f"Top {len(result)} modul dengan fail rate tertinggi: {module_lines}. "
            f"Indikasi konten terlalu teknis atau perlu review soal pada modul dengan fail rate > 30%."
        ),
    }


@app.get("/tools/training_prepost_comparison", summary="Perbandingan rata-rata pre-test vs post-test per modul")
def training_prepost_comparison(
    outlet_name: Optional[str] = Query(None, description="Filter nama outlet (partial match)"),
    brand_name:  Optional[str] = Query(None, description="Filter nama brand (partial match)"),
):
    """
    Compare average pre_test_grade vs post_test_grade per module (rows with pre_test_grade not null).
    Sorted by delta (post - pre) descending.
    Answers: "Perbandingan pre-test vs post-test per modul?"
    """
    df = load_training_df()
    if brand_name:
        df = df[df["brand_name"].str.contains(brand_name, case=False, na=False)]
    if outlet_name:
        df = df[df["outlet_name"].str.contains(outlet_name, case=False, na=False)]
    # Only include rows that have at least a pre_test_grade
    df = df[df["pre_test_grade"].notna()]
    if df.empty:
        return {"modules": [], "summary": "Tidak ada data pre_test_grade yang tercatat."}
    grp = df.groupby("module_name").agg(
        avg_pre  =("pre_test_grade",  "mean"),
        avg_post =("post_test_grade", "mean"),
        count    =("employee_id",     "nunique"),
    ).reset_index()
    grp["delta"] = grp["avg_post"] - grp["avg_pre"]
    grp = grp.sort_values("delta", ascending=False)
    def _improvement_label(delta) -> str:
        if delta is None:
            return "tidak ada data"
        if delta >= 20:
            return "sangat efektif"
        if delta >= 10:
            return "efektif"
        if delta >= 5:
            return "cukup baik"
        return "perlu dievaluasi"

    result = []
    for _, r in grp.iterrows():
        delta = round(float(r["delta"]), 1) if pd.notna(r["delta"]) else None
        result.append({
            "module_name":       r["module_name"],
            "avg_pre_test":      round(float(r["avg_pre"]),  1),
            "avg_post_test":     round(float(r["avg_post"]), 1) if pd.notna(r["avg_post"]) else None,
            "delta":             delta,
            "improvement_label": _improvement_label(delta),
            "employee_count":    int(r["count"]),
        })
    best = result[0] if result else {}
    needs_review = [m["module_name"] for m in result if m["delta"] is not None and m["delta"] < 10]
    top5_lines = "; ".join(
        f"'{m['module_name']}': {m['avg_pre_test']}→{m['avg_post_test']} (+{m['delta']} poin, {m['improvement_label']})"
        for m in result[:5]
    )
    review_msg = f" Modul delta < 10 poin (perlu review konten bulan depan): {', '.join(needs_review[:3])}." if needs_review else ""
    return {
        "total_modules": len(result),
        "modules":       result,
        "summary": (
            f"Perbandingan pre vs post test untuk {len(result)} modul. "
            f"Top 5 peningkatan: {top5_lines}."
            f"{review_msg}"
        ),
    }


@app.get("/tools/get_employee_training", summary="Daftar modul training yang diassign ke karyawan")
def get_employee_training(
    employee_name: Optional[str] = Query(None, description="Nama karyawan (partial match, case-insensitive)"),
    employee_id:   Optional[str] = Query(None, description="Employee ID (exact match)"),
):
    """
    All training modules assigned to a specific employee, looked up by name or ID.
    Answers: "Training apa saja yang diassign ke karyawan XX?"
    """
    df = load_training_df()
    if not employee_name and not employee_id:
        return {"employees": [], "summary": "Harap isi parameter employee_name atau employee_id."}
    if employee_id:
        df = df[df["employee_id"] == employee_id]
    elif employee_name:
        df = df[df["full_name"].str.contains(employee_name, case=False, na=False)]
    if df.empty:
        return {"employees": [], "summary": "Karyawan tidak ditemukan."}
    df = df.drop_duplicates(subset=["employee_id", "module_name"])
    result = []
    for emp_id, grp in df.groupby("employee_id"):
        r = grp.iloc[0]
        modules = []
        for _, row in grp.iterrows():
            modules.append({
                "module_name":          row["module_name"],
                "module_type":          row["module_type"],
                "is_module_mandatory":  row["is_module_mandatory"],
                "module_assigned_date": row["module_assigned_date"].strftime("%Y-%m-%d") if pd.notna(row["module_assigned_date"]) else None,
                "pre_test_grade":       float(row["pre_test_grade"])  if pd.notna(row["pre_test_grade"])  else None,
                "post_test_grade":      float(row["post_test_grade"]) if pd.notna(row["post_test_grade"]) else None,
                "post_test_status":     row["post_test_status"],
            })
        result.append({
            "employee_id":   emp_id,
            "full_name":     r["full_name"],
            "outlet_name":   r["outlet_name"],
            "brand_name":    r["brand_name"],
            "total_modules": len(modules),
            "modules":       sorted(modules, key=lambda x: x["module_name"]),
        })
    total_modules = sum(e["total_modules"] for e in result)
    return {
        "total_employees": len(result),
        "employees":       result,
        "summary":         f"Ditemukan {len(result)} karyawan dengan total {total_modules} modul training yang diassign.",
    }


@app.get("/tools/list_training_modules", summary="Daftar semua modul training (deduplikasi)")
def list_training_modules(
    brand_name:          Optional[str] = Query(None, description="Filter nama brand (partial match)"),
    is_module_mandatory: Optional[str] = Query(None, description="Filter: '1' = wajib, '0' = opsional"),
):
    """
    All unique training module names from the LMS data, optionally filtered.
    Answers: "Apa saja modul training yang ada?"
    """
    df = load_training_df()
    if brand_name:
        df = df[df["brand_name"].str.contains(brand_name, case=False, na=False)]
    if is_module_mandatory is not None:
        df = df[df["is_module_mandatory"] == is_module_mandatory.strip()]
    modules = (
        df[["module_name", "module_type", "is_module_mandatory"]]
        .drop_duplicates(subset="module_name")
        .sort_values("module_name")
    )
    result = [
        {
            "module_name":         r["module_name"],
            "module_type":         r["module_type"],
            "is_module_mandatory": r["is_module_mandatory"],
        }
        for _, r in modules.iterrows()
    ]
    label = "wajib" if is_module_mandatory == "1" else ("opsional" if is_module_mandatory == "0" else "semua")
    return {
        "total_modules": len(result),
        "modules":       result,
        "summary":       f"Terdapat {len(result)} modul training {label} yang terdaftar di LMS.",
    }


@app.get("/tools/training_completion_by_module", summary="Completion rate training per modul")
def training_completion_by_module(
    top_n:      int           = Query(10,   description="Tampilkan N modul terendah"),
    brand_name: Optional[str] = Query(None, description="Filter nama brand (partial match)"),
    sort_by:    str           = Query("asc", description="'asc' = terendah dulu, 'desc' = tertinggi dulu"),
):
    """
    Completion rate per training module with per-outlet breakdown.
    Completion = unique employees with post_test_grade >= 90 / total unique employees assigned.
    Answers: "Berapa % completion rate per modul? Yang paling rendah apa?"
    """
    df = load_training_df()
    if brand_name:
        df = df[df["brand_name"].str.contains(brand_name, case=False, na=False)]
    total_per_module = (
        df.drop_duplicates(subset=["employee_id", "module_name"])
        .groupby("module_name")["employee_id"].count()
        .reset_index().rename(columns={"employee_id": "total_assigned"})
    )
    completed_per_module = (
        df[df["post_test_grade"] >= 90]
        .drop_duplicates(subset=["employee_id", "module_name"])
        .groupby("module_name")["employee_id"].count()
        .reset_index().rename(columns={"employee_id": "completed"})
    )
    grp = total_per_module.merge(completed_per_module, on="module_name", how="left")
    grp["completed"]           = grp["completed"].fillna(0).astype(int)
    grp["not_completed"]       = grp["total_assigned"] - grp["completed"]
    grp["completion_rate_pct"] = (grp["completed"] / grp["total_assigned"] * 100).round(1)
    ascending = sort_by != "desc"
    grp = grp.sort_values("completion_rate_pct", ascending=ascending).head(top_n)
    result = []
    for _, r in grp.iterrows():
        mod_df = df[df["module_name"] == r["module_name"]].drop_duplicates(subset=["employee_id", "outlet_name"])
        total_by_outlet = mod_df.groupby("outlet_name")["employee_id"].count().reset_index().rename(columns={"employee_id": "total_assigned"})
        comp_by_outlet  = (
            df[(df["module_name"] == r["module_name"]) & (df["post_test_grade"] >= 90)]
            .drop_duplicates(subset=["employee_id", "outlet_name"])
            .groupby("outlet_name")["employee_id"].count()
            .reset_index().rename(columns={"employee_id": "completed"})
        )
        outlet_grp = total_by_outlet.merge(comp_by_outlet, on="outlet_name", how="left")
        outlet_grp["completed"]           = outlet_grp["completed"].fillna(0).astype(int)
        outlet_grp["completion_rate_pct"] = (outlet_grp["completed"] / outlet_grp["total_assigned"] * 100).round(1)
        outlet_grp = outlet_grp.sort_values("completion_rate_pct")
        result.append({
            "module_name":        r["module_name"],
            "total_assigned":     int(r["total_assigned"]),
            "completed":          int(r["completed"]),
            "not_completed":      int(r["not_completed"]),
            "completion_rate_pct": float(r["completion_rate_pct"]),
            "by_outlet": [
                {
                    "outlet_name":        row["outlet_name"],
                    "total_assigned":     int(row["total_assigned"]),
                    "completed":          int(row["completed"]),
                    "completion_rate_pct": float(row["completion_rate_pct"]),
                }
                for _, row in outlet_grp.iterrows()
            ],
        })
    lowest = result[0] if result else {}
    return {
        "total_modules": len(result),
        "modules":       result,
        "summary": (
            f"Modul dengan completion rate {'terendah' if ascending else 'tertinggi'}: "
            f"'{lowest.get('module_name')}' — {lowest.get('completion_rate_pct')}% "
            f"({lowest.get('completed')} dari {lowest.get('total_assigned')} karyawan selesai)."
        ),
    }


@app.get("/tools/competency_gap_by_role", summary="Gap kompetensi berdasarkan role dan modul training")
def competency_gap_by_role(
    top_n:       int           = Query(10,   description="Tampilkan N gap teratas"),
    module_name: Optional[str] = Query(None, description="Filter nama modul (partial match)"),
):
    """
    Identify which job positions have the highest fail rates per training module.
    Joins training data with employee data on employee_id to get job_position.
    Answers: "Role apa yang paling banyak fail post-test di modul tertentu?"
    """
    df_train = load_training_df()
    df_emp   = load_df()
    if module_name:
        df_train = df_train[df_train["module_name"].str.contains(module_name, case=False, na=False)]
    # Only rows with a post_test result
    df_attempted = df_train[df_train["post_test_grade"].notna()].drop_duplicates(subset=["employee_id", "module_name"])
    # Join on normalized full_name (employee_id formats differ between CSVs)
    df_emp["full_name_norm"]    = df_emp["full_name"].str.strip().str.lower()
    df_attempted["full_name_norm"] = df_attempted["full_name"].str.strip().str.lower()
    role_map = df_emp[["full_name_norm", "job_position"]].drop_duplicates(subset="full_name_norm")
    df_attempted = df_attempted.merge(role_map, on="full_name_norm", how="left")
    df_attempted = df_attempted[df_attempted["job_position"].notna()]
    if df_attempted.empty:
        return {"gaps": [], "summary": "Tidak ada data yang dapat dianalisis."}
    total_by_role_mod = (
        df_attempted.groupby(["job_position", "module_name"])["employee_id"].count()
        .reset_index().rename(columns={"employee_id": "total_attempted"})
    )
    failed = df_attempted[df_attempted["post_test_grade"] < 90]
    failed_by_role_mod = (
        failed.groupby(["job_position", "module_name"])["employee_id"].count()
        .reset_index().rename(columns={"employee_id": "failed_count"})
    )
    grp = total_by_role_mod.merge(failed_by_role_mod, on=["job_position", "module_name"], how="left")
    grp["failed_count"]  = grp["failed_count"].fillna(0).astype(int)
    grp["fail_rate_pct"] = (grp["failed_count"] / grp["total_attempted"] * 100).round(1)
    grp = grp.sort_values("fail_rate_pct", ascending=False).head(top_n)
    result = [
        {
            "job_position":    r["job_position"],
            "module_name":     r["module_name"],
            "total_attempted": int(r["total_attempted"]),
            "failed_count":    int(r["failed_count"]),
            "fail_rate_pct":   float(r["fail_rate_pct"]),
        }
        for _, r in grp.iterrows()
    ]
    top = result[0] if result else {}
    return {
        "total": len(result),
        "gaps":  result,
        "summary": (
            f"Gap kompetensi terbesar: '{top.get('job_position')}' pada modul '{top.get('module_name')}' "
            f"— fail rate {top.get('fail_rate_pct')}% "
            f"({top.get('failed_count')} dari {top.get('total_attempted')} karyawan gagal)."
        ),
    }


@app.get("/tools/ld_key_insights", summary="Key insight L&D: green news dan red news")
def ld_key_insights(
    brand_name: Optional[str] = Query(None, description="Filter nama brand (partial match)"),
):
    """
    Key L&D insights derived from current data snapshot: green news (positives) and
    red news (areas needing attention).
    Answers: "Berikan key insight L&D bulan ini – green news dan red news."
    """
    df = load_training_df()
    if brand_name:
        df = df[df["brand_name"].str.contains(brand_name, case=False, na=False)]

    # Completion rate per module
    total_per_mod = (
        df.drop_duplicates(subset=["employee_id", "module_name"])
        .groupby("module_name")["employee_id"].count().reset_index().rename(columns={"employee_id": "total"})
    )
    comp_per_mod = (
        df[df["post_test_grade"] >= 90].drop_duplicates(subset=["employee_id", "module_name"])
        .groupby("module_name")["employee_id"].count().reset_index().rename(columns={"employee_id": "completed"})
    )
    mod_grp = total_per_mod.merge(comp_per_mod, on="module_name", how="left")
    mod_grp["completed"]           = mod_grp["completed"].fillna(0).astype(int)
    mod_grp["completion_rate_pct"] = (mod_grp["completed"] / mod_grp["total"] * 100).round(1)

    # Pre-post delta per module
    df_pre = df[df["pre_test_grade"].notna()]
    prepost = df_pre.groupby("module_name").agg(avg_pre=("pre_test_grade","mean"), avg_post=("post_test_grade","mean")).reset_index()
    prepost["delta"] = prepost["avg_post"] - prepost["avg_pre"]

    # Fail rate per module
    attempted = df[df["post_test_grade"].notna()].drop_duplicates(subset=["employee_id","module_name"])
    failed    = attempted[attempted["post_test_grade"] < 90]
    fail_grp  = attempted.groupby("module_name")["employee_id"].count().reset_index().rename(columns={"employee_id":"total_att"})
    fail_cnt  = failed.groupby("module_name")["employee_id"].count().reset_index().rename(columns={"employee_id":"failed_cnt"})
    fail_rate = fail_grp.merge(fail_cnt, on="module_name", how="left")
    fail_rate["failed_cnt"]   = fail_rate["failed_cnt"].fillna(0).astype(int)
    fail_rate["fail_rate_pct"] = (fail_rate["failed_cnt"] / fail_rate["total_att"] * 100).round(1)

    green_news = []
    red_news   = []

    # GREEN: high completion modules
    high_comp = mod_grp[mod_grp["completion_rate_pct"] >= 70].sort_values("completion_rate_pct", ascending=False)
    for _, r in high_comp.head(3).iterrows():
        green_news.append({"type": "completion", "message": f"'{r['module_name']}' completion rate tinggi: {r['completion_rate_pct']}%"})

    # GREEN: high improvement modules (delta >= 20)
    high_delta = prepost[prepost["delta"].notna() & (prepost["delta"] >= 20)].sort_values("delta", ascending=False)
    for _, r in high_delta.head(2).iterrows():
        green_news.append({"type": "improvement", "message": f"'{r['module_name']}' delta pre→post tertinggi: +{round(r['delta'],1)} poin (sangat efektif)"})

    # RED: low completion modules
    low_comp = mod_grp[mod_grp["completion_rate_pct"] < 50].sort_values("completion_rate_pct")
    for _, r in low_comp.head(3).iterrows():
        red_news.append({"type": "completion", "message": f"'{r['module_name']}' completion rate rendah: {r['completion_rate_pct']}% ({int(r['completed'])} dari {int(r['total'])} selesai)"})

    # RED: high fail rate modules
    high_fail = fail_rate[fail_rate["fail_rate_pct"] > 30].sort_values("fail_rate_pct", ascending=False)
    for _, r in high_fail.head(3).iterrows():
        red_news.append({"type": "fail_rate", "message": f"'{r['module_name']}' fail rate tinggi: {r['fail_rate_pct']}% ({int(r['failed_cnt'])} dari {int(r['total_att'])} gagal)"})

    # RED: employees below threshold (post_test_grade not null but still < 90)
    below_thresh = df[df["post_test_grade"].notna() & (df["post_test_grade"] < 90)].drop_duplicates(subset="employee_id")
    red_news.append({"type": "below_threshold", "message": f"{len(below_thresh)} karyawan masih di bawah threshold post-test (nilai ada tapi < 90)"})

    return {
        "green_news": green_news,
        "red_news":   red_news,
        "summary": (
            f"Key Insight L&D: {len(green_news)} green news (hal positif), "
            f"{len(red_news)} red news (perlu tindak lanjut). "
            f"Modul terbaik: '{high_comp.iloc[0]['module_name'] if not high_comp.empty else '-'}'. "
            f"Modul perlu perhatian: '{low_comp.iloc[0]['module_name'] if not low_comp.empty else '-'}'."
        ),
    }


@app.get("/tools/weekly_ld_digest", summary="Weekly L&D digest: completion rate, overdue, modul bermasalah")
def weekly_ld_digest(
    brand_name:   Optional[str] = Query(None, description="Filter nama brand (partial match)"),
    overdue_days: int           = Query(14,   description="Ambang hari assign dianggap overdue (default 14)"),
):
    """
    Weekly L&D digest showing current module completion rates, overdue assignments,
    and modules needing attention. Note: week-over-week comparison unavailable (single snapshot).
    Answers: "Generate weekly L&D digest: completion rate, training overdue, modul drop."
    """
    df = load_training_df()
    if brand_name:
        df = df[df["brand_name"].str.contains(brand_name, case=False, na=False)]
    today_ts = pd.Timestamp(date.today())

    # Module completion rates
    total_per_mod = (
        df.drop_duplicates(subset=["employee_id", "module_name"])
        .groupby("module_name")["employee_id"].count().reset_index().rename(columns={"employee_id": "total"})
    )
    comp_per_mod = (
        df[df["post_test_grade"] >= 90].drop_duplicates(subset=["employee_id", "module_name"])
        .groupby("module_name")["employee_id"].count().reset_index().rename(columns={"employee_id": "completed"})
    )
    mod_grp = total_per_mod.merge(comp_per_mod, on="module_name", how="left")
    mod_grp["completed"]           = mod_grp["completed"].fillna(0).astype(int)
    mod_grp["completion_rate_pct"] = (mod_grp["completed"] / mod_grp["total"] * 100).round(1)
    mod_grp["status"] = mod_grp["completion_rate_pct"].apply(
        lambda x: "baik" if x >= 70 else ("perlu perhatian" if x >= 50 else "kritis")
    )
    module_completion = [
        {"module_name": r["module_name"], "completion_rate_pct": float(r["completion_rate_pct"]), "status": r["status"]}
        for _, r in mod_grp.sort_values("completion_rate_pct").head(30).iterrows()
    ]

    # Overdue assignments
    cutoff = today_ts - pd.Timedelta(days=overdue_days)
    overdue_df = df[
        df["module_assigned_date"].notna() &
        (df["module_assigned_date"] <= cutoff) &
        (df["post_test_grade"].isna() | (df["post_test_grade"] < 90))
    ].drop_duplicates(subset=["employee_id", "module_name"])
    overdue_list = [
        {
            "employee_id":  r["employee_id"],
            "full_name":    r["full_name"],
            "outlet_name":  r["outlet_name"],
            "module_name":  r["module_name"],
            "days_overdue": int((today_ts - r["module_assigned_date"]).days),
        }
        for _, r in overdue_df.sort_values("module_assigned_date").head(20).iterrows()
    ]

    modules_needing_attention = [m["module_name"] for m in module_completion if m["status"] in ("perlu perhatian", "kritis")]

    return {
        "digest_date":              today_ts.strftime("%Y-%m-%d"),
        "overdue_days_threshold":   overdue_days,
        "module_completion":        module_completion,
        "overdue_assignments":      overdue_list,
        "modules_needing_attention": modules_needing_attention,
        "summary": (
            f"Weekly L&D Digest ({today_ts.strftime('%Y-%m-%d')}): "
            f"{len(module_completion)} modul terpantau, "
            f"{len(overdue_list)} penugasan overdue > {overdue_days} hari, "
            f"{len(modules_needing_attention)} modul perlu perhatian."
        ),
    }


@app.get("/tools/list_employee_training_modules", summary="Daftar modul training yang di-assign ke karyawan tertentu")
def list_employee_training_modules(
    name_or_id: str = Query(..., description="Nama atau employee_id karyawan"),
):
    """
    Summary of all training modules assigned to a specific employee: total, completed, incomplete.
    Answers: "Ada modul apa saja yang sudah di assign ke karyawan X?"
    """
    df = load_training_df()
    # Match by employee_id (exact) or full_name (partial, case-insensitive)
    mask = (df["employee_id"] == name_or_id) | df["full_name"].str.contains(name_or_id, case=False, na=False)
    df   = df[mask].drop_duplicates(subset=["employee_id", "module_name"])
    if df.empty:
        return {"employees": [], "summary": f"Karyawan '{name_or_id}' tidak ditemukan di data training."}
    results = []
    for emp_id, grp in df.groupby("employee_id"):
        r = grp.iloc[0]
        modules = []
        for _, row in grp.iterrows():
            grade = row["post_test_grade"] if pd.notna(row["post_test_grade"]) else None
            pre   = row["pre_test_grade"]  if pd.notna(row["pre_test_grade"])  else None
            if grade is not None and grade >= 90:
                status = "completed"
            elif grade is None and pre is None:
                status = "not_started"
            else:
                status = "incomplete"
            modules.append({
                "module_name":         row["module_name"],
                "module_type":         row["module_type"],
                "is_mandatory":        row["is_module_mandatory"] == "1",
                "module_assigned_date": row["module_assigned_date"].strftime("%Y-%m-%d") if pd.notna(row["module_assigned_date"]) else None,
                "pre_test_grade":      float(pre) if pre is not None else None,
                "post_test_grade":     float(grade) if grade is not None else None,
                "status":              status,
            })
        modules.sort(key=lambda x: x["module_name"])
        total_assigned   = len(modules)
        total_completed  = sum(1 for m in modules if m["status"] == "completed")
        total_incomplete = total_assigned - total_completed
        results.append({
            "employee_id":     emp_id,
            "full_name":       r["full_name"],
            "outlet_name":     r["outlet_name"],
            "brand_name":      r["brand_name"],
            "total_assigned":  total_assigned,
            "total_completed": total_completed,
            "total_incomplete": total_incomplete,
            "modules":         modules,
            "summary": (
                f"{r['full_name']} sudah di-assign {total_assigned} modul: "
                f"{total_completed} selesai, {total_incomplete} belum selesai."
            ),
        })
    overall_summary = f"Ditemukan {len(results)} karyawan cocok dengan '{name_or_id}'."
    if len(results) == 1:
        overall_summary = results[0]["summary"]
    return {
        "total_employees": len(results),
        "employees":       results,
        "summary":         overall_summary,
    }


# ══════════════════════════════════════════════════════════════════
# EXPORT — /export (file download) + /tools/get_export_link (MCP)
# ══════════════════════════════════════════════════════════════════

TOOL_FUNCTIONS = {
    "total_active_employees":   total_active_employees,
    "employee_summary":         employee_summary,
    "headcount_per_outlet":     headcount_per_outlet,
    "headcount_per_level":      headcount_per_level,
    "headcount_per_branch":     headcount_per_branch,
    "contracts_expiring":       contracts_expiring,
    "contracts_missing_enddate":contracts_missing_enddate,
    "probation_employees":      probation_employees,
    "new_hires":                new_hires,
    "resigned_employees":       resigned_employees,
    "resign_by_position":       resign_by_position,
    "turnover_per_outlet":      turnover_per_outlet,
    "search_employee":          search_employee,
    "list_by_department":       list_by_department,
    "list_by_outlet":           list_by_outlet,
    "list_all_employees":       list_all_employees,
    "list_active_by_status":    list_active_by_status,
    "list_employees_by_join_year": list_employees_by_join_year,
    "unassigned_employees":     unassigned_employees,
    "outlets_without_leader":   outlets_without_leader,
    "training_wajib_not_completed":  training_wajib_not_completed,
    "training_completion_by_outlet": training_completion_by_outlet,
    "training_not_started":          training_not_started,
    "safety_training_not_completed": safety_training_not_completed,
    "sop_training_not_completed":    sop_training_not_completed,
    "onboarding_not_completed":      onboarding_not_completed,
    "training_incomplete_assigned":  training_incomplete_assigned,
    "training_low_score":            training_low_score,
    "training_most_failed":          training_most_failed,
    "training_prepost_comparison":   training_prepost_comparison,
    "get_employee_training":              get_employee_training,
    "list_training_modules":             list_training_modules,
    "training_completion_by_module":     training_completion_by_module,
    "competency_gap_by_role":            competency_gap_by_role,
    "ld_key_insights":                   ld_key_insights,
    "weekly_ld_digest":                  weekly_ld_digest,
    "list_employee_training_modules":    list_employee_training_modules,
}

# Maps tool name to the response key holding the main exportable list
TOOL_ARRAY_KEY = {
    "headcount_per_outlet":          "outlets",
    "headcount_per_level":           "levels",
    "headcount_per_branch":          "branches",
    "contracts_expiring":            "contracts",
    "contracts_missing_enddate":     "employees",
    "probation_employees":           "employees",
    "new_hires":                     "employees",
    "resigned_employees":            "employees",
    "resign_by_position":            "positions",
    "turnover_per_outlet":           "outlets",
    "search_employee":               "employees",
    "list_by_department":            "employees",
    "list_by_outlet":                "employees",
    "list_all_employees":            "employees",
    "list_employees_by_join_year":   "employees",
    "unassigned_employees":          "employees",
    "outlets_without_leader":        "outlets",
    "training_wajib_not_completed":  "employees",
    "training_completion_by_outlet": "outlets",
    "training_not_started":          "employees",
    "safety_training_not_completed": "employees",
    "sop_training_not_completed":    "employees",
    "onboarding_not_completed":      "employees",
    "training_incomplete_assigned":  "employees",
    "training_low_score":            "employees",
    "training_most_failed":          "modules",
    "training_prepost_comparison":   "modules",
    "get_employee_training":              "employees",
    "list_training_modules":             "modules",
    "training_completion_by_module":     "modules",
    "competency_gap_by_role":            "gaps",
    "ld_key_insights":                   "green_news",
    "weekly_ld_digest":                  "module_completion",
    "list_employee_training_modules":    "employees",
}


def _call_tool_for_export(tool_name: str, raw_params: dict):
    """Call a tool function by name, injecting only the params it accepts."""
    fn = TOOL_FUNCTIONS.get(tool_name)
    if fn is None:
        return None
    sig = inspect.signature(fn)
    kwargs = {}
    for param_name, param in sig.parameters.items():
        if param_name in raw_params and raw_params[param_name] is not None:
            kwargs[param_name] = raw_params[param_name]
        else:
            default = param.default
            if hasattr(default, "default"):  # FastAPI FieldInfo
                kwargs[param_name] = default.default
            elif default is not inspect.Parameter.empty:
                kwargs[param_name] = default
            else:
                kwargs[param_name] = None
    return fn(**kwargs)


def _extract_rows(result: dict, tool_name: str) -> list:
    """Extract the main list from a tool response and flatten nested structures."""
    # list_active_by_status returns {status: [employees], ...}
    if tool_name == "list_active_by_status":
        rows = []
        for status, items in result.items():
            if isinstance(items, list):
                for emp in items:
                    rows.append({**emp, "employment_status_group": status})
        return rows

    # get_employee_training: flatten one row per module
    if tool_name == "get_employee_training":
        rows = []
        for emp in result.get("employees", []):
            base = {k: v for k, v in emp.items() if k != "modules"}
            for module in emp.get("modules", []):
                rows.append({**base, **module})
        return rows

    # training_incomplete_assigned: join incomplete_modules list as string
    if tool_name == "training_incomplete_assigned":
        rows = []
        for emp in result.get("employees", []):
            row = {k: v for k, v in emp.items() if k != "incomplete_modules"}
            row["incomplete_modules"] = ", ".join(emp.get("incomplete_modules", []))
            rows.append(row)
        return rows

    # training_wajib_not_completed: join incomplete_mandatory_modules list as string
    if tool_name == "training_wajib_not_completed":
        rows = []
        for emp in result.get("employees", []):
            row = {k: v for k, v in emp.items() if k != "incomplete_mandatory_modules"}
            row["incomplete_mandatory_modules"] = ", ".join(emp.get("incomplete_mandatory_modules", []))
            rows.append(row)
        return rows

    array_key = TOOL_ARRAY_KEY.get(tool_name)
    if array_key and array_key in result:
        return result[array_key]

    # Fallback: first list value in response
    for v in result.values():
        if isinstance(v, list):
            return v

    return [result]


def _build_export_params(
    outlet_name, brand_name, limit, top_n, months, days, year,
    name, department, threshold, employee_name, employee_id,
    is_module_mandatory, employment_status,
) -> dict:
    return {
        "outlet_name": outlet_name, "brand_name": brand_name, "limit": limit,
        "top_n": top_n, "months": months, "days": days, "year": year,
        "name": name, "department": department, "threshold": threshold,
        "employee_name": employee_name, "employee_id": employee_id,
        "is_module_mandatory": is_module_mandatory,
        "employment_status": employment_status,
    }


@app.get("/export", include_in_schema=False)
def export_data(
    tool:                str           = Query(...,   description="Tool name"),
    format:              str           = Query("csv", description="'csv' or 'excel'"),
    outlet_name:         Optional[str] = Query(None),
    brand_name:          Optional[str] = Query(None),
    limit:               Optional[int] = Query(500),
    top_n:               Optional[int] = Query(None),
    months:              Optional[int] = Query(None),
    days:                Optional[int] = Query(None),
    year:                Optional[int] = Query(None),
    name:                Optional[str] = Query(None),
    department:          Optional[str] = Query(None),
    threshold:           Optional[int] = Query(None),
    employee_name:       Optional[str] = Query(None),
    employee_id:         Optional[str] = Query(None),
    is_module_mandatory: Optional[str] = Query(None),
    employment_status:   Optional[str] = Query(None),
):
    if tool not in TOOL_FUNCTIONS:
        return JSONResponse({"error": f"Tool '{tool}' tidak ditemukan."}, status_code=404)

    raw_params = _build_export_params(
        outlet_name, brand_name, limit, top_n, months, days, year,
        name, department, threshold, employee_name, employee_id,
        is_module_mandatory, employment_status,
    )
    result = _call_tool_for_export(tool, raw_params)
    if result is None:
        return JSONResponse({"error": "Tool gagal dijalankan."}, status_code=500)

    rows = _extract_rows(result, tool)
    filename = f"{tool}_{date.today().strftime('%Y%m%d')}"

    if format.lower() == "excel":
        df = pd.DataFrame(rows)
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Data")
        return Response(
            content=buf.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}.xlsx"},
        )
    else:
        df = pd.DataFrame(rows)
        return Response(
            content=df.to_csv(index=False),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}.csv"},
        )


@app.get("/tools/get_export_link", summary="Buat link download ekspor data")
def get_export_link(
    tool_name:           str           = Query(...,     description="Nama tool yang sebelumnya digunakan"),
    format:              str           = Query("excel", description="'csv' atau 'excel'"),
    outlet_name:         Optional[str] = Query(None),
    brand_name:          Optional[str] = Query(None),
    limit:               Optional[int] = Query(500),
    top_n:               Optional[int] = Query(None),
    months:              Optional[int] = Query(None),
    days:                Optional[int] = Query(None),
    year:                Optional[int] = Query(None),
    name:                Optional[str] = Query(None),
    department:          Optional[str] = Query(None),
    threshold:           Optional[int] = Query(None),
    employee_name:       Optional[str] = Query(None),
    employee_id:         Optional[str] = Query(None),
    is_module_mandatory: Optional[str] = Query(None),
    employment_status:   Optional[str] = Query(None),
):
    """
    Returns a download URL for exporting tool data as CSV or Excel.
    Call with the same tool_name and filter params as the previous tool call.
    Answers: "Export ke excel", "Download data ini", "Simpan sebagai CSV"
    """
    if tool_name not in TOOL_FUNCTIONS:
        return {"error": f"Tool '{tool_name}' tidak ditemukan.", "summary": "Tool tidak valid."}

    base = OPENAPI_SCHEMA["servers"][0]["url"]
    params: dict = {"tool": tool_name, "format": format}
    for k, v in [
        ("outlet_name", outlet_name), ("brand_name", brand_name),
        ("limit", limit), ("top_n", top_n), ("months", months),
        ("days", days), ("year", year), ("name", name),
        ("department", department), ("threshold", threshold),
        ("employee_name", employee_name), ("employee_id", employee_id),
        ("is_module_mandatory", is_module_mandatory),
        ("employment_status", employment_status),
    ]:
        if v is not None:
            params[k] = str(v)

    ext = "xlsx" if format.lower() == "excel" else "csv"
    filename = f"{tool_name}_{date.today().strftime('%Y%m%d')}.{ext}"
    download_url = f"{base}/export?{urlencode(params)}"

    return {
        "download_url": download_url,
        "filename":     filename,
        "format":       format,
        "summary":      f"Klik link berikut untuk mengunduh: [{filename}]({download_url})",
    }