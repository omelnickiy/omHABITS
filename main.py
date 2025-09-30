from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Tuple, Set
import calendar
from datetime import datetime

app = FastAPI(title="Telegram Calendar Formatter")

WEEKDAYS_RU = "Пн Вт Ср Чт Пт Сб Вс"

class CalendarRequest(BaseModel):
    dates: List[str] = Field(
        ...,
        description="Массив дат в формате DD-MM-YYYY, например ['14-03-2025', '20-03-2025']"
    )
    emoji: str = Field(default="✅", description="Эмодзи для пометки активных дат")

def parse_dates_grouped(dates: List[str]) -> Dict[Tuple[int, int], Set[int]]:
    """
    Группирует входные даты по (год, месяц) -> {дни}.
    Ожидаемый формат входа: DD-MM-YYYY.
    """
    grouped: Dict[Tuple[int, int], Set[int]] = {}
    for s in dates:
        try:
            dt = datetime.strptime(s, "%d-%m-%Y")
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Неверный формат даты: '{s}'. Ожидается DD-MM-YYYY.")
        key = (dt.year, dt.month)
        grouped.setdefault(key, set()).add(dt.day)
    return grouped

def render_month_calendar(year: int, month: int, marked_days: Set[int], mark: str) -> str:
    """
    Рисует календарь на месяц с пометками.
    Первым днём недели считается Понедельник.
    """
    cal = calendar.Calendar(firstweekday=0)  # 0 = Monday
    lines = [f"Календарь активностей для {year:04d}-{month:02d}:", WEEKDAYS_RU]

    # Каждая неделя — список из 7 чисел (0, если день вне текущего месяца)
    for week in cal.monthdayscalendar(year, month):
        row_cells = []
        for day in week:
            if day == 0:
                # Пустая ячейка (два пробела для выравнивания чисел)
                cell = "  "
            elif day in marked_days:
                # Эмодзи. Добавим небольшой пробел, чтобы не «съедать» разметку.
                cell = f"{mark}"
            else:
                # Двухсимвольное выравнивание чисел
                cell = f"{day:>2}"
            row_cells.append(cell)
        # Разделяем одним пробелом; в Телеграме лучше отправлять этот текст в моноширинном блоке.
        lines.append(" ".join(row_cells).rstrip())
    return "\n".join(lines)

@app.post("/calendar")
def build_calendar(payload: CalendarRequest):
    grouped = parse_dates_grouped(payload.dates)
    if not grouped:
        raise HTTPException(status_code=400, detail="Пустой список дат.")

    # Рендерим по каждому месяцу (отсортируем для стабильности)
    parts = []
    for (year, month) in sorted(grouped.keys()):
        parts.append(
            render_month_calendar(year, month, grouped[(year, month)], payload.emoji)
        )

    # Возвращаем единый текст — готов к вставке в Телеграм (оберните в ``` для моноширинного)
    return {"text": "\n\n".join(parts)}

@app.get("/health")
def health():
    return {"status": "ok"}
