import { useAuth } from './auth/context';
import { Dashboard } from './components/Dashboard';
import { LoginForm } from './components/LoginForm';

/**
 * Точка входа интерфейса.
 *
 * Всё приложение — это два состояния: пользователь не вошёл (форма входа) или
 * вошёл (главный экран). Отдельный маршрутизатор для этого не нужен — двух
 * состояний не тянут библиотеку, а вот `localStorage` с токеном нужен
 * всегда.
 */
export default function App() {
  const { token, loading } = useAuth();

  if (loading) {
    return <main className="loading">Проверяем сохранённый токен…</main>;
  }

  if (!token) {
    return <LoginForm />;
  }

  return <Dashboard token={token} />;
}
