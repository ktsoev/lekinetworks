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
<html lang="ru">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="color-scheme" content="dark">
</head>
<body style="margin: 0; padding: 0; background-color: #0a0a0a; font-family: 'Manrope', 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; -webkit-font-smoothing: antialiased;">
    <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #0a0a0a; padding: 40px 20px;">
        <tr>
            <td align="center">
                <table width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width: 560px;">

                    <!-- Header -->
                    <tr>
                        <td style="padding-bottom: 2px;">
                            <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background: linear-gradient(90deg, #00e5ff 0%, #00ccee 100%); height: 2px; font-size: 0; line-height: 0;">
                                <tr><td>&nbsp;</td></tr>
                            </table>
                        </td>
                    </tr>
                    <tr>
                        <td style="background-color: #111111; padding: 32px 32px 24px 32px; border-left: 1px solid rgba(0, 229, 255, 0.12); border-right: 1px solid rgba(0, 229, 255, 0.12);">
                            <table width="100%" cellpadding="0" cellspacing="0" border="0">
                                <tr>
                                    <td>
                                        <p style="margin: 0; font-size: 20px; font-weight: 700; color: #00e5ff; letter-spacing: 3px; text-transform: uppercase;">LEKI NETWORKS</p>
                                        <p style="margin: 6px 0 0 0; font-size: 12px; font-weight: 500; color: #9494A0; text-transform: uppercase; letter-spacing: 2px;">Код входа</p>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <!-- Body -->
                    <tr>
                        <td style="background-color: #111111; padding: 0 32px 32px 32px; border-left: 1px solid rgba(0, 229, 255, 0.12); border-right: 1px solid rgba(0, 229, 255, 0.12);">

                            <p style="margin: 0 0 16px 0; font-size: 15px; color: #EEEEF0; line-height: 1.6;">Здравствуйте!</p>
                            <p style="margin: 0 0 28px 0; font-size: 15px; color: #9494A0; line-height: 1.7;">Введите этот код на странице входа, чтобы продолжить в личном кабинете.</p>

                            <!-- OTP Block -->
                            <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #0d0d0d; border: 1px solid rgba(0, 229, 255, 0.25); margin-bottom: 28px;">
                                <tr>
                                    <td style="padding: 28px 24px; text-align: center;">
                                        <p style="margin: 0 0 14px 0; font-size: 11px; font-weight: 600; color: #9494A0; text-transform: uppercase; letter-spacing: 3px;">Ваш код</p>
                                        <p style="margin: 0; font-size: 40px; font-weight: 700; letter-spacing: 0.3em; color: #00e5ff; font-family: 'JetBrains Mono', 'Fira Code', 'Courier New', monospace; text-shadow: 0 0 20px rgba(0, 229, 255, 0.4);">{code_safe}</p>
                                    </td>
                                </tr>
                            </table>

                            <p style="margin: 0 0 28px 0; font-size: 14px; color: #5E5E6E; line-height: 1.7;">
                                Код действует <span style="color: #EEEEF0; font-weight: 600;">{ttl} мин.</span>&nbsp; Не передавайте его третьим лицам. Если вы не запрашивали вход — просто проигнорируйте это письмо.
                            </p>

                            <!-- Divider -->
                            <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom: 24px;">
                                <tr>
                                    <td style="border-top: 1px solid rgba(0, 229, 255, 0.08); font-size: 0; line-height: 0;">&nbsp;</td>
                                </tr>
                            </table>

                            <p style="margin: 0 0 4px 0; font-size: 14px; color: #5E5E6E;">
                                Если возникли вопросы, свяжитесь с поддержкой.
                            </p>
                            <p style="margin: 0; font-size: 14px; color: #9494A0;">
                                С уважением, <span style="color: #00e5ff; font-weight: 600;">Команда LEKI Networks</span>
                            </p>
                        </td>
                    </tr>

                    <!-- Bottom border -->
                    <tr>
                        <td style="border-left: 1px solid rgba(0, 229, 255, 0.12); border-right: 1px solid rgba(0, 229, 255, 0.12); border-bottom: 1px solid rgba(0, 229, 255, 0.12); background-color: #111111; height: 1px; font-size: 0; line-height: 0;">&nbsp;</td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td style="padding: 24px 0; text-align: center;">
                            <p style="margin: 0; font-size: 12px; color: #5E5E6E; letter-spacing: 0.5px;">
                                &copy; {year} LEKI Networks — ваш безопасный и свободный интернет.
                            </p>
                        </td>
                    </tr>

                </table>
            </td>
        </tr>
    </table>
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
        use_tls=True,
        start_tls=False,
        timeout=timeout,
    )
