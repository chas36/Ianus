import { isAxiosError } from 'axios'
import { useRef, useState } from 'react'

import { importXml } from '../api'
import type { ImportResponse } from '../types'

interface ImportDialogProps {
  open: boolean
  onClose: () => void
  onSuccess: () => void
}

interface ImportErrorBody {
  detail?: string
}

export default function ImportDialog({ open, onClose, onSuccess }: ImportDialogProps) {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<ImportResponse | null>(null)

  if (!open) {
    return null
  }

  const handleImport = async () => {
    const file = fileInputRef.current?.files?.[0]
    if (!file) {
      setError('Выберите XML-файл для импорта')
      return
    }

    setLoading(true)
    setError(null)

    try {
      const payload = await importXml(file)
      setResult(payload)
      onSuccess()
    } catch (err: unknown) {
      if (isAxiosError<ImportErrorBody>(err)) {
        setError(err.response?.data?.detail ?? 'Ошибка импорта')
      } else {
        setError('Ошибка импорта')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true" aria-label="Импорт XML">
      <div className="modal-card">
        <h3>Импорт из aSc Timetables</h3>

        <input ref={fileInputRef} type="file" accept=".xml" />

        <div className="modal-actions">
          <button type="button" className="btn" disabled={loading} onClick={handleImport}>
            {loading ? 'Импорт...' : 'Импортировать'}
          </button>
          <button type="button" className="btn ghost" onClick={onClose}>
            Закрыть
          </button>
        </div>

        {error ? <div className="modal-error">{error}</div> : null}

        {result ? (
          <div className="modal-success">
            Загружено: {result.subjects} предметов, {result.teachers} учителей, {result.classes}{' '}
            классов, {result.rooms} кабинетов, {result.lessons} уроков, {result.cards} карточек
          </div>
        ) : null}
      </div>
    </div>
  )
}
