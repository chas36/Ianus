import { useEffect, useState } from 'react'

import { getAuditLogs } from '../api'
import type { AuditLogItem } from '../types'

interface AuditPanelProps {
  open: boolean
  onClose: () => void
}

export default function AuditPanel({ open, onClose }: AuditPanelProps) {
  const [logs, setLogs] = useState<AuditLogItem[]>([])
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
        const data = await getAuditLogs(100)
        setLogs(data)
      } catch (_err) {
        setError('Не удалось загрузить журнал')
      } finally {
        setLoading(false)
      }
    }

    void run()
  }, [open])

  if (!open) {
    return null
  }

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true" aria-label="Журнал действий">
      <div className="modal-card audit-panel">
        <h3>Журнал действий</h3>

        {loading ? <div>Загрузка...</div> : null}
        {error ? <div className="modal-error">{error}</div> : null}

        <table className="audit-table">
          <thead>
            <tr>
              <th>Время</th>
              <th>Пользователь</th>
              <th>Действие</th>
              <th>Детали</th>
            </tr>
          </thead>
          <tbody>
            {logs.map((log) => (
              <tr key={log.id}>
                <td>{new Date(log.created_at).toLocaleString('ru-RU')}</td>
                <td>{log.username}</td>
                <td>{log.action}</td>
                <td>{log.detail}</td>
              </tr>
            ))}
          </tbody>
        </table>

        <div className="panel-actions">
          <button type="button" className="btn ghost" onClick={onClose}>
            Закрыть
          </button>
        </div>
      </div>
    </div>
  )
}
