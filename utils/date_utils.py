from __future__ import annotations
from datetime import date

MONTHS_ES = {
    1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
    5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
    9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre",
}

DAYS_ES = {
    0: "lunes", 1: "martes", 2: "miércoles", 3: "jueves",
    4: "viernes", 5: "sábado", 6: "domingo",
}


def format_date_es(d: date | None = None) -> str:
    """Returns a Spanish-formatted date string, e.g. 'Lunes, 28 de febrero de 2026'."""
    if d is None:
        d = date.today()
    day_name = DAYS_ES[d.weekday()].capitalize()
    month_name = MONTHS_ES[d.month]
    return f"{day_name}, {d.day} de {month_name} de {d.year}"
