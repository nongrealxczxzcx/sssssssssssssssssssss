import os
import threading
import datetime
import sqlite3
import discord
from discord import app_commands
from discord.ext import commands
from flask import Flask, redirect, request, render_template_string, session, jsonify
import requests
import logging
from collections import deque

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CLIENT_ID = os.environ.get("CLIENT_ID")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET")
REDIRECT_URI = "https://stifshop.up.railway.app/callback"

GUILD_ID = 1207514483527000084
ROLE_ID = 1211224793060478976

WEBHOOK_SUCCESS = "https://discord.com/api/webhooks/1540031111223189701/KhD_TF8YMxmRih4KQCH-MtBnTy74Qcodk7trYCqjy7_z6-6zQ8frXd8dJX-FOaZ1MO7X"
WEBHOOK_ERROR = "https://discord.com/api/webhooks/1540065078278365204/8MNh3CWoP4GUM_8k2WLw53H5EumtDUY7p-uMTQ1kvCD30zxFS7VadBlMfRchuBjoVsX3"

# โลโก้ที่ใช้แสดงในหน้า Admin Dashboard (สิ่งที่เคย hardcode ไว้ในเทมเพลตตรงๆ
# ตอนนี้ย้ายมาไว้เป็นตัวแปรที่นี่ แล้วส่งเข้า template ผ่าน logo_url แทน
# เพราะเดิมเทมเพลตเช็ค {% if logo_url %} แต่ไม่เคยมีการส่ง logo_url เข้าไปเลย
# เลยตกไป else แสดงไอคอนโล่ SVG เดิมทุกครั้ง)
BRAND_LOGO_URL = "https://images-ext-1.discordapp.net/external/wsyQrdpI7DwJnP-HyLwmBThFVdwmGd6QdhWAqD8_zmo/https/cdn.discordapp.com/avatars/1183718234806038563/ea310ab0a655ae6820b3021bbc93d734.png?format=webp&quality=lossless"

if not BOT_TOKEN or not CLIENT_SECRET:
    raise RuntimeError(
        "กรุณาตั้งค่า BOT_TOKEN และ CLIENT_SECRET เป็น environment variable ก่อนรัน"
    )

LOG_BUFFER_MAXLEN = 300
log_buffer = deque(maxlen=LOG_BUFFER_MAXLEN)

class MemoryLogHandler(logging.Handler):
    """เก็บ log ล่าสุดไว้ใน memory เพื่อโชว์แบบ live ในหน้า admin dashboard"""
    def emit(self, record):
        try:
            log_buffer.append({
                "time": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                "level": record.levelname,
                "message": self.format(record),
            })
        except Exception:
            pass

logger = logging.getLogger("stifshop")
logger.setLevel(logging.INFO)
_stream_handler = logging.StreamHandler()
_stream_handler.setFormatter(logging.Formatter("%(message)s"))
_memory_handler = MemoryLogHandler()
_memory_handler.setFormatter(logging.Formatter("%(message)s"))
logger.addHandler(_stream_handler)
logger.addHandler(_memory_handler)
logger.propagate = False

def init_db():
    conn = sqlite3.connect("verifications.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS verified_users (
            user_id TEXT PRIMARY KEY,
            username TEXT,
            global_name TEXT,
            avatar_url TEXT,
            verified_at TEXT,
            role_name TEXT,
            role_color TEXT
        )
    """)
    conn.commit()

    # Migration: เผื่อฐานข้อมูลเก่าที่ยังไม่มีคอลัมน์ role_name / role_color
    cursor.execute("PRAGMA table_info(verified_users)")
    existing_cols = {row[1] for row in cursor.fetchall()}
    if "role_name" not in existing_cols:
        cursor.execute("ALTER TABLE verified_users ADD COLUMN role_name TEXT")
    if "role_color" not in existing_cols:
        cursor.execute("ALTER TABLE verified_users ADD COLUMN role_color TEXT")
    conn.commit()
    conn.close()

init_db()

THAI_MONTHS = [
    "", "ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.",
    "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค.",
]
 
def thai_date(dt=None):
    dt = dt or datetime.datetime.utcnow()
    return f"{dt.day} {THAI_MONTHS[dt.month]} {dt.year + 543}"

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
<title>{{ title | default('ระบบยืนยันตัวตน STIF SHOP') }}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Outfit:wght@450;500;600;700&display=swap" rel="stylesheet">
<style>
  :root {
    --bg-base: #050508;
    --card-bg: rgba(13, 15, 22, 0.7);
    --border-glow: rgba(35, 165, 89, 0.3);
    --accent: #23a559;
    --accent-glow: rgba(35, 165, 89, 0.25);
    --text-main: #ffffff;
    --text-muted: #9ba1a6;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }
  html, body {
    height: 100%;
    min-height: 100dvh;
    background-color: var(--bg-base);
    font-family: 'Plus Jakarta Sans', 'Outfit', sans-serif;
    color: var(--text-main);
    overflow-x: hidden;
  }
  body {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 24px 16px;
    position: relative;
  }
  .bg-mesh {
    position: fixed;
    inset: 0;
    z-index: 1;
    pointer-events: none;
    background: 
      radial-gradient(circle at 50% 10%, rgba(35, 165, 89, 0.15), transparent 45%),
      radial-gradient(circle at 90% 90%, rgba(88, 101, 242, 0.12), transparent 40%),
      radial-gradient(circle at 10% 80%, rgba(15, 23, 42, 0.8), transparent 60%);
  }
  .wrapper {
    position: relative;
    z-index: 10;
    width: 100%;
    max-width: 400px;
  }
  .main-card {
    background: var(--card-bg);
    backdrop-filter: blur(24px);
    -webkit-backdrop-filter: blur(24px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 28px;
    padding: 32px 24px;
    box-shadow: 0 30px 60px rgba(0, 0, 0, 0.7), 0 0 50px rgba(35, 165, 89, 0.08);
    text-align: center;
    animation: cardAppear 0.7s cubic-bezier(0.16, 1, 0.3, 1) forwards;
  }
  @keyframes cardAppear {
    from { opacity: 0; transform: translateY(20px) scale(0.97); }
    to { opacity: 1; transform: translateY(0) scale(1); }
  }
  .phase { display: none; }
  .phase.active { display: block; animation: fadeIn 0.4s ease forwards; }
  @keyframes fadeIn {
    from { opacity: 0; transform: translateY(6px); }
    to { opacity: 1; transform: translateY(0); }
  }
  .loader-box {
    position: relative;
    width: 80px;
    height: 80px;
    margin: 0 auto 24px;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .spinner {
    position: absolute;
    inset: 0;
    border-radius: 50%;
    border: 3px solid rgba(255, 255, 255, 0.05);
    border-top-color: var(--accent);
    animation: spin 0.9s cubic-bezier(0.5, 0.1, 0.4, 0.9) infinite;
  }
  @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
  .loader-dot {
    width: 10px;
    height: 10px;
    background: var(--accent);
    border-radius: 50%;
    box-shadow: 0 0 12px var(--accent);
    animation: scalePulse 1s ease-in-out infinite alternate;
  }
  @keyframes scalePulse { from { transform: scale(0.8); opacity: 0.5; } to { transform: scale(1.2); opacity: 1; } }
  .brand-tag {
    font-size: 0.7rem;
    font-weight: 800;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: var(--accent);
    margin-bottom: 10px;
  }
  .title {
    font-size: 1.25rem;
    font-weight: 700;
    color: #fff;
    margin-bottom: 6px;
  }
  .subtitle {
    font-size: 0.85rem;
    color: var(--text-muted);
    line-height: 1.5;
    margin-bottom: 24px;
  }
  .profile-container {
    background: linear-gradient(180deg, rgba(20, 22, 30, 0.95) 0%, rgba(11, 13, 18, 0.98) 100%);
    border-radius: 20px;
    overflow: hidden;
    text-align: left;
    border: 1px solid rgba(255, 255, 255, 0.06);
    box-shadow: 0 16px 32px rgba(0, 0, 0, 0.5);
    margin-bottom: 20px;
  }
  .profile-banner {
    height: 90px;
    background: linear-gradient(135deg, rgba(35, 165, 89, 0.3) 0%, rgba(88, 101, 242, 0.15) 100%);
    position: relative;
    padding: 12px;
    display: flex;
    justify-content: flex-end;
    align-items: flex-start;
  }
  .verified-pill {
    background: rgba(35, 165, 89, 0.15);
    backdrop-filter: blur(8px);
    border: 1px solid rgba(35, 165, 89, 0.4);
    padding: 4px 10px;
    border-radius: 20px;
    display: flex;
    align-items: center;
    gap: 5px;
    font-size: 0.65rem;
    font-weight: 700;
    color: #2ecc71;
    letter-spacing: 0.5px;
  }
  .verified-pill svg { width: 10px; height: 10px; fill: #2ecc71; }
  .profile-body {
    padding: 0 16px 16px;
    position: relative;
  }
  .avatar-row {
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    margin-top: -38px;
    margin-bottom: 10px;
  }
  .avatar-wrap { position: relative; }
  .user-avatar {
    width: 74px;
    height: 74px;
    border-radius: 50%;
    border: 4px solid #0d0f14;
    object-fit: cover;
    box-shadow: 0 6px 16px rgba(0,0,0,0.5);
  }
  .status-dot {
    position: absolute;
    bottom: 4px;
    right: 4px;
    width: 14px;
    height: 14px;
    background: #23a559;
    border: 3px solid #0d0f14;
    border-radius: 50%;
  }
  .badge-tag {
    background: rgba(88, 101, 242, 0.12);
    border: 1px solid rgba(88, 101, 242, 0.25);
    color: #8ea1e1;
    font-size: 0.68rem;
    font-weight: 700;
    padding: 3px 10px;
    border-radius: 12px;
  }
  .user-name {
    font-size: 1.1rem;
    font-weight: 700;
    color: #ffffff;
    margin-bottom: 2px;
  }
  .user-handle {
    font-size: 0.78rem;
    color: var(--text-muted);
    margin-bottom: 14px;
  }
  .details-box {
    background: rgba(255, 255, 255, 0.02);
    border: 1px solid rgba(255, 255, 255, 0.04);
    border-radius: 12px;
    padding: 10px 14px;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .detail-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-size: 0.78rem;
  }
  .detail-label { color: var(--text-muted); }
  .role-badge-inline {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(255, 255, 255, 0.04);
    padding: 3px 8px;
    border-radius: 6px;
    color: #fff;
    font-weight: 600;
  }
  .role-color-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
  }
  .btn-primary {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    width: 100%;
    padding: 13px;
    background: linear-gradient(135deg, #2ecc71 0%, var(--accent) 100%);
    color: #fff;
    font-weight: 700;
    font-size: 0.92rem;
    border-radius: 14px;
    text-decoration: none;
    border: 1px solid rgba(255, 255, 255, 0.15);
    box-shadow: 0 8px 20px rgba(35, 165, 89, 0.35);
    transition: all 0.2s ease;
    cursor: pointer;
  }
  .btn-primary:hover {
    transform: translateY(-1px);
    box-shadow: 0 10px 25px rgba(35, 165, 89, 0.5);
  }
  .confetti-box {
    position: absolute;
    inset: 0;
    pointer-events: none;
    overflow: hidden;
    z-index: 5;
  }
  .confetti {
    position: absolute;
    top: -10px;
    width: 7px;
    height: 10px;
    border-radius: 2px;
    animation: fall linear forwards;
  }
  @keyframes fall {
    0% { transform: translateY(0) rotate(0deg); opacity: 1; }
    100% { transform: translateY(320px) rotate(540deg); opacity: 0; }
  }
</style>
</head>
<body>
  <div class="bg-mesh"></div>
  <div class="wrapper">
    <div class="main-card">
      <div class="phase active" id="phase-loading">
        <div class="brand-tag">STIF SHOP SYSTEM</div>
        <div class="loader-box">
          <div class="spinner"></div>
          <div class="loader-dot"></div>
        </div>
        <div class="title">{{ title | default('กำลังตรวจสอบข้อมูล') }}</div>
        <div class="subtitle">ระบบกำลังตรวจสอบสิทธิ์บัญชี Discord<br>และดำเนินการเพิ่มยศให้คุณอัตโนมัติ</div>
      </div>
      <div class="phase" id="phase-success">
        <div class="confetti-box" id="confettiBox"></div>
        <div class="profile-container">
          <div class="profile-banner">
            <div class="verified-pill">
              <svg viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/></svg>
              <span>VERIFIED</span>
            </div>
          </div>
          <div class="profile-body">
            <div class="avatar-row">
              <div class="avatar-wrap">
                <img src="{{ user.avatar_url if user and user.avatar_url else 'https://cdn.discordapp.com/embed/avatars/0.png' }}" class="user-avatar" alt="Avatar">
                <div class="status-dot"></div>
              </div>
              <div class="badge-tag">MEMBER</div>
            </div>
            <div class="user-name">{{ user.global_name if user and user.global_name else (user.username if user else 'ผู้ใช้งานทั่วไป') }}</div>
            <div class="user-handle">@{{ user.username if user and user.username else 'username' }}</div>
            <div class="details-box">
              <div class="detail-item">
                <span class="detail-label">บทบาทที่ได้รับ</span>
                <div class="role-badge-inline">
                  <span class="role-color-dot" style="background: {{ role_color }}; box-shadow: 0 0 6px {{ role_color }};"></span>
                  <span>{{ role_name }}</span>
                </div>
              </div>
              <div class="detail-item">
                <span class="detail-label">วันที่เข้าร่วม</span>
                <span style="color: #fff; font-weight: 600;">{{ user.joined_at if user and user.joined_at else 'วันนี้' }}</span>
              </div>
            </div>
          </div>
        </div>
        <a href="{{ button_url | default('https://discord.com/app') }}" id="returnBtn" class="btn-primary">
          <span>กลับไปที่ Discord</span>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline></svg>
        </a>
      </div>
    </div>
  </div>
  <script>
    function showSuccess() {
      document.getElementById('phase-loading').classList.remove('active');
      document.getElementById('phase-success').classList.add('active');
      const box = document.getElementById('confettiBox');
      const colors = ['#23a559', '#2ecc71', '#5865f2', '#ffffff'];
      for (let i = 0; i < 30; i++) {
        const p = document.createElement('div');
        p.className = 'confetti';
        p.style.left = Math.random() * 100 + '%';
        p.style.backgroundColor = colors[Math.floor(Math.random() * colors.length)];
        p.style.animationDuration = (1.8 + Math.random() * 1.2) + 's';
        p.style.animationDelay = (Math.random() * 0.2) + 's';
        box.appendChild(p);
      }
    }
    document.getElementById('returnBtn').addEventListener('click', function(e) {
      e.preventDefault();
      const targetUrl = this.href;
      const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);
      if (isMobile) {
        window.location.href = 'discord://';
        setTimeout(function() { window.location.href = targetUrl; }, 500);
      } else {
        window.location.href = targetUrl;
      }
    });
    setTimeout(showSuccess, 3000);
  </script>
</body>
</html>
"""

