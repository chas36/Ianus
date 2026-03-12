import axios from 'axios'
import type {
  ClassItem,
  ImportResponse,
  RoomItem,
  TeacherItem,
  TimetableResponse,
  ViewMode,
} from '../types'

const api = axios.create({ baseURL: '/api' })

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

export function getExportUrl(mode: ViewMode, id: number, format: 'xlsx' | 'pdf'): string {
  return `/api/export/${mode}/${id}?format=${format}`
}
