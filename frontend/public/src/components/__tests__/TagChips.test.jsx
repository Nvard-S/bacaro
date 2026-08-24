import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import TagChips from '../TagChips.jsx'

const tags = [
  { slug: 'budget_friendly', label: 'Budget-friendly' },
  { slug: 'lively', label: 'Lively' },
]

describe('TagChips', () => {
  it('renders every tag', () => {
    render(<TagChips tags={tags} selected={new Set()} onToggle={() => {}} />)
    expect(screen.getByText('Budget-friendly')).toBeInTheDocument()
    expect(screen.getByText('Lively')).toBeInTheDocument()
  })

  it('reflects selection via aria-pressed', () => {
    render(<TagChips tags={tags} selected={new Set(['lively'])} onToggle={() => {}} />)
    expect(screen.getByText('Lively')).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByText('Budget-friendly')).toHaveAttribute('aria-pressed', 'false')
  })

  it('calls onToggle with the tag slug', () => {
    const onToggle = vi.fn()
    render(<TagChips tags={tags} selected={new Set()} onToggle={onToggle} />)
    fireEvent.click(screen.getByText('Budget-friendly'))
    expect(onToggle).toHaveBeenCalledWith('budget_friendly')
  })
})
