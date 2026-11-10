/**
 * Форматирование денег и дат.
 *
 * Здесь проверяется ровно то, ради чего суммы не превращаются в числа:
 * «1 234,56 ₽» должно получаться из строки, а не из float.
 */

import { describe, expect, it } from 'vitest';
import { formatDate, formatMoney, formatMonth, formatShare, parseAmount } from '../src/utils/money';

describe('formatMoney', () => {
  it('разделяет разряды и ставит запятую', () => {
    expect(formatMoney('1234.56')).toBe('1 234,56 ₽');
  });

  it('оставляет маленькие суммы без пробела', () => {
    expect(formatMoney('42.00')).toBe('42,00 ₽');
  });

  it('показывает минус перед отрицательным остатком', () => {
    expect(formatMoney('-1500.00')).toBe('-1 500,00 ₽');
  });

  it('не теряет копейки, которых нет в float', () => {
    // 0.1 + 0.2 в двоичной точке равно 0.30000000000000004 — здесь сумма
    // приходит строкой и остаётся ровно «30,00».
    expect(formatMoney('30.00')).toBe('30,00 ₽');
  });
});

describe('formatShare', () => {
  it('переводит долю в проценты', () => {
    expect(formatShare(0.75)).toBe('75 %');
  });

  it('округляет до десятых долей процента', () => {
    expect(formatShare(0.4235)).toBe('42,4 %');
  });
});

describe('formatMonth', () => {
  it('называет месяц по-русски', () => {
    expect(formatMonth(2026, 11)).toBe('ноябрь 2026');
  });

  it('называет первый месяц январям', () => {
    expect(formatMonth(2026, 1)).toBe('январь 2026');
  });
});

describe('formatDate', () => {
  it('переводит ISO-дату в русский вид', () => {
    expect(formatDate('2026-11-10')).toBe('10.11.2026');
  });
});

describe('parseAmount', () => {
  it('принимает запятую и приводит к каноническому виду', () => {
    expect(parseAmount('1234,5')).toBe('1234.50');
  });

  it('дополняет копейки нулями', () => {
    expect(parseAmount('10')).toBe('10.00');
  });

  it('отклоняет пустое значение', () => {
    expect(parseAmount('')).toBeNull();
  });

  it('отклоняет отрицательную сумму', () => {
    expect(parseAmount('-10')).toBeNull();
  });

  it('отклоняет три знака после запятой', () => {
    expect(parseAmount('10.555')).toBeNull();
  });

  it('отклоняет сумму длиннее, чем вмещает NUMERIC(14, 2)', () => {
    expect(parseAmount('1234567890123.00')).toBeNull();
  });
});
