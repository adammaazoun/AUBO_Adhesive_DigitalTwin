import { useState } from 'react'
import { useAuth } from '../../context/AuthContext'
import { Link, useLocation } from 'react-router-dom'
import {
  LayoutDashboard,
  Cpu,
  Package2,
  History,
  Users,
  Wrench,
  Settings,
  TestTube2,
  LogOut,
  Menu,
  X,
} from 'lucide-react'
import BrandLogo from '../common/BrandLogo'

export default function Sidebar() {
  const { currentUser, logout, getPermissions } = useAuth()
  const location = useLocation()
  const [isOpen, setIsOpen] = useState(true)
  const permissions = currentUser ? getPermissions(currentUser.role) : null

  if (!currentUser) return null

  const navItems = [
    {
      label: 'Dashboard',
      href: '/dashboard',
      icon: LayoutDashboard,
      show: permissions?.canViewDashboard,
    },
    {
      label: 'Robot View',
      href: '/robot-view',
      icon: Cpu,
      show: permissions?.canViewDashboard,
    },
    {
      label: 'Pieces',
      href: '/pieces',
      icon: Package2,
      show: permissions?.canImportPieces,
    },
    {
      label: 'History',
      href: '/history',
      icon: History,
      show: permissions?.canViewHistory,
    },
    {
      label: 'Users',
      href: '/users',
      icon: Users,
      show: permissions?.canManageUsers,
    },
    {
      label: 'Calibration',
      href: '/calibration',
      icon: Wrench,
      show: permissions?.canEditCalibration,
    },
    {
      label: 'Settings',
      href: '/settings',
      icon: Settings,
      show: permissions?.canEditSettings,
    },
    {
      label: 'Test Results',
      href: '/test-results',
      icon: TestTube2,
      show: permissions?.canRunTests,
    },
  ]

  const visibleItems = navItems.filter((item) => item.show)

  return (
    <>
      {/* Mobile toggle */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="fixed left-4 top-4 z-40 lg:hidden"
      >
        {isOpen ? (
          <X className="h-6 w-6" />
        ) : (
          <Menu className="h-6 w-6" />
        )}
      </button>

      {/* Sidebar */}
      <aside
        className={`fixed left-0 top-0 h-screen w-56 bg-muted border-r border-border transition-all duration-300 ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        } lg:translate-x-0 z-30`}
      >
        {/* Logo */}
        <div className="border-b border-border p-6 flex justify-center">
          <BrandLogo imageClassName="h-auto w-auto max-w-full" />
          
        </div>

        {/* User info */}
        <div className="border-b border-border p-4">
          <div className="text-sm font-semibold">{currentUser.name}</div>
          <div className="text-xs text-secondary capitalize">{currentUser.role}</div>
          <div className="text-xs text-secondary mt-1">{currentUser.department}</div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto p-4 space-y-1">
          {visibleItems.map((item) => {
            const Icon = item.icon
            const isActive = location.pathname === item.href
            return (
              <Link
                key={item.href}
                to={item.href}
                className={`flex items-center gap-3 px-4 py-3 rounded-md text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-primary/10 text-primary font-semibold'
                    : 'text-secondary hover:bg-input hover:text-foreground'
                }`}
                onClick={() => setIsOpen(false)}
              >
                <Icon className="h-5 w-5" />
                <span>{item.label}</span>
              </Link>
            )
          })}
        </nav>

        {/* Logout button */}
        <div className="border-t border-border p-4">
          <button
            onClick={() => {
              logout()
              setIsOpen(false)
            }}
            className="w-full flex items-center gap-3 px-4 py-3 rounded-md text-sm font-medium text-destructive hover:bg-input transition-colors"
          >
            <LogOut className="h-5 w-5" />
            <span>Logout</span>
          </button>
        </div>
      </aside>

      {/* Mobile overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-20 lg:hidden"
          onClick={() => setIsOpen(false)}
        />
      )}
    </>
  )
}
