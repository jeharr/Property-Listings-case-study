import type { Listing } from '../types'
import { ListingRow } from './ListingRow'

interface ListingsTableProps {
  listings: Listing[]
}

export function ListingsTable({ listings }: ListingsTableProps) {
  return (
    <table aria-label="Listing results" className="listings-table">
      <thead>
        <tr>
          <th scope="col">Listing</th>
          <th scope="col">Price</th>
          <th scope="col">Beds</th>
          <th scope="col">Relevance</th>
        </tr>
      </thead>
      <tbody>
        {listings.map((listing) => (
          <ListingRow
            key={JSON.stringify([listing.source, listing.id])}
            listing={listing}
          />
        ))}
      </tbody>
    </table>
  )
}
