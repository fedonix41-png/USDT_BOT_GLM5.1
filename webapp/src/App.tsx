import { useEffect, useState } from 'react';
import { useAuthStore } from './store/useAuthStore';
import UserDashboard from './components/user/UserDashboard';
import AdminDashboard from './components/admin/AdminDashboard';
import LoadingSkeleton from './components/shared/LoadingSkeleton';

declare global {
  interface Window {
    Telegram?: {
      WebApp?: {
        ready: () => void;
        expand: () => void;
        initData: string;
        HapticFeedback?: {
          impactOccurred: (style: 'light' | 'medium' | 'heavy') => void;
          notificationOccurred: (type: 'error' | 'success' | 'warning') => void;
        };
      };
    };
  }
}

export default function App() {
  const { isAuthenticated, user, isLoading, setAuth, setLoading, setSettings } = useAuthStore();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (window.Telegram?.WebApp) {
      try {
        window.Telegram.WebApp.ready();
        window.Telegram.WebApp.expand();
      } catch (e) {
        console.warn('Telegram WebApp initialization error:', e);
      }
    }

    const initAuth = async () => {
      const tgInitData = window.Telegram?.WebApp?.initData;
      
      if (!tgInitData) {
        setError('Запустите приложение через Telegram');
        setLoading(false);
        return;
      }

      try {
        const response = await fetch('/api/v1/auth/telegram/verify', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ initData: tgInitData }),
        });

        if (response.ok) {
          const data = await response.json();
          setAuth(data.token, data.user);

          const settingsRes = await fetch('/api/v1/settings', {
            headers: { 'Authorization': `Bearer ${data.token}` },
          });
          
          if (settingsRes.ok) {
            const settings = await settingsRes.json();
            setSettings(settings);
          }
        } else {
          setError('Ошибка авторизации');
        }
      } catch (e) {
        console.error(e);
        setError('Сбой соединения с сервером');
      } finally {
        setLoading(false);
      }
    };

    initAuth();
  }, []);

  if (isLoading) {
    return <LoadingSkeleton />;
  }

  if (error || !isAuthenticated) {
    return (
      <div className="min-h-screen bg-gray-950 text-white flex items-center justify-center p-4">
        <div className="text-center space-y-4">
          <div className="text-6xl">⚠️</div>
          <h2 className="text-xl font-bold">Ошибка авторизации</h2>
          <p className="text-gray-400">{error || 'Не удалось войти в систему'}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      {user?.role === 'client' ? <UserDashboard /> : <AdminDashboard />}
    </div>
  );
}
