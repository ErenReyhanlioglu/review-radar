import logging
import smtplib
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import settings

logger = logging.getLogger(__name__)

SENDER = "merenr.oglu@gmail.com"


def _extract_first_section(md: str) -> str:
    """Returns only the first ## section of the report."""
    lines = md.split("\n")
    section_lines: list[str] = []
    in_section = False
    for line in lines:
        if line.startswith("## "):
            if in_section:
                break
            in_section = True
        if in_section:
            section_lines.append(line)
    return "\n".join(section_lines)


def _markdown_to_html(md: str) -> str:
    lines = md.split("\n")
    html_lines = []
    for line in lines:
        if line.startswith("### "):
            html_lines.append(f"<h3>{line[4:]}</h3>")
        elif line.startswith("## "):
            html_lines.append(f"<h2>{line[3:]}</h2>")
        elif line.startswith("# "):
            html_lines.append(f"<h1>{line[2:]}</h1>")
        elif line.startswith("- "):
            html_lines.append(f"<li>{_inline_bold(line[2:])}</li>")
        elif line.strip() == "":
            html_lines.append("<br>")
        else:
            html_lines.append(f"<p>{_inline_bold(line)}</p>")
    return "\n".join(html_lines)


def _inline_bold(text: str) -> str:
    import re
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)


async def send_report(
    month: date,
    content: str,
    recipients: list[str] | None = None,
    pm_email: str | None = None,
) -> bool:
    """
    Sends the monthly report via Gmail SMTP.
    PM gets a link to the full system; other recipients get the read-only viewer link.
    Returns True on success, False if Gmail is not configured.
    """
    if not settings.gmail_app_password:
        logger.warning("Gmail App Password yapılandırılmamış — email atlanıyor.")
        return False

    if not recipients:
        logger.warning("Alıcı listesi boş — email atlanıyor.")
        return False

    month_str = month.strftime("%Y-%m-%d")
    base_url = "http://localhost:5173"
    viewer_url = f"{base_url}?mode=viewer&month={month_str}"
    subject = f"Apollo.io Ürün İstihbarat Raporu — {month.strftime('%B %Y')}"
    report_html = _markdown_to_html(_extract_first_section(content))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(SENDER, settings.gmail_app_password)

            for recipient in recipients:
                is_pm = pm_email and recipient == pm_email
                link_url = base_url if is_pm else viewer_url
                link_label = "Sistemi aç →" if is_pm else "Raporu görüntüle →"

                html_body = f"""
<html><body style="font-family: Arial, sans-serif; max-width: 800px; margin: auto; padding: 24px;">
{report_html}
<hr>
<p>
  <a href="{link_url}" style="display:inline-block;padding:10px 20px;background:#3b82f6;color:#fff;border-radius:6px;text-decoration:none;font-size:14px;">
    {link_label}
  </a>
</p>
<small style="color: #888;">Review Radar tarafından otomatik oluşturulmuştur.</small>
</body></html>
"""
                msg = MIMEMultipart("alternative")
                msg["Subject"] = subject
                msg["From"] = SENDER
                msg["To"] = recipient
                msg.attach(MIMEText(html_body, "html"))

                smtp.sendmail(SENDER, recipient, msg.as_string())
                logger.info("Email gönderildi: %s (%s)", recipient, "PM" if is_pm else "çalışan")

        return True
    except Exception as exc:
        logger.error("Email gönderilemedi: %s", exc)
        return False
