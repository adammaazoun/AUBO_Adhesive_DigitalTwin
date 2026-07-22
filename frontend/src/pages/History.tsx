import { useEffect, useState } from 'react'
import PageLayout from '../components/layout/PageLayout'
import api from '../lib/api'
import { HistoryRecord } from '../lib/types'

export default function History() {
  const [history, setHistory] = useState<HistoryRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState<HistoryRecord | null>(null)

  useEffect(() => {
    api.get('/history/').then((res) => setHistory(res.data)).finally(() => setLoading(false))
  }, [])

  if (loading) return <PageLayout title="History"><p className="p-6 text-secondary">Loading...</p></PageLayout>


  return (
    <PageLayout title="History">
      <div className="p-6 space-y-6">
        <div className="bg-muted border border-border rounded-lg overflow-hidden">
          <table className="w-full">
            <thead className="bg-input border-b border-border">
              <tr>
                <th className="px-6 py-4 text-left font-semibold">Id</th>
                <th className="px-6 py-4 text-left font-semibold">Piece Name</th>
                <th className="px-6 py-4 text-left font-semibold">Date</th>
                <th className="px-6 py-4 text-left font-semibold">Material</th>
                <th className="px-6 py-4 text-right font-semibold">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {history.map((record) => (
                <tr key={record.id} className="hover:bg-input transition-colors">
                  <td className="px-6 py-4 font-mono text-sm">{record.piece.piece_code}</td>
                  <td className="px-6 py-4 font-semibold">{record.piece.piece_name}</td>
                  <td className="px-6 py-4 text-secondary">
                    {new Date(record.run_date).toLocaleDateString()}
                  </td>
                  <td className="px-6 py-4 text-secondary">{record.piece.material}</td>
                  <td className="px-6 py-4 text-right">
                    <button
                      onClick={() => setSelected(record)}
                      className="px-3 py-1.5 rounded-md border border-border hover:bg-input text-sm font-semibold transition-colors"
                    >
                      More Details
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {selected && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-muted border border-border rounded-lg p-6 max-w-md w-full mx-4">
            <h2 className="text-xl font-bold mb-4">Piece Details</h2>
            <div className="space-y-3 text-sm">
              <DetailRow label="Id" value={selected.piece.piece_code} />
              <DetailRow label="Piece Name" value={selected.piece.piece_name} />
              <DetailRow label="Date" value={new Date(selected.run_date).toLocaleDateString()} />
              <DetailRow label="Material" value={selected.piece.material} />
              <DetailRow label="Dimensions" value={selected.piece.dimensions || '—'} />
              <DetailRow label="Adhesive Type" value={selected.piece.adhesive_type || '—'} />
              <DetailRow
                label="Estimated Glue Time"
                value={
                  selected.piece.estimated_glue_time_seconds
                    ? `${selected.piece.estimated_glue_time_seconds}s`
                    : '—'
                }
              />
            </div>
            <div className="flex gap-2 mt-6">
              <button
                onClick={() => alert('Export Summary — not wired to backend yet')}
                className="flex-1 px-4 py-2 rounded-md bg-primary hover:opacity-90 text-primary-foreground font-semibold transition-opacity"
              >
                Export Summary
              </button>
              <button
                onClick={() => setSelected(null)}
                className="flex-1 px-4 py-2 rounded-md border border-border hover:bg-input font-semibold transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </PageLayout>
  )
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between">
      <span className="text-secondary">{label}</span>
      <span className="font-semibold">{value}</span>
    </div>
  )
}