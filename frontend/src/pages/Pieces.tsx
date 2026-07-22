import { useEffect, useState } from 'react'
import PageLayout from '../components/layout/PageLayout'
import api from '../lib/api'
import { Piece } from '../lib/types'
import { Edit2, Trash2, FileUp } from 'lucide-react'
import RoleGuard from '../components/common/RoleGuard'

export default function Pieces() {
  const [pieces, setPieces] = useState<Piece[]>([])
  const [loading, setLoading] = useState(true)
  const [showDialog, setShowDialog] = useState(false)
  const [editing, setEditing] = useState<Piece | null>(null)

  const load = () => {
    api.get('/pieces/').then((res) => setPieces(res.data)).finally(() => setLoading(false))
  }

  useEffect(load, [])

  const handleDelete = async (piece_code: string) => {
    if (!confirm('Delete this piece?')) return
    await api.delete(`/pieces/${piece_code}`)
    load()
  }

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const form = new FormData(e.currentTarget)
    const payload = {
      piece_code: form.get('piece_code') as string,
      piece_name: form.get('piece_name') as string,
      material: form.get('material') as string,
      dimensions: form.get('dimensions') as string,
      adhesive_type: form.get('adhesive_type') as string,
      estimated_glue_time_seconds: Number(form.get('glue_time')) || null,
    }

    if (editing) {
      await api.put(`/pieces/${editing.piece_code}`, payload)
    } else {
      await api.post('/pieces/', payload)
    }
    setShowDialog(false)
    load()
  }

  if (loading) return <PageLayout title="Pieces"><p className="p-6 text-secondary">Loading...</p></PageLayout>

  return (
    <RoleGuard allowedRoles={['admin', 'integrator']}>
      <PageLayout title="Pieces">
        <div className="p-6 space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-2xl font-bold">Piece Catalog</h2>
            <button onClick={() => { setEditing(null); setShowDialog(true) }} className="flex items-center gap-2 px-4 py-2 rounded-md bg-primary hover:opacity-90 text-primary-foreground font-semibold transition-opacity">
              <FileUp className="h-4 w-4" />
              Import Piece PDF
            </button>
          </div>

          <div className="bg-muted border border-border rounded-lg overflow-hidden">
            <table className="w-full">
              <thead className="bg-input border-b border-border">
                <tr>
                  <th className="px-6 py-4 text-left font-semibold">Id</th>
                  <th className="px-6 py-4 text-left font-semibold">Piece Name</th>
                  <th className="px-6 py-4 text-left font-semibold">Material</th>
                  <th className="px-6 py-4 text-left font-semibold">Dimensions</th>
                  <th className="px-6 py-4 text-left font-semibold">Adhesive</th>
                  <th className="px-6 py-4 text-left font-semibold">Glue Time</th>
                  <th className="px-6 py-4 text-right font-semibold">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {pieces.map((piece) => (
                  <tr key={piece.id} className="hover:bg-input transition-colors">
                    <td className="px-6 py-4 font-mono text-sm">{piece.piece_code}</td>
                    <td className="px-6 py-4 font-semibold">{piece.piece_name}</td>
                    <td className="px-6 py-4 text-secondary">{piece.material}</td>
                    <td className="px-6 py-4 text-secondary">{piece.dimensions || '—'}</td>
                    <td className="px-6 py-4 text-secondary">{piece.adhesive_type || '—'}</td>
                    <td className="px-6 py-4 text-secondary">{piece.estimated_glue_time_seconds ? `${piece.estimated_glue_time_seconds}s` : '—'}</td>
                    <td className="px-6 py-4 text-right flex justify-end gap-2">
                      <button onClick={() => { setEditing(piece); setShowDialog(true) }} className="p-2 hover:bg-border rounded-md transition-colors">
                        <Edit2 className="h-4 w-4 text-secondary hover:text-foreground" />
                      </button>
                      <button onClick={() => handleDelete(piece.piece_code)} className="p-2 hover:bg-border rounded-md transition-colors">
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {showDialog && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-muted border border-border rounded-lg p-6 max-w-md w-full mx-4">
              <h2 className="text-xl font-bold mb-4">{editing ? 'Edit Piece' : 'Import New Piece'}</h2>

              {!editing && (
                <div className="mb-4 border-2 border-dashed border-border rounded-md p-6 text-center">
                  <FileUp className="h-6 w-6 text-secondary mx-auto mb-2" />
                  <p className="text-sm text-secondary">PDF parsing not wired yet — fill fields manually below</p>
                </div>
              )}

              <form onSubmit={handleSubmit} className="space-y-3">
                <input name="piece_code" placeholder="Piece Code (e.g. P007)" defaultValue={editing?.piece_code} disabled={!!editing} required className="w-full px-4 py-2 rounded-md bg-input border border-border text-foreground disabled:opacity-60" />
                <input name="piece_name" placeholder="Piece Name" defaultValue={editing?.piece_name} required className="w-full px-4 py-2 rounded-md bg-input border border-border text-foreground" />
                <input name="material" placeholder="Material" defaultValue={editing?.material} required className="w-full px-4 py-2 rounded-md bg-input border border-border text-foreground" />
                <input name="dimensions" placeholder="Dimensions (e.g. 180 X 120 X 20)" defaultValue={editing?.dimensions || ''} className="w-full px-4 py-2 rounded-md bg-input border border-border text-foreground" />
                <input name="adhesive_type" placeholder="Adhesive Type" defaultValue={editing?.adhesive_type || ''} className="w-full px-4 py-2 rounded-md bg-input border border-border text-foreground" />
                <input name="glue_time" type="number" placeholder="Estimated Glue Time (seconds)" defaultValue={editing?.estimated_glue_time_seconds || ''} className="w-full px-4 py-2 rounded-md bg-input border border-border text-foreground" />
                <button type="submit" className="w-full px-4 py-2 rounded-md bg-primary hover:opacity-90 text-primary-foreground font-semibold transition-opacity">
                  {editing ? 'Update' : 'Save'}
                </button>
                <button type="button" onClick={() => setShowDialog(false)} className="w-full px-4 py-2 rounded-md border border-border hover:bg-input font-semibold transition-colors">
                  Cancel
                </button>
              </form>
            </div>
          </div>
        )}
      </PageLayout>
    </RoleGuard>
  )
}