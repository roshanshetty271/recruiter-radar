import { useState, useEffect, useCallback, useRef } from "react";

/**
 * Simple debounce hook for values
 */
export function useDebounce<T>(value: T, delay: number = 300): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
}

/**
 * Chat-specific hook for managing typing indicators and anti-spam
 */
export function useChatHelpers() {
  const [isTypingUser, setIsTypingUser] = useState(false);
  const lastMessageTime = useRef<number>(0);
  const typingTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const startTyping = useCallback(() => {
    setIsTypingUser(true);

    // Clear existing timeout
    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current);
    }

    // Set new timeout to stop typing indicator
    typingTimeoutRef.current = setTimeout(() => {
      setIsTypingUser(false);
      typingTimeoutRef.current = null;
    }, 2000);
  }, []);

  const stopTyping = useCallback(() => {
    setIsTypingUser(false);
    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current);
      typingTimeoutRef.current = null;
    }
  }, []);

  const canSendMessage = useCallback((minDelay: number = 500): boolean => {
    const now = Date.now();
    const timeSinceLastMessage = now - lastMessageTime.current;
    return timeSinceLastMessage >= minDelay;
  }, []);

  const recordMessageSent = useCallback(() => {
    lastMessageTime.current = Date.now();
    stopTyping();
  }, [stopTyping]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (typingTimeoutRef.current) {
        clearTimeout(typingTimeoutRef.current);
      }
    };
  }, []);

  return {
    isTypingUser,
    startTyping,
    stopTyping,
    canSendMessage,
    recordMessageSent,
  };
}
