import React, { createContext, useContext, useState, ReactNode, useEffect } from 'react'
import { User, UserRole, PermissionSet } from '../lib/types'
import api from '../lib/api'

interface AuthContextType {
  currentUser: User | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  getPermissions: (role: UserRole) => PermissionSet
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

const ROLE_PERMISSIONS: Record<UserRole, PermissionSet> = {
  visitor: {
    canViewDashboard: true, canControlRobot: false, canImportPieces: false,
    canEditSettings: false, canManageUsers: false, canViewHistory: false,
    canRunTests: false, canEditCalibration: false,
  },
  operator: {
    canViewDashboard: true, canControlRobot: true, canImportPieces: true,
    canEditSettings: false, canManageUsers: false, canViewHistory: true,
    canRunTests: false, canEditCalibration: false,
  },
  admin: {
    canViewDashboard: true, canControlRobot: true, canImportPieces: true,
    canEditSettings: true, canManageUsers: true, canViewHistory: true,
    canRunTests: true, canEditCalibration: true,
  },
  integrator: {
    canViewDashboard: true, canControlRobot: true, canImportPieces: true,
    canEditSettings: true, canManageUsers: true, canViewHistory: true,
    canRunTests: true, canEditCalibration: true,
  },
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [currentUser, setCurrentUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  // On app load: if a token exists, try to restore the session
  useEffect(() => {
    const token = localStorage.getItem('access_token')
    if (!token) {
      setIsLoading(false)
      return
    }

    api
      .get('/users/me')
      .then((res) => setCurrentUser(res.data))
      .catch(() => {
        localStorage.removeItem('access_token') // stale/expired token
        setCurrentUser(null)
      })
      .finally(() => setIsLoading(false))
  }, [])

  const login = async (email: string, password: string) => {
    // FastAPI's OAuth2PasswordRequestForm expects form-encoded data, not JSON
    const form = new URLSearchParams()
    form.append('username', email)
    form.append('password', password)

    const tokenRes = await api.post('/users/login', form, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    })

    localStorage.setItem('access_token', tokenRes.data.access_token)

    const meRes = await api.get('/users/me')
    setCurrentUser(meRes.data)
  }

  const logout = () => {
    setCurrentUser(null)
    localStorage.removeItem('access_token')
  }

  const getPermissions = (role: UserRole): PermissionSet => ROLE_PERMISSIONS[role]

  return (
    <AuthContext.Provider
      value={{
        currentUser,
        isAuthenticated: !!currentUser,
        isLoading,
        login,
        logout,
        getPermissions,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}