import { useState } from 'react'
import type { FormEvent } from 'react'

interface AuthPanelProps {
  bootstrapRequired: boolean
  loading: boolean
  error: string | null
  onBootstrap: (username: string, password: string) => Promise<void>
  onLogin: (username: string, password: string) => Promise<void>
}

export default function AuthPanel({
  bootstrapRequired,
  loading,
  error,
  onBootstrap,
  onLogin,
}: AuthPanelProps) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')

  const submitText = bootstrapRequired ? 'Создать администратора' : 'Войти'
  const heading = bootstrapRequired ? 'Первичный запуск' : 'Вход в Ianus'
  const description = bootstrapRequired
    ? 'Создайте первую учетную запись администратора для доступа к системе.'
    : 'Введите учетные данные администратора или учителя.'

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (bootstrapRequired) {
      await onBootstrap(username, password)
      return
    }
    await onLogin(username, password)
  }

  return (
    <section className="auth-wrap">
      <form className="auth-card" onSubmit={(event) => void handleSubmit(event)}>
        <span className="content-kicker">Ianus Phase 2</span>
        <h1>{heading}</h1>
        <p>{description}</p>

        <label className="auth-field">
          <span>Логин</span>
          <input
            type="text"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            required
            minLength={3}
            maxLength={120}
            autoComplete="username"
          />
        </label>

        <label className="auth-field">
          <span>Пароль</span>
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
            minLength={8}
            maxLength={120}
            autoComplete={bootstrapRequired ? 'new-password' : 'current-password'}
          />
        </label>

        <button className="btn" type="submit" disabled={loading}>
          {loading ? 'Подождите...' : submitText}
        </button>

        {error ? <div className="auth-error">{error}</div> : null}
      </form>
    </section>
  )
}
