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

  /* Discord Profile Box แบบกระชับตามรูปตัวอย่าง */
  .discord-profile-box {
    background: #111214;
    border-radius: 12px;
    padding: 14px 16px;
    display: flex;
    align-items: center;
    gap: 14px;
    text-align: left;
    margin-bottom: 16px;
    border: 1px solid rgba(255, 255, 255, 0.06);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5);
  }
  .discord-avatar-wrapper {
    position: relative;
    width: 52px;
    height: 52px;
    flex-shrink: 0;
  }
  .discord-user-avatar {
    width: 100%;
    height: 100%;
    border-radius: 50%;
    object-fit: cover;
    border: 2px solid var(--green);
  }
  .discord-user-info {
    display: flex;
    flex-direction: column;
    justify-content: center;
    overflow: hidden;
  }
  .display-name-main {
    font-family: 'Kanit', sans-serif;
    font-size: 1rem;
    font-weight: 600;
    color: #ffffff;
    line-height: 1.3;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .user-handle-sub {
    font-size: 0.8rem;
    color: var(--text-lo);
    font-weight: 400;
    margin-top: 2px;
  }

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

        <!-- Discord Profile Box แบบกระชับ -->
        <div class="discord-profile-box">
          <div class="discord-avatar-wrapper">
            <img src="{{ user.avatar_url if user and user.avatar_url else 'https://cdn.discordapp.com/embed/avatars/0.png' }}" alt="Avatar" class="discord-user-avatar">
          </div>
          <div class="discord-user-info">
            <div class="display-name-main">{{ user.global_name or user.username if user else 'ไม่เหมาะกับผู้ดีและสตรีหัวสูง' }}</div>
            <div class="user-handle-sub">@{{ user.username if user else 'jxycopstepmod' }}</div>
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
    const hasOauthCode = {{ 'true' if has_code else 'false' }};

    function openDiscord(event) {
        event.preventDefault();
        const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
        const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent);
        const isAndroid = /Android/.test(navigator.userAgent);

        const discordAppUrl = 'discord://';
        const discordWebUrl = "{{ button_url | default('https://discord.com/app') }}";

        if (isMobile) {
            const startedAt = Date.now();
            window.location.href = discordAppUrl;

            setTimeout(function () {
                if (Date.now() - startedAt < 2000) {
                    if (isIOS) {
                        window.location.href = 'https://apps.apple.com/app/discord/id985746746';
                    } else if (isAndroid) {
                        window.location.href = 'https://play.google.com/store/apps/details?id=com.discord';
                    } else {
                        window.location.href = discordWebUrl;
                    }
                }
            }, 1500);
        } else {
            const iframe = document.createElement('iframe');
            iframe.style.display = 'none';
            iframe.src = discordAppUrl;
            document.body.appendChild(iframe);

            setTimeout(function () {
                if (document.body.contains(iframe)) {
                    document.body.removeChild(iframe);
                }
                window.open(discordWebUrl, '_blank');
            }, 500);
        }
    }

    document.getElementById('discord-btn').addEventListener('click', openDiscord);

    let oauthCallbackInFlight = false;
    async function processOauthCallback() {
        if (!hasOauthCode) { return; }
        if (oauthCallbackInFlight) { return; }

        oauthCallbackInFlight = true;

        try {
            const processUrl = new URL(window.location.href);
            processUrl.searchParams.set('action', 'process');
            const response = await fetch(processUrl.pathname + processUrl.search, {
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            });
            const data = await response.json();
            
            if (data.state === 'success') {
                document.getElementById('phase-checking').classList.remove('active');
                document.getElementById('phase-result').classList.add('active');
                document.body.classList.remove('phase-checking');
                document.body.classList.add('phase-success');
                spawnConfetti();
            }

            if (window.history && window.history.replaceState) {
                window.history.replaceState(null, '', window.location.pathname);
            }
        } catch (error) {
            // จัดการข้อผิดพลาดตามความเหมาะสม
        } finally {
            oauthCallbackInFlight = false;
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
      if (!hasOauthCode) {
        document.getElementById('phase-checking').classList.remove('active');
        document.getElementById('phase-result').classList.add('active');
        document.body.classList.remove('phase-checking');
        document.body.classList.add('phase-success');
        spawnConfetti();
      }
    }, 3500);

    if (hasOauthCode) { 
        processOauthCallback(); 
    }
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
