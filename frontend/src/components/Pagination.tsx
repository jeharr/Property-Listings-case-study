interface PaginationProps {
  page: number
  pageSize: number
  total: number
  totalPages: number
  onPageChange: (page: number) => void
}

export function Pagination({
  page,
  pageSize,
  total,
  totalPages,
  onPageChange,
}: PaginationProps) {
  return (
    <div className="pagination-row">
      <p>
        Showing {(page - 1) * pageSize + 1}–{Math.min(page * pageSize, total)}{' '}
        of {total}
      </p>
      <nav className="actions" aria-label="Results pages">
        <button
          type="button"
          disabled={page <= 1}
          onClick={() => onPageChange(page - 1)}
        >
          Previous page
        </button>
        {Array.from({ length: totalPages }, (_, index) => index + 1).map(
          (pageNumber) => (
            <button
              type="button"
              key={pageNumber}
              aria-label={`Go to page ${pageNumber}`}
              aria-current={pageNumber === page ? 'page' : undefined}
              onClick={() => onPageChange(pageNumber)}
            >
              {pageNumber}
            </button>
          ),
        )}
        <button
          type="button"
          disabled={page >= totalPages}
          onClick={() => onPageChange(page + 1)}
        >
          Next page
        </button>
      </nav>
    </div>
  )
}
