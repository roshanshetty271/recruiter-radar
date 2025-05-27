"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { MapPin, TrendingUp } from "lucide-react";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

export function LocationHeatMap() {
  const [heatData, setHeatData] = useState(api.getLocationHeatMap());

  useEffect(() => {
    // Update after each search
    const interval = setInterval(() => {
      setHeatData(api.getLocationHeatMap());
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  if (heatData.length === 0) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass rounded-lg p-4 mb-6"
    >
      <div className="flex items-center gap-2 mb-3">
        <TrendingUp className="w-4 h-4 text-blue-500" />
        <h3 className="text-sm font-medium">Talent Hotspots</h3>
      </div>
      <div className="space-y-2">
        {heatData.slice(0, 5).map((location, i) => (
          <motion.div
            key={location.location}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.1 }}
            className="flex items-center justify-between"
          >
            <div className="flex items-center gap-2">
              <MapPin className="w-3 h-3 text-muted-foreground" />
              <span className="text-sm">{location.location}</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="relative w-20 h-2 bg-white/10 rounded-full overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${location.intensity * 100}%` }}
                  transition={{ duration: 0.5, delay: i * 0.1 }}
                  className={cn(
                    "absolute h-full rounded-full",
                    location.intensity > 0.7
                      ? "bg-red-500"
                      : location.intensity > 0.4
                      ? "bg-orange-500"
                      : "bg-blue-500"
                  )}
                />
              </div>
              <span className="text-xs text-muted-foreground w-8 text-right">
                {location.count}
              </span>
            </div>
          </motion.div>
        ))}
      </div>
      {heatData.length > 5 && (
        <p className="text-xs text-muted-foreground mt-2">
          +{heatData.length - 5} more locations
        </p>
      )}
    </motion.div>
  );
}
