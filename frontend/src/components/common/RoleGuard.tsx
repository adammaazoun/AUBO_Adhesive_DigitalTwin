import { ReactNode } from 'react'
import { useAuth } from '../../context/AuthContext'
import { UserRole } from '../../lib/types'

interface RoleGuardProps {
  children: ReactNode
  allowedRoles: UserRole[]
  fallback?: ReactNode
}

export default function RoleGuard({
  children,
  allowedRoles,
  fallback = null,
}: RoleGuardProps) {
  const { currentUser } = useAuth()

  if (!currentUser) return fallback

  if (allowedRoles.includes(currentUser.role)) {
    return children
  }

  return fallback
}
