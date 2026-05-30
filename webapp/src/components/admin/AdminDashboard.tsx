import { useAuthStore } from '../../store/useAuthStore';

export default function AdminDashboard() {
  const { user } = useAuthStore();

  return (
    <div className="min-h-screen p-4">
      <div className="max-w-4xl mx-auto space-y-4">
        <div className="bg-gray-900 rounded-2xl p-4">
          <h1 className="text-xl font-bold">Панель {user?.role}</h1>
          <p className="text-gray-400 text-sm">@{user?.username}</p>
        </div>

        <div className="bg-gray-900 rounded-2xl p-4">
          <p className="text-center text-gray-400">Админ-панель в разработке</p>
        </div>
      </div>
    </div>
  );
}
