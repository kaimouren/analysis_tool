"""Small deterministic datasets with manually specified expected findings."""
import numpy as np
import pandas as pd


def cases():
    anchor = np.linspace(.01, 1.99, 100)
    mixed = ["12", "24", "unknown", "36"] * 25
    missing = [None] * 60 + list(np.linspace(.1, 9.9, 40))
    # Expectations below are authored from fixture construction, never from detector output.
    return {
        "clean": (pd.DataFrame({"signal": anchor}), [], 100),
        "missingness": (pd.DataFrame({"signal": anchor, "partial": missing}),
                        [("missingness", "partial", "critical")], 91),
        "duplicates": (pd.DataFrame({"signal": list(np.linspace(.01, 1.99, 80)) + list(np.linspace(.01, 1.99, 80))[:20]}),
                       [("duplicates", None, "high")], 96),
        "outliers": (pd.DataFrame({"signal": anchor, "extremes": list(np.linspace(.01, .99, 80)) + [100.] * 20}),
                     [("outliers", "extremes", "high")], 92.5),
        "mixed_type": (pd.DataFrame({"signal": anchor, "mixed": mixed}),
                       [("mixed_type", "mixed", "high")], 94),
        "messy_strings": (pd.DataFrame({"signal": anchor, "label": ["North", "north", " North ", " ", "South"] * 20}),
                          [("blank_strings", "label", "low"), ("surrounding_whitespace", "label", "low"),
                           ("case_variants", "label", "low")], 100),
        "combined": (pd.DataFrame({"signal": anchor, "partial": missing, "mixed": mixed, "constant": ["US"] * 100}),
                     [("missingness", "partial", "critical"), ("mixed_type", "mixed", "high"),
                      ("constant", "constant", "high")], 88.75),
        "edge_case": (pd.DataFrame(columns=["signal"]), [("empty_dataset", None, "critical")], 0),
    }
