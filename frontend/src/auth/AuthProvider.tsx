import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';
import { authApi } from '../api/kopilka';
import { AuthContext, type AuthContextValue } from './context';
import type { User } from '../types';

/**
 * Ключ, под которым токен лежит в `localStorage`.
 *
 * **Токен хранится в браузере, а не в cookie.** Это сознательный размен:
 * `localStorage` доступен JavaScript, поэтому токен можно выкрасть через XSS.
 * Взамен не нужно разбираться с `SameSite`, `Secure` и с тем, как cookie
 * переживает перезагрузку страницы. Для личного трекера, где в токене нет
 * ничего, кроме идентификатора пользователя, размен выгоден; для банковского
 * приложения — нет, и там нужен `HttpOnly`-cookie и защита от CSRF.
 */
const TOKEN_KEY = 'kopilka.token';

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  // При перезагрузке страницы токен остаётся в localStorage. Проверяем его
  // один раз: сервер — источник правды о том, действителен ли он ещё.
  useEffect(() => {
    const stored = localStorage.getItem(TOKEN_KEY);
    if (!stored) {
      setLoading(false);
      return;
    }

    let cancelled = false;
    authApi
      .me(stored)
      .then((current) => {
        if (cancelled) return;
        setToken(stored);
        setUser(current);
      })
      .catch(() => {
        // Токен протух или отозван — молча выходим, чтобы не оставлять
        // пользователя в состоянии «вроде бы вошёл, но ничего не работает».
        localStorage.removeItem(TOKEN_KEY);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const result = await authApi.login(email, password);
    localStorage.setItem(TOKEN_KEY, result.access_token);
    setToken(result.access_token);
    setUser(result.user);
  }, []);

  const register = useCallback(async (email: string, password: string, fullName?: string) => {
    await authApi.register(email, password, fullName);
    // После регистрации сразу входим: пользователю не нужно снова вводить
    // пароль только что введённый.
    await login(email, password);
  }, [login]);

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    setToken(null);
    setUser(null);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({ token, user, loading, login, register, logout }),
    [token, user, loading, login, register, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
