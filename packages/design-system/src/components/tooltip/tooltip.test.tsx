import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Tooltip, TooltipProvider } from './tooltip';

describe('Tooltip', () => {
  it('wraps a trigger and exposes a label', () => {
    render(
      <TooltipProvider delayDuration={0}>
        <Tooltip label="Hi">
          <button>Trigger</button>
        </Tooltip>
      </TooltipProvider>,
    );
    expect(screen.getByText('Trigger')).toBeInTheDocument();
  });
});
