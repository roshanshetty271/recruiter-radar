"use client";

import React, { useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChatBubble } from "./ChatBubble";
import { ChatTypingIndicator } from "./ChatTypingIndicator";
import type { ChatMessage } from "../../lib/types";

interface ChatSectionProps {
  messages: ChatMessage[];
  isTyping: boolean;
  className?: string;
}

export function ChatSection({
  messages,
  isTyping,
  className = "",
}: ChatSectionProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  // 🚨 LOG J: Duplicate Render Detector
  useEffect(() => {
    console.log(
      `🚨 LOG J [CHAT_RENDER]: messages_count=${
        messages.length
      }, isTyping=${isTyping}, timestamp=${Date.now()}`
    );
    if (messages.length > 0) {
      const lastMessage = messages[messages.length - 1];
      console.log(
        `🚨 LOG J [CHAT_RENDER]: last_message_role=${
          lastMessage.role
        }, content_preview='${lastMessage.content.substring(
          0,
          50
        )}...', candidates_count=${lastMessage.candidates?.length || 0}`
      );
    }
  }, [messages, isTyping]);

  // If no messages and not typing, don't render anything
  if (messages.length === 0 && !isTyping) {
    return null;
  }

  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: "auto" }}
      exit={{ opacity: 0, height: 0 }}
      transition={{ duration: 0.3, ease: "easeInOut" }}
      className={`max-h-96 overflow-y-auto space-y-4 p-4 ${className}`}
      style={{
        background: "rgba(255,255,255,0.02)",
        backdropFilter: "blur(8px)",
        border: "1px solid rgba(255,255,255,0.05)",
        borderRadius: "12px",
      }}
      role="log"
      aria-live="polite"
      aria-label="Chat conversation"
    >
      <AnimatePresence initial={false}>
        {messages.map((message, index) => (
          <motion.div
            key={message.id}
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -20, scale: 0.95 }}
            transition={{
              duration: 0.3,
              delay: index * 0.05, // Stagger animation
              ease: "easeOut",
            }}
          >
            <ChatBubble message={message} />
          </motion.div>
        ))}
      </AnimatePresence>

      {/* Typing indicator */}
      {isTyping && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -20 }}
          transition={{ duration: 0.2 }}
        >
          <ChatTypingIndicator />
        </motion.div>
      )}

      {/* Invisible element to scroll to */}
      <div ref={messagesEndRef} />
    </motion.div>
  );
}
