"use client";

import React, { useState, memo } from "react";
import { motion } from "framer-motion";
import { Copy, Check, Bot, User } from "lucide-react";
import { Button } from "../ui/button";
import { toast } from "../../hooks/use-toast";
import type { ChatMessage } from "../../lib/types";

interface ChatBubbleProps {
  message: ChatMessage;
}

const ChatBubbleComponent = function ChatBubble({ message }: ChatBubbleProps) {
  const [copied, setCopied] = useState(false);
  const [showTimestamp, setShowTimestamp] = useState(false);

  const isUser = message.role === "user";

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      toast({
        title: "Copied to clipboard",
        description: "Message copied successfully",
      });
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      toast({
        title: "Copy failed",
        description: "Failed to copy message to clipboard",
        variant: "destructive",
      });
    }
  };

  const formatTimestamp = (date: Date) => {
    return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  };

  return (
    <div
      className={`flex ${
        isUser ? "justify-end" : "justify-start"
      } items-start space-x-2`}
    >
      {/* Assistant avatar */}
      {!isUser && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-r from-purple-600 to-blue-600 flex items-center justify-center">
          <Bot className="w-4 h-4 text-white" />
        </div>
      )}

      {/* Message bubble */}
      <motion.div
        layout
        className={`
          max-w-xs lg:max-w-md px-4 py-3 rounded-2xl relative group
          ${
            isUser
              ? "bg-gradient-to-r from-purple-600 to-blue-600 text-white"
              : "bg-white/10 backdrop-blur-sm text-white border border-white/20"
          }
        `}
        onMouseEnter={() => setShowTimestamp(true)}
        onMouseLeave={() => setShowTimestamp(false)}
      >
        {/* Message content */}
        <div className="text-sm leading-relaxed whitespace-pre-wrap">
          {message.content}
        </div>

        {/* Candidates count indicator */}
        {message.candidates && message.candidates.length > 0 && (
          <div className="mt-2 pt-2 border-t border-white/20">
            <div className="text-xs opacity-75">
              Found {message.candidates.length} candidate
              {message.candidates.length !== 1 ? "s" : ""}
            </div>
          </div>
        )}

        {/* Copy button (appears on hover) */}
        <Button
          variant="ghost"
          size="sm"
          onClick={handleCopy}
          className={`
            absolute top-1 right-1 w-6 h-6 p-0 opacity-0 group-hover:opacity-100
            transition-opacity duration-200
            ${
              isUser
                ? "text-white/70 hover:text-white"
                : "text-gray-400 hover:text-white"
            }
          `}
        >
          {copied ? (
            <Check className="w-3 h-3" />
          ) : (
            <Copy className="w-3 h-3" />
          )}
        </Button>

        {/* Timestamp tooltip */}
        {showTimestamp && (
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.9 }}
            className={`
              absolute top-full mt-1 px-2 py-1 bg-black/80 text-white text-xs rounded
              ${isUser ? "right-0" : "left-0"}
            `}
          >
            {formatTimestamp(message.timestamp)}
          </motion.div>
        )}

        {/* Message tail */}
        <div
          className={`
            absolute top-4 w-3 h-3 rotate-45
            ${
              isUser
                ? "-right-1.5 bg-gradient-to-r from-purple-600 to-blue-600"
                : "-left-1.5 bg-white/10 border-l border-b border-white/20"
            }
          `}
        />
      </motion.div>

      {/* User avatar */}
      {isUser && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gray-600 flex items-center justify-center">
          <User className="w-4 h-4 text-white" />
        </div>
      )}
    </div>
  );
};

// Memoize the component to prevent unnecessary re-renders
export const ChatBubble = memo(ChatBubbleComponent);
