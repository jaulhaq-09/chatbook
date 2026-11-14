// These types mirror backend/app/schemas.py. Field names are snake_case on the wire.

export type JobStatus = 'processing' | 'ready' | 'failed'
export type DateOrder = 'auto' | 'dmy' | 'mdy'

export interface Progress {
  stage: string
  done: number
  total: number
}

export interface Sender {
  name: string
  count: number
}

export interface Job {
  id: string
  status: JobStatus
  error: string | null
  warnings: string[]
  progress: Progress
  created_at: string
  expires_at: string
  date_order: DateOrder
  order_ambiguous: boolean
  is_sample: boolean
  sources: { id: number; name: string; messages: number }[]
  senders: Sender[]
  counts: { messages: number; photos: number; videos: number; missing_media: number; omitted_media: number }
  date_range: { start: string; end: string } | null
  suggested_title: string
  video_posters: boolean
  background: BackgroundInfo | null
}

export interface BackgroundInfo {
  name: string
  width: number
  height: number
  /** Changes whenever a new picture is uploaded, so previews and thumbnails refresh. */
  version: string
}

export interface User {
  id: string
  email: string
  name: string
  created_at?: string
}

export interface AuthResponse {
  user: User
  token: string
}

export interface UserBook {
  id: string
  user_id?: string
  title: string
  status: string
  message_count: number
  photo_count: number
  video_count: number
  date_range?: string
  options_json?: string
  created_at?: string
  updated_at?: string
}

export type Mode = 'book' | 'album'
export type PageSize = 'A4' | 'Letter' | 'A5' | 'Square'
export type Theme = 'classic' | 'clean' | 'ink'
export type TextSize = 's' | 'm' | 'l'
export type Clock = 'h12' | 'h24'
export type Quality = 'standard' | 'print'
export type VolumeMode = 'none' | 'month' | 'year' | 'size'

export interface AlbumOptions {
  group: 'month' | 'day' | 'sender' | 'none'
  columns: 1 | 2 | 3 | 4
  fit: 'fill' | 'fit'
  paper: 'white' | 'warm' | 'black'
  captions: boolean
  include_videos: boolean
}

export interface BackgroundOptions {
  enabled: boolean
  fit: 'cover' | 'contain' | 'tile'
  /** 0.05 to 1: how strongly the picture shows. */
  opacity: number
  scope: 'all' | 'inside' | 'cover'
}

export type FontKey = 'sans' | 'humanist' | 'friendly' | 'wide' | 'serif' | 'book' | 'mono' | 'hand' | 'script'
export type CoverStyle = 'classic' | 'centered' | 'bold' | 'minimal' | 'frame'

export type Motif = 'none' | 'bubbles' | 'dots' | 'waves' | 'rings' | 'hearts' | 'sparkles'
export type LeftFooter = 'people' | 'text' | 'none'
export type RightFooter = 'counts' | 'dates' | 'text' | 'none'

export interface DesignOptions {
  cover_style: CoverStyle
  color1: string
  color2: string
  heading_font: FontKey
  /** A small drawing in the empty space of the cover and back page. */
  motif: Motif
}

/** Words on the cover. A blank field uses the automatic text. */
export interface CoverText {
  kicker: string
  subtitle: string
  tagline: string
  left_mode: LeftFooter
  right_mode: RightFooter
  footer_left: string
  footer_right: string
}

export interface BackOptions {
  enabled: boolean
  heading: string
  message: string
  signature: string
  left_mode: LeftFooter
  right_mode: RightFooter
  footer_left: string
  footer_right: string
}

export interface RenderOptions {
  mode: Mode
  title: string
  me: string | null
  page_size: PageSize
  theme: Theme
  text_size: TextSize
  clock: Clock
  show_media: boolean
  cover: boolean
  toc: boolean
  page_numbers: boolean
  date_from: string | null
  date_to: string | null
  exclude_people: string[]
  query: string
  album: AlbumOptions
  background: BackgroundOptions
  chat_font: FontKey
  design: DesignOptions
  cover_text: CoverText
  back: BackOptions
  header_left: string
  header_right: string
  quality: Quality
  volume_mode: VolumeMode
  volume_size: number
}

export interface VolumeStat {
  index: number
  label: string
  messages: number
  photos: number
  videos: number
  start: string
  end: string
  estimated_pages: number
}

export interface Stats {
  messages: number
  photos: number
  videos: number
  estimated_pages: number
  toc_available: boolean
  volumes: VolumeStat[]
}

export interface SectionInfo {
  start: string
  end: string
  photos: number
  videos: number
  /** Rough number of printed pages in this section. */
  pages: number
}

export interface Preview {
  html: string
  page: number
  page_count: number
  volume: number
  stats: Stats
  sections: SectionInfo[]
}

export type ExportStatus = 'queued' | 'running' | 'done' | 'failed' | 'cancelled'

export interface ExportFile {
  name: string
  size: number
  pages: number
  volume: number
  label: string
}

export interface ExportJob {
  id: string
  job_id: string
  status: ExportStatus
  progress: Progress
  files: ExportFile[]
  archive: string | null
  error: string | null
  created_at: string
}

export interface CountItem {
  label: string
  count: number
}

export interface SenderInsight {
  name: string
  messages: number
  words: number
  photos: number
  videos: number
  voice: number
  deleted: number
  starts: number
}

export interface Insights {
  total_messages: number
  total_days: number
  active_days: number
  avg_per_active_day: number
  busiest_day: { date: string; count: number } | null
  longest_streak: number
  by_hour: number[]
  by_weekday: CountItem[]
  by_month: CountItem[]
  daily: { date: string; count: number }[]
  senders: SenderInsight[]
  emojis: { emoji: string; count: number }[]
}