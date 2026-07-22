import { useEffect, useState } from 'react'
import PageLayout from '../components/layout/PageLayout'
import api from '../lib/api'
import { User, UserRole } from '../lib/types'
import { RoleBadge } from '../components/common/StatusBadge'
import { Mail, Trash2, UserPlus } from 'lucide-react'
import RoleGuard from '../components/common/RoleGuard'

const roleOptions: UserRole[] = ['visitor', 'operator', 'admin', 'integrator']

export default function Users() {
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [showDialog, setShowDialog] = useState(false)

  const load = () => {
    api.get('/users/').then((res) => setUsers(res.data)).finally(() => setLoading(false))
  }
  useEffect(load, [])

  const handleDelete = async (id: number) => {
    if (!confirm('Remove this user?')) return
    await api.delete(`/users/${id}`)
    load()
  }

  const handleRoleChange = async (id: number, role: UserRole) => {
    await api.put(`/users/${id}/role`, { role })
    load()
  }

  const handleInvite = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const form = new FormData(e.currentTarget)
    await api.post('/users/signup', {
      full_name: form.get('full_name'),
      email: form.get('email'),
      password: form.get('password'),
      role: form.get('role'),
    })
    setShowDialog(false)
    load()
  }

  if (loading) return <PageLayout title="Users"><p className="p-6 text-secondary">Loading...</p></PageLayout>

  return (
    <RoleGuard allowedRoles={['admin', 'integrator']}>
      <PageLayout title="Users">
        <div className="p-6 space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-2xl font-bold">Users</h2>
            <button onClick={() => setShowDialog(true)} className="flex items-center gap-2 px-4 py-2 rounded-md bg-primary hover:opacity-90 text-primary-foreground font-semibold transition-opacity">
              <UserPlus className="h-4 w-4" />
              Invite User
            </button>
          </div>

          <div className="bg-muted border border-border rounded-lg overflow-hidden">
            <table className="w-full">
              <thead className="bg-input border-b border-border">
                <tr>
                  <th className="px-6 py-4 text-left font-semibold">Name</th>
                  <th className="px-6 py-4 text-left font-semibold">Email</th>
                  <th className="px-6 py-4 text-left font-semibold">Role</th>
                  <th className="px-6 py-4 text-left font-semibold">Created</th>
                  <th className="px-6 py-4 text-right font-semibold">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {users.map((user) => (
                  <tr key={user.id} className="hover:bg-input transition-colors">
                    <td className="px-6 py-4 font-semibold">{user.full_name}</td>
                    <td className="px-6 py-4 text-secondary flex items-center gap-2">
                      <Mail className="h-4 w-4" />
                      {user.email}
                    </td>
                    <td className="px-6 py-4">
                      <select value={user.role} onChange={(e) => handleRoleChange(user.id, e.target.value as UserRole)} className="px-3 py-1.5 rounded-md bg-input border border-border text-sm capitalize">
                        {roleOptions.map((role) => <option key={role} value={role}>{role}</option>)}
                      </select>
                    </td>
                    <td className="px-6 py-4 text-secondary">{new Date(user.created_at).toLocaleDateString()}</td>
                    <td className="px-6 py-4 text-right">
                      <button onClick={() => handleDelete(user.id)} className="p-2 hover:bg-border rounded-md transition-colors">
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {showDialog && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-muted border border-border rounded-lg p-6 max-w-md w-full mx-4">
              <h2 className="text-xl font-bold mb-4">Invite New User</h2>
              <form onSubmit={handleInvite} className="space-y-3">
                <input name="full_name" placeholder="Full Name" required className="w-full px-4 py-2 rounded-md bg-input border border-border text-foreground" />
                <input name="email" type="email" placeholder="user@tunibot.com" required className="w-full px-4 py-2 rounded-md bg-input border border-border text-foreground" />
                <input name="password" type="password" placeholder="Temporary password" required className="w-full px-4 py-2 rounded-md bg-input border border-border text-foreground" />
                <select name="role" defaultValue="operator" className="w-full px-4 py-2 rounded-md bg-input border border-border text-foreground">
                  {roleOptions.map((role) => <option key={role} value={role} className="capitalize">{role}</option>)}
                </select>
                <button type="submit" className="w-full px-4 py-2 rounded-md bg-primary hover:opacity-90 text-primary-foreground font-semibold transition-opacity">
                  Send Invite
                </button>
                <button type="button" onClick={() => setShowDialog(false)} className="w-full px-4 py-2 rounded-md border border-border hover:bg-input font-semibold transition-colors">
                  Cancel
                </button>
              </form>
            </div>
          </div>
        )}
      </PageLayout>
    </RoleGuard>
  )
}