export function LoadingSpinner({ size = 20 }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      className="animate-spin text-brand-400"
    >
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
      />
    </svg>
  );
}

export function PageLoader({ message = "Loading…" }) {
  return (
    <div className="flex flex-col items-center justify-center h-64 gap-4">
      <LoadingSpinner size={32} />
      <p className="text-sm text-gray-500">{message}</p>
    </div>
  );
}

export function ErrorState({ error }) {
  return (
    <div className="flex flex-col items-center justify-center h-64 gap-3 text-center px-8">
      <div className="w-12 h-12 rounded-full bg-red-500/10 flex items-center justify-center">
        <span className="text-red-400 text-xl">!</span>
      </div>
      <p className="text-sm font-medium text-red-400">Failed to load data</p>
      <p className="text-xs text-gray-500 max-w-sm">
        {error?.message || "Make sure the simulation has been run and the API is running on port 8000."}
      </p>
    </div>
  );
}
