/**
 * Форма операции: правила, которые видно пользователю.
 *
 * Ключевое из них — категории фильтруются по виду операции: правило
 * «вид операции совпадает с видом категории» проверяет и бэкенд, но
 * заставлять человека выбрать неподходящую категорию, чтобы получить 409, —
 * плохой интерфейс.
 */

import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { transactionsApi } from '../src/api/kopilka';
import { TransactionForm } from '../src/components/TransactionForm';
import type { Category, Transaction } from '../src/types';

vi.mock('../src/api/kopilka', () => ({
  transactionsApi: { create: vi.fn() },
}));

const CATEGORIES: Category[] = [
  {
    id: '22222222-2222-2222-2222-222222222222',
    owner_id: '11111111-1111-1111-1111-111111111111',
    name: 'Еда',
    kind: 'expense',
    color: '#ef4444',
    created_at: '2026-11-01T00:00:00Z',
  },
  {
    id: '33333333-3333-3333-3333-333333333333',
    owner_id: '11111111-1111-1111-1111-111111111111',
    name: 'Зарплата',
    kind: 'income',
    color: '#22c55e',
    created_at: '2026-11-01T00:00:00Z',
  },
];

const TRANSACTION: Transaction = {
  id: '44444444-4444-4444-4444-444444444444',
  owner_id: '11111111-1111-1111-1111-111111111111',
  category_id: '22222222-2222-2222-2222-222222222222',
  kind: 'expense',
  amount: '1234.50',
  occurred_on: '2026-11-10',
  note: null,
  created_at: '2026-11-10T00:00:00Z',
};

function renderForm(onCreated = vi.fn()) {
  render(
    <TransactionForm token="token-123" categories={CATEGORIES} onCreated={onCreated} />,
  );
  return { onCreated };
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe('TransactionForm', () => {
  it('показывает только категории выбранного вида', () => {
    renderForm();

    expect(screen.getByRole('option', { name: 'Еда' })).toBeInTheDocument();
    expect(screen.queryByRole('option', { name: 'Зарплата' })).not.toBeInTheDocument();
  });

  it('после переключения на доход показывает доходные категории', () => {
    renderForm();

    fireEvent.click(screen.getByRole('button', { name: 'Доход' }));

    expect(screen.getByRole('option', { name: 'Зарплата' })).toBeInTheDocument();
    expect(screen.queryByRole('option', { name: 'Еда' })).not.toBeInTheDocument();
  });

  it('не записывает операцию без суммы', () => {
    renderForm();

    fireEvent.change(screen.getByLabelText('Категория'), {
      target: { value: CATEGORIES[0]!.id },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Записать' }));

    expect(screen.getByRole('alert')).toHaveTextContent('Сумма');
    expect(transactionsApi.create).not.toHaveBeenCalled();
  });

  it('не записывает операцию без категории', () => {
    renderForm();

    fireEvent.change(screen.getByLabelText('Сумма'), { target: { value: '100' } });
    fireEvent.click(screen.getByRole('button', { name: 'Записать' }));

    expect(screen.getByRole('alert')).toHaveTextContent('категорию');
    expect(transactionsApi.create).not.toHaveBeenCalled();
  });

  it('отправляет сумму в каноническом виде', async () => {
    vi.mocked(transactionsApi.create).mockResolvedValue(TRANSACTION);
    const { onCreated } = renderForm();

    fireEvent.change(screen.getByLabelText('Категория'), {
      target: { value: CATEGORIES[0]!.id },
    });
    fireEvent.change(screen.getByLabelText('Сумма'), { target: { value: '1234,5' } });
    fireEvent.click(screen.getByRole('button', { name: 'Записать' }));

    await waitFor(() => expect(transactionsApi.create).toHaveBeenCalled());
    expect(transactionsApi.create).toHaveBeenCalledWith(
      'token-123',
      expect.objectContaining({ amount: '1234.50', kind: 'expense' }),
    );
    await waitFor(() => expect(onCreated).toHaveBeenCalled());
  });

  it('не отправляет заметку, если она пустая', async () => {
    vi.mocked(transactionsApi.create).mockResolvedValue(TRANSACTION);
    renderForm();

    fireEvent.change(screen.getByLabelText('Категория'), {
      target: { value: CATEGORIES[0]!.id },
    });
    fireEvent.change(screen.getByLabelText('Сумма'), { target: { value: '10' } });
    fireEvent.click(screen.getByRole('button', { name: 'Записать' }));

    await waitFor(() => expect(transactionsApi.create).toHaveBeenCalled());
    const [, payload] = vi.mocked(transactionsApi.create).mock.calls[0] as [
      string,
      Record<string, unknown>,
    ];
    expect(payload).not.toHaveProperty('note');
  });
});
