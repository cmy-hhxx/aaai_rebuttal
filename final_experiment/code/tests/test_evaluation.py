import csv
import json
import tempfile
import unittest
from pathlib import Path

from experiment.evaluation import prepare_audit, summarize


def corpus():
    return [{"id": f"{method}-{seed}-{slot}", "method": method, "seed_id": seed,
             "slot": slot, "cohort": "matched", "status": "ok", "problem": f"Question {seed} {slot}",
             "answer": {"value": slot}, "explanation": "Check the constraints."}
            for method in ("puzzleforge", "direct", "framework")
            for seed in ("s1", "s2", "s3") for slot in range(4)]


class EvaluationTest(unittest.TestCase):
    def test_blind_sample_is_deterministic_and_preserves_failures(self):
        records = corpus()
        for row in records:
            row.update(status="generation_failed", problem="", explanation=None)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            prepare_audit(records, root)
            first = (root / "audit_blind.jsonl").read_text()
            prepare_audit(list(reversed(records)), root)
            self.assertEqual(first, (root / "audit_blind.jsonl").read_text())
            rows = [json.loads(line) for line in first.splitlines()]
            self.assertEqual(len(rows), 18)
            self.assertEqual(set(rows[0]), {"anon_id", "problem", "answer"})
            self.assertTrue((root / "audit_native_explanations.private.jsonl").exists())
            self.assertTrue(all(row["problem"] == "" for row in rows))
            with (root / "audit_labels.csv").open(newline="") as handle:
                self.assertEqual(len(list(csv.DictReader(handle))), 54)

    def test_resume_does_not_overwrite_labels_and_rejects_new_sample(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            prepare_audit(corpus(), root)
            labels_path = root / "audit_labels.csv"
            labels_path.write_text("review completed")
            prepare_audit(corpus(), root)
            self.assertEqual(labels_path.read_text(), "review completed")
            with self.assertRaises(ValueError):
                prepare_audit(corpus(), root, seed=7)

    def test_no_labels_does_not_claim_superiority(self):
        report = summarize(corpus())
        self.assertIn("尚无可用于主终点", report)
        self.assertNotIn("PF −", report)

    def test_dual_review_adjudication_and_na_explanations(self):
        records = corpus()
        key = [{"anon_id": row["id"], "id": row["id"]} for row in records]
        labels = []
        for row in records:
            row["explanation"] = None
            for reviewer in ("r1", "r2"):
                value = "1" if row["method"] == "puzzleforge" else "0"
                labels.append({"anon_id": row["id"], "reviewer": reviewer, "valid": value,
                               "depth": "3", "explainability": "4", "evidence": "independent check"})
        report = summarize(records, labels, key)
        self.assertIn("| PF − direct | valid | 3/3 | 1.000", report)
        self.assertIn("| puzzleforge | 12 | 1.000 (12) | 3.000 (12) | NA (0)", report)
        # A single unadjudicated disagreement leaves one seed below the 2-item threshold.
        disputed = records[0]["id"]
        labels = [r for r in labels if r["anon_id"] != disputed]
        labels.extend([{"anon_id": disputed, "reviewer": reviewer, "valid": value,
                        "evidence": "checked"} for reviewer, value in (("r1", "0"), ("r2", "1"))])
        report = summarize(records, labels, key)
        self.assertIn("记录：35", report)
        labels.append({"anon_id": disputed, "reviewer": "adjudicator", "valid": "1", "evidence": "resolved"})
        self.assertIn("记录：36", summarize(records, labels, key))

    def test_unknown_labels_or_duplicate_reviewers_are_rejected(self):
        with self.assertRaises(ValueError):
            summarize(corpus(), [{"anon_id": "unknown", "reviewer": "r", "valid": "1", "evidence": "proof"}], [])

    def test_duplicate_record_ids_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            rows = corpus()
            with self.assertRaises(ValueError):
                prepare_audit(rows + [rows[0]], Path(folder))

    def test_min_count_fails_before_writing_audit_files(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with self.assertRaisesRegex(ValueError, "below required"):
                prepare_audit(corpus(), root, per_seed=1, min_count=20)
            self.assertFalse((root / "audit_blind.jsonl").exists())

    def test_nonfinite_scores_and_false_valid_failures_are_rejected(self):
        records = corpus()[:1]
        key = [{"anon_id": "a", "id": records[0]["id"]}]
        labels = [{"anon_id": "a", "reviewer": reviewer, "valid": "1", "depth": "nan", "evidence": "checked"}
                  for reviewer in ("r1", "r2")]
        with self.assertRaises(ValueError):
            summarize(records, labels, key)
        for label in labels:
            label["depth"] = "3"
        records[0]["status"] = "generation_failed"
        with self.assertRaises(ValueError):
            summarize(records, labels, key)


if __name__ == "__main__":
    unittest.main()
