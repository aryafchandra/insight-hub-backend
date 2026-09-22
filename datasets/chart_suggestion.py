DATE_NUMERIC = frozenset({"date", "numeric"})
CATEGORICAL_NUMERIC = frozenset({"categorical", "numeric"})


def suggest_chart_type(x_type: str, y_type: str | None) -> str | None:
    """Default chart type for two column types, per build spec §4b.

    Column order doesn't matter for a symmetric default (a user picking
    "amount" then "date" should get the same suggestion as "date" then
    "amount"), so pairs are compared as an unordered set.
    """
    if y_type is None:
        return "pie" if x_type == "categorical" else None

    pair = frozenset({x_type, y_type})

    if pair == DATE_NUMERIC:
        return "line"
    if pair == CATEGORICAL_NUMERIC:
        return "bar"
    if x_type == "numeric" and y_type == "numeric":
        return "scatter"
    return None
