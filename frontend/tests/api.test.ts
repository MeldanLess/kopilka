/**
 * Клиент API: заголовки, разбор ответов и ошибки.
 *
 * Здесь нет настоящего сервера — `fetch` подменён. Проверяется ровно то, что
 * клиент обещает: заголовок авторизации, форма вместо JSON на входе и понятное
 * сообщение об ошибке вместо `undefined`.
 */

import { afterEach, describe, expect, it, vi } from 'vitest';
import { ApiError, api, download, toQuery } from '../src/api/client';

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('toQuery', () => {
  it('убирает пустые значения', () => {
    expect(toQuery({ kind: 'expense', search: '', limit: undefined })).toBe('?kind=expense');
  });

  it('возвращает пустую строку, если фильтр пуст', () => {
    expect(toQuery({})).toBe('');
  });
});

describe('api.get', () => {
  it('добавляет заголовок авторизации', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ ok: true }));
    vi.stubGlobal('fetch', fetchMock);

    await api.get('/auth/me', { token: 'secret-token' });

    const [, options] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect((options.headers as Record<string, string>).Authorization).toBe('Bearer secret-token');
  });

  it('разбирает JSON-ответ', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({ status: 'ok' })));

    await expect(api.get<{ status: string }>('/health')).resolves.toEqual({ status: 'ok' });
  });

  it('превращает ошибку сервера в ApiError с текстом из detail', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(jsonResponse({ detail: 'Неверная почта или пароль' }, 401)),
    );

    await expect(api.get('/auth/me')).rejects.toThrow('Неверная почта или пароль');
  });

  it('не роняется на пустом теле ответа', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(null, { status: 204 })));

    await expect(api.delete('/transactions/1')).resolves.toBeNull();
  });
});

describe('api.postForm', () => {
  it('отправляет форму, а не JSON', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ access_token: 'x' }));
    vi.stubGlobal('fetch', fetchMock);

    await api.postForm('/auth/token', new URLSearchParams({ username: 'a@b.ru', password: 'x' }));

    const [, options] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect((options.headers as Record<string, string>)['Content-Type']).toBe(
      'application/x-www-form-urlencoded',
    );
    expect(String(options.body)).toBe('username=a%40b.ru&password=x');
  });
});

describe('download', () => {
  it('берёт имя файла из заголовка Content-Disposition', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response('a,b', {
          status: 200,
          headers: { 'Content-Disposition': 'attachment; filename="kopilka-all.csv"' },
        }),
      ),
    );

    const result = await download('/export/transactions.csv', { token: 'secret-token' });

    expect(result.filename).toBe('kopilka-all.csv');
  });

  it('подставляет своё имя, если сервер его не прислал', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(new Response('a,b', { status: 200 })),
    );

    const result = await download('/export/transactions.csv');

    expect(result.filename).toBe('kopilka.csv');
  });
});

describe('ApiError', () => {
  it('хранит код и тело ответа', () => {
    const error = new ApiError(409, 'Категория не найдена', { detail: 'Категория не найдена' });

    expect(error.status).toBe(409);
    expect(error.body).toEqual({ detail: 'Категория не найдена' });
    expect(error).toBeInstanceOf(Error);
  });
});
