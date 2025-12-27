export default function EventsLoading() {
  return (
    <div className="flex min-h-screen flex-col bg-gray-950">
      <div className="h-16 border-b border-gray-800 bg-gray-900/50 backdrop-blur" />

      <main className="flex-1 px-4 py-6 md:px-6 lg:px-8">
        <div className="mx-auto max-w-6xl">
          <div className="mb-6 flex items-center justify-between">
            <div>
              <div className="h-8 w-48 animate-pulse rounded bg-gray-800" />
              <div className="mt-2 h-4 w-32 animate-pulse rounded bg-gray-800" />
            </div>
            <div className="h-10 w-28 animate-pulse rounded-lg bg-gray-800" />
          </div>

          <div className="mb-6 flex flex-wrap gap-2">
            {Array.from({ length: 6 }).map((_, i) => (
              <div
                key={i}
                className="h-8 w-24 animate-pulse rounded-full bg-gray-800"
              />
            ))}
          </div>

          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <div
                key={i}
                className="rounded-lg border border-gray-800 bg-gray-900 p-4"
              >
                <div className="flex items-start gap-3">
                  <div className="h-10 w-10 animate-pulse rounded-lg bg-gray-800" />
                  <div className="flex-1">
                    <div className="h-5 w-3/4 animate-pulse rounded bg-gray-800" />
                    <div className="mt-2 h-4 w-full animate-pulse rounded bg-gray-800" />
                    <div className="mt-1 h-4 w-2/3 animate-pulse rounded bg-gray-800" />
                  </div>
                </div>
                <div className="mt-4 flex gap-4">
                  <div className="h-4 w-20 animate-pulse rounded bg-gray-800" />
                  <div className="h-4 w-24 animate-pulse rounded bg-gray-800" />
                </div>
                <div className="mt-3 flex gap-2">
                  <div className="h-6 w-16 animate-pulse rounded-full bg-gray-800" />
                  <div className="h-6 w-14 animate-pulse rounded-full bg-gray-800" />
                </div>
              </div>
            ))}
          </div>
        </div>
      </main>
    </div>
  );
}
