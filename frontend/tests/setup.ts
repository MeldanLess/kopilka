import '@testing-library/jest-dom/vitest';

/**
 * jsdom не умеет измерять размеры элементов, а графики Recharts измеряют
 * контейнер, чтобы подобрать ширину и высоту.
 *
 * Заглушка ничего не проверяет: она нужна только для того, чтобы
 * `ResizeObserver` существовал. Размеры остаются нулевыми, поэтому сам график
 * не рисуется — проверяются тексты, списки и подписи вокруг него.
 */
class ResizeObserverStub {
  observe(): void {}
  unobserve(): void {}
  disconnect(): void {}
}

Object.defineProperty(globalThis, 'ResizeObserver', {
  writable: true,
  configurable: true,
  value: ResizeObserverStub,
});
