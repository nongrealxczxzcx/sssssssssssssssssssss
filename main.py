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
 
HTML_TEMPLATE = """<!DOCTYPE html
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

  /* Futuristic Background Mesh */
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

  /* Main Container Card */
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

  /* Loading State */
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

  /* --- Ultra-Premium Profile Card --- */
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

  .avatar-wrap {
    position: relative;
  }

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

  /* Info Details Box */
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

  .detail-label {
    color: var(--text-muted);
  }

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

  /* Action Button */
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

  /* Confetti */
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

      <!-- PHASE 1: LOADING -->
      <div class="phase active" id="phase-loading">
        <div class="brand-tag">STIF SHOP SYSTEM</div>
        <div class="loader-box">
          <div class="spinner"></div>
          <div class="loader-dot"></div>
        </div>
        <div class="title">{{ title | default('กำลังตรวจสอบข้อมูล') }}</div>
        <div class="subtitle">ระบบกำลังตรวจสอบสิทธิ์บัญชี Discord<br>และดำเนินการเพิ่มยศให้คุณอัตโนมัติ</div>
      </div>

      <!-- PHASE 2: SUCCESS -->
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
        if (!clicked) { window.location.href = targetUrl; }
      }, 1500);
    });

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
