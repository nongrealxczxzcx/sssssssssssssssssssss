import os
import threading
import datetime
import discord
from discord import app_commands
from discord.ext import commands
from flask import Flask, redirect, request, render_template_string
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

if not BOT_TOKEN or not CLIENT_SECRET:
    raise RuntimeError(
        "กรุณาตั้งค่า BOT_TOKEN และ CLIENT_SECRET เป็น environment variable ก่อนรัน"
    )

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
<title>{{ title | default('กำลังตรวจสอบและรับยศ') }}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Kanit:wght@300;400;500;600;700&family=Sarabun:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
  :root{
    --bg-0:#000000;
    --card-bg:#111214;
    --border-color:rgba(255, 255, 255, 0.08);
    --text-hi:#ffffff;
    --text-lo:#949ba4;
  }
  *{box-sizing:border-box;margin:0;padding:0;-webkit-tap-highlight-color:transparent;}
  html,body{
    height:100%;
    min-height:100dvh;
    background:var(--bg-0);
    overflow-x:hidden;
    overflow-y:auto;
  }
  body{
    font-family:'Sarabun','Kanit',sans-serif;
    display:flex;
    align-items:center;
    justify-content:center;
    position:relative;
    isolation:isolate;
    min-height:100dvh;
    padding:24px 16px;
  }
 
  .ambient-bg{
    position:fixed;inset:0;pointer-events:none;z-index:1;
    background:
      radial-gradient(circle at 50% 0%, rgba(30, 30, 35, 0.25), transparent 60%),
      radial-gradient(circle at 50% 100%, rgba(10, 10, 15, 0.4), transparent 60%);
    transition:background 0.8s ease;
  }
  body.phase-success .ambient-bg{
    background:
      radial-gradient(circle at 50% 0%, rgba(16, 185, 129, 0.12), transparent 60%),
      radial-gradient(circle at 50% 100%, rgba(10, 10, 15, 0.4), transparent 60%);
  }
 
  .noise{
    position:fixed;inset:0;
    background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='120' height='120'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='2' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.03'/%3E%3C/svg%3E");
    mix-blend-mode:overlay;pointer-events:none;z-index:2;
  }
 
  .card-wrap{ position:relative; z-index:10; width:100%; max-width:400px; margin:auto; }
  .card-glow{
    position:absolute; inset:-2px; border-radius:26px;
    background:linear-gradient(135deg, rgba(255,255,255,0.1), rgba(50,50,60,0.05));
    filter:blur(24px);
    opacity:0.5;
    z-index:-1;
    animation:glowPulse 6s ease-in-out infinite;
    transition:background 0.8s ease;
  }
  @keyframes glowPulse{
    0%,100%{ opacity:0.3; transform:scale(1); }
    50%{ opacity:0.6; transform:scale(1.02); }
  }
  body.phase-success .card-glow{
    background:linear-gradient(135deg, rgba(16,185,129,0.3), rgba(255,255,255,0.05));
  }
 
  .card{
    position:relative;
    width:100%;
    padding:24px 20px;
    background:var(--card-bg);
    border:1px solid var(--border-color);
    border-radius:20px;
    box-shadow: 0 30px 70px -15px rgba(0,0,0,0.95);
    text-align:center;
    animation:cardIn 0.7s cubic-bezier(0.16, 1, 0.3, 1) both;
    overflow: hidden;
  }
  @keyframes cardIn{ from{opacity:0; transform:translateY(20px) scale(0.95);} to{opacity:1; transform:translateY(0) scale(1);} }
 
  .phase{ display:none; position:relative; z-index:3; }
  .phase.active{ display:block; animation:phaseIn 0.6s cubic-bezier(0.16, 1, 0.3, 1) both; }
  @keyframes phaseIn{ from{opacity:0; transform:translateY(10px);} to{opacity:1; transform:translateY(0);} }
 
  .loader{
    position:relative; width:88px; height:88px; margin:0 auto 22px;
    display:flex; align-items:center; justify-content:center;
  }
  .loader-ring-outer {
    position: absolute; inset: 0; border-radius: 50%;
    border: 2px solid transparent;
    border-top-color: #ffffff;
    border-right-color: rgba(255, 255, 255, 0.2);
    animation: spinClockwise 1.2s cubic-bezier(0.68, -0.55, 0.265, 1.55) infinite;
  }
  .loader-ring-inner {
    position: absolute; inset: 12px; border-radius: 50%;
    border: 2px solid transparent;
    border-bottom-color: #a1a1aa;
    border-left-color: rgba(161, 161, 170, 0.2);
    animation: spinCounter 0.9s linear infinite;
  }
  @keyframes spinClockwise { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
  @keyframes spinCounter { 0% { transform: rotate(360deg); } 100% { transform: rotate(0deg); } }
  .loader-core {
    width: 12px; height: 12px; border-radius: 50%;
    background: #ffffff;
    box-shadow: 0 0 15px rgba(255, 255, 255, 0.8);
    animation: pulseCore 1.5s ease-in-out infinite alternate;
  }
  @keyframes pulseCore { 0% { transform: scale(0.7); opacity: 0.5; } 100% { transform: scale(1.25); opacity: 1; } }
 
  .eyebrow{ font-size: 0.72rem; font-weight: 600; text-transform: uppercase; letter-spacing: 2px; color: var(--text-lo); margin-bottom: 6px; }
  .title{ font-family:'Kanit',sans-serif; font-weight:600; font-size:1.2rem; color: #ffffff; margin-bottom:6px; }
  .subtitle{ font-size:0.82rem; line-height:1.6; color:var(--text-lo); font-weight:300; margin-bottom:18px; }
  
  .status-line{
    display:flex; align-items:center; justify-content:center; gap:8px;
    width:100%; padding:11px 16px; border-radius:14px;
    border:1px solid rgba(255,255,255,0.05);
    background: rgba(255, 255, 255, 0.02);
    color:var(--text-hi); font-size:0.8rem; font-weight:400;
  }
  .status-line .dots span{
    display:inline-block; width:4px; height:4px; margin-left:2px; border-radius:50%; background:#ffffff;
    animation:bounce 1.2s ease-in-out infinite;
  }
  .status-line .dots span:nth-child(2){animation-delay:0.15s;}
  .status-line .dots span:nth-child(3){animation-delay:0.3s;}
  @keyframes bounce{ 0%,80%,100%{transform:translateY(0); opacity:0.3;} 40%{transform:translateY(-4px); opacity:1;} }
 
  .discord-profile-modal {
    background: #18191c;
    border-radius: 12px;
    overflow: hidden;
    text-align: left;
    margin-bottom: 16px;
    box-shadow: 0 16px 40px rgba(0, 0, 0, 0.7);
    border: 1px solid rgba(255,255,255,0.04);
  }
 
  .discord-banner {
    width: 100%;
    height: 100px;
    background: #111214;
    position: relative;
    display: flex;
    justify-content: flex-end;
    align-items: flex-start;
    padding: 10px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.04);
  }
 
  .banner-status-badge {
    background: rgba(0, 0, 0, 0.55);
    backdrop-filter: blur(8px);
    padding: 4px 10px;
    border-radius: 20px;
    display: flex;
    align-items: center;
    gap: 5px;
    font-size: 0.7rem;
    color: #dbdee1;
    font-weight: 500;
    border: 1px solid rgba(255,255,255,0.06);
  }
  .banner-status-badge svg { width: 10px; height: 10px; fill: #ffffff; }

  .discord-body {
    padding: 0 16px 16px 16px;
    background: #111214;
    position: relative;
  }

  .profile-avatar-row {
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    margin-top: -38px;
    margin-bottom: 10px;
  }

  .avatar-container {
    position: relative;
    width: 80px;
    height: 80px;
  }

  .avatar-img {
    width: 80px;
    height: 80px;
    border-radius: 50%;
    object-fit: cover;
    border: 6px solid #111214;
  }

  .profile-actions {
    display: flex;
    gap: 8px;
    margin-bottom: 8px;
  }
  .action-icon-btn {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    background: #2b2d31;
    border: none;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #dbdee1;
    cursor: pointer;
    transition: background 0.2s;
  }
  .action-icon-btn:hover { background: #35373c; }
  .action-icon-btn svg { width: 18px; height: 18px; fill: currentColor; }

  .profile-name {
    font-family: 'Kanit', sans-serif;
    font-size: 1.15rem;
    font-weight: 700;
    color: #f2f3f5;
    line-height: 1.2;
    margin-bottom: 4px;
  }

  .profile-handle-row {
    font-size: 0.78rem;
    color: #b5bac1;
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 4px;
  }

  .badge-row {
    display: flex;
    gap: 6px;
    margin-bottom: 10px;
  }
  .discord-badge {
    width: 18px;
    height: 18px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
  }

  .roles-section {
    margin-bottom: 12px;
  }
  .roles-title {
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    color: #949ba4;
    margin-bottom: 6px;
    letter-spacing: 0.5px;
    text-align: left;
  }
  .roles-container {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }
  .role-tag {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: #2b2d31;
    padding: 3px 8px;
    border-radius: 6px;
    font-size: 0.75rem;
    font-weight: 500;
    color: #dbdee1;
  }
  .role-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #5865f2;
  }

  .main-chat-btn {
    width: 100%;
    background: #5865f2;
    color: #ffffff;
    border: none;
    border-radius: 4px;
    padding: 8px;
    font-weight: 600;
    font-size: 0.85rem;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    cursor: pointer;
    margin-bottom: 16px;
    font-family: 'Sarabun', sans-serif;
  }
  .main-chat-btn svg { width: 16px; height: 16px; fill: currentColor; }

  .divider {
    height: 1px;
    background: #232428;
    margin: 12px 0;
  }

  .info-section-title {
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    color: #949ba4;
    margin-bottom: 4px;
    letter-spacing: 0.5px;
    text-align: left;
  }

  .info-section-value {
    font-size: 0.82rem;
    color: #dbdee1;
    text-align: left;
    margin-bottom: 12px;
  }

  .connections-placeholder {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 0.82rem;
    color: #b5bac1;
    text-align: left;
    margin-bottom: 12px;
  }
  .connections-placeholder svg { width: 14px; height: 14px; fill: #b5bac1; }

  .note-box {
    background: #111214;
    border-radius: 4px;
    padding: 6px 8px;
    font-size: 0.78rem;
    color: #949ba4;
    text-align: left;
    border: 1px dashed transparent;
  }

  .result-btn {
    display: flex; align-items: center; justify-content: center; gap: 8px;
    width: 100%; color: #000000; font-weight: 600; font-size: 0.95rem; padding: 12px;
    border-radius: 10px; text-decoration: none; border: none; cursor: pointer;
    transition: all 0.25s ease;
    font-family: 'Sarabun', 'Kanit', sans-serif;
  }
  .btn-success { background: #ffffff; box-shadow: 0 4px 20px rgba(255,255,255,0.2); }
  .btn-success:hover { background: #e2e2e2; transform: translateY(-1px); }

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
 
      <!-- PHASE 1: LOADING -->
      <div class="phase active" id="phase-checking">
        <div class="eyebrow">ระบบยืนยันตัวตน</div>
        <div class="loader">
          <div class="loader-ring-outer"></div>
          <div class="loader-ring-inner"></div>
          <div class="loader-core"></div>
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
 
      <!-- PHASE 2: RESULT -->
      <div class="phase" id="phase-result">
        <div class="confetti" id="confetti"></div>
 
        <div class="discord-profile-modal">
          <div class="discord-banner">
            <div class="banner-status-badge">
              <svg viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/></svg>
              <span>ยืนยันตัวตนแล้ว</span>
            </div>
          </div>
 
          <div class="discord-body">
            <div class="profile-avatar-row">
              <div class="avatar-container">
                <img src="{{ user.avatar_url if user and user.avatar_url else 'https://cdn.discordapp.com/embed/avatars/0.png' }}" alt="Avatar" class="avatar-img">
              </div>
              <div class="profile-actions">
                <button class="action-icon-btn" title="ข้อความ">
                  <svg viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12c0 1.85.5 3.6 1.38 5.11L2 22l4.89-1.38C8.4 21.5 10.15 22 12 22c5.52 0 10-4.48 10-10S17.52 2 12 2zm0 18c-1.44 0-2.8-.38-3.97-1.05l-.28-.17-3.02.85.86-2.95-.18-.3A7.95 7.95 0 014 12c0-4.41 3.59-8 8-8s8 3.59 8 8-3.59 8-8 8z"/></svg>
                </button>
                <button class="action-icon-btn" title="เพิ่มเพื่อน">
                  <svg viewBox="0 0 24 24"><path d="M15 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm-9-2V7H4v3H1v2h3v3h2v-3h3v-2H6zm9 4c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/></svg>
                </button>
                <button class="action-icon-btn" title="เพิ่มเติม">
                  <svg viewBox="0 0 24 24"><path d="M6 10c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2zm12 0c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2zm-6 0c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2z"/></svg>
                </button>
              </div>
            </div>
 
            <div class="profile-name">{{ user.username if user and user.username else 'ผู้ใช้งานทั่วไป' }}</div>
            <div class="profile-handle-row">
              <span>{{ user.username if user and user.username else 'username' }}</span>
              <span>•</span>
              <span style="color: #00a8fc; cursor: pointer;">เพิ่มสรรพนาม</span>
              <span>•</span>
              <span style="color: #00a8fc; cursor: pointer;">แท็กเซิร์ฟเวอร์ ▾</span>
            </div>
 
            <div class="badge-row">
              <span class="discord-badge" title="Active Developer">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="#5865f2"><path d="M20 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zM8.5 15H7v-4.5C7 9.67 7.67 9 8.5 9h1.5v1.5H8.5V15zm8 0h-1.5v-1.5h-1.5V12h3V15z"/></svg>
              </span>
            </div>
 
            <div class="roles-section">
              <div class="roles-title">บทบาท</div>
              <div class="roles-container">
                <div class="role-tag">
                  <span class="role-dot" style="background: {{ role_color }};"></span>
                  <span>{{ role_name }}</span>
                </div>
              </div>
            </div>
 
            <button class="main-chat-btn">
              <svg viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12c0 1.85.5 3.6 1.38 5.11L2 22l4.89-1.38C8.4 21.5 10.15 22 12 22c5.52 0 10-4.48 10-10S17.52 2 12 2zm0 18c-1.44 0-2.8-.38-3.97-1.05l-.28-.17-3.02.85.86-2.95-.18-.3A7.95 7.95 0 014 12c0-4.41 3.59-8 8-8s8 3.59 8 8-3.59 8-8 8z"/></svg>
              ข้อความ
            </button>
 
            <div class="divider"></div>
 
            <!-- แสดงวันที่สมัครสมาชิกจริงของผู้ใช้ -->
            <div class="info-section-title">เป็นสมาชิกตั้งแต่</div>
            <div class="info-section-value">{{ user.joined_at if user and user.joined_at else 'วันนี้' }}</div>
 
            <div class="info-section-title">การเชื่อมต่อ</div>
            <div class="connections-placeholder">
              <svg viewBox="0 0 24 24"><path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/></svg>
              เพิ่มการเชื่อมต่อ
            </div>
 
            <div class="info-section-title">หมายเหตุ (มีเฉพาะคุณที่เห็น)</div>
            <div class="note-box">คลิกเพื่อเพิ่มหมายเหตุ</div>
 
          </div>
        </div>
 
        <a href="{{ button_url | default('https://discord.com/app') }}"
           id="discord-btn"
           class="result-btn btn-success">
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
      const isIOS = /iPhone|iPad|iPod/i.test(ua) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
 
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
 
    document.getElementById('discord-btn').addEventListener('click', openDiscord);
 
    function spawnConfetti() {
      const colors = ['#ffffff', '#5865f2', '#fa777c', '#33333d'];
      const container = document.getElementById('confetti');
      if (!container) return;
      for (let i = 0; i < 30; i++) {
        const piece = document.createElement('span');
        piece.style.left = Math.random() * 100 + '%';
        piece.style.background = colors[Math.floor(Math.random() * colors.length)];
        piece.style.animationDelay = (Math.random() * 0.4) + 's';
        piece.style.animationDuration = (2.2 + Math.random() * 0.8) + 's';
        container.appendChild(piece);
      }
    }
 
    setTimeout(function () {
      document.getElementById('phase-checking').classList.remove('active');
      document.getElementById('phase-result').classList.add('active');
      document.body.classList.remove('phase-checking');
      document.body.classList.add('phase-success');
      spawnConfetti();
    }, 3500);
  </script>
 
</body>
</html>
"""
app = Flask(__name__)

@app.route('/favicon.ico')
def favicon():
    return '', 204

def _role_color_hex(color_int):
    if not color_int:
        return "#99AAB5"
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
    return {"name": "Verified", "color": "#57F287"}

@app.route("/")
def home():
    discord_login_url = (
        f"https://discord.com/api/oauth2/authorize?client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}&response_type=code&scope=identify%20guilds.join"
    )
    return render_template_string(
        HTML_TEMPLATE,
        title="ยืนยันตัวตน",
        subtitle="กำลังนำคุณไปหน้ายืนยันตัวตนผ่าน Discord",
        button_url=discord_login_url,
        button_text="🚀 เข้าสู่ระบบผ่าน Discord",
        user=None,
    )

@app.route("/callback", strict_slashes=False)
def callback():
    code = request.args.get("code")
    if not code:
        return "ไม่พบรหัสยืนยันตัวตน", 400

    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    token_resp = requests.post("https://discord.com/api/oauth2/token", data=data, headers=headers)
    access_token = token_resp.json().get("access_token")

    if not access_token:
        return "เกิดข้อผิดพลาดในการขอ Token", 400

    user_data = requests.get("https://discord.com/api/users/@me", headers={"Authorization": f"Bearer {access_token}"}).json()
    user_id = user_data.get("id")
    username = user_data.get("username")
    avatar_id = user_data.get("avatar")
    avatar_url = f"https://cdn.discordapp.com/avatars/{user_id}/{avatar_id}.png" if avatar_id else "https://cdn.discordapp.com/embed/avatars/0.png"

    # คำนวณวันที่สมัครสมาชิกจาก Discord Snowflake ID
    timestamp = ((int(user_id) >> 22) + 1420070400000) / 1000
    joined_dt = datetime.datetime.utcfromtimestamp(timestamp)
    joined_date_thai = thai_date(joined_dt)

    user_info = {
        "id": user_id, 
        "username": username, 
        "avatar_url": avatar_url,
        "joined_at": joined_date_thai
    }

    bot_headers = {"Authorization": f"Bot {BOT_TOKEN}"}
    add_role_url = f"https://discord.com/api/v10/guilds/{GUILD_ID}/members/{user_id}/roles/{ROLE_ID}"
    r = requests.put(add_role_url, headers=bot_headers)

    role_info = get_role_info(GUILD_ID, ROLE_ID)

    if r.status_code in [204, 200]:
        return render_template_string(
            HTML_TEMPLATE,
            title="ยืนยันตัวตนสำเร็จ",
            user=user_info,
            role_name=role_info["name"],
            role_color=role_info["color"],
        )
    else:
        return render_template_string(
            HTML_TEMPLATE,
            title="เกิดข้อผิดพลาด",
            user=user_info,
            role_name=role_info["name"],
            role_color=role_info["color"],
        )

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
