'use client'

interface SliderProps {
  label: string
  value: number
  min: number
  max: number
  step?: number
  unit?: string
  onChange: (value: number) => void
}

export function Slider({ label, value, min, max, step = 1, unit, onChange }: SliderProps) {
  const pct = ((value - min) / (max - min)) * 100

  return (
    <div className="flex flex-col gap-2">
      <div className="flex justify-between items-center">
        <span className="text-xs text-[#8b949e] font-medium">{label}</span>
        <span className="text-sm text-[#58a6ff] font-mono font-semibold">
          {value}{unit}
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={e => onChange(Number(e.target.value))}
        className="w-full h-1.5 rounded-full appearance-none cursor-pointer"
        style={{
          background: `linear-gradient(to right, #58a6ff ${pct}%, #30363d ${pct}%)`,
        }}
      />
      <div className="flex justify-between text-[10px] text-[#484f58]">
        <span>{min}{unit}</span>
        <span>{max}{unit}</span>
      </div>
    </div>
  )
}
