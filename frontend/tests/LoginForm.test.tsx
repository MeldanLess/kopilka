/**
 * Форма входа: что видит человек и что происходит при ошибке.
 */

import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { AuthProvider } from '../src/auth/AuthProvider';
import { LoginForm } from '../src/components/LoginForm';

function renderForm() {
  return render(
    <AuthProvider>
      <LoginForm />
    </AuthProvider>,
  );
}

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
});

describe('LoginForm', () => {
  it('показывает поля для входа', () => {
    renderForm();

    expect(screen.getByLabelText('Почта')).toBeInTheDocument();
    expect(screen.getByLabelText('Пароль')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Войти' })).toBeInTheDocument();
  });

  it('на регистрации добавляется поле имени', () => {
    renderForm();

    fireEvent.click(screen.getByRole('tab', { name: 'Регистрация' }));

    expect(screen.getByLabelText('Имя')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Создать аккаунт' })).toBeInTheDocument();
  });

  it('показывает сообщение сервера, если вход не удался', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(jsonResponse({ detail: 'Неверная почта или пароль' }, 401)),
    );
    renderForm();

    fireEvent.change(screen.getByLabelText('Почта'), { target: { value: 'a@b.ru' } });
    fireEvent.change(screen.getByLabelText('Пароль'), { target: { value: 'password123' } });
    fireEvent.click(screen.getByRole('button', { name: 'Войти' }));

    await waitFor(() =>
      expect(screen.getByRole('alert')).toHaveTextContent('Неверная почта или пароль'),
    );
  });

  it('сохраняет токен в localStorage после успешного входа', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        jsonResponse({
          access_token: 'token-123',
          token_type: 'bearer',
          expires_in: 3600,
          user: {
            id: '11111111-1111-1111-1111-111111111111',
            email: 'a@b.ru',
            full_name: null,
            created_at: '2026-11-10T00:00:00Z',
          },
        }),
      ),
    );
    renderForm();

    fireEvent.change(screen.getByLabelText('Почта'), { target: { value: 'a@b.ru' } });
    fireEvent.change(screen.getByLabelText('Пароль'), { target: { value: 'password123' } });
    fireEvent.click(screen.getByRole('button', { name: 'Войти' }));

    await waitFor(() => expect(localStorage.getItem('kopilka.token')).toBe('token-123'));
  });

  it('отправляет форму входа, а не JSON', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ access_token: 'token-123' }));
    vi.stubGlobal('fetch', fetchMock);
    renderForm();

    fireEvent.change(screen.getByLabelText('Почта'), { target: { value: 'a@b.ru' } });
    fireEvent.change(screen.getByLabelText('Пароль'), { target: { value: 'password123' } });
    fireEvent.click(screen.getByRole('button', { name: 'Войти' }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    const [, options] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect((options.headers as Record<string, string>)['Content-Type']).toBe(
      'application/x-www-form-urlencoded',
    );
  });
});
