import { Link, useLocation, useNavigate } from 'react-router-dom'
import { BarChart3, FileText, LogOut, PieChart, Settings } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useAuth } from '@/contexts/AuthContext'
import { Button } from '@/components/ui/button'

export function Sidebar() {
  const location = useLocation()
  const navigate = useNavigate()
  const { user, logout, isLoading } = useAuth()

  const links = [
    { href: '/', label: 'Dashboard', icon: BarChart3 },
    { href: '/documents', label: 'Documentos', icon: FileText },
    { href: '/reports', label: 'Relatórios', icon: PieChart },
    { href: '/settings', label: 'Configurações', icon: Settings },
  ]

  const handleLogout = async () => {
    try {
      await logout()
      navigate('/login')
    } catch (error) {
      console.error('Logout error:', error)
      // Mesmo com erro, redirecionar para login
      navigate('/login')
    }
  }

  return (
    <div className="w-64 border-r bg-white flex flex-col h-screen">
      <div className="p-6">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-brand-600">FiscalAI</h1>
          <p className="text-xs text-slate-500">Auditoria Fiscal Inteligente</p>
        </div>

        <nav className="space-y-2">
          {links.map((link) => {
            const Icon = link.icon
            const isActive = location.pathname === link.href
            return (
              <Link
                key={link.href}
                to={link.href}
                className={cn(
                  'flex items-center gap-3 rounded-lg px-3 py-2 transition-colors',
                  isActive
                    ? 'bg-brand-50 text-brand-600 font-medium'
                    : 'text-slate-600 hover:bg-slate-50'
                )}
              >
                <Icon size={20} />
                {link.label}
              </Link>
            )
          })}
        </nav>
      </div>

      {/* User section - fixed at bottom */}
      <div className="border-t p-6 mt-auto">
        <div className="mb-4">
          <p className="text-xs text-slate-500 uppercase tracking-wide">Usuário</p>
          <p className="text-sm font-medium text-slate-900 truncate">{user?.email}</p>
          <p className="text-xs text-slate-500">{user?.full_name || '–'}</p>
        </div>
        <Button
          onClick={handleLogout}
          disabled={isLoading}
          variant="outline"
          size="sm"
          className="w-full"
        >
          <LogOut size={16} className="mr-2" />
          Sair
        </Button>
      </div>
    </div>
  )
}
