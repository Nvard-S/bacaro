import { highlightSegments } from '../lib/highlight.js'

export default function AnswerBanner({ answer, query, names }) {
  const segments = highlightSegments(answer, names, query)
  return (
    <div
      className="rounded-2xl border border-line p-5 mb-5 text-lg font-semibold"
      style={{
        background:
          'linear-gradient(135deg, color-mix(in srgb, var(--color-coral) 12%, var(--color-card)), color-mix(in srgb, var(--color-teal) 12%, var(--color-card)))',
      }}
    >
      {segments.map((s, i) => {
        if (s.kind === 'name') return <span key={i} className="text-teal-strong font-extrabold">{s.text}</span>
        if (s.kind === 'query') return <span key={i} className="underline decoration-coral decoration-2 underline-offset-2">{s.text}</span>
        return <span key={i}>{s.text}</span>
      })}
    </div>
  )
}
