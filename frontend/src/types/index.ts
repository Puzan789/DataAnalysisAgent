export interface Step {
  type: string
  label: string
  detail?: string
  timestamp: Date
}

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  steps?: Step[]
}

export interface Thread {
  thread_id?: string
  id?: string
  title?: string
  first_message?: string
  created_at?: string
  updated_at?: string
}

export interface StreamCallbacks {
  onToken: (token: string) => void
  onStep: (step: { type: string; label: string; detail?: string }) => void
  onIds: (ids: string[]) => void
  onDone: () => void
  onError: (error: Error) => void
}

export interface User {
  id: string
  email: string
  name?: string | null
}

export interface TableInfo {
  table_name: string
  row_count: number
}

export interface ColumnInfo {
  column_name: string
  data_type: string
  nullable: boolean
  default: string | null
  max_length: number | null
  numeric_precision: number | null
  is_primary_key: boolean
}

export interface ForeignKey {
  column: string
  references_table: string
  references_column: string
}

export interface TableSchema {
  table_name: string
  row_count: number
  columns: ColumnInfo[]
  primary_keys: string[]
  foreign_keys: ForeignKey[]
}

export interface DatabaseOverview {
  table_count: number
  total_rows: number
  database_size: string
  tables: TableInfo[]
}

export interface TableData {
  table_name: string
  columns: string[]
  rows: Record<string, unknown>[]
  pagination: {
    page: number
    page_size: number
    total_rows: number
    total_pages: number
  }
}

export interface Relationship {
  source_table: string
  source_column: string
  target_table: string
  target_column: string
}

export interface VectorCollectionStats {
  name: string
  status: string
  vectors_count: number
  points_count: number
  vector_size: number | null
  counts: Record<string, number>
  chunk_type_counts: Record<string, number>
  segments_count?: number | null
  distance_metric?: string | null
  hnsw_ef_construct?: number | null
  hnsw_m?: number | null
  shard_number?: number | null
  replication_factor?: number | null
  optimizer_status?: string | null
}

export interface VectorStats {
  qdrant_url?: string | null
  collections: VectorCollectionStats[]
  total_vectors: number
  total_points: number
}
