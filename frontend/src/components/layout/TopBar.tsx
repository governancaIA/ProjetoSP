import { ReactNode } from 'react'

interface TopBarProps {
  title: string
  children?: ReactNode
}

export function TopBar({ title, children }: TopBarProps) {
  return (
    <div className="border-b bg-white px-8 py-4 flex items-center justify-between">
      <h2 className="text-2xl font-bold text-slate-900">{title}</h2>
      {children}
    </div>
  )
}
