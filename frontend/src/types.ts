// 与后端 Pydantic 模型对齐(见 backend/app/models/)
export type DocStatus = 'processing' | 'ready' | 'failed'

export interface DocRecord {
  doc_id: string
  doc_name: string
  status: DocStatus
  created_at: string
  error?: string | null
}

export interface Reference {
  index: number
  doc_name: string
  section_path: string
  snippet: string
}

export interface ChatTurn {
  role: 'user' | 'assistant'
  content: string
}

export interface ChatDone {
  answer: string
  references: Reference[]
  no_evidence: boolean
}
