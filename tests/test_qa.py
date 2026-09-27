import copy
import json
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
from pydantic import ValidationError

from qa_core import load_csv, profile_dataframe, severity
from llm import (UNAVAILABLE, ExplanationBundle, explain_profile, explanation_payload,
                 fallback_explanations, validate_explanations)
from report import markdown_report

ROOT = Path(__file__).resolve().parents[1]


class CoreTests(unittest.TestCase):
    def test_hand_calculated_statistics(self):
        df = pd.DataFrame({"x": [0., 1., 2., 3., 100., np.nan], "group": ["a"]*6})
        original = df.copy(deep=True)
        p = profile_dataframe(df)
        self.assertAlmostEqual(p["summary"]["missing_pct"], 100/12)
        self.assertEqual(p["columns"][0]["outlier_count"], 1)
        self.assertEqual(p["columns"][0]["outlier_pct"], 20)
        self.assertEqual(p["columns"][0]["outlier_lower"], -2)
        self.assertEqual(p["columns"][0]["outlier_upper"], 6)
        # Missing 2.5, outliers 15, constant 7.5, integer-like ID 1.5.
        self.assertEqual(p["quality_score"], 73.5)
        pd.testing.assert_frame_equal(df, original)
        json.dumps(p, allow_nan=False)

    def test_duplicate_denominator(self):
        p = profile_dataframe(pd.DataFrame({"x": [1, 1, 2, 2, 2]}))
        self.assertEqual(p["summary"]["duplicate_rows"], 3)
        self.assertEqual(p["summary"]["duplicate_pct"], 60)

    def test_sample_coverage_and_repeatability(self):
        frame, _ = load_csv((ROOT / "examples/messy_sample.csv").read_bytes())
        p = profile_dataframe(frame)
        self.assertEqual(p["summary"]["rows"], 500)
        self.assertEqual(p["summary"]["duplicate_rows"], 20)
        self.assertTrue({"missingness", "duplicates", "outliers", "constant", "near_constant", "possible_id", "mixed_type"}.issubset({i["issue_type"] for i in p["issues"]}))
        self.assertEqual(json.dumps(p, allow_nan=False), json.dumps(profile_dataframe(frame), allow_nan=False))
        clean = next(c for c in p["columns"] if c["column"] == "engagement_score")
        self.assertEqual(clean["outlier_count"], 0)
        self.assertEqual(clean["missing_count"], 0)

    def test_empty_null_single_and_infinite(self):
        for df in [pd.DataFrame(), pd.DataFrame(columns=["x"]), pd.DataFrame({"x": [None, None]}),
                   pd.DataFrame({"x": [1]}), pd.DataFrame({"x": [float("inf"), -float("inf"), 1]})]:
            p = profile_dataframe(df)
            json.dumps(p, allow_nan=False)
            self.assertTrue(0 <= p["quality_score"] <= 100)
        self.assertEqual(profile_dataframe(pd.DataFrame(columns=["x"]))["quality_score"], 0)
        p = profile_dataframe(pd.DataFrame({"x": [None, None]}))
        self.assertFalse(p["columns"][0]["constant"])
        p = profile_dataframe(pd.DataFrame({"x": [np.inf, 1]}))
        self.assertIn("non_finite", [i["issue_type"] for i in p["issues"]])

    def test_semantics_and_boundaries(self):
        p = profile_dataframe(pd.DataFrame({"mixed": ["123", "456", "unknown", "789"],
                                           "dates": ["2024-01-01", "2024-01-02", "bad", "2024-01-04"],
                                           "long": ["a"*90+str(i) for i in range(4)]}))
        self.assertTrue(p["columns"][0]["mixed_type"])
        self.assertEqual(p["columns"][1]["datetime_parseability_pct"], 75)
        self.assertFalse(p["columns"][2]["possible_id"])
        p = profile_dataframe(pd.DataFrame({"near": ["a"]*95+["b"]*5}))
        self.assertTrue(p["columns"][0]["near_constant"])
        for pct, expected in [(0.1, "low"), (5, "medium"), (20, "high"), (50, "critical")]:
            self.assertEqual(severity(pct, 20, 5, 50), expected)
        p = profile_dataframe(pd.DataFrame({"numbers": [1, 2, 3]}))
        self.assertEqual(p["columns"][0]["datetime_parseability_pct"], 0)
        p = profile_dataframe(pd.DataFrame({"mixed": ["12"]*90+["unknown"]*10}))
        self.assertEqual(next(i for i in p["issues"] if i["issue_type"] == "mixed_type")["severity"], "high")

    def test_nullable_notebook_types(self):
        p = profile_dataframe(pd.DataFrame({"i": pd.Series([1, None, 2], dtype="Int64"),
                                           "s": pd.Series(["x", None, "y"], dtype="string"),
                                           "b": pd.Series([True, None, False], dtype="boolean")}))
        json.dumps(p, allow_nan=False)

    def test_encodings_and_bad_csv(self):
        for data, expected in [("name\ncafé\n".encode("utf-8"), "utf-8"),
                               ("name\ncafé\n".encode("utf-8-sig"), "utf-8"),
                               ("name\ncafé\n".encode("latin-1"), "latin-1")]:
            frame, encoding = load_csv(data)
            self.assertEqual(encoding, expected)
            self.assertEqual(frame.iloc[0, 0], "café")
            self.assertEqual(frame.columns[0], "name")
        for data in [b"", b'a,b\n"unterminated,2', b"a,b\n1,2,3\n4,5,6"]:
            with self.assertRaises(ValueError):
                load_csv(data)