ERROR_TEMPLATE = """<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>เกิดข้อผิดพลาด - STIF SHOP</title>
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@500;700&display=swap" rel="stylesheet">
<style>
  body { background: #050508; color: #fff; font-family: 'Plus Jakarta Sans', sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }
  .error-card { background: rgba(13, 15, 22, 0.8); border: 1px solid rgba(255, 75, 75, 0.2); padding: 30px; border-radius: 20px; text-align: center; max-width: 380px; width: 90%; box-shadow: 0 20px 40px rgba(0,0,0,0.6); }
  h2 { color: #ff5252; margin-bottom: 10px; font-size: 1.2rem; }
  p { color: #9ba1a6; font-size: 0.85rem; line-height: 1.5; margin-bottom: 20px; }
  .btn { display: inline-block; padding: 10px 20px; background: #23a559; color: #fff; text-decoration: none; border-radius: 10px; font-weight: 700; font-size: 0.85rem; }
</style>
</head>
<body>
  <div class="error-card">
    <h2>⚠️ เกิดข้อผิดพลาด</h2>
    <p>{{ error_message }}</p>
    <a href="/" class="btn">กลับหน้าแรก</a>
  </div>
</body>
</html>
"""

ADMIN_STATS_TEMPLATE = """<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Dashboard - STIF SHOP</title>
    <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-base: #0a0c10;
            --card-bg: rgba(17, 20, 26, 0.72);
            --card-bg-solid: rgba(15, 17, 22, 0.94);
            --gold: #f2b705;
            --gold-soft: rgba(242, 183, 5, 0.14);
            --gold-border: rgba(242, 183, 5, 0.38);
            --teal: #2dd4bf;
            --teal-soft: rgba(45, 212, 191, 0.14);
            --teal-border: rgba(45, 212, 191, 0.35);
            --red: #f87171;
            --text-main: #f5f3ee;
            --text-muted: #8d93a1;
            --border-color: rgba(255, 255, 255, 0.08);
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }
        html { scroll-behavior: smooth; }

        @media (prefers-reduced-motion: reduce) {
            *, *::before, *::after {
                animation-duration: 0.001ms !important;
                animation-iteration-count: 1 !important;
                transition-duration: 0.001ms !important;
                scroll-behavior: auto !important;
            }
        }

        body {
            background-color: var(--bg-base);
            background-image:
                linear-gradient(to right, rgba(255, 255, 255, 0.025) 1px, transparent 1px),
                linear-gradient(to bottom, rgba(255, 255, 255, 0.025) 1px, transparent 1px);
            background-size: 42px 42px, 42px 42px;
            color: var(--text-main);
            font-family: 'Plus Jakarta Sans', sans-serif;
            font-size: 16.5px;
            padding: clamp(16px, 4vw, 44px);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            position: relative;
            overflow-x: hidden;
        }

        .grain {
            position: fixed; inset: -100px; z-index: 3; pointer-events: none; opacity: 0.035;
            background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='120' height='120'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
        }

        .aurora { position: fixed; inset: 0; z-index: 0; pointer-events: none; overflow: hidden; }
        .aurora span { position: absolute; border-radius: 50%; filter: blur(100px); opacity: 0.45; }
        .aurora span:nth-child(1) {
            width: 44vw; height: 44vw; max-width: 600px; max-height: 600px; top: -16%; left: -10%;
            background: radial-gradient(circle, rgba(242,183,5,0.35), transparent 70%);
            animation: drift1 24s ease-in-out infinite;
        }
        .aurora span:nth-child(2) {
            width: 38vw; height: 38vw; max-width: 540px; max-height: 540px; bottom: -16%; right: -8%;
            background: radial-gradient(circle, rgba(45,212,191,0.32), transparent 70%);
            animation: drift2 28s ease-in-out infinite;
        }
        @keyframes drift1 { 0%,100% { transform: translate(0,0) scale(1); } 50% { transform: translate(6vw,5vh) scale(1.1); } }
        @keyframes drift2 { 0%,100% { transform: translate(0,0) scale(1); } 50% { transform: translate(-5vw,-6vh) scale(1.08); } }

        .scanline {
            position: fixed; inset: 0; z-index: 2; pointer-events: none;
            background: linear-gradient(180deg, transparent 0%, rgba(45,212,191,0.05) 50%, transparent 100%);
            height: 220px; width: 100%;
            animation: sweep 7s ease-in-out infinite;
            mix-blend-mode: screen;
        }
        @keyframes sweep {
            0% { transform: translateY(-260px); opacity: 0; }
            10% { opacity: 1; }
            90% { opacity: 1; }
            100% { transform: translateY(100vh); opacity: 0; }
        }

        #loader {
            position: fixed; inset: 0; background: var(--bg-base);
            display: flex; flex-direction: column; gap: 20px; justify-content: center; align-items: center;
            z-index: 9999; transition: opacity 0.6s ease, visibility 0.6s ease;
        }
        .seal-spin {
            width: 60px; height: 60px; position: relative;
            animation: sealTurn 1.1s cubic-bezier(0.68,-0.4,0.3,1.3) infinite;
            filter: drop-shadow(0 0 12px rgba(242,183,5,0.35));
        }
        @keyframes sealTurn { to { transform: rotate(360deg); } }
        .loader-text {
            font-family: 'JetBrains Mono', monospace; font-size: 0.78rem; color: var(--text-muted);
            letter-spacing: 2.5px; font-weight: 600; text-transform: uppercase;
            animation: fadeFlicker 1.8s ease-in-out infinite;
        }
        @keyframes fadeFlicker { 0%,100% { opacity: 0.5; } 50% { opacity: 1; } }

        .dashboard-wrapper {
            width: 100%; max-width: 1720px;
            background: linear-gradient(180deg, rgba(14, 16, 21, 0.92), rgba(8, 9, 13, 0.97));
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: clamp(20px, 3vw, 34px); padding: clamp(16px, 2.8vw, 34px);
            box-shadow: 0 60px 120px rgba(0,0,0,0.85), 0 0 110px rgba(242,183,5,0.06), inset 0 1px 0 rgba(255,255,255,0.04);
            backdrop-filter: blur(30px);
            position: relative; overflow: hidden; z-index: 1;
            opacity: 0; transform: translateY(18px);
            animation: pageIn 0.9s cubic-bezier(0.16,1,0.3,1) forwards;
            display: grid; grid-template-columns: 300px 1fr; gap: clamp(16px, 2.2vw, 32px);
        }
        .dashboard-wrapper::before {
            content: ''; position: absolute; top: 0; left: 0; width: 100%; height: 3px;
            background: linear-gradient(90deg, transparent 5%, var(--gold) 45%, var(--teal) 80%, transparent);
            background-size: 200% 100%; opacity: 0.9;
            animation: shimmerLine 6s linear infinite;
        }
        @keyframes shimmerLine { 0% { background-position: 0% 0; } 100% { background-position: -200% 0; } }
        @keyframes pageIn { to { opacity: 1; transform: translateY(0); } }


        .sidebar {
            background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 24px;
            padding: 32px 22px; display: flex; flex-direction: column; justify-content: space-between; position: relative;
        }
        .brand-area { display: flex; align-items: center; gap: 14px; margin-bottom: 8px; }
        .brand-mark {
            width: 50px; height: 50px; border-radius: 14px; flex-shrink: 0;
            background: linear-gradient(135deg, var(--gold), #d99a04);
            display: flex; align-items: center; justify-content: center;
            box-shadow: 0 10px 24px rgba(242,183,5,0.28);
        }
        .brand-mark svg { width: 24px; height: 24px; }
        .brand-mark img { width: 26px; height: 26px; object-fit: contain; display: block; }
        .brand-name { font-family: 'Space Grotesk', sans-serif; font-size: 1.5rem; font-weight: 700; letter-spacing: 0.2px; color: #fff; }
        .brand-name span {
            background: linear-gradient(90deg, var(--gold) 0%, #ffe08a 25%, var(--gold) 50%, #d99a04 75%, var(--gold) 100%);
            background-size: 250% auto; -webkit-background-clip: text; background-clip: text; color: transparent;
            animation: goldShimmer 5s linear infinite;
        }
        @keyframes goldShimmer { 0% { background-position: 0% center; } 100% { background-position: -250% center; } }
        .brand-mark { animation: markFloat 4.5s ease-in-out infinite; }
        @keyframes markFloat { 0%,100% { transform: translateY(0) rotate(0deg); } 50% { transform: translateY(-3px) rotate(-3deg); } }
        .brand-sub {
            font-family: 'JetBrains Mono', monospace; font-size: 0.72rem; color: var(--text-muted);
            letter-spacing: 2px; text-transform: uppercase; margin-bottom: 34px; padding-left: 64px; margin-top: -8px;
        }

        .nav-menu { display: flex; flex-direction: column; gap: 8px; position: relative; }
        .nav-highlight {
            position: absolute; left: 0; width: 100%; border-radius: 14px; z-index: 0;
            background: linear-gradient(135deg, var(--gold-soft), rgba(242,183,5,0.04));
            border: 1px solid var(--gold-border);
            box-shadow: 0 8px 20px rgba(242,183,5,0.1);
            transition: transform 0.45s cubic-bezier(0.16,1,0.3,1), height 0.45s cubic-bezier(0.16,1,0.3,1), opacity 0.3s ease;
            pointer-events: none; opacity: 0;
        }
        .nav-item {
            padding: 15px 18px; border-radius: 14px; font-size: 1rem; font-weight: 600;
            color: var(--text-muted); text-decoration: none; transition: color 0.25s ease, transform 0.25s ease;
            display: flex; align-items: center; gap: 14px; border: 1px solid transparent;
            position: relative; z-index: 1;
        }
        .nav-item svg { width: 20px; height: 20px; opacity: 0.85; flex-shrink: 0; transition: transform 0.3s cubic-bezier(0.34,1.56,0.64,1); }
        .nav-item.active {
            color: var(--gold); border: 1px solid transparent;
        }
        .nav-item:not(.active):hover { background: rgba(255,255,255,0.04); color: var(--text-main); transform: translateX(4px); }
        .nav-item:not(.active):hover svg { transform: translateX(2px) scale(1.06); }
        .nav-item:active { transform: scale(0.97); }

        .sidebar-footer {
            font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; color: var(--text-muted);
            border-top: 1px solid var(--border-color); padding-top: 18px;
            display: flex; flex-direction: column; gap: 8px;
        }
        .status-dot {
            display: inline-block; width: 7px; height: 7px; border-radius: 50%; background: var(--teal);
            margin-right: 7px; box-shadow: 0 0 8px var(--teal); animation: pulse 2s ease-in-out infinite;
        }
        @keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.35; } }


        .main-content { display: flex; flex-direction: column; gap: 28px; min-width: 0; }

        .topbar { display: flex; justify-content: space-between; align-items: center; padding: 4px 6px 0; }
        .topbar h1 { font-family: 'Space Grotesk', sans-serif; font-size: clamp(1.5rem, 3.4vw, 2.05rem); font-weight: 700; letter-spacing: -0.3px; }
        .topbar p { font-size: 0.98rem; color: var(--text-muted); margin-top: 6px; }
        .topbar-badge {
            font-family: 'JetBrains Mono', monospace; font-size: 0.86rem; color: var(--teal);
            background: var(--teal-soft); padding: 10px 18px; border-radius: 20px; border: 1px solid var(--teal-border);
            font-weight: 600; display: flex; align-items: center; gap: 9px; letter-spacing: 0.3px;
        }


        .stats-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 22px; }
        .stat-card {
            background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 22px;
            padding: clamp(22px, 2.6vw, 30px) clamp(22px, 2.8vw, 32px); position: relative; overflow: hidden;
            transition: transform 0.5s cubic-bezier(0.16,1,0.3,1), border-color 0.4s ease, box-shadow 0.4s ease;
            box-shadow: 0 15px 40px rgba(0,0,0,0.35);
            opacity: 0; transform: translateY(14px);
            animation: cardIn 0.7s cubic-bezier(0.16,1,0.3,1) forwards;
            transform-style: preserve-3d; will-change: transform;
        }
        .stat-card.tilting { transition: box-shadow 0.4s ease, border-color 0.4s ease; }
        .stat-card .glow-cursor {
            position: absolute; width: 220px; height: 220px; border-radius: 50%; pointer-events: none;
            background: radial-gradient(circle, var(--card-glow, var(--gold-soft)), transparent 70%);
            opacity: 0; transition: opacity 0.3s ease; transform: translate(-50%, -50%); z-index: 0;
        }
        .stat-card.tilting .glow-cursor { opacity: 0.6; }

        /* Ripple micro-interaction for clickable controls */
        .ripple-el { position: relative; overflow: hidden; }
        .ripple-dot {
            position: absolute; border-radius: 50%; background: rgba(255,255,255,0.35);
            transform: scale(0); animation: rippleOut 0.6s ease-out forwards; pointer-events: none;
        }
        @keyframes rippleOut { to { transform: scale(1); opacity: 0; } }
        .stat-card:nth-child(1) { animation-delay: 0.05s; }
        .stat-card:nth-child(2) { animation-delay: 0.15s; }
        .stat-card:nth-child(3) { animation-delay: 0.25s; }
        @keyframes cardIn { to { opacity: 1; transform: translateY(0); } }
        .stat-card::after {
            content: ''; position: absolute; top: -40%; right: -20%; width: 150px; height: 150px;
            background: radial-gradient(circle, var(--card-glow, var(--gold-soft)), transparent 70%);
            opacity: 0; transition: opacity 0.4s ease;
        }
        .stat-card:hover { box-shadow: 0 20px 50px rgba(0,0,0,0.4); }
        .stat-card:hover::after { opacity: 1; }
        .stat-card.gold:hover { border-color: var(--gold-border); }
        .stat-card.teal:hover { border-color: var(--teal-border); --card-glow: var(--teal-soft); }

        .stat-top { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 18px; position: relative; z-index: 1; }
        .flap-row, .stat-trend { position: relative; z-index: 1; }
        .stat-card h3 {
            font-family: 'JetBrains Mono', monospace; font-size: 0.76rem; letter-spacing: 1.8px;
            color: var(--text-muted); font-weight: 600; text-transform: uppercase;
        }
        .stat-icon {
            width: 40px; height: 40px; border-radius: 12px; flex-shrink: 0;
            background: var(--gold-soft); border: 1px solid var(--gold-border);
            display: flex; align-items: center; justify-content: center;
            transition: transform 0.4s cubic-bezier(0.34,1.56,0.64,1);
            animation: iconBreathe 3.6s ease-in-out infinite;
        }
        @keyframes iconBreathe { 0%,100% { transform: translateY(0) scale(1); } 50% { transform: translateY(-2px) scale(1.04); } }
        .stat-icon svg { width: 20px; height: 20px; stroke: var(--gold); }
        .stat-card.teal .stat-icon { background: var(--teal-soft); border-color: var(--teal-border); }
        .stat-card.teal .stat-icon svg { stroke: var(--teal); }
        .stat-card:hover .stat-icon { transform: rotate(-8deg) scale(1.12); animation-play-state: paused; }


        .flap-row { display: flex; align-items: baseline; gap: 1px; font-family: 'JetBrains Mono', monospace; }
        .flap-char {
            position: relative; display: inline-block; font-size: clamp(2.1rem, 5vw, 3rem); font-weight: 700;
            color: #fff; min-width: 0.62em; text-align: center;
            transform-style: preserve-3d;
        }
        .flap-char.unit { font-size: 1.3rem; color: var(--text-muted); font-weight: 600; margin-left: 3px; }
        .stat-trend { font-size: 0.86rem; color: var(--teal); margin-top: 12px; font-weight: 600; }
        .stat-card.gold .stat-trend { color: var(--gold); }


        .section-box {
            background: var(--card-bg); border-radius: 22px; overflow: hidden; border: 1px solid var(--border-color);
            box-shadow: 0 24px 55px rgba(0,0,0,0.4); flex: 1; display: flex; flex-direction: column;
            opacity: 0; transform: translateY(14px);
            animation: cardIn 0.7s cubic-bezier(0.16,1,0.3,1) forwards; animation-delay: 0.32s;
        }
        .section-header { padding: 24px 30px; border-bottom: 1px solid var(--border-color); display: flex; justify-content: space-between; align-items: center; }
        .section-eyebrow {
            font-family: 'JetBrains Mono', monospace; font-size: 0.72rem; letter-spacing: 2.2px; color: var(--text-muted);
            text-transform: uppercase; margin-bottom: 4px; display: block;
        }
        .section-title { font-family: 'Space Grotesk', sans-serif; font-size: 1.2rem; font-weight: 600; }
        .live-badge {
            font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; color: var(--teal); background: var(--teal-soft);
            padding: 7px 15px; border-radius: 20px; border: 1px solid var(--teal-border);
            display: flex; align-items: center; gap: 8px; font-weight: 600;
        }
        .live-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--teal); animation: pulse 1.6s ease-in-out infinite; }

        #list { max-height: 560px; overflow-y: auto; }
        #list::-webkit-scrollbar { width: 6px; }
        #list::-webkit-scrollbar-thumb { background: var(--gold-border); border-radius: 10px; }
        #list::-webkit-scrollbar-track { background: transparent; }

        .activity-item {
            display: flex; align-items: center; justify-content: space-between; padding: 20px 30px;
            border-bottom: 1px solid var(--border-color); transition: background 0.25s ease, padding-left 0.25s ease;
            animation: slideUp 0.6s cubic-bezier(0.16,1,0.3,1) forwards; opacity: 0;
            gap: 16px;
        }
        .activity-item:last-child { border-bottom: none; }
        @keyframes slideUp { from { transform: translateY(16px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
        .activity-item:hover { background: rgba(242,183,5,0.045); padding-left: 36px; }

        .user-info { display: flex; align-items: center; gap: 17px; min-width: 0; }

        .avatar-wrap { position: relative; flex-shrink: 0; width: 54px; height: 54px; }
        .avatar-wrap img {
            width: 100%; height: 100%; border-radius: 13px; border: 2px solid var(--border-color);
            object-fit: cover; transition: border-color 0.25s ease, transform 0.25s ease; display: block;
        }
        .activity-item:hover .avatar-wrap img { border-color: rgba(255,255,255,0.16); transform: scale(1.04); }
        .corner { position: absolute; width: 10px; height: 10px; border: 2px solid var(--gold); opacity: 0; transition: opacity 0.25s ease, transform 0.25s ease; }
        .corner.tl { top: -4px; left: -4px; border-right: none; border-bottom: none; border-radius: 4px 0 0 0; transform: translate(4px, 4px); }
        .corner.tr { top: -4px; right: -4px; border-left: none; border-bottom: none; border-radius: 0 4px 0 0; transform: translate(-4px, 4px); }
        .corner.bl { bottom: -4px; left: -4px; border-right: none; border-top: none; border-radius: 0 0 0 4px; transform: translate(4px, -4px); }
        .corner.br { bottom: -4px; right: -4px; border-left: none; border-top: none; border-radius: 0 0 4px 0; transform: translate(-4px, -4px); }
        .activity-item:hover .corner { opacity: 1; transform: translate(0, 0); }

        .avatar-badge {
            position: absolute; bottom: -3px; right: -3px; width: 19px; height: 19px;
            background: var(--gold); border-radius: 50%; border: 2px solid #101318;
            display: flex; align-items: center; justify-content: center;
            animation: stampIn 0.5s cubic-bezier(0.34,1.56,0.64,1) both;
        }
        .avatar-badge svg { width: 10px; height: 10px; stroke: #14171c; stroke-width: 3.5; }
        @keyframes stampIn { from { transform: scale(0) rotate(-35deg); opacity: 0; } to { transform: scale(1) rotate(0); opacity: 1; } }

        .user-text { min-width: 0; }
        .user-name { font-weight: 700; font-size: 1.08rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .user-handle { font-size: 0.88rem; color: var(--text-muted); margin-top: 3px; }

        .role-badge {
            display: inline-flex; align-items: center; gap: 7px; flex-shrink: 0;
            font-family: 'JetBrains Mono', monospace; font-size: 0.84rem; font-weight: 600;
            padding: 7px 14px; border-radius: 10px; letter-spacing: 0.2px;
            background: var(--role-soft, rgba(255,255,255,0.05));
            border: 1px solid var(--role-border, rgba(255,255,255,0.12));
            color: var(--role-c, var(--text-main));
        }
        .role-dot {
            width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0;
            background: var(--role-c, var(--text-muted));
            box-shadow: 0 0 6px var(--role-c, transparent);
        }

        .item-right { display: flex; align-items: center; gap: 12px; flex-shrink: 0; }

        .user-id-badge {
            font-family: 'JetBrains Mono', monospace; color: var(--gold); background: var(--gold-soft);
            padding: 7px 15px; border-radius: 10px; font-size: 0.9rem; border: 1px solid var(--gold-border);
            flex-shrink: 0; letter-spacing: 0.3px;
        }

        .empty-state { padding: 64px 30px; text-align: center; color: var(--text-muted); display: flex; flex-direction: column; align-items: center; gap: 14px; }
        .empty-state svg { width: 40px; height: 40px; stroke: var(--text-muted); opacity: 0.6; animation: floatIcon 3s ease-in-out infinite; }
        @keyframes floatIcon { 0%,100% { transform: translateY(0); } 50% { transform: translateY(-8px); } }

        .view-panel { display: none; flex-direction: column; gap: 22px; flex: 1; min-height: 0; }
        .view-panel.active { display: flex; }

        .terminal-card {
            background: #07080b; border: 1px solid var(--border-color); border-radius: 22px;
            overflow: hidden; box-shadow: 0 24px 55px rgba(0,0,0,0.5), inset 0 0 70px rgba(45,212,191,0.03);
            flex: 1; display: flex; flex-direction: column; min-height: 480px;
            opacity: 0; transform: translateY(14px);
            animation: cardIn 0.7s cubic-bezier(0.16,1,0.3,1) forwards;
        }
        .terminal-titlebar {
            display: flex; align-items: center; justify-content: space-between; gap: 14px; flex-wrap: wrap;
            padding: 19px 24px; background: linear-gradient(180deg, rgba(255,255,255,0.035), transparent);
            border-bottom: 1px solid var(--border-color);
        }
        .terminal-id { display: flex; align-items: center; gap: 14px; min-width: 0; }
        .terminal-dots { display: flex; gap: 8px; flex-shrink: 0; }
        .terminal-dots span { width: 12px; height: 12px; border-radius: 50%; display: block; }
        .terminal-dots span:nth-child(1) { background: #ff5f57; }
        .terminal-dots span:nth-child(2) { background: #febc2e; }
        .terminal-dots span:nth-child(3) { background: #28c840; }
        .terminal-path {
            font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; color: var(--text-muted);
            display: flex; align-items: center; gap: 7px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
        }
        .terminal-path .t-user { color: #7ee787; }
        .terminal-path .t-path { color: var(--gold); }
        .terminal-path .t-cmd { color: var(--text-main); }
        .terminal-filters { display: flex; gap: 6px; flex-shrink: 0; }
        .term-filter-btn {
            font-family: 'JetBrains Mono', monospace; font-size: 0.68rem; font-weight: 700; letter-spacing: 0.5px;
            padding: 6px 12px; border-radius: 8px; border: 1px solid var(--border-color); background: rgba(255,255,255,0.03);
            color: var(--text-muted); cursor: pointer; transition: all 0.2s ease;
        }
        .term-filter-btn:hover { background: rgba(255,255,255,0.07); color: var(--text-main); }
        .term-filter-btn.active { color: #08090c; background: var(--teal); border-color: var(--teal); }
        .terminal-body {
            flex: 1; padding: 18px 24px 22px; overflow-y: auto; max-height: 580px;
            font-family: 'JetBrains Mono', monospace; font-size: 0.9rem; line-height: 1.75;
            background-image: linear-gradient(rgba(45,212,191,0.015) 50%, transparent 50%);
            background-size: 100% 4px;
        }
        .terminal-body::-webkit-scrollbar { width: 6px; }
        .terminal-body::-webkit-scrollbar-thumb { background: var(--gold-border); border-radius: 10px; }
        .terminal-body::-webkit-scrollbar-track { background: transparent; }
        .term-line {
            display: flex; gap: 12px; white-space: pre-wrap; word-break: break-word;
            opacity: 0; animation: termLineIn 0.35s ease forwards; padding: 1px 0;
        }
        @keyframes termLineIn { to { opacity: 1; } }
        .term-time { color: #4a5160; flex-shrink: 0; }
        .term-level { flex-shrink: 0; font-weight: 700; letter-spacing: 0.5px; }
        .term-level.ERROR { color: var(--red); }
        .term-level.WARNING { color: #fbbf24; }
        .term-level.INFO { color: var(--teal); }
        .term-level.DEBUG { color: var(--text-muted); }
        .term-msg { color: #dbe0e8; }
        .term-cursor {
            display: inline-block; width: 8px; height: 15px; background: var(--teal); margin-left: 2px;
            animation: cursorBlink 1s step-end infinite; vertical-align: -2px;
        }
        @keyframes cursorBlink { 50% { opacity: 0; } }
        .term-empty { color: #565d68; font-style: italic; padding: 6px 0; }
        .terminal-footer {
            padding: 10px 20px; border-top: 1px solid var(--border-color);
            display: flex; align-items: center; justify-content: space-between;
            font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: var(--text-muted);
        }
        .terminal-footer .live-badge { padding: 4px 11px; }

        #notification-container { position: fixed; top: 28px; right: 28px; z-index: 1000; display: flex; flex-direction: column; gap: 12px; width: min(400px, calc(100vw - 40px)); }
        .notify-box {
            background: rgba(14, 16, 21, 0.97); border: 1px solid var(--nc-border, var(--gold-border));
            padding: 17px 19px; border-radius: 16px;
            box-shadow: 0 20px 45px rgba(0,0,0,0.65);
            display: flex; align-items: flex-start; gap: 13px;
            backdrop-filter: blur(14px); position: relative; overflow: hidden;
            animation: notifyIn 0.5s cubic-bezier(0.16,1,0.3,1) forwards; cursor: pointer;
        }
        .notify-box:hover { transform: translateX(-3px); }
        .notify-box.leaving { animation: notifyOut 0.4s cubic-bezier(0.4,0,1,1) forwards; }
        @keyframes notifyIn { from { transform: translateX(120%) scale(0.9); opacity: 0; } to { transform: translateX(0) scale(1); opacity: 1; } }
        @keyframes notifyOut { to { transform: translateX(120%) scale(0.9); opacity: 0; } }

        .notify-icon {
            width: 42px; height: 42px; background: var(--nc-soft, var(--gold-soft)); border-radius: 12px;
            display: flex; align-items: center; justify-content: center; flex-shrink: 0;
            animation: stampImpact 0.55s cubic-bezier(0.34,1.56,0.64,1) 0.08s both;
        }
        .notify-icon svg { width: 19px; height: 19px; stroke: var(--nc, var(--gold)); stroke-width: 2.4; }
        @keyframes stampImpact { from { transform: scale(1.9) rotate(-20deg); opacity: 0; } 70% { transform: scale(0.94) rotate(2deg); } to { transform: scale(1) rotate(0); opacity: 1; } }
        .notify-content { display: flex; flex-direction: column; gap: 4px; min-width: 0; padding-top: 1px; }
        .notify-title { font-weight: 700; font-size: 1rem; color: #fff; }
        .notify-desc { font-size: 0.87rem; color: var(--text-muted); line-height: 1.45; }
        .notify-close {
            position: absolute; top: 10px; right: 10px; width: 20px; height: 20px; border-radius: 50%;
            display: flex; align-items: center; justify-content: center; color: var(--text-muted);
            font-size: 0.65rem; opacity: 0; transition: opacity 0.2s ease, background 0.2s ease;
        }
        .notify-box:hover .notify-close { opacity: 1; }
        .notify-close:hover { background: rgba(255,255,255,0.08); color: #fff; }
        .notify-progress {
            position: absolute; bottom: 0; left: 0; height: 3px;
            background: linear-gradient(90deg, var(--nc, var(--gold)), var(--teal));
            width: 100%; animation: progressAnim linear forwards; animation-duration: var(--dur, 4s);
        }
        @keyframes progressAnim { to { width: 0%; } }

        @media (max-width: 900px) {
            .dashboard-wrapper { grid-template-columns: 1fr; }
            .sidebar { flex-direction: row; align-items: center; padding: 14px 16px; gap: 16px; }
            .sidebar > div:first-child { display: flex; align-items: center; gap: 18px; flex-shrink: 0; }
            .brand-sub { display: none; }
            .nav-menu {
                flex-direction: row; gap: 6px; overflow-x: auto; scrollbar-width: none;
                -ms-overflow-style: none; padding-bottom: 2px;
            }
            .nav-menu::-webkit-scrollbar { display: none; }
            .nav-item { white-space: nowrap; padding: 11px 16px; font-size: 0.92rem; }
            .nav-highlight { display: none; }
            .nav-item.active {
                background: linear-gradient(135deg, var(--gold-soft), rgba(242,183,5,0.04));
                border: 1px solid var(--gold-border);
            }
            .sidebar-footer {
                display: flex; flex-direction: row; align-items: center; gap: 14px;
                border-top: none; border-left: 1px solid var(--border-color);
                padding-top: 0; padding-left: 16px; margin-left: auto; flex-shrink: 0;
            }
            .sidebar-footer div:last-child { display: none; }
        }

        @media (max-width: 640px) {
            .stats-grid {
                grid-template-columns: none;
                grid-auto-flow: column;
                grid-auto-columns: 78%;
                overflow-x: auto;
                scroll-snap-type: x mandatory;
                scrollbar-width: none; -ms-overflow-style: none;
                padding-bottom: 2px; margin: 0 -2px;
            }
            .stats-grid::-webkit-scrollbar { display: none; }
            .stat-card { scroll-snap-align: start; }
        }

        @media (max-width: 560px) {
            #notification-container { top: 12px; right: 12px; left: 12px; width: auto; }
            .topbar { flex-wrap: wrap; gap: 10px; }
            .section-header { padding: 18px 20px; }
            .activity-item { padding: 15px 20px; flex-wrap: wrap; }
            .activity-item:hover { padding-left: 24px; }
            .item-right { margin-left: auto; }
            .user-id-badge { font-size: 0.74rem; padding: 5px 10px; }
            .role-badge { font-size: 0.72rem; padding: 5px 9px; }
        }

        /* Floating scroll-to-top, appears once the page has scrolled */
        .scroll-top-btn {
            position: fixed; bottom: 26px; right: 26px; z-index: 500;
            width: 52px; height: 52px; border-radius: 16px;
            background: rgba(17, 20, 26, 0.9); border: 1px solid var(--gold-border);
            display: flex; align-items: center; justify-content: center; cursor: pointer;
            box-shadow: 0 12px 30px rgba(0,0,0,0.5);
            opacity: 0; visibility: hidden; transform: translateY(10px) scale(0.9);
            transition: opacity 0.3s ease, transform 0.3s cubic-bezier(0.34,1.56,0.64,1), visibility 0.3s ease;
            backdrop-filter: blur(10px);
        }
        .scroll-top-btn.show { opacity: 1; visibility: visible; transform: translateY(0) scale(1); }
        .scroll-top-btn svg { width: 18px; height: 18px; stroke: var(--gold); }
        .scroll-top-btn:hover { border-color: var(--gold); transform: translateY(-2px) scale(1.04); }

        a:focus-visible, button:focus-visible, .notify-box:focus-visible {
            outline: 2px solid var(--gold); outline-offset: 2px;
        }

        .section-box.pulse-highlight { animation: sectionPulse 1.4s ease-out; }
        @keyframes sectionPulse {
            0% { box-shadow: 0 20px 45px rgba(0,0,0,0.4), 0 0 0 1px var(--gold-border), 0 0 40px rgba(242,183,5,0.25); }
            100% { box-shadow: 0 20px 45px rgba(0,0,0,0.4); }
        }

        /* Settings modal */
        .modal-overlay {
            position: fixed; inset: 0; z-index: 2000; display: flex; align-items: center; justify-content: center;
            background: rgba(6, 7, 10, 0.72); backdrop-filter: blur(6px);
            opacity: 0; visibility: hidden; transition: opacity 0.3s ease, visibility 0.3s ease;
            padding: 20px;
        }
        .modal-overlay.open { opacity: 1; visibility: visible; }
        .modal-card {
            width: 100%; max-width: 480px;
            background: linear-gradient(180deg, rgba(17,20,26,0.98), rgba(11,13,17,0.99));
            border: 1px solid var(--border-color); border-radius: 24px;
            box-shadow: 0 40px 90px rgba(0,0,0,0.7), 0 0 60px rgba(242,183,5,0.06);
            padding: 30px 30px 26px; position: relative; overflow: hidden;
            transform: translateY(18px) scale(0.97); opacity: 0;
            transition: transform 0.35s cubic-bezier(0.16,1,0.3,1), opacity 0.35s ease;
        }
        .modal-overlay.open .modal-card { transform: translateY(0) scale(1); opacity: 1; }
        .modal-card::before {
            content: ''; position: absolute; top: 0; left: 0; width: 100%; height: 3px;
            background: linear-gradient(90deg, transparent 5%, var(--gold) 45%, var(--teal) 80%, transparent);
        }
        .modal-head { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 22px; }
        .modal-eyebrow { font-family: 'JetBrains Mono', monospace; font-size: 0.66rem; letter-spacing: 2px; color: var(--text-muted); text-transform: uppercase; display: block; margin-bottom: 4px; }
        .modal-title { font-family: 'Space Grotesk', sans-serif; font-size: 1.3rem; font-weight: 700; }
        .modal-close {
            width: 30px; height: 30px; border-radius: 9px; background: rgba(255,255,255,0.04); border: 1px solid var(--border-color);
            color: var(--text-muted); display: flex; align-items: center; justify-content: center; cursor: pointer;
            transition: all 0.2s ease; flex-shrink: 0;
        }
        .modal-close:hover { background: rgba(255,255,255,0.08); color: #fff; }

        .field-group { margin-bottom: 18px; }
        .field-label {
            font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; letter-spacing: 1px; color: var(--text-muted);
            text-transform: uppercase; display: block; margin-bottom: 8px;
        }
        .field-input {
            width: 100%; background: rgba(255,255,255,0.03); border: 1px solid var(--border-color); border-radius: 12px;
            padding: 13px 16px; color: var(--text-main); font-family: 'Plus Jakarta Sans', sans-serif; font-size: 0.96rem;
            transition: border-color 0.2s ease, background 0.2s ease;
        }
        .field-input:focus { outline: none; border-color: var(--gold-border); background: rgba(255,255,255,0.05); }

        .toggle-row {
            display: flex; align-items: center; justify-content: space-between;
            padding: 13px 0; border-bottom: 1px solid var(--border-color);
        }
        .toggle-row:last-of-type { border-bottom: none; }
        .toggle-label { font-size: 0.88rem; font-weight: 600; }
        .toggle-desc { font-size: 0.76rem; color: var(--text-muted); margin-top: 2px; }
        .switch { position: relative; width: 42px; height: 24px; flex-shrink: 0; cursor: pointer; }
        .switch input { opacity: 0; width: 0; height: 0; }
        .switch-track {
            position: absolute; inset: 0; background: rgba(255,255,255,0.1); border-radius: 20px;
            transition: background 0.25s ease; border: 1px solid var(--border-color);
        }
        .switch-track::before {
            content: ''; position: absolute; width: 18px; height: 18px; left: 2px; top: 2px;
            background: #cfd3da; border-radius: 50%; transition: transform 0.25s cubic-bezier(0.34,1.56,0.64,1), background 0.25s ease;
        }
        .switch input:checked + .switch-track { background: var(--gold-soft); border-color: var(--gold-border); }
        .switch input:checked + .switch-track::before { transform: translateX(18px); background: var(--gold); }

        .modal-actions { display: flex; gap: 10px; margin-top: 24px; }
        .btn {
            flex: 1; padding: 12px 16px; border-radius: 12px; font-weight: 700; font-size: 0.88rem;
            border: 1px solid var(--border-color); cursor: pointer; transition: all 0.2s ease;
            font-family: 'Plus Jakarta Sans', sans-serif;
        }
        .btn-primary { background: linear-gradient(135deg, var(--gold), #d99a04); color: #14171c; border: none; }
        .btn-primary:hover { filter: brightness(1.08); transform: translateY(-1px); }
        .btn-ghost { background: rgba(255,255,255,0.03); color: var(--text-muted); }
        .btn-ghost:hover { background: rgba(255,255,255,0.06); color: var(--text-main); }
    </style>
</head>
<body>

    <div class="aurora"><span></span><span></span></div>
    <div class="scanline"></div>
    <div class="grain"></div>

    <!-- Loader -->
    <div id="loader">
        <svg class="seal-spin" viewBox="0 0 60 60" fill="none">
            <circle cx="30" cy="30" r="26" stroke="rgba(255,255,255,0.08)" stroke-width="3"/>
            <path d="M30 4 A26 26 0 0 1 56 30" stroke="#f2b705" stroke-width="3" stroke-linecap="round"/>
            <path d="M30 56 A26 26 0 0 1 4 30" stroke="#2dd4bf" stroke-width="3" stroke-linecap="round"/>
        </svg>
        <div class="loader-text">Verifying Session</div>
    </div>

    <div id="notification-container"></div>

    <div class="modal-overlay" id="settings-overlay">
        <div class="modal-card">
            <div class="modal-head">
                <div>
                    <span class="modal-eyebrow">CONFIG // GENERAL</span>
                    <span class="modal-title">System Settings</span>
                </div>
                <div class="modal-close" id="settings-close">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><path d="M18 6 6 18M6 6l12 12"/></svg>
                </div>
            </div>

            <div class="field-group">
                <label class="field-label" for="setting-notif-title">Notification title</label>
                <input class="field-input" type="text" id="setting-notif-title" value="ระบบสำเร็จ">
            </div>
            <div class="field-group" style="margin-bottom: 20px;">
                <label class="field-label" for="setting-notif-msg">Notification message</label>
                <input class="field-input" type="text" id="setting-notif-msg" value="โหลดข้อมูล Dashboard เรียบร้อยแล้ว">
            </div>

            <div class="toggle-row">
                <div>
                    <div class="toggle-label">Scanline effect</div>
                    <div class="toggle-desc">แถบสแกนที่กวาดผ่านหน้าจอ</div>
                </div>
                <label class="switch">
                    <input type="checkbox" id="setting-scanline" checked>
                    <span class="switch-track"></span>
                </label>
            </div>
            <div class="toggle-row">
                <div>
                    <div class="toggle-label">Ambient glow</div>
                    <div class="toggle-desc">แสงพื้นหลังทอง/เขียวมิ้นท์</div>
                </div>
                <label class="switch">
                    <input type="checkbox" id="setting-aurora" checked>
                    <span class="switch-track"></span>
                </label>
            </div>

            <div class="modal-actions">
                <button class="btn btn-ghost ripple-el" id="settings-cancel">Cancel</button>
                <button class="btn btn-primary ripple-el" id="settings-save">Save changes</button>
            </div>
        </div>
    </div>

    <div class="dashboard-wrapper">

        <aside class="sidebar">
            <div>
                <div class="brand-area">
                    <div class="brand-mark">
                        {% if logo_url %}
                        <img src="{{ logo_url }}" alt="STIFSHOP logo">
                        {% else %}
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#14171c" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M12 2 3 6v6c0 5 3.8 8.7 9 10 5.2-1.3 9-5 9-10V6l-9-4Z"/>
                            <path d="m9 12 2 2 4-4"/>
                        </svg>
                        {% endif %}
                    </div>
                    <div class="brand-name">STIF<span>SHOP</span></div>
                </div>
                <div class="brand-sub">Verification Console</div>
                <div class="nav-menu">
                    <span class="nav-highlight" id="nav-highlight"></span>
                    <a href="#" class="nav-item ripple-el active" id="nav-dashboard">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="9" rx="1.5"/><rect x="14" y="3" width="7" height="5" rx="1.5"/><rect x="14" y="12" width="7" height="9" rx="1.5"/><rect x="3" y="16" width="7" height="5" rx="1.5"/></svg>
                        Dashboard
                    </a>
                    <a href="#" class="nav-item ripple-el" id="nav-verified">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
                        Verified
                    </a>
                    <a href="#" class="nav-item ripple-el" id="nav-logs">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="m6 9 3 3-3 3"/><path d="M12 15h6"/></svg>
                        Logs
                    </a>
                    <a href="#" class="nav-item ripple-el" id="nav-settings">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1Z"/></svg>
                        Settings
                    </a>
                </div>
            </div>
            <div class="sidebar-footer">
                <div><span class="status-dot"></span>STATUS.ONLINE</div>
                <div>BUILD v3.1</div>
            </div>
        </aside>

        <main class="main-content">

            <div class="topbar">
                <div>
                    <h1>ภาพรวมระบบ</h1>
                    <p>สรุปข้อมูลผู้ใช้และกิจกรรมล่าสุด</p>
                </div>
                <div class="topbar-badge"><span class="live-dot"></span> ระบบทำงานปกติ</div>
            </div>

            <div class="view-panel active" id="view-dashboard">
                <div class="stats-grid">
                    <div class="stat-card gold">
                        <span class="glow-cursor"></span>
                        <div class="stat-top">
                            <h3>Total Verified</h3>
                            <div class="stat-icon">
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/></svg>
                            </div>
                        </div>
                        <div class="flap-row" data-flap="{{ total_count }}"></div>
                        <div class="stat-trend">ผู้ใช้ทั้งหมดที่ยืนยันแล้ว</div>
                    </div>
                    <div class="stat-card gold">
                        <span class="glow-cursor"></span>
                        <div class="stat-top">
                            <h3>Today Verified</h3>
                            <div class="stat-icon">
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/></svg>
                            </div>
                        </div>
                        <div class="flap-row" data-flap="{{ today_count }}"></div>
                        <div class="stat-trend">ยืนยันตัวตนวันนี้</div>
                    </div>
                    <div class="stat-card teal">
                        <span class="glow-cursor"></span>
                        <div class="stat-top">
                            <h3>System Ping</h3>
                            <div class="stat-icon">
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M13 2 3 14h9l-1 8 10-12h-9l1-8Z"/></svg>
                            </div>
                        </div>
                        <div class="flap-row" data-flap="12" data-unit="ms"></div>
                        <div class="stat-trend">การตอบสนองของระบบ</div>
                    </div>
                </div>

                <div class="section-box" id="verified-section">
                    <div class="section-header">
                        <div>
                            <span class="section-eyebrow">LOG // ACTIVITY</span>
                            <span class="section-title" id="verified-section-title">Recent Verifications</span>
                        </div>
                        <span class="live-badge"><span class="live-dot"></span> Live Updates</span>
                    </div>
                    <div id="list">
                        {% for u in users %}
                        <div class="activity-item" style="animation-delay: {{ loop.index * 0.06 }}s;">
                            <div class="user-info">
                                <div class="avatar-wrap">
                                    <img src="{{ u[3] or 'https://cdn.discordapp.com/embed/avatars/0.png' }}" alt="avatar">
                                    <span class="corner tl"></span><span class="corner tr"></span><span class="corner bl"></span><span class="corner br"></span>
                                    <div class="avatar-badge">
                                        <svg viewBox="0 0 24 24" fill="none" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>
                                    </div>
                                </div>
                                <div class="user-text">
                                    <div class="user-name">{{ u[2] or u[1] }}</div>
                                    <div class="user-handle">@{{ u[1] }}</div>
                                </div>
                            </div>
                            <div class="item-right">
                                {% if u[5] %}
                                <span class="role-badge" style="--role-c: {{ u[6] or '#f2b705' }}; --role-soft: {{ u[6] or '#f2b705' }}22; --role-border: {{ u[6] or '#f2b705' }}55;">
                                    <span class="role-dot"></span>{{ u[5] }}
                                </span>
                                {% endif %}
                                <span class="user-id-badge" data-utc="{{ u[4] }}">{{ u[4] }}</span>
                            </div>
                        </div>
                        {% else %}
                        <div class="empty-state">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M3 7h18M3 12h18M3 17h18" opacity="0.5"/><rect x="3" y="4" width="18" height="16" rx="2"/></svg>
                            <div>ยังไม่มีข้อมูลผู้ใช้</div>
                        </div>
                        {% endfor %}
                    </div>
                </div>
            </div>

            <div class="view-panel" id="view-logs">
                <div class="terminal-card" id="terminal-card">
                    <div class="terminal-titlebar">
                        <div class="terminal-id">
                            <div class="terminal-dots"><span></span><span></span><span></span></div>
                            <div class="terminal-path">
                                <span class="t-user">admin@stifshop</span><span style="opacity:.4">:</span><span class="t-path">~/logs</span><span style="opacity:.4">$</span><span class="t-cmd">tail -f error.log</span>
                            </div>
                        </div>
                        <div class="terminal-filters">
                            <button class="term-filter-btn ripple-el active" data-filter="ALL">ALL</button>
                            <button class="term-filter-btn ripple-el" data-filter="ERROR">ERROR</button>
                            <button class="term-filter-btn ripple-el" data-filter="WARNING">WARN</button>
                            <button class="term-filter-btn ripple-el" data-filter="INFO">INFO</button>
                        </div>
                    </div>
                    <div class="terminal-body" id="terminal-body">
                        <div class="term-empty">// กำลังเชื่อมต่อ log stream...</div>
                    </div>
                    <div class="terminal-footer">
                        <span id="terminal-count">0 entries</span>
                        <span class="live-badge"><span class="live-dot"></span> Live Updates</span>
                    </div>
                </div>
            </div>

        </main>
    </div>

    <button class="scroll-top-btn ripple-el" id="scroll-top-btn" aria-label="Scroll to top">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 19V5M5 12l7-7 7 7"/></svg>
    </button>

    <script>
        function toThaiTime(str) {
            const m = String(str).match(/^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2}):(\d{2})/);
            if (!m) return str;
            const utcMs = Date.UTC(+m[1], +m[2] - 1, +m[3], +m[4], +m[5], +m[6]);
            const thaiMs = utcMs + 7 * 60 * 60 * 1000;
            const d = new Date(thaiMs);
            const pad = (n) => String(n).padStart(2, '0');
            return `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())} ${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}:${pad(d.getUTCSeconds())}`;
        }

        document.querySelectorAll('.user-id-badge[data-utc]').forEach((el) => {
            el.textContent = toThaiTime(el.getAttribute('data-utc'));
        });

        window.addEventListener('load', () => {
            setTimeout(() => {
                const loader = document.getElementById('loader');
                loader.style.opacity = '0';
                loader.style.visibility = 'hidden';
            }, 450);

            document.querySelectorAll('.flap-row').forEach((row) => {
                const value = row.getAttribute('data-flap') || '0';
                const unit = row.getAttribute('data-unit');
                const chars = value.split('');

                chars.forEach((ch, i) => {
                    const span = document.createElement('span');
                    span.className = 'flap-char';
                    span.textContent = '0';
                    row.appendChild(span);

                    const delay = 550 + i * 110;
                    setTimeout(() => {
                        span.style.transition = 'transform 0.28s cubic-bezier(0.6,0,0.4,1), opacity 0.28s ease';
                        span.style.transform = 'rotateX(-90deg)';
                        span.style.opacity = '0.2';
                        setTimeout(() => {
                            span.textContent = ch;
                            span.style.transform = 'rotateX(0deg)';
                            span.style.opacity = '1';
                        }, 260);
                    }, delay);
                });

                if (unit) {
                    const u = document.createElement('span');
                    u.className = 'flap-char unit';
                    u.textContent = ' ' + unit;
                    row.appendChild(u);
                }
            });
        });

        const navHighlight = document.getElementById('nav-highlight');
        const navMenuEl = document.querySelector('.nav-menu');

        function moveNavHighlight(el, animate = true) {
            if (!el || !navHighlight || !navMenuEl) return;
            const menuRect = navMenuEl.getBoundingClientRect();
            const elRect = el.getBoundingClientRect();
            navHighlight.style.transition = animate
                ? 'transform 0.45s cubic-bezier(0.16,1,0.3,1), height 0.45s cubic-bezier(0.16,1,0.3,1), opacity 0.3s ease'
                : 'none';
            navHighlight.style.height = elRect.height + 'px';
            navHighlight.style.transform = `translateY(${elRect.top - menuRect.top}px)`;
            navHighlight.style.opacity = '1';
        }

        window.addEventListener('load', () => {
            const activeEl = document.querySelector('.nav-item.active');
            moveNavHighlight(activeEl, false);
        });
        window.addEventListener('resize', () => {
            const activeEl = document.querySelector('.nav-item.active');
            moveNavHighlight(activeEl, false);
        });

        document.querySelectorAll('.stat-card').forEach((card) => {
            const glow = card.querySelector('.glow-cursor');
            let ticking = false;
            let lastEvent = null;

            function applyTilt() {
                ticking = false;
                if (!lastEvent) return;
                const rect = card.getBoundingClientRect();
                const x = lastEvent.clientX - rect.left;
                const y = lastEvent.clientY - rect.top;
                const px = x / rect.width - 0.5;
                const py = y / rect.height - 0.5;
                const rotateX = (-py * 8).toFixed(2);
                const rotateY = (px * 10).toFixed(2);
                card.style.transform = `perspective(900px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) translateY(-6px) scale(1.015)`;
                if (glow) { glow.style.left = x + 'px'; glow.style.top = y + 'px'; }
            }

            card.addEventListener('mouseenter', () => {
                card.classList.add('tilting');
                card.style.transition = 'box-shadow 0.4s ease, border-color 0.4s ease';
            });
            card.addEventListener('mousemove', (e) => {
                lastEvent = e;
                if (!ticking) { ticking = true; requestAnimationFrame(applyTilt); }
            });
            card.addEventListener('mouseleave', () => {
                card.classList.remove('tilting');
                card.style.transition = 'transform 0.5s cubic-bezier(0.16,1,0.3,1), box-shadow 0.4s ease, border-color 0.4s ease';
                card.style.transform = 'translateY(0) scale(1)';
            });
        });

        document.querySelectorAll('.ripple-el').forEach((el) => {
            el.addEventListener('click', (e) => {
                const rect = el.getBoundingClientRect();
                const size = Math.max(rect.width, rect.height) * 1.6;
                const dot = document.createElement('span');
                dot.className = 'ripple-dot';
                dot.style.width = dot.style.height = size + 'px';
                dot.style.left = (e.clientX - rect.left - size / 2) + 'px';
                dot.style.top = (e.clientY - rect.top - size / 2) + 'px';
                el.appendChild(dot);
                setTimeout(() => dot.remove(), 620);
            });
        });

        const auroraSpans = document.querySelectorAll('.aurora span');
        let auroraTicking = false;
        document.addEventListener('mousemove', (e) => {
            if (auroraTicking) return;
            auroraTicking = true;
            requestAnimationFrame(() => {
                const px = (e.clientX / window.innerWidth - 0.5) * 2;
                const py = (e.clientY / window.innerHeight - 0.5) * 2;
                auroraSpans.forEach((span, i) => {
                    const strength = i === 0 ? 18 : -14;
                    span.style.marginLeft = (px * strength) + 'px';
                    span.style.marginTop = (py * strength) + 'px';
                });
                auroraTicking = false;
            });
        });

        const notifyIcons = {
            success: '<path d="M20 6 9 17l-5-5"/>',
            info: '<circle cx="12" cy="12" r="9"/><path d="M12 8h.01M11 12h1v5h1"/>',
            warning: '<path d="M12 9v4M12 17h.01"/><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z"/>',
            error: '<circle cx="12" cy="12" r="9"/><path d="m15 9-6 6M9 9l6 6"/>'
        };
        const notifyTheme = {
            success: { c: '#f2b705', soft: 'rgba(242,183,5,0.14)', border: 'rgba(242,183,5,0.38)' },
            info:    { c: '#2dd4bf', soft: 'rgba(45,212,191,0.14)', border: 'rgba(45,212,191,0.35)' },
            warning: { c: '#fbbf24', soft: 'rgba(251,191,36,0.14)', border: 'rgba(251,191,36,0.35)' },
            error:   { c: '#f87171', soft: 'rgba(248,113,113,0.14)', border: 'rgba(248,113,113,0.35)' }
        };

        function showNotification(title, message, type = 'success', duration = 4000) {
            const container = document.getElementById('notification-container');
            const theme = notifyTheme[type] || notifyTheme.success;

            const box = document.createElement('div');
            box.className = 'notify-box';
            box.style.setProperty('--nc', theme.c);
            box.style.setProperty('--nc-soft', theme.soft);
            box.style.setProperty('--nc-border', theme.border);
            box.style.setProperty('--dur', duration + 'ms');
            box.setAttribute('role', 'status');
            box.setAttribute('tabindex', '0');

            box.innerHTML = `
                <div class="notify-icon">
                    <svg viewBox="0 0 24 24" fill="none" stroke-linecap="round" stroke-linejoin="round">${notifyIcons[type] || notifyIcons.success}</svg>
                </div>
                <div class="notify-content">
                    <div class="notify-title">${title}</div>
                    <div class="notify-desc">${message}</div>
                </div>
                <div class="notify-close">✕</div>
                <div class="notify-progress"></div>
            `;

            function dismiss() {
                if (box.classList.contains('leaving')) return;
                box.classList.add('leaving');
                setTimeout(() => box.remove(), 400);
            }

            box.querySelector('.notify-close').addEventListener('click', (e) => { e.stopPropagation(); dismiss(); });
            box.addEventListener('click', dismiss);

            container.appendChild(box);
            const timer = setTimeout(dismiss, duration);
            box.addEventListener('mouseenter', () => {
                clearTimeout(timer);
                box.querySelector('.notify-progress').style.animationPlayState = 'paused';
            });
        }

        let demoNotifTitle = "ระบบสำเร็จ";
        let demoNotifMsg = "โหลดข้อมูล Dashboard เรียบร้อยแล้ว";

        setTimeout(() => {
            showNotification(demoNotifTitle, demoNotifMsg, "success");
        }, 1200);

        const navDashboard = document.getElementById('nav-dashboard');
        const navVerified = document.getElementById('nav-verified');
        const navLogs = document.getElementById('nav-logs');
        const navSettings = document.getElementById('nav-settings');
        const verifiedSection = document.getElementById('verified-section');
        const viewDashboard = document.getElementById('view-dashboard');
        const viewLogs = document.getElementById('view-logs');

        function setActiveNav(el) {
            [navDashboard, navVerified, navLogs].forEach(n => n.classList.remove('active'));
            el.classList.add('active');
            moveNavHighlight(el, true);
        }

        function showView(view) {
            [viewDashboard, viewLogs].forEach(v => v.classList.remove('active'));
            view.classList.add('active');
        }

        navDashboard.addEventListener('click', (e) => {
            e.preventDefault();
            setActiveNav(navDashboard);
            showView(viewDashboard);
            stopLogsPolling();
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });

        navVerified.addEventListener('click', (e) => {
            e.preventDefault();
            setActiveNav(navVerified);
            showView(viewDashboard);
            stopLogsPolling();
            verifiedSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
            verifiedSection.classList.remove('pulse-highlight');
            void verifiedSection.offsetWidth; // restart animation
            verifiedSection.classList.add('pulse-highlight');
        });

        // --- Nav: Logs -> terminal panel with live-polled error log ---
        const terminalBody = document.getElementById('terminal-body');
        const terminalCount = document.getElementById('terminal-count');
        const filterBtns = document.querySelectorAll('.term-filter-btn');
        let currentLogFilter = 'ALL';
        let logsPollTimer = null;

        function escapeHtml(str) {
            const div = document.createElement('div');
            div.textContent = str;
            return div.innerHTML;
        }

        function renderLogs(logs) {
            terminalCount.textContent = logs.length + ' entries';
            if (!logs.length) {
                terminalBody.innerHTML = '<div class="term-empty">// ยังไม่มี log รายการ ระบบทำงานปกติ</div>';
                return;
            }
            const filtered = currentLogFilter === 'ALL' ? logs : logs.filter(l => l.level === currentLogFilter);
            if (!filtered.length) {
                terminalBody.innerHTML = '<div class="term-empty">// ไม่มี log ประเภทนี้</div>';
                return;
            }
            const wasNearBottom = (terminalBody.scrollHeight - terminalBody.scrollTop - terminalBody.clientHeight) < 60;
            terminalBody.innerHTML = filtered.map((l, i) => `
                <div class="term-line" style="animation-delay:${Math.min(i, 20) * 0.02}s;">
                    <span class="term-time">${toThaiTime(l.time)}</span>
                    <span class="term-level ${l.level}">${l.level.padEnd(7, ' ')}</span>
                    <span class="term-msg">${escapeHtml(l.message)}</span>
                </div>
            `).join('') + '<span class="term-cursor"></span>';
            if (wasNearBottom) terminalBody.scrollTop = terminalBody.scrollHeight;
        }

        async function fetchLogs() {
            try {
                const res = await fetch('/admin/logs');
                if (!res.ok) return;
                const data = await res.json();
                renderLogs(data.logs || []);
            } catch (e) { /* เงียบไว้ ไม่รบกวนผู้ใช้ */ }
        }

        function startLogsPolling() {
            fetchLogs();
            if (!logsPollTimer) logsPollTimer = setInterval(fetchLogs, 4000);
        }
        function stopLogsPolling() {
            if (logsPollTimer) { clearInterval(logsPollTimer); logsPollTimer = null; }
        }

        filterBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                filterBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                currentLogFilter = btn.getAttribute('data-filter');
                fetchLogs();
            });
        });

        navLogs.addEventListener('click', (e) => {
            e.preventDefault();
            setActiveNav(navLogs);
            showView(viewLogs);
            startLogsPolling();
        });

        const overlay = document.getElementById('settings-overlay');
        const titleInput = document.getElementById('setting-notif-title');
        const msgInput = document.getElementById('setting-notif-msg');
        const scanlineToggle = document.getElementById('setting-scanline');
        const auroraToggle = document.getElementById('setting-aurora');
        const scanlineEl = document.querySelector('.scanline');
        const auroraEl = document.querySelector('.aurora');

        function openSettings() {
            titleInput.value = demoNotifTitle;
            msgInput.value = demoNotifMsg;
            overlay.classList.add('open');
        }
        function closeSettings() { overlay.classList.remove('open'); }

        navSettings.addEventListener('click', (e) => { e.preventDefault(); openSettings(); });
        document.getElementById('settings-close').addEventListener('click', closeSettings);
        document.getElementById('settings-cancel').addEventListener('click', closeSettings);
        overlay.addEventListener('click', (e) => { if (e.target === overlay) closeSettings(); });
        document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && overlay.classList.contains('open')) closeSettings(); });

        scanlineToggle.addEventListener('change', () => {
            scanlineEl.style.display = scanlineToggle.checked ? '' : 'none';
        });
        auroraToggle.addEventListener('change', () => {
            auroraEl.style.display = auroraToggle.checked ? '' : 'none';
        });

        document.getElementById('settings-save').addEventListener('click', () => {
            demoNotifTitle = titleInput.value.trim() || demoNotifTitle;
            demoNotifMsg = msgInput.value.trim() || demoNotifMsg;
            closeSettings();
            showNotification(demoNotifTitle, demoNotifMsg, "success");
        });

        const scrollTopBtn = document.getElementById('scroll-top-btn');
        window.addEventListener('scroll', () => {
            scrollTopBtn.classList.toggle('show', window.scrollY > 400);
        });
        scrollTopBtn.addEventListener('click', () => {
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });
    </script>
</body>
</html>
"""

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "stifshop_secret_key_change_me")

