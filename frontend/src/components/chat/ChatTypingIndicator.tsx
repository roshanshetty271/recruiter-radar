"use client";

import React, { memo } from "react";
import { motion } from "framer-motion";
import { Bot } from "lucide-react";

const ChatTypingIndicatorComponent = function ChatTypingIndicator() {
  return (
    <div className="flex justify-start items-start space-x-2">
      {/* Assistant avatar */}
      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-r from-purple-600 to-blue-600 flex items-center justify-center">
        <Bot className="w-4 h-4 text-white" />
      </div>

      {/* Typing bubble */}
      <div className="bg-white/10 backdrop-blur-sm border border-white/20 px-4 py-3 rounded-2xl relative max-w-xs">
        {/* Typing dots */}
        <div className="flex items-center space-x-1">
          <span className="text-sm text-white/70">AI is thinking</span>
          <div className="flex space-x-1 ml-2">
            {[0, 1, 2].map((index) => (
              <motion.div
                key={index}
                className="w-2 h-2 bg-purple-400 rounded-full"
                animate={{
                  scale: [1, 1.2, 1],
                  opacity: [0.5, 1, 0.5],
                }}
                transition={{
                  duration: 1.2,
                  repeat: Infinity,
                  delay: index * 0.2,
                  ease: "easeInOut",
                }}
              />
            ))}
          </div>
        </div>

        {/* Message tail */}
        <div className="absolute top-4 -left-1.5 w-3 h-3 rotate-45 bg-white/10 border-l border-b border-white/20" />
      </div>
    </div>
  );
};

// Memoize the component for performance
export const ChatTypingIndicator = memo(ChatTypingIndicatorComponent);
