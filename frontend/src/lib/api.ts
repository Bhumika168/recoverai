import {
  DashboardKPIs,
  DashboardChartsData,
  Transaction,
  RecoveryCase,
  RecoveryCaseDetail,
  AuditLog,
  AuditVerificationResult,
  AuthResponse,
  User,
  Organization,
  OrganizationUpdateRequest,
  CSVPreviewResponse,
  CSVImportSummaryResponse,
  CSVTransactionRow,
  ManualTransactionPayload,
} from "./types";

const PRODUCTION_BACKEND_URL = "https://recoverai-u329.onrender.com";

const getApiBase = () => {
  const envUrl = process.env.NEXT_PUBLIC_API_URL;
  if (envUrl && envUrl.trim() && !envUrl.includes("recoverai-3ny5.onrender.com")) {
    const base = envUrl.trim().replace(/\/$/, "");
    return base.endsWith("/api/v1") ? base : `${base}/api/v1`;
  }
  if (typeof window !== "undefined") {
    const host = window.location.hostname || "localhost";
    const protocol = window.location.protocol || "http:";
    if (host.includes("onrender.com") || (host !== "localhost" && host !== "127.0.0.1")) {
      return `${PRODUCTION_BACKEND_URL}/api/v1`;
    }
    return `http://${host}:8000/api/v1`;
  }
  if (process.env.NODE_ENV === "production") {
    return `${PRODUCTION_BACKEND_URL}/api/v1`;
  }
  return "http://localhost:8000/api/v1";
};

export function getStoredToken(): string | null {
  if (typeof document !== "undefined") {
    const match = document.cookie.match(new RegExp("(^| )recoverai_session=([^;]+)"));
    if (match && match[2]) return match[2];
  }
  if (typeof window !== "undefined") {
    return localStorage.getItem("recoverai_session");
  }
  return null;
}

export function setStoredSession(token: string) {
  if (typeof document !== "undefined") {
    document.cookie = `recoverai_session=${token}; path=/; max-age=604800; SameSite=Lax`;
  }
  if (typeof window !== "undefined") {
    localStorage.setItem("recoverai_session", token);
  }
}

export function clearStoredSession() {
  if (typeof document !== "undefined") {
    document.cookie = "recoverai_session=; path=/; max-age=0; SameSite=Lax";
  }
  if (typeof window !== "undefined") {
    localStorage.removeItem("recoverai_session");
  }
}

