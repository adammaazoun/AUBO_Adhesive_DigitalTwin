export function StatusBadge({ status }: { status: string }) {
  const statusClasses: Record<string, string> = {
  success: 'bg-success/20 text-success',
  failed: 'bg-destructive/20 text-destructive',
  warning: 'bg-warning/20 text-warning',
  running: 'bg-primary/20 text-primary',
  idle: 'bg-secondary/20 text-secondary',
  error: 'bg-destructive/20 text-destructive',
  maintenance: 'bg-warning/20 text-warning',
  passed: 'bg-success/20 text-success',
  pending: 'bg-secondary/20 text-secondary',
  online: 'bg-success/20 text-success',
  offline: 'bg-destructive/20 text-destructive',
  completed: 'bg-success/20 text-success',
}

  return (
    <span
      className={`px-3 py-1 rounded-full text-xs font-semibold capitalize ${
        statusClasses[status] || 'bg-secondary/20 text-secondary'
      }`}
    >
      {status}
    </span>
  )
}

export function RoleBadge({ role }: { role: string }) {
  const roleClasses: Record<string, string> = {
    visitor: 'bg-secondary/20 text-secondary',
    operator: 'bg-primary/20 text-primary',
    admin: 'bg-warning/20 text-warning',
    integrator: 'bg-success/20 text-success',
  }

  return (
    <span
      className={`px-3 py-1 rounded-full text-xs font-semibold capitalize ${
        roleClasses[role] || 'bg-secondary/20 text-secondary'
      }`}
    >
      {role}
    </span>
  )
}
