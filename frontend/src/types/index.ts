export interface ClassItem {
  id: number
  name: string
  short_name: string
}

export interface TeacherItem {
  id: number
  name: string
  short_name: string
  color?: string
}

export interface RoomItem {
  id: number
  name: string
  short_name: string
}

export interface TimetableCell {
  subject: string
  teacher: string | null
  room: string | null
  group: string | null
}

export interface TimetableRow {
  period: number
  time: string
  days: Record<number, TimetableCell[]>
}

export interface TimetableResponse {
  entity_type: 'class' | 'teacher' | 'room' | string
  entity_name: string
  rows: TimetableRow[]
}

export interface ImportResponse {
  subjects: number
  teachers: number
  classes: number
  rooms: number
  lessons: number
  cards: number
}

export type ViewMode = 'class' | 'teacher' | 'room'
