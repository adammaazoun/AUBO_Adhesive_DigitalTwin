import { useEffect, useState } from 'react'
import PageLayout from '../components/layout/PageLayout'
import { Piece } from '../lib/types'
import api from '../lib/api'
import { useAuth } from '../context/AuthContext'
import RoleGuard from '../components/common/RoleGuard'
import { Usb, Smartphone, QrCode, RotateCw, RotateCcw } from 'lucide-react'

export default function RobotView() {
  const [pieces, setPieces] = useState<Piece[]>([])
  const [selectedPiece, setSelectedPiece] = useState('')
  const [online, setOnline] = useState(false)
  const [loading, setLoading] = useState(true)
  const [mode, setMode] = useState<'real_world' | 'simulation'>('simulation')
  const [controlTab, setControlTab] = useState<'joystick' | 'gyroscope'>('joystick')
  const [inputDevice, setInputDevice] = useState('onscreen')
  const [statusMsg, setStatusMsg] = useState<string | null>(null)
  const [params, setParams] = useState({ speed_fraction: 1.0, acc: 0.6, blend_radius_mm: 2 })

  const { currentUser, getPermissions } = useAuth()
  const permissions = currentUser ? getPermissions(currentUser.role) : null

  useEffect(() => {
    async function load() {
      try {
        const [piecesRes, statusRes] = await Promise.all([
          api.get('/pieces/'),
          api.get('/robot/status'),
        ])
        setPieces(piecesRes.data)
        setOnline(statusRes.data.online)
        if (piecesRes.data.length > 0) setSelectedPiece(piecesRes.data[0].piece_code)
      } catch (err) {
        console.error(err)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  useEffect(() => {
    api.get('/robot/parameters')
      .then((res) => setParams(res.data.speed_fraction !== undefined ? {
        speed_fraction: res.data.speed_fraction,
        acc: res.data.acc,
        blend_radius_mm: res.data.blend_radius * 1000,
      } : params))
      .catch(() => {}) // Robot PC may be offline — keep defaults, not fatal
  }, [])

  const sendCommand = async (command: 'start' | 'pause' | 'stop') => {
    setStatusMsg(null)
    try {
      await api.post('/robot/command', { command, piece_code: selectedPiece || null })
      setStatusMsg(`Command "${command}" sent successfully`)
    } catch (err: any) {
      setStatusMsg(err.response?.data?.detail || 'Robot PC unreachable')
    }
  }

  const saveParameters = async () => {
    setStatusMsg(null)
    try {
      await api.post('/robot/parameters', params)
      setStatusMsg('Parameters sent to robot')
    } catch (err: any) {
      setStatusMsg(err.response?.data?.detail || 'Robot PC unreachable')
    }
  }

  const handleJog = (axis: string) => {
    // No real-time jog endpoint yet — this needs a WebSocket, planned for later
    console.log(`[jog] ${axis}`)
  }

  if (loading) {
    return (
      <PageLayout title="Robot View">
        <p className="p-6 text-secondary">Loading...</p>
      </PageLayout>
    )
  }

  return (
    <PageLayout title="Robot View" robotOnline={online}>
      <div className="p-6 space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold">Unity Simulation</h2>
          <div className="flex items-center gap-3 bg-muted border border-border rounded-full p-1">
            <button
              onClick={() => setMode('real_world')}
              className={`px-4 py-1.5 rounded-full text-sm font-semibold transition-colors ${
                mode === 'real_world' ? 'bg-primary text-primary-foreground' : 'text-secondary'
              }`}
            >
              Real World
            </button>
            <button
              onClick={() => setMode('simulation')}
              className={`px-4 py-1.5 rounded-full text-sm font-semibold transition-colors ${
                mode === 'simulation' ? 'bg-primary text-primary-foreground' : 'text-secondary'
              }`}
            >
              Simulation
            </button>
          </div>
        </div>

        <div className="bg-muted border border-border rounded-lg overflow-hidden">
          <div className="p-4">
            <div className="bg-black rounded-md aspect-video flex items-center justify-center relative">
              <p className="text-white/40 text-sm">
                {mode === 'simulation' ? 'Unity simulation — integration pending' : 'Live robot view — integration pending'}
              </p>
            </div>
          </div>

          <RoleGuard allowedRoles={['operator', 'admin', 'integrator']}>
            <div className="px-4 pb-4 space-y-3">
              <div className="flex items-center gap-3">
                <label className="text-sm font-semibold">Piece:</label>
                <select
                  value={selectedPiece}
                  onChange={(e) => setSelectedPiece(e.target.value)}
                  className="px-3 py-1.5 rounded-md bg-input border border-border text-sm"
                >
                  {pieces.map((p) => (
                    <option key={p.id} value={p.piece_code}>
                      {p.piece_code} — {p.piece_name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex gap-3">
                <button onClick={() => sendCommand('start')} className="px-4 py-2 rounded-md bg-primary hover:opacity-90 text-primary-foreground font-semibold transition-opacity">
                  Start
                </button>
                <button onClick={() => sendCommand('pause')} className="px-4 py-2 rounded-md border border-border hover:bg-input font-semibold transition-colors">
                  Pause
                </button>
                <button onClick={() => sendCommand('stop')} className="px-4 py-2 rounded-md border border-border hover:bg-input font-semibold transition-colors">
                  Stop
                </button>
              </div>
              {statusMsg && <p className="text-sm text-secondary">{statusMsg}</p>}
            </div>
          </RoleGuard>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <RoleGuard allowedRoles={['operator', 'admin', 'integrator']}>
            <div className="bg-muted border border-border rounded-lg p-6">
              <h3 className="font-bold mb-4">Robot Parameters</h3>
              <div className="space-y-4">
                <ParamInput label="Speed Fraction" value={params.speed_fraction} step={0.01} min={0.02} max={2.0} onChange={(v) => setParams({ ...params, speed_fraction: v })} />
                <ParamInput label="Acceleration (m/s²)" value={params.acc} step={0.05} min={0.05} max={3.0} onChange={(v) => setParams({ ...params, acc: v })} />
                <ParamInput label="Blend Radius (mm)" value={params.blend_radius_mm} step={0.5} min={0} max={50} onChange={(v) => setParams({ ...params, blend_radius_mm: v })} />
                <button onClick={saveParameters} className="w-full px-4 py-2 rounded-md bg-primary hover:opacity-90 text-primary-foreground font-semibold transition-opacity">
                  Send Parameters
                </button>
              </div>
            </div>
          </RoleGuard>

          <RoleGuard allowedRoles={['integrator']}>
            <div className="bg-muted border border-border rounded-lg p-6">
              <h3 className="font-bold mb-4">Manual Control</h3>
              <div className="flex gap-2 mb-4 border-b border-border">
                <button
                  onClick={() => setControlTab('joystick')}
                  className={`px-4 py-2 text-sm font-semibold border-b-2 transition-colors ${
                    controlTab === 'joystick'
                      ? 'border-primary text-primary'
                      : 'border-transparent text-secondary'
                  }`}
                >
                  Joystick Control
                </button>
                <button
                  onClick={() => setControlTab('gyroscope')}
                  className={`px-4 py-2 text-sm font-semibold border-b-2 transition-colors ${
                    controlTab === 'gyroscope'
                      ? 'border-primary text-primary'
                      : 'border-transparent text-secondary'
                  }`}
                >
                  Gyroscope Control
                </button>
              </div>

              {controlTab === 'joystick' ? (
                <div className="space-y-6">
                  {/* Input source selector */}
                  <div className="flex items-center gap-3">
                    <Usb className="h-4 w-4 text-secondary" />
                    <select
                      value={inputDevice}
                      onChange={(e) => setInputDevice(e.target.value as typeof inputDevice)}
                      className="px-3 py-1.5 rounded-md bg-input border border-border text-sm"
                    >
                      <option value="onscreen">On-screen buttons</option>
                      <option value="usb-generic">USB Joystick (Generic Gamepad)</option>
                      <option value="usb-spacemouse">USB Joystick (3Dconnexion SpaceMouse)</option>
                    </select>
                    {inputDevice !== 'onscreen' && (
                      <span className="text-xs text-warning">Not connected — plug in device</span>
                    )}
                  </div>

                  {/* Position + Rotation pads */}
                  <div className="flex flex-wrap gap-10 justify-center">
                    <div>
                      <div className="text-xs text-secondary mb-3 text-center font-semibold">Position</div>
                      <div className="grid grid-cols-3 gap-2">
                        <ArrowButton direction="up" label="Z+" onClick={() => handleJog('Z+')} />
                        <div />
                        <ArrowButton direction="down" label="Z-" onClick={() => handleJog('Z-')} />

                        <div />
                        <ArrowButton direction="up" label="X+" onClick={() => handleJog('X+')} />
                        <div />

                        <ArrowButton direction="left" label="Y-" onClick={() => handleJog('Y-')} />
                        <ArrowButton direction="down" label="X-" onClick={() => handleJog('X-')} />
                        <ArrowButton direction="right" label="Y+" onClick={() => handleJog('Y+')} />
                      </div>
                    </div>

                    <div>
                      <div className="text-xs text-secondary mb-3 text-center font-semibold">Rotation</div>
                      <div className="grid grid-cols-3 gap-2">
                        <RotateButton clockwise label="RZ+" onClick={() => handleJog('RZ+')} />
                        <div />
                        <RotateButton clockwise={false} label="RZ-" onClick={() => handleJog('RZ-')} />

                        <div />
                        <RotateButton clockwise label="RX+" onClick={() => handleJog('RX+')} />
                        <div />

                        <RotateButton clockwise={false} label="RY-" onClick={() => handleJog('RY-')} />
                        <RotateButton clockwise={false} label="RX-" onClick={() => handleJog('RX-')} />
                        <RotateButton clockwise label="RY+" onClick={() => handleJog('RY+')} />
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-center py-6">
                  <Smartphone className="h-10 w-10 text-secondary mx-auto mb-3" />
                  <p className="text-sm text-secondary mb-4 max-w-xs mx-auto">
                    Gyroscope control runs from the Tunibot mobile app. Scan the code below from your
                    phone to pair and start controlling the robot by tilting it.
                  </p>
                  <div className="inline-flex flex-col items-center gap-3 bg-input border border-border rounded-lg p-6">
                    <QrCode className="h-24 w-24 text-foreground" />
                    <span className="text-xs text-secondary">Waiting for device to connect…</span>
                  </div>
                </div>
              )}
            </div>
          </RoleGuard>
        </div>
      </div>
    </PageLayout>
  )
}

function ParamInput({ label, value, step, min, max, onChange }: { label: string; value: number; step: number; min: number; max: number; onChange: (v: number) => void }) {
  return (
    <div>
      <label className="block text-sm font-semibold mb-2">{label}</label>
      <input
        type="number"
        value={value}
        step={step}
        min={min}
        max={max}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full px-4 py-2 rounded-md bg-input border border-border text-foreground"
      />
    </div>
  )
}

function ArrowButton({ direction, label, onClick }: { direction: 'up' | 'down' | 'left' | 'right'; label: string; onClick: () => void }) {
  const rotation = { up: 0, right: 90, down: 180, left: 270 }[direction]
  return (
    <button onClick={onClick} className="group flex flex-col items-center justify-center gap-1 w-20 h-20 rounded-lg bg-input border border-border hover:bg-primary/10 hover:border-primary transition-colors">
      <svg width="22" height="22" viewBox="0 0 24 24" style={{ transform: `rotate(${rotation}deg)` }} className="fill-secondary group-hover:fill-primary transition-colors">
        <polygon points="12,3 21,19 3,19" />
      </svg>
      <span className="text-xs font-semibold text-secondary group-hover:text-primary transition-colors">{label}</span>
    </button>
  )
}

function RotateButton({ clockwise, label, onClick }: { clockwise: boolean; label: string; onClick: () => void }) {
  const Icon = clockwise ? RotateCw : RotateCcw
  return (
    <button onClick={onClick} className="group flex flex-col items-center justify-center gap-1 w-20 h-20 rounded-lg bg-input border border-border hover:bg-primary/10 hover:border-primary transition-colors">
      <Icon className="h-5 w-5 text-secondary group-hover:text-primary transition-colors" />
      <span className="text-xs font-semibold text-secondary group-hover:text-primary transition-colors">{label}</span>
    </button>
  )
}