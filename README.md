# 🏛️ GrantScout

![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)
![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB.svg?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg?logo=fastapi&logoColor=white)
![Legal Data Flow](https://img.shields.io/badge/Data%20Flow-Official%20Public%20RSS%20%26%20Open%20Data-success)

**GrantScout** is an open-source grant discovery and matching engine for founders, Indie Hackers, and R&D engineers. It matches your technology profile against public government incentives, TÜBİTAK/KOSGEB calls, and EU Horizon open funding announcements.

---

## ⚖️ Legal Data Architecture & Compliance

GrantScout operates with 100% legal transparency:
- **Public Agency RSS & Open Data Only:** Consumes official public RSS 2.0 feeds from government portals, EU Funding & Tenders portals, and user-submitted open call URLs.
- **No Paywall or Private Portal Scraping:** Never accesses password-protected applicant portals or scrapes private databases.
- **Local SQLite Cache:** Stores public call metadata locally in `grantscout_cache.db` for instant offline keyword matching.

---

## 📊 Sample Output

```text
🏛️ Matching grants for keywords: ai, software, startup
Agency                 | Title                                      | Deadline     | Match
----------------------------------------------------------------------------------------
TÜBİTAK BİGG           | 1512 Techno-Entrepreneurship Capital Suppo | 2026-12-31   | 100.0%
European Innovation Co | EIC Accelerator Open Call - Breakthrough D | 2027-01-20   | 66.7%
KOSGEB                 | R&D, P&D and Innovation Support Program fo | 2027-03-15   | 33.3%
```

| Agency | Program Title | Deadline | Match Score |
| :--- | :--- | :---: | :---: |
| **TÜBİTAK BİGG** | 1512 Techno-Entrepreneurship Capital Support Program | `2026-12-31` | **100.0%** |
| **European Innovation Council** | EIC Accelerator Open Call - Breakthrough Digital & AI | `2027-01-20` | **66.7%** |
| **KOSGEB** | R&D, P&D and Innovation Support Program for SMEs | `2027-03-15` | **33.3%** |

---

## 🚀 Step-by-Step Installation

```bash
git clone https://github.com/yigitozkan56/GrantScout.git
cd GrantScout
cp .env.example .env
pip install -r requirements.txt
```

---

## 💻 Usage Examples

### CLI Mode
```bash
# Match your startup profile against cached public grants
python app.py match --keywords "ai,deeptech,seed,software"

# Ingest an official public RSS feed
python app.py ingest-rss https://ec.europa.eu/info/funding-tenders/opportunities/data/rss.xml
```

### Web Dashboard & REST API Mode
```bash
python app.py serve --port 8002
```
Visit `http://127.0.0.1:8002` or query `GET http://127.0.0.1:8002/api/grants?keywords=ai,saas`.

### Running Unit Tests
```bash
pytest tests/
```

---

## 🗺️ Roadmap

- [x] Official RSS 2.0 XML parser for public grant portals
- [x] Keyword-based startup profile matching engine
- [x] Local SQLite persistence and FastAPI Web UI
- [ ] iCal (`.ics`) deadline export for matched funding calls
- [ ] Multi-language grant summary translation helper
