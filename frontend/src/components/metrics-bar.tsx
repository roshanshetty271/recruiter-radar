"use client";

import type React from "react";

import { useState, useEffect } from "react";
import { Zap, Clock, Target, TrendingUp, Users, Star } from "lucide-react";

export function MetricsBar({
  totalSearches = 0,
  totalResults = 0,
  searchTimeMs = 0,
}) {
  const [isScrolled, setIsScrolled] = useState(false);
  const [sessionTime, setSessionTime] = useState(0);
  const [metrics, setMetrics] = useState({
    candidatesFound: 0,
    timeSaved: 0,
    efficiencyRank: 0,
    activeSearches: 0,
  });

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 50);
    };

    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  useEffect(() => {
    // Update metrics when search results come in
    setMetrics((prev) => ({
      ...prev,
      candidatesFound: totalResults || prev.candidatesFound,
      activeSearches: totalSearches || prev.activeSearches,
      // Assume each manual search would take 15 minutes (0.25 hours)
      timeSaved:
        totalSearches > 0 ? (totalSearches * 0.25).toFixed(1) : prev.timeSaved,
      // Calculate efficiency based on search time (faster = higher %)
      efficiencyRank:
        searchTimeMs > 0
          ? Math.min(99, Math.max(70, 100 - searchTimeMs / 100))
          : prev.efficiencyRank,
    }));
  }, [totalSearches, totalResults, searchTimeMs]);

  useEffect(() => {
    // Animate metrics on load if no real metrics exist yet
    if (totalSearches === 0) {
      const timer = setTimeout(() => {
        setMetrics({
          candidatesFound: 1247,
          timeSaved: 23.5,
          efficiencyRank: 94,
          activeSearches: 8,
        });
      }, 500);

      return () => clearTimeout(timer);
    }
  }, [totalSearches]);

  useEffect(() => {
    // Session timer
    const interval = setInterval(() => {
      setSessionTime((prev) => prev + 1);
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, "0")}:${secs
      .toString()
      .padStart(2, "0")}`;
  };

  return (
    <div
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        isScrolled ? "h-12" : "h-16"
      }`}
      style={{
        backdropFilter: "blur(20px)",
        background: "rgba(10,10,20,0.6)",
        borderBottom: "1px solid rgba(255,255,255,0.1)",
      }}
    >
      <div className="container mx-auto px-4 h-full flex items-center justify-between">
        <div className="flex items-center space-x-8">
          <div className="flex items-center space-x-2">
            <div className="w-8 h-8 bg-gradient-to-r from-purple-500 to-blue-500 rounded-lg flex items-center justify-center">
              <Target className="w-4 h-4 text-white" />
            </div>
            <span className="font-bold text-white">Recruiter Radar</span>
          </div>

          <div className="hidden md:flex items-center space-x-6">
            <MetricItem
              icon={<Users className="w-4 h-4" />}
              label="Candidates"
              value={metrics.candidatesFound.toLocaleString()}
              animate={totalResults > 0}
            />

            <MetricItem
              icon={<Clock className="w-4 h-4 text-green-400" />}
              label="Time Saved"
              value={`${metrics.timeSaved}h`}
              glow
            />

            <MetricItem
              icon={<Zap className="w-4 h-4 text-yellow-400" />}
              label="Efficiency"
              value={`${metrics.efficiencyRank.toFixed(0)}%`}
              lightning={searchTimeMs > 0 && searchTimeMs < 500}
            />

            <MetricItem
              icon={<TrendingUp className="w-4 h-4" />}
              label="Searches"
              value={metrics.activeSearches.toString()}
            />
          </div>
        </div>

        <div className="flex items-center space-x-4">
          <div className="text-sm text-gray-400 font-mono">
            Session: {formatTime(sessionTime)}
          </div>
          <div className="flex items-center space-x-1">
            <Star className="w-4 h-4 text-yellow-400" />
            <span className="text-sm text-white">Pro</span>
          </div>
        </div>
      </div>
    </div>
  );
}

function MetricItem({
  icon,
  label,
  value,
  animate = false,
  glow = false,
  lightning = false,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  animate?: boolean;
  glow?: boolean;
  lightning?: boolean;
}) {
  return (
    <div
      className={`flex items-center space-x-2 group cursor-pointer ${
        glow ? "text-green-400" : "text-gray-300"
      }`}
    >
      <div
        className={`${animate ? "animate-pulse" : ""} ${
          lightning ? "animate-bounce" : ""
        }`}
      >
        {icon}
      </div>
      <div className="text-sm">
        <div className="text-xs opacity-60">{label}</div>
        <div className="font-semibold">{value}</div>
      </div>
    </div>
  );
}
