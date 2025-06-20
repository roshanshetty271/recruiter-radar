"use client";

import React, {
  createContext,
  useContext,
  useReducer,
  useEffect,
  ReactNode,
} from "react";
import {
  SessionData,
  getOrCreateSession,
  updateSession,
  resetSession,
  getRemainingUploads,
  getRemainingMessages,
  isSessionExpired,
} from "../lib/session-manager";

// Session Actions
type SessionAction =
  | { type: "LOAD_SESSION" }
  | { type: "INCREMENT_UPLOAD" }
  | { type: "INCREMENT_MESSAGE" }
  | { type: "RESET_SESSION" }
  | { type: "SET_SESSION"; payload: SessionData };

// Session State
interface SessionState {
  session: SessionData;
  remainingUploads: number;
  remainingMessages: number;
  isLoading: boolean;
}

// Session Context Type
interface SessionContextType extends SessionState {
  incrementUpload: () => void;
  incrementMessage: () => void;
  resetSessionData: () => void;
}

// Session Reducer
function sessionReducer(
  state: SessionState,
  action: SessionAction
): SessionState {
  switch (action.type) {
    case "LOAD_SESSION": {
      const session = getOrCreateSession();

      // Check if expired and auto-reset
      if (isSessionExpired(session)) {
        const newSession = resetSession();
        return {
          session: newSession,
          remainingUploads: getRemainingUploads(newSession),
          remainingMessages: getRemainingMessages(newSession),
          isLoading: false,
        };
      }

      return {
        session,
        remainingUploads: getRemainingUploads(session),
        remainingMessages: getRemainingMessages(session),
        isLoading: false,
      };
    }

    case "INCREMENT_UPLOAD": {
      const updatedSession = updateSession(state.session, {
        uploadCount: state.session.uploadCount + 1,
      });

      return {
        ...state,
        session: updatedSession,
        remainingUploads: getRemainingUploads(updatedSession),
      };
    }

    case "INCREMENT_MESSAGE": {
      const updatedSession = updateSession(state.session, {
        messageCount: state.session.messageCount + 1,
      });

      return {
        ...state,
        session: updatedSession,
        remainingMessages: getRemainingMessages(updatedSession),
      };
    }

    case "RESET_SESSION": {
      const newSession = resetSession();
      return {
        session: newSession,
        remainingUploads: getRemainingUploads(newSession),
        remainingMessages: getRemainingMessages(newSession),
        isLoading: false,
      };
    }

    case "SET_SESSION": {
      return {
        ...state,
        session: action.payload,
        remainingUploads: getRemainingUploads(action.payload),
        remainingMessages: getRemainingMessages(action.payload),
      };
    }

    default:
      return state;
  }
}

// Create Context
const SessionContext = createContext<SessionContextType | null>(null);

// Initial State
const initialState: SessionState = {
  session: {
    id: "",
    uploadCount: 0,
    messageCount: 0,
    createdAt: 0,
    expiresAt: 0,
  },
  remainingUploads: 10,
  remainingMessages: 10,
  isLoading: true,
};

// Session Provider Component
export function SessionProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(sessionReducer, initialState);

  // Load session on mount
  useEffect(() => {
    dispatch({ type: "LOAD_SESSION" });
  }, []);

  // Actions
  const incrementUpload = () => {
    if (state.remainingUploads > 0) {
      dispatch({ type: "INCREMENT_UPLOAD" });
    }
  };

  const incrementMessage = () => {
    if (state.remainingMessages > 0) {
      dispatch({ type: "INCREMENT_MESSAGE" });
    }
  };

  const resetSessionData = () => {
    dispatch({ type: "RESET_SESSION" });
  };

  const contextValue: SessionContextType = {
    ...state,
    incrementUpload,
    incrementMessage,
    resetSessionData,
  };

  return (
    <SessionContext.Provider value={contextValue}>
      {children}
    </SessionContext.Provider>
  );
}

// useSession Hook
export function useSession(): SessionContextType {
  const context = useContext(SessionContext);

  if (!context) {
    throw new Error("useSession must be used within a SessionProvider");
  }

  return context;
}
