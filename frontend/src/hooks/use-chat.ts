import { useState, useCallback, useRef, useEffect } from "react";
import { useSession } from "@/contexts/SessionContext";
import { apiService } from "@/services/apiService";
import { FrontendCandidate } from "@/services/types";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  candidates?: FrontendCandidate[];
  timestamp: Date;
}

export interface UseChatReturn {
  messages: ChatMessage[];
  isLoading: boolean;
  error: string | null;
  sendMessage: (content: string) => Promise<void>;
  clearMessages: () => void;
  clearError: () => void;
}

// Generate unique message ID
function generateMessageId(): string {
  return `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

// Chat message storage key
const CHAT_STORAGE_KEY = "recruiter-radar-chat-messages";
const MAX_STORED_MESSAGES = 10;
const MESSAGE_EXPIRY_HOURS = 24;

// Load messages from localStorage
function loadStoredMessages(): ChatMessage[] {
  try {
    const stored = localStorage.getItem(CHAT_STORAGE_KEY);
    if (!stored) return [];

    const parsed = JSON.parse(stored);
    if (!Array.isArray(parsed)) return [];

    // Filter out expired messages
    const now = Date.now();
    const validMessages = parsed.filter((msg: any) => {
      const messageTime = new Date(msg.timestamp).getTime();
      const expiryTime = messageTime + MESSAGE_EXPIRY_HOURS * 60 * 60 * 1000;
      return now < expiryTime;
    });

    // Keep only the most recent messages
    return validMessages.slice(-MAX_STORED_MESSAGES).map((msg: any) => ({
      ...msg,
      timestamp: new Date(msg.timestamp),
    }));
  } catch (error) {
    console.error("Failed to load stored chat messages:", error);
    return [];
  }
}

// Save messages to localStorage
function saveMessages(messages: ChatMessage[]): void {
  try {
    const toStore = messages.slice(-MAX_STORED_MESSAGES).map((msg) => ({
      ...msg,
      timestamp: msg.timestamp.toISOString(),
    }));

    localStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(toStore));
  } catch (error) {
    console.error("Failed to save chat messages:", error);
  }
}

export function useChat(): UseChatReturn {
  const { session, canSendMessage, incrementMessage } = useSession();
  const [messages, setMessages] = useState<ChatMessage[]>(() =>
    loadStoredMessages()
  );
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Ref to track if component is mounted
  const isMountedRef = useRef(true);

  // Save messages to localStorage whenever they change
  useEffect(() => {
    saveMessages(messages);
  }, [messages]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  const sendMessage = useCallback(
    async (content: string) => {
      // Validate message limits
      if (!canSendMessage) {
        setError(
          "Message limit reached. You've used all 10 messages for this session."
        );
        return;
      }

      // Clear any previous errors
      setError(null);

      // Create user message
      const userMessage: ChatMessage = {
        id: generateMessageId(),
        role: "user",
        content: content.trim(),
        timestamp: new Date(),
      };

      // Add user message and set loading state
      setMessages((prev) => [...prev, userMessage]);
      setIsLoading(true);

      try {
        // Call API
        const response = await apiService.chat(content, session.id);

        // Check if component is still mounted
        if (!isMountedRef.current) return;

        // Create assistant message
        const assistantMessage: ChatMessage = {
          id: generateMessageId(),
          role: "assistant",
          content: response.ai_message,
          candidates: response.candidates,
          timestamp: new Date(),
        };

        // Add assistant message
        setMessages((prev) => [...prev, assistantMessage]);

        // Increment message count in session
        incrementMessage();
      } catch (err) {
        // Check if component is still mounted
        if (!isMountedRef.current) return;

        console.error("Chat error:", err);

        // Create error message
        const errorMessage: ChatMessage = {
          id: generateMessageId(),
          role: "assistant",
          content:
            "Sorry, I encountered an error processing your message. Please try again.",
          timestamp: new Date(),
        };

        setMessages((prev) => [...prev, errorMessage]);
        setError(err instanceof Error ? err.message : "Failed to send message");
      } finally {
        // Check if component is still mounted
        if (isMountedRef.current) {
          setIsLoading(false);
        }
      }
    },
    [canSendMessage, session.id, incrementMessage]
  );

  const clearMessages = useCallback(() => {
    setMessages([]);
    localStorage.removeItem(CHAT_STORAGE_KEY);
  }, []);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  return {
    messages,
    isLoading,
    error,
    sendMessage,
    clearMessages,
    clearError,
  };
}
