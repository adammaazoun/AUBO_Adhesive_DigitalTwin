import { ReactNode } from 'react'
import Sidebar from './Sidebar'
import TopBar from './TopBar'

interface PageLayoutProps {
  children: ReactNode
  title: string
  robotOnline?: boolean
  recentAlerts?: number
}

export default function PageLayout({
  children,
  title,
  robotOnline = true,
  recentAlerts = 0,
}: PageLayoutProps) {
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col lg:ml-56">
        <TopBar title={title} robotOnline={robotOnline} recentAlerts={recentAlerts} />
        <main className="flex-1 overflow-y-auto">{children}</main>
      </div>
    </div>
  )
}