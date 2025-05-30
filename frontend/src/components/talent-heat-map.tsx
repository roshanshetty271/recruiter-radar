"use client"

import { MapPin } from "lucide-react"

const LOCATIONS = [
  { name: "San Francisco", count: 1247, percentage: 35 },
  { name: "New York", count: 892, percentage: 25 },
  { name: "Austin", count: 623, percentage: 18 },
  { name: "Seattle", count: 445, percentage: 13 },
  { name: "Remote", count: 334, percentage: 9 },
]

export function TalentHeatMap() {
  return (
    <div
      className="p-6 rounded-xl"
      style={{
        background: "rgba(255,255,255,0.03)",
        backdropFilter: "blur(12px)",
        border: "1px solid rgba(255,255,255,0.1)",
      }}
    >
      <div className="flex items-center space-x-2 mb-6">
        <MapPin className="w-5 h-5 text-purple-400 animate-pulse" />
        <h3 className="text-lg font-semibold bg-gradient-to-r from-white to-gray-300 bg-clip-text text-transparent">
          Talent Heat Map
        </h3>
      </div>

      <div className="space-y-4">
        {LOCATIONS.map((location, index) => (
          <div key={location.name} className="group cursor-pointer">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-gray-300 group-hover:text-white transition-colors">{location.name}</span>
              <span className="text-xs text-gray-500">{location.count.toLocaleString()}</span>
            </div>

            <div className="w-full bg-gray-800 rounded-full h-2 overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-purple-500 to-blue-500 rounded-full transition-all duration-1000 ease-out group-hover:shadow-lg group-hover:shadow-purple-500/50"
                style={{
                  width: `${location.percentage}%`,
                  animationDelay: `${index * 100}ms`,
                }}
              />
            </div>

            <div className="text-xs text-gray-500 mt-1">{location.percentage}% of candidates</div>
          </div>
        ))}
      </div>

      <button className="w-full mt-6 text-sm text-purple-400 hover:text-purple-300 transition-colors flex items-center justify-center space-x-1">
        <span>View Geographic Map</span>
        <span className="transform group-hover:translate-x-1 transition-transform">→</span>
      </button>
    </div>
  )
}
