/**
 * React Query hooks for client management
 * 
 * Provides data fetching, caching, and mutation hooks for client operations
 * with automatic background refetching and analytics capabilities.
 */

import React from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiService, Client } from '../services/api';
import { useApp } from '../contexts/AppContext';

// Query keys for consistent caching
export const clientQueryKeys = {
  all: ['clients'] as const,
  lists: () => [...clientQueryKeys.all, 'list'] as const,
  list: (filters: any) => [...clientQueryKeys.lists(), filters] as const,
  details: () => [...clientQueryKeys.all, 'detail'] as const,
  detail: (id: string) => [...clientQueryKeys.details(), id] as const,
  analytics: () => [...clientQueryKeys.all, 'analytics'] as const,
  analyticsData: (userId: string, timeframe: string) => [...clientQueryKeys.analytics(), userId, timeframe] as const,
};

interface UseClientsOptions {
  page?: number;
  pageSize?: number;
  businessCategory?: string;
  relationshipStrengthMin?: number;
  enabled?: boolean;
}

// Hook for fetching clients with pagination and filtering
export const useClients = (options: UseClientsOptions = {}) => {
  const { addNotification } = useApp();
  
  return useQuery({
    queryKey: clientQueryKeys.list(options),
    queryFn: () => apiService.getClients({
      page: options.page || 1,
      page_size: options.pageSize || 20,
      business_category: options.businessCategory,
      relationship_strength_min: options.relationshipStrengthMin,
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
        title: 'Failed to load clients',
        message: error?.response?.data?.detail || 'An error occurred while loading clients',
      });
    },
  });
};

// Hook for fetching a single client
export const useClient = (clientId: string, enabled: boolean = true) => {
  const { addNotification } = useApp();
  
  return useQuery({
    queryKey: clientQueryKeys.detail(clientId),
    queryFn: () => apiService.getClient(clientId),
    enabled: enabled && !!clientId,
    staleTime: 10 * 60 * 1000, // 10 minutes
    gcTime: 30 * 60 * 1000, // 30 minutes
    onError: (error: any) => {
      addNotification({
        type: 'error',
        title: 'Failed to load client',
        message: error?.response?.data?.detail || 'An error occurred while loading client details',
      });
    },
  });
};

// Hook for analyzing client communication patterns
export const useAnalyzeClient = () => {
  const queryClient = useQueryClient();
  const { addNotification, updateTaskStatus } = useApp();
  
  return useMutation({
    mutationFn: ({ userId, clientEmail }: { userId: string; clientEmail: string }) =>
      apiService.analyzeClient(userId, clientEmail),
    onSuccess: (data, variables) => {
      if (data.task_id) {
        addNotification({
          type: 'info',
          title: 'Client analysis started',
          message: `Analyzing communication patterns for ${variables.clientEmail} (${data.task_id.slice(0, 8)}...)`,
        });
        
        // Start polling for task status
        const pollTask = async () => {
          try {
            const status = await apiService.getTaskStatus(data.task_id);
            updateTaskStatus(status);
            
            if (status.status === 'SUCCESS') {
              // Invalidate client queries to refresh analysis results
              queryClient.invalidateQueries({ queryKey: clientQueryKeys.all });
              
              addNotification({
                type: 'success',
                title: 'Client analysis completed',
                message: `Analysis for ${variables.clientEmail} is ready`,
              });
            } else if (status.status === 'PENDING' || status.status === 'STARTED') {
              // Continue polling
              setTimeout(pollTask, 2000);
            } else if (status.status === 'FAILURE') {
              addNotification({
                type: 'error',
                title: 'Client analysis failed',
                message: status.error || `Failed to analyze ${variables.clientEmail}`,
              });
            }
          } catch (error) {
            console.error('Error polling task status:', error);
          }
        };
        
        setTimeout(pollTask, 1000);
      } else {
        // Immediate result
        queryClient.invalidateQueries({ queryKey: clientQueryKeys.all });
        
        addNotification({
          type: 'success',
          title: 'Client analysis completed',
          message: `Analysis for ${variables.clientEmail} has been completed`,
        });
      }
    },
    onError: (error: any, variables) => {
      addNotification({
        type: 'error',
        title: 'Failed to analyze client',
        message: error?.response?.data?.detail || `Failed to start analysis for ${variables.clientEmail}`,
      });
    },
  });
};

// Hook for fetching client analytics
export const useClientAnalytics = (userId: string, timeframe: string = '30_days', enabled: boolean = true) => {
  const { addNotification } = useApp();
  
  return useQuery({
    queryKey: clientQueryKeys.analyticsData(userId, timeframe),
    queryFn: () => apiService.getClientAnalytics(userId, timeframe),
    enabled: enabled && !!userId,
    staleTime: 10 * 60 * 1000, // 10 minutes
    gcTime: 30 * 60 * 1000, // 30 minutes
    refetchOnWindowFocus: false,
    onError: (error: any) => {
      addNotification({
        type: 'error',
        title: 'Failed to load client analytics',
        message: error?.response?.data?.detail || 'An error occurred while loading client analytics',
      });
    },
  });
};

