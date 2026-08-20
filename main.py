import os
import re
import json
import time
import secrets
import logging
import asyncio
import traceback
import threading
import datetime
from functools import wraps
import discord
from discord import app_commands
from discord.ext import commands
from flask import Flask, redirect, request, render_template_string, make_response
import requests


intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CLIENT_ID = os.environ.get("CLIENT_ID")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET")
REDIRECT_URI = "https://sdfsafasfasfsafasf.onrender.com/callback"

START_URL = "https://sdfsafasfasfsafasf.onrender.com/start"

GUILD_ID = 1207514483527000084
ROLE_ID = 1211224793060478976

LOG_CHANNEL_ID = int(os.environ.get("LOG_CHANNEL_ID", "1539922513189150780") or 0)
ERROR_LOG_CHANNEL_ID = int(os.environ.get("ERROR_LOG_CHANNEL_ID", "1539922650510532658") or 0) or LOG_CHANNEL_ID

OAUTH_STATE_TTL_SECONDS = 600
RATE_LIMIT_MAX_REQUESTS = 8
RATE_LIMIT_WINDOW_SECONDS = 60
VERIFY_COOLDOWN_SECONDS = 60

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
VERIFIED_LOG_PATH = os.path.join(DATA_DIR, "verified_users.json")
ERROR_LOG_PATH = os.path.join(DATA_DIR, "error_log.json")

if not BOT_TOKEN or not CLIENT_SECRET:
    raise RuntimeError(
        "กรุณาตั้งค่า BOT_TOKEN และ CLIENT_SECRET เป็น environment variable ก่อนรัน "
        "(ห้าม hardcode ไว้ในไฟล์ เพราะเป็นข้อมูลลับที่รั่วไหลได้ง่ายมาก)"
    )

logger = logging.getLogger("verifybot-stifshop")
logger.setLevel(logging.INFO)

_console_handler = logging.StreamHandler()
_console_handler.setFormatter(
    logging.Formatter("[%(asctime)s] %(levelname)s - %(message)s", "%Y-%m-%d %H:%M:%S")
)
logger.addHandler(_console_handler)

_file_handler = logging.FileHandler(os.path.join(DATA_DIR, "bot.log"), encoding="utf-8")
_file_handler.setFormatter(
    logging.Formatter("[%(asctime)s] %(levelname)s - %(message)s", "%Y-%m-%d %H:%M:%S")
)
logger.addHandler(_file_handler)
_json_lock = threading.Lock()


def _load_json(path):
    with _json_lock:
        if not os.path.exists(path):
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                return json.loads(content) if content else []
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"อ่านไฟล์ JSON ไม่สำเร็จ ({path}): {e}")
            return []


def _append_json(path, record):
    with _json_lock:
        data = []
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        loaded = json.loads(content)
                        if isinstance(loaded, list):
                            data = loaded
            except (json.JSONDecodeError, OSError) as e:
                logger.error(f"อ่านไฟล์ JSON ไม่สำเร็จ ({path}): {e}")
        if not isinstance(data, list):
            data = []
        data.append(record)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except OSError as e:
            logger.error(f"เขียนไฟล์ JSON ไม่สำเร็จ ({path}): {e}")


def save_verified_user(user_info, role_name, ip_address=None, already_verified=False):
    record = {
        "user_id": user_info.get("id"),
        "username": user_info.get("username"),
        "role_id": ROLE_ID,
        "role_name": role_name,
        "ip_address": ip_address,
        "already_verified": already_verified,
        "verified_at_utc": datetime.datetime.utcnow().isoformat(),
        "verified_at_thai": thai_date(),
    }
    _append_json(VERIFIED_LOG_PATH, record)
    return record


def save_error_log(context, error_message, user_info=None):
    record = {
        "context": context,
        "error": _redact_secrets(error_message),
        "user_id": user_info.get("id") if user_info else None,
        "username": user_info.get("username") if user_info else None,
        "timestamp_utc": datetime.datetime.utcnow().isoformat(),
    }
    _append_json(ERROR_LOG_PATH, record)
    return record


_SECRET_PATTERNS = [p for p in [
    (CLIENT_SECRET, "[REDACTED_CLIENT_SECRET]") if CLIENT_SECRET else None,
    (BOT_TOKEN, "[REDACTED_BOT_TOKEN]") if BOT_TOKEN else None,
] if p]


def _redact_secrets(text):
    if not text:
        return text
    text = str(text)
    for secret_value, placeholder in _SECRET_PATTERNS:
        if secret_value:
            text = text.replace(secret_value, placeholder)
    text = re.sub(r'("access_token"\s*:\s*")[^"]+(")', r"\1[REDACTED]\2", text)
    text = re.sub(r"(access_token=)[^&\s]+", r"\1[REDACTED]", text)
    return text


THAI_MONTHS = [
    "", "ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.",
    "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค.",
]


def thai_date(dt=None):
    dt = dt or datetime.datetime.utcnow()
    return f"{dt.day} {THAI_MONTHS[dt.month]} {dt.year + 543}"


def send_log_embed(embed: discord.Embed, channel_id: int = None):
    target_channel_id = channel_id or LOG_CHANNEL_ID
    if not target_channel_id:
        return
    if not bot.is_ready() or bot.loop is None:
        logger.warning("บอทยังไม่พร้อม ส่ง log ไปยัง Discord channel ไม่ได้")
        return

    async def _send():
        try:
            channel = bot.get_channel(target_channel_id) or await bot.fetch_channel(target_channel_id)
            await channel.send(embed=embed)
        except Exception as e:
            logger.error(f"ส่ง log ไปยัง Discord channel ({target_channel_id}) ไม่สำเร็จ: {e}")

    try:
        asyncio.run_coroutine_threadsafe(_send(), bot.loop)
    except Exception as e:
        logger.error(f"schedule ส่ง log ไม่สำเร็จ: {e}")

