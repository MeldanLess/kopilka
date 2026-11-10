import { useState } from 'react';
import { ApiError } from '../api/client';
import { transactionsApi } from '../api/kopilka';
import type { Category, Transaction } from '../types';
import { formatDate, formatMoney } from '../utils/money';

interface Props {
  token: string;
  transactions: Transaction[];
  categories: Category[];
  /** Вызывается после удаления — сводка и список перезагружаются. */
  onChanged: () => void;
}

/**
 * Список операций.
 *
 * Порядок задаёт бэкенд (по дате, от новых к старым), а интерфейс его не
 * пересортировывает: иначе список разойдётся со сводкой, в которой месяц
 * считается по тому же правилу.
 */
export function TransactionList({ token, transactions, categories, onChanged }: Props) {
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  const byId = new Map<string, Category>(categories.map((c) => [c.id, c] as const));

  async function handleDelete(id: string) {
    setError(null);
    setBusyId(id);
    try {
      await transactionsApi.remove(token, id);
      onChanged();
    } catch (cause: unknown) {
      setError(cause instanceof ApiError ? cause.message : 'Не удалось удалить операцию.');
    } finally {
      setBusyId(null);
    }
  }

  if (transactions.length === 0) {
    return <p className="muted">Операций пока нет.</p>;
  }

  return (
    <>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      <table className="table">
        <thead>
          <tr>
            <th>Дата</th>
            <th>Категория</th>
            <th>Сумма</th>
            <th>Заметка</th>
            <th aria-label="Действия" />
          </tr>
        </thead>
        <tbody>
          {transactions.map((transaction) => {
            const category = byId.get(transaction.category_id);
            return (
              <tr key={transaction.id}>
                <td>{formatDate(transaction.occurred_on)}</td>
                <td>
                  <span
                    className="legend__dot"
                    style={{ background: category?.color ?? '#6b7280' }}
                  />
                  {category?.name ?? 'Без категории'}
                </td>
                <td
                  className={
                    transaction.kind === 'income'
                      ? 'amount amount--income'
                      : 'amount amount--expense'
                  }
                >
                  {transaction.kind === 'income' ? '+' : '−'}
                  {formatMoney(transaction.amount)}
                </td>
                <td className="muted">{transaction.note ?? '—'}</td>
                <td>
                  <button
                    type="button"
                    className="button button--ghost"
                    disabled={busyId === transaction.id}
                    onClick={() => void handleDelete(transaction.id)}
                  >
                    Удалить
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </>
  );
}
