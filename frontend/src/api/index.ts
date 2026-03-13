import axios from 'axios'

import type {
  AuthBootstrapRequest,
  AuthBootstrapRequiredResponse,
  AuthBootstrapResponse,
  AuthLoginRequest,
  AuthLoginResponse,
  AuthMeResponse,
  AuditLogItem,
  ClassItem,
  ImportResponse,
  RoomItem,
  TeacherItem,
  TimetableResponse,
  UserCreateRequest,
  UserItem,
  ViewMode,
} from '../types'

const TOKEN_STORAGE_KEY = 'ianus_access_token'

const api = axios.create({ baseURL: '/api' })

api.interceptors.request.use((config) => {
  const token = getStoredToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_STORAGE_KEY)
}

export function setStoredToken(token: string): void {
  localStorage.setItem(TOKEN_STORAGE_KEY, token)
}

export function clearStoredToken(): void {
  localStorage.removeItem(TOKEN_STORAGE_KEY)
}

export async function getBootstrapRequired(): Promise<AuthBootstrapRequiredResponse> {
  const { data } = await api.get<AuthBootstrapRequiredResponse>('/auth/bootstrap-required')
  return data
}

export async function bootstrapAdmin(payload: AuthBootstrapRequest): Promise<AuthBootstrapResponse> {
  const { data } = await api.post<AuthBootstrapResponse>('/auth/bootstrap', payload)
  return data
}

export async function login(payload: AuthLoginRequest): Promise<AuthLoginResponse> {
  const { data } = await api.post<AuthLoginResponse>('/auth/login', payload)
  return data
}

export async function getMe(): Promise<AuthMeResponse> {
  const { data } = await api.get<AuthMeResponse>('/auth/me')
  return data
}

export async function getClasses(): Promise<ClassItem[]> {
  const { data } = await api.get<ClassItem[]>('/classes')
  return data
}

export async function getTeachers(): Promise<TeacherItem[]> {
  const { data } = await api.get<TeacherItem[]>('/teachers')
  return data
}

export async function getRooms(): Promise<RoomItem[]> {
  const { data } = await api.get<RoomItem[]>('/rooms')
  return data
}

export async function getTimetable(mode: ViewMode, id: number): Promise<TimetableResponse> {
  const { data } = await api.get<TimetableResponse>(`/timetable/${mode}/${id}`)
  return data
}

export async function importXml(file: File): Promise<ImportResponse> {
  const formData = new FormData()
  formData.append('file', file)
  const { data } = await api.post<ImportResponse>('/import/asc-xml', formData)
  return data
}

export async function exportTimetable(
  mode: ViewMode,
  id: number,
  format: 'xlsx' | 'pdf',
): Promise<{ blob: Blob; filename: string }> {
  const response = await api.get<Blob>(`/export/${mode}/${id}?format=${format}`, {
    responseType: 'blob',
  })

  const disposition = response.headers['content-disposition']
  const fallback = `${mode}_${id}.${format}`
  const filename = parseFilename(disposition) ?? fallback

  return { blob: response.data, filename }
}

export async function getUsers(): Promise<UserItem[]> {
  const { data } = await api.get<UserItem[]>('/users')
  return data
}

export async function createUser(payload: UserCreateRequest): Promise<UserItem> {
  const { data } = await api.post<UserItem>('/users', payload)
  return data
}

export async function updateUser(
  id: number,
  payload: { role?: string; is_active?: boolean; password?: string },
): Promise<UserItem> {
  const { data } = await api.patch<UserItem>(`/users/${id}`, payload)
  return data
}

export async function getAuditLogs(limit = 50): Promise<AuditLogItem[]> {
  const { data } = await api.get<AuditLogItem[]>(`/audit?limit=${limit}`)
  return data
}

function parseFilename(contentDisposition: string | undefined): string | null {
  if (!contentDisposition) {
    return null
  }

  const match = contentDisposition.match(/filename="?([^";]+)"?/i)
  return match ? match[1] : null
}
