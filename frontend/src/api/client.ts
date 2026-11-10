/**
 * Небольшая типизированная обёртка над fetch.
 *
 * Четыре вещи, которых нет у голого `fetch`:
 *   1. одно место для базового адреса, поэтому окружение настраивается один раз;
 *   2. типизированная ошибка, поэтому неудачный запрос — это то, что можно
 *      перехватить, а не `undefined` тремя кадрами ниже;
 *   3. JSON на входе и на выходе, вместе с подразумеваемыми заголовками;
 *   4. отправка формы — `/auth/token` ждёт `application/x-www-form-urlencoded`,
 *      а не JSON.
 */

const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

export class ApiError extends Error {
  readonly status: number;
  readonly body: unknown;

  constructor(status: number, message: string, body: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.body = body;
  }
}

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE';
  body?: unknown;
  /** Тело запроса как форма — для OAuth2 password flow. */
  form?: URLSearchParams;
  token?: string | null;
  signal?: AbortSignal;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, form, token, signal } = options;

  const headers: Record<string, string> = { Accept: 'application/json' };
  if (body !== undefined) {
    headers['Content-Type'] = 'application/json';
  }
  if (form !== undefined) {
    headers['Content-Type'] = 'application/x-www-form-urlencoded';
  }
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const init: RequestInit = { method, headers };
  // `exactOptionalPropertyTypes` запрещает писать `undefined` в необязательные
  // поля — поэтому необязательные куски добавляем по одному.
  if (signal !== undefined) {
    init.signal = signal;
  }
  const requestBody = form ?? (body === undefined ? undefined : JSON.stringify(body));
  if (requestBody !== undefined) {
    init.body = requestBody;
  }

  const response = await fetch(`${BASE_URL}${path}`, init);

  // У 204 нет тела, которое можно разобрать, а `response.json()` падает на
  // пустом теле.
  const text = await response.text();
  const payload: unknown = text ? JSON.parse(text) : null;

  if (!response.ok) {
    const detail =
      typeof payload === 'object' && payload !== null && 'detail' in payload
        ? String((payload as { detail: unknown }).detail)
        : `Запрос завершился с кодом ${response.status}`;
    throw new ApiError(response.status, detail, payload);
  }

  return payload as T;
}

/** Собрать строку запроса из фильтра, убрав пустые значения. */
export function toQuery(params: Record<string, string | number | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== '') {
      search.set(key, String(value));
    }
  }
  const query = search.toString();
  return query ? `?${query}` : '';
}

/**
 * Скачать файл, не разбирая его содержимое.
 *
 * Обычный `fetch` здесь не годится: у CSV нет JSON-тела, а заголовок
 * `Content-Disposition` с именем файла нужно достать отдельно.
 */
export async function download(
  path: string,
  options: { token?: string | null; signal?: AbortSignal } = {},
): Promise<{ blob: Blob; filename: string }> {
  const { token, signal } = options;
  const headers: Record<string, string> = {};
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const init: RequestInit = { headers };
  if (signal !== undefined) {
    init.signal = signal;
  }

  const response = await fetch(`${BASE_URL}${path}`, init);
  if (!response.ok) {
    throw new ApiError(response.status, `Загрузка не удалась: код ${response.status}`, null);
  }

  const disposition = response.headers.get('content-disposition') ?? '';
  const match = /filename="([^"]+)"/.exec(disposition);
  return {
    blob: await response.blob(),
    filename: match?.[1] ?? 'kopilka.csv',
  };
}

export const api = {
  get: <T>(path: string, options: Omit<RequestOptions, 'method' | 'body' | 'form'> = {}) =>
    request<T>(path, { ...options, method: 'GET' }),
  post: <T>(
    path: string,
    body?: unknown,
    options: Omit<RequestOptions, 'method' | 'body'> = {},
  ) => request<T>(path, { ...options, method: 'POST', body }),
  postForm: <T>(path: string, form: URLSearchParams, options: Omit<RequestOptions, 'method' | 'form'> = {}) =>
    request<T>(path, { ...options, method: 'POST', form }),
  patch: <T>(
    path: string,
    body?: unknown,
    options: Omit<RequestOptions, 'method' | 'body'> = {},
  ) => request<T>(path, { ...options, method: 'PATCH', body }),
  put: <T>(
    path: string,
    body?: unknown,
    options: Omit<RequestOptions, 'method' | 'body'> = {},
  ) => request<T>(path, { ...options, method: 'PUT', body }),
  delete: <T>(path: string, options: Omit<RequestOptions, 'method' | 'body' | 'form'> = {}) =>
    request<T>(path, { ...options, method: 'DELETE' }),
};
