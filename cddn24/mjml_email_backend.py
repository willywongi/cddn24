import mrml
from django.core.mail import EmailMessage
from django.core.mail.backends.smtp import EmailBackend


class MJMLEmailBackend(EmailBackend):
    MIME_TYPES = {
        "text/html",
    }

    def send_messages(self, email_messages: list[EmailMessage]) -> None:
        for message in email_messages:
            alternatives = getattr(message, "alternatives", None)
            if alternatives is not None:
                for i, (content, mime_type) in enumerate(alternatives):
                    content = content.strip()
                    if mime_type in self.MIME_TYPES and content.strip().startswith("<mjml>"):
                        message.alternatives[i] = mrml.to_html(content), mime_type
            elif message.content_subtype == "html" and message.body.strip().startswith("<mjml>"):
                message.body = mrml.to_html(message.body)
        return super().send_messages(email_messages)
