import { useCallback, useEffect, useMemo, useState } from 'react'

import { getClasses, getExportUrl, getRooms, getTeachers, getTimetable } from './api'
import ImportDialog from './components/ImportDialog'
import Sidebar from './components/Sidebar'
import TimetableGrid from './components/TimetableGrid'
import TopBar from './components/TopBar'
import type { ClassItem, RoomItem, TeacherItem, TimetableResponse, ViewMode } from './types'
import './App.css'

const MODE_LABELS: Record<ViewMode, string> = {
  class: 'Классы',
  teacher: 'Учителя',
  room: 'Кабинеты',
}

export default function App() {
  const [mode, setMode] = useState<ViewMode>('class')
  const [selectedId, setSelectedId] = useState<number | null>(null)

  const [classes, setClasses] = useState<ClassItem[]>([])
  const [teachers, setTeachers] = useState<TeacherItem[]>([])
  const [rooms, setRooms] = useState<RoomItem[]>([])

  const [loadingLists, setLoadingLists] = useState(false)
  const [loadingTimetable, setLoadingTimetable] = useState(false)
  const [timetable, setTimetable] = useState<TimetableResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [importOpen, setImportOpen] = useState(false)

  const loadLists = useCallback(async () => {
    setLoadingLists(true)
    setError(null)
    try {
      const [classList, teacherList, roomList] = await Promise.all([
        getClasses(),
        getTeachers(),
        getRooms(),
      ])
      setClasses(classList)
      setTeachers(teacherList)
      setRooms(roomList)
    } catch (_err) {
      setError('Не удалось загрузить списки. Проверьте backend API.')
    } finally {
      setLoadingLists(false)
    }
  }, [])

  useEffect(() => {
    void loadLists()
  }, [loadLists])

  useEffect(() => {
    setSelectedId(null)
    setTimetable(null)
    setError(null)
  }, [mode])

  useEffect(() => {
    if (selectedId == null) {
      setTimetable(null)
      setLoadingTimetable(false)
      return
    }

    const run = async () => {
      setLoadingTimetable(true)
      setError(null)
      try {
        const data = await getTimetable(mode, selectedId)
        setTimetable(data)
      } catch (_err) {
        setError('Не удалось загрузить расписание. Проверьте данные и API.')
      } finally {
        setLoadingTimetable(false)
      }
    }

    void run()
  }, [mode, selectedId])

  const handleExport = (format: 'xlsx' | 'pdf') => {
    if (selectedId == null) {
      return
    }
    window.open(getExportUrl(mode, selectedId, format), '_blank', 'noopener,noreferrer')
  }

  const sidebarCount = useMemo(() => {
    if (mode === 'class') {
      return classes.length
    }
    if (mode === 'teacher') {
      return teachers.length
    }
    return rooms.length
  }, [classes.length, mode, rooms.length, teachers.length])

  const selectedName = useMemo(() => {
    if (selectedId == null) {
      return 'не выбрано'
    }

    if (timetable?.entity_name) {
      return timetable.entity_name
    }

    const items = mode === 'class' ? classes : mode === 'teacher' ? teachers : rooms
    const selected = items.find((item) => item.id === selectedId)
    return selected?.name ?? 'не выбрано'
  }, [classes, mode, rooms, selectedId, teachers, timetable?.entity_name])

  return (
    <div className="app-shell">
      <TopBar
        mode={mode}
        selectedId={selectedId}
        onModeChange={setMode}
        onImportClick={() => setImportOpen(true)}
        onExport={handleExport}
      />

      <main className="app-main">
        <Sidebar
          mode={mode}
          classes={classes}
          teachers={teachers}
          rooms={rooms}
          selectedId={selectedId}
          onSelect={setSelectedId}
        />

        <div className="content-area">
          <div className="content-headline">
            <div>
              <span className="content-kicker">Ianus MVP</span>
              <h1>Школьное расписание</h1>
              <p className="content-subtitle">
                Режим: {MODE_LABELS[mode]} · Выбрано: {selectedName}
              </p>
            </div>
            <div className="content-chips">
              <span className="chip">
                {loadingLists ? 'Обновление справочников...' : `Элементов: ${sidebarCount}`}
              </span>
              <span className="chip">Оси: дни x уроки</span>
            </div>
          </div>

          <TimetableGrid timetable={timetable} loading={loadingTimetable} error={error} />
        </div>
      </main>

      <ImportDialog
        open={importOpen}
        onClose={() => setImportOpen(false)}
        onSuccess={() => {
          void loadLists()
        }}
      />
    </div>
  )
}
