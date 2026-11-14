import { useState, type ReactNode } from 'react'

const STEPS = [
  { n: '1', title: 'Export your chat', text: 'Get your chat out of WhatsApp, Instagram or Facebook, with photos and videos. You get one .zip file.' },
  { n: '2', title: 'Drop it in', text: 'Chatbook reads the messages, shrinks the photos and finds the dates. Nothing to configure.' },
  { n: '3', title: 'Make your book', text: 'Pick paper, style and filters, watch the preview update, then download a print-ready PDF.' },
]

interface Source {
  id: string
  name: string
  file: string
  steps: { title: string; text: ReactNode }[]
  tip: string
}

const SOURCES: Source[] = [
  {
    id: 'whatsapp',
    name: 'WhatsApp',
    file: 'a .zip (or just the .txt chat file)',
    steps: [
      { title: 'Open the chat', text: 'Open the conversation you want in WhatsApp on your phone.' },
      {
        title: 'Choose Export chat',
        text: (
          <>
            <b>Android:</b> tap ⋮ then <b>More</b> then <b>Export chat</b>. <b>iPhone:</b> tap the contact or group name at the top, then <b>Export Chat</b>.
          </>
        ),
      },
      { title: 'Include media', text: 'Choose Include media so the photos and videos come along. Without media you get only the words.' },
      { title: 'Send it to your computer', text: 'Share the .zip to yourself with email, Google Drive, Telegram or Files, then save it on your computer.' },
    ],
    tip: 'WhatsApp limits how much one export can hold. For a very long chat, export it in parts and add them together in Chatbook.',
  },
  {
    id: 'instagram',
    name: 'Instagram',
    file: 'the .zip that Instagram emails you',
    steps: [
      {
        title: 'Open Download your information',
        text: (
          <>
            On Instagram go to <b>Profile → ☰ menu → Accounts Centre → Your information and permissions → Download your information</b>.
          </>
        ),
      },
      {
        title: 'Pick only your messages',
        text: (
          <>
            Choose <b>Download or transfer information</b>, pick your Instagram account, then <b>Some of your information</b> and tick <b>Messages</b>.
          </>
        ),
      },
      {
        title: 'Set JSON and High quality',
        text: (
          <>
            Choose <b>Download to device</b>. Set the date range, the format to <b>JSON</b> (not HTML) and the media quality to <b>High</b>. Then submit the request.
          </>
        ),
      },
      { title: 'Wait for the email, then download', text: 'Meta emails you when the file is ready. It can take minutes or a few days. Download it before the link expires.' },
    ],
    tip: 'A download holds all your chats. Chatbook uses the biggest one. To use another, zip just that chat’s folder (inside messages → inbox) and upload that. A shorter date range keeps the download small.',
  },
  {
    id: 'facebook',
    name: 'Facebook',
    file: 'the .zip that Facebook emails you',
    steps: [
      {
        title: 'Open Download your information',
        text: (
          <>
            On Facebook go to <b>Settings &amp; privacy → Settings → Your information and permissions → Download your information</b>.
          </>
        ),
      },
      {
        title: 'Pick only your messages',
        text: (
          <>
            Choose <b>Download or transfer information</b>, pick your Facebook account, then <b>Some of your information</b> and tick <b>Messages</b>.
          </>
        ),
      },
      {
        title: 'Set JSON and High quality',
        text: (
          <>
            Choose <b>Download to device</b>. Set the date range, the format to <b>JSON</b> (not HTML) and the media quality to <b>High</b>. Then submit the request.
          </>
        ),
      },
      { title: 'Wait for the email, then download', text: 'Meta emails you when the file is ready. It can take minutes or a few days. You may be asked for your password.' },
    ],
    tip: 'Messenger chats are included under Messages. A download holds all your chats, and Chatbook uses the biggest one. To use another, zip just that chat’s folder (inside messages → inbox).',
  },
]

