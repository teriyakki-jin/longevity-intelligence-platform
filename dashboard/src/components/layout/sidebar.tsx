'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'

const NAV = [
  { href: '/', label: 'Biological Age', icon: '🧬' },
  { href: '/twin', label: 'Digital Twin', icon: '🔮' },
  { href: '/risk', label: 'Mortality Risk', icon: '☠️' },
  { href: '/coach', label: 'AI Coach', icon: '🤖' },
]

export function Sidebar() {
  const pathname = usePathname()

  return (
    <aside className="w-56 min-h-screen bg-[#161b22] border-r border-[#30363d] flex flex-col py-6 px-3 shrink-0">
      <div className="mb-8 px-3">
        <h1 className="text-[#58a6ff] font-bold text-base leading-tight">Longevity</h1>
        <p className="text-[#8b949e] text-xs mt-0.5">Intelligence Platform</p>
      </div>
      <nav className="flex flex-col gap-1">
        {NAV.map(({ href, label, icon }) => {
          const active = href === '/' ? pathname === '/' : pathname.startsWith(href)
          return (
            <Link
              key={href}
              href={href}
              className={`
                flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium
                transition-colors duration-150
                ${active
                  ? 'bg-[#21262d] text-[#e6edf3]'
                  : 'text-[#8b949e] hover:bg-[#21262d] hover:text-[#e6edf3]'
                }
              `}
            >
              <span>{icon}</span>
              {label}
            </Link>
          )
        })}
      </nav>
    </aside>
  )
}
