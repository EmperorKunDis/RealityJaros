/**
 * Application Context for AI Email Assistant
 * 
 * Provides global application state management including
 * email data, tasks, notifications, and system status.
 */

import React, { createContext, useContext, useReducer, useEffect, ReactNode } from 'react';
import { EmailMessage, GeneratedResponse, Client, TaskStatus } from '../services/api';
import { toast } from 'sonner';

// Application state interface
interface AppState {
  // Email management
  emails: EmailMessage[];
  selectedEmail: EmailMessage | null;
  emailsLoading: boolean;
  emailsError: string | null;
  
  // Response management
  responses: GeneratedResponse[];
  responsesLoading: boolean;
  responsesError: string | null;
  
  // Client management
  clients: Client[];
  clientsLoading: boolean;
  clientsError: string | null;
  
  // Background tasks
  activeTasks: Map<string, TaskStatus>;
  taskHistory: TaskStatus[];
  
  // System status
  systemHealth: {
    api: boolean;
    database: boolean;
    vectorDb: boolean;
    workers: boolean;
  };
  
  // UI state
  sidebarOpen: boolean;
  selectedView: 'emails' | 'responses' | 'analytics' | 'settings';
  notifications: Notification[];
}

interface Notification {
  id: string;
  type: 'info' | 'success' | 'warning' | 'error';
  title: string;
  message: string;
  timestamp: Date;
  read: boolean;
}

// Action types
type AppAction =
  | { type: 'SET_EMAILS'; payload: EmailMessage[] }
  | { type: 'ADD_EMAIL'; payload: EmailMessage }
  | { type: 'UPDATE_EMAIL'; payload: { id: string; updates: Partial<EmailMessage> } }
  | { type: 'SELECT_EMAIL'; payload: EmailMessage | null }
  | { type: 'SET_EMAILS_LOADING'; payload: boolean }
  | { type: 'SET_EMAILS_ERROR'; payload: string | null }
  
  | { type: 'SET_RESPONSES'; payload: GeneratedResponse[] }
  | { type: 'ADD_RESPONSE'; payload: GeneratedResponse }
  | { type: 'UPDATE_RESPONSE'; payload: { id: string; updates: Partial<GeneratedResponse> } }
  | { type: 'SET_RESPONSES_LOADING'; payload: boolean }
  | { type: 'SET_RESPONSES_ERROR'; payload: string | null }
  
  | { type: 'SET_CLIENTS'; payload: Client[] }
  | { type: 'ADD_CLIENT'; payload: Client }
  | { type: 'UPDATE_CLIENT'; payload: { id: string; updates: Partial<Client> } }
  | { type: 'SET_CLIENTS_LOADING'; payload: boolean }
  | { type: 'SET_CLIENTS_ERROR'; payload: string | null }
  
  | { type: 'ADD_TASK'; payload: TaskStatus }
  | { type: 'UPDATE_TASK'; payload: TaskStatus }
  | { type: 'REMOVE_TASK'; payload: string }
  | { type: 'CLEAR_COMPLETED_TASKS' }
  
  | { type: 'UPDATE_SYSTEM_HEALTH'; payload: Partial<AppState['systemHealth']> }
  
  | { type: 'TOGGLE_SIDEBAR' }
  | { type: 'SET_SELECTED_VIEW'; payload: AppState['selectedView'] }
  | { type: 'ADD_NOTIFICATION'; payload: Omit<Notification, 'id' | 'timestamp' | 'read'> }
  | { type: 'MARK_NOTIFICATION_READ'; payload: string }
  | { type: 'CLEAR_NOTIFICATIONS' };

// Initial state
const initialState: AppState = {
  emails: [],
  selectedEmail: null,
  emailsLoading: false,
  emailsError: null,
  
  responses: [],
  responsesLoading: false,
  responsesError: null,
  
  clients: [],
  clientsLoading: false,
  clientsError: null,
  
  activeTasks: new Map(),
  taskHistory: [],
  
  systemHealth: {
    api: false,
    database: false,
    vectorDb: false,
    workers: false,
  },
  
  sidebarOpen: true,
  selectedView: 'emails',
  notifications: [],
};

