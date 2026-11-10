import { useState, type FormEvent } from 'react';
import { ApiError } from '../api/client';
import { useAuth } from '../auth/context';

type Mode = 'login' | 'register';

/**
 * Форма входа и регистрации.
 *
 * Обе формы живут в одном компоненте, потому что отличаются тремя полями и
 * одной кнопкой; держать два почти одинаковых компонента ради этого — значит
 * завести два места, где потом что-нибудь забудут поправить.
 */
export function LoginForm() {
  const { login, register } = useAuth();

  const [mode, setMode] = useState<Mode>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setBusy(true);
    try {
      if (mode === 'login') {
        await login(email, password);
      } else {
        await register(email, password, fullName || undefined);
      }
    } catch (cause: unknown) {
      setError(cause instanceof ApiError ? cause.message : 'Не удалось выполнить вход.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="auth">
      <section className="auth__card">
        <h1>Копилка</h1>
        <p className="muted">Личный финансовый трекер: доходы, расходы и сводка по месяцу.</p>

        <div className="tabs" role="tablist">
          <button
            type="button"
            role="tab"
            aria-selected={mode === 'login'}
            className={mode === 'login' ? 'tab tab--active' : 'tab'}
            onClick={() => setMode('login')}
          >
            Вход
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={mode === 'register'}
            className={mode === 'register' ? 'tab tab--active' : 'tab'}
            onClick={() => setMode('register')}
          >
            Регистрация
          </button>
        </div>

        <form onSubmit={handleSubmit} noValidate>
          {mode === 'register' && (
            <label>
              Имя
              <input
                type="text"
                value={fullName}
                onChange={(event) => setFullName(event.target.value)}
                autoComplete="name"
              />
            </label>
          )}

          <label>
            Почта
            <input
              type="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              autoComplete="email"
            />
          </label>

          <label>
            Пароль
            <input
              type="password"
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
            />
          </label>

          {error && (
            <p className="error" role="alert">
              {error}
            </p>
          )}

          <button type="submit" className="button button--primary" disabled={busy}>
            {busy ? 'Подождите…' : mode === 'login' ? 'Войти' : 'Создать аккаунт'}
          </button>
        </form>
      </section>
    </main>
  );
}
