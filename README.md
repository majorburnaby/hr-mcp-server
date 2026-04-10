# HR Employee MCP Server v2.0.0

FastAPI server yang meng-expose data karyawan sebagai **31 MCP tools** untuk integrasi dengan Dify.  
Di-deploy di Vercel, terhubung ke Dify sebagai Custom Tool via OpenAPI schema.

---

## Struktur Project

```
hr-mcp-server/
├── app/
│   └── main.py              # FastAPI app — semua 31 tools
├── data/
│   └── employee_data.csv    # Dataset karyawan (wajib di-commit!)
├── requirements.txt
├── vercel.json
└── README.md
```

---

## Quick Start (Local)

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Buka **http://localhost:8000/docs** untuk test semua tools secara interaktif via Swagger UI.

---

## Deploy ke Vercel

### Step 1 — Push ke GitHub

```bash
git init
git add .
git commit -m "HR MCP Server v2.0.0"
git remote add origin https://github.com/YOUR_USER/hr-mcp-server.git
git push -u origin main
```

> **Penting:** Pastikan folder `data/` ikut di-commit. File CSV adalah sumber data utama.

### Step 2 — Import ke Vercel

1. Buka https://vercel.com → **New Project**
2. Import repo GitHub kamu
3. Framework: pilih **Other**
4. Root directory: `/` (default)
5. Klik **Deploy**

Server akan live di: `https://hr-mcp-server.vercel.app`

---

## Integrasi ke Dify

### Step 1 — Tambah Custom Tool

1. Di Dify, masuk ke **Tools → Custom Tools → Create Tool**
2. Pilih **Import from OpenAPI Schema**
3. Masukkan URL:
   ```
   https://hr-mcp-server.vercel.app/openapi.json
   ```
4. Klik **Import** — semua 31 tools akan muncul otomatis.

### Step 2 — Tambahkan ke Agent/Chatflow

1. Buka Agent atau Chatflow kamu
2. Di bagian **Tools**, aktifkan tools HR yang diinginkan
3. Tambahkan system prompt berikut:

```
Kamu adalah asisten HR yang membantu menjawab pertanyaan tentang data karyawan.
Gunakan tools yang tersedia untuk mengambil data terkini.
Jawab selalu dalam Bahasa Indonesia yang natural dan informatif.
Sertakan angka spesifik dari data, bukan perkiraan.
Jika pertanyaan tidak bisa dijawab dari data yang ada, jelaskan datanya tidak tersedia.
```

---

## 31 Tools — Referensi Lengkap

### Group 1 — Headcount & Summary

| Tool | Endpoint | Contoh Pertanyaan |
|---|---|---|
| `total_active_employees` | `GET /tools/total_active_employees` | "Berapa total karyawan aktif?" |
| `employee_summary` | `GET /tools/employee_summary` | "Ringkasan data karyawan", "Berapa permanent vs kontrak?" |
| `headcount_per_outlet` | `GET /tools/headcount_per_outlet` | "Berapa karyawan per outlet?" |
| `headcount_per_level` | `GET /tools/headcount_per_level` | "Berapa karyawan per level?" |
| `headcount_per_branch` | `GET /tools/headcount_per_branch` | "Brand mana paling banyak karyawan?" |

### Group 2 — Contracts & Lifecycle

| Tool | Endpoint | Contoh Pertanyaan |
|---|---|---|
| `contracts_expiring` | `GET /tools/contracts_expiring` | "Siapa kontrak habis bulan ini?", "Kontrak habis dalam 30 hari?" |
| `contracts_missing_enddate` | `GET /tools/contracts_missing_enddate` | "Siapa belum tanda tangan kontrak?" |
| `probation_employees` | `GET /tools/probation_employees` | "Siapa masih probation?" |
| `new_hires` | `GET /tools/new_hires` | "Siapa karyawan baru bulan ini?" |

### Group 3 — Resign & Turnover

| Tool | Endpoint | Contoh Pertanyaan |
|---|---|---|
| `resigned_employees` | `GET /tools/resigned_employees` | "Siapa yang sudah resign?", "Berapa yang resign bulan ini?" |
| `resign_by_position` | `GET /tools/resign_by_position` | "Posisi apa paling banyak resign?" |
| `turnover_per_outlet` | `GET /tools/turnover_per_outlet` | "Outlet mana turnover tinggi?" |

### Group 4 — Search & Roster

| Tool | Endpoint | Contoh Pertanyaan |
|---|---|---|
| `search_employee` | `GET /tools/search_employee?name=Andi` | "Cari data karyawan Andi" |
| `list_by_department` | `GET /tools/list_by_department?department=Operations` | "Karyawan di department Operations?" |
| `list_by_outlet` | `GET /tools/list_by_outlet?outlet=Gandaria` | "Karyawan yang ada di Gandaria?" |
| `list_all_employees` | `GET /tools/list_all_employees` | "Siapa saja karyawan aktif?" |
| `list_active_by_status` | `GET /tools/list_active_by_status` | "Berapa permanent vs kontrak dan siapa saja?" |
| `list_employees_by_join_year` | `GET /tools/list_employees_by_join_year?year=2024` | "Siapa yang masuk tahun 2024?" |

### Group 5 — Assignment Gaps

| Tool | Endpoint | Contoh Pertanyaan |
|---|---|---|
| `unassigned_employees` | `GET /tools/unassigned_employees?check=outlet` | "Siapa belum assign outlet/jabatan/SPV?" |
| `outlets_without_leader` | `GET /tools/outlets_without_leader` | "Outlet mana belum ada leader?" |

