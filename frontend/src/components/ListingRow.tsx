import type { Listing } from '../types'

const money = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  maximumFractionDigits: 0,
})

export function ListingRow({ listing }: { listing: Listing }) {
  return (
    <tr aria-label={listing.address}>
      <td>
        <strong>{listing.address}</strong>
        <p className="listing-meta">
          {listing.city}, {listing.state} {listing.zip} ·{' '}
          <span className="source">
            {listing.source} / {listing.id}
          </span>{' '}
          · {listing.listedDate}
        </p>
        <p>{listing.description}</p>
      </td>
      <td>{money.format(listing.price)}</td>
      <td>{listing.bedrooms}</td>
      <td>{listing.relevanceScore.toFixed(2)}</td>
    </tr>
  )
}