// Reducer function
function appReducer(state: AppState, action: AppAction): AppState {
  switch (action.type) {
    // Email actions
    case 'SET_EMAILS':
      return { ...state, emails: action.payload };
    
    case 'ADD_EMAIL':
      return { ...state, emails: [action.payload, ...state.emails] };
    
    case 'UPDATE_EMAIL':
      return {
        ...state,
        emails: state.emails.map(email =>
          email.id === action.payload.id
            ? { ...email, ...action.payload.updates }
            : email
        ),
        selectedEmail: state.selectedEmail?.id === action.payload.id
          ? { ...state.selectedEmail, ...action.payload.updates }
          : state.selectedEmail,
      };
    
    case 'SELECT_EMAIL':
      return { ...state, selectedEmail: action.payload };
    
    case 'SET_EMAILS_LOADING':
      return { ...state, emailsLoading: action.payload };
    
    case 'SET_EMAILS_ERROR':
      return { ...state, emailsError: action.payload };
    
    // Response actions
    case 'SET_RESPONSES':
      return { ...state, responses: action.payload };
    
    case 'ADD_RESPONSE':
      return { ...state, responses: [action.payload, ...state.responses] };
    
    case 'UPDATE_RESPONSE':
      return {
        ...state,
        responses: state.responses.map(response =>
          response.id === action.payload.id
            ? { ...response, ...action.payload.updates }
            : response
        ),
      };
    
    case 'SET_RESPONSES_LOADING':
      return { ...state, responsesLoading: action.payload };
    
    case 'SET_RESPONSES_ERROR':
      return { ...state, responsesError: action.payload };
    
    // Client actions
    case 'SET_CLIENTS':
      return { ...state, clients: action.payload };
    
    case 'ADD_CLIENT':
      return { ...state, clients: [action.payload, ...state.clients] };
    
    case 'UPDATE_CLIENT':
      return {
        ...state,
        clients: state.clients.map(client =>
          client.id === action.payload.id
            ? { ...client, ...action.payload.updates }
            : client
        ),
      };
    
    case 'SET_CLIENTS_LOADING':
      return { ...state, clientsLoading: action.payload };
    
    case 'SET_CLIENTS_ERROR':
      return { ...state, clientsError: action.payload };
    
    // Task actions
    case 'ADD_TASK':
      return {
        ...state,
        activeTasks: new Map(state.activeTasks.set(action.payload.task_id, action.payload)),
      };
    
    case 'UPDATE_TASK':
      const updatedTasks = new Map(state.activeTasks);
      updatedTasks.set(action.payload.task_id, action.payload);
      
      let newTaskHistory = state.taskHistory;
      if (action.payload.status === 'SUCCESS' || action.payload.status === 'FAILURE') {
        newTaskHistory = [action.payload, ...state.taskHistory.slice(0, 49)]; // Keep last 50
        updatedTasks.delete(action.payload.task_id);
      }
      
      return {
        ...state,
        activeTasks: updatedTasks,
        taskHistory: newTaskHistory,
      };
    
    case 'REMOVE_TASK':
      const tasksAfterRemoval = new Map(state.activeTasks);
      tasksAfterRemoval.delete(action.payload);
      return { ...state, activeTasks: tasksAfterRemoval };
    
    case 'CLEAR_COMPLETED_TASKS':
      return { ...state, taskHistory: [] };
    
    // System health actions
    case 'UPDATE_SYSTEM_HEALTH':
      return {
        ...state,
        systemHealth: { ...state.systemHealth, ...action.payload },
      };
    
    // UI actions
    case 'TOGGLE_SIDEBAR':
      return { ...state, sidebarOpen: !state.sidebarOpen };
    
    case 'SET_SELECTED_VIEW':
      return { ...state, selectedView: action.payload };
    
    case 'ADD_NOTIFICATION':
      const notification: Notification = {
        ...action.payload,
        id: Math.random().toString(36).substr(2, 9),
        timestamp: new Date(),
        read: false,
      };
      return {
        ...state,
        notifications: [notification, ...state.notifications.slice(0, 99)], // Keep last 100
      };
    
    case 'MARK_NOTIFICATION_READ':
      return {
        ...state,
        notifications: state.notifications.map(notif =>
          notif.id === action.payload ? { ...notif, read: true } : notif
        ),
      };
    
    case 'CLEAR_NOTIFICATIONS':
      return { ...state, notifications: [] };
    
    default:
      return state;
  }
}

// Context interface
interface AppContextValue {
  state: AppState;
  dispatch: React.Dispatch<AppAction>;
  
  // Convenience methods
  addNotification: (notification: Omit<Notification, 'id' | 'timestamp' | 'read'>) => void;
  selectEmail: (email: EmailMessage | null) => void;
  updateTaskStatus: (taskStatus: TaskStatus) => void;
  setSystemHealth: (health: Partial<AppState['systemHealth']>) => void;
}

const AppContext = createContext<AppContextValue | undefined>(undefined);

interface AppProviderProps {
  children: ReactNode;
}

