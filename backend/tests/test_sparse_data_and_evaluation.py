import unittest
from app.demo import demo_events
from app.main import evaluate_scenarios
from app.features import CATEGORIES, build_temporal_features

class ScenarioLabTests(unittest.TestCase):
    def test_all_scenarios_have_temporal_data_across_supported_windows(self):
        for weeks in (4, 8, 12, 24):
            for scenario in ('mixed', 'improving', 'declining', 'stable', 'sudden_change'):
                events = demo_events(weeks, scenario)
                self.assertEqual(len(events), weeks * len(CATEGORIES) * 2)
                features = build_temporal_features(events, weeks)
                self.assertTrue(all(features[c] for c in CATEGORIES))

    def test_evaluation_metrics_are_consistent_with_cases(self):
        report = evaluate_scenarios()
        self.assertEqual(report['sample_size'], 4)
        self.assertIn('synthetic', report['warning'].lower())
        self.assertEqual(report['metrics']['true_positive'] + report['metrics']['false_positive'] + report['metrics']['false_negative'] + report['metrics']['true_negative'], 4)
        self.assertEqual(len(report['cases']), 4)

if __name__ == '__main__':
    unittest.main()
