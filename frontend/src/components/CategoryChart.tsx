import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts';
import type { CategorySlice } from '../types';
import { formatMoney, formatShare } from '../utils/money';

/**
 * Круговая диаграмма «куда ушли деньги».
 *
 * Суммы здесь превращаются в числа — Recharts умеет строить графики только по
 * числам. Точность при этом не теряется: её считает бэкенд, а диаграмма
 * показывает пропорции, а не копейки.
 */
export function CategoryChart({
  slices,
  kind,
}: {
  slices: CategorySlice[];
  kind: 'income' | 'expense';
}) {
  const data = slices
    .filter((slice) => slice.amount !== '0.00')
    .map((slice) => ({
      name: slice.name,
      value: Number(slice.amount),
      color: slice.color,
      share: slice.share,
    }));

  if (data.length === 0) {
    return <p className="muted">В этом месяце операций не было.</p>;
  }

  return (
    <div className="chart">
      <ResponsiveContainer width="100%" height={260}>
        <PieChart>
          <Pie
            data={data}
            dataKey="value"
            nameKey="name"
            innerRadius="55%"
            outerRadius="85%"
            paddingAngle={2}
          >
            {data.map((entry) => (
              <Cell key={entry.name} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip formatter={(value: unknown) => formatMoney(String(value))} />
        </PieChart>
      </ResponsiveContainer>

      <ul className="legend">
        {data.map((entry) => (
          <li key={entry.name} className="legend__item">
            <span className="legend__dot" style={{ background: entry.color }} />
            <span className="legend__name">{entry.name}</span>
            <span className="legend__share">{formatShare(entry.share)}</span>
          </li>
        ))}
      </ul>
      <p className="muted">
        {kind === 'income' ? 'Доходы' : 'Расходы'} за выбранный месяц.
      </p>
    </div>
  );
}
