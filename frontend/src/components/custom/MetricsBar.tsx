"use client";

import { motion } from "framer-motion";
import { Clock, Search, Mail, TrendingUp, Zap } from "lucide-react";
import { formatDuration, formatNumber } from "@/lib/utils";
import { cn } from "@/lib/utils";

interface MetricsBarProps {
  sessionDuration: number;
  totalSearches: number;
  outreachGenerated: number;
  candidatesViewed: number;
  estimatedTimeSaved: number;
}

export function MetricsBar(props: MetricsBarProps) {
  const efficiencyRank =
    props.totalSearches > 0
      ? Math.min(
          5,
          Math.floor((props.estimatedTimeSaved / props.sessionDuration) * 100)
        )
      : 0;

  return (
    <motion.div
      initial={{ y: -20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      className="border-b border-border/50 bg-background/80 backdrop-blur-xl sticky top-0 z-50"
    >
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between py-3">
          <div className="flex items-center gap-6 overflow-x-auto">
            <MetricItem
              icon={Clock}
              label="Session"
              value={formatDuration(props.sessionDuration)}
            />
            <MetricItem
              icon={Search}
              label="Searches"
              value={props.totalSearches.toString()}
              pulse={props.totalSearches > 0}
            />
            <MetricItem
              icon={Mail}
              label="Outreach"
              value={props.outreachGenerated.toString()}
              pulse={props.outreachGenerated > 0}
            />
            <MetricItem
              icon={TrendingUp}
              label="Time Saved"
              value={`${props.estimatedTimeSaved}min`}
              highlight
            />
          </div>

          <div className="hidden md:flex items-center gap-2">
            <Zap className="w-4 h-4 text-yellow-500" />
            <span className="text-sm text-muted-foreground">
              Efficiency:{" "}
              <span
                className={cn(
                  "font-medium",
                  efficiencyRank > 3
                    ? "text-green-500"
                    : efficiencyRank > 1
                    ? "text-yellow-500"
                    : "text-muted-foreground"
                )}
              >
                Top {efficiencyRank || "?"}%
              </span>
            </span>
          </div>
        </div>
      </div>
    </motion.div>
  );
}

function MetricItem({
  icon: Icon,
  label,
  value,
  highlight = false,
  pulse = false,
}: {
  icon: any;
  label: string;
  value: string;
  highlight?: boolean;
  pulse?: boolean;
}) {
  return (
    <motion.div
      className="flex items-center gap-2"
      animate={pulse ? { scale: [1, 1.05, 1] } : {}}
      transition={{ duration: 0.3 }}
    >
      <Icon
        className={cn(
          "w-4 h-4",
          highlight ? "text-green-500" : "text-muted-foreground"
        )}
      />
      <span className="text-sm text-muted-foreground">{label}:</span>
      <span
        className={cn(
          "text-sm font-medium tabular-nums",
          highlight && "text-green-500"
        )}
      >
        {value}
      </span>
    </motion.div>
  );
}
