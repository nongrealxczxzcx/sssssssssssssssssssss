import os
import threading
import datetime
import sqlite3
import discord
from discord import app_commands
from discord.ext import commands
from flask import Flask, redirect, request, render_template_string, session
import requests

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
WEBHOOK_ERROR = "https://discord.com/api/webhooks/1540031111223189701/KhD_TF8YMxmRih4KQCH-MtBnTy74Qcodk7trYCqjy7_z6-6zQ8frXd8dJX-FOaZ1MO7X"

if not BOT_TOKEN or not CLIENT_SECRET:
    raise RuntimeError(
        "กรุณาตั้งค่า BOT_TOKEN และ CLIENT_SECRET เป็น environment variable ก่อนรัน"
    )

def init_db():
    conn = sqlite3.connect("verifications.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS verified_users (
            user_id TEXT PRIMARY KEY,
            username TEXT,
            global_name TEXT,
            avatar_url TEXT,
            verified_at TEXT
        )
    """)
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
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>Admin Dashboard - STIF SHOP</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
  :root {
    --bg-base: #050508;
    --card-bg: rgba(13, 15, 22, 0.75);
    --accent: #23a559;
    --accent-glow: rgba(35, 165, 89, 0.25);
    --text-main: #ffffff;
    --text-muted: #9ba1a6;
    --border-color: rgba(255, 255, 255, 0.08);
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background-color: var(--bg-base);
    color: var(--text-main);
    font-family: 'Plus Jakarta Sans', sans-serif;
    min-height: 100vh;
    padding: 24px 16px;
    position: relative;
    overflow-x: hidden;
  }
  .bg-mesh {
    position: fixed;
    inset: 0;
    z-index: 1;
    pointer-events: none;
    background: 
      radial-gradient(circle at 20% 15%, rgba(35, 165, 89, 0.12), transparent 45%),
      radial-gradient(circle at 80% 85%, rgba(88, 101, 242, 0.1), transparent 45%),
      radial-gradient(circle at 50% 50%, rgba(10, 12, 18, 0.9), transparent 80%);
  }
  .container {
    position: relative;
    z-index: 10;
    max-width: 900px;
    margin: 0 auto;
  }
  .navbar {
    background: var(--card-bg);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid var(--border-color);
    border-radius: 20px;
    padding: 16px 24px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;
    box-shadow: 0 15px 35px rgba(0, 0, 0, 0.5);
  }
  .nav-brand {
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .nav-logo {
    width: 38px;
    height: 38px;
    background: linear-gradient(135deg, #2ecc71, var(--accent));
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 800;
    font-size: 1.1rem;
    box-shadow: 0 0 15px var(--accent-glow);
  }
  .nav-title h1 {
    font-size: 1.05rem;
    font-weight: 700;
    letter-spacing: 0.5px;
  }
  .nav-title p {
    font-size: 0.72rem;
    color: var(--text-muted);
  }
  .btn-back {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 8px 16px;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid var(--border-color);
    color: #fff;
    text-decoration: none;
    border-radius: 10px;
    font-size: 0.8rem;
    font-weight: 600;
    transition: all 0.2s ease;
  }
  .btn-back:hover {
    background: rgba(255, 255, 255, 0.1);
    border-color: rgba(255, 255, 255, 0.2);
  }
  .stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    gap: 16px;
    margin-bottom: 24px;
  }
  .stat-card {
    background: var(--card-bg);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid var(--border-color);
    border-radius: 20px;
    padding: 24px;
    position: relative;
    overflow: hidden;
    box-shadow: 0 15px 35px rgba(0, 0, 0, 0.5);
    transition: transform 0.2s ease;
  }
  .stat-card:hover {
    transform: translateY(-2px);
    border-color: rgba(35, 165, 89, 0.3);
  }
  .stat-card::after {
    content: '';
    position: absolute;
    top: 0; right: 0;
    width: 100px; height: 100px;
    background: radial-gradient(circle, var(--accent-glow) 0%, transparent 70%);
    pointer-events: none;
  }
  .stat-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 14px;
  }
  .stat-card h3 {
    font-size: 0.78rem;
    color: var(--text-muted);
    font-weight: 600;
    letter-spacing: 1px;
    text-transform: uppercase;
  }
  .stat-icon {
    width: 32px; height: 32px;
    border-radius: 8px;
    background: rgba(35, 165, 89, 0.12);
    display: flex; align-items: center; justify-content: center;
    color: var(--accent);
  }
  .stat-card .number {
    font-size: 2.2rem;
    font-weight: 800;
    color: #fff;
    letter-spacing: -0.5px;
  }
  .table-box {
    background: var(--card-bg);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid var(--border-color);
    border-radius: 20px;
    overflow: hidden;
    box-shadow: 0 15px 35px rgba(0, 0, 0, 0.5);
  }
  .table-header {
    padding: 20px 24px;
    font-weight: 700;
    border-bottom: 1px solid var(--border-color);
    font-size: 0.95rem;
    display: flex;
    align-items: center;
    gap: 8px;
    color: #fff;
  }
  .table-responsive {
    width: 100%;
    overflow-x: auto;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    text-align: left;
    font-size: 0.85rem;
    white-space: nowrap;
  }
  th, td {
    padding: 14px 24px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.04);
  }
  th {
    color: var(--text-muted);
    font-weight: 600;
    background: rgba(255, 255, 255, 0.01);
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }
  tr:hover td {
    background: rgba(255, 255, 255, 0.015);
  }
  .user-cell {
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .user-avatar-wrap {
    position: relative;
  }
  .user-avatar {
    width: 38px;
    height: 38px;
    border-radius: 50%;
    object-fit: cover;
    border: 2px solid rgba(255, 255, 255, 0.1);
  }
  .online-indicator {
    position: absolute;
    bottom: 0; right: 0;
    width: 10px; height: 10px;
    background: #23a559;
    border: 2px solid #0d0f14;
    border-radius: 50%;
  }
  .user-info .display-name {
    font-weight: 600;
    color: #fff;
  }
  .user-info .username {
    font-size: 0.75rem;
    color: var(--text-muted);
  }
  .discord-id {
    font-family: monospace;
    color: var(--text-muted);
    background: rgba(255, 255, 255, 0.03);
    padding: 3px 8px;
    border-radius: 6px;
    border: 1px solid rgba(255, 255, 255, 0.04);
  }
  @media (max-width: 640px) {
    body { padding: 12px 8px; }
    .navbar { padding: 12px 16px; }
    th, td { padding: 12px 16px; }
  }
</style>
</head>
<body>
  <div class="bg-mesh"></div>
  <div class="container">
    <div class="navbar">
      <div class="nav-brand">
        <div class="nav-logo">⚡</div>
        <div class="nav-title">
          <h1>STIF SHOP</h1>
          <p>Admin Control Center</p>
        </div>
      </div>
      <a href="/" class="btn-back">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>
        <span>หน้าแรกเว็บไซต์</span>
      </a>
    </div>

    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-header">
          <h3>ยอดรับยศทั้งหมด</h3>
          <div class="stat-icon">👥</div>
        </div>
        <div class="number">{{ total_count }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-header">
          <h3>รับยศวันนี้</h3>
          <div class="stat-icon">✨</div>
        </div>
        <div class="number">{{ today_count }}</div>
      </div>
    </div>

    <div class="table-box">
      <div class="table-header">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color: var(--accent);"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"></path><rect x="8" y="2" width="8" height="4" rx="1" ry="1"></rect></svg>
        <span>ประวัติการยืนยันตัวตนล่าสุด</span>
      </div>
      <div class="table-responsive">
        <table>
          <thead>
            <tr>
              <th>ผู้ใช้งาน</th>
              <th>Discord ID</th>
              <th>เวลาที่ยืนยัน</th>
            </tr>
          </thead>
          <tbody>
            {% if users %}
              {% for u in users %}
              <tr>
                <td>
                  <div class="user-cell">
                    <div class="user-avatar-wrap">
                      <img src="{{ u[3] if u[3] else 'https://cdn.discordapp.com/embed/avatars/0.png' }}" class="user-avatar" alt="Avatar">
                      <div class="online-indicator"></div>
                    </div>
                    <div class="user-info">
                      <div class="display-name">{{ u[2] or u[1] }}</div>
                      <div class="username">@{{ u[1] }}</div>
                    </div>
                  </div>
                </td>
                <td><span class="discord-id">{{ u[0] }}</span></td>
                <td style="color: var(--text-muted);">{{ u[4] }}</td>
              </tr>
              {% endfor %}
            {% else %}
              <tr>
                <td colspan="3" style="text-align: center; color: var(--text-muted); padding: 40px;">ยังไม่มีข้อมูลการยืนยันตัวตนในระบบ</td>
              </tr>
            {% endif %}
          </tbody>
        </table>
      </div>
    </div>
  </div>
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
        print("ดึงข้อมูลยศไม่สำเร็จ:", e)
    return {"name": "Verified", "color": "#23a559"}

def send_webhook_log(webhook_url, title, description, color):
    if not webhook_url or webhook_url.startswith("ใส่_"):
        return
    try:
        payload = {
            "embeds": [{
                "title": title,
                "description": description,
                "color": color,
                "timestamp": datetime.datetime.utcnow().isoformat()
            }]
        }
        requests.post(webhook_url, json=payload)
    except Exception as e:
        print("ส่ง Webhook Log ไม่สำเร็จ:", e)

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
            send_webhook_log(WEBHOOK_ERROR, "❌ เพิ่มยศไม่สำเร็จ", f"ผู้ใช้: {username} (`{user_id}`)\nAPI Error Code: {r.status_code}", 16711680)
        else:
            if not already_verified:
                conn = sqlite3.connect("verifications.db")
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT OR REPLACE INTO verified_users (user_id, username, global_name, avatar_url, verified_at) VALUES (?, ?, ?, ?, ?)",
                    (user_id, username, global_name, avatar_url, str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                )
                conn.commit()
                conn.close()
                
                send_webhook_log(
                    WEBHOOK_SUCCESS, 
                    "✅ มีผู้ยืนยันตัวตนสำเร็จ", 
                    f"**ผู้ใช้งาน:** {global_name or username} (`@{username}`)\n**ID:** {user_id}\n**ยศที่ได้รับ:** {role_info['name']}", 
                    2318169
                )

        return render_template_string(
            HTML_TEMPLATE,
            title="ยืนยันตัวตนสำเร็จ",
            user=user_info,
            role_name=role_info["name"],
            role_color=role_info["color"],
        )

    except Exception as e:
        print("Error ในหน้า callback:", e)
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

    cursor.execute("SELECT user_id, username, global_name, avatar_url, verified_at FROM verified_users ORDER BY verified_at DESC LIMIT 50")
    users = cursor.fetchall()
    conn.close()

    return render_template_string(ADMIN_STATS_TEMPLATE, total_count=total_count, today_count=today_count, users=users)

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
