"use client";

import React from "react";
import { motion } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import { Badge } from "../ui/badge";
import { Progress } from "../ui/progress";

interface ChatPerformanceMetrics {
  totalRequests: number;
  assistantSuccessRate: number;
  fallbackRate: number;
  cacheHitRate: number;
  avgResponseTime: number;
  systemHealth: "healthy" | "degraded";
}

interface PerformanceMonitorProps {
  metrics: ChatPerformanceMetrics | null;
  onRefresh?: () => void;
  compact?: boolean;
  className?: string;
}

export function PerformanceMonitor({
  metrics,
  onRefresh,
  compact = false,
  className = "",
}: PerformanceMonitorProps) {
  if (!metrics) {
    return null;
  }

  const getHealthColor = (health: string) => {
    switch (health) {
      case "healthy":
        return "bg-green-500";
      case "degraded":
        return "bg-yellow-500";
      default:
        return "bg-red-500";
    }
  };

  const getHealthIcon = (health: string) => {
    switch (health) {
      case "healthy":
        return "🟢";
      case "degraded":
        return "🟡";
      default:
        return "🔴";
    }
  };

  if (compact) {
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className={`flex items-center gap-2 p-2 rounded-lg bg-white/5 border border-white/10 ${className}`}
      >
        <span className="text-xs font-medium">System:</span>
        <Badge variant="outline" className="text-xs">
          {getHealthIcon(metrics.systemHealth)} {metrics.systemHealth}
        </Badge>
        <span className="text-xs text-white/60">|</span>
        <span className="text-xs text-white/80">
          Cache: {metrics.cacheHitRate.toFixed(1)}%
        </span>
        <span className="text-xs text-white/60">|</span>
        <span className="text-xs text-white/80">
          Avg: {metrics.avgResponseTime.toFixed(2)}s
        </span>
        {onRefresh && (
          <button
            onClick={onRefresh}
            className="ml-2 text-xs px-2 py-1 rounded bg-white/10 hover:bg-white/20 transition-colors"
          >
            🔄
          </button>
        )}
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className={className}
    >
      <Card className="bg-white/5 border-white/10 backdrop-blur-sm">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg font-semibold text-white">
              🚀 Bulletproof Chat Metrics
            </CardTitle>
            <div className="flex items-center gap-2">
              <Badge
                variant="outline"
                className={`px-3 py-1 ${getHealthColor(
                  metrics.systemHealth
                )} border-0 text-white`}
              >
                {getHealthIcon(metrics.systemHealth)}{" "}
                {metrics.systemHealth.toUpperCase()}
              </Badge>
              {onRefresh && (
                <button
                  onClick={onRefresh}
                  className="px-3 py-1 rounded bg-white/10 hover:bg-white/20 transition-colors text-sm"
                >
                  🔄 Refresh
                </button>
              )}
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Performance Overview */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-white">
                {metrics.totalRequests}
              </div>
              <div className="text-xs text-white/60">Total Requests</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-green-400">
                {metrics.assistantSuccessRate.toFixed(1)}%
              </div>
              <div className="text-xs text-white/60">Assistant Success</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-yellow-400">
                {metrics.fallbackRate.toFixed(1)}%
              </div>
              <div className="text-xs text-white/60">Fallback Rate</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-white">
                {metrics.avgResponseTime.toFixed(2)}s
              </div>
              <div className="text-xs text-white/60">Avg Response</div>
            </div>
          </div>

          {/* Performance Bars */}
          <div className="space-y-3">
            <div>
              <div className="flex justify-between text-sm mb-1">
                <span className="text-white/80">⚡ Cache Hit Rate</span>
                <span className="text-white font-medium">
                  {metrics.cacheHitRate.toFixed(1)}%
                </span>
              </div>
              <Progress
                value={metrics.cacheHitRate}
                className="h-2 bg-white/10"
              />
            </div>

            <div>
              <div className="flex justify-between text-sm mb-1">
                <span className="text-white/80">🤖 Assistant Success</span>
                <span className="text-white font-medium">
                  {metrics.assistantSuccessRate.toFixed(1)}%
                </span>
              </div>
              <Progress
                value={metrics.assistantSuccessRate}
                className="h-2 bg-white/10"
              />
            </div>

            <div>
              <div className="flex justify-between text-sm mb-1">
                <span className="text-white/80">🛡️ System Reliability</span>
                <span className="text-white font-medium">
                  {(100 - metrics.fallbackRate).toFixed(1)}%
                </span>
              </div>
              <Progress
                value={100 - metrics.fallbackRate}
                className="h-2 bg-white/10"
              />
            </div>
          </div>

          {/* Performance Insights */}
          <div className="mt-4 p-3 rounded-lg bg-white/5 border border-white/10">
            <div className="text-sm text-white/80 space-y-1">
              <div className="font-medium mb-2">🎯 Performance Insights:</div>
              {metrics.cacheHitRate > 80 && (
                <div className="text-green-400">
                  ⚡ Excellent cache performance - ultra-fast responses!
                </div>
              )}
              {metrics.assistantSuccessRate > 50 && (
                <div className="text-blue-400">
                  🤖 High assistant engagement - enhanced conversation quality!
                </div>
              )}
              {metrics.fallbackRate > 30 && (
                <div className="text-yellow-400">
                  🛡️ Fallback protection active - ensuring 100% reliability!
                </div>
              )}
              {metrics.avgResponseTime < 1 && (
                <div className="text-green-400">
                  🚀 Lightning-fast responses - excellent user experience!
                </div>
              )}
              {metrics.systemHealth === "healthy" && (
                <div className="text-green-400">
                  ✅ All systems operating optimally!
                </div>
              )}
            </div>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}
