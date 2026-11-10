/**
 * Работа с месяцами: арифметика, которая чаще всего и ломается.
 */

import { describe, expect, it } from 'vitest';
import { inputToPeriod, lastMonths, periodToInput, shiftMonth } from '../src/utils/period';

describe('shiftMonth', () => {
  it('переходит к следующему месяцу', () => {
    expect(shiftMonth({ year: 2026, month: 11 }, 1)).toEqual({ year: 2026, month: 12 });
  });

  it('переходит через новый год', () => {
    expect(shiftMonth({ year: 2026, month: 12 }, 1)).toEqual({ year: 2027, month: 1 });
  });

  it('возвращается назад через новый год', () => {
    expect(shiftMonth({ year: 2027, month: 1 }, -1)).toEqual({ year: 2026, month: 12 });
  });

  it('переходит назад внутри года', () => {
    expect(shiftMonth({ year: 2026, month: 3 }, -1)).toEqual({ year: 2026, month: 2 });
  });
});

describe('lastMonths', () => {
  it('отдаёт нужное число месяцев, начиная с самого раннего', () => {
    expect(lastMonths({ year: 2026, month: 3 }, 6)).toEqual([
      { year: 2025, month: 10 },
      { year: 2025, month: 11 },
      { year: 2025, month: 12 },
      { year: 2026, month: 1 },
      { year: 2026, month: 2 },
      { year: 2026, month: 3 },
    ]);
  });

  it('заканчивается выбранным месяцем', () => {
    const months = lastMonths({ year: 2026, month: 11 }, 3);
    expect(months[months.length - 1]).toEqual({ year: 2026, month: 11 });
  });
});

describe('periodToInput и inputToPeriod', () => {
  it('превращает период в значение поля месяца', () => {
    expect(periodToInput({ year: 2026, month: 3 })).toBe('2026-03');
  });

  it('разбирает значение поля месяца обратно', () => {
    expect(inputToPeriod('2026-03')).toEqual({ year: 2026, month: 3 });
  });

  it('переживает круг туда-обратно', () => {
    const period = { year: 2026, month: 11 };
    expect(inputToPeriod(periodToInput(period))).toEqual(period);
  });
});
