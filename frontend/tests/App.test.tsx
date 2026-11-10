/**
 * Приложение целиком: пользователь не вошёл — значит видит форму входа.
 */

import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import App from '../src/App';
import { AuthProvider } from '../src/auth/AuthProvider';

describe('App', () => {
  it('показывает форму входа, пока нет токена', () => {
    render(
      <AuthProvider>
        <App />
      </AuthProvider>,
    );

    expect(screen.getByRole('heading', { name: 'Копилка' })).toBeInTheDocument();
    expect(screen.getByLabelText('Почта')).toBeInTheDocument();
    expect(screen.getByLabelText('Пароль')).toBeInTheDocument();
  });
});
