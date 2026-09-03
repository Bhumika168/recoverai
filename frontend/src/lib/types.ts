export type TransactionStatus =
  | "CREATED"
  | "AUTHORIZED"
  | "CAPTURED"
  | "FAILED"
  | "ABANDONED"
  | "RECOVERED"
  | "REFUNDED";

export type PaymentMethod =
  | "CARD"
  | "UPI"
  | "NETBANKING"
  | "WALLET"
  | "EMI"
  | "SUBSCRIPTION"
  | "UNKNOWN";

export type CaseStatus =
  | "OPEN"
  | "IN_PROGRESS"
  | "PENDING_APPROVAL"
  | "RECOVERED"
  | "ESCALATED"
  | "EXPIRED"
  | "UNRECOVERABLE";

export type ActionType =
  | "DELAYED_RETRY"
  | "PAYMENT_LINK"
  | "SMART_NOTIFICATION"
  | "SWITCH_METHOD"
  | "HUMAN_ESCALATION"
  | "NO_ACTION";

export type ActionStatus =
  | "PENDING_APPROVAL"
  | "SCHEDULED"
  | "EXECUTING"
  | "COMPLETED"
  | "FAILED"
  | "CANCELLED"
  | "REJECTED";

export interface Customer {
  id: string;
  email: string;
  phone?: string;
  name?: string;
  risk_score: number;
  recovery_receptivity_score: number;
  lifetime_recovered_amount: number;
  created_at: string;
  updated_at: string;
}

export interface Transaction {
  id: string;
  organization_id?: string;
  transaction_id?: string;
  customer_id: string;
  customer_email?: string;
  amount: number;
  currency: string;
  status: TransactionStatus;
  payment_method: PaymentMethod;
  rzp_order_id?: string;
  rzp_payment_id?: string;
  rzp_invoice_id?: string;
  failure_code?: string;
  failure_reason?: string;
  failure_source?: string;
  error_step?: string;
  transaction_time?: string;
  created_at: string;
  updated_at: string;
}

export interface PaymentAttempt {
  id: string;
  transaction_id: string;
  attempt_number: number;
  rzp_payment_id?: string;
  status: string;
  error_code?: string;
  error_description?: string;
  gateway_response?: Record<string, any>;
  created_at: string;
}

export interface AIDecision {
  id: string;
  case_id: string;
  failure_category: string;
  root_cause_explanation: string;
  confidence_score: number;
  recovery_probability: number;
  reasoning_steps: string[];
  risk_factors: string[];
  recommended_action: string;
  recommended_delay_minutes: number;
  recommended_channel: string;
  model_name: string;
  created_at: string;
}

export interface RecoveryAction {
  id: string;
  case_id: string;
  action_type: ActionType;
  status: ActionStatus;
  channel: string;
  idempotency_key: string;
  rzp_payment_link_id?: string;
  rzp_short_url?: string;
  payload?: Record<string, any>;
  result?: Record<string, any>;
  policy_passed: string;
  policy_rule_notes?: string;
  scheduled_at: string;
  executed_at?: string;
  created_at: string;
  updated_at: string;
}

export interface RecoveryCase {
  id: string;
  transaction_id: string;
  customer_id: string;
  status: CaseStatus;
  amount_at_risk: number;
  recovered_amount: number;
  recovery_score: number;
  risk_level: string;
  retry_count: number;
  max_retries_allowed: number;
  next_retry_at?: string;
  strategy_summary?: string;
  requires_human_approval: string;
  approval_reason?: string;
  created_at: string;
  updated_at: string;
  recovered_at?: string;
}

export interface RecoveryCaseDetail extends RecoveryCase {
  transaction?: Transaction;
  customer?: Customer;
  ai_decisions: AIDecision[];
  actions: RecoveryAction[];
}

export interface DashboardKPIs {
  revenue_at_risk: number;
  revenue_recovered: number;
  recovery_rate_percentage: number;
  active_recovery_cases: number;
  successful_recoveries: number;
  human_escalations: number;
  unrecoverable_count: number;
  total_cases: number;
  avg_recovery_score: number;
  currency: string;
  timestamp: string;
}

export interface DashboardChartsData {
  recovery_trend: Array<{
    name: string;
    at_risk: number;
    recovered: number;
    case_amount?: number;
    status?: string;
  }>;
  failure_distribution: Array<{
    category: string;
    name: string;
    count: number;
    color: string;
  }>;
  recovery_funnel: Array<{
    stage: string;
    count: number;
    fill: string;
  }>;
  action_distribution: Array<{
    action_type: string;
    name: string;
    count: number;
  }>;
}

export interface AuditLog {
  id: string;
  entity_name: string;
  entity_id: string;
  event_type: string;
  actor: string;
  state_before?: Record<string, any>;
  state_after: Record<string, any>;
  prev_hash?: string;
  sha256_hash: string;
  timestamp_iso: string;
  notes?: string;
  created_at: string;
}

export interface AuditVerificationResult {
  is_valid: boolean;
  total_entries_verified: number;
  invalid_entry_ids: string[];
  latest_hash?: string;
  verified_at: string;
}

export interface User {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
}

export interface Organization {
  id: string;
  name: string;
  slug: string;
  role: string;
  environment?: string;
  industry?: string;
  company_size?: string;
  country?: string;
  currency?: string;
  onboarding_completed?: boolean;
  max_retries?: number;
  high_value_threshold?: number;
  require_human_approval?: boolean;
  hard_decline_behavior?: string;
  auto_escalate_rules?: string;
  auto_retry_enabled?: boolean;
}

export interface OrganizationUpdateRequest {
  name?: string;
  environment?: string;
  industry?: string;
  company_size?: string;
  country?: string;
  currency?: string;
  onboarding_completed?: boolean;
  max_retries?: number;
  high_value_threshold?: number;
  require_human_approval?: boolean;
  hard_decline_behavior?: string;
  auto_escalate_rules?: string;
  auto_retry_enabled?: boolean;
}

export interface CSVTransactionRow {
  transaction_id: string;
  customer_id?: string;
  customer_email?: string;
  amount: number;
  currency?: string;
  status?: string;
  failure_code?: string;
  failure_reason?: string;
  payment_method?: string;
  timestamp: string;
  invoice_id?: string;
  subscription_id?: string;
}

export interface CSVPreviewResponse {
  headers_detected?: string[];
  preview_rows?: Record<string, any>[];
  rows_detected: number;
  valid_rows_count: number;
  invalid_rows_count: number;
  duplicate_rows_count: number;
  sample_rows: Record<string, any>[];
  errors: string[];
}

export interface CSVImportSummaryResponse {
  imported_count: number;
  failed_recoveries_triggered: number;
  skipped_count: number;
  duplicate_count: number;
  errors: string[];
}

export interface ManualTransactionPayload {
  transaction_id?: string;
  customer_name?: string;
  customer_id?: string;
  customer_email?: string;
  amount: number;
  currency?: string;
  status?: string;
  failure_code?: string;
  failure_reason?: string;
  payment_method?: PaymentMethod | string;
  timestamp?: string;
  invoice_id?: string;
  subscription_id?: string;
}

export interface AuthResponse {
  user: User;
  organization: Organization;
  access_token: string;
  token_type: string;
}

export interface APIResponse<T> {
  success: boolean;
  message: string;
  data: T;
  error?: Record<string, any>;
  timestamp: string;
}
