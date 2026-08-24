export function MapIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4">
      <path d="M12 21s-7-7.5-7-12a7 7 0 0 1 14 0c0 4.5-7 12-7 12z" />
      <circle cx="12" cy="9" r="2.5" />
    </svg>
  )
}

export function SiteIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4">
      <circle cx="12" cy="12" r="9" />
      <path d="M3 12h18M12 3c2.5 2.7 4 6 4 9s-1.5 6.3-4 9c-2.5-2.7-4-6-4-9s1.5-6.3 4-9z" />
    </svg>
  )
}

export function InstagramIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4">
      <rect x="3" y="3" width="18" height="18" rx="5" />
      <circle cx="12" cy="12" r="4" />
      <circle cx="17.5" cy="6.5" r="0.6" fill="currentColor" stroke="none" />
    </svg>
  )
}

// Simplified crostino: bread base, cream swirl, coral topping, pick with loop.
export function CrostinoIcon() {
  return (
    <svg viewBox="0 0 32 32" className="w-full h-full block">
      <path d="M6 21c0 4.5 4.7 6.5 10.5 6.5S27 25.5 27 21c0-1.6-1-2.7-2-3.3-4.3 1.6-12.6 1.6-17 0-1 .6-2 1.7-2 3.3z" fill="var(--color-ink)" />
      <path d="M6.5 18c2.2-3.2 6.3-3.2 9.5-1.6s7.5-1.6 9.5 1c-3.2 2.1-6.4 2.6-9.5 2.1-3.1.5-7.3-.1-9.5-1.5z" fill="var(--color-card)" stroke="var(--color-ink)" strokeWidth="1.3" strokeLinejoin="round" />
      <circle cx="17.5" cy="13.5" r="2.8" fill="var(--color-coral)" />
      <ellipse cx="18.7" cy="12.3" rx="1" ry="1.3" fill="var(--color-ink)" />
      <path d="M19.3 11.2 24 4.2" stroke="var(--color-ink)" strokeWidth="1.4" strokeLinecap="round" />
      <circle cx="25" cy="3" r="2.3" fill="none" stroke="var(--color-ink)" strokeWidth="1.4" />
    </svg>
  )
}

export function SunIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5">
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
    </svg>
  )
}

export function MoonIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5">
      <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" />
    </svg>
  )
}
