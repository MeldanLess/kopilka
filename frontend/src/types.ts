/**
 * Типы публичного контракта API.
 *
 * Они повторяют схемы бэкенда один в один: смена контракта должна быть видна
 * и в TypeScript, и в FastAPI, а не разъезжаться молча.
 *
 * **Сумма приходит строкой.** Так её и отдаёт бэкенд, и это не формальность:
 * если превратить сумму в число IEEE 754, то при сложении появятся
 * «1234,5599999999999». Строка разбирается тем кодом, в котором нет двоичной
 * точки.
 */

export type Kind = 'income' | 'expense';

export interface User {
  id: string;
  email: string;
  full_name: string | null;
  created_at: string;
}

export interface Token {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface Category {
  id: string;
  owner_id: string;
  name: string;
  kind: Kind;
  color: string;
  created_at: string;
}

export interface Transaction {
  id: string;
  owner_id: string;
  category_id: string;
  kind: Kind;
  amount: string;
  occurred_on: string;
  note: string | null;
  created_at: string;
}

export interface Page<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface CategorySlice {
  category_id: string;
  name: string;
  color: string;
  amount: string;
  count: number;
  share: number;
}

export interface MonthlySummary {
  year: number;
  month: number;
  income: string;
  expense: string;
  balance: string;
  by_category: CategorySlice[];
}

/**
 * Параметры фильтрации списка операций.
 *
 * `| undefined` в необязательных полях — не опечатка: проект собран с
 * `exactOptionalPropertyTypes`, и без этого сбросить фильтр (`kind: undefined`)
 * было бы ошибкой типов.
 */
export interface TransactionFilter {
  kind?: Kind | undefined;
  category_id?: string | undefined;
  date_from?: string | undefined;
  date_to?: string | undefined;
  search?: string | undefined;
  limit?: number | undefined;
  offset?: number | undefined;
}