@app.route('/favicon.ico')
def favicon():
    return '', 204

def _role_color_hex(color_int):
    if not color_int:
        return "#23a559"
    return f"#{color_int:06x}"

def get_role_info(guild_id, role_id):
    try:
        resp = requests.get(
            f"https://discord.com/api/v10/guilds/{guild_id}/roles",
            headers={"Authorization": f"Bot {BOT_TOKEN}"},
        )
        resp.raise_for_status()
        for role in resp.json():
            if str(role.get("id")) == str(role_id):
                return {
                    "name": role.get("name"),
                    "color": _role_color_hex(role.get("color")),
                }
    except Exception as e:
        logger.error(f"ดึงข้อมูลยศไม่สำเร็จ: {e}")
    return {"name": "Verified", "color": "#23a559"}

def send_webhook_log(webhook_url, title, description, color, avatar_url=None,
                     author_name=None, fields=None, footer_text="STIF SHOP • ระบบยืนยันตัวตน"):
    if not webhook_url or webhook_url.startswith("ใส่_"):
        logger.warning("[webhook] skipped: no url configured")
        return
    try:
        embed = {
            "title": title,
            "description": description,
            "color": color,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        if author_name:
            embed["author"] = {"name": author_name}
            if avatar_url:
                embed["author"]["icon_url"] = avatar_url
 
        if avatar_url:
            embed["thumbnail"] = {"url": avatar_url}
 
        if fields:
            embed["fields"] = fields
 
        if footer_text:
            embed["footer"] = {"text": footer_text}
 
        payload = {"embeds": [embed]}
        resp = requests.post(webhook_url, json=payload, timeout=10)

        if resp.status_code != 204:
            logger.error(f"[webhook] FAILED status={resp.status_code} body={resp.text[:300]}")
        else:
            logger.info(f"[webhook] sent ok -> {title}")
 
    except Exception as e:
        logger.error(f"[webhook] exception: {e}")

@app.route("/")
def home():
    discord_login_url = (
        f"https://discord.com/api/oauth2/authorize?client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}&response_type=code&scope=identify%20guilds.join"
    )
    return render_template_string(
        HTML_TEMPLATE,
        title="ยืนยันตัวตน",
        button_url=discord_login_url,
        user=None,
    )

@app.route("/callback", strict_slashes=False)
def callback():
    code = request.args.get("code")
    if not code:
        return render_template_string(ERROR_TEMPLATE, error_message="ไม่พบรหัสยืนยันตัวตนจาก Discord กรุณาลองใหม่อีกครั้ง")

    try:
        data = {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        token_resp = requests.post("https://discord.com/api/oauth2/token", data=data, headers=headers)
        token_json = token_resp.json()
        access_token = token_json.get("access_token")

        if not access_token:
            logger.error("❌ ไม่สามารถขอ Access Token จาก Discord ได้ (OAuth token exchange failed)")
            send_webhook_log(WEBHOOK_ERROR, "❌ ยืนยันตัวตนล้มเหลว", "ไม่สามารถขอ Access Token จาก Discord ได้", 16711680)
            return render_template_string(ERROR_TEMPLATE, error_message="เกิดข้อผิดพลาดในการขอ Token จากระบบ Discord")

        user_data = requests.get("https://discord.com/api/users/@me", headers={"Authorization": f"Bearer {access_token}"}).json()
        user_id = user_data.get("id")
        username = user_data.get("username")
        global_name = user_data.get("global_name")
        avatar_id = user_data.get("avatar")
        avatar_url = f"https://cdn.discordapp.com/avatars/{user_id}/{avatar_id}.png" if avatar_id else "https://cdn.discordapp.com/embed/avatars/0.png"

        conn = sqlite3.connect("verifications.db")
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM verified_users WHERE user_id = ?", (user_id,))
        already_verified = cursor.fetchone()
        conn.close()

        timestamp = ((int(user_id) >> 22) + 1420070400000) / 1000
        joined_dt = datetime.datetime.utcfromtimestamp(timestamp)
        joined_date_thai = thai_date(joined_dt)

        user_info = {
            "id": user_id, 
            "username": username,
            "global_name": global_name,
            "avatar_url": avatar_url,
            "joined_at": joined_date_thai
        }

        role_info = get_role_info(GUILD_ID, ROLE_ID)

        bot_headers = {"Authorization": f"Bot {BOT_TOKEN}"}
        add_role_url = f"https://discord.com/api/v10/guilds/{GUILD_ID}/members/{user_id}/roles/{ROLE_ID}"
        r = requests.put(add_role_url, headers=bot_headers)

        if r.status_code not in [200, 204]:
            logger.error(f"❌ เพิ่มยศไม่สำเร็จ สำหรับ {username} ({user_id}) — API status {r.status_code}")
            send_webhook_log(WEBHOOK_ERROR, "❌ เพิ่มยศไม่สำเร็จ", f"ผู้ใช้: {username} (`{user_id}`)\nAPI Error Code: {r.status_code}", 16711680)
        else:
            logger.info(f"✅ {username} ({user_id}) ยืนยันตัวตนสำเร็จ — ได้รับยศ {role_info['name']}")

            if not already_verified:
                conn = sqlite3.connect("verifications.db")
                cursor = conn.cursor()
                cursor.execute(
                    """INSERT OR REPLACE INTO verified_users
                       (user_id, username, global_name, avatar_url, verified_at, role_name, role_color)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        user_id,
                        username,
                        global_name,
                        avatar_url,
                        str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                        role_info["name"],
                        role_info["color"],
                    )
                )
                conn.commit()
                conn.close()

                send_webhook_log(
                    WEBHOOK_SUCCESS,
                    "`✅` **มีผู้ยืนยันตัวตนสำเร็จ**",
                    f"- **ผู้ใช้งาน:** **{global_name or username}** (`@{username}`)\n- **ID:** **{user_id}**\n- **ยศที่ได้รับ:** **{role_info['name']}**",
                    2318169,
                    avatar_url=avatar_url,
                )
            else:
                logger.info(f"ℹ️ {username} ({user_id}) ยืนยันตัวตนซ้ำ (มีอยู่ในระบบแล้ว)")
                send_webhook_log(
                    WEBHOOK_SUCCESS,
                    "`🔁` **มีผู้ยืนยันตัวตนซ้ำ**",
                    f"- **ผู้ใช้งาน:** **{global_name or username}** (`@{username}`)\n- **ID:** **{user_id}**\n- **ยศที่ได้รับ:** **{role_info['name']}**\n- หมายเหตุ: ผู้ใช้นี้เคยยืนยันตัวตนไปแล้วก่อนหน้านี้",
                    3447003,
                    avatar_url=avatar_url,
                )

        return render_template_string(
            HTML_TEMPLATE,
            title="ยืนยันตัวตนสำเร็จ",
            user=user_info,
            role_name=role_info["name"],
            role_color=role_info["color"],
        )

    except Exception as e:
        logger.error(f"💥 Exception ในหน้า /callback: {e}")
        send_webhook_log(WEBHOOK_ERROR, "💥 ระบบเกิดข้อผิดพลาดรุนแรง (Exception)", f"Error details: `{str(e)}`", 16711680)
        return render_template_string(ERROR_TEMPLATE, error_message="เกิดข้อผิดพลาดบางประการจากระบบเซิร์ฟเวอร์ กรุณาลองใหม่อีกครั้งในภายหลัง")

@app.route("/admin/stats")
def admin_stats():
    admin_auth_url = (
        f"https://discord.com/api/oauth2/authorize?client_id={CLIENT_ID}"
        f"&redirect_uri=https%3A%2F%2Fstifshop.up.railway.app%2Fadmin/login&response_type=code&scope=identify%20guilds"
    )
    
    if not session.get("is_admin"):
        return redirect(admin_auth_url)

    conn = sqlite3.connect("verifications.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM verified_users")
    total_count = cursor.fetchone()[0]

    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    cursor.execute("SELECT COUNT(*) FROM verified_users WHERE verified_at LIKE ?", (f"{today_str}%",))
    today_count = cursor.fetchone()[0]

    cursor.execute(
        """SELECT user_id, username, global_name, avatar_url, verified_at, role_name, role_color
           FROM verified_users ORDER BY verified_at DESC LIMIT 50"""
    )
    users = cursor.fetchall()
    conn.close()

    return render_template_string(
        ADMIN_STATS_TEMPLATE,
        total_count=total_count,
        today_count=today_count,
        users=users,
        logo_url=BRAND_LOGO_URL,
    )

@app.route("/admin/logs")
def admin_logs():
    if not session.get("is_admin"):
        return jsonify({"error": "unauthorized"}), 403
    return jsonify({"logs": list(log_buffer)})

@app.route("/admin/login", strict_slashes=False)
def admin_login():
    code = request.args.get("code")
    if not code:
        return redirect("/admin/stats")

    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": "https://stifshop.up.railway.app/admin/login",
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    token_resp = requests.post("https://discord.com/api/oauth2/token", data=data, headers=headers)
    access_token = token_resp.json().get("access_token")

    if access_token:
        guilds_resp = requests.get("https://discord.com/api/users/@me/guilds", headers={"Authorization": f"Bearer {access_token}"})
        if guilds_resp.status_code == 200:
            for g in guilds_resp.json():
                if str(g.get("id")) == str(GUILD_ID):
                    permissions = int(g.get("permissions", 0))
                    if (permissions & 0x8) == 0x8 or g.get("owner"):
                        session["is_admin"] = True
                        return redirect("/admin/stats")

    logger.warning("⚠️ มีความพยายามเข้าหน้า admin โดยไม่มีสิทธิ์ (ไม่ใช่ผู้ดูแลเซิร์ฟเวอร์)")
    return render_template_string(ERROR_TEMPLATE, error_message="คุณไม่มีสิทธิ์เข้าถึงหน้าแดชบอร์ดแอดมิน (ต้องเป็นผู้ดูแลเซิร์ฟเวอร์เท่านั้น)")

class VerifyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(
            discord.ui.Button(
                label="ยืนยันตัวตนเข้าดิส",
                url=f"https://discord.com/oauth2/authorize?client_id={CLIENT_ID}&response_type=code&redirect_uri=https%3A%2F%2Fstifshop.up.railway.app%2Fcallback&scope=identify",
                style=discord.ButtonStyle.link,
                emoji="<a:emoji_125:1283873278129213471>",
            )
        )

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    activity = discord.Streaming(name="STIF SHOP รับยศออโต้", url="https://www.twitch.tv/Jxycop_x")
    await bot.change_presence(status=discord.Status.idle, activity=activity)

    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s).")
    except Exception as e:
        print(e)

@bot.tree.command(name="setup", description="ส่งหน้าต่างยืนยันตัวตนสำหรับสมาชิก")
@app_commands.checks.has_permissions(administrator=True)
async def setup(interaction: discord.Interaction):
    embed = discord.Embed(
        title="⚙️ STIF SHOP",
        description=f"🛒    บอทรับยศ 24 ชั่วโมง\n\n"
                    f"📥 กดปุ่มข้างล่างเพื่อรับยศ <@&{ROLE_ID}>",
        color=discord.Color(0x000000)
    )
    embed.set_footer(
        text="🟢• STIF SHOP • ระบบรับยศ",
        icon_url='https://media.tenor.com/bhC8X-tsTK4AAAAi/tspchan1-lick.gif'
    )
    embed.set_image(url="https://images-ext-1.discordapp.net/external/UZlJhcpilRkbJAUtbbLfM3I8NByAJj3W2YYl-lZdCMs/https/i.postimg.cc/8PFsC2cg/im-age.png?format=webp&quality=lossless")
    embed.set_thumbnail(url='https://media.tenor.com/bhC8X-tsTK4AAAAi/tspchan1-lick.gif')
    await interaction.response.send_message("✅ สร้างปุ่มยืนยันตัวตนสำเร็จ!", ephemeral=True)
    await interaction.channel.send(embed=embed, view=VerifyView())

def run_web():
    app.run(host="0.0.0.0", port=5000)

if __name__ == "__main__":
    t = threading.Thread(target=run_web)
    t.daemon = True
    t.start()
    
    bot.run(BOT_TOKEN)
