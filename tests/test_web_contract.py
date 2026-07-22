import re
import unittest
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path


WEB_ROOT = Path(__file__).resolve().parents[1] / "web" / "src"


class IdParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []

    def handle_starttag(self, _tag, attrs):
        values = dict(attrs)
        if "id" in values:
            self.ids.append(values["id"])


class WebContractTests(unittest.TestCase):
    def test_ids_are_unique_and_modeler_references_exist(self):
        html = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
        script = (WEB_ROOT / "workflow_modeler.js").read_text(encoding="utf-8")
        parser = IdParser()
        parser.feed(html)
        counts = Counter(parser.ids)
        duplicates = sorted(element_id for element_id, count in counts.items() if count > 1)
        self.assertEqual(duplicates, [])

        referenced = set(re.findall(r"getElementById\(['\"]([^'\"]+)['\"]\)", script))
        missing = sorted(referenced.difference(counts))
        self.assertEqual(missing, [])

    def test_modeler_assets_are_linked(self):
        html = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
        app = (WEB_ROOT / "app.js").read_text(encoding="utf-8")
        self.assertIn("workflow_modeler.css", html)
        self.assertIn("./workflow_modeler.js", app)

    def test_one_click_workflow_contract(self):
        html = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
        script = (WEB_ROOT / "workflow_modeler.js").read_text(encoding="utf-8")
        self.assertRegex(html, r'id="workflow-one-click"[^>]*checked')
        self.assertIn('id="workflow-open-guide"', html)
        self.assertIn("smartPredecessor(type)", script)
        self.assertIn("smartConnect: this.oneClickToggle?.checked !== false", script)
        self.assertIn("element.addEventListener('pointerdown'", script)

    def test_analytical_guide_is_complete_and_navigable(self):
        html = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
        required_sections = {
            "guide-start", "guide-data", "guide-workspaces", "guide-workflow",
            "guide-nodes", "guide-optimizer", "guide-results", "guide-decision",
            "guide-improve", "guide-output",
        }
        section_ids = set(re.findall(r'id="(guide-[^"]+)"', html))
        nav_targets = set(re.findall(r'data-guide-target="([^"]+)"', html))
        self.assertTrue(required_sections.issubset(section_ids))
        self.assertEqual(nav_targets, required_sections)
        searchable_html = html.casefold()
        for term in ("Pareto", "TOPSIS", "QGIS", "constraint_penalty", "Duyarlılık"):
            self.assertIn(term.casefold(), searchable_html)

        guide_path = WEB_ROOT.parents[1] / "USER_GUIDE_TR.md"
        guide = guide_path.read_text(encoding="utf-8")
        self.assertGreater(len(guide), 12000)
        self.assertIn("## 9. Karar protokolü", guide)
        self.assertIn("## 13. Nihai checklist", guide)


if __name__ == "__main__":
    unittest.main()
