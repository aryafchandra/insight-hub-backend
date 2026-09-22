from django.test import SimpleTestCase

from datasets.chart_suggestion import suggest_chart_type


class ChartSuggestionTests(SimpleTestCase):
    def test_date_and_numeric_suggests_line(self):
        self.assertEqual(suggest_chart_type("date", "numeric"), "line")

    def test_numeric_and_date_suggests_line_regardless_of_order(self):
        self.assertEqual(suggest_chart_type("numeric", "date"), "line")

    def test_categorical_and_numeric_suggests_bar(self):
        self.assertEqual(suggest_chart_type("categorical", "numeric"), "bar")

    def test_numeric_and_categorical_suggests_bar_regardless_of_order(self):
        self.assertEqual(suggest_chart_type("numeric", "categorical"), "bar")

    def test_numeric_and_numeric_suggests_scatter(self):
        self.assertEqual(suggest_chart_type("numeric", "numeric"), "scatter")

    def test_categorical_alone_suggests_pie(self):
        self.assertEqual(suggest_chart_type("categorical", None), "pie")

    def test_numeric_alone_has_no_suggestion(self):
        self.assertIsNone(suggest_chart_type("numeric", None))

    def test_date_alone_has_no_suggestion(self):
        self.assertIsNone(suggest_chart_type("date", None))

    def test_text_columns_have_no_suggestion(self):
        self.assertIsNone(suggest_chart_type("text", "text"))

    def test_categorical_and_categorical_has_no_suggestion(self):
        self.assertIsNone(suggest_chart_type("categorical", "categorical"))

    def test_date_and_date_has_no_suggestion(self):
        self.assertIsNone(suggest_chart_type("date", "date"))
