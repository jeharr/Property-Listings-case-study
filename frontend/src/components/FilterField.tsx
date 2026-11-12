import type { HTMLAttributes } from 'react'
import type { FilterForm } from '../types'

export interface FilterFieldDefinition {
  name: keyof FilterForm
  label: string
  placeholder: string
  inputMode?: HTMLAttributes<HTMLInputElement>['inputMode']
  hint?: string
}

interface FilterFieldProps extends FilterFieldDefinition {
  value: string
  error?: string
  onChange: (name: keyof FilterForm, value: string) => void
}

export function FilterField({
  name,
  label,
  placeholder,
  inputMode,
  hint,
  value,
  error,
  onChange,
}: FilterFieldProps) {
  return (
    <div>
      <label htmlFor={name}>{label}</label>
      <input
        id={name}
        name={name}
        type="text"
        inputMode={inputMode}
        placeholder={placeholder}
        value={value}
        onChange={(event) => onChange(name, event.target.value)}
        aria-invalid={!!error}
        aria-describedby={
          error ? `${name}-error` : hint ? `${name}-hint` : undefined
        }
      />
      {error && (
        <p className="error" id={`${name}-error`}>
          {error}
        </p>
      )}
      {hint && !error && (
        <p className="hint" id={`${name}-hint`}>
          {hint}
        </p>
      )}
    </div>
  )
}
