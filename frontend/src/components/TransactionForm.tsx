import { useEffect, useState, type FormEvent } from 'react';
import { ApiError } from '../api/client';
import { transactionsApi } from '../api/kopilka';
import type { Category, Kind } from '../types';
import { parseAmount } from '../utils/money';
import { today } from '../utils/period';

interface Props {
  token: string;
  categories: Category[];
  /** Вызывается после успешного сохранения — список и сводка перезагружаются. */
  onCreated: () => void;
}

/**
 * Форма записи операции.
 *
 * Правило «вид операции совпадает с видом категории» проверяет и бэкенд, но
 * здесь оно ещё и в интерфейсе: показываются только категории выбранного
 * вида. Заставлять человека выбрать заведомо неподходящую категорию, чтобы
 * потом получить 409, — плохой интерфейс.
 */
export function TransactionForm({ token, categories, onCreated }: Props) {
  const [kind, setKind] = useState<Kind>('expense');
  const [categoryId, setCategoryId] = useState('');
  const [amount, setAmount] = useState('');
  const [occurredOn, setOccurredOn] = useState(today());
  const [note, setNote] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const available = categories.filter((category) => category.kind === kind);

  // Смена вида означает смену списка категорий: выбранная категория может
  // оказаться другого вида, и её нужно сбросить.
  useEffect(() => {
    setCategoryId('');
  }, [kind]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    const normalised = parseAmount(amount);
    if (normalised === null) {
      setError('Сумма — положительное число, максимум два знака после запятой.');
      return;
    }
    if (!categoryId) {
      setError('Выберите категорию операции.');
      return;
    }
    if (!occurredOn) {
      setError('Укажите дату операции.');
      return;
    }

    setBusy(true);
    try {
      await transactionsApi.create(token, {
        category_id: categoryId,
        kind,
        amount: normalised,
        occurred_on: occurredOn,
        ...(note ? { note } : {}),
      });
      setAmount('');
      setNote('');
      onCreated();
    } catch (cause: unknown) {
      setError(cause instanceof ApiError ? cause.message : 'Не удалось сохранить операцию.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel">
      <h2>Новая операция</h2>

      <div className="tabs">
        <button
          type="button"
          className={kind === 'expense' ? 'tab tab--active' : 'tab'}
          onClick={() => setKind('expense')}
        >
          Расход
        </button>
        <button
          type="button"
          className={kind === 'income' ? 'tab tab--active' : 'tab'}
          onClick={() => setKind('income')}
        >
          Доход
        </button>
      </div>

      <form onSubmit={handleSubmit} noValidate>
        <label>
          Категория
          <select value={categoryId} onChange={(event) => setCategoryId(event.target.value)}>
            <option value="">— выберите —</option>
            {available.map((category) => (
              <option key={category.id} value={category.id}>
                {category.name}
              </option>
            ))}
          </select>
        </label>

        <label>
          Сумма
          <input
            type="text"
            inputMode="decimal"
            placeholder="1234,56"
            value={amount}
            onChange={(event) => setAmount(event.target.value)}
          />
        </label>

        <label>
          Дата
          <input
            type="date"
            value={occurredOn}
            onChange={(event) => setOccurredOn(event.target.value)}
          />
        </label>

        <label>
          Заметка
          <input
            type="text"
            maxLength={500}
            placeholder="За что"
            value={note}
            onChange={(event) => setNote(event.target.value)}
          />
        </label>

        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}

        <button type="submit" className="button button--primary" disabled={busy}>
          {busy ? 'Сохраняем…' : 'Записать'}
        </button>
      </form>
    </section>
  );
}
