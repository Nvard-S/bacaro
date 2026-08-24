import { useEffect, useRef, useState } from 'react'

// Types out rotating example prompts, then erases and moves to the next.
// Pauses whenever `paused` is true (e.g. the input is focused or has text),
// so it never fights the user.
export function useTypewriter(phrases, paused) {
  const [text, setText] = useState('')
  const state = useRef({ phrase: 0, char: 0, erasing: false })

  useEffect(() => {
    if (paused) return
    let timer
    const tick = () => {
      const s = state.current
      const phrase = phrases[s.phrase]
      if (!s.erasing) {
        s.char += 1
        setText(phrase.slice(0, s.char))
        if (s.char >= phrase.length) {
          s.erasing = true
          timer = setTimeout(tick, 1300)
        } else {
          timer = setTimeout(tick, 55)
        }
      } else {
        s.char -= 1
        setText(phrase.slice(0, s.char))
        if (s.char <= 0) {
          s.erasing = false
          s.phrase = (s.phrase + 1) % phrases.length
          timer = setTimeout(tick, 300)
        } else {
          timer = setTimeout(tick, 28)
        }
      }
    }
    timer = setTimeout(tick, 400)
    return () => clearTimeout(timer)
  }, [phrases, paused])

  return paused ? '' : text
}
