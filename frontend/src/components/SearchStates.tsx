export function LoadingState() {
  return <p role="status">Searching listings…</p>
}

export function ErrorState({
  message,
  onRetry,
}: {
  message: string
  onRetry: () => void
}) {
  return (
    <div role="alert">
      <p>We couldn’t load listings. {message}</p>
      <button className="primary" type="button" onClick={onRetry}>
        Try again
      </button>
    </div>
  )
}

export function EmptyState({ onReset }: { onReset: () => void }) {
  return (
    <div>
      <p>No listings match your search</p>
      <p className="muted">
        Try a different city, price range, or description keyword.
      </p>
      <button className="primary" type="button" onClick={onReset}>
        Clear filters
      </button>
    </div>
  )
}