async function fetchAPI<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${getApiBase()}${endpoint}`;
  const token = getStoredToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((options.headers || {}) as Record<string, string>),
  };
  if (token && !headers["Authorization"]) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  try {
    const res = await fetch(url, {
      ...options,
      credentials: "include",
      headers,
      cache: "no-store",
    });

    if (!res.ok) {
      const errorData = await res.json().catch(() => ({}));
      let message = errorData.message || errorData.detail || `API request failed with status ${res.status}`;
      if (errorData.error?.details && Array.isArray(errorData.error.details) && errorData.error.details.length > 0) {
        const detailStr = errorData.error.details
          .map((d: any) => {
            const loc = d.loc && d.loc.length > 1 ? d.loc.slice(1).join(".") : "field";
            return `${loc}: ${d.msg}`;
          })
          .join(", ");
        message = `${message} (${detailStr})`;
      }
      throw new Error(message);
    }

    const json = await res.json();
    return json.data !== undefined ? json.data : json;
  } catch (err: any) {
    console.error(`[API Client Error] ${endpoint}:`, err.message);
    throw err;
  }
}

export const api = {
  // Authentication & Multi-Tenancy
  async signup(payload: {
    full_name: string;
    email: string;
    password: string;
    company_name?: string;
  }): Promise<AuthResponse> {
    return fetchAPI<AuthResponse>("/auth/signup", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async login(payload: { email: string; password: string }): Promise<AuthResponse> {
    return fetchAPI<AuthResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async logout(): Promise<{ success: boolean; message: string }> {
    return fetchAPI<{ success: boolean; message: string }>("/auth/logout", {
      method: "POST",
    });
  },

  async getMe(): Promise<AuthResponse> {
    return fetchAPI<AuthResponse>("/auth/me");
  },

  async forgotPassword(email: string): Promise<{ success: boolean; message: string }> {
    return fetchAPI<{ success: boolean; message: string }>("/auth/forgot-password", {
      method: "POST",
      body: JSON.stringify({ email }),
    });
  },

  async resetPassword(payload: { token: string; new_password: string }): Promise<{ success: boolean; message: string }> {
    return fetchAPI<{ success: boolean; message: string }>("/auth/reset-password", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  // Organization Workspace
  async getCurrentOrganization(): Promise<Organization> {
    return fetchAPI<Organization>("/organization/current");
  },

  async updateOrganization(payload: OrganizationUpdateRequest): Promise<Organization> {
    return fetchAPI<Organization>("/organization/current", {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  },

  // KPIs & Analytics
  async getKPIs(range = "all", startDate?: string, endDate?: string): Promise<DashboardKPIs> {
    const params = new URLSearchParams({ range });
    if (startDate) params.append("start_date", startDate);
    if (endDate) params.append("end_date", endDate);
    return fetchAPI<DashboardKPIs>(`/analytics/summary?${params.toString()}`);
  },

  async getRevenueTrend(range = "30d"): Promise<any[]> {
    return fetchAPI<any[]>(`/analytics/revenue-trend?range=${range}`);
  },

  async getFailureBreakdown(range = "all"): Promise<any[]> {
    return fetchAPI<any[]>(`/analytics/failure-breakdown?range=${range}`);
  },

  async getRecoveryFunnel(range = "all"): Promise<any[]> {
    return fetchAPI<any[]>(`/analytics/recovery-funnel?range=${range}`);
  },

  async getRecentActivity(limit = 10): Promise<any[]> {
    return fetchAPI<any[]>(`/analytics/recent-activity?limit=${limit}`);
  },

  async getTopOpportunities(limit = 5): Promise<any[]> {
    return fetchAPI<any[]>(`/analytics/top-opportunities?limit=${limit}`);
  },

  async getDataSourcesStatus(): Promise<any> {
    return fetchAPI<any>("/analytics/data-sources");
  },

  async getCharts(): Promise<DashboardChartsData> {
    return fetchAPI<DashboardChartsData>("/analytics/charts");
  },

  // Transactions
  async getTransactions(status?: string, limit = 50): Promise<Transaction[]> {
    const query = status ? `?status=${status}&limit=${limit}` : `?limit=${limit}`;
    return fetchAPI<Transaction[]>(`/transactions${query}`);
  },

  async getTransaction(id: string): Promise<Transaction> {
    return fetchAPI<Transaction>(`/transactions/${id}`);
  },

  async createTransaction(payload: ManualTransactionPayload): Promise<Transaction> {
    return fetchAPI<Transaction>("/transactions", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async recoverTransaction(id: string): Promise<any> {
    return fetchAPI<any>(`/transactions/${id}/recover`, {
      method: "POST",
    });
  },

  async previewCSV(file: File): Promise<CSVPreviewResponse> {
    const formData = new FormData();
    formData.append("file", file);

    const url = `${getApiBase()}/transactions/preview-csv`;
    const token = getStoredToken();
    const headers: Record<string, string> = {};
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const res = await fetch(url, {
      method: "POST",
      credentials: "include",
      headers,
      body: formData,
    });

    if (!res.ok) {
      const errorData = await res.json().catch(() => ({}));
      throw new Error(errorData.message || errorData.detail || `CSV preview failed (${res.status})`);
    }
    const json = await res.json();
    return json.data !== undefined ? json.data : json;
  },

  async importCSV(rows: CSVTransactionRow[]): Promise<CSVImportSummaryResponse> {
    return fetchAPI<CSVImportSummaryResponse>("/transactions/import-csv", {
      method: "POST",
      body: JSON.stringify({ rows }),
    });
  },

  async ingestFailure(payload: {
    customer_email: string;
    customer_name?: string;
    amount: number;
    currency?: string;
    payment_method?: string;
    failure_code: string;
    failure_reason: string;
  }): Promise<Transaction> {
    return fetchAPI<Transaction>("/transactions/ingest-failure", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  // Recovery Cases
  async getCases(status?: string, limit = 50): Promise<RecoveryCase[]> {
    const query = status ? `?status=${status}&limit=${limit}` : `?limit=${limit}`;
    return fetchAPI<RecoveryCase[]>(`/cases${query}`);
  },

  async getCaseDetail(id: string): Promise<RecoveryCaseDetail> {
    return fetchAPI<RecoveryCaseDetail>(`/cases/${id}`);
  },

  async triggerCaseRecovery(caseId: string): Promise<RecoveryCase> {
    return fetchAPI<RecoveryCase>(`/cases/${caseId}/trigger-recovery`, {
      method: "POST",
    });
  },

  async approveCase(caseId: string): Promise<RecoveryCase> {
    return fetchAPI<RecoveryCase>(`/cases/${caseId}/approve`, {
      method: "POST",
    });
  },

  async rejectCase(caseId: string): Promise<RecoveryCase> {
    return fetchAPI<RecoveryCase>(`/cases/${caseId}/reject`, {
      method: "POST",
    });
  },

  async simulateRecovery(caseId: string): Promise<RecoveryCase> {
    return fetchAPI<RecoveryCase>(`/cases/${caseId}/simulate-recovery`, {
      method: "POST",
    });
  },

  async verifyRecovery(caseId: string): Promise<RecoveryCase> {
    return fetchAPI<RecoveryCase>(`/cases/${caseId}/verify-recovery`, {
      method: "POST",
    });
  },

  async batchEvaluateCases(caseIds?: string[]): Promise<{
    total_evaluated: number;
    processed_count: number;
    approved_count: number;
    held_for_approval: number;
    blocked_or_stopped: number;
  }> {
    return fetchAPI("/cases/batch-evaluate", {
      method: "POST",
      body: JSON.stringify(caseIds ? { case_ids: caseIds } : {}),
    });
  },

  // Audit Logs
  async getAuditLogs(entityName?: string, entityId?: string, limit = 100): Promise<AuditLog[]> {
    const params = new URLSearchParams();
    if (entityName) params.append("entity_name", entityName);
    if (entityId) params.append("entity_id", entityId);
    params.append("limit", limit.toString());
    return fetchAPI<AuditLog[]>(`/audit/logs?${params.toString()}`);
  },

  async verifyAuditChain(): Promise<AuditVerificationResult> {
    return fetchAPI<AuditVerificationResult>("/audit/verify-chain");
  },

  // Integrations & Webhooks
  async getIntegrations(): Promise<any[]> {
    return fetchAPI<any[]>("/integrations");
  },

  async connectIntegration(payload: {
    provider: string;
    api_key: string;
    secret_key?: string;
    webhook_secret?: string;
    environment?: string;
  }): Promise<any> {
    return fetchAPI("/integrations/connect", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async testIntegration(payload: {
    provider: string;
    api_key: string;
    secret_key?: string;
  }): Promise<any> {
    return fetchAPI("/integrations/test", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async disconnectIntegration(provider: string): Promise<any> {
    return fetchAPI("/integrations/disconnect", {
      method: "POST",
      body: JSON.stringify({ provider }),
    });
  },

  async syncIntegration(provider: string): Promise<any> {
    return fetchAPI("/integrations/sync", {
      method: "POST",
      body: JSON.stringify({ provider }),
    });
  },

  async getWebhookEvents(limit = 50): Promise<any[]> {
    return fetchAPI<any[]>(`/integrations/events?limit=${limit}`);
  },

  // Campaigns
  async getCampaigns(status?: string): Promise<any[]> {
    const query = status ? `?status=${status}` : "";
    return fetchAPI<any[]>(`/campaigns${query}`);
  },

  async createCampaign(payload: any): Promise<any> {
    return fetchAPI("/campaigns", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async getCampaignDetail(id: string): Promise<any> {
    return fetchAPI<any>(`/campaigns/${id}`);
  },

  async pauseCampaign(id: string): Promise<any> {
    return fetchAPI(`/campaigns/${id}/pause`, { method: "POST" });
  },

  async resumeCampaign(id: string): Promise<any> {
    return fetchAPI(`/campaigns/${id}/resume`, { method: "POST" });
  },

  async archiveCampaign(id: string): Promise<any> {
    return fetchAPI(`/campaigns/${id}/archive`, { method: "POST" });
  },

  // Templates
  async getTemplates(channel?: string, language?: string): Promise<any[]> {
    const params = new URLSearchParams();
    if (channel) params.append("channel", channel);
    if (language) params.append("language", language);
    return fetchAPI<any[]>(`/templates?${params.toString()}`);
  },

  async createTemplate(payload: any): Promise<any> {
    return fetchAPI("/templates", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async previewTemplate(payload: { body: string; subject?: string }): Promise<any> {
    return fetchAPI("/templates/preview", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  // Notifications
  async getNotifications(limit = 50): Promise<{ unread_count: number; notifications: any[] }> {
    return fetchAPI<{ unread_count: number; notifications: any[] }>(`/notifications?limit=${limit}`);
  },

  async markNotificationRead(id: string): Promise<any> {
    return fetchAPI(`/notifications/${id}/read`, { method: "PATCH" });
  },

  async markAllNotificationsRead(): Promise<any> {
    return fetchAPI("/notifications/mark-all-read", { method: "POST" });
  },

  // Case Communications & Timeline
  async getCaseTimeline(caseId: string): Promise<any[]> {
    return fetchAPI<any[]>(`/cases/${caseId}/timeline`);
  },

  async dispatchCaseCommunication(caseId: string, payload?: any): Promise<any> {
    return fetchAPI(`/cases/${caseId}/dispatch-communication`, {
      method: "POST",
      body: JSON.stringify(payload || {}),
    });
  },

  async optOutCustomer(caseId: string, reason?: string): Promise<any> {
    return fetchAPI(`/cases/${caseId}/opt-out`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    });
  },

  async getCaseCommunications(caseId: string): Promise<any[]> {
    return fetchAPI<any[]>(`/cases/${caseId}/communications`);
  },

  // Customer Recovery Portal
  async getRecoveryTokenData(token: string): Promise<any> {
    return fetchAPI<any>(`/recover/${token}`);
  },

  async initiateCustomerPayment(token: string): Promise<any> {
    return fetchAPI<any>(`/recover/${token}/initiate-payment`, {
      method: "POST",
    });
  },

  async completeSandboxRecovery(token: string): Promise<any> {
    return fetchAPI<any>(`/recover/${token}/complete-sandbox`, {
      method: "POST",
    });
  },

  async optOutFromRecoveryLink(token: string): Promise<any> {
    return fetchAPI<any>(`/recover/${token}/opt-out`, {
      method: "POST",
    });
  },

  // Sandbox Mode (Safe for Production & Development)
  async resetDemoDataset(): Promise<any> {
    return fetchAPI("/sandbox/reset", {
      method: "POST",
    });
  },

  async runDemoBatch(): Promise<any> {
    return fetchAPI("/sandbox/run", {
      method: "POST",
    });
  },

  async getDemoStatus(): Promise<any> {
    return fetchAPI("/sandbox/status");
  },
};
