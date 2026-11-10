/**
 * Типизированные вызовы API «Копилки».
 *
 * Здесь нет ни одного URL в компонентах: если адрес эндпоинта поменяется,
 * он поменяется в одном файле, а не по всему интерфейсу.
 */

import { api, download, toQuery } from './client';
import type {
  Category,
  Kind,
  MonthlySummary,
  Page,
  Token,
  Transaction,
  TransactionFilter,
  User,
} from '../types';

export const authApi = {
  /** Зарегистрировать аккаунт. Возвращает пользователя без токена. */
  register: (email: string, password: string, fullName?: string) =>
    api.post<User>('/auth/register', {
      email,
      password,
      ...(fullName ? { full_name: fullName } : {}),
    }),

  /** Войти и получить токен. Форма, а не JSON — этого ждёт OAuth2. */
  login: (email: string, password: string) =>
    api.postForm<Token>(
      '/auth/token',
      new URLSearchParams({ username: email, password }),
    ),

  /** Кто я — по уже полученному токену. */
  me: (token: string) => api.get<User>('/auth/me', { token }),
};

export const categoriesApi = {
  list: (token: string, kind?: Kind) =>
    api.get<Category[]>(`/categories${toQuery({ kind })}`, { token }),

  create: (token: string, payload: { name: string; kind: Kind; color?: string }) =>
    api.post<Category>('/categories', payload, { token }),

  update: (token: string, id: string, payload: { name?: string; color?: string }) =>
    api.patch<Category>(`/categories/${id}`, payload, { token }),

  remove: (token: string, id: string) => api.delete<void>(`/categories/${id}`, { token }),
};

export const transactionsApi = {
  list: (token: string, filter: TransactionFilter = {}) =>
    api.get<Page<Transaction>>(
      `/transactions${toQuery({
        kind: filter.kind,
        category_id: filter.category_id,
        date_from: filter.date_from,
        date_to: filter.date_to,
        search: filter.search,
        limit: filter.limit,
        offset: filter.offset,
      })}`,
      { token },
    ),

  create: (
    token: string,
    payload: {
      category_id: string;
      kind: Kind;
      amount: string;
      occurred_on: string;
      note?: string;
    },
  ) => api.post<Transaction>('/transactions', payload, { token }),

  update: (
    token: string,
    id: string,
    payload: { amount?: string; note?: string; category_id?: string; kind?: Kind },
  ) => api.patch<Transaction>(`/transactions/${id}`, payload, { token }),

  remove: (token: string, id: string) => api.delete<void>(`/transactions/${id}`, { token }),
};

export const summaryApi = {
  monthly: (token: string, year: number, month: number) =>
    api.get<MonthlySummary>(`/summary/monthly${toQuery({ year, month })}`, { token }),
};

export const exportApi = {
  /** Выгрузить операции в CSV. Возвращает файл и имя, предложенное сервером. */
  csv: (token: string, dateFrom?: string, dateTo?: string) =>
    download(`/export/transactions.csv${toQuery({ date_from: dateFrom, date_to: dateTo })}`, {
      token,
    }),
};
