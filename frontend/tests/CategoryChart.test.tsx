/**
 * Круговая диаграмма: подпись под ней — обычный HTML, и именно её видит
 * человек. Проверяем, что категории и их доли попадают в подпись правильно.
 *
 * Сам график в тестах не рисуется: jsdom не умеет измерять контейнер, и без
 * этого Recharts не рисует SVG. Проверяется та часть, которую написал я.
 */

import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { CategoryChart } from '../src/components/CategoryChart';

const SLICES = [
  {
    category_id: '22222222-2222-2222-2222-222222222222',
    name: 'Еда',
    color: '#ef4444',
    amount: '450.50',
    count: 3,
    share: 0.75,
  },
  {
    category_id: '33333333-3333-3333-3333-333333333333',
    name: 'Транспорт',
    color: '#3b82f6',
    amount: '150.17',
    count: 1,
    share: 0.25,
  },
];

describe('CategoryChart', () => {
  it('показывает категории и их доли', () => {
    render(<CategoryChart slices={SLICES} kind="expense" />);

    expect(screen.getByText('Еда')).toBeInTheDocument();
    expect(screen.getByText('75 %')).toBeInTheDocument();
    expect(screen.getByText('Транспорт')).toBeInTheDocument();
    expect(screen.getByText('25 %')).toBeInTheDocument();
  });

  it('не рисует диаграмму, если операций не было', () => {
    render(<CategoryChart slices={[]} kind="expense" />);

    expect(screen.getByText('В этом месяце операций не было.')).toBeInTheDocument();
  });
});
