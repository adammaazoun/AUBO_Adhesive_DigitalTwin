import { useAuth } from '../../context/AuthContext'
import { AlertTriangle } from 'lucide-react'

interface TopBarProps {
  title: string
  robotOnline?: boolean
  recentAlerts?: number
}

export default function TopBar({ title, robotOnline = true, recentAlerts = 0 }: TopBarProps) {
  const { currentUser, getPermissions } = useAuth()
  const permissions = currentUser ? getPermissions(currentUser.role) : null

  const handleEmergencyStop = () => {
    console.log('[v0] Emergency stop triggered')
    alert('EMERGENCY STOP: Robot halted!')
  }

  return (
    <div className="h-16 bg-muted border-b border-border px-6 flex items-center justify-between">
      <h1 className="text-xl font-bold">{title}</h1>

      <div className="flex items-center gap-6">
        <div className="flex items-center gap-4 text-sm">
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${robotOnline ? 'bg-success' : 'bg-destructive'}`} />
            <span className="text-secondary">{robotOnline ? 'Robot Online' : 'Robot Offline'}</span>
          </div>
          {recentAlerts > 0 && (
            <div className="flex items-center gap-2 text-warning">
              <AlertTriangle className="h-4 w-4" />
              <span>{recentAlerts} Alerts</span>
            </div>
          )}
        </div>

        {permissions?.canControlRobot && (
          <button
            onClick={handleEmergencyStop}
            className="px-4 py-2 bg-destructive hover:bg-red-600 text-foreground font-semibold rounded-md transition-colors"
          >
            STOP
          </button>
        )}

        <div className="h-8 w-px bg-border" />
        <div className="text-xs text-secondary">{new Date().toLocaleTimeString()}</div>
      </div>
    </div>
  )
}