const THEN = [
  { title: 'Drop the file in', text: 'Open the workspace and drop the .zip (or the chat file) on the left. You can add several files to merge them.' },
  { title: 'Say which side is you', text: 'Pick your own name under “Right-hand side is” so your messages sit on the right, like in the app.' },
  { title: 'Choose book or album', text: 'Chat book keeps the whole conversation. Photo album shows only pictures. Try Photo layout: Album style for big photos.' },
  { title: 'Design the pages', text: 'Pick paper, a chat font, a cover style and colours, a background picture and the words on the first and last page.' },
  { title: 'Check the preview', text: 'Flip through the sections, use Go to for any page or date, and look at the pages with photos and videos.' },
  { title: 'Make the PDF and print', text: 'Press Make PDF. For long chats split it by month, and choose Print quality for sharp photos.' },
]

const FEATURES: { title: string; text: string; icon: ReactNode }[] = [
  {
    title: 'Looks like the app',
    text: 'Chat bubbles, times, sender names, photo and video bubbles with captions, voice notes and deleted messages.',
    icon: <path d="M5 6h14v9H11l-6 4z" />,
  },
  {
    title: 'Made for long chats',
    text: 'Months of daily messages in one book. Long chats are laid out in slices and joined, with continuous page numbers.',
    icon: <path d="M6 4h9l3 3v13H6zM9 11h6M9 15h6" />,
  },
  {
    title: 'Contents and bookmarks',
    text: 'A cover, a contents page by month with real page numbers, a running header and PDF bookmarks.',
    icon: <path d="M5 5h14M5 10h10M5 15h14M5 20h8" />,
  },
  {
    title: 'Photo albums',
    text: 'Only the pictures and videos, grouped by month, day or person, one to four across, on white, warm or black paper.',
    icon: <path d="M4 6h16v12H4zM4 16l5-5 4 4 3-3 4 4M9 9.5h.01" />,
  },
  {
    title: 'Insights',
    text: 'See who talks most, your busiest day, longest streak, favourite hours and emoji before you print.',
    icon: <path d="M5 20V10M12 20V4M19 20v-7" />,
  },
  {
    title: 'Split into volumes',
    text: 'One book per month or year, or by size, delivered together as a single .zip. Easy to print and bind.',
    icon: <path d="M5 8l7-4 7 4-7 4zM5 12l7 4 7-4M5 16l7 4 7-4" />,
  },
]

const FAQ = [
  { q: 'Is my chat private?', a: 'Your chat is processed by the server running this app, which may be your own computer, and nothing is sent to anyone else. Each chat is deleted automatically 24 hours after you last used it, or immediately when you press remove.' },
  { q: 'How large a chat can it handle?', a: 'In testing, 30,000 messages with 300 photos became a 1,650 page PDF in about two minutes. For very long chats, splitting into one volume per month is the easiest way to print.' },
  { q: 'Which apps work?', a: 'WhatsApp (.zip or .txt), and Instagram or Facebook downloads in JSON format. Pick JSON, not HTML, when you request your Instagram or Facebook data.' },
  { q: 'WhatsApp limits my export. What do I do?', a: 'WhatsApp caps how much one export can hold. Export in parts and add them together with Add another export. Messages that appear in two parts are merged, not repeated.' },
  { q: 'Do voice notes and videos play in the PDF?', a: 'No. A PDF cannot play sound or video, so voice notes print as a player bar and videos as a still frame with a play mark and the length.' },
  { q: 'The dates look swapped. Can I fix that?', a: 'Yes. When a chat can be read as day first or month first, Chatbook tells you which it chose and offers a one-click switch.' },
]

function GetYourChat() {
  const [id, setId] = useState(SOURCES[0].id)
  const src = SOURCES.find((s) => s.id === id) ?? SOURCES[0]
  return (
    <section className="block" id="get-chat">
      <h2>Get your chat, then make your book</h2>
      <div className="src-tabs" role="tablist" aria-label="Where is your chat?">
        {SOURCES.map((s) => (
          <button key={s.id} type="button" role="tab" aria-selected={s.id === id} className={s.id === id ? 'on' : ''} onClick={() => setId(s.id)}>
            {s.name}
          </button>
        ))}
      </div>
      <div className="src-card" role="tabpanel">
        <h3>
          1. Get it from {src.name} <small>You end up with {src.file}.</small>
        </h3>
        <ol className="how-list">
          {src.steps.map((s, i) => (
            <li key={s.title}>
              <span>{i + 1}</span>
              <div>
                <strong>{s.title}</strong>
                <p>{s.text}</p>
              </div>
            </li>
          ))}
        </ol>
        <p className="src-tip">{src.tip}</p>
        <p className="src-note">Menu names move around between app versions. If you cannot find one, search for “Download your information” in the app’s settings.</p>
      </div>
      <div className="src-card then">
        <h3>2. Then, in Chatbook</h3>
        <ol className="how-list">
          {THEN.map((s, i) => (
            <li key={s.title}>
              <span>{i + 1}</span>
              <div>
                <strong>{s.title}</strong>
                <p>{s.text}</p>
              </div>
            </li>
          ))}
        </ol>
      </div>
    </section>
  )
}

