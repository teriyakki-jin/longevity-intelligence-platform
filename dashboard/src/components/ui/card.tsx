import { type ReactNode } from 'react'

interface CardProps {
  children: ReactNode
  className?: string
  title?: string
}

export function Card({ children, className = '', title }: CardProps) {
  return (
    <div className={`bg-[#161b22] border border-[#30363d] rounded-xl p-5 ${className}`}>
      {title && <h3 className="text-[#e6edf3] font-semibold text-sm mb-4">{title}</h3>}
      {children}
    </div>
  )
}
