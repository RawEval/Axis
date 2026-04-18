import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Card, CardHeader, CardBody, CardFooter } from './card';

describe('Card', () => {
  it('renders children inside a surface container', () => {
    render(<Card data-testid="c">hello</Card>);
    const el = screen.getByTestId('c');
    expect(el).toHaveTextContent('hello');
    expect(el).toHaveClass('bg-canvas-surface');
    expect(el).toHaveClass('border');
  });

  it('renders header / body / footer slots', () => {
    render(
      <Card>
        <CardHeader data-testid="h">title</CardHeader>
        <CardBody data-testid="b">body</CardBody>
        <CardFooter data-testid="f">footer</CardFooter>
      </Card>,
    );
    expect(screen.getByTestId('h')).toHaveTextContent('title');
    expect(screen.getByTestId('b')).toHaveTextContent('body');
    expect(screen.getByTestId('f')).toHaveTextContent('footer');
  });

  it('forwards className', () => {
    render(<Card className="custom-class" data-testid="c">x</Card>);
    expect(screen.getByTestId('c')).toHaveClass('custom-class');
  });
});
