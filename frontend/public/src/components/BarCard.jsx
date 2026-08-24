import { MapIcon, SiteIcon, InstagramIcon } from './Icons.jsx'

function ratingColor(r) {
  if (r == null) return 'text-muted'
  if (r >= 4.5) return 'text-good'
  if (r >= 4.0) return 'text-teal'
  if (r >= 3.5) return 'text-ok'
  return 'text-muted'
}

function IconLink({ href, label, children }) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      aria-label={label}
      title={label}
      className="w-8 h-8 rounded-full bg-chip text-ink flex items-center justify-center hover:bg-teal hover:text-white transition-colors shrink-0"
    >
      {children}
    </a>
  )
}

export default function BarCard({ bar, isSearchResult = false, tagLabelMap = {}, index = 0 }) {
  const mapUrl = `https://www.google.com/maps/place/?q=place_id:${encodeURIComponent(bar.place_id)}`
  const meta = [bar.neighborhood, bar.price].filter(Boolean).join(' · ')
  const description = isSearchResult && bar.explanation ? bar.explanation : bar.blurb || ''
  const unconfirmed = isSearchResult && !bar.confirmed
  const tags = bar.tags || []

  return (
    <div
      className={
        'fade-rise bg-card rounded-2xl p-[18px] flex flex-col gap-2 border transition duration-150 hover:-translate-y-0.5 hover:shadow-lg ' +
        (unconfirmed ? 'border-dashed border-line' : 'border-line')
      }
      style={{ animationDelay: `${Math.min(index, 8) * 40}ms` }}
    >
      <div className="flex justify-between items-start gap-2">
        <div className="font-bold text-[1.05rem] tracking-tight">{bar.name}</div>
        <div className="shrink-0 bg-chip rounded-full px-2.5 py-0.5 text-sm font-bold whitespace-nowrap">
          <span className={ratingColor(bar.rating)}>★ {bar.rating ?? '–'}</span>
          {bar.user_rating_count ? <span className="font-semibold text-muted"> ({bar.user_rating_count})</span> : null}
        </div>
      </div>

      {meta && <div className="text-muted text-[0.88rem]">{meta}</div>}
      {bar.address && <div className="text-[0.9rem]">{bar.address}</div>}

      {unconfirmed && (
        <span className="self-start inline-block bg-chip text-ok px-2.5 py-0.5 rounded-full text-[0.72rem] font-bold">
          Possible match
        </span>
      )}

      {description && <div className="text-[0.88rem]">{description}</div>}

      {tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-0.5">
          {tags.map((t) => (
            <span key={t} className="bg-chip text-muted text-[0.74rem] font-semibold px-2.5 py-0.5 rounded-full">
              {tagLabelMap[t] || t.replace(/_/g, ' ')}
            </span>
          ))}
        </div>
      )}

      <div className="flex gap-2 mt-1">
        <IconLink href={mapUrl} label="Open in Google Maps"><MapIcon /></IconLink>
        {bar.website && <IconLink href={bar.website} label="Visit website"><SiteIcon /></IconLink>}
        {bar.instagram_url && <IconLink href={bar.instagram_url} label="Instagram"><InstagramIcon /></IconLink>}
      </div>
    </div>
  )
}
