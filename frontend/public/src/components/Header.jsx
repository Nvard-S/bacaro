import { SunIcon, MoonIcon } from './Icons.jsx'

export default function Header({ theme, onToggleTheme }) {
  return (
    <header className="flex items-center justify-between py-5 border-b border-line mb-9">
      <div className="font-extrabold text-lg tracking-tight">
        Bacaro<span className="text-coral">Hop</span>
      </div>
      <button
        type="button"
        onClick={onToggleTheme}
        aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
        className="w-10 h-10 rounded-full bg-chip text-ink flex items-center justify-center hover:text-coral transition-colors"
      >
        {theme === 'dark' ? <SunIcon /> : <MoonIcon />}
      </button>
    </header>
  )
}
