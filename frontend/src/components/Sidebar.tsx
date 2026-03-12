import type { ClassItem, RoomItem, TeacherItem, ViewMode } from '../types'

interface SidebarProps {
  mode: ViewMode
  classes: ClassItem[]
  teachers: TeacherItem[]
  rooms: RoomItem[]
  selectedId: number | null
  onSelect: (id: number) => void
}

function extractGrade(className: string): string {
  const match = className.match(/^\d+/)
  return match ? match[0] : 'Без параллели'
}

export default function Sidebar({
  mode,
  classes,
  teachers,
  rooms,
  selectedId,
  onSelect,
}: SidebarProps) {
  const title = mode === 'class' ? 'Классы' : mode === 'teacher' ? 'Учителя' : 'Кабинеты'

  if (mode === 'class') {
    const grouped: Record<string, ClassItem[]> = {}
    for (const item of classes) {
      const grade = extractGrade(item.name)
      if (!grouped[grade]) {
        grouped[grade] = []
      }
      grouped[grade].push(item)
    }

    const orderedGrades = Object.keys(grouped).sort((a, b) => {
      const na = Number(a)
      const nb = Number(b)
      if (Number.isNaN(na) || Number.isNaN(nb)) {
        return a.localeCompare(b, 'ru')
      }
      return na - nb
    })

    return (
      <aside className="sidebar">
        <h3 className="sidebar-title">{title}</h3>
        {orderedGrades.map((grade) => (
          <section key={grade} className="sidebar-group">
            <div className="sidebar-group-label">{grade}</div>
            <div className="sidebar-list">
              {grouped[grade].map((item) => (
                <button
                  key={item.id}
                  type="button"
                  className={`sidebar-item ${selectedId === item.id ? 'active' : ''}`}
                  onClick={() => onSelect(item.id)}
                >
                  {item.name}
                </button>
              ))}
            </div>
          </section>
        ))}
      </aside>
    )
  }

  const items: Array<{ id: number; name: string }> = mode === 'teacher' ? teachers : rooms

  return (
    <aside className="sidebar">
      <h3 className="sidebar-title">{title}</h3>
      <div className="sidebar-list">
        {items.map((item) => (
          <button
            key={item.id}
            type="button"
            className={`sidebar-item ${selectedId === item.id ? 'active' : ''}`}
            onClick={() => onSelect(item.id)}
          >
            {item.name}
          </button>
        ))}
      </div>
    </aside>
  )
}
