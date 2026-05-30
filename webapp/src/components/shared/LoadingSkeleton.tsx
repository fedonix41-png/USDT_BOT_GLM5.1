export default function LoadingSkeleton() {
  return (
    <div className="min-h-screen bg-[#0B0E14] text-white p-4 flex flex-col justify-between font-sans">
      {/* Header Skeleton */}
      <div className="flex items-center justify-between border-b border-gray-800/40 pb-4 mb-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-[#161B26] animate-pulse" />
          <div>
            <div className="w-24 h-4 bg-[#161B26] rounded animate-pulse mb-2" />
            <div className="w-16 h-3 bg-[#161B26] rounded animate-pulse" />
          </div>
        </div>
        <div className="w-20 h-6 bg-[#161B26] rounded-full animate-pulse" />
      </div>

      {/* Balance Card Skeleton */}
      <div className="bg-[#161B26] border border-gray-800/50 p-6 rounded-2xl mb-6 flex flex-col items-center justify-center relative overflow-hidden">
        <div className="w-32 h-3 bg-gray-700/30 rounded animate-pulse mb-3" />
        <div className="w-48 h-8 bg-gray-700/40 rounded animate-pulse mb-6" />
        <div className="grid grid-cols-2 gap-4 w-full">
          <div className="h-12 bg-gray-800/80 rounded-xl animate-pulse" />
          <div className="h-12 bg-gray-800/80 rounded-xl animate-pulse" />
        </div>
      </div>

      {/* Tabs / Actions Skeleton */}
      <div className="flex-1 space-y-4">
        <div className="w-24 h-4 bg-[#161B26] rounded animate-pulse" />
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="flex justify-between items-center bg-[#161B26] border border-gray-800/40 p-3.5 rounded-xl">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-gray-800/80 animate-pulse" />
                <div>
                  <div className="w-20 h-3.5 bg-gray-800/80 rounded animate-pulse mb-1.5" />
                  <div className="w-12 h-3 bg-gray-800/80 rounded animate-pulse" />
                </div>
              </div>
              <div className="w-16 h-4 bg-gray-800/80 rounded animate-pulse" />
            </div>
          ))}
        </div>
      </div>

      {/* Navbar Skeleton */}
      <div className="mt-6 bg-[#161B26] border border-gray-800/60 rounded-2xl p-2.5 flex justify-around">
        {[1, 2, 3].map((i) => (
          <div key={i} className="w-12 h-12 rounded-xl bg-gray-800/60 animate-pulse" />
        ))}
      </div>
    </div>
  );
}
