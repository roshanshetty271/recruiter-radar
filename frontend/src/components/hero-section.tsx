"use client";

import { useState, useEffect } from "react";
import { Search, Sparkles, Users, MapPin, Code } from "lucide-react";
import { Button } from "./ui/button";

const VALUE_PROPS = [
  "Find top talent in seconds",
  "AI-powered candidate matching",
  "Global talent pool access",
  "Real-time availability tracking",
];

const EXAMPLE_SEARCHES = [
  { text: "Senior React Developer in SF", icon: Code },
  { text: "Product Manager with AI experience", icon: Sparkles },
  { text: "Remote DevOps Engineer", icon: MapPin },
  { text: "UX Designer at Series B startups", icon: Users },
];

export function HeroSection({
  onSearch,
}: {
  onSearch: (query: string) => void;
}) {
  const [currentPropIndex, setCurrentPropIndex] = useState(0);
  const [displayText, setDisplayText] = useState("");
  const [isTyping, setIsTyping] = useState(true);

  // --- Fix hydration error: move code rain randomization to useEffect ---
  type Dot = {
    left: string;
    top: string;
    animationDelay: string;
    label: string;
  };
  const [dots, setDots] = useState<Dot[]>([]);
  useEffect(() => {
    const newDots: Dot[] = Array.from({ length: 20 }).map(() => ({
      left: `${Math.random() * 100}%`,
      top: `${Math.random() * 100}%`,
      animationDelay: `${Math.random() * 5}s`,
      label: Math.random().toString(36).substring(7),
    }));
    setDots(newDots);
  }, []);
  // --- End fix ---

  useEffect(() => {
    const currentProp = VALUE_PROPS[currentPropIndex];
    let charIndex = 0;

    if (isTyping) {
      const typeInterval = setInterval(() => {
        if (charIndex < currentProp.length) {
          setDisplayText(currentProp.slice(0, charIndex + 1));
          charIndex++;
        } else {
          clearInterval(typeInterval);
          setTimeout(() => setIsTyping(false), 2000);
        }
      }, 100);

      return () => clearInterval(typeInterval);
    } else {
      const eraseInterval = setInterval(() => {
        if (charIndex >= 0) {
          setDisplayText(currentProp.slice(0, charIndex));
          charIndex--;
        } else {
          clearInterval(eraseInterval);
          setCurrentPropIndex((prev) => (prev + 1) % VALUE_PROPS.length);
          setIsTyping(true);
        }
      }, 50);

      return () => clearInterval(eraseInterval);
    }
  }, [currentPropIndex, isTyping]);

  return (
    <div className="min-h-[60vh] flex items-center justify-center relative">
      {/* Code rain effect */}
      <div className="absolute inset-0 overflow-hidden opacity-5">
        <div className="absolute animate-pulse">
          {dots.map((dot, i) => (
            <div
              key={i}
              className="absolute text-green-400 font-mono text-xs"
              style={{
                left: dot.left,
                top: dot.top,
                animationDelay: dot.animationDelay,
              }}
            >
              {dot.label}
            </div>
          ))}
        </div>
      </div>

      <div className="text-center space-y-6 max-w-4xl mx-auto px-4">
        <div className="space-y-4">
          <h1 className="text-5xl md:text-6xl font-black bg-gradient-to-r from-white via-purple-200 to-blue-200 bg-clip-text text-transparent animate-pulse">
            Recruiter Radar
          </h1>

          <div className="h-12 flex items-center justify-center">
            <p className="text-lg md:text-xl text-gray-300">
              {displayText}
              <span className="animate-pulse">|</span>
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-2xl mx-auto">
          {EXAMPLE_SEARCHES.map((search, index) => (
            <button
              key={index}
              onClick={() => onSearch(search.text)}
              className="group relative p-4 rounded-xl backdrop-blur-md bg-white/5 border border-white/10 hover:border-purple-400/50 transition-all duration-300 hover:scale-105 hover:shadow-lg hover:shadow-purple-500/25"
              style={{
                background:
                  "linear-gradient(135deg, rgba(255,255,255,0.1) 0%, rgba(255,255,255,0.05) 100%)",
              }}
            >
              <div className="flex items-center space-x-3">
                <search.icon className="w-5 h-5 text-purple-400 group-hover:rotate-12 transition-transform duration-300" />
                <span className="text-white/90 group-hover:text-white transition-colors">
                  {search.text}
                </span>
              </div>

              {/* Ripple effect */}
              <div className="absolute inset-0 rounded-xl opacity-0 group-active:opacity-100 bg-white/10 transition-opacity duration-150" />
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
