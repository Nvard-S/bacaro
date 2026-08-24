import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import BarCard from '../BarCard.jsx'

const bar = {
  place_id: 'p1', name: 'Vino Vero', rating: 4.6, user_rating_count: 120,
  neighborhood: 'Cannaregio', price: '€€', address: 'Fondamenta Misericordia',
  website: 'https://example.com', instagram_url: null,
  blurb: 'Great natural wine', tags: ['natural_wine'],
}

describe('BarCard', () => {
  it('shows the name, rating, address and tag label', () => {
    render(<BarCard bar={bar} tagLabelMap={{ natural_wine: 'Natural wine' }} />)
    expect(screen.getByText('Vino Vero')).toBeInTheDocument()
    expect(screen.getByText(/4\.6/)).toBeInTheDocument()
    expect(screen.getByText('Fondamenta Misericordia')).toBeInTheDocument()
    expect(screen.getByText('Natural wine')).toBeInTheDocument()
  })

  it('flags an unconfirmed search result', () => {
    render(<BarCard bar={{ ...bar, confirmed: false }} isSearchResult />)
    expect(screen.getByText('Possible match')).toBeInTheDocument()
  })

  it('shows the explanation and no badge when confirmed', () => {
    render(<BarCard bar={{ ...bar, confirmed: true, explanation: 'Serves cicchetti' }} isSearchResult />)
    expect(screen.queryByText('Possible match')).not.toBeInTheDocument()
    expect(screen.getByText('Serves cicchetti')).toBeInTheDocument()
  })

  it('links the map to the place id', () => {
    render(<BarCard bar={bar} />)
    expect(screen.getByLabelText('Open in Google Maps')).toHaveAttribute(
      'href', expect.stringContaining('place_id:p1'),
    )
  })
})
