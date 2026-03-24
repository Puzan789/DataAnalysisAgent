import { useState, useEffect } from 'react'
import {
  Database, Table2, HardDrive, Rows3,
  ChevronRight, Key, Link2, ArrowLeft, Layers,
  ChevronLeft, ChevronsLeft, ChevronsRight,
  Loader2,
} from 'lucide-react'
import {
  fetchDatabaseOverview,
  fetchTableSchema,
  fetchTableData,
  fetchRelationships,
  fetchVectorStats,
  initializeVectorSchema,
} from '@/lib/api'
import type {
  DatabaseOverview,
  TableSchema,
  TableData,
  Relationship,
  VectorStats,
} from '@/types'

type View = 'overview' | 'schema' | 'data'

export default function Dashboard() {
  const [overview, setOverview] = useState<DatabaseOverview | null>(null)
  const [relationships, setRelationships] = useState<Relationship[]>([])
  const [vectorStats, setVectorStats] = useState<VectorStats | null>(null)
  const [selectedTable, setSelectedTable] = useState<string | null>(null)
  const [schema, setSchema] = useState<TableSchema | null>(null)
  const [tableData, setTableData] = useState<TableData | null>(null)
  const [view, setView] = useState<View>('overview')
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [isInitializingVector, setIsInitializingVector] = useState(false)
  const [vectorActionMsg, setVectorActionMsg] = useState<string | null>(null)

  const formatNumber = (value?: number | null) =>
    value !== undefined && value !== null ? value.toLocaleString() : '—'

  useEffect(() => {
    loadOverview()
  }, [])

  const loadOverview = async () => {
    setLoading(true)
    try {
      const [ov, rels, vec] = await Promise.all([
        fetchDatabaseOverview(),
        fetchRelationships(),
        fetchVectorStats().catch(() => null),
      ])
      setOverview(ov)
      setRelationships(rels)
      setVectorStats(vec)
    } catch (err) {
      console.error('Failed to load overview:', err)
    }
    setLoading(false)
  }

  const openTable = async (tableName: string) => {
    setSelectedTable(tableName)
    setView('schema')
    setLoading(true)
    try {
      const s = await fetchTableSchema(tableName)
      setSchema(s)
    } catch (err) {
      console.error('Failed to load schema:', err)
    }
    setLoading(false)
  }

  const openData = async (tableName: string, p = 1) => {
    setSelectedTable(tableName)
    setView('data')
    setPage(p)
    setLoading(true)
    try {
      const d = await fetchTableData(tableName, p)
      setTableData(d)
    } catch (err) {
      console.error('Failed to load data:', err)
    }
    setLoading(false)
  }

  const goBack = () => {
    if (view === 'data') {
      setView('schema')
    } else {
      setView('overview')
      setSelectedTable(null)
      setSchema(null)
    }
  }

  const handleInitializeVector = async () => {
    setIsInitializingVector(true)
    setVectorActionMsg(null)
    try {
      await initializeVectorSchema()
      const vec = await fetchVectorStats().catch(() => null)
      setVectorStats(vec)
      setVectorActionMsg('Vector store initialized successfully')
    } catch (err) {
      console.error('Failed to initialize vector schema:', err)
      setVectorActionMsg('Failed to initialize vector store')
    }
    setIsInitializingVector(false)
  }

  if (loading && !overview) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <Loader2 size={24} className="animate-spin text-brand" />
      </div>
    )
  }

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-6xl mx-auto px-6 py-8">

        {/* Breadcrumb */}
        {view !== 'overview' && (
          <button
            onClick={goBack}
            className="flex items-center gap-1.5 text-sm text-zinc-500 hover:text-zinc-300 mb-6 transition-colors"
          >
            <ArrowLeft size={14} />
            {view === 'data' ? 'Schema' : 'All Tables'}
          </button>
        )}

        {/* OVERVIEW */}
        {view === 'overview' && overview && (
          <>
            {/* Stats cards */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
              <StatCard
                icon={<Table2 size={18} />}
                label="Tables"
                value={overview.table_count.toString()}
              />
              <StatCard
                icon={<Rows3 size={18} />}
                label="Total Rows"
                value={overview.total_rows.toLocaleString()}
              />
              <StatCard
                icon={<HardDrive size={18} />}
                label="Database Size"
                value={overview.database_size}
              />
            </div>

            {vectorStats && (
              <div className="mb-8">
                <div className="flex items-center justify-between mb-3">
                  <h2 className="text-sm font-semibold text-zinc-300 flex items-center gap-2">
                    <Layers size={14} className="text-brand" />
                    Vector Store
                  </h2>
                  <div className="flex items-center gap-3">
                    {vectorStats.qdrant_url && (
                      <span className="text-[11px] text-zinc-500">{vectorStats.qdrant_url}</span>
                    )}
                    <button
                      onClick={handleInitializeVector}
                      disabled={isInitializingVector}
                      className="px-3 py-1.5 text-xs font-medium bg-brand text-white rounded-lg hover:bg-brand-light transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
                    >
                      {isInitializingVector
                        ? 'Initializing...'
                        : (vectorStats.total_points || 0) > 0
                          ? 'Refresh Vector Store'
                          : 'Create Vector Store'}
                    </button>
                  </div>
                </div>
                {vectorActionMsg && (
                  <p className="text-xs text-zinc-400 mb-3">{vectorActionMsg}</p>
                )}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {vectorStats.collections.map((col) => {
                    const chunkTotal = Object.values(col.counts || {}).reduce(
                      (acc, n) => acc + (n || 0),
                      0,
                    )
                    const statusTone = ['green', 'ready', 'ok', 'active'].includes(
                      (col.status || '').toLowerCase(),
                    )
                    return (
                      <div key={col.name} className="bg-surface-1 border border-zinc-800 rounded-xl p-4">
                        <div className="flex items-center justify-between mb-3">
                          <div className="flex items-center gap-2">
                            <Layers size={14} className="text-brand" />
                            <div>
                              <p className="text-sm font-semibold text-zinc-200">{col.name}</p>
                              <p className="text-[11px] text-zinc-500">Vectors: {formatNumber(col.vectors_count)}</p>
                            </div>
                          </div>
                          <span
                            className={`text-[11px] px-2 py-0.5 rounded-full ${
                              statusTone
                                ? 'bg-emerald-500/15 text-emerald-400'
                                : 'bg-amber-500/15 text-amber-400'
                            }`}
                          >
                            {col.status}
                          </span>
                        </div>
                        <div className="grid grid-cols-2 gap-3 text-xs text-zinc-400">
                          <Metric label="Points" value={formatNumber(col.points_count)} />
                          <Metric label="Chunks" value={formatNumber(chunkTotal)} />
                          <Metric label="Dimension" value={col.vector_size ? col.vector_size.toString() : '—'} />
                          <Metric label="Segments" value={formatNumber(col.segments_count)} />
                          <Metric label="Distance" value={col.distance_metric || '—'} />
                          <Metric label="HNSW (m/ef)" value={col.hnsw_m && col.hnsw_ef_construct ? `${col.hnsw_m}/${col.hnsw_ef_construct}` : '—'} />
                          <Metric label="Shards" value={formatNumber(col.shard_number)} />
                          <Metric label="Replication" value={formatNumber(col.replication_factor)} />
                        </div>

                        {col.chunk_type_counts && (
                          <div className="mt-3 flex flex-wrap gap-2 text-[11px]">
                            {Object.entries(col.chunk_type_counts).map(([type, count]) => (
                              <span
                                key={type}
                                className="px-2 py-1 rounded-full bg-surface-2 border border-zinc-800 text-zinc-300"
                              >
                                {type}: {formatNumber(count)}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
              </div>
            )}

            {/* Tables list */}
            <div className="mb-8">
              <h2 className="text-sm font-semibold text-zinc-300 mb-3 flex items-center gap-2">
                <Database size={14} className="text-brand" />
                Tables
              </h2>
              <div className="bg-surface-1 border border-zinc-800 rounded-xl overflow-hidden">
                {overview.tables.map((t, i) => (
                  <div
                    key={t.table_name}
                    onClick={() => openTable(t.table_name)}
                    className={`
                      flex items-center justify-between px-4 py-3 cursor-pointer
                      hover:bg-surface-2 transition-colors
                      ${i > 0 ? 'border-t border-zinc-800/60' : ''}
                    `}
                  >
                    <div className="flex items-center gap-3">
                      <Table2 size={14} className="text-zinc-500" />
                      <span className="text-sm font-medium text-zinc-200">{t.table_name}</span>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-xs text-zinc-500 bg-surface-2 px-2 py-0.5 rounded-full">
                        {t.row_count.toLocaleString()} rows
                      </span>
                      <ChevronRight size={14} className="text-zinc-600" />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Relationships */}
            {relationships.length > 0 && (
              <div>
                <h2 className="text-sm font-semibold text-zinc-300 mb-3 flex items-center gap-2">
                  <Link2 size={14} className="text-brand" />
                  Relationships
                </h2>
                <div className="bg-surface-1 border border-zinc-800 rounded-xl overflow-hidden">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-zinc-800">
                        <th className="text-left px-4 py-2.5 text-xs font-medium text-zinc-500 uppercase tracking-wider">Source</th>
                        <th className="text-left px-4 py-2.5 text-xs font-medium text-zinc-500 uppercase tracking-wider">Column</th>
                        <th className="text-left px-4 py-2.5 text-xs font-medium text-zinc-500 uppercase tracking-wider">References</th>
                        <th className="text-left px-4 py-2.5 text-xs font-medium text-zinc-500 uppercase tracking-wider">FK Column</th>
                      </tr>
                    </thead>
                    <tbody>
                      {relationships.map((r, i) => (
                        <tr key={i} className="border-t border-zinc-800/60 hover:bg-surface-2">
                          <td className="px-4 py-2.5 text-zinc-300 font-mono text-xs">{r.source_table}</td>
                          <td className="px-4 py-2.5 text-zinc-400 font-mono text-xs">{r.source_column}</td>
                          <td className="px-4 py-2.5 text-brand-light font-mono text-xs">{r.target_table}</td>
                          <td className="px-4 py-2.5 text-zinc-400 font-mono text-xs">{r.target_column}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </>
        )}

        {/* SCHEMA VIEW */}
        {view === 'schema' && schema && (
          <>
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-lg font-semibold text-zinc-100">{schema.table_name}</h2>
                <p className="text-xs text-zinc-500 mt-0.5">{schema.row_count.toLocaleString()} rows</p>
              </div>
              <button
                onClick={() => openData(schema.table_name)}
                className="px-3 py-1.5 text-xs font-medium bg-brand text-white rounded-lg hover:bg-brand-light transition-colors"
              >
                View Data
              </button>
            </div>

            {/* Columns */}
            <div className="mb-6">
              <h3 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-2">Columns</h3>
              <div className="bg-surface-1 border border-zinc-800 rounded-xl overflow-hidden">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-zinc-800">
                      <th className="text-left px-4 py-2.5 text-xs font-medium text-zinc-500 uppercase tracking-wider">Name</th>
                      <th className="text-left px-4 py-2.5 text-xs font-medium text-zinc-500 uppercase tracking-wider">Type</th>
                      <th className="text-left px-4 py-2.5 text-xs font-medium text-zinc-500 uppercase tracking-wider">Nullable</th>
                      <th className="text-left px-4 py-2.5 text-xs font-medium text-zinc-500 uppercase tracking-wider">Default</th>
                      <th className="text-left px-4 py-2.5 text-xs font-medium text-zinc-500 uppercase tracking-wider">Key</th>
                    </tr>
                  </thead>
                  <tbody>
                    {schema.columns.map((col, i) => (
                      <tr key={col.column_name} className={i > 0 ? 'border-t border-zinc-800/60' : ''}>
                        <td className="px-4 py-2.5 font-mono text-xs text-zinc-200 flex items-center gap-2">
                          {col.is_primary_key && <Key size={11} className="text-amber-400" />}
                          {col.column_name}
                        </td>
                        <td className="px-4 py-2.5 font-mono text-xs text-brand-light">{col.data_type}</td>
                        <td className="px-4 py-2.5 text-xs text-zinc-500">
                          {col.nullable ? 'YES' : 'NO'}
                        </td>
                        <td className="px-4 py-2.5 font-mono text-xs text-zinc-500">
                          {col.default || '—'}
                        </td>
                        <td className="px-4 py-2.5 text-xs">
                          {col.is_primary_key && (
                            <span className="px-1.5 py-0.5 bg-amber-500/15 text-amber-400 rounded text-[10px] font-medium">PK</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Foreign Keys */}
            {schema.foreign_keys.length > 0 && (
              <div>
                <h3 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-2">Foreign Keys</h3>
                <div className="bg-surface-1 border border-zinc-800 rounded-xl overflow-hidden">
                  {schema.foreign_keys.map((fk, i) => (
                    <div
                      key={i}
                      className={`flex items-center gap-3 px-4 py-2.5 text-xs ${i > 0 ? 'border-t border-zinc-800/60' : ''}`}
                    >
                      <span className="font-mono text-zinc-300">{fk.column}</span>
                      <ChevronRight size={12} className="text-zinc-600" />
                      <button
                        onClick={() => openTable(fk.references_table)}
                        className="font-mono text-brand-light hover:underline"
                      >
                        {fk.references_table}.{fk.references_column}
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}

        {/* DATA VIEW */}
        {view === 'data' && tableData && (
          <>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-zinc-100">{tableData.table_name}</h2>
              <span className="text-xs text-zinc-500">
                {tableData.pagination.total_rows.toLocaleString()} total rows
              </span>
            </div>

            <div className="bg-surface-1 border border-zinc-800 rounded-xl overflow-hidden mb-4">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-zinc-800">
                      {tableData.columns.map((col) => (
                        <th
                          key={col}
                          className="text-left px-4 py-2.5 text-[11px] font-medium text-zinc-500 uppercase tracking-wider whitespace-nowrap"
                        >
                          {col}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {tableData.rows.map((row, i) => (
                      <tr
                        key={i}
                        className={`hover:bg-surface-2 transition-colors ${i > 0 ? 'border-t border-zinc-800/40' : ''}`}
                      >
                        {tableData.columns.map((col) => (
                          <td
                            key={col}
                            className="px-4 py-2 text-xs text-zinc-300 font-mono whitespace-nowrap max-w-[300px] truncate"
                            title={String(row[col] ?? '')}
                          >
                            {row[col] == null ? (
                              <span className="text-zinc-600 italic">null</span>
                            ) : (
                              String(row[col])
                            )}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Pagination */}
            {tableData.pagination.total_pages > 1 && (
              <div className="flex items-center justify-between">
                <span className="text-xs text-zinc-500">
                  Page {tableData.pagination.page} of {tableData.pagination.total_pages}
                </span>
                <div className="flex items-center gap-1">
                  <PaginationBtn
                    onClick={() => openData(tableData.table_name, 1)}
                    disabled={page === 1}
                  >
                    <ChevronsLeft size={14} />
                  </PaginationBtn>
                  <PaginationBtn
                    onClick={() => openData(tableData.table_name, page - 1)}
                    disabled={page === 1}
                  >
                    <ChevronLeft size={14} />
                  </PaginationBtn>
                  <PaginationBtn
                    onClick={() => openData(tableData.table_name, page + 1)}
                    disabled={page >= tableData.pagination.total_pages}
                  >
                    <ChevronRight size={14} />
                  </PaginationBtn>
                  <PaginationBtn
                    onClick={() => openData(tableData.table_name, tableData.pagination.total_pages)}
                    disabled={page >= tableData.pagination.total_pages}
                  >
                    <ChevronsRight size={14} />
                  </PaginationBtn>
                </div>
              </div>
            )}
          </>
        )}

        {loading && (view === 'schema' || view === 'data') && (
          <div className="flex justify-center py-12">
            <Loader2 size={20} className="animate-spin text-brand" />
          </div>
        )}
      </div>
    </div>
  )
}

function StatCard({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="bg-surface-1 border border-zinc-800 rounded-xl p-4 flex items-center gap-4">
      <div className="w-10 h-10 rounded-lg bg-brand-dim flex items-center justify-center text-brand">
        {icon}
      </div>
      <div>
        <p className="text-[11px] text-zinc-500 uppercase tracking-wider">{label}</p>
        <p className="text-lg font-semibold text-zinc-100">{value}</p>
      </div>
    </div>
  )
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-[11px] uppercase tracking-wide text-zinc-500">{label}</span>
      <span className="text-sm text-zinc-100 font-medium">{value}</span>
    </div>
  )
}

function PaginationBtn({
  children,
  onClick,
  disabled,
}: {
  children: React.ReactNode
  onClick: () => void
  disabled: boolean
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="p-1.5 rounded-md bg-surface-2 border border-zinc-800 text-zinc-400 hover:text-zinc-200 hover:border-zinc-700 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
    >
      {children}
    </button>
  )
}
