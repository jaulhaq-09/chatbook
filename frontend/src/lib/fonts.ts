import type { FontKey } from '../api/types'

/**
 * The fonts offered for the chat text and the titles. The server has its own, longer stacks (see
 * backend/app/services/render/fonts.py) that also cover other scripts and emoji. These start with the same
 * names, so the sample line here looks like the printed page.
 */
export interface FontChoice {
  key: FontKey
  label: string
  note: string
  stack: string
  /** Fine for long stretches of chat text. Script type is for titles only. */
  forChat: boolean
}

export const FONT_CHOICES: FontChoice[] = [
  { key: 'sans', label: 'Modern sans', note: 'Clean and neutral', stack: '"Noto Sans","Segoe UI","Helvetica Neue",Arial,sans-serif', forChat: true },
  { key: 'humanist', label: 'Soft sans', note: 'Segoe UI or Calibri', stack: '"Segoe UI",Calibri,Carlito,Candara,sans-serif', forChat: true },
  { key: 'friendly', label: 'Rounded', note: 'Relaxed and friendly', stack: '"Trebuchet MS",Candara,"Lucida Grande",sans-serif', forChat: true },
  { key: 'wide', label: 'Wide and clear', note: 'Verdana, easy on the eyes', stack: 'Verdana,Geneva,"DejaVu Sans",sans-serif', forChat: true },
  { key: 'serif', label: 'Classic serif', note: 'Georgia, like a novel', stack: 'Georgia,"Times New Roman","Noto Serif",serif', forChat: true },
  { key: 'book', label: 'Book serif', note: 'Palatino, elegant', stack: '"Palatino Linotype","Book Antiqua",Palatino,Georgia,serif', forChat: true },
  { key: 'mono', label: 'Typewriter', note: 'Courier', stack: '"Courier New","Liberation Mono",monospace', forChat: true },
  { key: 'hand', label: 'Handwriting', note: 'Casual, playful', stack: '"Segoe Print","Bradley Hand","Comic Sans MS",cursive', forChat: true },
  { key: 'script', label: 'Script', note: 'Flowing, for titles', stack: '"Segoe Script","Brush Script MT","Lucida Handwriting",cursive', forChat: false },
]

export const SAMPLE_TEXT = 'Good morning! Coffee at 9? ☕ चलो चलें'

export function fontStack(key: FontKey): string {
  return (FONT_CHOICES.find((f) => f.key === key) ?? FONT_CHOICES[0]).stack
}