export function Home({ onStart, onSample }: { onStart: () => void; onSample: () => void }) {
  return (
    <div className="home">
      <section className="hero">
        <div className="hero-copy">
          <span className="eyebrow">For WhatsApp, Instagram and Facebook chats</span>
          <h1>
            Turn a long chat into a <em>book you can hold</em>
          </h1>
          <p>
            Every message, photo and video exactly where it was sent. Chatbook makes a clean, print-ready PDF or a photo album from your WhatsApp, Instagram or Facebook chat, in a couple of minutes.
          </p>
          <div className="hero-cta">
            <button type="button" className="btn primary big" onClick={onStart}>
              Start with your chat
            </button>
            <button type="button" className="btn big" onClick={onSample}>
              Try a sample
            </button>
          </div>
          <ul className="hero-points">
            <li>A4, Letter, A5 or square</li>
            <li>Cover, contents, page numbers</li>
            <li>Private and auto-deleted</li>
          </ul>
        </div>

        <div className="hero-art" aria-hidden="true">
          <div className="phone">
            <div className="phone-bar">Priya</div>
            <div className="b in">Good morning! Are we still on for Coorg this weekend?</div>
            <div className="b out">Yes! Booked the homestay last night</div>
            <div className="b img">
              <span />
            </div>
            <div className="b in">That view 😍</div>
          </div>
          <div className="arrow">
            <svg viewBox="0 0 48 24" width="48" height="24">
              <path d="M2 12h40M34 4l8 8-8 8" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
          <div className="book">
            <div className="book-cover">
              <i />
              <strong>Priya &amp; Arjun</strong>
              <small>12 March – 18 April 2026</small>
            </div>
            <div className="book-page">
              <b>March 2026</b>
              <span className="l in" />
              <span className="l out" />
              <span className="l in short" />
              <span className="l img" />
              <span className="l out short" />
            </div>
          </div>
        </div>
      </section>

      <section className="band" aria-label="Tested sizes">
        <div>
          <strong>30,000</strong>
          <span>messages in one test chat</span>
        </div>
        <div>
          <strong>1,650</strong>
          <span>pages, made in about 2 minutes</span>
        </div>
        <div>
          <strong>24 h</strong>
          <span>then your chat is deleted</span>
        </div>
      </section>

      <section className="block">
        <h2>How it works</h2>
        <ol className="steps">
          {STEPS.map((s) => (
            <li key={s.n}>
              <span className="step-n">{s.n}</span>
              <h3>{s.title}</h3>
              <p>{s.text}</p>
            </li>
          ))}
        </ol>
      </section>

      <GetYourChat />

      <section className="block">
        <h2>Everything for a book that feels like the chat</h2>
        <div className="features">
          {FEATURES.map((f) => (
            <article key={f.title}>
              <span className="f-icon">
                <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  {f.icon}
                </svg>
              </span>
              <h3>{f.title}</h3>
              <p>{f.text}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="block narrow">
        <h2>Questions</h2>
        <div className="faq">
          {FAQ.map((f) => (
            <details key={f.q}>
              <summary>{f.q}</summary>
              <p>{f.a}</p>
            </details>
          ))}
        </div>
      </section>

      <section className="cta-end">
        <h2>Ready when your export is</h2>
        <p>Try the sample first if you just want to see what it makes.</p>
        <div className="hero-cta center">
          <button type="button" className="btn primary big" onClick={onStart}>
            Open the workspace
          </button>
          <button type="button" className="btn big" onClick={onSample}>
            Try a sample
          </button>
        </div>
      </section>

      <footer className="foot">Chatbook · Not affiliated with WhatsApp, Instagram, Facebook or Meta. Chats are processed by the server you run this on.</footer>
    </div>
  )
}