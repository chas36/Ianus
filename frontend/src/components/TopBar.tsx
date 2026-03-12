import type { ViewMode } from '../types'

interface TopBarProps {
  mode: ViewMode
  selectedId: number | null
  onModeChange: (mode: ViewMode) => void
  onImportClick: () => void
  onExport: (format: 'xlsx' | 'pdf') => void
}

const MODES: Array<{ key: ViewMode; label: string }> = [
  { key: 'class', label: 'Классы' },
  { key: 'teacher', label: 'Учителя' },
  { key: 'room', label: 'Кабинеты' },
]

export default function TopBar({
  mode,
  selectedId,
  onModeChange,
  onImportClick,
  onExport,
}: TopBarProps) {
  return (
    <header className="topbar">
      <div className="mode-switch" role="tablist" aria-label="Режим просмотра расписания">
        {MODES.map((item) => (
          <button
            key={item.key}
            type="button"
            className={`mode-pill ${mode === item.key ? 'active' : ''}`}
            onClick={() => onModeChange(item.key)}
          >
            {item.label}
          </button>
        ))}
      </div>

      <div className="topbar-actions">
        <button type="button" className="btn ghost" onClick={onImportClick}>
          Импорт XML
        </button>
        <button
          type="button"
          className="btn"
          disabled={selectedId == null}
          onClick={() => onExport('xlsx')}
        >
          Excel
        </button>
        <button
          type="button"
          className="btn"
          disabled={selectedId == null}
          onClick={() => onExport('pdf')}
        >
          PDF
        </button>
      </div>
    </header>
  )
}