class ExplanationTests(unittest.TestCase):
    def setUp(self):
        self.profile = profile_dataframe(pd.DataFrame({"private_name": [1, 1, None]}))

    def test_offline_report(self):
        before = copy.deepcopy(self.profile)
        bundle, status = explain_profile(self.profile, api_key="")
        self.assertEqual(status, UNAVAILABLE)
        report = markdown_report(self.profile, bundle, status)
        for value in ("Suggested fix", "private", "Quality score", "missing", UNAVAILABLE):
            self.assertIn(value, report)
        self.assertEqual(self.profile, before)
        self.assertNotIn("private_name", json.dumps(explanation_payload(self.profile)))

    @patch("llm.OpenAI")
    def test_failure_and_valid_mock_response(self, mocked):
        client = mocked.return_value.__enter__.return_value
        client.chat.completions.parse.side_effect = RuntimeError("secret")
        _, status = explain_profile(self.profile, api_key="test")
        self.assertEqual(status, UNAVAILABLE)
        client.chat.completions.parse.side_effect = None
        bundle = fallback_explanations(self.profile)
        response = MagicMock()
        response.choices[0].message.parsed = bundle
        client.chat.completions.parse.return_value = response
        result, status = explain_profile(self.profile, api_key="test")
        self.assertEqual(result, bundle)
        self.assertIn("available", status)

    def test_reject_invented_identity_numbers_and_score(self):
        bundle = fallback_explanations(self.profile)
        bundle.issues[0].issue_id = "invented"
        with self.assertRaises(ValueError):
            validate_explanations(bundle, self.profile)
        bundle = fallback_explanations(self.profile)
        bundle.score_explanation = "The score is 99."
        with self.assertRaises(ValueError):
            validate_explanations(bundle, self.profile)
        with self.assertRaises(ValidationError):
            ExplanationBundle.model_validate({**fallback_explanations(self.profile).model_dump(), "quality_score": 99})


class StreamlitTests(unittest.TestCase):
    @patch.dict("os.environ", {"OPENAI_API_KEY": "", "OPENAI_BASE_URL": ""})
    def test_offline_sample_and_charts(self):
        from streamlit.testing.v1 import AppTest
        app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
        self.assertFalse(app.exception)
        app.toggle[0].set_value(True).run()
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value, "500")
        self.assertEqual(len(app.get("download_button")), 1)
        self.assertEqual(len(app.get("plotly_chart")), 1)
        self.assertTrue(any(UNAVAILABLE in c.value for c in app.caption))
        app.selectbox[0].select("annual_income").run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.get("plotly_chart")), 1)
        app.selectbox[0].select("region").run()
        self.assertFalse(app.exception)


if __name__ == "__main__":
    unittest.main()