export const AppProvider: React.FC<AppProviderProps> = ({ children }) => {
  const [state, dispatch] = useReducer(appReducer, initialState);

  // Convenience methods
  const addNotification = (notification: Omit<Notification, 'id' | 'timestamp' | 'read'>) => {
    dispatch({ type: 'ADD_NOTIFICATION', payload: notification });
    
    // Show toast notification
    const toastFn = {
      info: toast.info,
      success: toast.success,
      warning: toast.warning,
      error: toast.error,
    }[notification.type];
    
    toastFn(`${notification.title}: ${notification.message}`);
  };

  const selectEmail = (email: EmailMessage | null) => {
    dispatch({ type: 'SELECT_EMAIL', payload: email });
  };

  const updateTaskStatus = (taskStatus: TaskStatus) => {
    dispatch({ type: 'UPDATE_TASK', payload: taskStatus });
    
    // Add notification for completed tasks
    if (taskStatus.status === 'SUCCESS') {
      addNotification({
        type: 'success',
        title: 'Task Completed',
        message: `Task ${taskStatus.task_id.slice(0, 8)} completed successfully`,
      });
    } else if (taskStatus.status === 'FAILURE') {
      addNotification({
        type: 'error',
        title: 'Task Failed',
        message: `Task ${taskStatus.task_id.slice(0, 8)} failed: ${taskStatus.error || 'Unknown error'}`,
      });
    }
  };

  const setSystemHealth = (health: Partial<AppState['systemHealth']>) => {
    dispatch({ type: 'UPDATE_SYSTEM_HEALTH', payload: health });
  };

  // System health monitoring
  useEffect(() => {
    const checkSystemHealth = async () => {
      try {
        // This would check various system components
        // For now, we'll simulate health checks
        setSystemHealth({
          api: true,
          database: true,
          vectorDb: true,
          workers: true,
        });
      } catch (error) {
        console.error('System health check failed:', error);
        setSystemHealth({
          api: false,
          database: false,
          vectorDb: false,
          workers: false,
        });
      }
    };

    // Check system health every 30 seconds
    const healthCheckInterval = setInterval(checkSystemHealth, 30000);
    checkSystemHealth(); // Initial check

    return () => clearInterval(healthCheckInterval);
  }, []);

  const contextValue: AppContextValue = {
    state,
    dispatch,
    addNotification,
    selectEmail,
    updateTaskStatus,
    setSystemHealth,
  };

  return (
    <AppContext.Provider value={contextValue}>
      {children}
    </AppContext.Provider>
  );
};

export const useApp = (): AppContextValue => {
  const context = useContext(AppContext);
  if (context === undefined) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
};

// Convenience hooks
export const useEmails = () => {
  const { state, dispatch } = useApp();
  return {
    emails: state.emails,
    selectedEmail: state.selectedEmail,
    loading: state.emailsLoading,
    error: state.emailsError,
    setEmails: (emails: EmailMessage[]) => dispatch({ type: 'SET_EMAILS', payload: emails }),
    addEmail: (email: EmailMessage) => dispatch({ type: 'ADD_EMAIL', payload: email }),
    updateEmail: (id: string, updates: Partial<EmailMessage>) => 
      dispatch({ type: 'UPDATE_EMAIL', payload: { id, updates } }),
    selectEmail: (email: EmailMessage | null) => dispatch({ type: 'SELECT_EMAIL', payload: email }),
    setLoading: (loading: boolean) => dispatch({ type: 'SET_EMAILS_LOADING', payload: loading }),
    setError: (error: string | null) => dispatch({ type: 'SET_EMAILS_ERROR', payload: error }),
  };
};

export const useResponses = () => {
  const { state, dispatch } = useApp();
  return {
    responses: state.responses,
    loading: state.responsesLoading,
    error: state.responsesError,
    setResponses: (responses: GeneratedResponse[]) => 
      dispatch({ type: 'SET_RESPONSES', payload: responses }),
    addResponse: (response: GeneratedResponse) => 
      dispatch({ type: 'ADD_RESPONSE', payload: response }),
    updateResponse: (id: string, updates: Partial<GeneratedResponse>) => 
      dispatch({ type: 'UPDATE_RESPONSE', payload: { id, updates } }),
    setLoading: (loading: boolean) => dispatch({ type: 'SET_RESPONSES_LOADING', payload: loading }),
    setError: (error: string | null) => dispatch({ type: 'SET_RESPONSES_ERROR', payload: error }),
  };
};

export const useClients = () => {
  const { state, dispatch } = useApp();
  return {
    clients: state.clients,
    loading: state.clientsLoading,
    error: state.clientsError,
    setClients: (clients: Client[]) => dispatch({ type: 'SET_CLIENTS', payload: clients }),
    addClient: (client: Client) => dispatch({ type: 'ADD_CLIENT', payload: client }),
    updateClient: (id: string, updates: Partial<Client>) => 
      dispatch({ type: 'UPDATE_CLIENT', payload: { id, updates } }),
    setLoading: (loading: boolean) => dispatch({ type: 'SET_CLIENTS_LOADING', payload: loading }),
    setError: (error: string | null) => dispatch({ type: 'SET_CLIENTS_ERROR', payload: error }),
  };
};

export const useTasks = () => {
  const { state, dispatch, updateTaskStatus } = useApp();
  return {
    activeTasks: Array.from(state.activeTasks.values()),
    taskHistory: state.taskHistory,
    addTask: (task: TaskStatus) => dispatch({ type: 'ADD_TASK', payload: task }),
    updateTask: updateTaskStatus,
    removeTask: (taskId: string) => dispatch({ type: 'REMOVE_TASK', payload: taskId }),
    clearHistory: () => dispatch({ type: 'CLEAR_COMPLETED_TASKS' }),
  };
};

export default AppContext;