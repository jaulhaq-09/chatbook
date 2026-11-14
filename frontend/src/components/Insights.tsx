import type { Insights as InsightsData, SenderInsight } from '../api/types'
import type { InsightsState } from '../hooks/useInsights'
import { formatDay, hourLabel, plural, share } from '../lib/format'
import { Spinner } from './ui'

const MONTH_ABBR = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

/** Bars drawn as plain SVG so there is no chart library to install. Values are in the <title> tooltips. */
function Bars({
  values,
  labels,
  height = 120,
  tick,
}: {
  values: number[]
  labels: string[]
  height?: number
  tick?: (i: number) => string | null
}) {
  const max = Math.max(1, ...values)
  const n = values.length
  const gap = n > 60 ? 0 : 1.5
  return (
    <div className="bars">
      <svg viewBox={`0 0 ${n * 10} ${height}`} preserveAspectRatio="none" role="img" aria-label="Bar chart" height={height}>
        {values.map((v, i) => {
          const h = (v / max) * (height - 2)
          return (
            <rect key={i} x={i * 10 + gap / 2} y={height - h} width={10 - gap} height={Math.max(v > 0 ? 1.5 : 0, h)}>
              <title>{`${labels[i]}: ${plural(v, 'message')}`}</title>
            </rect>
          )
        })}
      </svg>
      {tick && (
        <div className="bar-ticks" aria-hidden="true">
          {values.map((_, i) => {
            const t = tick(i)
            return t ? (
              <span key={i} style={{ left: `${((i + 0.5) / n) * 100}%` }}>
                {t}
              </span>
            ) : null
          })}
        </div>
      )}
    </div>
  )
}

function Card({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="stat">
      <span>{label}</span>
      <strong>{value}</strong>
      {hint && <small>{hint}</small>}
    </div>
  )
}

function Panel({ title, note, children }: { title: string; note?: string; children: React.ReactNode }) {
  return (
    <section className="panel">
      <header>
        <h3>{title}</h3>
        {note && <small>{note}</small>}
      </header>
      {children}
    </section>
  )
}

function SenderRow({ s, total, top }: { s: SenderInsight; total: number; top: number }) {
  return (
    <li>
      <div className="sender-head">
        <strong title={s.name}>{s.name}</strong>
        <span>
          {s.messages.toLocaleString('en-GB')} · {share(s.messages, total)}%
        </span>
      </div>
      <div className="bar" aria-hidden="true">
        <i style={{ width: `${(s.messages / Math.max(1, top)) * 100}%` }} />
      </div>
      <small>
        {s.words.toLocaleString('en-GB')} words · {plural(s.photos, 'photo')} · {plural(s.videos, 'video')} · {plural(s.voice, 'voice note')}
        {' '}· started the chat on {plural(s.starts, 'day')}
      </small>
    </li>
  )
}

export function InsightsView({ state }: { state: InsightsState }) {
  const { data, loading, error } = state
  if (error) {
    return (
      <div className="insights">
        <p className="note error" role="alert">
          {error}
        </p>
      </div>
    )
  }
  if (!data) {
    return (
      <div className="stage-empty">
        <Spinner />
        {loading && <span>Counting messages</span>}
      </div>
    )
  }
  if (data.total_messages === 0) {
    return (
      <div className="stage-empty">
        <strong>No messages to summarise</strong>
      </div>
    )
  }
  return <Loaded data={data} />
}

function Loaded({ data }: { data: InsightsData }) {
  const topSender = data.senders[0]?.messages ?? 1
  const peakHour = data.by_hour.indexOf(Math.max(...data.by_hour))
  const daily = data.daily
  return (
    <div className="insights">
      <div className="stats">
        <Card label="Messages" value={data.total_messages.toLocaleString('en-GB')} hint={`${data.avg_per_active_day} per active day`} />
        <Card label="Days with chat" value={`${data.active_days} of ${data.total_days}`} hint={`${share(data.active_days, data.total_days)}% of the period`} />
        <Card label="Longest streak" value={plural(data.longest_streak, 'day')} hint="talking every day" />
        {data.busiest_day && <Card label="Busiest day" value={plural(data.busiest_day.count, 'message')} hint={formatDay(data.busiest_day.date)} />}
        <Card label="Most active hour" value={hourLabel(peakHour)} hint={plural(data.by_hour[peakHour], 'message')} />
      </div>

      <Panel title="Every day" note="Quiet days show as gaps">
        <Bars
          values={daily.map((d) => d.count)}
          labels={daily.map((d) => formatDay(d.date))}
          tick={(i) => (i === 0 ? `${Number(daily[i].date.slice(8, 10))} ${MONTH_ABBR[Number(daily[i].date.slice(5, 7)) - 1]}` : daily[i].date.endsWith('-01') ? MONTH_ABBR[Number(daily[i].date.slice(5, 7)) - 1] : null)}
        />
      </Panel>

      <div className="two-panels">
        <Panel title="Time of day">
          <Bars values={data.by_hour} labels={data.by_hour.map((_, h) => hourLabel(h))} tick={(i) => (i % 6 === 0 ? hourLabel(i) : null)} />
        </Panel>
        <Panel title="Day of the week">
          <Bars values={data.by_weekday.map((w) => w.count)} labels={data.by_weekday.map((w) => w.label)} tick={(i) => data.by_weekday[i].label} />
        </Panel>
      </div>

      {data.by_month.length > 1 && (
        <Panel title="By month">
          <Bars values={data.by_month.map((m) => m.count)} labels={data.by_month.map((m) => m.label)} tick={(i) => (data.by_month.length <= 12 || i % 2 === 0 ? data.by_month[i].label.slice(0, 3) : null)} />
        </Panel>
      )}

      <Panel title="Who says what">
        <ul className="senders">
          {data.senders.map((s) => (
            <SenderRow key={s.name} s={s} total={data.total_messages} top={topSender} />
          ))}
        </ul>
      </Panel>

      {data.emojis.length > 0 && (
        <Panel title="Favourite emoji">
          <ul className="emojis">
            {data.emojis.map((e) => (
              <li key={e.emoji} title={plural(e.count, 'time')}>
                <span>{e.emoji}</span>
                <small>{e.count.toLocaleString('en-GB')}</small>
              </li>
            ))}
          </ul>
        </Panel>
      )}
    </div>
  )
}