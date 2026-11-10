import { useCallback, useEffect, useMemo, useState } from 'react';
import { ApiError } from '../api/client';
import { categoriesApi, exportApi, summaryApi, transactionsApi } from '../api/kopilka';
import { useAuth } from '../auth/context';
import type { Category, Kind, MonthlySummary, Transaction, TransactionFilter } from '../types';
import { formatMonth } from '../utils/money';
import { currentPeriod, inputToPeriod, lastMonths, periodToInput } from '../utils/period';
import { CategoryChart } from './CategoryChart';
import { CategoryPanel } from './CategoryPanel';
import { MonthlyChart } from './MonthlyChart';
import { SummaryCards } from './SummaryCards';
import { TransactionForm } from './TransactionForm';
import { TransactionList } from './TransactionList';

/** Сколько месяцев показывает график динамики. */
const TREND_MONTHS = 6;

interface Props {
  token: string;
}

/**
 * Главный экран: сводка, графики, форма операции, список и категории.
 *
 * Все данные загружаются одним заходом и перезагружаются целиком после любого
 * изменения. Для трекера с сотнями операций это честный размен: сложное
 * частичное обновление даёт выигрыш в миллисекундах, а взамен появляется
 * рассинхрон между списком, сводкой и диаграммой — а это уже настоящая
 * ошибка, которую увидит пользователь.
 */
export function Dashboard({ token }: Props) {
  const { user, logout } = useAuth();

  const [period, setPeriod] = useState(currentPeriod);
  const [filter, setFilter] = useState<TransactionFilter>({ limit: 50 });
  const [summary, setSummary] = useState<MonthlySummary | null>(null);
  const [trend, setTrend] = useState<MonthlySummary[]>([]);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);

  const months = useMemo(() => lastMonths(period, TREND_MONTHS), [period]);

  const reload = useCallback(async () => {
    setError(null);
    try {
      const [trendResponses, transactionsResponse, categoriesResponse] = await Promise.all([
        Promise.all(months.map((month) => summaryApi.monthly(token, month.year, month.month))),
        transactionsApi.list(token, filter),
        categoriesApi.list(token),
      ]);

      setTrend(trendResponses);
      // Последний месяц графика — это и есть выбранный месяц.
      setSummary(trendResponses[trendResponses.length - 1] ?? null);
      setTransactions(transactionsResponse.items);
      setCategories(categoriesResponse);
    } catch (cause: unknown) {
      setError(cause instanceof ApiError ? cause.message : 'Не удалось загрузить данные.');
    } finally {
      setLoading(false);
    }
  }, [token, months, filter]);

  useEffect(() => {
    void reload();
  }, [reload]);

  async function handleExport() {
    setError(null);
    setExporting(true);
    try {
      const { blob, filename } = await exportApi.csv(token);
      // Файл скачивается через временную ссылку: обычная ссылка не умеет
      // приложить заголовок авторизации, а выгрузка без токена — это 401.
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (cause: unknown) {
      setError(cause instanceof ApiError ? cause.message : 'Не удалось выгрузить операции.');
    } finally {
      setExporting(false);
    }
  }

  const slices = summary?.by_category ?? [];

  return (
    <main className="app">
      <header className="app__header">
        <div>
          <h1>Копилка</h1>
          <p className="muted">{user?.email ?? 'Гость'}</p>
        </div>
        <div className="app__actions">
          <label className="inline">
            Месяц
            <input
              type="month"
              value={periodToInput(period)}
              onChange={(event) => setPeriod(inputToPeriod(event.target.value))}
            />
          </label>
          <button
            type="button"
            className="button"
            disabled={exporting}
            onClick={() => void handleExport()}
          >
            {exporting ? 'Готовим файл…' : 'Выгрузить CSV'}
          </button>
          <button type="button" className="button button--ghost" onClick={logout}>
            Выйти
          </button>
        </div>
      </header>

      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}

      <h2 className="app__period">{formatMonth(period.year, period.month)}</h2>

      <SummaryCards summary={summary} />

      <div className="grid">
        <section className="panel">
          <h2>Куда ушли деньги</h2>
          <CategoryChart slices={slices} kind="expense" />
        </section>

        <section className="panel">
          <h2>Динамика за полгода</h2>
          <MonthlyChart months={trend} />
        </section>
      </div>

      <div className="grid">
        <TransactionForm token={token} categories={categories} onCreated={() => void reload()} />
        <CategoryPanel token={token} categories={categories} onChanged={() => void reload()} />
      </div>

      <section className="panel">
        <h2>Операции</h2>

        <div className="filters">
          <label className="inline">
            Вид
            <select
              value={filter.kind ?? ''}
              onChange={(event) =>
                setFilter((current) => ({
                  ...current,
                  kind: event.target.value ? (event.target.value as Kind) : undefined,
                }))
              }
            >
              <option value="">Все</option>
              <option value="income">Доходы</option>
              <option value="expense">Расходы</option>
            </select>
          </label>

          <label className="inline">
            Категория
            <select
              value={filter.category_id ?? ''}
              onChange={(event) =>
                setFilter((current) => ({
                  ...current,
                  category_id: event.target.value || undefined,
                }))
              }
            >
              <option value="">Все</option>
              {categories.map((category) => (
                <option key={category.id} value={category.id}>
                  {category.name}
                </option>
              ))}
            </select>
          </label>

          <label className="inline">
            Поиск
            <input
              type="search"
              placeholder="По заметке"
              value={filter.search ?? ''}
              onChange={(event) =>
                setFilter((current) => ({ ...current, search: event.target.value || undefined }))
              }
            />
          </label>
        </div>

        {loading ? <p className="muted">Загружаем…</p> : <TransactionList token={token} transactions={transactions} categories={categories} onChanged={() => void reload()} />}
      </section>
    </main>
  );
}
