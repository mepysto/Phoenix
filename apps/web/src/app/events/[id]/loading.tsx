export default function EventDetailLoading() {
  return (
    <div className="flex min-h-screen flex-col bg-gray-950">
      <div className="h-16 border-b border-gray-800 bg-gray-900/50 backdrop-blur" />

      <main className="flex-1 px-4 py-6 md:px-6 lg:px-8">
        <div className="mx-auto max-w-4xl">
          <div className="mb-6 h-5 w-32 animate-pulse rounded bg-gray-800" />

          <div className="grid gap-6 lg:grid-cols-3">
            <div className="lg:col-span-2 space-y-6">
              <div className="rounded-lg border border-gray-800 bg-gray-900 p-6">
                <div className="flex items-start gap-4">
                  <div className="h-14 w-14 animate-pulse rounded-xl bg-gray-800" />
                  <div className="flex-1">
                    <div className="mb-2 flex gap-2">
                      <div className="h-6 w-20 animate-pulse rounded-full bg-gray-800" />
                      <div className="h-6 w-16 animate-pulse rounded-full bg-gray-800" />
                    </div>
                    <div className="h-8 w-3/4 animate-pulse rounded bg-gray-800" />
                  </div>
                </div>
                <div className="mt-4 h-16 w-full animate-pulse rounded bg-gray-800" />
              </div>

              <div className="rounded-lg border border-gray-800 bg-gray-900 overflow-hidden">
                <div className="h-64 lg:h-80 animate-pulse bg-gray-800" />
              </div>
            </div>

            <div className="space-y-6">
              <div className="rounded-lg border border-gray-800 bg-gray-900 p-6">
                <div className="h-6 w-32 animate-pulse rounded bg-gray-800 mb-4" />
                <div className="space-y-4">
                  {Array.from({ length: 4 }).map((_, i) => (
                    <div
                      key={i}
                      className="flex items-start gap-3 py-3 border-b border-gray-800 last:border-0"
                    >
                      <div className="h-4 w-4 animate-pulse rounded bg-gray-800" />
                      <div className="flex-1">
                        <div className="h-3 w-16 animate-pulse rounded bg-gray-800 mb-1" />
                        <div className="h-4 w-24 animate-pulse rounded bg-gray-800" />
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="rounded-lg border border-gray-800 bg-gray-900 p-6">
                <div className="h-6 w-24 animate-pulse rounded bg-gray-800 mb-4" />
                <div className="h-10 w-full animate-pulse rounded-lg bg-gray-800" />
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
