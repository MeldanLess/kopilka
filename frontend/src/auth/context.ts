import { createContext, useContext } from 'react';
import type { User } from '../types';

/**
 * Состояние аутентификации.
 *
 * Контекст и хук живут в отдельном от компонента файле: правило «файл
 * экспортирует только компоненты» существует ради горячей перезагрузки, и
 * хук в этом файле был бы нарушением без всякой практической пользы.
 */
export interface AuthContextValue {
  /** Токен доступа или `null`, если пользователь не вошёл. */
  token: string | null;
  /** Текущий пользователь или `null`. */
  user: User | null;
  /** Идёт ли проверка сохранённого токена при старте. */
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName?: string) => Promise<void>;
  logout: () => void;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

/** Достать состояние аутентификации. */
export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);
  if (value === null) {
    throw new Error('Хук useAuth можно вызывать только внутри AuthProvider');
  }
  return value;
}
