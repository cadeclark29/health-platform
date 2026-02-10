// API Service - Communicates with Health Platform backend

import { User, AnalyticsData, OuraStatus, SupplementLog } from '../types';

// Base URL for the API
// Switch to 'https://api.customdose.ai' once DNS propagates
const API_BASE_URL = 'https://health-platform-production-94aa.up.railway.app';

class ApiService {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;

    const defaultHeaders = {
      'Content-Type': 'application/json',
    };

    const response = await fetch(url, {
      ...options,
      headers: {
        ...defaultHeaders,
        ...options.headers,
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Request failed' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  }

  // ============ User Endpoints ============

  async signIn(email: string): Promise<User> {
    return this.request<User>('/users/signin', {
      method: 'POST',
      body: JSON.stringify({ email }),
    });
  }

  async createUser(name: string, email: string): Promise<User> {
    return this.request<User>('/users', {
      method: 'POST',
      body: JSON.stringify({ name, email }),
    });
  }

  async getUser(userId: string): Promise<User> {
    return this.request<User>(`/users/${userId}`);
  }

  async updateUser(userId: string, updates: Partial<User>): Promise<User> {
    return this.request<User>(`/users/${userId}`, {
      method: 'PATCH',
      body: JSON.stringify(updates),
    });
  }

  async resetAccount(userId: string): Promise<any> {
    return this.request(`/users/${userId}/reset`, {
      method: 'POST',
    });
  }

  // ============ Analytics Endpoints ============

  async getAnalytics(userId: string, days: number = 60): Promise<AnalyticsData> {
    return this.request<AnalyticsData>(`/analytics/${userId}/analytics?days=${days}`);
  }

  async getSupplementInsights(userId: string): Promise<any> {
    return this.request(`/analytics/${userId}/supplement-insights`);
  }

  async getOutcomeAnalysis(userId: string, supplementId: string): Promise<any> {
    return this.request(`/analytics/${userId}/outcome-analysis/${supplementId}`);
  }

  async getCorrelations(userId: string): Promise<any> {
    return this.request(`/analytics/${userId}/correlations`);
  }

  // ============ Supplement Endpoints ============

  async logSupplement(
    userId: string,
    supplementId: string,
    logDate: string,
    timeTaken?: string
  ): Promise<SupplementLog> {
    return this.request<SupplementLog>(`/analytics/${userId}/supplement-logs`, {
      method: 'POST',
      body: JSON.stringify({
        supplement_id: supplementId,
        log_date: logDate,  // API accepts log_date in POST but returns "date"
        time_taken: timeTaken,
      }),
    });
  }

  async deleteSupplementLog(userId: string, logId: string): Promise<void> {
    await this.request(`/analytics/${userId}/supplement-logs/${logId}`, {
      method: 'DELETE',
    });
  }

  async addSupplement(
    userId: string,
    data: {
      supplement_id: string;
      supplement_name?: string;
      start_date: string;
      dosage?: string;
      frequency?: string;
      reason?: string;
      notes?: string;
      is_manual?: boolean;
    }
  ): Promise<any> {
    return this.request(`/analytics/${userId}/supplement-starts`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateSupplement(
    userId: string,
    supplementId: string,
    data: {
      start_date?: string;
      end_date?: string;
      dosage?: string;
      frequency?: string;
      reason?: string;
      notes?: string;
    }
  ): Promise<any> {
    return this.request(`/analytics/${userId}/supplement-starts/${supplementId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  async deleteSupplement(userId: string, supplementId: string): Promise<void> {
    await this.request(`/analytics/${userId}/supplement-starts/${supplementId}`, {
      method: 'DELETE',
    });
  }

  // ============ Life Events Endpoints ============

  async addLifeEvent(
    userId: string,
    data: {
      event_type: string;
      event_date: string;
      description?: string;
    }
  ): Promise<any> {
    return this.request(`/analytics/${userId}/life-events`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async deleteLifeEvent(userId: string, eventId: string): Promise<void> {
    await this.request(`/analytics/${userId}/life-events/${eventId}`, {
      method: 'DELETE',
    });
  }

  async getLifeEventTypes(userId: string): Promise<any> {
    return this.request(`/analytics/${userId}/life-events/types`);
  }

  // ============ Oura Endpoints ============

  async getOuraStatus(userId: string): Promise<OuraStatus> {
    return this.request<OuraStatus>(`/integrations/${userId}/oura/status`);
  }

  async syncOuraHistory(userId: string, days: number = 7): Promise<any> {
    return this.request(`/integrations/${userId}/oura/history?days=${days}`);
  }

  getOuraAuthUrl(userId: string): string {
    return `${this.baseUrl}/integrations/${userId}/oura/auth`;
  }

  async disconnectOura(userId: string): Promise<void> {
    await this.request(`/integrations/${userId}/oura`, {
      method: 'DELETE',
    });
  }

  // ============ Mixes & Catalog Endpoints ============

  async getMixes(): Promise<any[]> {
    return this.request<any[]>('/mixes/all');
  }

  async getSupplementCatalog(): Promise<any[]> {
    return this.request<any[]>('/mixes/catalog');
  }

  async getDailyTracking(userId: string, dateOverride?: string): Promise<any> {
    const params = dateOverride ? `?date_override=${dateOverride}` : '';
    return this.request(`/mixes/${userId}/tracking/daily${params}`);
  }

  // ============ Interactions Endpoints ============

  async checkInteractions(supplements: string[]): Promise<any> {
    return this.request('/interactions/check', {
      method: 'POST',
      body: JSON.stringify({ supplement_ids: supplements }),
    });
  }

  async getSupplementInfo(): Promise<any[]> {
    return this.request<any[]>('/interactions/supplements');
  }
}

// Export singleton instance
export const api = new ApiService();

// Export class for testing
export { ApiService };
