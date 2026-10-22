import concurrent.futures
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine import Workshop, quote


class WorkshopTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "workshop.sqlite3"
        self.shop = Workshop(self.path)
        self.payload = {
            "name": "Алексей",
            "contact": "@sample_client",
            "device": "washer",
            "issue": "drain",
            "description": "Не сливает воду, ошибка E20",
            "preferred": "Вечером",
            "request_key": "request_key_1234",
            "consent": True,
            "low": 1,
        }

    def tearDown(self):
        self.temp.cleanup()

    def test_quote_recomputed_ignores_client_price(self):
        result = self.shop.submit(self.payload)
        self.assertEqual(result["quote"]["min"], 1600)
        self.assertEqual(self.shop.listing()[0]["low"], 1600)

    def test_repeat_and_conflicting_reuse(self):
        first = self.shop.submit(self.payload)
        self.assertEqual(self.shop.submit(self.payload)["id"], first["id"])
        with self.assertRaises(ValueError):
            self.shop.submit({**self.payload, "name": "Другой клиент"})
        self.assertEqual(len(self.shop.listing()), 1)

    def test_concurrent_double_click(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda _: self.shop.submit(self.payload), range(4)))
        self.assertEqual(len({r["id"] for r in results}), 1)
        self.assertEqual(len(self.shop.listing()), 1)

    def test_invalid_contact_and_missing_consent(self):
        for update in [
            {"contact": "abc"},
            {"consent": False},
            {"device": "unknown"},
            {"description": "x"},
        ]:
            with self.assertRaises(ValueError):
                self.shop.submit({**self.payload, **update})
        self.assertEqual(self.shop.listing(), [])

    def test_status_and_persistence(self):
        identifier = self.shop.submit(self.payload)["id"]
        self.shop.set_status(identifier, "progress")
        self.assertEqual(Workshop(self.path).listing()[0]["status"], "progress")
        with self.assertRaises(ValueError):
            self.shop.set_status(identifier, "invented")

    def test_unknown_quote_rejected(self):
        with self.assertRaises(ValueError):
            quote("washer", "bad")


if __name__ == "__main__":
    unittest.main()
