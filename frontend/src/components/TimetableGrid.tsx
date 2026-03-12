import type { JSX } from 'react'

import type { TimetableCell, TimetableResponse } from '../types'

const DAY_NAMES: Record<number, string> = {
  1: 'Понедельник',
  2: 'Вторник',
  3: 'Среда',
  4: 'Четверг',
  5: 'Пятница',
}

const DAYS = [1, 2, 3, 4, 5] as const

function subjectColor(subject: string): string {
  let hash = 0
  for (let index = 0; index < subject.length; index += 1) {
    hash = subject.charCodeAt(index) + ((hash << 5) - hash)
  }
  const hue = Math.abs(hash) % 360
  return `hsl(${hue} 63% 88%)`
}

function renderCell(entry: TimetableCell, idx: number, multiple: boolean): JSX.Element {
  return (
    <article
      key={`${entry.subject}-${idx}`}
      className={`lesson-card ${multiple ? 'split' : ''}`}
      style={{ backgroundColor: subjectColor(entry.subject) }}
    >
      <div className="lesson-subject">{entry.subject}</div>
      {entry.teacher ? <div className="lesson-meta">{entry.teacher}</div> : null}
      {entry.room ? <div className="lesson-meta">каб. {entry.room}</div> : null}
      {entry.group ? <div className="lesson-group">({entry.group})</div> : null}
    </article>
  )
}

interface TimetableGridProps {
  timetable: TimetableResponse | null
  loading: boolean
  error: string | null
}

export default function TimetableGrid({ timetable, loading, error }: TimetableGridProps) {
  if (loading) {
    return <section className="grid-empty">Загрузка расписания...</section>
  }

  if (error) {
    return <section className="grid-empty error">{error}</section>
  }

  if (!timetable) {
    return <section className="grid-empty">Выберите класс, учителя или кабинет</section>
  }

  const periods = [...timetable.rows]
    .sort((a, b) => a.period - b.period)
    .map((row) => ({ period: row.period, time: row.time }))

  const rowsByPeriod = new Map(timetable.rows.map((row) => [row.period, row]))

  return (
    <section className="grid-wrap">
      <div className="grid-title-row">
        <h2>{timetable.entity_name}</h2>
        <p>Ось X: уроки и время, ось Y: дни недели</p>
      </div>

      <div className="grid-scroll">
        <table className="timetable-grid">
          <thead>
            <tr>
              <th className="day-stub">День / Урок</th>
              {periods.map((periodItem) => (
                <th key={periodItem.period} className="period-header-cell">
                  <span>{periodItem.period}</span>
                  <small>{periodItem.time}</small>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {DAYS.map((day) => (
              <tr key={day}>
                <th className="day-cell" scope="row">
                  {DAY_NAMES[day]}
                </th>
                {periods.map((periodItem) => {
                  const periodRow = rowsByPeriod.get(periodItem.period)
                  const entries = periodRow?.days[day] ?? []
                  const hasSplit = entries.length > 1

                  if (entries.length === 0) {
                    return (
                      <td key={`${day}-${periodItem.period}`}>
                        <div className="empty-cell-mark">—</div>
                      </td>
                    )
                  }

                  return (
                    <td key={`${day}-${periodItem.period}`}>
                      {entries.map((entry, index) => renderCell(entry, index, hasSplit))}
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}
