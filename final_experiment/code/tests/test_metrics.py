import unittest
from experiment.metrics import lexical_metrics


class MetricsTests(unittest.TestCase):
    def test_normalized_duplicates_and_cohort_boundary(self):
        def r(text, cohort="matched"):
            return {"method": "direct", "seed_id": "s", "problem": text, "status": "ok", "cohort": cohort}
        result = lexical_metrics([r("A B C D E F"), r("a b c d e f"), r("Entirely unrelated puzzle"), r("hidden", "extra")])
        self.assertEqual(result[0]["n"], 3)
        self.assertEqual(result[0]["near_duplicate_items"], 2)


if __name__ == "__main__":
    unittest.main()
