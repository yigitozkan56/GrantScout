import os
import tempfile

from fastapi.testclient import TestClient

from app import GrantScoutDB, match_grants_for_profile, parse_rss_xml, web_app


def test_parse_rss_xml():
    sample_xml = """<?xml version="1.0" encoding="UTF-8" ?>
    <rss version="2.0">
      <channel>
        <title>EU Funding Calls</title>
        <item>
          <title>Open Source AI Infrastructure Grant</title>
          <link>https://ec.europa.eu/grants/ai-infra</link>
          <description>Funding for open source AI developer tools.</description>
          <pubDate>2026-12-15</pubDate>
        </item>
      </channel>
    </rss>"""
    items = parse_rss_xml(sample_xml, agency_name="EU Portal")
    assert len(items) == 1
    assert items[0]["agency"] == "EU Portal"
    assert items[0]["title"] == "Open Source AI Infrastructure Grant"


def test_match_grants_for_profile():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = GrantScoutDB(db_path=os.path.join(tmpdir, "grants.db"))
        results = match_grants_for_profile(["ai", "seed", "startup"], db=db)
        assert len(results) >= 3
        assert results[0]["match_score"] > 0


def test_web_and_api_endpoints():
    client = TestClient(web_app)
    resp = client.get("/api/grants?keywords=ai,saas")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] >= 3
    html_resp = client.get("/")
    assert html_resp.status_code == 200
    assert "GrantScout" in html_resp.text
