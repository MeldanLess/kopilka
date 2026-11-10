/**
 * Главный экран: сводка подставляется в карточки, операции — в таблицу.
 */

import { render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { AuthProvider } from '../src/auth/AuthProvider';
import { Dashboard } from '../src/components/Dashboard';

vi.mock('../src/api/kopilka', () => ({
  authApi: { me: vi.fn(), login: vi.fn(), register: vi.fn() },
  categoriesApi: { list: vi.fn() },
  transactionsApi: { list: vi.fn() },
  summaryApi: { monthly: vi.fn() },
  exportApi: { csv: vi.fn() },
}));

import { categoriesApi, summaryApi, transactionsApi } from '../src/api/kopilka';

const SUMMARY = {
  year: 2026,
  month: 11,
  income: '1000.00',
  expense: '450.50',
  balance: '549.50',
  by_category: [
    {
      category_id: '22222222-2222-2222-2222-222222222222',
      name: 'Еда',
      color: '#ef4444',
      amount: '450.50',
      count: 3,
      share: 1,
    },
  ],
};

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(summaryApi.monthly).mockResolvedValue(SUMMARY);
  vi.mocked(transactionsApi.list).mockResolvedValue({
    items: [],
    total: 0,
    limit: 50,
    offset: 0,
  });
  vi.mocked(categoriesApi.list).mockResolvedValue([]);
});

describe('Dashboard', () => {
  it('показывает итоги месяца', async () => {
    render(
      <AuthProvider>
        <Dashboard token="token-123" />
      </AuthProvider>,
    );

    await waitFor(() => expect(screen.getByText('1 000,00 ₽')).toBeInTheDocument());
    expect(screen.getByText('450,50 ₽')).toBeInTheDocument();
    expect(screen.getByText('549,50 ₽')).toBeInTheDocument();
  });

  it('показывает, что операций нет', async () => {
    render(
      <AuthProvider>
        <Dashboard token="token-123" />
      </AuthProvider>,
    );

    await waitFor(() => expect(screen.getByText('Операций пока нет.')).toBeInTheDocument());
  });

  it('запрашивает сводку за шесть месяцев', async () => {
    render(
      <AuthProvider>
        <Dashboard token="token-123" />
      </AuthProvider>,
    );

    await waitFor(() => expect(summaryApi.monthly).toHaveBeenCalledTimes(6));
  });
});
