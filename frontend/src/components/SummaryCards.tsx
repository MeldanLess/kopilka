import type { MonthlySummary } from '../types';
import { formatMoney } from '../utils/money';

/**
 * Три карточки с итогами месяца: доходы, расходы и остаток.
 *
 * Остаток — это разность первых двух, и он может быть отрицательным. Знак
 * «минус» здесь важен: «−1 234,56 ₽» читается как «в минусе», а
 * «1 234,56 ₽» с классом `negative` — нет.
 */
export function SummaryCards({ summary }: { summary: MonthlySummary | null }) {
  const income = summary?.income ?? '0.00';
  const expense = summary?.expense ?? '0.00';
  const balance = summary?.balance ?? '0.00';

  return (
    <div className="cards">
      <div className="card">
        <span className="card__label">Доходы</span>
        <strong className="card__value card__value--income">{formatMoney(income)}</strong>
      </div>
      <div className="card">
        <span className="card__label">Расходы</span>
        <strong className="card__value card__value--expense">{formatMoney(expense)}</strong>
      </div>
      <div className="card">
        <span className="card__label">Остаток</span>
        <strong
          className={
            balance.startsWith('-')
              ? 'card__value card__value--negative'
              : 'card__value card__value--balance'
          }
        >
          {formatMoney(balance)}
        </strong>
      </div>
    </div>
  );
}
