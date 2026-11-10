import { useState, type FormEvent } from 'react';
import { ApiError } from '../api/client';
import { categoriesApi } from '../api/kopilka';
import type { Category, Kind } from '../types';

interface Props {
  token: string;
  categories: Category[];
  /** Вызывается после любого изменения — сводка пересчитывается. */
  onChanged: () => void;
}

/** Палитра для новых категорий — по одному цвету на вид. */
const PALETTE = ['#22c55e', '#84cc16', '#eab308', '#ef4444', '#f97316', '#8b5cf6', '#06b6d4'];

/**
 * Управление категориями.
 *
 * Категорию с операциями удалить нельзя — так решил бэкенд, и это правильно:
 * молча терять историю денег нельзя. Здесь об этом сказано прямо, потому что
 * сообщение об ошибке приходит с сервера.
 */
export function CategoryPanel({ token, categories, onChanged }: Props) {
  const [name, setName] = useState('');
  const [kind, setKind] = useState<Kind>('expense');
  const [color, setColor] = useState(PALETTE[3] ?? '#6b7280');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const income = categories.filter((category) => category.kind === 'income');
  const expense = categories.filter((category) => category.kind === 'expense');

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    if (!name.trim()) {
      setError('Название категории не может быть пустым.');
      return;
    }
    setBusy(true);
    try {
      await categoriesApi.create(token, { name: name.trim(), kind, color });
      setName('');
      onChanged();
    } catch (cause: unknown) {
      setError(cause instanceof ApiError ? cause.message : 'Не удалось создать категорию.');
    } finally {
      setBusy(false);
    }
  }

  async function handleRemove(id: string) {
    setError(null);
    try {
      await categoriesApi.remove(token, id);
      onChanged();
    } catch (cause: unknown) {
      setError(cause instanceof ApiError ? cause.message : 'Не удалось удалить категорию.');
    }
  }

  function renderGroup(title: string, group: Category[]) {
    return (
      <div className="category-group">
        <h3>{title}</h3>
        {group.length === 0 ? (
          <p className="muted">Пока пусто.</p>
        ) : (
          <ul className="category-list">
            {group.map((category) => (
              <li key={category.id} className="category-list__item">
                <span className="legend__dot" style={{ background: category.color }} />
                <span>{category.name}</span>
                <button
                  type="button"
                  className="button button--ghost"
                  onClick={() => void handleRemove(category.id)}
                >
                  Удалить
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    );
  }

  return (
    <section className="panel">
      <h2>Категории</h2>

      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}

      <form onSubmit={handleCreate} className="category-form">
        <label>
          Название
          <input
            type="text"
            value={name}
            maxLength={80}
            placeholder="Например, «Еда»"
            onChange={(event) => setName(event.target.value)}
          />
        </label>
        <label>
          Вид
          <select value={kind} onChange={(event) => setKind(event.target.value as Kind)}>
            <option value="expense">Расход</option>
            <option value="income">Доход</option>
          </select>
        </label>
        <label>
          Цвет
          <input
            type="color"
            value={color}
            onChange={(event) => setColor(event.target.value)}
          />
        </label>
        <button type="submit" className="button" disabled={busy}>
          Добавить
        </button>
      </form>

      {renderGroup('Доходы', income)}
      {renderGroup('Расходы', expense)}
    </section>
  );
}
