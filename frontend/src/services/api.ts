/**
 * API Service Layer for AI Email Assistant Frontend
 * 
 * This module provides a comprehensive interface for communicating with the
 * AI Email Assistant backend API, including authentication, email management,
 * and AI services.
 */

import axios, { AxiosInstance, AxiosResponse } from 'axios';

// Types for our API responses
export interface User {
  id: string;
  email: string;
  display_name: string | null;
  profile_picture: string | null;
  is_active: boolean;
  created_at: string;
  last_login: string | null;
}

export interface EmailMessage {
  id: string;
  user_id: string;
  client_id: string | null;
  subject: string | null;
  sender: string;
  recipient: string;
  body_text: string | null;
  body_html: string | null;
  sent_datetime: string;
  received_datetime: string | null;
  is_read: boolean;
  is_starred: boolean;
  has_attachments: boolean;
  labels: string[] | null;
  urgency_level: string | null;
  sentiment_score: number | null;
  topic_categories: string[] | null;
  is_processed: boolean;
  is_analyzed: boolean;
}

export interface Client {
  id: string;
  user_id: string;
  email_address: string;
  client_name: string | null;
  organization_name: string | null;
  business_category: string | null;
  communication_frequency: string | null;
  relationship_strength: number | null;
  total_emails_received: number;
  total_emails_sent: number;
  first_interaction: string | null;
  last_interaction: string | null;
  priority_level: string;
}

export interface GeneratedResponse {
  id: string;
  original_email_id: string;
  generated_response: string;
  response_type: string;
  confidence_score: number | null;
  relevance_score: number | null;
  style_match_score: number | null;
  model_used: string | null;
  status: string;
  created_at: string;
}

export interface TaskStatus {
  task_id: string;
  status: string;
  result: any;
  error?: string;
  date_done?: string;
  successful?: boolean;
}

export interface AnalysisResult {
  client_analysis: any;
  style_analysis: any;
  topic_analysis: any;
  overall_analysis: any;
}

export interface VectorSearchResult {
  similar_emails: EmailMessage[];
  context_sources: any[];
  total_results: number;
}

// API Configuration
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const API_VERSION = '/api/v1';

class ApiService {
  private api: AxiosInstance;
  private authToken: string | null = null;

