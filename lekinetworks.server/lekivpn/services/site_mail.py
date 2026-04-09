import html
import os
from datetime import datetime, timezone
from email.message import EmailMessage

import aiosmtplib


def _otp_ttl_minutes() -> int:
    return int(os.getenv("OTP_EXPIRE_MINUTES", "15"))


async def send_login_code(to_email: str, code: str) -> None:
    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")
    from_email = os.getenv("SMTP_FROM_EMAIL", user)
    from_name = os.getenv("SMTP_FROM_NAME", "LEKI Networks")

    if not all([host, user, password, from_email]):
        raise RuntimeError("SMTP env vars are not fully configured")

    timeout = float(os.getenv("SMTP_TIMEOUT", "60"))
    ttl = _otp_ttl_minutes()
    year = datetime.now(timezone.utc).year
    code_safe = html.escape(code)

    text = f"""
Здравствуйте!

Ваш код для входа в LEKI Networks:

{code}

Код действует {ttl} минут. Если вы не запрашивали вход, просто игнорируйте это письмо.

С уважением,
Команда LEKI Networks
"""

    html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #1f2937; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f9fafb;">
    <div style="background: linear-gradient(135deg, #38B2AC 0%, #2C7A7B 100%); color: white; padding: 40px 30px; border-radius: 16px 16px 0 0; text-align: center;">
        <h1 style="margin: 0; font-size: 32px; font-weight: 600; letter-spacing: -0.5px;">LEKI Networks</h1>
        <p style="margin: 12px 0 0 0; font-size: 18px; opacity: 0.95;">Код входа</p>
    </div>

    <div style="background: #ffffff; padding: 40px 30px; border-radius: 0 0 16px 16px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);">
        <p style="font-size: 16px; margin-top: 0; color: #374151;">Здравствуйте!</p>

        <p style="font-size: 16px; color: #374151;">Введите этот код на странице входа, чтобы продолжить в личном кабинете LEKI Networks.</p>

        <div style="background: #E0F7F4 !important; padding: 24px; border-radius: 12px; margin: 30px 0; border-left: 4px solid #38B2AC; color-scheme: light only; text-align: center;">
            <p style="margin: 0 0 12px 0; font-size: 14px; color: #000000 !important; text-transform: uppercase; letter-spacing: 0.06em;">Ваш код</p>
            <p style="margin: 0; font-size: 36px; font-weight: 700; letter-spacing: 0.35em; color: #0f766e !important; font-family: 'Courier New', ui-monospace, monospace;">{code_safe}</p>
        </div>

        <p style="font-size: 15px; color: #6b7280; margin: 0 0 24px 0;">
            Код действует <strong style="color: #374151;">{ttl} мин.</strong> Не передавайте его другим. Если вы не запрашивали вход, просто закройте это письмо.
        </p>

        <div style="margin-top: 40px; padding-top: 30px; border-top: 2px solid #f3f4f6;">
            <p style="font-size: 14px; color: #6b7280; margin: 0 0 20px 0;">
                Если у вас возникли вопросы, свяжитесь с нашей службой поддержки.
            </p>
            <p style="font-size: 15px; color: #374151; margin: 0;">
                С уважением,<br>
                <strong style="color: #38B2AC;">Команда LEKI Networks</strong>
            </p>
        </div>
    </div>

    <div style="text-align: center; margin-top: 30px; padding: 20px;">
        <p style="font-size: 13px; color: #9ca3af; margin: 0;">
            © {year} LEKI Networks. Ваш безопасный и свободный интернет.
        </p>
    </div>
</body>
</html>
"""

    msg = EmailMessage()
    msg["From"] = f"{from_name} <{from_email}>"
    msg["To"] = to_email
    msg["Subject"] = "Код входа — LEKI Networks"
    msg.set_content(text.strip())
    msg.add_alternative(html_body.strip(), subtype="html")

    await aiosmtplib.send(
        msg,
        hostname=host,
        port=port,
        username=user,
        password=password,
        start_tls=True,
        timeout=timeout,
    )
