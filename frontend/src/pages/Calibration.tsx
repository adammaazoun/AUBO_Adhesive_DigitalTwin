import { useState } from 'react'
import PageLayout from '../components/layout/PageLayout'
import { mockCalibrations } from '../lib/mockData'
import { StatusBadge } from '../components/common/StatusBadge'
import { Camera, Bot, Play } from 'lucide-react'
import RoleGuard from '../components/common/RoleGuard'

export default function Calibration() {
  const [calibrations, setCalibrations] = useState(mockCalibrations)

  const handleStart = (type: 'camera' | 'robot') => {
    setCalibrations((prev) =>
      prev.map((c) => (c.type === type ? { ...c, status: 'pending' } : c))
    )
    // will call a real /calibration/camera or /calibration/robot endpoint once built
  }

  return (
    <RoleGuard allowedRoles={['integrator']} fallback={<AccessDenied />}>
      <PageLayout title="Calibration">
        <div className="p-6 space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <CalibrationCard
              icon={<Camera className="h-5 w-5 text-primary" />}
              title="Camera Calibration"
              data={calibrations.find((c) => c.type === 'camera')}
              onStart={() => handleStart('camera')}
            />
            <CalibrationCard
              icon={<Bot className="h-5 w-5 text-primary" />}
              title="Robot Calibration"
              data={calibrations.find((c) => c.type === 'robot')}
              onStart={() => handleStart('robot')}
            />
          </div>
        </div>
      </PageLayout>
    </RoleGuard>
  )
}

function CalibrationCard({ icon, title, data, onStart }: any) {
  return (
    <div className="bg-muted border border-border rounded-lg p-6">
      <div className="flex items-center gap-2 mb-4">
        {icon}
        <h3 className="font-bold">{title}</h3>
      </div>

      <div className="bg-black rounded-md aspect-video flex items-center justify-center mb-4">
        <p className="text-white/40 text-sm">Preview placeholder</p>
      </div>

      <div className="flex items-center justify-between mb-4">
        <div className="text-sm text-secondary">
          {data?.lastRun
            ? `Last run: ${new Date(data.lastRun).toLocaleDateString()}`
            : 'Never run'}
          {data?.accuracy && <span className="ml-2">• {data.accuracy}% accuracy</span>}
        </div>
        <StatusBadge status={data?.status || 'never_run'} />
      </div>

      <button
        onClick={onStart}
        className="w-full flex items-center justify-center gap-2 px-4 py-2 rounded-md bg-primary hover:opacity-90 text-primary-foreground font-semibold transition-opacity"
      >
        <Play className="h-4 w-4" />
        Start Calibration
      </button>
    </div>
  )
}

function AccessDenied() {
  return (
    <div className="p-6 text-center text-secondary">
      This page is only available to Integrators.
    </div>
  )
}