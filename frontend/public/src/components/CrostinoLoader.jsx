import { CrostinoIcon } from './Icons.jsx'

export default function CrostinoLoader() {
  return (
    <div className="flex py-5" role="status" aria-label="Loading bacari">
      <div className="flex gap-2 items-end">
        {[0, 1, 2, 3, 4].map((i) => (
          <span key={i} className="loader-bite w-7 h-7">
            <CrostinoIcon />
          </span>
        ))}
      </div>
    </div>
  )
}
