import { type InputHTMLAttributes } from 'react'

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string
  unit?: string
  optional?: boolean
}

export function Input({ label, unit, optional, className = '', ...props }: InputProps) {
  return (
    <div className="flex flex-col gap-1">
      <label className="text-xs text-[#8b949e] font-medium">
        {label}
        {optional && <span className="ml-1 text-[#484f58]">(optional)</span>}
        {unit && <span className="ml-1 text-[#484f58]">{unit}</span>}
      </label>
      <input
        className={`
          bg-[#0d1117] border border-[#30363d] rounded-lg px-3 py-2
          text-sm text-[#e6edf3] placeholder-[#484f58]
          focus:outline-none focus:border-[#58a6ff] focus:ring-1 focus:ring-[#58a6ff]
          transition-colors duration-150 w-full
          ${className}
        `}
        {...props}
      />
    </div>
  )
}
