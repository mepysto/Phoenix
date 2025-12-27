export default function Loading() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-950">
      <div className="text-center">
        <div className="relative mb-6">
          <div className="h-16 w-16 animate-spin rounded-full border-4 border-primary-500/30 border-t-primary-500 mx-auto" />
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="h-8 w-8 rounded-full bg-primary-500/20" />
          </div>
        </div>
        <h2 className="text-xl font-semibold text-white mb-2">
          Loading Phoenix
        </h2>
        <p className="text-sm text-gray-400">
          Preparing global disaster data...
        </p>
      </div>
    </div>
  );
}
