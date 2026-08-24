import re

_YEAR_RE = re.compile(r"(\d{4})")


def parse_period_years(period: str | None) -> tuple[int, int] | None:
    """Parse a Leiden Period string like '2020–2023' (en dash, U+2013) into
    (start_year, end_year), inclusive on both ends.

    Deliberately regex-based rather than splitting on the dash character —
    the source uses U+2013 but this stays robust to either dash variant.
    Returns None if the string doesn't contain two 4-digit years (e.g. no
    Leiden data imported yet).
    """
    if not period:
        return None
    years = _YEAR_RE.findall(period)
    if len(years) < 2:
        return None
    return int(years[0]), int(years[-1])
