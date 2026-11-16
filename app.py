"""
GrantScout - Legal Public Grant, R&D Incentive & Open Funding Matcher.
Exclusively processes official public agency RSS/XML feeds, open data portals, and user-submitted grant URLs.
"""

import os
from contextlib import closing
import sqlite3
import time
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional

import httpx
import typer
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

app_cli = typer.Typer(help="GrantScout CLI - Match startups & developers with public R&D grants (TUBITAK, KOSGEB, EU Horizon).")
web_app = FastAPI(
    title="GrantScout API & Web UI",
    description="Matches developers and founders with public grants using official RSS feeds and open data portals.",
    version="1.0.0",
)

DEFAULT_PUBLIC_GRANTS = [
    {
        "grant_id": "TUBITAK-1512-2026",
        "agency": "TÃœBÄ°TAK BÄ°GG",
        "title": "1512 Techno-Entrepreneurship Capital Support Program (BiGG)",
        "summary": "Seed funding for early-stage deep-tech, AI, software, and green technology startups.",
        "tags": "ai,software,deeptech,seed,startup,cloud",
        "url": "https://tubitak.gov.tr/tr/destekler/sanayi/ulusal-destek-programlari/1512",
        "deadline": "2026-12-31",
    },
    {
        "grant_id": "KOSGEB-ARGE-2026",
        "agency": "KOSGEB",
        "title": "R&D, P&D and Innovation Support Program for SMEs",
        "summary": "Hardware, developer personnel, and cloud commercialization grant for innovative SME software products.",
        "tags": "sme,r&d,innovation,software,saas,hardware",
        "url": "https://www.kosgeb.gov.tr/site/tr/genel/detay/1231/arge-urge-ve-inovasyon-destek-programi",
        "deadline": "2027-03-15",
    },
    {
        "grant_id": "EU-HORIZON-EIC-2026",
        "agency": "European Innovation Council (Horizon Europe)",
        "title": "EIC Accelerator Open Call - Breakthrough Digital & AI Technologies",
        "summary": "Grant and equity funding for high-impact European startups building open-source, AI, and climate solutions.",
        "tags": "eu,horizon,ai,opensource,climate,deeptech,scaleup",
        "url": "https://eic.ec.europa.eu/eic-funding-opportunities/eic-accelerator_en",
        "deadline": "2027-01-20",
    },
]


class GrantSubmission(BaseModel):
    grant_id: str
    agency: str
    title: str
    summary: str
    tags: str
    url: str
    deadline: str = "Open"


class GrantScoutDB:
    """SQLite local storage and cache for public grant announcements."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.getenv("GRANTSCOUT_DB_PATH", "grantscout_cache.db")
        self._init_db()

    def _init_db(self) -> None:
        with closing(sqlite3.connect(self.db_path)) as conn, conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS grants (
                    grant_id TEXT PRIMARY KEY,
                    agency TEXT,
                    title TEXT,
                    summary TEXT,
                    tags TEXT,
                    url TEXT,
                    deadline TEXT,
                    updated_at INTEGER
                )
                """
            )
            conn.commit()
        if not self.list_grants():
            for item in DEFAULT_PUBLIC_GRANTS:
                self.upsert_grant(item)

    def upsert_grant(self, grant: Dict[str, Any]) -> None:
        with closing(sqlite3.connect(self.db_path)) as conn, conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO grants (
                    grant_id, agency, title, summary, tags, url, deadline, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    grant["grant_id"],
                    grant["agency"],
                    grant["title"],
                    grant["summary"],
                    grant["tags"],
                    grant["url"],
                    grant.get("deadline", "Open"),
                    int(time.time()),
                ),
            )
            conn.commit()

    def list_grants(self) -> List[Dict[str, Any]]:
        with closing(sqlite3.connect(self.db_path)) as conn, conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM grants ORDER BY deadline ASC").fetchall()
            return [dict(r) for r in rows]


def parse_rss_xml(xml_text: str, agency_name: str = "Public RSS Feed") -> List[Dict[str, Any]]:
    """Parses standard RSS 2.0 XML from public government/EU funding portals."""
    parsed: List[Dict[str, Any]] = []
    root = ET.fromstring(xml_text.strip())
    for idx, item in enumerate(root.findall(".//item")):
        title = (item.findtext("title") or "Untitled Grant Call").strip()
        link = (item.findtext("link") or "https://ec.europa.eu").strip()
        desc = (item.findtext("description") or "").strip()
        pub_date = (item.findtext("pubDate") or "Open").strip()
        parsed.append(
            {
                "grant_id": f"RSS-{idx + 1}-{ abs(hash(link)) % 100000 }",
                "agency": agency_name,
                "title": title,
                "summary": desc,
                "tags": "rss,public-grant,open-call",
                "url": link,
                "deadline": pub_date,
            }
        )
    return parsed


