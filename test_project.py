import unittest

from project import demo, extract, make_fixtures


class IntakeEvalTests(unittest.TestCase):
    def test_regression_gate_and_positive_control(self):
        report = demo()
        self.assertEqual(report["candidate"]["rows"], 60)
        self.assertGreater(report["candidate"]["exact"], report["baseline"]["exact"])
        self.assertEqual(report["candidate"]["unsupported_values"], 0)
        self.assertTrue(report["baseline"]["failures"])

    def test_selected_evidence_resolves_to_applicant_turn(self):
        for row in make_fixtures():
            for item in extract(row["turns"], evidence_aware=True).values():
                turn = row["turns"][item["turn"] - 1]
                self.assertEqual(turn["role"], "applicant")
                self.assertIn(item["quote"], turn["text"])

    def test_unrelated_negation_does_not_clear_prior_value(self):
        turns = [{"role": "applicant", "text": "I want finance. I don't want architecture."}]
        self.assertEqual(extract(turns, evidence_aware=True)["program"]["value"], "finance")
