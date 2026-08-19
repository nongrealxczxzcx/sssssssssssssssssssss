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
REDIRECT_URI = "https://sdfsafasfasfsafasf.onrender.com/callback"

GUILD_ID = 1207514483527000084
ROLE_ID = 1211224793060478976

if not BOT_TOKEN or not CLIENT_SECRET:
    raise RuntimeError(
        "กรุณาตั้งค่า BOT_TOKEN และ CLIENT_SECRET เป็น environment variable ก่อนรัน "
        "(ห้าม hardcode ไว้ในไฟล์ เพราะเป็นข้อมูลลับที่รั่วไหลได้ง่ายมาก)"
    )

THAI_MONTHS = [
    "", "ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.",
    "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค.",
]
 
 
def thai_date(dt=None):
    dt = dt or datetime.datetime.utcnow()
    return f"{dt.day} {THAI_MONTHS[dt.month]} {dt.year + 543}"
 
 
HTML_TEMPLATE = """<!DOCTYPE html>
<!DOCTYPE html>
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

  /* Loader สไตล์โซนาร์พรีเมียม (Phase 1) */
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

  /* ผลลัพธ์ (Phase 2) */
  .result-title {
    font-family: 'Kanit', sans-serif;
    font-size: 1.35rem; font-weight: 700; margin-bottom: 16px;
    background: linear-gradient(90deg, #57F287, #22d3ee);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  }

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
  .role-remove-icon { width: 12px; height: 12px; fill: #949ba4; cursor: pointer; transition: fill 0.2s; }
  .role-remove-icon:hover { fill: #ffffff; }

  .result-message { margin-bottom: 16px; color: #b5bac1; font-size: 0.86rem; font-weight: 400; }

  .discord-btn-primary {
    display: flex; align-items: center; justify-content: center; gap: 8px;
    width: 100%; background: linear-gradient(135deg, #23a55a, #1f934e);
    color: #fff; font-weight: 600; font-size: 0.95rem; padding: 12px;
    border-radius: 12px; text-decoration: none; border: none; cursor: pointer;
    transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    font-family: 'Sarabun', 'Kanit', sans-serif;
    box-shadow: 0 6px 20px rgba(35, 165, 90, 0.4);
  }
  .discord-btn-primary:hover {
    background: linear-gradient(135deg, #26b763, #22a55a);
    transform: translateY(-2px); box-shadow: 0 8px 25px rgba(35, 165, 90, 0.6);
  }
  .discord-btn-primary:active { transform: scale(0.98); }

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

      <!-- Phase 1: หน้าจอตรวจสอบ/โหลดอัตโนมัติ -->
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

      <!-- Phase 2: หน้าจอผลลัพธ์สำเร็จ -->
      <div class="phase" id="phase-result">
        <div class="confetti" id="confetti"></div>

        <h1 class="result-title">{{ result_title | default('ให้ยศสำเร็จ') }}</h1>

        {% if user %}
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
                <img src="{{ user.avatar_url }}" alt="Avatar" class="discord-user-avatar">
                <div class="avatar-status-dot"></div>
              </div>
            </div>

            <div class="display-name-main">{{ user.username | default('jxycopstepmod') }}</div>
            <div class="user-handle-sub">
              <span>@{{ user.username | default('jxycopstepmod') }}</span>
              <span>•</span>
              <span>ID: {{ user.id | default('1183718234806038563') }}</span>
            </div>

            <div class="divider-line"></div>

            <div class="profile-info-block">
              <div class="label">บทบาท</div>
              <div class="roles-container">
                <div class="role-tag">
                  <span class="role-dot"></span>
                  <span>User</span>
                  <svg class="role-remove-icon" viewBox="0 0 24 24"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>
                </div>
              </div>
            </div>

            <div class="profile-info-block" style="margin-bottom: 0; margin-top: 10px;">
              <div class="label" style="display:flex; align-items:center; gap:5px; color: #b5bac1; font-size: 0.72rem; text-transform: none; font-weight: 500;">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><path d="M19 3h-1V1h-2v2H8V1H6v2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H5V8h14v11z"/></svg>
                ยืนยันตัวตนเมื่อ วันนี้
              </div>
            </div>

          </div>
        </div>
        {% endif %}

        <p class="result-message">{{ result_message | default('ระบบได้เพิ่มยศให้คุณเรียบร้อยแล้ว') }}</p>

        <a href="{{ button_url | default('https://discord.com/app') }}" class="discord-btn-primary" onclick="openDiscord(event)">
          {{ button_text | default('กลับไปที่ Discord') }}
        </a>
      </div>

    </div>
  </div>

  <script>
    history.pushState(null, '', window.location.href);
    window.addEventListener('popstate', function (event) {
      openDiscord(null);
    });

    function openDiscord(event) {
      if (event) event.preventDefault();
      const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
      if (isMobile) {
        window.location.href = 'discord://';
        setTimeout(() => { window.location.href = 'https://discord.com/app'; }, 1500);
      } else {
        window.location.href = 'https://discord.com/app';
      }
    }

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
      document.body.classList.add('phase-success');
      spawnConfetti();
    }, 3500);
  </script>

</body>
</html>
"""
app = Flask(__name__)

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

def get_role_name(guild_id, role_id):
    info = get_role_info(guild_id, role_id)
    return info["name"]

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
        result_state="processing",
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
        return "เกิดข้อผิดพลาด", 400

    user_data = requests.get("https://discord.com/api/users/@me", headers={"Authorization": f"Bearer {access_token}"}).json()
    user_id = user_data.get("id")
    username = user_data.get("username")
    avatar_id = user_data.get("avatar")
    avatar_url = f"https://cdn.discordapp.com/avatars/{user_id}/{avatar_id}.png" if avatar_id else "https://cdn.discordapp.com/embed/avatars/0.png"

    user_info = {"id": user_id, "username": username, "avatar_url": avatar_url}

    bot_headers = {"Authorization": f"Bot {BOT_TOKEN}"}
    add_role_url = f"https://discord.com/api/v10/guilds/{GUILD_ID}/members/{user_id}/roles/{ROLE_ID}"
    r = requests.put(add_role_url, headers=bot_headers)

    if r.status_code in [204, 200]:
        return render_template_string(
            HTML_TEMPLATE,
            title="ยืนยันตัวตนสำเร็จ",
            result_state="success",
            result_title="ให้ยศสำเร็จ",
            result_message="ระบบได้เพิ่มยศให้คุณเรียบร้อยแล้ว",
            user=user_info,
            role_name=get_role_name(GUILD_ID, ROLE_ID) or "Verified",
        )
    else:
        return render_template_string(
            HTML_TEMPLATE,
            title="เกิดข้อผิดพลาด",
            result_state="error",
            result_title="เกิดข้อผิดพลาด",
            result_message="ไม่สามารถเพิ่มยศได้ (ตรวจสอบลำดับยศของบอท)",
            user=user_info,
        )


class VerifyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(
            discord.ui.Button(
                label="ยืนยันตัวตนเข้าดิส",
                url="https://discord.com/oauth2/authorize?client_id=1292567654405771334&response_type=code&redirect_uri=https%3A%2F%2Fsdfsafasfasfsafasf.onrender.com%2Fcallback&scope=identify+guilds.join",
                style=discord.ButtonStyle.link,
                emoji="<a:emoji_125:1283873278129213471>",
            )
        )

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")

    activity = discord.Streaming(name="อยากดูหี", url="https://www.twitch.tv/Jxycop_x")
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
        description=f"🛒   บอทรับยศ 24 ชั่วโมง\n\n"
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