def match_grants_for_profile(keywords: List[str], db: Optional[GrantScoutDB] = None) -> List[Dict[str, Any]]:
    """Scores and ranks public grants against developer/startup profile keywords."""
    db = db or GrantScoutDB()
    grants = db.list_grants()
    norm_kw = [k.strip().lower() for k in keywords if k.strip()]
    scored_list: List[Dict[str, Any]] = []

    for g in grants:
        haystack = f"{g['title']} {g['summary']} {g['tags']} {g['agency']}".lower()
        hits = sum(1 for k in norm_kw if k in haystack)
        match_score = round((hits / max(len(norm_kw), 1)) * 100.0, 1) if norm_kw else 100.0
        item_copy = dict(g)
        item_copy["match_score"] = match_score
        scored_list.append(item_copy)

    scored_list.sort(key=lambda x: x["match_score"], reverse=True)
    return scored_list


@web_app.get("/api/grants")
def api_match_grants(
    keywords: str = Query("ai,software,startup", description="Comma-separated profile keywords"),
) -> Dict[str, Any]:
    kw_list = [k.strip() for k in keywords.split(",") if k.strip()]
    matched = match_grants_for_profile(kw_list)
    return {"count": len(matched), "source": "Official Public Agency RSS & Open Data", "items": matched}


@web_app.post("/api/grants")
def api_add_grant(submission: GrantSubmission) -> Dict[str, Any]:
    db = GrantScoutDB()
    data = submission.model_dump()
    db.upsert_grant(data)
    return {"status": "saved", "grant": data}


@web_app.get("/", response_class=HTMLResponse)
def web_dashboard(keywords: str = "ai,software,startup") -> str:
    kw_list = [k.strip() for k in keywords.split(",") if k.strip()]
    matched = match_grants_for_profile(kw_list)
    rows_html = "".join(
        f"<tr><td><strong>{g['agency']}</strong></td>"
        f"<td><a href='{g['url']}' target='_blank'>{g['title']}</a><br><small>{g['summary']}</small></td>"
        f"<td>{g['deadline']}</td><td><strong>{g['match_score']}%</strong></td></tr>"
        for g in matched
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>GrantScout - Public R&D & Grant Matcher</title>
    <style>
        body {{ font-family: system-ui, sans-serif; max-width: 960px; margin: 2rem auto; padding: 0 1rem; background: #0f172a; color: #f8fafc; }}
        h1 {{ color: #34d399; }}
        .badge {{ background: #059669; padding: 0.25rem 0.6rem; border-radius: 4px; font-size: 0.85rem; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 1.5rem; background: #1e293b; border-radius: 8px; overflow: hidden; }}
        th, td {{ padding: 0.75rem 1rem; text-align: left; border-bottom: 1px solid #334155; }}
        th {{ background: #0f172a; color: #94a3b8; }}
        a {{ color: #34d399; text-decoration: none; }}
    </style>
</head>
<body>
    <h1>ğŸ›ï¸ GrantScout <span class="badge">Official Public Feeds & Open Data</span></h1>
    <p>Matching profile keywords (<code>{keywords}</code>) against TÃœBÄ°TAK, KOSGEB, and EU Horizon open calls.</p>
    <table>
        <thead>
            <tr><th>Agency</th><th>Program & Summary</th><th>Deadline</th><th>Match Score</th></tr>
        </thead>
        <tbody>{rows_html}</tbody>
    </table>
</body>
</html>"""


@app_cli.command("match")
def cli_match(
    keywords: str = typer.Option("ai,software,startup", "--keywords", "-k", help="Comma-separated startup keywords"),
) -> None:
    """Match your project keywords against public R&D grants and open funding calls."""
    kw_list = [k.strip() for k in keywords.split(",") if k.strip()]
    results = match_grants_for_profile(kw_list)
    typer.echo(f"ğŸ›ï¸ Matching grants for keywords: {', '.join(kw_list)}")
    typer.echo(f"{'Agency':<22} | {'Title':<42} | {'Deadline':<12} | {'Match'}")
    typer.echo("-" * 88)
    for r in results:
        typer.echo(
            f"{r['agency'][:22]:<22} | {r['title'][:42]:<42} | {r['deadline'][:12]:<12} | {r['match_score']}%"
        )


@app_cli.command("ingest-rss")
def cli_ingest_rss(url: str = typer.Argument(..., help="Official public RSS XML URL")) -> None:
    """Ingest grants from an official public institution RSS feed."""
    with httpx.Client(timeout=10.0) as client:
        resp = client.get(url)
        resp.raise_for_status()
        items = parse_rss_xml(resp.text)
        db = GrantScoutDB()
        for item in items:
            db.upsert_grant(item)
        typer.echo(f"Ingested {len(items)} public grant notices into SQLite cache.")


@app_cli.command("serve")
def cli_serve(port: int = typer.Option(8002, "--port", "-p")) -> None:
    """Start the GrantScout FastAPI web server."""
    import uvicorn

    uvicorn.run(web_app, host="127.0.0.1", port=port)


if __name__ == "__main__":
    app_cli()
