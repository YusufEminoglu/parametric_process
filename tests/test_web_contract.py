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


if __name__ == "__main__":
    unittest.main()
