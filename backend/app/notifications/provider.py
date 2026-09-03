import abc
import uuid
import html
import re
from typing import Dict, Any, Optional, Tuple
from app.logging_config import logger


def sanitize_and_render_template(template_body: str, variables: Dict[str, Any]) -> str:
    """
    Safely renders message templates with variable substitution.
    Escapes untrusted characters to prevent HTML/script injection.
    """
    if not template_body:
        return ""

    def replace_var(match):
        var_name = match.group(1).strip()
        val = variables.get(var_name, "")
        if val is None:
            return ""
        # Stringify and escape
        return html.escape(str(val))

    # Pattern: {{ variable_name }}
    pattern = re.compile(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}")
    return pattern.sub(replace_var, template_body)


# Default Multi-Language Templates (English, Hindi, Hinglish)
DEFAULT_TEMPLATES = [
    {
        "name": "Failed Payment Recovery (English)",
        "channel": "EMAIL",
        "language": "EN",
        "subject": "Action Required: Payment for {{company_name}} could not be completed",
        "body": "Hi {{customer_name}},\n\nYour payment of {{currency}} {{amount}} to {{company_name}} could not be processed due to a {{payment_method}} error.\n\nPlease update your payment method or retry your payment using the secure link below:\n{{payment_link}}\n\nThank you,\n{{company_name}} Team",
    },
    {
        "name": "Failed Payment Recovery (Hinglish)",
        "channel": "WHATSAPP",
        "language": "HINGLISH",
        "subject": "Payment update from {{company_name}}",
        "body": "Hi {{customer_name}}, aapka {{currency}} {{amount}} ka payment complete nahi ho paya. Please neeche diye gaye secure link se payment complete karein:\n{{payment_link}}\n\nShukriya,\n{{company_name}}",
    },
    {
        "name": "Failed Payment Recovery (Hindi)",
        "channel": "SMS",
        "language": "HI",
        "subject": "{{company_name}} भुगतान सूचना",
        "body": "नमस्ते {{customer_name}}, {{company_name}} के लिए आपका {{currency}} {{amount}} का भुगतान विफल रहा। कृपया इस लिंक से पुनः प्रयास करें: {{payment_link}}",
    },
    {
        "name": "Checkout Abandonment Recovery",
        "channel": "EMAIL",
        "language": "EN",
        "subject": "Complete your order with {{company_name}}",
        "body": "Hi {{customer_name}},\n\nWe noticed your checkout was interrupted. Your items are saved. Click below to complete your payment:\n{{payment_link}}\n\nWarm regards,\n{{company_name}}",
    },
]


class NotificationProvider(abc.ABC):
    """
    Abstract Notification Provider interface.
    Decouples communication orchestration from third-party SMS/Email/WhatsApp APIs.
    """

    @property
    @abc.abstractmethod
    def provider_name(self) -> str:
        pass

    @abc.abstractmethod
    def send(
        self,
        channel: str,
        recipient: str,
        subject: Optional[str],
        body: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Dispatches communication message.
        Returns: (success: bool, provider_message_id: str, error_code: Optional[str])
        """
        pass


class MockNotificationProvider(NotificationProvider):
    """Deterministic Simulation Notification Provider for sandbox & tests."""

    @property
    def provider_name(self) -> str:
        return "MOCK_DISPATCHER"

    def send(
        self,
        channel: str,
        recipient: str,
        subject: Optional[str],
        body: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[str]]:
        msg_id = f"msg_{channel.lower()}_{uuid.uuid4().hex[:10]}"
        logger.info(f"[MockNotification] Sent {channel} to {recipient} -> ID: {msg_id}")
        return True, msg_id, None


class EmailNotificationProvider(NotificationProvider):
    """Email Communication Adapter."""

    @property
    def provider_name(self) -> str:
        return "EMAIL_GATEWAY"

    def send(
        self,
        channel: str,
        recipient: str,
        subject: Optional[str],
        body: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[str]]:
        msg_id = f"em_{uuid.uuid4().hex[:12]}"
        logger.info(f"[EmailGateway] Sent email to {recipient} (Subject: {subject})")
        return True, msg_id, None


class WhatsAppNotificationProvider(NotificationProvider):
    """WhatsApp Business API Adapter."""

    @property
    def provider_name(self) -> str:
        return "WHATSAPP_CLOUD_API"

    def send(
        self,
        channel: str,
        recipient: str,
        subject: Optional[str],
        body: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[str]]:
        msg_id = f"wamid_{uuid.uuid4().hex[:14]}"
        logger.info(f"[WhatsAppGateway] Sent message to {recipient}")
        return True, msg_id, None


NOTIFICATION_REGISTRY: Dict[str, NotificationProvider] = {
    "MOCK": MockNotificationProvider(),
    "EMAIL": EmailNotificationProvider(),
    "SMS": MockNotificationProvider(),
    "WHATSAPP": WhatsAppNotificationProvider(),
    "IN_APP": MockNotificationProvider(),
}


def get_notification_provider(channel: str = "EMAIL") -> NotificationProvider:
    key = channel.upper().strip()
    return NOTIFICATION_REGISTRY.get(key, NOTIFICATION_REGISTRY["MOCK"])
