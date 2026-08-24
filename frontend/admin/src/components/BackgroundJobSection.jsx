import { useEffect, useRef, useState } from 'react'
import { apiJson } from '../lib/api.js'
import Section, { btnGreen } from './Section.jsx'

// Reusable section for the long-running admin jobs (enrich / tag / instagram):
// POST to start, then poll a progress endpoint until it stops running.
export default function BackgroundJobSection({
  n, title, note, buttonLabel, startPath, progressPath, getBody, renderProgress,
}) {
  const [status, setStatus] = useState('')
  const timer = useRef(null)

  useEffect(() => () => { if (timer.current) clearInterval(timer.current) }, [])

  const poll = async () => {
    try {
      const p = await apiJson(progressPath)
      setStatus(renderProgress(p))
      if (!p.running && timer.current) { clearInterval(timer.current); timer.current = null }
    } catch {
      if (timer.current) { clearInterval(timer.current); timer.current = null }
    }
  }

  const start = async () => {
    setStatus('Starting…')
    try {
      const data = await apiJson(startPath, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(getBody ? getBody() : {}),
      })
      setStatus(renderProgress({ ...data, done: 0, running: data.total > 0 }))
      if (data.total > 0) {
        if (timer.current) clearInterval(timer.current)
        timer.current = setInterval(poll, 1000)
      }
    } catch (e) {
      setStatus(`Error: ${e.message}`)
    }
  }

  return (
    <Section n={n} title={title} note={note}>
      <button className={btnGreen} onClick={start}>{buttonLabel}</button>
      {status && <div className="text-sm text-gray-600 mt-2">{status}</div>}
    </Section>
  )
}