  constructor() {
    this.api = axios.create({
      baseURL: `${API_BASE_URL}${API_VERSION}`,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor to add auth token
    this.api.interceptors.request.use(
      (config) => {
        if (this.authToken) {
          config.headers.Authorization = `Bearer ${this.authToken}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor for error handling
    this.api.interceptors.response.use(
      (response) => response,
      (error) => {
        console.error('API Error:', error.response?.data || error.message);
        
        // Handle authentication errors
        if (error.response?.status === 401) {
          this.clearAuth();
          window.location.href = '/login';
        }
        
        return Promise.reject(error);
      }
    );

    // Load auth token from localStorage
    this.loadAuthToken();
  }

  // Authentication methods
  setAuthToken(token: string) {
    this.authToken = token;
    localStorage.setItem('auth_token', token);
  }

  clearAuth() {
    this.authToken = null;
    localStorage.removeItem('auth_token');
  }

  private loadAuthToken() {
    const token = localStorage.getItem('auth_token');
    if (token) {
      this.authToken = token;
    }
  }

  // Health check
  async healthCheck(): Promise<any> {
    const response = await this.api.get('/health');
    return response.data;
  }

  // Authentication endpoints
  async login(): Promise<string> {
    const response = await this.api.get('/auth/login');
    return response.data.authorization_url;
  }

  async getAuthStatus(): Promise<any> {
    const response = await this.api.get('/auth/status');
    return response.data;
  }

  async logout(): Promise<void> {
    await this.api.post('/auth/logout');
    this.clearAuth();
  }

  // Email management endpoints
  async getEmails(params?: {
    page?: number;
    page_size?: number;
    sender?: string;
    is_analyzed?: boolean;
    priority?: string;
  }): Promise<{ emails: EmailMessage[]; total_count: number; page: number; page_size: number }> {
    const response = await this.api.get('/emails/', { params });
    return response.data;
  }

  async getEmail(emailId: string): Promise<EmailMessage> {
    const response = await this.api.get(`/emails/${emailId}`);
    return response.data;
  }

  async fetchEmails(userId: string, limit: number = 50): Promise<any> {
    const response = await this.api.post('/emails/fetch', {
      user_id: userId,
      limit,
      fetch_attachments: false
    });
    return response.data;
  }

  async updateEmail(emailId: string, updates: Partial<EmailMessage>): Promise<EmailMessage> {
    const response = await this.api.put(`/emails/${emailId}`, updates);
    return response.data;
  }

  // Client management endpoints
  async getClients(params?: {
    page?: number;
    page_size?: number;
    business_category?: string;
    relationship_strength_min?: number;
  }): Promise<{ clients: Client[]; total_count: number; page: number; page_size: number }> {
    const response = await this.api.get('/clients/', { params });
    return response.data;
  }

  async getClient(clientId: string): Promise<Client> {
    const response = await this.api.get(`/clients/${clientId}`);
    return response.data;
  }

  async analyzeClient(userId: string, clientEmail: string): Promise<any> {
    const response = await this.api.post('/clients/analyze', {
      user_id: userId,
      client_email: clientEmail
    });
    return response.data;
  }

  async getClientAnalytics(userId: string, timeframe: string = '30_days'): Promise<any> {
    const response = await this.api.get('/clients/analytics', {
      params: { user_id: userId, timeframe }
    });
    return response.data;
  }

  // Response generation endpoints
  async getResponses(params?: {
    page?: number;
    page_size?: number;
    status?: string;
  }): Promise<{ responses: GeneratedResponse[]; total_count: number; page: number; page_size: number }> {
    const response = await this.api.get('/responses/', { params });
    return response.data;
  }

  async generateResponse(emailId: string, options?: {
    use_rag?: boolean;
    max_context_length?: number;
    custom_instructions?: string;
  }): Promise<any> {
    const response = await this.api.post('/responses/generate', {
      email_id: emailId,
      use_rag: true,
      ...options
    });
    return response.data;
  }

  async generateRagResponse(emailId: string, customInstructions?: string, maxContextLength: number = 2000): Promise<any> {
    const response = await this.api.post(`/responses/generate-rag/${emailId}`, null, {
      params: {
        custom_instructions: customInstructions,
        max_context_length: maxContextLength
      }
    });
    return response.data;
  }

  async updateResponseStatus(responseId: string, status: string): Promise<any> {
    const response = await this.api.put(`/responses/${responseId}/status`, null, {
      params: { status }
    });
    return response.data;
  }

  // Analysis endpoints
  async analyzeWritingStyle(userId: string, emailIds?: string[]): Promise<any> {
    const response = await this.api.post('/analysis/style', {
      user_id: userId,
      email_ids: emailIds
    });
    return response.data;
  }

  async analyzeTopics(userId: string, emailIds?: string[]): Promise<any> {
    const response = await this.api.post('/analysis/topics', {
      user_id: userId,
      email_ids: emailIds
    });
    return response.data;
  }

  async comprehensiveAnalysis(userId: string, emailIds?: string[], includeRecommendations: boolean = true): Promise<AnalysisResult> {
    const response = await this.api.post('/analysis/comprehensive', {
      user_id: userId,
      email_ids: emailIds,
      include_recommendations: includeRecommendations
    });
    return response.data;
  }

  async getCommunicationPatterns(userId: string, timeframe: string = '30_days', patternType: string = 'all'): Promise<any> {
    const response = await this.api.get('/analysis/patterns', {
      params: { user_id: userId, timeframe, pattern_type: patternType }
    });
    return response.data;
  }

  // Vector database endpoints
  async vectorHealthCheck(): Promise<any> {
    const response = await this.api.get('/vectors/health');
    return response.data;
  }

  async initializeVectors(userId: string): Promise<any> {
    const response = await this.api.post('/vectors/initialize', {
      user_id: userId
    });
    return response.data;
  }

  async vectorizeEmails(userId: string, emailIds: string[], updateExisting: boolean = false): Promise<any> {
    const response = await this.api.post('/vectors/vectorize', {
      user_id: userId,
      email_ids: emailIds,
      update_existing: updateExisting
    });
    return response.data;
  }

  async searchVectors(query: string, userId: string, nResults: number = 10, similarityThreshold: number = 0.7): Promise<VectorSearchResult> {
    const response = await this.api.post('/vectors/search', {
      query,
      user_id: userId,
      n_results: nResults,
      similarity_threshold: similarityThreshold
    });
    return response.data;
  }

  async getCollectionStats(): Promise<any> {
    const response = await this.api.get('/vectors/collections/stats');
    return response.data;
  }

  // Background tasks endpoints
  async submitEmailAnalysis(emailId: string, userId: string, priority: string = 'normal'): Promise<{ task_id: string }> {
    const response = await this.api.post('/tasks/analysis/email', {
      email_id: emailId,
      user_id: userId,
      priority
    });
    return response.data;
  }

  async submitBatchAnalysis(emailIds: string[], userId: string, maxConcurrent: number = 5): Promise<{ task_id: string }> {
    const response = await this.api.post('/tasks/analysis/batch', {
      email_ids: emailIds,
      user_id: userId,
      max_concurrent: maxConcurrent
    });
    return response.data;
  }

  async submitResponseGeneration(emailId: string, userId: string, generationOptions?: any): Promise<{ task_id: string }> {
    const response = await this.api.post('/tasks/generation/response', {
      email_id: emailId,
      user_id: userId,
      generation_options: generationOptions
    });
    return response.data;
  }

  async submitVectorization(emailIds: string[], userId: string, updateExisting: boolean = false): Promise<{ task_id: string }> {
    const response = await this.api.post('/tasks/vectorization/emails', {
      email_ids: emailIds,
      user_id: userId,
      update_existing: updateExisting
    });
    return response.data;
  }

  async submitProfileUpdate(userId: string): Promise<{ task_id: string }> {
    const response = await this.api.post('/tasks/profile/update', {
      user_id: userId
    });
    return response.data;
  }

  async getTaskStatus(taskId: string): Promise<TaskStatus> {
    const response = await this.api.get(`/tasks/status/${taskId}`);
    return response.data;
  }

  async cancelTask(taskId: string): Promise<any> {
    const response = await this.api.delete(`/tasks/cancel/${taskId}`);
    return response.data;
  }

  async getTaskSystemHealth(): Promise<any> {
    const response = await this.api.get('/tasks/health');
    return response.data;
  }

  async getWorkerStatus(): Promise<any> {
    const response = await this.api.get('/tasks/admin/workers');
    return response.data;
  }

  // Utility methods
  async uploadFile(file: File, endpoint: string): Promise<any> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await this.api.post(endpoint, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });

    return response.data;
  }

  // Streaming responses for real-time updates
  async streamTaskUpdates(taskId: string, onUpdate: (data: any) => void): Promise<void> {
    // This would implement Server-Sent Events or WebSocket connection
    // For now, we'll poll the task status
    const pollInterval = setInterval(async () => {
      try {
        const status = await this.getTaskStatus(taskId);
        onUpdate(status);
        
        if (status.status === 'SUCCESS' || status.status === 'FAILURE') {
          clearInterval(pollInterval);
        }
      } catch (error) {
        console.error('Error polling task status:', error);
        clearInterval(pollInterval);
      }
    }, 2000);
  }
}

// Create and export a singleton instance
export const apiService = new ApiService();

// Export individual methods for easier testing
export default ApiService;