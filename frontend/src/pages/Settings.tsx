import { useEffect, useState } from 'react'
import PageLayout from '../components/layout/PageLayout'
import api from '../lib/api'
import { Save, Wifi } from 'lucide-react'
import RoleGuard from '../components/common/RoleGuard'

const MOCK_LOGS = [
  '2026-07-14 09:12:03 INFO  robot_bridge  Connected to Robot PC',
  '2026-07-14 09:22:10 WARN  camera        Frame drop detected, retrying',
  '2026-07-14 10:04:02 ERROR robot_bridge  Robot PC unreachable (timeout)',
]

export default function Settings() {
  const [robotPcUrl, setRobotPcUrl] = useState('')
  const [loading, setLoading] = useState(true)
  const [saved, setSaved] = useState(false)
  const [showDetailedLogs, setShowDetailedLogs] = useState(false)

  useEffect(() => {
    api.get('/settings/').then((res) => setRobotPcUrl(res.data.robot_pc_url || '')).finally(() => setLoading(false))
  }, [])

  const handleSave = async () => {
    await api.put('/settings/', { robot_pc_url: robotPcUrl })
    setSaved(true)
    setTimeout(() => setSaved(false), 2500)
  }

  if (loading) return <PageLayout title="Settings"><p className="p-6 text-secondary">Loading...</p></PageLayout>

  return (
    <RoleGuard allowedRoles={['admin', 'integrator']}>
      <PageLayout title="Settings">
        <div className="p-6 space-y-6 max-w-3xl">
          {saved && <div className="px-4 py-3 rounded-md bg-success/20 text-success text-sm font-semibold">Settings saved successfully</div>}

          <div className="bg-muted border border-border rounded-lg p-6">
            <div className="flex items-center gap-2 mb-4">
              <Wifi className="h-5 w-5 text-primary" />
              <h2 className="text-lg font-bold">Robot IP</h2>
            </div>
            <div className="flex gap-3">
              <input
                value={robotPcUrl}
                onChange={(e) => setRobotPcUrl(e.target.value)}
                placeholder="http://192.168.1.50:8001"
                className="flex-1 px-4 py-2 rounded-md bg-input border border-border text-foreground font-mono text-sm"
              />
              <button onClick={handleSave} className="flex items-center gap-2 px-4 py-2 rounded-md bg-primary hover:opacity-90 text-primary-foreground font-semibold transition-opacity">
                <Save className="h-4 w-4" />
                Save
              </button>
            </div>
          </div>

          <div className="bg-muted border border-border rounded-lg overflow-hidden">
            <div className="px-6 py-4 border-b border-border flex items-center justify-between">
              <h2 className="text-lg font-bold">Logs</h2>
              <span className="text-xs text-secondary">(sample data — log ingestion not built yet)</span>
            </div>
            <div className="p-4 bg-black/90 font-mono text-xs text-green-400 max-h-72 overflow-y-auto space-y-1">
              {MOCK_LOGS.map((line, i) => <div key={i}>{line}</div>)}
            </div>
          </div>
        </div>
      </PageLayout>
    </RoleGuard>
  )
}