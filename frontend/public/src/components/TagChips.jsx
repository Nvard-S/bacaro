export default function TagChips({ tags, selected, onToggle }) {
  return (
    <div>
      <div className="text-xs uppercase tracking-wider text-muted font-bold mb-2.5">
        Filter by tag
      </div>
      <div className="flex flex-wrap gap-2">
        {tags.map((t) => {
          const active = selected.has(t.slug)
          return (
            <button
              key={t.slug}
              type="button"
              aria-pressed={active}
              onClick={() => onToggle(t.slug)}
              className={
                'px-3.5 py-2 rounded-full text-sm font-semibold border-[1.5px] transition ' +
                (active
                  ? 'bg-teal text-white border-transparent'
                  : 'bg-chip text-ink border-transparent hover:border-line')
              }
            >
              {t.label}
            </button>
          )
        })}
      </div>
    </div>
  )
}
