import { User, Piece, HistoryRecord, RobotState, AppSettings, CalibrationStatus } from './types'

export const mockPieces: Piece[] = [
  { id: 1, piece_code: 'P001', piece_name: 'Plastic Cover', material: 'ABS', dimensions: '180 X 120 X 20', adhesive_type: 'Epoxy', estimated_glue_time_seconds: 10, created_at: '2024-04-02' },
  { id: 2, piece_code: 'P002', piece_name: 'Metal Plate', material: 'Aluminum', dimensions: '200 X 150 X 15', adhesive_type: 'Cyanoacrylate', estimated_glue_time_seconds: 8, created_at: '2024-06-15' },
  { id: 3, piece_code: 'P003', piece_name: 'Electronic Housing', material: 'ABS', dimensions: '160 X 100 X 40', adhesive_type: 'Epoxy', estimated_glue_time_seconds: 12, created_at: '2025-10-06' },
  { id: 4, piece_code: 'P004', piece_name: 'Wooden Panel', material: 'MDF', dimensions: '250 X 180 X 18', adhesive_type: 'PVA', estimated_glue_time_seconds: 15, created_at: '2025-10-06' },
  { id: 5, piece_code: 'P005', piece_name: 'Glass Panel', material: 'Glass', dimensions: '300 X 200 X 6', adhesive_type: 'Silicone', estimated_glue_time_seconds: 20, created_at: '2025-10-06' },
  { id: 6, piece_code: 'P006', piece_name: 'Plastic Bracket', material: 'Polypropylene', dimensions: '90 X 60 X 25', adhesive_type: 'Epoxy', estimated_glue_time_seconds: 9, created_at: '2025-10-06' },
]

// Generate a realistic run history so charts have something to show
export const mockHistory: HistoryRecord[] = Array.from({ length: 45 }, (_, i) => {
  const piece = mockPieces[i % mockPieces.length]
  const daysAgo = 45 - i
  const date = new Date()
  date.setDate(date.getDate() - daysAgo)

  return {
    id: i + 1,
    run_date: date.toISOString(),
    status: Math.random() > 0.08 ? 'completed' : 'failed',
    piece,
  }
})

export const mockRobotState: RobotState = {
  online: true,
  mode: 'simulation',
  currentPieceCode: 'P001',
  finishedPieces: 120,
  productionProgress: 70,
  applicationRate: 320,
  parameters: {
    speed: 350,
    blend_radius: 350,
    acceleration: 350,
  },
  ros2Ip: '192.168.239.128:10000',
}

export const mockSettings: AppSettings = {
  id: 1,
  robot_pc_url: 'http://192.168.1.50:8001',
  updated_at: new Date().toISOString(),
}

export const mockUsers: User[] = [
  { id: 1, full_name: 'Morad Kallel', email: 'morad@tunibot.com', role: 'integrator', created_at: '2024-01-01' },
  { id: 2, full_name: 'Yesmine', email: 'yesmine@tunibot.com', role: 'admin', created_at: '2024-02-01' },
  { id: 3, full_name: 'Sam Kim', email: 'sam@tunibot.com', role: 'operator', created_at: '2024-03-01' },
  { id: 4, full_name: 'Jordan Smith', email: 'jordan@tunibot.com', role: 'visitor', created_at: '2024-04-01' },
]

export const mockCalibrations: CalibrationStatus[] = [
  { type: 'camera', lastRun: '2026-07-10T09:00:00Z', accuracy: 98.5, status: 'passed' },
  { type: 'robot', lastRun: '2026-07-08T14:00:00Z', accuracy: 99.1, status: 'passed' },
]