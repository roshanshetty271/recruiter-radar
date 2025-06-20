"use client";

import { useState, useEffect } from "react";
import { Search, Clock, Zap, Users, Settings, X } from "lucide-react";
import { Input } from "./ui/input";

const QUICK_ACTIONS = [
  {
    icon: Search,
    label: "Search Candidates",
    shortcut: "⌘S",
    action: "search",
  },
  {
    icon: Users,
    label: "View Saved Candidates",
    shortcut: "⌘B",
    action: "saved",
  },
  { icon: Zap, label: "Quick Filters", shortcut: "⌘F", action: "filters" },
  { icon: Settings, label: "Settings", shortcut: "⌘,", action: "settings" },
];

const RECENT_SEARCHES = [
  "Senior React Developer",
  "Product Manager AI",
  "DevOps Engineer Remote",
  "UX Designer Series B",
];

export function CommandPalette({
  isOpen,
  onClose,
  onSearch,
}: {
  isOpen: boolean;
  onClose: () => void;
  onSearch: (query: string) => void;
}) {
  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);

  useEffect(() => {
    if (isOpen) {
      setQuery("");
      setSelectedIndex(0);
    }
  }, [isOpen]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isOpen) return;

      if (e.key === "Escape") {
        onClose();
      } else if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedIndex((prev) =>
          Math.min(prev + 1, QUICK_ACTIONS.length + RECENT_SEARCHES.length - 1)
        );
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedIndex((prev) => Math.max(prev - 1, 0));
      } else if (e.key === "Enter") {
        e.preventDefault();
        if (selectedIndex < QUICK_ACTIONS.length) {
          // Handle quick action
          onClose();
        } else {
          // Handle recent search
          const searchIndex = selectedIndex - QUICK_ACTIONS.length;
          onSearch(RECENT_SEARCHES[searchIndex]);
          onClose();
        }
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, selectedIndex, onClose, onSearch]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-[20vh]">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div
        className="relative w-full max-w-lg mx-4 rounded-xl overflow-hidden animate-in slide-in-from-bottom-4 duration-300"
        style={{
          background: "rgba(10,10,20,0.95)",
          backdropFilter: "blur(20px)",
          border: "1px solid rgba(255,255,255,0.1)",
        }}
      >
        {/* Header */}
        <div className="flex items-center p-4 border-b border-white/10">
          <Search className="w-5 h-5 text-gray-400 mr-3" />
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search or run a command..."
            className="flex-1 bg-transparent border-0 text-white placeholder-gray-400 focus:ring-0"
            autoFocus
          />
          <button
            onClick={onClose}
            className="ml-3 text-gray-400 hover:text-white"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="max-h-96 overflow-y-auto">
          {/* Quick Actions */}
          <div className="p-2">
            <div className="px-3 py-2 text-xs font-medium text-gray-400 uppercase tracking-wider">
              Quick Actions
            </div>
            {QUICK_ACTIONS.map((action, index) => (
              <button
                key={action.action}
                className={`w-full flex items-center justify-between p-3 rounded-lg text-left transition-colors ${
                  selectedIndex === index
                    ? "bg-purple-600/20 text-white"
                    : "text-gray-300 hover:bg-white/5"
                }`}
              >
                <div className="flex items-center space-x-3">
                  <action.icon className="w-4 h-4" />
                  <span>{action.label}</span>
                </div>
                <span className="text-xs text-gray-500">{action.shortcut}</span>
              </button>
            ))}
          </div>

          {/* Recent Searches */}
          <div className="p-2 border-t border-white/10">
            <div className="px-3 py-2 text-xs font-medium text-gray-400 uppercase tracking-wider">
              Recent Searches
            </div>
            {RECENT_SEARCHES.map((search, index) => (
              <button
                key={search}
                onClick={() => {
                  onSearch(search);
                  onClose();
                }}
                className={`w-full flex items-center space-x-3 p-3 rounded-lg text-left transition-colors ${
                  selectedIndex === QUICK_ACTIONS.length + index
                    ? "bg-purple-600/20 text-white"
                    : "text-gray-300 hover:bg-white/5"
                }`}
              >
                <Clock className="w-4 h-4 text-gray-500" />
                <span>{search}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-3 border-t border-white/10 text-xs text-gray-500">
          <div className="flex items-center space-x-4">
            <span>↑↓ Navigate</span>
            <span>↵ Select</span>
            <span>ESC Close</span>
          </div>
        </div>
      </div>
    </div>
  );
}
