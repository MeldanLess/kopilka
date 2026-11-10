import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { MonthlySummary } from '../types';
import { formatMoney } from '../utils/money';

const MONTH_LABELS = [
  'янв',
  'фев',
  'мар',
  'апр',
  'май',
  'июн',
  'июл',
  'авг',
  'сен',
  'окт',
  'ноя',
  'дек',
];

/**
 * Столбчатая диаграмма «доходы и расходы по месяцам».
 *
 * Это главный ответ на вопрос «как я трачу»: за один месяц цифры ничего не
 * говорят, а за полгода видно, где деньги утекают.
 */
export function MonthlyChart({ months }: { months: MonthlySummary[] }) {
  const data = months.map((summary) => ({
    name: `${MONTH_LABELS[summary.month - 1] ?? summary.month} ${String(summary.year).slice(2)}`,
    Доходы: Number(summary.income),
    Расходы: Number(summary.expense),
  }));

  if (data.length === 0) {
    return <p className="muted">Недостаточно данных для графика.</p>;
  }

  return (
    <div className="chart">
      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="name" tick={{ fontSize: 12 }} />
          <YAxis tick={{ fontSize: 12 }} tickFormatter={(value: number) => String(value)} />
          <Tooltip
            formatter={(value: unknown) => formatMoney(String(value))}
            cursor={{ fill: 'rgba(0, 0, 0, 0.04)' }}
          />
          <Legend />
          <Bar dataKey="Доходы" fill="#22c55e" radius={[4, 4, 0, 0]} />
          <Bar dataKey="Расходы" fill="#ef4444" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
