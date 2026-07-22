export type UserRole = 'visitor' | 'operator' | 'admin' | 'integrator'

export interface User {
  id: number
  full_name: string
  email: string
  role: UserRole
  created_at: string
}

export interface Piece {
  id: number
  piece_code: string
  piece_name: string
  material: string
  dimensions: string | null
  adhesive_type: string | null
  estimated_glue_time_seconds: number | null
  created_at: string
}

export interface HistoryRecord {
  id: number
  run_date: string
  status: 'completed' | 'failed'
  piece: Piece
}

export interface RobotParameters {
  speed: number
  blend_radius: number
  acceleration: number
}

export type RobotMode = 'simulation' | 'real_world'

// There is only ONE robot in this system — not a fleet.
export interface RobotState {
  online: boolean
  mode: RobotMode
  currentPieceCode: string | null
  finishedPieces: number
  productionProgress: number // 0-100
  applicationRate: number // pieces per hour
  parameters: RobotParameters
  ros2Ip: string
}

export interface AppSettings {
  id: number
  robot_pc_url: string | null
  updated_at: string
}

export interface PermissionSet {
  canViewDashboard: boolean
  canControlRobot: boolean
  canImportPieces: boolean
  canEditSettings: boolean
  canManageUsers: boolean
  canViewHistory: boolean
  canRunTests: boolean
  canEditCalibration: boolean
}

// Calibration isn't in the backend yet — mock-only until that endpoint exists
export interface CalibrationStatus {
  type: 'camera' | 'robot'
  lastRun: string | null
  accuracy: number | null
  status: 'passed' | 'pending' | 'failed' | 'never_run'
}