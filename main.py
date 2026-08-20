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
<title>{{ title | default('ระบบยืนยันตัวตน STIF SHOP') }}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Kanit:wght@300;400;500;600;700&family=Sarabun:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
  :root {
    --bg-base: #07090e;
    --card-bg: rgba(17, 18, 24, 0.75);
    --card-border: rgba(35, 165, 89, 0.25);
    --accent-green: #23a559;
    --accent-green-hover: #1f8b4c;
    --text-main: #f2f3f5;
    --text-muted: #949ba4;
  }

  * { box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }

  html, body {
    height: 100%;
    min-height: 100dvh;
    background-color: var(--bg-base);
    font-family: 'Sarabun', 'Kanit', sans-serif;
    color: var(--text-main);
    overflow-x: hidden;
    overflow-y: auto;
  }

  body {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 20px 16px;
    position: relative;
    isolation: isolate;
  }

  /* Dynamic Background Effects */
  .bg-glow {
    position: fixed;
    inset: 0;
    z-index: 1;
    pointer-events: none;
    background: 
      radial-gradient(circle at 50% 15%, rgba(35, 165, 89, 0.18), transparent 50%),
      radial-gradient(circle at 10% 90%, rgba(88, 101, 242, 0.1), transparent 40%);
  }

  .bg-noise {
    position: fixed;
    inset: 0;
    z-index: 2;
    pointer-events: none;
    background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)' opacity='0.025'/%3E%3C/svg%3E");
  }

  .wrapper {
    position: relative;
    z-index: 10;
    width: 100%;
    max-width: 420px;
  }

  .main-card {
    background: var(--card-bg);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid var(--card-border);
    border-radius: 24px;
    padding: 28px 22px;
    box-shadow: 0 24px 60px rgba(0, 0, 0, 0.8), 0 0 40px rgba(35, 165, 89, 0.1);
    text-align: center;
    animation: cardAppear 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards;
  }

  @keyframes cardAppear {
    from { opacity: 0; transform: translateY(24px) scale(0.96); }
    to { opacity: 1; transform: translateY(0) scale(1); }
  }

  .phase { display: none; }
  .phase.active { display: block; animation: fadeIn 0.5s ease forwards; }

  @keyframes fadeIn {
    from { opacity: 0; transform: translateY(8px); }
    to { opacity: 1; transform: translateY(0); }
  }

  /* Loading State Styles */
  .loader-box {
    position: relative;
    width: 90px;
    height: 90px;
    margin: 0 auto 24px;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .spinner-ring {
    position: absolute;
    inset: 0;
    border-radius: 50%;
    border: 3px solid transparent;
    border-top-color: var(--accent-green);
    border-right-color: rgba(35, 165, 89, 0.2);
    animation: spin 1s cubic-bezier(0.68, -0.55, 0.265, 1.55) infinite;
  }
  .spinner-ring-inner {
    position: absolute;
    inset: 10px;
    border-radius: 50%;
    border: 3px solid transparent;
    border-bottom-color: #5865f2;
    animation: spinReverse 0.8s linear infinite;
  }
  @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
  @keyframes spinReverse { 0% { transform: rotate(360deg); } 100% { transform: rotate(0deg); } }
  
  .loader-core {
    width: 14px;
    height: 14px;
    background: var(--accent-green);
    border-radius: 50%;
    box-shadow: 0 0 15px var(--accent-green);
    animation: pulse 1.2s ease-in-out infinite alternate;
  }
  @keyframes pulse { from { transform: scale(0.8); opacity: 0.6; } to { transform: scale(1.3); opacity: 1; } }

  .brand-tag {
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 2.5px;
    text-transform: uppercase;
    color: var(--accent-green);
    margin-bottom: 8px;
  }

  .title {
    font-family: 'Kanit', sans-serif;
    font-size: 1.35rem;
    font-weight: 600;
    color: #fff;
    margin-bottom: 8px;
  }

  .subtitle {
    font-size: 0.85rem;
    color: var(--text-muted);
    line-height: 1.6;
    margin-bottom: 24px;
  }

  .status-pill {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: rgba(35, 165, 89, 0.08);
    border: 1px solid rgba(35, 165, 89, 0.2);
    padding: 10px 18px;
    border-radius: 50px;
    font-size: 0.82rem;
    color: #fff;
  }
  .dots span {
    display: inline-block;
    width: 4px;
    height: 4px;
    margin-left: 2px;
    background: var(--accent-green);
    border-radius: 50%;
    animation: bounce 1.4s infinite ease-in-out both;
  }
  .dots span:nth-child(2) { animation-delay: 0.2s; }
  .dots span:nth-child(3) { animation-delay: 0.4s; }
  @keyframes bounce { 0%, 80%, 100% { transform: scale(0); } 40% { transform: scale(1.0); } }

  /* Discord Profile UI Preview Card */
  .dc-profile {
    background: #18191c;
    border-radius: 16px;
    overflow: hidden;
    text-align: left;
    border: 1px solid rgba(255, 255, 255, 0.06);
    box-shadow: 0 12px 30px rgba(0, 0, 0, 0.6);
    margin-bottom: 20px;
  }

  .dc-banner {
    height: 95px;
    background: linear-gradient(135deg, #1e3526 0%, #111214 100%);
    position: relative;
    padding: 12px;
    display: flex;
    justify-content: flex-end;
    align-items: flex-start;
    border-bottom: 1px solid rgba(35, 165, 89, 0.2);
  }

  .verified-badge {
    background: rgba(35, 165, 89, 0.2);
    backdrop-filter: blur(8px);
    border: 1px solid rgba(35, 165, 89, 0.4);
    padding: 5px 12px;
    border-radius: 20px;
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 0.72rem;
    font-weight: 700;
    color: #2ecc71;
    box-shadow: 0 4px 12px rgba(35, 165, 89, 0.25);
  }
  .verified-badge svg { width: 12px; height: 12px; fill: #2ecc71; }

  .dc-content {
    padding: 0 16px 16px;
    background: #111214;
    position: relative;
  }

  .dc-avatar-row {
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    margin-top: -38px;
    margin-bottom: 10px;
  }

  .dc-avatar {
    width: 78px;
    height: 78px;
    border-radius: 50%;
    border: 5px solid #111214;
    object-fit: cover;
    box-shadow: 0 4px 12px rgba(0,0,0,0.5);
  }

  .dc-action-btns {
    display: flex;
    gap: 6px;
  }
  .dc-icon-btn {
    width: 34px;
    height: 34px;
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
  .dc-icon-btn:hover { background: #35373c; color: #fff; }
  .dc-icon-btn svg { width: 16px; height: 16px; fill: currentColor; }

  .dc-username {
    font-family: 'Kanit', sans-serif;
    font-size: 1.15rem;
    font-weight: 700;
    color: #f2f3f5;
    margin-bottom: 2px;
  }

  .dc-subtext {
    font-size: 0.78rem;
    color: var(--text-muted);
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .dc-section-title {
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    color: var(--text-muted);
    letter-spacing: 0.5px;
    margin-bottom: 6px;
  }

  .dc-role-wrap {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-bottom: 14px;
  }
  .dc-role-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: #2b2d31;
    padding: 4px 10px;
    border-radius: 6px;
    font-size: 0.75rem;
    color: #dbdee1;
    border: 1px solid rgba(255,255,255,0.03);
  }
  .dc-role-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
  }

  .dc-divider {
    height: 1px;
    background: #232428;
    margin: 12px 0;
  }

  .dc-info-grid {
    font-size: 0.8rem;
    color: #dbdee1;
    margin-bottom: 12px;
  }

  /* Success Action Button */
  .btn-action {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    width: 100%;
    padding: 14px;
    background: linear-gradient(135deg, #2ecc71 0%, var(--accent-green) 100%);
    color: #fff;
    font-family: 'Kanit', sans-serif;
    font-weight: 600;
    font-size: 1rem;
    border-radius: 14px;
    text-decoration: none;
    border: 1px solid rgba(255, 255, 255, 0.2);
    box-shadow: 0 6px 20px rgba(35, 165, 89, 0.4);
    transition: all 0.25s ease;
    cursor: pointer;
  }
  .btn-action:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba(35, 165, 89, 0.6);
    background: linear-gradient(135deg, #27ae60 0%, var(--accent-green-hover) 100%);
  }

  /* Confetti Animation Elements */
  .confetti-container {
    position: absolute;
    inset: 0;
    pointer-events: none;
    overflow: hidden;
    z-index: 5;
  }
  .confetti-piece {
    position: absolute;
    top: -10px;
    width: 8px;
    height: 12px;
    border-radius: 3px;
    animation: fall linear forwards;
  }
  @keyframes fall {
    0% { transform: translateY(0) rotate(0deg); opacity: 1; }
    100% { transform: translateY(350px) rotate(720deg); opacity: 0; }
  }
</style>
</head>
<body>

  <div class="bg-glow"></div>
  <div class="bg-noise"></div>

  <div class="wrapper">
    <div class="main-card">

      <!-- PHASE 1: LOADING -->
      <div class="phase active" id="phase-loading">
        <div class="brand-tag">STIF SHOP SECURITY</div>
        <div class="loader-box">
          <div class="spinner-ring"></div>
          <div class="spinner-ring-inner"></div>
          <div class="loader-core"></div>
        </div>
        <div class="title">{{ title | default('กำลังตรวจสอบข้อมูล') }}</div>
        <div class="subtitle">ระบบกำลังตรวจสอบสิทธิ์บัญชี Discord<br>และดำเนินการเพิ่มยศให้อัตโนมัติ</div>
        <div class="status-pill">
          <span>กำลังเชื่อมต่อเซิร์ฟเวอร์</span>
          <div class="dots"><span></span><span></span><span></span></div>
        </div>
      </div>

      <!-- PHASE 2: SUCCESS RESULT -->
      <div class="phase" id="phase-success">
        <div class="confetti-container" id="confettiBox"></div>

        <div class="dc-profile">
          <div class="dc-banner">
            <div class="verified-badge">
              <svg viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/></svg>
              <span>ยืนยันตัวตนแล้ว</span>
            </div>
          </div>

          <div class="dc-content">
            <div class="dc-avatar-row">
              <img src="{{ user.avatar_url if user and user.avatar_url else 'https://cdn.discordapp.com/embed/avatars/0.png' }}" class="dc-avatar" alt="Avatar">
              <div class="dc-action-btns">
                <button class="dc-icon-btn" title="ส่งข้อความ"><svg viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12c0 1.85.5 3.6 1.38 5.11L2 22l4.89-1.38C8.4 21.5 10.15 22 12 22c5.52 0 10-4.48 10-10S17.52 2 12 2zm0 18c-1.44 0-2.8-.38-3.97-1.05l-.28-.17-3.02.85.86-2.95-.18-.3A7.95 7.95 0 014 12c0-4.41 3.59-8 8-8s8 3.59 8 8-3.59 8-8 8z"/></svg></button>
                <button class="dc-icon-btn" title="เพิ่มเพื่อน"><svg viewBox="0 0 24 24"><path d="M15 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm-9-2V7H4v3H1v2h3v3h2v-3h3v-2H6zm9 4c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/></svg></button>
              </div>
            </div>

            <div class="dc-username">{{ user.global_name if user and user.global_name else (user.username if user else 'ผู้ใช้งานทั่วไป') }}</div>
            <div class="dc-subtext">
              <span>{{ user.username if user and user.username else 'username' }}</span>
              <span>•</span>
              <span style="color: var(--accent-green);">สถานะปลอดภัย</span>
            </div>

            <div class="dc-section-title">บทบาทที่ได้รับ</div>
            <div class="dc-role-wrap">
              <div class="dc-role-pill">
                <span class="dc-role-dot" style="background: {{ role_color }};"></span>
                <span>{{ role_name }}</span>
              </div>
            </div>

            <div class="dc-divider"></div>

            <div class="dc-section-title">เป็นสมาชิกตั้งแต่</div>
            <div class="dc-info-grid">{{ user.joined_at if user and user.joined_at else 'วันนี้' }}</div>
          </div>
        </div>

        <a href="{{ button_url | default('https://discord.com/app') }}" id="returnBtn" class="btn-action">
          <span>กลับไปที่ Discord</span>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline></svg>
        </a>
      </div>

    </div>
  </div>

  <script>
    // ฟังก์ชันช่วยสลับหน้าจอ (Loading -> Success)
    function showSuccess() {
      document.getElementById('phase-loading').classList.remove('active');
      document.getElementById('phase-success').classList.add('active');
      triggerConfetti();
    }

    // สร้างเอฟเฟกต์พลุฉลอง
    function triggerConfetti() {
      const box = document.getElementById('confettiBox');
      const colors = ['#23a559', '#2ecc71', '#5865f2', '#ffffff', '#f1c40f'];
      for (let i = 0; i < 40; i++) {
        const p = document.createElement('div');
        p.className = 'confetti-piece';
        p.style.left = Math.random() * 100 + '%';
        p.style.backgroundColor = colors[Math.floor(Math.random() * colors.length)];
        p.style.animationDuration = (2 + Math.random() * 1.5) + 's';
        p.style.animationDelay = (Math.random() * 0.3) + 's';
        box.appendChild(p);
      }
    }

    // ระบบตรวจจับเปิดแอป Discord อัตโนมัติ (Deep Link)
    document.getElementById('returnBtn').addEventListener('click', function(e) {
      e.preventDefault();
      const targetUrl = this.href;
      const ua = navigator.userAgent || navigator.vendor || window.opera;
      const isMobile = /android|iphone|ipad|ipod/i.test(ua);

      if (!isMobile) {
        window.location.href = targetUrl;
        return;
      }

      let clicked = false;
      window.addEventListener('blur', function() { clicked = true; }, { once: true });
      
      window.location.href = 'discord://';
      setTimeout(function() {
        if (!clicked) {
          window.location.href = targetUrl;
        }
      }, 1500);
    });

    // หน่วงเวลาจำลองการตรวจสอบ 3 วินาทีแล้วแสดงหน้าสำเร็จสวยงาม
    setTimeout(showSuccess, 3000);
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
    global_name = user_data.get("global_name")
    avatar_id = user_data.get("avatar")
    avatar_url = f"https://cdn.discordapp.com/avatars/{user_id}/{avatar_id}.png" if avatar_id else "https://cdn.discordapp.com/embed/avatars/0.png"

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

    bot_headers = {"Authorization": f"Bot {BOT_TOKEN}"}
    add_role_url = f"https://discord.com/api/v10/guilds/{GUILD_ID}/members/{user_id}/roles/{ROLE_ID}"
    r = requests.put(add_role_url, headers=bot_headers)

    role_info = get_role_info(GUILD_ID, ROLE_ID)

    return render_template_string(
        HTML_TEMPLATE,
        title="ยืนยันตัวตนสำเร็จ",
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
