"use client";

import type React from "react";

import { useState, useEffect } from "react";
import {
  Zap,
  Clock,
  Target,
  TrendingUp,
  Users,
  Star,
  MessageSquare,
  Sparkles,
} from "lucide-react";
import { useSavedCandidates } from "@/hooks/use-saved-candidates";

interface MetricsBarProps {
  totalSearches?: number;
  totalResults?: number;
  searchTimeMs?: number;
  outreachGenerated?: number;
  onSavedClick?: () => void;
}

export function MetricsBar({
  totalSearches = 0,
  totalResults = 0,
  searchTimeMs = 0,
  outreachGenerated = 0,
  onSavedClick,
}: MetricsBarProps) {
  const [isScrolled, setIsScrolled] = useState(false);
  const [sessionTime, setSessionTime] = useState(0);
  const { count: savedCount } = useSavedCandidates();
  const [metrics, setMetrics] = useState({
    candidatesFound: 0,
    efficiencyRank: 0,
    activeSearches: 0,
    outreachMessages: 0,
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
      candidatesFound: totalResults || 0,
      activeSearches: totalSearches || 0,
      outreachMessages: outreachGenerated || 0,
      // Calculate efficiency based on search time (faster = higher %)
      // Also boost efficiency if user has saved candidates (power user bonus!)
      efficiencyRank:
        searchTimeMs > 0
          ? Math.min(
              99,
              Math.max(70, 100 - searchTimeMs / 100) + (savedCount > 10 ? 5 : 0)
            )
          : savedCount > 10
          ? 5
          : 0,
    }));
  }, [
    totalSearches,
    totalResults,
    searchTimeMs,
    outreachGenerated,
    savedCount,
  ]);

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
              icon={<Star className="w-4 h-4 text-yellow-500" />}
              label="Saved"
              value={savedCount.toString()}
              highlight={savedCount > 0}
              onClick={onSavedClick}
              clickable={true}
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

            <MetricItem
              icon={<MessageSquare className="w-4 h-4 text-purple-400" />}
              label="Outreach"
              value={metrics.outreachMessages.toString()}
              animate={outreachGenerated > 0}
              sparkle={outreachGenerated > 0}
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
  sparkle = false,
  highlight = false,
  onClick,
  clickable = false,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  animate?: boolean;
  glow?: boolean;
  lightning?: boolean;
  sparkle?: boolean;
  highlight?: boolean;
  onClick?: () => void;
  clickable?: boolean;
}) {
  return (
    <div
      className={`flex items-center space-x-2 group relative transition-all duration-200 ${
        glow
          ? "text-green-400"
          : sparkle
          ? "text-purple-400"
          : highlight
          ? "text-yellow-500"
          : "text-gray-300"
      } ${
        clickable
          ? "cursor-pointer hover:bg-white/10 rounded-lg px-3 py-1.5 hover:scale-105"
          : "cursor-pointer"
      } ${
        highlight && clickable
          ? "bg-gradient-to-r from-yellow-500/20 to-orange-500/20 border border-yellow-500/30 rounded-lg px-3 py-1.5"
          : ""
      }`}
      onClick={onClick}
    >
      {sparkle && (
        <div className="absolute -top-1 -right-1">
          <Sparkles className="w-3 h-3 text-purple-400 animate-pulse" />
        </div>
      )}

      {highlight && clickable && parseInt(value) > 0 && (
        <div className="absolute -top-1 -right-1">
          <span className="text-xs text-yellow-500 font-bold animate-pulse">
            NEW
          </span>
        </div>
      )}

      <div
        className={`${animate ? "animate-pulse" : ""} ${
          lightning ? "animate-bounce" : ""
        } ${sparkle ? "animate-pulse" : ""} ${
          highlight ? "drop-shadow-lg" : ""
        }`}
      >
        {icon}
      </div>
      <div className="text-sm">
        <div className="text-xs opacity-60">{label}</div>
        <div
          className={`font-semibold group-hover:scale-110 transition-transform ${
            highlight ? "text-yellow-500" : ""
          }`}
        >
          {value}
        </div>
      </div>
    </div>
  );
}
