/**
 * Форматирование денег, долей и дат.
 *
 * **Сумма остаётся строкой до самого вывода.** На бэкенде она приходит
 * строкой, и здесь она не превращается в число: двоичная точка не умеет
 * хранить копейку, а напечатать «1 234,56 ₽» можно прямо из строки.
 */

/** Русские названия месяцев — в том виде, в котором их пишут в интерфейсе. */
const MONTH_NAMES = [
  'январь',
  'февраль',
  'март',
  'апрель',
  'май',
  'июнь',
  'июль',
  'август',
  'сентябрь',
  'октябрь',
  'ноябрь',
  'декабрь',
] as const;

/** Сколько целых цифр влезает в `NUMERIC(14, 2)`: 14 минус два знака после запятой. */
const MAX_WHOLE_DIGITS = 12;

/**
 * Разделить целую часть на разряды пробелом: 1234567.89 → «1 234 567,89».
 *
 * Разряды расставляются регулярным выражением по строке, а не через
 * `toLocaleString`: тот работает с числом, а число — это как раз то, чего мы
 * хотим избежать.
 */
export function formatMoney(amount: string): string {
  const negative = amount.startsWith('-');
  const digits = negative ? amount.slice(1) : amount;
  const [whole = '0', fraction = '00'] = digits.split('.');
  const grouped = whole.replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
  return `${negative ? '-' : ''}${grouped},${fraction} ₽`;
}

/** Доля категории: 0.423 → «42,3 %». */
export function formatShare(share: number): string {
  const percent = Math.round(share * 1000) / 10;
  return `${String(percent).replace('.', ',')} %`;
}

/** Название месяца: (2026, 11) → «ноябрь 2026». */
export function formatMonth(year: number, month: number): string {
  const name = MONTH_NAMES[month - 1];
  return `${name ?? month} ${year}`;
}

/** Дата в русском виде: «2026-11-10» → «10.11.2026». */
export function formatDate(iso: string): string {
  const [year = '', month = '', day = ''] = iso.split('-');
  return `${day}.${month}.${year}`;
}

/**
 * Проверить и привести к каноническому виду сумму, введённую пользователем.
 *
 * Принимает «1234,56» и «1234.56», возвращает «1234.56» — ровно то, что
 * ждёт бэкенд. Возвращает `null`, если сумма не имеет смысла.
 */
export function parseAmount(input: string): string | null {
  const cleaned = input.trim().replace(',', '.');
  if (!/^\d+(\.\d{1,2})?$/.test(cleaned)) {
    return null;
  }
  const [whole = '', fraction = ''] = cleaned.split('.');
  if (whole.length > MAX_WHOLE_DIGITS) {
    return null;
  }
  const cents = `${fraction}00`.slice(0, 2);
  return `${whole}.${cents}`;
}
