import React, { useState } from 'react';
import { AppShell } from '@/components/layout/AppShell';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Save, Bell, Lock, User } from 'lucide-react';

export function SettingsPage() {
  const [formData, setFormData] = useState({
    companyName: 'Minha Empresa',
    cnpj: 'XX.XXX.XXX/0001-XX',
    email: 'admin@empresa.com.br',
  });

  const [notifications, setNotifications] = useState({
    emailAlerts: true,
    weeklyReports: true,
    criticalOnly: false,
  });

  const [saved, setSaved] = useState(false);

  const handleInputChange = (field: string, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    setSaved(false);
  };

  const handleNotificationChange = (field: string, value: boolean) => {
    setNotifications(prev => ({ ...prev, [field]: value }));
    setSaved(false);
  };

  const handleSave = () => {
    // Aqui você chamaria a API para salvar as configurações
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  return (
    <AppShell title="Configurações">
      <div className="space-y-6 max-w-2xl">
        {/* Perfil */}
        <Card className="p-6">
          <div className="flex items-center gap-3 mb-6">
            <User className="w-5 h-5 text-blue-600" />
            <h3 className="font-semibold text-lg">Perfil da Empresa</h3>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-2">Nome da Empresa</label>
              <input
                type="text"
                value={formData.companyName}
                onChange={(e) => handleInputChange('companyName', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">CNPJ</label>
              <input
                type="text"
                value={formData.cnpj}
                onChange={(e) => handleInputChange('cnpj', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">Email Principal</label>
              <input
                type="email"
                value={formData.email}
                onChange={(e) => handleInputChange('email', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
        </Card>

        {/* Notificações */}
        <Card className="p-6">
          <div className="flex items-center gap-3 mb-6">
            <Bell className="w-5 h-5 text-orange-600" />
            <h3 className="font-semibold text-lg">Notificações</h3>
          </div>

          <div className="space-y-4">
            <label className="flex items-center p-3 border rounded hover:bg-gray-50 cursor-pointer">
              <input
                type="checkbox"
                checked={notifications.emailAlerts}
                onChange={(e) => handleNotificationChange('emailAlerts', e.target.checked)}
                className="w-4 h-4 text-blue-600 mr-3"
              />
              <div className="flex-1">
                <p className="font-medium text-sm">Alertas por Email</p>
                <p className="text-xs text-gray-500">Receba notificações de inconsistências encontradas</p>
              </div>
            </label>

            <label className="flex items-center p-3 border rounded hover:bg-gray-50 cursor-pointer">
              <input
                type="checkbox"
                checked={notifications.weeklyReports}
                onChange={(e) => handleNotificationChange('weeklyReports', e.target.checked)}
                className="w-4 h-4 text-blue-600 mr-3"
              />
              <div className="flex-1">
                <p className="font-medium text-sm">Relatórios Semanais</p>
                <p className="text-xs text-gray-500">Resumo semanal das atividades e achados</p>
              </div>
            </label>

            <label className="flex items-center p-3 border rounded hover:bg-gray-50 cursor-pointer">
              <input
                type="checkbox"
                checked={notifications.criticalOnly}
                onChange={(e) => handleNotificationChange('criticalOnly', e.target.checked)}
                className="w-4 h-4 text-red-600 mr-3"
              />
              <div className="flex-1">
                <p className="font-medium text-sm">Apenas Críticos</p>
                <p className="text-xs text-gray-500">Receba alertas apenas para inconsistências críticas</p>
              </div>
            </label>
          </div>
        </Card>

        {/* Segurança */}
        <Card className="p-6">
          <div className="flex items-center gap-3 mb-6">
            <Lock className="w-5 h-5 text-green-600" />
            <h3 className="font-semibold text-lg">Segurança</h3>
          </div>

          <div className="space-y-3">
            <Button variant="outline" className="w-full justify-start">
              Alterar Senha
            </Button>
            <Button variant="outline" className="w-full justify-start">
              Autenticação de Dois Fatores
            </Button>
          </div>
        </Card>

        {/* Salvar */}
        <div className="flex gap-3">
          <Button onClick={handleSave} className="flex items-center gap-2">
            <Save className="w-4 h-4" />
            Salvar Alterações
          </Button>
          {saved && (
            <div className="flex items-center text-green-600 text-sm">
              ✓ Configurações salvas com sucesso
            </div>
          )}
        </div>
      </div>
    </AppShell>
  );
}
