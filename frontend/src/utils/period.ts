/**
 * Работа с месяцами.
 *
 * Месяц — это пара «год + номер», а не дата: `new Date(2026, 11)` — это
 * декабрь, и такая ошибка стоит месяц чужих денег в сводке. Поэтому месяцы
 * пересчитываются арифметикой по номеру месяца, а не календарными датами.
 */

/** Год и номер месяца (1-12). */
export interface Period {
  year: number;
  month: number;
}

/** Сдвинуть месяц на `delta` (отрицательное — назад). */
export function shiftMonth(period: Period, delta: number): Period {
  const index = period.year * 12 + (period.month - 1) + delta;
  return { year: Math.floor(index / 12), month: (index % 12) + 1 };
}

/** Последние `count` месяцев, заканчивая `period` (включая его самого). */
export function lastMonths(period: Period, count: number): Period[] {
  const months: Period[] = [];
  for (let offset = count - 1; offset >= 0; offset -= 1) {
    months.push(shiftMonth(period, -offset));
  }
  return months;
}

/** Период в формате `<input type="month">`: (2026, 11) → «2026-11». */
export function periodToInput(period: Period): string {
  const month = String(period.month).padStart(2, '0');
  return `${period.year}-${month}`;
}

/** Период из значения `<input type="month">`. */
export function inputToPeriod(value: string): Period {
  const [year = '1970', month = '1'] = value.split('-');
  return { year: Number(year), month: Number(month) };
}

/** Текущий месяц по часам браузера. */
export function currentPeriod(): Period {
  const now = new Date();
  return { year: now.getFullYear(), month: now.getMonth() + 1 };
}

/** Сегодняшняя дата в формате `YYYY-MM-DD` — так её ждёт `<input type="date">`. */
export function today(): string {
  const now = new Date();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  return `${now.getFullYear()}-${month}-${day}`;
}