### Group 6 — Training

> Data dari `data/all_employee_training_data.csv`

| Tool | Endpoint | Contoh Pertanyaan |
|---|---|---|
| `training_wajib_not_completed` | `GET /tools/training_wajib_not_completed` | "Siapa belum training wajib?" |
| `training_completion_by_outlet` | `GET /tools/training_completion_by_outlet` | "Outlet mana training rendah?" |
| `certification_not_completed` | `GET /tools/certification_not_completed` | "Siapa belum sertifikasi?" |
| `training_not_started` | `GET /tools/training_not_started` | "Siapa belum training tapi sudah kerja?" |
| `training_low_score` | `GET /tools/training_low_score` | "Siapa training score rendah?" |
| `training_most_failed` | `GET /tools/training_most_failed` | "Training apa paling sering gagal?" |
| `role_certification_not_completed` | `GET /tools/role_certification_not_completed` | "Siapa belum sertifikasi role?" |
| `training_not_started_3months` | `GET /tools/training_not_started_3months` | "Siapa belum training tapi sudah 3 bulan kerja?" |
| `leader_training_not_completed` | `GET /tools/leader_training_not_completed` | "Siapa leader belum training leader?" |
| `safety_training_not_completed` | `GET /tools/safety_training_not_completed` | "Siapa belum training safety?" |
| `sop_training_not_completed` | `GET /tools/sop_training_not_completed` | "Siapa belum training SOP?" |

---

## Query Parameters Detail

### `contracts_expiring`
| Parameter | Tipe | Default | Keterangan |
|---|---|---|---|
| `month` | int | bulan ini | Bulan 1–12 |
| `year` | int | tahun ini | Contoh: 2026 |
| `within_days` | int | — | Jika diisi, mengabaikan month/year |

### `new_hires`
| Parameter | Tipe | Default | Keterangan |
|---|---|---|---|
| `month` | int | bulan ini | Bulan bergabung |
| `year` | int | tahun ini | Tahun bergabung |
| `within_days` | int | — | N hari terakhir |

### `resigned_employees`
| Parameter | Tipe | Default | Keterangan |
|---|---|---|---|
| `month` | int | — | Filter bulan resign |
| `year` | int | — | Filter tahun resign |

### `resign_by_position`
| Parameter | Tipe | Default | Keterangan |
|---|---|---|---|
| `top_n` | int | 10 | Tampilkan N posisi teratas |
| `year` | int | — | Filter tahun resign |

### `turnover_per_outlet`
| Parameter | Tipe | Default | Keterangan |
|---|---|---|---|
| `year` | int | — | Kosong = semua periode |

### `probation_employees`
| Parameter | Tipe | Default | Keterangan |
|---|---|---|---|
| `probation_months` | int | 3 | Durasi probasi dalam bulan |

### `unassigned_employees`
| Parameter | Tipe | Default | Keterangan |
|---|---|---|---|
| `check` | string | `outlet` | `outlet` / `job_position` / `supervisor` |
| `active_only` | bool | `true` | Filter hanya karyawan aktif |

### `headcount_per_outlet`, `headcount_per_level`, `headcount_per_branch`, `list_by_department`, `list_by_outlet`
| Parameter | Tipe | Default | Keterangan |
|---|---|---|---|
| `active_only` | bool | `true` | Filter hanya karyawan aktif |

---

## Pertanyaan yang Belum Bisa Dijawab

Pertanyaan berikut memerlukan data tambahan yang tidak ada di CSV saat ini:

| Pertanyaan | Data yang Dibutuhkan |
|---|---|
| "Siapa belum onboarding lengkap?" | Field `onboarding_status` |
| "Siapa belum upload dokumen?" | Field `document_status` atau tabel dokumen |
| "Siapa belum BPJS?" | Field `bpjs_status` dari sistem benefit |
| "Siapa belum payroll setup?" | Field `payroll_status` dari sistem payroll |
| "Outlet mana kelebihan/kekurangan staff?" | Field `target_headcount` per outlet |

---

## Update Data Karyawan

Ganti file `data/employee_data.csv` dengan export terbaru, lalu redeploy ke Vercel.  
Server membaca CSV setiap request — tidak perlu database.

**Format kolom CSV yang diharapkan:**

| Kolom | Keterangan |
|---|---|
| `full_name` | Nama lengkap karyawan |
| `employee_id` | ID unik karyawan |
| `department` | Nama department |
| `outlet` | Nama outlet/lokasi |
| `job_position` | Jabatan |
| `job_level` | Level jabatan (angka) |
| `branch` | Branch/perusahaan |
| `join_date` | Tanggal bergabung (YYYY-MM-DD) |
| `employee_data_status` | `Active` atau `Inactive` |
| `employment_status` | `Permanent` atau `Contract` |
| `resign_date` | Tanggal resign (YYYY-MM-DD atau kosong) |
| `end_employment_date` | Tanggal akhir kontrak (YYYY-MM-DD atau kosong) |

---

## Catatan Production

Jika jumlah karyawan sudah besar (>1000 baris) atau data sering berubah, pertimbangkan:

- Ganti CSV dengan PostgreSQL / Supabase
- Tambahkan autentikasi API key di header
- Setup caching (Redis) untuk query yang sering dipanggil
- Tambahkan logging per request untuk audit trail