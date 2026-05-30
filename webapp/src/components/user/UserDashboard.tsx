import { useState } from 'react';
import { useAuthStore } from '../../store/useAuthStore';

export default function UserDashboard() {
  const { user, settings } = useAuthStore();
  const [activeTab, setActiveTab] = useState<'exchange' | 'history'>('exchange');

  return (
    <div className="min-h-screen p-4">
      <div className="max-w-md mx-auto space-y-4">
        <div className="bg-gray-900 rounded-2xl p-4">
          <h1 className="text-xl font-bold">Обмен USDT</h1>
          <p className="text-gray-400 text-sm">@{user?.username}</p>
        </div>

        <div className="bg-gray-900 rounded-2xl p-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-gray-400 text-xs">Баланс USDT</p>
              <p className="text-2xl font-bold">{user?.balance.toFixed(2)}</p>
            </div>
            <div>
              <p className="text-gray-400 text-xs">Баланс RUB</p>
              <p className="text-2xl font-bold">{user?.fiat_balance.toFixed(2)}</p>
            </div>
          </div>
        </div>

        {settings && (
          <div className="bg-gray-900 rounded-2xl p-4">
            <h2 className="font-bold mb-2">Курсы</h2>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-400">Покупка:</span>
                <span className="font-mono">{settings.buy_rate.toFixed(2)} ₽</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Продажа:</span>
                <span className="font-mono">{settings.sell_rate.toFixed(2)} ₽</span>
              </div>
            </div>
          </div>
        )}

        <div className="bg-gray-900 rounded-2xl p-4">
          <p className="text-center text-gray-400">Функционал в разработке</p>
        </div>
      </div>
    </div>
  );
}
