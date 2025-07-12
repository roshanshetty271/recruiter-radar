"use client";

import { X, ContrastIcon as Versus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";

interface Candidate {
  id: number;
  name: string;
  title: string;
  avatar: string;
  matchScore: number;
}

export function ComparisonBar({
  candidates,
  onRemove,
  onCompare,
  onClear,
}: {
  candidates: Candidate[];
  onRemove: (id: number) => void;
  onCompare: () => void;
  onClear: () => void;
}) {
  return (
    <div
      className="flex items-center space-x-4 p-4 rounded-xl animate-in slide-in-from-bottom-4 duration-300"
      style={{
        background: "rgba(10,10,20,0.95)",
        backdropFilter: "blur(20px)",
        border: "1px solid rgba(255,255,255,0.2)",
        boxShadow: "0 20px 40px rgba(0,0,0,0.3)",
      }}
    >
      <div className="flex items-center space-x-2">
        <Versus className="w-5 h-5 text-purple-400" />
        <span className="text-sm font-medium text-white">
          Compare ({candidates.length}/3)
        </span>
      </div>

      <div className="flex items-center space-x-2">
        {candidates.map((candidate, index) => (
          <div key={candidate.id} className="relative group">
            <div className="flex items-center space-x-2 p-2 bg-white/10 rounded-lg">
              <img
                src={candidate.avatar || "/placeholder.svg"}
                alt={candidate.name}
                className="w-8 h-8 rounded-full object-cover"
              />
              <div className="text-xs">
                <div className="text-white font-medium truncate max-w-20">
                  {candidate.name}
                </div>
                <div className="text-purple-300">{candidate.matchScore}%</div>
              </div>
              <button
                onClick={() => onRemove(candidate.id)}
                className="opacity-0 group-hover:opacity-100 transition-opacity p-1 hover:bg-red-500/20 rounded"
              >
                <X className="w-3 h-3 text-red-400" />
              </button>
            </div>
            {index < candidates.length - 1 && (
              <div className="absolute top-1/2 -right-3 transform -translate-y-1/2 text-gray-500">
                vs
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="flex items-center space-x-2">
        <Button
          onClick={onCompare}
          disabled={candidates.length < 2}
          className="px-4 py-2 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-500 hover:to-blue-500 disabled:opacity-50 text-sm"
        >
          Compare
        </Button>

        <Button
          onClick={onClear}
          variant="ghost"
          size="sm"
          className="text-gray-400 hover:text-red-400"
        >
          <Trash2 className="w-4 h-4" />
        </Button>
      </div>
    </div>
  );
}