_oauth_states = {}
_oauth_states_lock = threading.Lock()


def _purge_expired_states():
    now = time.time()
    expired = [s for s, ts in _oauth_states.items() if now - ts > OAUTH_STATE_TTL_SECONDS]
    for s in expired:
        _oauth_states.pop(s, None)


def generate_oauth_state():
    state = secrets.token_urlsafe(32)
    with _oauth_states_lock:
        _purge_expired_states()
        _oauth_states[state] = time.time()
    return state


def verify_and_consume_oauth_state(state_from_query, state_from_cookie):
    if not state_from_query or not state_from_cookie:
        return False
    if state_from_query != state_from_cookie:
        return False
    with _oauth_states_lock:
        _purge_expired_states()
        issued_at = _oauth_states.pop(state_from_query, None)
    if issued_at is None:
        return False
    if time.time() - issued_at > OAUTH_STATE_TTL_SECONDS:
        return False
    return True


_rate_limit_store = {}
_rate_limit_lock = threading.Lock()


def rate_limit(max_requests=RATE_LIMIT_MAX_REQUESTS, window_seconds=RATE_LIMIT_WINDOW_SECONDS):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            ip = _client_ip()
            now = time.time()
            with _rate_limit_lock:
                timestamps = _rate_limit_store.setdefault(ip, [])
                timestamps[:] = [t for t in timestamps if now - t < window_seconds]
                if len(timestamps) >= max_requests:
                    logger.warning(f"Rate limit เกินกำหนด: IP={ip} path={request.path}")
                    return "คำขอถี่เกินไป กรุณาลองใหม่อีกครั้งในภายหลัง", 429
                timestamps.append(now)
            return f(*args, **kwargs)
        return wrapped
    return decorator


_verify_cooldown = {}
_verify_cooldown_lock = threading.Lock()


def check_and_set_cooldown(user_id):
    now = time.time()
    with _verify_cooldown_lock:
        last = _verify_cooldown.get(user_id)
        if last is not None and (now - last) < VERIFY_COOLDOWN_SECONDS:
            return False, round(VERIFY_COOLDOWN_SECONDS - (now - last), 1)
        _verify_cooldown[user_id] = now
        return True, 0


def user_has_role(guild_id, user_id, role_id):
    try:
        resp = requests.get(
            f"https://discord.com/api/v10/guilds/{guild_id}/members/{user_id}",
            headers={"Authorization": f"Bot {BOT_TOKEN}"},
            timeout=10,
        )
        if resp.status_code == 404:
            return False
        resp.raise_for_status()
        member_roles = [str(r) for r in resp.json().get("roles", [])]
        return str(role_id) in member_roles
    except Exception as e:
        logger.error(f"เช็คยศผู้ใช้ไม่สำเร็จ: {e}")
        return None


def log_role_granted(user_info, role_name, ip_address=None, already_verified=False):
    if already_verified:
        logger.info(f"ยืนยันซ้ำ (มียศอยู่แล้ว): {user_info.get('username')} ({user_info.get('id')})")
    else:
        logger.info(f"ให้ยศสำเร็จ: {user_info.get('username')} ({user_info.get('id')})")
    save_verified_user(user_info, role_name, ip_address, already_verified=already_verified)

    embed = discord.Embed(
        title="🔁 ยืนยันซ้ำ (มียศอยู่แล้ว)" if already_verified else "✅ รับยศสำเร็จ",
        description=(
            f"<@{user_info.get('id')}> ยืนยันตัวตนซ้ำ (มียศ <@&{ROLE_ID}> อยู่แล้ว)"
            if already_verified
            else f"<@{user_info.get('id')}> ได้รับยศ <@&{ROLE_ID}> เรียบร้อยแล้ว"
        ),
        color=discord.Color.blurple() if already_verified else discord.Color.green(),
        timestamp=datetime.datetime.utcnow(),
    )
    if user_info.get("avatar_url"):
        embed.set_thumbnail(url=user_info.get("avatar_url"))
    embed.add_field(name="ผู้ใช้", value=f"{user_info.get('username')}", inline=True)
    embed.add_field(name="User ID", value=f"{user_info.get('id')}", inline=True)
    embed.add_field(name="ยศ", value=role_name, inline=True)
    if ip_address:
        embed.add_field(name="IP Address", value=ip_address, inline=False)
    embed.set_footer(text="ระบบยืนยันตัวตน • STIF SHOP")
    send_log_embed(embed, channel_id=LOG_CHANNEL_ID)


def log_error_event(context, error_message, user_info=None, ip_address=None):
    error_message = _redact_secrets(error_message)
    logger.error(f"[{context}] {error_message}")
    save_error_log(context, error_message, user_info)

    embed = discord.Embed(
        title="⚠️ เกิดข้อผิดพลาด",
        description=f"เกิดข้อผิดพลาดในขั้นตอน: **{context}**",
        color=discord.Color.red(),
        timestamp=datetime.datetime.utcnow(),
    )
    if user_info:
        embed.add_field(name="ผู้ใช้", value=f"{user_info.get('username')} ({user_info.get('id')})", inline=False)
    embed.add_field(name="รายละเอียด", value=f"```{error_message[:1000]}```", inline=False)
    if ip_address:
        embed.add_field(name="IP Address", value=ip_address, inline=False)
    embed.set_footer(text="ระบบยืนยันตัวตน • STIF SHOP")
    send_log_embed(embed, channel_id=ERROR_LOG_CHANNEL_ID)


