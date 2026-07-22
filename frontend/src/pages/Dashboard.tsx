import { useEffect, useState } from 'react'
import PageLayout from '../components/layout/PageLayout'
import { StatusBadge } from '../components/common/StatusBadge'
import api from '../lib/api'
import { Piece, HistoryRecord } from '../lib/types'
import { Camera, ScanLine } from 'lucide-react'

export default function Dashboard() {
  const [pieces, setPieces] = useState<Piece[]>([])
  const [history, setHistory] = useState<HistoryRecord[]>([])
  const [online, setOnline] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [robotPcHost, setRobotPcHost] = useState<string | null>(null)


  // These are input controls the user adjusts, not fetched data — that's correct as local state
  const [blend, setBlend] = useState(350)
  const [acc, setAcc] = useState(350)
  const [speed, setSpeed] = useState(350)

  useEffect(() => {
    async function load() {
      try {
        const [piecesRes, historyRes, statusRes] = await Promise.all([
          api.get('/pieces/'),
          api.get('/history/'),
          api.get('/robot/status'),
          api.get('/settings/').then((res) => {
            if (res.data.robot_pc_url) {
              const host = new URL(res.data.robot_pc_url).hostname
              setRobotPcHost(host)
            }
          })
        ])
        setPieces(piecesRes.data)
        setHistory(historyRes.data)
        setOnline(statusRes.data.online)
      } catch (err) {
        setError('Could not load dashboard data. Is the backend running?')
        console.error(err)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  if (loading) {
    return (
      <PageLayout title="Dashboard">
        <p className="p-6 text-secondary">Loading dashboard...</p>
      </PageLayout>
    )
  }
  if (error) {
    return (
      <PageLayout title="Dashboard">
        <p className="p-6 text-destructive">{error}</p>
      </PageLayout>
    )
  }

  const finishedPieces = history.filter((h) => h.status === 'completed').length
  const recentAlerts = history.filter((h) => h.status === 'failed').length

  const oneHourAgo = Date.now() - 60 * 60 * 1000
  const applicationRate = history.filter(
    (h) => new Date(h.run_date).getTime() > oneHourAgo && h.status === 'completed'
  ).length

  const materialCounts: Record<string, number> = {}
  history.forEach((record) => {
    materialCounts[record.piece.material] = (materialCounts[record.piece.material] || 0) + 1
  })

  return (
    <PageLayout title="Dashboard" robotOnline={online} recentAlerts={recentAlerts}>
      <div className="p-6 space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold">Robot Overview</h2>
          <StatusBadge status={online ? 'online' : 'offline'} />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="lg:col-span-2 bg-muted border border-border rounded-lg overflow-hidden">
            <div className="px-6 py-4 border-b border-border">
              <h3 className="font-bold">Robot Preview</h3>
            </div>
            <div className="p-4 flex gap-4">
              <div className="flex-1 relative bg-black rounded-md aspect-video flex items-center justify-center">
                <p className="text-white/40 text-sm">Unity simulation view — integration pending</p>
                <div className="absolute bottom-3 left-3 text-xs text-white/50 leading-relaxed">
                  <div>Press left/right arrow to select a robot joint</div>
                  <div>Press up/down arrow to move selected joint</div>
                </div>
              </div>
              <div className="w-40 flex flex-col gap-4 justify-center">
                <SliderControl label="blend" value={blend} onChange={setBlend} />
                <SliderControl label="acc" value={acc} onChange={setAcc} />
                <SliderControl label="speed" value={speed} onChange={setSpeed} />
                <div className="flex gap-2 mt-2">
                  <button className="flex-1 px-3 py-2 bg-primary text-primary-foreground text-sm font-semibold rounded-md hover:opacity-90 transition-opacity">
                    Run Sim
                  </button>
                  <button className="flex-1 px-3 py-2 bg-secondary/20 text-secondary text-sm font-semibold rounded-md hover:bg-secondary/30 transition-colors">
                    Reset
                  </button>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-muted border border-border rounded-lg overflow-hidden">
            <div className="px-6 py-4 border-b border-border flex items-center gap-2">
              <Camera className="h-4 w-4 text-secondary" />
              <h3 className="font-bold">Camera Preview</h3>
            </div>
            <div className="p-4">
              <div className="relative bg-black/80 rounded-md aspect-video flex items-center justify-center">
                {robotPcHost ? (
                  <img src={`http://${robotPcHost}:8095/`} alt="Camera feed" className="w-full h-full object-contain" />
                ) : (
                  <p className="text-white/30 text-xs">Camera unavailable — configure Robot PC IP in Settings</p>
                )}
                <ScanLine className="absolute top-2 left-2 h-4 w-4 text-white/40" />
                <ScanLine className="absolute top-2 right-2 h-4 w-4 text-white/40 -scale-x-100" />
                <ScanLine className="absolute bottom-2 left-2 h-4 w-4 text-white/40 -scale-y-100" />
                <ScanLine className="absolute bottom-2 right-2 h-4 w-4 text-white/40 -scale-100" />
              </div>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <StatCard label="Total Pieces" value={pieces.length} />
          <StatCard label="Finished Pieces" value={finishedPieces} />
          <StatCard label="Application Rate (last hr)" value={`${applicationRate} Pcs/H`} />
        </div>

        <div className="bg-muted border border-border rounded-lg p-6">
          <h3 className="font-bold mb-4">Runs by Material</h3>
          <div className="space-y-2">
            {Object.entries(materialCounts).map(([material, count]) => (
              <div key={material} className="flex items-center gap-3">
                <span className="w-28 text-sm text-secondary">{material}</span>
                <div className="flex-1 bg-input rounded-full h-3">
                  <div
                    className="bg-primary h-3 rounded-full"
                    style={{ width: `${(count / history.length) * 100}%` }}
                  />
                </div>
                <span className="text-sm font-semibold w-6 text-right">{count}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </PageLayout>
  )
}

function SliderControl({
  label,
  value,
  onChange,
}: {
  label: string
  value: number
  onChange: (v: number) => void
}) {
  return (
    <div>
      <div className="flex justify-between text-xs text-secondary mb-1">
        <span className="capitalize">{label}</span>
        <span>{value}</span>
      </div>
      <input
        type="range"
        min={0}
        max={1000}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full accent-primary"
      />
    </div>
  )
}

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="bg-muted border border-border rounded-lg p-6">
      <div className="text-secondary text-sm font-semibold">{label}</div>
      <div className="text-3xl font-bold text-foreground mt-2">{value}</div>
    </div>
  )
}