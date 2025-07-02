/**
 * React Query hooks for response generation management
 * 
 * Provides data fetching, caching, and mutation hooks for AI response operations
 * with automatic background refetching and optimistic updates.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiService, GeneratedResponse } from '../services/api';
import { useApp } from '../contexts/AppContext';

// Query keys for consistent caching
export const responseQueryKeys = {
  all: ['responses'] as const,
  lists: () => [...responseQueryKeys.all, 'list'] as const,
  list: (filters: any) => [...responseQueryKeys.lists(), filters] as const,
  details: () => [...responseQueryKeys.all, 'detail'] as const,
  detail: (id: string) => [...responseQueryKeys.details(), id] as const,
};

interface UseResponsesOptions {
  page?: number;
  pageSize?: number;
  status?: string;
  enabled?: boolean;
}

// Hook for fetching responses with pagination and filtering
export const useResponses = (options: UseResponsesOptions = {}) => {
  const { addNotification } = useApp();
  
  return useQuery({
    queryKey: responseQueryKeys.list(options),
    queryFn: () => apiService.getResponses({
      page: options.page || 1,
      page_size: options.pageSize || 20,
      status: options.status,
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
        title: 'Failed to load responses',
        message: error?.response?.data?.detail || 'An error occurred while loading responses',
      });
    },
  });
};

// Hook for generating AI responses
export const useGenerateResponse = () => {
  const queryClient = useQueryClient();
  const { addNotification, updateTaskStatus } = useApp();
  
  return useMutation({
    mutationFn: ({ emailId, options }: { 
      emailId: string; 
      options?: {
        use_rag?: boolean;
        max_context_length?: number;
        custom_instructions?: string;
      }
    }) => apiService.generateResponse(emailId, options),
    onSuccess: (data, variables) => {
      addNotification({
        type: 'info',
        title: 'Response generation started',
        message: `AI response generation in progress (${data.task_id.slice(0, 8)}...)`,
      });
      
      // Start polling for task status
      const pollTask = async () => {
        try {
          const status = await apiService.getTaskStatus(data.task_id);
          updateTaskStatus(status);
          
          if (status.status === 'SUCCESS') {
            // Invalidate response queries to refresh generated responses
            queryClient.invalidateQueries({ queryKey: responseQueryKeys.all });
            
            addNotification({
              type: 'success',
              title: 'Response generated',
              message: 'AI response has been generated successfully',
            });
          } else if (status.status === 'PENDING' || status.status === 'STARTED') {
            // Continue polling
            setTimeout(pollTask, 2000);
          } else if (status.status === 'FAILURE') {
            addNotification({
              type: 'error',
              title: 'Response generation failed',
              message: status.error || 'Failed to generate AI response',
            });
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
        title: 'Failed to start response generation',
        message: error?.response?.data?.detail || 'Failed to start AI response generation',
      });
    },
  });
};

// Hook for generating RAG-enhanced responses
export const useGenerateRagResponse = () => {
  const queryClient = useQueryClient();
  const { addNotification, updateTaskStatus } = useApp();
  
  return useMutation({
    mutationFn: ({ emailId, customInstructions, maxContextLength }: { 
      emailId: string; 
      customInstructions?: string;
      maxContextLength?: number;
    }) => apiService.generateRagResponse(emailId, customInstructions, maxContextLength),
    onSuccess: (data, variables) => {
      addNotification({
        type: 'info',
        title: 'RAG response generation started',
        message: `Enhanced AI response generation in progress (${data.task_id.slice(0, 8)}...)`,
      });
      
      // Start polling for task status
      const pollTask = async () => {
        try {
          const status = await apiService.getTaskStatus(data.task_id);
          updateTaskStatus(status);
          
          if (status.status === 'SUCCESS') {
            queryClient.invalidateQueries({ queryKey: responseQueryKeys.all });
            
            addNotification({
              type: 'success',
              title: 'Enhanced response generated',
              message: 'RAG-enhanced AI response has been generated successfully',
            });
          } else if (status.status === 'PENDING' || status.status === 'STARTED') {
            setTimeout(pollTask, 2000);
          } else if (status.status === 'FAILURE') {
            addNotification({
              type: 'error',
              title: 'RAG response generation failed',
              message: status.error || 'Failed to generate enhanced AI response',
            });
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
        title: 'Failed to start RAG response generation',
        message: error?.response?.data?.detail || 'Failed to start enhanced response generation',
      });
    },
  });
};

// Hook for updating response status
export const useUpdateResponseStatus = () => {
  const queryClient = useQueryClient();
  const { addNotification } = useApp();
  
  return useMutation({
    mutationFn: ({ responseId, status }: { responseId: string; status: string }) =>
      apiService.updateResponseStatus(responseId, status),
    onMutate: async ({ responseId, status }) => {
      // Cancel any outgoing refetches
      await queryClient.cancelQueries({ queryKey: responseQueryKeys.all });
      
      // Optimistically update response status in all queries
      queryClient.setQueriesData(
        { queryKey: responseQueryKeys.lists() },
        (old: any) => {
          if (!old) return old;
          return {
            ...old,
            responses: old.responses.map((response: GeneratedResponse) =>
              response.id === responseId ? { ...response, status } : response
            ),
          };
        }
      );
    },
    onSuccess: (data, variables) => {
      addNotification({
        type: 'success',
        title: 'Response status updated',
        message: `Response marked as ${variables.status}`,
      });
    },
    onError: (error: any, variables) => {
      addNotification({
        type: 'error',
        title: 'Failed to update response status',
        message: error?.response?.data?.detail || 'An error occurred while updating response status',
      });
    },
    onSettled: () => {
      // Always refetch after error or success
      queryClient.invalidateQueries({ queryKey: responseQueryKeys.all });
    },
  });
};

// Hook for response analysis and scoring
export const useAnalyzeWritingStyle = () => {
  const { addNotification, updateTaskStatus } = useApp();
  
  return useMutation({
    mutationFn: ({ userId, emailIds }: { userId: string; emailIds?: string[] }) =>
      apiService.analyzeWritingStyle(userId, emailIds),
    onSuccess: (data, variables) => {
      if (data.task_id) {
        addNotification({
          type: 'info',
          title: 'Writing style analysis started',
          message: `Analyzing writing style patterns (${data.task_id.slice(0, 8)}...)`,
        });
        
        // Start polling for task status
        const pollTask = async () => {
          try {
            const status = await apiService.getTaskStatus(data.task_id);
            updateTaskStatus(status);
            
            if (status.status === 'SUCCESS') {
              addNotification({
                type: 'success',
                title: 'Writing style analysis completed',
                message: 'Your writing style analysis is ready',
              });
            } else if (status.status === 'PENDING' || status.status === 'STARTED') {
              setTimeout(pollTask, 2000);
            } else if (status.status === 'FAILURE') {
              addNotification({
                type: 'error',
                title: 'Writing style analysis failed',
                message: status.error || 'Failed to analyze writing style',
              });
            }
          } catch (error) {
            console.error('Error polling task status:', error);
          }
        };
        
        setTimeout(pollTask, 1000);
      } else {
        // Immediate result
        addNotification({
          type: 'success',
          title: 'Writing style analysis completed',
          message: 'Writing style analysis has been completed',
        });
      }
    },
    onError: (error: any) => {
      addNotification({
        type: 'error',
        title: 'Failed to analyze writing style',
        message: error?.response?.data?.detail || 'Failed to start writing style analysis',
      });
    },
  });
};

// Hook for comprehensive analysis
export const useComprehensiveAnalysis = () => {
  const { addNotification, updateTaskStatus } = useApp();
  
  return useMutation({
    mutationFn: ({ userId, emailIds, includeRecommendations }: { 
      userId: string; 
      emailIds?: string[];
      includeRecommendations?: boolean;
    }) => apiService.comprehensiveAnalysis(userId, emailIds, includeRecommendations),
    onSuccess: (data, variables) => {
      if (data.task_id) {
        addNotification({
          type: 'info',
          title: 'Comprehensive analysis started',
          message: `Running comprehensive communication analysis (${data.task_id.slice(0, 8)}...)`,
        });
        
        // Start polling for task status
        const pollTask = async () => {
          try {
            const status = await apiService.getTaskStatus(data.task_id);
            updateTaskStatus(status);
            
            if (status.status === 'SUCCESS') {
              addNotification({
                type: 'success',
                title: 'Comprehensive analysis completed',
                message: 'Your comprehensive communication analysis is ready',
              });
            } else if (status.status === 'PENDING' || status.status === 'STARTED') {
              setTimeout(pollTask, 2000);
            } else if (status.status === 'FAILURE') {
              addNotification({
                type: 'error',
                title: 'Comprehensive analysis failed',
                message: status.error || 'Failed to complete comprehensive analysis',
              });
            }
          } catch (error) {
            console.error('Error polling task status:', error);
          }
        };
        
        setTimeout(pollTask, 1000);
      } else {
        // Immediate result
        addNotification({
          type: 'success',
          title: 'Comprehensive analysis completed',
          message: 'Comprehensive analysis has been completed',
        });
      }
    },
    onError: (error: any) => {
      addNotification({
        type: 'error',
        title: 'Failed to start comprehensive analysis',
        message: error?.response?.data?.detail || 'Failed to start comprehensive analysis',
      });
    },
  });
};

export default {
  useResponses,
  useGenerateResponse,
  useGenerateRagResponse,
  useUpdateResponseStatus,
  useAnalyzeWritingStyle,
  useComprehensiveAnalysis,
};