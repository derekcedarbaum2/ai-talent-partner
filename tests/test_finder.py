"""Offline regressions for filtering, duplicate suppression, and liveness."""
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import urllib.error
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import filters
import poll
import check_live
import terms_lib

class FinderTests(unittest.TestCase):
    def test_board_filters_with_saved_response(self):
        data = json.loads((Path(__file__).parent / "fixtures/greenhouse.json").read_text())
        company = {"name": "Fictional Company", "ats": {"provider": "greenhouse", "api": "https://example.com/api"}}
        cfg = {"filters": {"us_only": True, "salary_floor_usd": 150000}}
        matcher = terms_lib.make_title_matcher(["product manager"], ["marketing"])
        with patch.object(poll, "fetch_json", return_value=data):
            rows = poll.poll(company, matcher, cfg)
        self.assertEqual([r["url"] for r in rows], ["https://example.com/jobs/1"])

    def test_missing_salary_and_mixed_us_location_are_kept(self):
        cfg = {"filters": {"us_only": True, "salary_floor_usd": 150000}}
        self.assertIsNone(filters.salary_excluded("Competitive salary", cfg))
        self.assertFalse(filters.is_international("London, UK / Remote, US", cfg))
        self.assertTrue(filters.is_international("London, UK", cfg))

    def test_exclusion_section_overrides_inclusion(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "terms.md"
            p.write_text("# Notes\nignore me\n## Include\nProduct Manager\n## Exclusions\nMarketing\n## Hard filters\nnot a term\n")
            include, exclude = terms_lib.parse(p)
        self.assertEqual(include, ["product manager"])
        self.assertEqual(exclude, ["marketing"])
        self.assertFalse(terms_lib.make_title_matcher(include, exclude)("Product Manager, Marketing"))

    def test_duplicate_and_already_tracked_urls_are_removed(self):
        with tempfile.TemporaryDirectory() as tmp:
            comps = [{"name": "Example", "url": "https://example.com", "ats": {"provider": "greenhouse"}}]
            rows = [{"url": "https://example.com/known"}, {"url": "https://example.com/new"}, {"url": "https://example.com/new"}]
            with patch.object(poll.C, "load", return_value={}), patch.object(poll.C, "REPO_ROOT", tmp), \
                 patch.object(poll.companies_lib, "load", return_value=comps), \
                 patch.object(poll.terms_lib, "load", return_value=(["manager"], [])), \
                 patch.object(poll, "poll", return_value=rows), \
                 patch.object(poll.sheet_io, "get_existing_urls", return_value={"https://example.com/known"}), \
                 patch("sys.stdout", new_callable=io.StringIO):
                poll.main()
            data = json.loads((Path(tmp) / "state/candidates.json").read_text())
            self.assertEqual(data, [{"url": "https://example.com/new"}])

    def test_workday_locale_uses_site_not_locale(self):
        url = "https://example.wd1.myworkdayjobs.com/en-US/External/job/Remote/Manager_123"
        with patch.object(check_live, "api_status", return_value=200) as probe:
            self.assertTrue(check_live.workday_live(url))
            self.assertIn("/example/External/job/", probe.call_args.args[0])
        with patch.object(check_live, "api_status", return_value=404):
            self.assertFalse(check_live.workday_live(url))

    def test_closed_job_vs_network_failure(self):
        for code, expected in [(404, False), (410, False), (429, True), (500, True)]:
            with self.subTest(code=code), patch.object(check_live.urllib.request, "urlopen",
                side_effect=urllib.error.HTTPError("https://example.com", code, "fixture", {}, None)):
                self.assertEqual(check_live.http_live("https://example.com"), expected)
        with patch.object(check_live.urllib.request, "urlopen", side_effect=TimeoutError):
            self.assertTrue(check_live.http_live("https://example.com"))

    def test_unknown_ashby_status_does_not_delete(self):
        with patch.object(check_live, "parse_ats", return_value=("ashby", "example", "id")), \
             patch.object(check_live, "ashby_live", return_value=None), \
             patch.object(check_live, "ashby_listed", return_value=None):
            self.assertFalse(check_live.is_dead("Example", "https://example.com/job"))

if __name__ == "__main__":
    unittest.main()
