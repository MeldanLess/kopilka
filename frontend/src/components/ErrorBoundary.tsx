import { Component, type ErrorInfo, type ReactNode } from 'react';

interface Props {
  children: ReactNode;
}

interface State {
  error: Error | null;
}

/**
 * Ловит ошибку рендеринга, чтобы один сломанный компонент не оставлял пустую
 * страницу.
 *
 * Это классовый компонент, потому что у React пока нет хука, аналогичного
 * `componentDidCatch`. Ничего об ошибке здесь намеренно не пишется в консоль —
 * эта граница последняя линия обороны, и тихий запасной экран читается лучше,
 * чем стектрейс перед пользователем.
 */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    // Сюда отправляйте ошибку в ту систему отчётности, которая используется в
    // приложении.
    console.error('Необработанная ошибка рендеринга', error, info.componentStack);
  }

  render(): ReactNode {
    if (this.state.error) {
      return (
        <main role="alert" className="fallback">
          <h1>Что-то пошло не так</h1>
          <p>Страницу не удалось отрисовать. Попробуйте ещё раз.</p>
          <button type="button" onClick={() => this.setState({ error: null })}>
            Попробовать снова
          </button>
        </main>
      );
    }

    return this.props.children;
  }
}
