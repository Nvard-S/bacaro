import BarCard from './BarCard.jsx'

function SkeletonCard() {
  return (
    <div className="bg-card border border-line rounded-2xl p-[18px] flex flex-col gap-3">
      <div className="flex justify-between">
        <div className="skeleton h-4 w-32 rounded" />
        <div className="skeleton h-4 w-12 rounded-full" />
      </div>
      <div className="skeleton h-3 w-24 rounded" />
      <div className="skeleton h-3 w-full rounded" />
      <div className="skeleton h-3 w-3/4 rounded" />
      <div className="flex gap-2 mt-1">
        <div className="skeleton h-8 w-8 rounded-full" />
        <div className="skeleton h-8 w-8 rounded-full" />
      </div>
    </div>
  )
}

const GRID = 'grid gap-4 [grid-template-columns:repeat(auto-fill,minmax(260px,1fr))]'

export default function ResultsGrid({ loading, isSearch, items, tagLabelMap, emptyText }) {
  if (loading) {
    return (
      <div className={GRID}>
        {Array.from({ length: 6 }).map((_, i) => <SkeletonCard key={i} />)}
      </div>
    )
  }
  if (!items.length) {
    return <div className="text-muted text-[0.95rem] py-6">{emptyText}</div>
  }
  return (
    <div className={GRID}>
      {items.map((bar, i) => (
        <BarCard key={bar.place_id} bar={bar} isSearchResult={isSearch} tagLabelMap={tagLabelMap} index={i} />
      ))}
    </div>
  )
}
