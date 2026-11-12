import type { RefObject, SubmitEventHandler } from 'react'
import type { FieldErrors, FilterForm } from '../types'
import { FilterField } from './FilterField'
import type { FilterFieldDefinition } from './FilterField'

const fields: FilterFieldDefinition[] = [
  { name: 'city', label: 'City', placeholder: 'e.g. Springfield' },
  {
    name: 'minPrice',
    label: 'Min. price',
    placeholder: 'No minimum',
    inputMode: 'decimal',
  },
  {
    name: 'maxPrice',
    label: 'Max. price',
    placeholder: 'No maximum',
    inputMode: 'decimal',
  },
  {
    name: 'minBedrooms',
    label: 'Minimum bedrooms',
    placeholder: 'Any',
    inputMode: 'numeric',
  },
  {
    name: 'keyword',
    label: 'Description keyword',
    placeholder: 'e.g. Updated kitchen',
  },
  {
    name: 'targetBudget',
    label: 'Target budget',
    placeholder: 'e.g. 500000',
    inputMode: 'decimal',
  },
]

interface SearchFiltersProps {
  form: FilterForm
  errors: FieldErrors
  formRef: RefObject<HTMLFormElement | null>
  onChange: (name: keyof FilterForm, value: string) => void
  onSubmit: SubmitEventHandler<HTMLFormElement>
  onReset: () => void
}

export function SearchFilters({
  form,
  errors,
  formRef,
  onChange,
  onSubmit,
  onReset,
}: SearchFiltersProps) {
  return (
    <form
      ref={formRef}
      onSubmit={onSubmit}
      noValidate
      aria-labelledby="filters-title"
    >
      <h2 id="filters-title">Search filters</h2>
      <div className="filters">
        {fields.map((field) => (
          <FilterField
            key={field.name}
            {...field}
            value={form[field.name]}
            error={errors[field.name]}
            onChange={onChange}
          />
        ))}
      </div>
      {Object.values(errors).some(Boolean) && (
        <p className="error" role="alert">
          Please check the highlighted fields.
        </p>
      )}
      <div className="actions">
        <button className="primary" type="submit">
          Search listings
        </button>
        <button type="button" onClick={onReset}>
          Reset filters
        </button>
      </div>
    </form>
  )
}
