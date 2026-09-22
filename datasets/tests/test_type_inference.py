import pandas as pd
from django.test import SimpleTestCase

from datasets.type_inference import infer_schema


def _column_entry(schema, name):
    return next(col for col in schema if col["name"] == name)


class TypeInferenceTests(SimpleTestCase):
    def test_clean_numeric_column(self):
        df = pd.DataFrame({"price": [1, 2, 3, 4, 5]})

        schema = infer_schema(df)

        entry = _column_entry(schema, "price")
        self.assertEqual(entry["type"], "numeric")
        self.assertNotIn("low_confidence", entry)

    def test_mostly_numeric_column_with_malformed_cells_is_numeric_and_flagged(self):
        # 19/20 parse cleanly (95%) -> still numeric, but flagged low_confidence
        values = list(range(1, 20)) + ["oops"]
        df = pd.DataFrame({"amount": values})

        schema = infer_schema(df)

        entry = _column_entry(schema, "amount")
        self.assertEqual(entry["type"], "numeric")
        self.assertTrue(entry["low_confidence"])

    def test_column_below_numeric_threshold_is_not_numeric(self):
        values = list(range(1, 15)) + ["x"] * 6  # only 70% numeric
        df = pd.DataFrame({"mixed": values})

        schema = infer_schema(df)

        entry = _column_entry(schema, "mixed")
        self.assertNotEqual(entry["type"], "numeric")

    def test_iso_date_column(self):
        df = pd.DataFrame({"created": ["2024-01-01", "2024-01-02", "2024-01-03"]})

        schema = infer_schema(df)

        entry = _column_entry(schema, "created")
        self.assertEqual(entry["type"], "date")

    def test_low_cardinality_string_column_is_categorical(self):
        df = pd.DataFrame({"region": ["north", "south", "north", "south", "east"] * 5})

        schema = infer_schema(df)

        entry = _column_entry(schema, "region")
        self.assertEqual(entry["type"], "categorical")

    def test_high_cardinality_string_column_is_text(self):
        df = pd.DataFrame({"comment": [f"unique comment {i}" for i in range(50)]})

        schema = infer_schema(df)

        entry = _column_entry(schema, "comment")
        self.assertEqual(entry["type"], "text")

    def test_missing_cells_dont_force_numeric_column_to_text(self):
        df = pd.DataFrame({"score": [1, 2, None, 4, None, 6, 7, 8]})

        schema = infer_schema(df)

        entry = _column_entry(schema, "score")
        self.assertEqual(entry["type"], "numeric")
        self.assertNotIn("low_confidence", entry)
