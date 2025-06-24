"use client";

import React, {
  createContext,
  useContext,
  useReducer,
  useEffect,
  ReactNode,
  useState,
} from "react";
import { api } from "../lib/api";
import type { SessionStatus } from "../lib/types";

// Session actions
type SessionAction =
  | { type: "INITIALIZE"; payload: SessionStatus }
  | { type: "UPDATE_STATUS"; payload: SessionStatus }
  | { type: "SET_LOADING"; payload: boolean }
  | { type: "SET_ERROR"; payload: string | null }
  | { type: "INCREMENT_UPLOAD" }
  | { type: "INCREMENT_MESSAGE" };

// Session state
interface SessionState {
  session: SessionStatus | null;
  isLoading: boolean;
  error: string | null;
}

// Session context value
interface SessionContextValue extends SessionState {
  refreshSession: () => Promise<void>;
  getRemainingUploads: () => number;
  getRemainingMessages: () => number;
  canUpload: () => boolean;
  canSendMessage: () => boolean;
  incrementUpload: () => void;
  incrementMessage: () => void;
}

// Create context
const SessionContext = createContext<SessionContextValue | undefined>(
  undefined
);

// Session reducer
function sessionReducer(
  state: SessionState,
  action: SessionAction
): SessionState {
  switch (action.type) {
    case "INITIALIZE":
    case "UPDATE_STATUS":
      return {
        ...state,
        session: action.payload,
        isLoading: false,
        error: null,
      };

    case "SET_LOADING":
      return {
        ...state,
        isLoading: action.payload,
      };

    case "SET_ERROR":
      return {
        ...state,
        error: action.payload,
        isLoading: false,
      };

    case "INCREMENT_UPLOAD":
      return {
        ...state,
        session: state.session
          ? {
              ...state.session,
              upload_count: state.session.upload_count + 1,
            }
          : null,
      };

    case "INCREMENT_MESSAGE":
      return {
        ...state,
        session: state.session
          ? {
              ...state.session,
              message_count: state.session.message_count + 1,
            }
          : null,
      };

    default:
      return state;
  }
}

// Create initial state (SSR-safe)
function createInitialState(): SessionState {
  return {
    session: null,
    isLoading: true,
    error: null,
  };
}

// Session provider props
interface SessionProviderProps {
  children: ReactNode;
}

// Session provider component
export function SessionProvider({ children }: SessionProviderProps) {
  const [state, dispatch] = useReducer(sessionReducer, createInitialState());

  // Initialize session on mount
  useEffect(() => {
    const initializeSession = async () => {
      try {
        dispatch({ type: "SET_LOADING", payload: true });
        const sessionData = await api.getOrCreateSession();
        dispatch({ type: "INITIALIZE", payload: sessionData });
      } catch (error) {
        console.error("Failed to initialize session:", error);
        dispatch({
          type: "SET_ERROR",
          payload:
            error instanceof Error
              ? error.message
              : "Session initialization failed",
        });
      }
    };

    initializeSession();
  }, []);

  // Refresh session status
  const refreshSession = async () => {
    if (!state.session) return;

    try {
      const sessionData = await api.getSessionStatus();
      dispatch({ type: "UPDATE_STATUS", payload: sessionData });
    } catch (error) {
      console.error("Failed to refresh session:", error);
      dispatch({
        type: "SET_ERROR",
        payload:
          error instanceof Error ? error.message : "Failed to refresh session",
      });
    }
  };

  // Helper functions
  const getRemainingUploads = (): number => {
    if (!state.session) return 0;
    return Math.max(0, state.session.max_uploads - state.session.upload_count);
  };

  const getRemainingMessages = (): number => {
    if (!state.session) return 0;
    return Math.max(
      0,
      state.session.max_messages - state.session.message_count
    );
  };

  const canUpload = (): boolean => {
    return getRemainingUploads() > 0;
  };

  const canSendMessage = (): boolean => {
    return getRemainingMessages() > 0;
  };

  const incrementUpload = (): void => {
    dispatch({ type: "INCREMENT_UPLOAD" });
  };

  const incrementMessage = (): void => {
    dispatch({ type: "INCREMENT_MESSAGE" });
  };

  const contextValue: SessionContextValue = {
    ...state,
    refreshSession,
    getRemainingUploads,
    getRemainingMessages,
    canUpload,
    canSendMessage,
    incrementUpload,
    incrementMessage,
  };

  return (
    <SessionContext.Provider value={contextValue}>
      {children}
    </SessionContext.Provider>
  );
}

// Hook to use session context
export function useSession(): SessionContextValue {
  const context = useContext(SessionContext);
  if (context === undefined) {
    throw new Error("useSession must be used within a SessionProvider");
  }
  return context;
}
