import { isAxiosError } from 'axios'
import { useEffect, useState } from 'react'

import { createUser, getUsers, updateUser } from '../api'
import type { UserItem } from '../types'

interface UsersPanelProps {
  open: boolean
  onClose: () => void
}

interface ErrorBody {
  detail?: string
}

export default function UsersPanel({ open, onClose }: UsersPanelProps) {
  const [users, setUsers] = useState<UserItem[]>([])
  const [newUsername, setNewUsername] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [newRole, setNewRole] = useState('teacher')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!open) {
      return
    }

    const run = async () => {
      setLoading(true)
      setError(null)
      try {
        const data = await getUsers()
        setUsers(data)
      } catch (_err) {
        setError('Не удалось загрузить пользователей')
      } finally {
        setLoading(false)
      }
    }

    void run()
  }, [open])

  if (!open) {
    return null
  }

  const handleCreate = async () => {
    setError(null)
    try {
      const user = await createUser({
        username: newUsername,
        password: newPassword,
        role: newRole,
      })
      setUsers((prev) => [...prev, user].sort((a, b) => a.username.localeCompare(b.username, 'ru')))
      setNewUsername('')
      setNewPassword('')
      setNewRole('teacher')
    } catch (err: unknown) {
      if (isAxiosError<ErrorBody>(err)) {
        setError(err.response?.data?.detail ?? 'Ошибка создания пользователя')
        return
      }
      setError('Ошибка создания пользователя')
    }
  }

  const handleToggleActive = async (user: UserItem) => {
    setError(null)
    try {
      const updated = await updateUser(user.id, { is_active: !user.is_active })
      setUsers((prev) => prev.map((item) => (item.id === updated.id ? updated : item)))
    } catch (_err) {
      setError('Не удалось обновить пользователя')
    }
  }

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true" aria-label="Пользователи">
      <div className="modal-card users-panel">
        <h3>Управление пользователями</h3>

        {loading ? <div>Загрузка...</div> : null}

        <table className="users-table">
          <thead>
            <tr>
              <th>Логин</th>
              <th>Роль</th>
              <th>Статус</th>
              <th>Действие</th>
            </tr>
          </thead>
          <tbody>
            {users.map((user) => (
              <tr key={user.id}>
                <td>{user.username}</td>
                <td>{user.role}</td>
                <td>{user.is_active ? 'Активен' : 'Заблокирован'}</td>
                <td>
                  <button
                    type="button"
                    className="btn ghost"
                    onClick={() => void handleToggleActive(user)}
                  >
                    {user.is_active ? 'Блокировать' : 'Активировать'}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        <div className="users-create-row">
          <input
            type="text"
            placeholder="Логин"
            value={newUsername}
            minLength={3}
            maxLength={120}
            onChange={(event) => setNewUsername(event.target.value)}
          />
          <input
            type="password"
            placeholder="Пароль"
            value={newPassword}
            minLength={8}
            maxLength={120}
            onChange={(event) => setNewPassword(event.target.value)}
          />
          <select value={newRole} onChange={(event) => setNewRole(event.target.value)}>
            <option value="teacher">Учитель</option>
            <option value="admin">Админ</option>
          </select>
          <button
            type="button"
            className="btn"
            onClick={() => void handleCreate()}
            disabled={newUsername.trim().length < 3 || newPassword.length < 8}
          >
            Добавить
          </button>
        </div>

        {error ? <div className="modal-error">{error}</div> : null}

        <div className="panel-actions">
          <button type="button" className="btn ghost" onClick={onClose}>
            Закрыть
          </button>
        </div>
      </div>
    </div>
  )
}
