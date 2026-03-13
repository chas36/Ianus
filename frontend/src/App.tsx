import { AxiosError, isAxiosError } from 'axios'
import { useCallback, useEffect, useMemo, useState } from 'react'

import {
  bootstrapAdmin,
  clearStoredToken,
  exportTimetable,
  getBootstrapRequired,
  getClasses,
  getMe,
  getRooms,
  getTeachers,
  getTimetable,
  login,
  setStoredToken,
} from './api'
import AuditPanel from './components/AuditPanel'
import AuthPanel from './components/AuthPanel'
import ImportDialog from './components/ImportDialog'
import Sidebar from './components/Sidebar'
import TimetableGrid from './components/TimetableGrid'
import TopBar from './components/TopBar'
import UsersPanel from './components/UsersPanel'
import type {
  AuthMeResponse,
  ClassItem,
  RoomItem,
  TeacherItem,
  TimetableResponse,
  ViewMode,
} from './types'
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
  const [usersOpen, setUsersOpen] = useState(false)
  const [auditOpen, setAuditOpen] = useState(false)

  const [authLoading, setAuthLoading] = useState(true)
  const [authError, setAuthError] = useState<string | null>(null)
  const [bootstrapRequired, setBootstrapRequired] = useState(false)
  const [currentUser, setCurrentUser] = useState<AuthMeResponse | null>(null)

  const loadLists = useCallback(async () => {
    if (!currentUser) {
      return
    }

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
  }, [currentUser])

  useEffect(() => {
    const initializeAuth = async () => {
      setAuthLoading(true)
      setAuthError(null)
      try {
        const bootstrapState = await getBootstrapRequired()
        setBootstrapRequired(bootstrapState.required)

        if (bootstrapState.required) {
          setCurrentUser(null)
          return
        }

        const me = await getMe()
        setCurrentUser(me)
      } catch (err: unknown) {
        if (isAxiosError(err) && err.response?.status === 401) {
          clearStoredToken()
          setCurrentUser(null)
        } else {
          setAuthError('Ошибка проверки авторизации. Проверьте backend.')
        }
      } finally {
        setAuthLoading(false)
      }
    }

    void initializeAuth()
  }, [])

  useEffect(() => {
    if (!currentUser) {
      return
    }
    void loadLists()
  }, [currentUser, loadLists])

  useEffect(() => {
    setSelectedId(null)
    setTimetable(null)
    setError(null)
  }, [mode])

  useEffect(() => {
    if (!currentUser) {
      return
    }

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
  }, [currentUser, mode, selectedId])

  const handleAuth = async (username: string, password: string, bootstrap: boolean) => {
    setAuthError(null)
    setAuthLoading(true)
    try {
      if (bootstrap) {
        await bootstrapAdmin({ username, password })
        setBootstrapRequired(false)
      }

      const response = await login({ username, password })
      setStoredToken(response.access_token)
      const me = await getMe()
      setCurrentUser(me)
    } catch (err: unknown) {
      const message =
        isAxiosError(err) && typeof err.response?.data?.detail === 'string'
          ? err.response.data.detail
          : 'Не удалось выполнить вход'
      setAuthError(message)
    } finally {
      setAuthLoading(false)
    }
  }

  const handleLogout = () => {
    clearStoredToken()
    setCurrentUser(null)
    setClasses([])
    setTeachers([])
    setRooms([])
    setSelectedId(null)
    setTimetable(null)
    setImportOpen(false)
    setUsersOpen(false)
    setAuditOpen(false)
  }

  const handleExport = async (format: 'xlsx' | 'pdf') => {
    if (selectedId == null) {
      return
    }

    try {
      const { blob, filename } = await exportTimetable(mode, selectedId, format)
      const url = URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = filename
      anchor.click()
      URL.revokeObjectURL(url)
    } catch (err: unknown) {
      if (err instanceof AxiosError && err.response?.status === 503) {
        setError('PDF недоступен: не установлены системные библиотеки WeasyPrint')
        return
      }
      setError('Не удалось выполнить экспорт файла')
    }
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

  if (authLoading && !currentUser) {
    return (
      <div className="app-shell">
        <section className="grid-empty">Проверка доступа...</section>
      </div>
    )
  }

  if (!currentUser) {
    return (
      <div className="app-shell">
        <AuthPanel
          bootstrapRequired={bootstrapRequired}
          loading={authLoading}
          error={authError}
          onBootstrap={async (username, password) => handleAuth(username, password, true)}
          onLogin={async (username, password) => handleAuth(username, password, false)}
        />
      </div>
    )
  }

  return (
    <div className="app-shell">
      <TopBar
        mode={mode}
        selectedId={selectedId}
        currentUsername={`${currentUser.username} (${currentUser.role})`}
        role={currentUser.role}
        onModeChange={setMode}
        onImportClick={() => setImportOpen(true)}
        onExport={(format) => void handleExport(format)}
        onUsersClick={() => setUsersOpen(true)}
        onAuditClick={() => setAuditOpen(true)}
        onLogout={handleLogout}
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
              <span className="content-kicker">Ianus Phase 2</span>
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

      <UsersPanel
        open={usersOpen && currentUser.role === 'admin'}
        onClose={() => setUsersOpen(false)}
      />

      <AuditPanel
        open={auditOpen && currentUser.role === 'admin'}
        onClose={() => setAuditOpen(false)}
      />
    </div>
  )
}
