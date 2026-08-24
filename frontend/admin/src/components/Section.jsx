export default function Section({ n, title, note, children }) {
  return (
    <section className="mb-6 p-4 bg-white border border-gray-200 rounded-lg">
      <h2 className="text-base font-semibold mb-1">{n}. {title}</h2>
      {note && <p className="text-sm text-gray-500 mb-3">{note}</p>}
      {children}
    </section>
  )
}

export const btnBlue = 'px-3.5 py-2 rounded bg-blue-700 text-white text-sm font-semibold hover:bg-blue-800 mr-2 mb-2'
export const btnGray = 'px-3.5 py-2 rounded bg-gray-500 text-white text-sm font-semibold hover:bg-gray-600 mr-2 mb-2'
export const btnGreen = 'px-3.5 py-2 rounded bg-green-700 text-white text-sm font-semibold hover:bg-green-800 mr-2 mb-2'
export const inputCls = 'w-full mb-2.5 px-2.5 py-2 border border-gray-300 rounded text-sm'