def _client_ip():
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.remote_addr


def _role_color_hex(color_int):
    if not color_int:
        return "#99AAB5"
    return f"#{color_int:06x}"


def get_role_info(guild_id, role_id):
    try:
        resp = requests.get(
            f"https://discord.com/api/v10/guilds/{guild_id}/roles",
            headers={"Authorization": f"Bot {BOT_TOKEN}"},
            timeout=10,
        )
        resp.raise_for_status()
        for role in resp.json():
            if str(role.get("id")) == str(role_id):
                return {"name": role.get("name"), "color": _role_color_hex(role.get("color"))}
    except Exception as e:
        logger.error(f"ดึงข้อมูลยศไม่สำเร็จ: {e}")
        log_error_event("get_role_info", str(e))
    return {"name": "Verified", "color": "#57F287"}


def get_role_name(guild_id, role_id):
    return get_role_info(guild_id, role_id)["name"]


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
<title>{{ title | default('กำลังตรวจสอบและรับยศ') }}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Kanit:wght@300;400;500;600;700&family=Sarabun:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
  :root{
    --bg-0:#050508;
    --violet:#8b5cf6;
    --magenta:#ec4899;
    --cyan:#22d3ee;
    --green:#23a55a;
    --red:#ED4245;
    --text-hi:#ffffff;
    --text-lo:#949ba4;
  }
  *{box-sizing:border-box;margin:0;padding:0;-webkit-tap-highlight-color:transparent;}
  html,body{
    height:100%;
    min-height:100dvh;
    background:var(--bg-0);
    overflow:hidden;
  }
  body{
    font-family:'Sarabun','Kanit',sans-serif;
    display:flex;
    align-items:center;
    justify-content:center;
    position:relative;
    isolation:isolate;
    min-height:100dvh;
    padding:20px 16px;
  }

  .ambient-bg{
    position:fixed;inset:0;pointer-events:none;z-index:1;
    background:
      radial-gradient(circle at 15% 15%, rgba(139, 92, 246, 0.15), transparent 45%),
      radial-gradient(circle at 85% 85%, rgba(34, 211, 238, 0.12), transparent 45%),
      radial-gradient(circle at 50% 50%, rgba(35, 165, 90, 0.1), transparent 55%);
    transition:background 0.6s ease;
  }
  body.phase-success .ambient-bg{
    background:
      radial-gradient(circle at 15% 15%, rgba(35, 165, 90, 0.18), transparent 45%),
      radial-gradient(circle at 85% 85%, rgba(34, 211, 238, 0.15), transparent 45%),
      radial-gradient(circle at 50% 50%, rgba(35, 165, 90, 0.12), transparent 55%);
  }

  .noise{
    position:fixed;inset:0;
    background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='120' height='120'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='2' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.03'/%3E%3C/svg%3E");
    mix-blend-mode:overlay;pointer-events:none;z-index:2;
  }

  .card-wrap{ position:relative; z-index:10; width:100%; max-width:420px; }
  .card-glow{
    position:absolute; inset:-2px; border-radius:24px;
    background:linear-gradient(135deg, rgba(139,92,246,0.6), rgba(34,211,238,0.4), rgba(236,72,153,0.5));
    filter:blur(16px);
    opacity:0.5;
    z-index:-1;
    animation:glowPulse 6s ease-in-out infinite;
    transition:background 0.6s ease;
  }
  @keyframes glowPulse{
    0%,100%{ opacity:0.4; transform:scale(1); }
    50%{ opacity:0.7; transform:scale(1.02); }
  }
  body.phase-success .card-glow{
    background:linear-gradient(135deg, rgba(35,165,90,0.6), rgba(34,211,238,0.4), rgba(35,165,90,0.5));
  }

  .card{
    position:relative;
    width:100%;
    padding:26px 22px 24px;
    background:linear-gradient(180deg, rgba(14, 24, 22, 0.95), rgba(8, 16, 15, 0.98));
    border:1px solid rgba(35, 165, 90, 0.35);
    border-radius:22px;
    backdrop-filter:blur(30px);
    -webkit-backdrop-filter:blur(30px);
    box-shadow: 0 24px 60px -15px rgba(0,0,0,0.85), inset 0 1px 0 rgba(255,255,255,0.12);
    text-align:center;
    animation:cardIn 0.6s cubic-bezier(0.16, 1, 0.3, 1) both;
    overflow: hidden;
  }
  @keyframes cardIn{ from{opacity:0; transform:translateY(16px) scale(0.96);} to{opacity:1; transform:translateY(0) scale(1);} }

  .phase{ display:none; position:relative; z-index:3; }
  .phase.active{ display:block; animation:phaseIn 0.5s cubic-bezier(0.16, 1, 0.3, 1) both; }
  @keyframes phaseIn{ from{opacity:0; transform:translateY(8px);} to{opacity:1; transform:translateY(0);} }

  .loader{
    position:relative; width:92px; height:92px; margin:0 auto 18px;
    display:flex; align-items:center; justify-content:center;
  }
  .sonar{
    position:absolute; inset:0; border-radius:50%; border:1.5px solid var(--cyan); opacity:0;
    animation:sonar 2.8s cubic-bezier(.25,.7,.4,1) infinite;
  }
  .sonar.s2{ animation-delay:0.7s; border-color:var(--violet); }
  .sonar.s3{ animation-delay:1.4s; border-color:var(--magenta); }
  @keyframes sonar{
    0%{ transform:scale(0.4); opacity:0; }
    12%{ opacity:0.9; }
    100%{ transform:scale(1.15); opacity:0; }
  }
  .halo{
    position:absolute; inset:6%; border-radius:50%;
    background:radial-gradient(circle at 30% 28%, rgba(139,92,246,0.95), transparent 55%),
               radial-gradient(circle at 72% 35%, rgba(34,211,238,0.9), transparent 55%),
               radial-gradient(circle at 50% 78%, rgba(236,72,153,0.85), transparent 55%);
    filter:blur(10px); opacity:0.65;
  }
  .glass-circle{
    position:absolute; inset:14%; border-radius:50%;
    background:radial-gradient(circle at 35% 30%, rgba(255,255,255,0.16), rgba(10,10,16,0.6) 60%);
    border:1px solid rgba(255,255,255,0.22); backdrop-filter:blur(6px);
  }
  .core{
    position:absolute; top:50%; left:50%; width:18px; height:18px; margin:-9px 0 0 -9px;
    clip-path:polygon(50% 0%, 90% 25%, 100% 70%, 50% 100%, 0% 70%, 10% 25%);
    background:linear-gradient(160deg, #ffffff 0%, #c9b8ff 22%, var(--violet) 55%, var(--cyan) 100%);
    box-shadow:0 0 20px 6px rgba(139,92,246,0.8);
  }

  .eyebrow{ font-size: 0.72rem; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; color: var(--cyan); margin-bottom: 6px; }
  .title{
    font-family:'Kanit',sans-serif; font-weight:600; font-size:1.15rem;
    background:linear-gradient(90deg, #c4b5fd, #67e8f9 55%, #f5a8d0);
    -webkit-background-clip:text; background-clip:text; color:transparent;
    margin-bottom:8px;
  }
  .subtitle{ font-size:0.8rem; line-height:1.5; color:var(--text-lo); font-weight:300; margin-bottom:16px; }
  .status-line{
    display:flex; align-items:center; justify-content:center; gap:8px;
    width:100%; padding:10px 14px; border-radius:12px;
    border:1px solid rgba(255,255,255,0.08);
    background:linear-gradient(135deg, rgba(139,92,246,0.2), rgba(34,211,238,0.15));
    color:var(--text-hi); font-size:0.8rem; font-weight:500;
  }
  .status-line .dots span{
    display:inline-block; width:4px; height:4px; margin-left:2px; border-radius:50%; background:var(--cyan);
    animation:bounce 1.2s ease-in-out infinite;
  }
  .status-line .dots span:nth-child(2){animation-delay:0.15s;}
  .status-line .dots span:nth-child(3){animation-delay:0.3s;}
  @keyframes bounce{ 0%,80%,100%{transform:translateY(0); opacity:0.5;} 40%{transform:translateY(-4px); opacity:1;} }

  .discord-profile-card {
    background: #0b0c0e; border-radius: 16px; overflow: hidden;
    text-align: left; margin-bottom: 16px;
    border: 1px solid rgba(255, 255, 255, 0.08);
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.6);
  }

  .discord-banner-area {
    width: 100%; height: 72px;
    background: linear-gradient(135deg, #111214, #000000);
    position: relative; display: flex; justify-content: flex-end; align-items: flex-start;
    padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.04);
  }

  .status-bubble {
    background: rgba(17, 18, 20, 0.85);
    border: 1px solid rgba(35, 165, 90, 0.3);
    padding: 5px 12px; border-radius: 20px;
    display: flex; align-items: center; gap: 6px;
    font-size: 0.75rem; font-weight: 500; color: #e2e8f0;
    backdrop-filter: blur(8px); box-shadow: 0 4px 15px rgba(0,0,0,0.4);
  }
  .status-bubble svg { width: 13px; height: 13px; fill: #23a55a; }

  .discord-content-area { padding: 0 16px 16px 16px; position: relative; }

  .discord-avatar-container { display: flex; align-items: flex-end; margin-top: -34px; margin-bottom: 10px; }
  .discord-avatar-wrapper {
    position: relative; width: 62px; height: 62px; border-radius: 50%;
    background: #0b0c0e; padding: 3px; box-shadow: 0 4px 12px rgba(0,0,0,0.5);
  }
  .discord-user-avatar { width: 100%; height: 100%; border-radius: 50%; object-fit: cover; }
  .avatar-status-dot {
    position: absolute; bottom: 3px; right: 3px; width: 14px; height: 14px;
    background: #23a55a; border: 3px solid #0b0c0e; border-radius: 50%;
  }

  .display-name-main {
    font-family: 'Kanit', sans-serif; font-size: 1.15rem; font-weight: 700;
    color: #ffffff; line-height: 1.2; margin-bottom: 3px;
  }
  .user-handle-sub {
    font-size: 0.78rem; color: var(--text-lo); margin-bottom: 12px;
    display: flex; align-items: center; gap: 6px; font-weight: 400;
  }

  .divider-line { height: 1px; background: rgba(255, 255, 255, 0.07); margin: 10px 0; }

  .profile-info-block { font-size: 0.76rem; color: var(--text-lo); margin-bottom: 10px; }
  .profile-info-block .label {
    font-weight: 600; text-transform: uppercase; font-size: 0.65rem;
    letter-spacing: 0.8px; margin-bottom: 4px; color: #80848e;
  }

  .roles-container { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 4px; }
  .role-tag {
    display: inline-flex; align-items: center; gap: 6px;
    background: #18191c; padding: 4px 10px; border-radius: 8px;
    font-size: 0.76rem; font-weight: 500; color: #f2f3f5;
    border: 1px solid rgba(255,255,255,0.06); box-shadow: 0 2px 5px rgba(0,0,0,0.2);
  }
  .role-dot { width: 8px; height: 8px; border-radius: 50%; background: #57F287; box-shadow: 0 0 8px #57F287; }

  .result-message { margin-bottom: 16px; color: #b5bac1; font-size: 0.86rem; font-weight: 400; }

  .result-btn {
    display: flex; align-items: center; justify-content: center; gap: 8px;
    width: 100%; color: #fff; font-weight: 600; font-size: 0.95rem; padding: 12px;
    border-radius: 12px; text-decoration: none; border: none; cursor: pointer;
    transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    font-family: 'Sarabun', 'Kanit', sans-serif;
  }
  .btn-success {
    background: linear-gradient(135deg, #23a55a, #1f934e);
    box-shadow: 0 6px 20px rgba(35, 165, 90, 0.4);
  }
  .btn-success:hover {
    background: linear-gradient(135deg, #26b763, #22a55a);
    transform: translateY(-2px); box-shadow: 0 8px 25px rgba(35, 165, 90, 0.6);
  }
  .btn-retry {
    background: linear-gradient(135deg, #ED4245, #c93639);
    box-shadow: 0 6px 20px rgba(237, 66, 69, 0.4);
  }
  .btn-retry:hover {
    background: linear-gradient(135deg, #f05457, #ED4245);
    transform: translateY(-2px); box-shadow: 0 8px 25px rgba(237, 66, 69, 0.6);
  }
  .result-btn:active { transform: scale(0.98); }

  @keyframes confettiFall{ 0%{transform:translateY(-20px) rotate(0deg); opacity:1;} 100%{transform:translateY(240px) rotate(360deg); opacity:0;} }
  .confetti{ position:absolute; top:0; left:0; width:100%; height:100%; pointer-events:none; overflow:hidden; z-index:0; }
  .confetti span{ position:absolute; top:-10px; width:7px; height:11px; border-radius:2px; opacity:0.95; animation:confettiFall 2.6s ease-in forwards; }
  #phase-result > *:not(.confetti){ position:relative; z-index:1; }
</style>
</head>
<body class="phase-checking">

  <div class="ambient-bg"></div>
  <div class="noise"></div>

  <div class="card-wrap">
    <div class="card-glow"></div>
    <div class="card">

      <div class="phase active" id="phase-checking">
        <div class="eyebrow">ระบบยืนยันตัวตน</div>
        <div class="loader">
          <div class="sonar s1"></div>
          <div class="sonar s2"></div>
          <div class="sonar s3"></div>
          <div class="halo"></div>
          <div class="glass-circle"></div>
          <div class="core"></div>
        </div>
        <div class="title">{{ title | default('กำลังตรวจสอบข้อมูล') }}</div>
        <div class="subtitle">
          {{ subtitle | default('ระบบกำลังตรวจสอบสิทธิ์และเพิ่มยศให้คุณ<br>โปรดรอสักครู่ ระบบกำลังประมวลผล') | safe }}
        </div>
        <div class="status-line">
          {{ status_text | default('กำลังเชื่อมต่อฐานข้อมูล Discord') }}
          <span class="dots"><span></span><span></span><span></span></span>
        </div>
      </div>

      <div class="phase" id="phase-result">
        <div class="confetti" id="confetti"></div>

        <div class="discord-profile-card">
          <div class="discord-banner-area">
            <div class="status-bubble">
              <svg viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/></svg>
              <span>ยืนยันตัวตนแล้ว</span>
            </div>
          </div>

          <div class="discord-content-area">
            <div class="discord-avatar-container">
              <div class="discord-avatar-wrapper">
                <img src="{{ user.avatar_url if user and user.avatar_url else 'https://cdn.discordapp.com/embed/avatars/0.png' }}" alt="Avatar" class="discord-user-avatar">
                <div class="avatar-status-dot"></div>
              </div>
            </div>

            <div class="display-name-main">{{ user.username if user and user.username else 'Unknown' }}</div>
            <div class="user-handle-sub">
              <span>@{{ user.username if user and user.username else 'unknown' }}</span>
              <span>•</span>
              <span>ID: {{ user.id if user and user.id else '-' }}</span>
            </div>

            <div class="divider-line"></div>

            <div class="profile-info-block">
              <div class="label">บทบาท</div>
              <div class="roles-container">
                {% if role_name %}
                <div class="role-tag">
                  <span class="role-dot" style="background:{{ role_color | default('#57F287') }}; box-shadow: 0 0 8px {{ role_color | default('#57F287') }};"></span>
                  <span>{{ role_name }}</span>
                </div>
                {% else %}
                <div class="role-tag">
                  <span class="role-dot"></span>
                  <span>Verified</span>
                </div>
                {% endif %}
              </div>
            </div>

            <div class="profile-info-block" style="margin-bottom: 0; margin-top: 10px;">
              <div class="label" style="display:flex; align-items:center; gap:5px; color: #b5bac1; font-size: 0.72rem; text-transform: none; font-weight: 500;">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><path d="M19 3h-1V1h-2v2H8V1H6v2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H5V8h14v11z"/></svg>
                ยืนยันตัวตนเมื่อ {{ verified_at | default('วันนี้') }}
              </div>
            </div>
          </div>
        </div>

        <p class="result-message">{{ result_message | default('ระบบได้เพิ่มยศให้คุณเรียบร้อยแล้ว') }}</p>

        <a href="{{ button_url | default('https://discord.com/app') }}"
           id="discord-btn"
           class="result-btn {{ 'btn-success' if (result_state | default('success')) == 'success' else 'btn-retry' }}">
          {{ button_text | default('กลับไปที่ Discord') }}
        </a>
      </div>

    </div>
  </div>

  <script>
    function openDiscord(event) {
      event.preventDefault();
      const discordWebUrl = "{{ button_url | default('https://discord.com/app') }}";
      const ua = navigator.userAgent || navigator.vendor || window.opera;
      const isAndroid = /Android/i.test(ua);
      const isIOS = /iPhone|iPad|iPod/i.test(ua) ||
                    (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
      if (!isAndroid && !isIOS) {
        window.location.href = discordWebUrl;
        return;
      }
      let appOpened = false;
      const onVisibilityChange = function () { if (document.hidden) appOpened = true; };
      document.addEventListener('visibilitychange', onVisibilityChange);
      window.addEventListener('pagehide', onVisibilityChange);
      setTimeout(function () {
        document.removeEventListener('visibilitychange', onVisibilityChange);
        window.removeEventListener('pagehide', onVisibilityChange);
        if (!appOpened) window.location.href = discordWebUrl;
      }, 2000);
      if (isAndroid) {
        window.location.href = 'intent://-#Intent;scheme=discord;package=com.discord;S.browser_fallback_url=' + encodeURIComponent(discordWebUrl) + ';end';
      } else if (isIOS) {
        window.location.href = 'discord://-';
      }
    }

    const btn = document.getElementById('discord-btn');
    if (btn) btn.addEventListener('click', openDiscord);

    function spawnConfetti() {
      const colors = ['#57F287', '#8b5cf6', '#22d3ee', '#ffffff'];
      const container = document.getElementById('confetti');
      if (!container) return;
      for (let i = 0; i < 28; i++) {
        const piece = document.createElement('span');
        piece.style.left = Math.random() * 100 + '%';
        piece.style.background = colors[Math.floor(Math.random() * colors.length)];
        piece.style.animationDelay = (Math.random() * 0.4) + 's';
        piece.style.animationDuration = (2 + Math.random() * 0.8) + 's';
        container.appendChild(piece);
      }
    }

    setTimeout(function () {
      document.getElementById('phase-checking').classList.remove('active');
      document.getElementById('phase-result').classList.add('active');
      document.body.classList.remove('phase-checking');
      document.body.classList.add('phase-{{ result_state | default("success") }}');
      {% if (result_state | default('success')) == 'success' %}
      spawnConfetti();
      {% endif %}
    }, 3500);
  </script>
</body>
</html>
"""

app = Flask(__name__)


@app.route('/favicon.ico')
def favicon():
    return '', 204

@app.errorhandler(Exception)
def handle_unhandled_exception(e):
    error_detail = _redact_secrets(f"{e}\n{traceback.format_exc()}")
    logger.error(f"Unhandled Flask exception ที่ {request.path}: {error_detail}")
    log_error_event(f"flask:{request.path}", str(e), ip_address=_client_ip())
    return "เกิดข้อผิดพลาดที่ไม่คาดคิด กรุณาลองใหม่อีกครั้ง", 500


@app.route("/start")
@rate_limit()
def start():
    state = generate_oauth_state()
    discord_login_url = (
        f"https://discord.com/api/oauth2/authorize?client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}&response_type=code&scope=identify%20guilds.join"
        f"&state={state}"
    )
    resp = make_response(redirect(discord_login_url, code=302))
    resp.set_cookie(
        "oauth_state",
        state,
        max_age=OAUTH_STATE_TTL_SECONDS,
        httponly=True,
        secure=True,
        samesite="Lax",
    )
    logger.info(f"[/start] สร้าง OAuth state สำหรับ IP={_client_ip()}")
    return resp


@app.route("/")
@rate_limit()
def home():
    state = generate_oauth_state()
    discord_login_url = (
        f"https://discord.com/api/oauth2/authorize?client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}&response_type=code&scope=identify%20guilds.join"
        f"&state={state}"
    )
    html = render_template_string(
        HTML_TEMPLATE,
        title="ยืนยันตัวตน",
        subtitle="กำลังนำคุณไปหน้ายืนยันตัวตนผ่าน Discord",
        result_state="processing",
        button_url=discord_login_url,
        button_text="🚀 เข้าสู่ระบบผ่าน Discord",
        user=None,
    )
    resp = make_response(html)
    resp.set_cookie(
        "oauth_state",
        state,
        max_age=OAUTH_STATE_TTL_SECONDS,
        httponly=True,
        secure=True,
        samesite="Lax",
    )
    return resp

@app.route("/callback", strict_slashes=False)
@rate_limit()
def callback():
    ip_address = _client_ip()
    code = request.args.get("code")
    state_from_query = request.args.get("state")
    state_from_cookie = request.cookies.get("oauth_state")

    logger.info(
        f"[/callback] IP={ip_address} "
        f"code={'yes' if code else 'no'} "
        f"state_query={'yes' if state_from_query else 'no'} "
        f"state_cookie={'yes' if state_from_cookie else 'no'}"
    )

    if not code:
        log_error_event("callback:missing_code", "ไม่พบรหัสยืนยันตัวตน (code) ใน request", ip_address=ip_address)
        return "ไม่พบรหัสยืนยันตัวตน", 400

    if not verify_and_consume_oauth_state(state_from_query, state_from_cookie):
        log_error_event(
            "callback:invalid_state",
            "state ไม่ตรงกันหรือหมดอายุ (อาจเป็นความพยายาม CSRF หรือลิงก์เก่าที่หมดอายุ)",
            ip_address=ip_address,
        )
        resp = make_response(render_template_string(
            HTML_TEMPLATE,
            title="ลิงก์หมดอายุ",
            result_state="error",
            result_title="ลิงก์ไม่ถูกต้อง",
            result_message="ลิงก์ยืนยันตัวตนหมดอายุหรือไม่ถูกต้อง กรุณากดปุ่มยืนยันตัวตนใหม่อีกครั้ง",
            user=None,
        ), 400)
        resp.delete_cookie("oauth_state")
        return resp

    user_info = None

    try:
        token_resp = requests.post(
            "https://discord.com/api/oauth2/token",
            data={"client_id": CLIENT_ID, "client_secret": CLIENT_SECRET,
                  "grant_type": "authorization_code", "code": code, "redirect_uri": REDIRECT_URI},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10,
        )
        token_json = token_resp.json()
        access_token = token_json.get("access_token")

        if not access_token:
            error_detail = token_json.get("error_description") or token_json.get("error") or "ไม่ทราบสาเหตุ"
            log_error_event("callback:token_exchange", f"แลก token ไม่สำเร็จ: {error_detail}", ip_address=ip_address)
            resp = make_response(render_template_string(
                HTML_TEMPLATE,
                title="เกิดข้อผิดพลาด",
                result_state="error",
                result_title="เกิดข้อผิดพลาด",
                result_message="ไม่สามารถยืนยันตัวตนได้ กรุณาลองใหม่อีกครั้ง",
                user=None,
            ))
            resp.delete_cookie("oauth_state")
            return resp

        user_data = requests.get(
            "https://discord.com/api/users/@me",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        ).json()
        user_id   = user_data.get("id")
        username  = user_data.get("username")
        avatar_id = user_data.get("avatar")
        avatar_url = (f"https://cdn.discordapp.com/avatars/{user_id}/{avatar_id}.png"
                      if avatar_id else "https://cdn.discordapp.com/embed/avatars/0.png")

        user_info = {"id": user_id, "username": username, "avatar_url": avatar_url}

        if not user_id:
            log_error_event("callback:fetch_user", f"ดึงข้อมูลผู้ใช้ไม่สำเร็จ: {user_data}", ip_address=ip_address)
            resp = make_response(render_template_string(
                HTML_TEMPLATE,
                title="เกิดข้อผิดพลาด",
                result_state="error",
                result_title="เกิดข้อผิดพลาด",
                result_message="ไม่สามารถดึงข้อมูลผู้ใช้ Discord ได้",
                user=None,
            ))
            resp.delete_cookie("oauth_state")
            return resp

        allowed, seconds_left = check_and_set_cooldown(user_id)
        if not allowed:
            resp = make_response(render_template_string(
                HTML_TEMPLATE,
                title="กรุณารอสักครู่",
                result_state="error",
                result_title="กรุณารอสักครู่",
                result_message=f"คุณเพิ่งยืนยันตัวตนไปแล้ว กรุณารออีก {int(seconds_left)} วินาทีแล้วลองใหม่",
                user=user_info,
            ))
            resp.delete_cookie("oauth_state")
            return resp

        already_has_role = user_has_role(GUILD_ID, user_id, ROLE_ID)

        if already_has_role:
            role_info = get_role_info(GUILD_ID, ROLE_ID)
            log_role_granted(user_info, role_info["name"], ip_address, already_verified=True)
            resp = make_response(render_template_string(
                HTML_TEMPLATE,
                title="ยืนยันตัวตนแล้ว",
                result_state="success",
                result_title="ยืนยันตัวตนแล้ว",
                result_message="คุณมียศนี้อยู่แล้ว ไม่ต้องทำอะไรเพิ่ม",
                user=user_info,
                role_name=role_info["name"],
                role_color=role_info["color"],
                verified_at=thai_date(),
                button_url="https://discord.com/app",
                button_text="กลับไปที่ Discord",
            ))
            resp.delete_cookie("oauth_state")
            return resp

        r = requests.put(
            f"https://discord.com/api/v10/guilds/{GUILD_ID}/members/{user_id}/roles/{ROLE_ID}",
            headers={"Authorization": f"Bot {BOT_TOKEN}"},
            timeout=10,
        )

        if r.status_code in [204, 200]:
            role_info = get_role_info(GUILD_ID, ROLE_ID)
            log_role_granted(user_info, role_info["name"], ip_address)
            resp = make_response(render_template_string(
                HTML_TEMPLATE,
                title="ยืนยันตัวตนสำเร็จ",
                result_state="success",
                result_title="ให้ยศสำเร็จ",
                result_message="ระบบได้เพิ่มยศให้คุณเรียบร้อยแล้ว",
                user=user_info,
                role_name=role_info["name"],
                role_color=role_info["color"],
                verified_at=thai_date(),
                button_url="https://discord.com/app",
                button_text="กลับไปที่ Discord",
            ))
            resp.delete_cookie("oauth_state")
            return resp
        else:
            error_detail = f"HTTP {r.status_code}: {r.text[:300]}"
            log_error_event("callback:add_role", error_detail, user_info, ip_address)
            resp = make_response(render_template_string(
                HTML_TEMPLATE,
                title="เกิดข้อผิดพลาด",
                result_state="error",
                result_title="เกิดข้อผิดพลาด",
                result_message="ไม่สามารถเพิ่มยศได้ (ตรวจสอบลำดับยศของบอท)",
                user=user_info,
            ))
            resp.delete_cookie("oauth_state")
            return resp

    except requests.exceptions.RequestException as e:
        log_error_event("callback:request_exception", f"เชื่อมต่อ Discord API ไม่สำเร็จ: {e}", user_info, ip_address)
        resp = make_response(render_template_string(
            HTML_TEMPLATE,
            title="เกิดข้อผิดพลาด",
            result_state="error",
            result_title="เกิดข้อผิดพลาด",
            result_message="เชื่อมต่อ Discord ไม่สำเร็จ กรุณาลองใหม่อีกครั้ง",
            user=user_info,
        ))
        resp.delete_cookie("oauth_state")
        return resp
    except Exception as e:
        log_error_event("callback:unhandled_exception", str(e), user_info, ip_address)
        resp = make_response(render_template_string(
            HTML_TEMPLATE,
            title="เกิดข้อผิดพลาด",
            result_state="error",
            result_title="เกิดข้อผิดพลาด",
            result_message="เกิดข้อผิดพลาดที่ไม่คาดคิด กรุณาลองใหม่อีกครั้ง",
            user=user_info,
        ))
        resp.delete_cookie("oauth_state")
        return resp

class VerifyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(
            discord.ui.Button(
                label="ยืนยันตัวตนเข้าดิส",
                url=START_URL,
                style=discord.ButtonStyle.link,
                emoji="<a:emoji_125:1283873278129213471>",
            )
        )


@bot.event
async def on_ready():
    logger.info(f"Logged in as {bot.user} (ID: {bot.user.id})")

    for ch_id, label in [(LOG_CHANNEL_ID, "log"), (ERROR_LOG_CHANNEL_ID, "error log")]:
        if ch_id:
            ch = bot.get_channel(ch_id)
            if ch is None:
                logger.warning(f"ไม่พบ {label} channel ID={ch_id}")
            else:
                logger.info(f"ตั้งค่า {label} channel: #{ch.name} ({ch_id})")
        else:
            logger.warning(f"ยังไม่ได้ตั้งค่า {label.upper()}_CHANNEL_ID")

    activity = discord.Streaming(name="อยากดูหี", url="https://www.twitch.tv/Jxycop_x")
    await bot.change_presence(status=discord.Status.idle, activity=activity)

    try:
        synced = await bot.tree.sync()
        logger.info(f"Synced {len(synced)} command(s).")
    except Exception as e:
        logger.error(f"Sync command ไม่สำเร็จ: {e}")
        log_error_event("bot:sync_commands", str(e))


@bot.event
async def on_error(event_method, *args, **kwargs):
    error_detail = traceback.format_exc()
    logger.error(f"เกิดข้อผิดพลาดใน event '{event_method}': {error_detail}")
    log_error_event(f"discord_event:{event_method}", error_detail)


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    logger.error(f"Slash command error ({interaction.command}): {error}")
    log_error_event(f"slash_command:{interaction.command}", str(error))
    if interaction.response.is_done():
        await interaction.followup.send("❌ เกิดข้อผิดพลาด กรุณาลองใหม่อีกครั้ง", ephemeral=True)
    else:
        await interaction.response.send_message("❌ เกิดข้อผิดพลาด กรุณาลองใหม่อีกครั้ง", ephemeral=True)


@bot.tree.command(name="setup", description="ส่งหน้าต่างยืนยันตัวตนสำหรับสมาชิก")
@app_commands.checks.has_permissions(administrator=True)
async def setup(interaction: discord.Interaction):
    embed = discord.Embed(
        title="⚙️ STIF SHOP",
        description=f"🛒   บอทรับยศ 24 ชั่วโมง\n\n"
                    f"📥 กดปุ่มข้างล่างเพื่อรับยศ <@&{ROLE_ID}>",
        color=discord.Color(0x000000),
    )
    embed.set_footer(
        text="🟢• STIF SHOP • ระบบรับยศ",
        icon_url="https://media.tenor.com/bhC8X-tsTK4AAAAi/tspchan1-lick.gif",
    )
    embed.set_image(
        url="https://images-ext-1.discordapp.net/external/UZlJhcpilRkbJAUtbbLfM3I8NByAJj3W2YYl-lZdCMs/https/i.postimg.cc/8PFsC2cg/im-age.png?format=webp&quality=lossless"
    )
    embed.set_thumbnail(url="https://media.tenor.com/bhC8X-tsTK4AAAAi/tspchan1-lick.gif")
    await interaction.response.send_message("✅ สร้างปุ่มยืนยันตัวตนสำเร็จ!", ephemeral=True)
    await interaction.channel.send(embed=embed, view=VerifyView())


def run_web():
    port = int(os.environ.get("PORT", "5000"))
    try:
        from waitress import serve
        logger.info(f"เริ่ม production server (waitress) ที่พอร์ต {port}")
        serve(app, host="0.0.0.0", port=port, threads=8)
    except ImportError:
        logger.warning("ไม่พบ waitress — fallback ไปใช้ Flask dev server")
        try:
            app.run(host="0.0.0.0", port=port)
        except Exception as e:
            logger.error(f"Flask dev server ล่ม: {e}\n{traceback.format_exc()}")
    except Exception as e:
        logger.error(f"Waitress server ล่ม: {e}\n{traceback.format_exc()}")


if __name__ == "__main__":
    logger.info("กำลังเริ่มระบบ...")
    t = threading.Thread(target=run_web)
    t.daemon = True
    t.start()

    try:
        bot.run(BOT_TOKEN)
    except Exception as e:
        logger.error(f"บอทหยุดทำงานเนื่องจากข้อผิดพลาด: {e}\n{traceback.format_exc()}")