// Hook for fetching communication patterns
export const useCommunicationPatterns = (
  userId: string, 
  timeframe: string = '30_days', 
  patternType: string = 'all',
  enabled: boolean = true
) => {
  const { addNotification } = useApp();
  
  return useQuery({
    queryKey: [...clientQueryKeys.analytics(), 'patterns', userId, timeframe, patternType],
    queryFn: () => apiService.getCommunicationPatterns(userId, timeframe, patternType),
    enabled: enabled && !!userId,
    staleTime: 15 * 60 * 1000, // 15 minutes
    gcTime: 30 * 60 * 1000, // 30 minutes
    refetchOnWindowFocus: false,
    onError: (error: any) => {
      addNotification({
        type: 'error',
        title: 'Failed to load communication patterns',
        message: error?.response?.data?.detail || 'An error occurred while loading communication patterns',
      });
    },
  });
};

// Hook for client statistics and insights
export const useClientStats = (clients: Client[]) => {
  const stats = React.useMemo(() => {
    if (!clients.length) {
      return {
        totalClients: 0,
        activeClients: 0,
        highPriorityClients: 0,
        averageRelationshipStrength: 0,
        topBusinessCategories: [],
        recentInteractions: 0,
      };
    }

    const now = new Date();
    const thirtyDaysAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
    
    const activeClients = clients.filter(client => {
      const lastInteraction = client.last_interaction ? new Date(client.last_interaction) : null;
      return lastInteraction && lastInteraction > thirtyDaysAgo;
    });

    const highPriorityClients = clients.filter(client => client.priority_level === 'high');
    
    const avgRelationshipStrength = clients.reduce((sum, client) => 
      sum + (client.relationship_strength || 0), 0) / clients.length;

    const businessCategories = clients.reduce((acc, client) => {
      if (client.business_category) {
        acc[client.business_category] = (acc[client.business_category] || 0) + 1;
      }
      return acc;
    }, {} as Record<string, number>);

    const topBusinessCategories = Object.entries(businessCategories)
      .sort(([,a], [,b]) => b - a)
      .slice(0, 5)
      .map(([category, count]) => ({ category, count }));

    const recentInteractions = clients.filter(client => {
      const lastInteraction = client.last_interaction ? new Date(client.last_interaction) : null;
      const sevenDaysAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
      return lastInteraction && lastInteraction > sevenDaysAgo;
    }).length;

    return {
      totalClients: clients.length,
      activeClients: activeClients.length,
      highPriorityClients: highPriorityClients.length,
      averageRelationshipStrength: Math.round(avgRelationshipStrength * 100) / 100,
      topBusinessCategories,
      recentInteractions,
    };
  }, [clients]);

  return stats;
};

// Hook for filtering and sorting clients
export const useClientFilters = (clients: Client[]) => {
  const [filters, setFilters] = React.useState({
    search: '',
    businessCategory: '',
    priorityLevel: '',
    relationshipStrengthMin: 0,
    sortBy: 'last_interaction',
    sortOrder: 'desc' as 'asc' | 'desc',
  });

  const filteredClients = React.useMemo(() => {
    let filtered = [...clients];

    // Apply search filter
    if (filters.search) {
      const searchLower = filters.search.toLowerCase();
      filtered = filtered.filter(client =>
        client.client_name?.toLowerCase().includes(searchLower) ||
        client.email_address.toLowerCase().includes(searchLower) ||
        client.organization_name?.toLowerCase().includes(searchLower)
      );
    }

    // Apply business category filter
    if (filters.businessCategory) {
      filtered = filtered.filter(client => client.business_category === filters.businessCategory);
    }

    // Apply priority level filter
    if (filters.priorityLevel) {
      filtered = filtered.filter(client => client.priority_level === filters.priorityLevel);
    }

    // Apply relationship strength filter
    if (filters.relationshipStrengthMin > 0) {
      filtered = filtered.filter(client => 
        (client.relationship_strength || 0) >= filters.relationshipStrengthMin
      );
    }

    // Apply sorting
    filtered.sort((a, b) => {
      let aValue, bValue;

      switch (filters.sortBy) {
        case 'client_name':
          aValue = a.client_name || a.email_address;
          bValue = b.client_name || b.email_address;
          break;
        case 'relationship_strength':
          aValue = a.relationship_strength || 0;
          bValue = b.relationship_strength || 0;
          break;
        case 'total_emails_received':
          aValue = a.total_emails_received;
          bValue = b.total_emails_received;
          break;
        case 'last_interaction':
        default:
          aValue = a.last_interaction ? new Date(a.last_interaction).getTime() : 0;
          bValue = b.last_interaction ? new Date(b.last_interaction).getTime() : 0;
          break;
      }

      if (typeof aValue === 'string' && typeof bValue === 'string') {
        const comparison = aValue.localeCompare(bValue);
        return filters.sortOrder === 'asc' ? comparison : -comparison;
      } else {
        const comparison = (aValue as number) - (bValue as number);
        return filters.sortOrder === 'asc' ? comparison : -comparison;
      }
    });

    return filtered;
  }, [clients, filters]);

  const updateFilter = (key: keyof typeof filters, value: any) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  };

  const resetFilters = () => {
    setFilters({
      search: '',
      businessCategory: '',
      priorityLevel: '',
      relationshipStrengthMin: 0,
      sortBy: 'last_interaction',
      sortOrder: 'desc',
    });
  };

  return {
    filters,
    filteredClients,
    updateFilter,
    resetFilters,
  };
};

export default {
  useClients,
  useClient,
  useAnalyzeClient,
  useClientAnalytics,
  useCommunicationPatterns,
  useClientStats,
  useClientFilters,
};