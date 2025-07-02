/**
 * React Query hooks for email management
 * 
 * Provides data fetching, caching, and mutation hooks for email operations
 * with automatic background refetching and optimistic updates.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiService, EmailMessage } from '../services/api';
import { useApp } from '../contexts/AppContext';
import { toast } from 'sonner';

// Query keys for consistent caching
export const emailQueryKeys = {
  all: ['emails'] as const,
  lists: () => [...emailQueryKeys.all, 'list'] as const,
  list: (filters: any) => [...emailQueryKeys.lists(), filters] as const,
  details: () => [...emailQueryKeys.all, 'detail'] as const,
  detail: (id: string) => [...emailQueryKeys.details(), id] as const,
};

interface UseEmailsOptions {
  page?: number;
  pageSize?: number;
  sender?: string;
  isAnalyzed?: boolean;
  priority?: string;
  enabled?: boolean;
}

// Hook for fetching emails with pagination and filtering
export const useEmails = (options: UseEmailsOptions = {}) => {
  const { addNotification } = useApp();
  
  return useQuery({
    queryKey: emailQueryKeys.list(options),
    queryFn: () => apiService.getEmails({
      page: options.page || 1,
      page_size: options.pageSize || 20,
      sender: options.sender,
      is_analyzed: options.isAnalyzed,
      priority: options.priority,
    }),
    enabled: options.enabled !== false,
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes
    refetchOnWindowFocus: false,
    retry: (failureCount, error: any) => {
      if (error?.response?.status === 401) return false;
      return failureCount < 3;
    },
    onError: (error: any) => {
      addNotification({
        type: 'error',
        title: 'Failed to load emails',
        message: error?.response?.data?.detail || 'An error occurred while loading emails',
      });
    },
  });
};

// Hook for fetching a single email
export const useEmail = (emailId: string, enabled: boolean = true) => {
  const { addNotification } = useApp();
  
  return useQuery({
    queryKey: emailQueryKeys.detail(emailId),
    queryFn: () => apiService.getEmail(emailId),
    enabled: enabled && !!emailId,
    staleTime: 10 * 60 * 1000, // 10 minutes
    gcTime: 30 * 60 * 1000, // 30 minutes
    onError: (error: any) => {
      addNotification({
        type: 'error',
        title: 'Failed to load email',
        message: error?.response?.data?.detail || 'An error occurred while loading email details',
      });
    },
  });
};

// Hook for fetching emails from Gmail
export const useFetchEmails = () => {
  const queryClient = useQueryClient();
  const { addNotification } = useApp();
  
  return useMutation({
    mutationFn: ({ userId, limit }: { userId: string; limit?: number }) =>
      apiService.fetchEmails(userId, limit),
    onSuccess: (data) => {
      // Invalidate and refetch emails
      queryClient.invalidateQueries({ queryKey: emailQueryKeys.all });
      
      addNotification({
        type: 'success',
        title: 'Emails fetched successfully',
        message: `Fetched ${data.fetched_count || 0} new emails from Gmail`,
      });
    },
    onError: (error: any) => {
      addNotification({
        type: 'error',
        title: 'Failed to fetch emails',
        message: error?.response?.data?.detail || 'Failed to fetch emails from Gmail',
      });
    },
  });
};

// Hook for updating email properties
export const useUpdateEmail = () => {
  const queryClient = useQueryClient();
  const { addNotification } = useApp();
  
  return useMutation({
    mutationFn: ({ emailId, updates }: { emailId: string; updates: Partial<EmailMessage> }) =>
      apiService.updateEmail(emailId, updates),
    onMutate: async ({ emailId, updates }) => {
      // Cancel any outgoing refetches
      await queryClient.cancelQueries({ queryKey: emailQueryKeys.detail(emailId) });
      
      // Snapshot the previous value
      const previousEmail = queryClient.getQueryData(emailQueryKeys.detail(emailId));
      
      // Optimistically update to the new value
      queryClient.setQueryData(emailQueryKeys.detail(emailId), (old: any) => ({
        ...old,
        ...updates,
      }));
      
      // Update email in lists
      queryClient.setQueriesData(
        { queryKey: emailQueryKeys.lists() },
        (old: any) => {
          if (!old) return old;
          return {
            ...old,
            emails: old.emails.map((email: EmailMessage) =>
              email.id === emailId ? { ...email, ...updates } : email
            ),
          };
        }
      );
      
      return { previousEmail };
    },
    onError: (error: any, variables, context) => {
      // Rollback to previous value on error
      if (context?.previousEmail) {
        queryClient.setQueryData(emailQueryKeys.detail(variables.emailId), context.previousEmail);
      }
      
      addNotification({
        type: 'error',
        title: 'Failed to update email',
        message: error?.response?.data?.detail || 'An error occurred while updating the email',
      });
    },
    onSettled: (data, error, variables) => {
      // Always refetch after error or success
      queryClient.invalidateQueries({ queryKey: emailQueryKeys.detail(variables.emailId) });
      queryClient.invalidateQueries({ queryKey: emailQueryKeys.lists() });
    },
    onSuccess: () => {
      addNotification({
        type: 'success',
        title: 'Email updated',
        message: 'Email has been updated successfully',
      });
    },
  });
};

// Hook for marking emails as read/unread
export const useMarkEmailRead = () => {
  const updateEmail = useUpdateEmail();
  
  return {
    markAsRead: (emailId: string) => updateEmail.mutate({
      emailId,
      updates: { is_read: true }
    }),
    markAsUnread: (emailId: string) => updateEmail.mutate({
      emailId,
      updates: { is_read: false }
    }),
    isLoading: updateEmail.isPending,
  };
};

// Hook for starring/unstarring emails
export const useStarEmail = () => {
  const updateEmail = useUpdateEmail();
  
  return {
    star: (emailId: string) => updateEmail.mutate({
      emailId,
      updates: { is_starred: true }
    }),
    unstar: (emailId: string) => updateEmail.mutate({
      emailId,
      updates: { is_starred: false }
    }),
    isLoading: updateEmail.isPending,
  };
};

// Hook for submitting email analysis tasks
export const useAnalyzeEmail = () => {
  const queryClient = useQueryClient();
  const { addNotification, updateTaskStatus } = useApp();
  
  return useMutation({
    mutationFn: ({ emailId, userId, priority }: { 
      emailId: string; 
      userId: string; 
      priority?: string 
    }) => apiService.submitEmailAnalysis(emailId, userId, priority),
    onSuccess: (data, variables) => {
      addNotification({
        type: 'info',
        title: 'Analysis started',
        message: `Email analysis task submitted (${data.task_id.slice(0, 8)}...)`,
      });
      
      // Start polling for task status
      const pollTask = async () => {
        try {
          const status = await apiService.getTaskStatus(data.task_id);
          updateTaskStatus(status);
          
          if (status.status === 'SUCCESS') {
            // Invalidate email queries to refresh analysis results
            queryClient.invalidateQueries({ queryKey: emailQueryKeys.detail(variables.emailId) });
            queryClient.invalidateQueries({ queryKey: emailQueryKeys.lists() });
          } else if (status.status === 'PENDING' || status.status === 'STARTED') {
            // Continue polling
            setTimeout(pollTask, 2000);
          }
        } catch (error) {
          console.error('Error polling task status:', error);
        }
      };
      
      setTimeout(pollTask, 1000);
    },
    onError: (error: any) => {
      addNotification({
        type: 'error',
        title: 'Failed to start analysis',
        message: error?.response?.data?.detail || 'Failed to submit email for analysis',
      });
    },
  });
};

// Hook for batch operations on emails
export const useBatchEmailOperations = () => {
  const queryClient = useQueryClient();
  const { addNotification } = useApp();
  
  const batchAnalyze = useMutation({
    mutationFn: ({ emailIds, userId }: { emailIds: string[]; userId: string }) =>
      apiService.submitBatchAnalysis(emailIds, userId),
    onSuccess: (data, variables) => {
      addNotification({
        type: 'info',
        title: 'Batch analysis started',
        message: `Analyzing ${variables.emailIds.length} emails (${data.task_id.slice(0, 8)}...)`,
      });
    },
    onError: (error: any) => {
      addNotification({
        type: 'error',
        title: 'Batch analysis failed',
        message: error?.response?.data?.detail || 'Failed to submit emails for batch analysis',
      });
    },
  });
  
  const batchVectorize = useMutation({
    mutationFn: ({ emailIds, userId }: { emailIds: string[]; userId: string }) =>
      apiService.submitVectorization(emailIds, userId),
    onSuccess: (data, variables) => {
      addNotification({
        type: 'info',
        title: 'Vectorization started',
        message: `Vectorizing ${variables.emailIds.length} emails (${data.task_id.slice(0, 8)}...)`,
      });
    },
    onError: (error: any) => {
      addNotification({
        type: 'error',
        title: 'Vectorization failed',
        message: error?.response?.data?.detail || 'Failed to submit emails for vectorization',
      });
    },
  });
  
  const batchMarkRead = useMutation({
    mutationFn: async ({ emailIds, isRead }: { emailIds: string[]; isRead: boolean }) => {
      // Execute updates in parallel
      await Promise.all(
        emailIds.map(emailId => 
          apiService.updateEmail(emailId, { is_read: isRead })
        )
      );
    },
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({ queryKey: emailQueryKeys.lists() });
      
      addNotification({
        type: 'success',
        title: 'Emails updated',
        message: `Marked ${variables.emailIds.length} emails as ${variables.isRead ? 'read' : 'unread'}`,
      });
    },
    onError: (error: any) => {
      addNotification({
        type: 'error',
        title: 'Batch update failed',
        message: 'Failed to update emails',
      });
    },
  });
  
  return {
    batchAnalyze: batchAnalyze.mutate,
    batchVectorize: batchVectorize.mutate,
    batchMarkRead: batchMarkRead.mutate,
    isAnalyzing: batchAnalyze.isPending,
    isVectorizing: batchVectorize.isPending,
    isUpdating: batchMarkRead.isPending,
  };
};

// Hook for email search and filtering
export const useEmailSearch = () => {
  const queryClient = useQueryClient();
  
  const searchEmails = (query: string, filters?: any) => {
    return queryClient.fetchQuery({
      queryKey: emailQueryKeys.list({ ...filters, search: query }),
      queryFn: () => apiService.getEmails({ ...filters, search: query }),
      staleTime: 1 * 60 * 1000, // 1 minute for search results
    });
  };
  
  const vectorSearch = useMutation({
    mutationFn: ({ query, userId, nResults, similarityThreshold }: {
      query: string;
      userId: string;
      nResults?: number;
      similarityThreshold?: number;
    }) => apiService.searchVectors(query, userId, nResults, similarityThreshold),
  });
  
  return {
    searchEmails,
    vectorSearch: vectorSearch.mutate,
    vectorSearchData: vectorSearch.data,
    isVectorSearching: vectorSearch.isPending,
  };
};

export default {
  useEmails,
  useEmail,
  useFetchEmails,
  useUpdateEmail,
  useMarkEmailRead,
  useStarEmail,
  useAnalyzeEmail,
  useBatchEmailOperations,
  useEmailSearch,
};