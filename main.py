import os
import threading
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

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
<title>{{ title | default('โปรไฟล์ผู้ใช้ Discord') }}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Kanit:wght@300;400;500;600;700&family=Sarabun:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
  :root {
    --discord-bg: #111214;
    --discord-modal: #2b2d31;
    --discord-input: #1e1f22;
    --discord-text-normal: #dbdee1;
    --discord-text-muted: #949ba4;
    --discord-header: #f2f3f5;
    --discord-blurple: #5865f2;
    --discord-green: #23a55a;
    --border-color: #3f4147;
  }
  *{box-sizing:border-box;margin:0;padding:0;-webkit-tap-highlight-color:transparent;}
  html,body{
    height:100%;
    min-height:100dvh;
    background: #0b0d13;
    overflow-x:hidden;
    font-family:'Sarabun','Kanit',sans-serif;
    color: var(--discord-text-normal);
  }
  body{
    display:flex;
    align-items:center;
    justify-content:center;
    padding:16px;
    position: relative;
    overflow: hidden;
  }

  /* พื้นหลัง (Background Effects) */
  .bg-glow-container {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    overflow: hidden;
    z-index: 1;
    pointer-events: none;
  }
  .glow-orb {
    position: absolute;
    border-radius: 50%;
    filter: blur(80px);
    opacity: 0.35;
    animation: floatOrb 10s ease-in-out infinite alternate;
  }
  .glow-1 { width: 300px; height: 300px; background: #5865f2; top: -100px; left: -100px; }
  .glow-2 { width: 350px; height: 350px; background: #eb459e; bottom: -120px; right: -100px; animation-delay: -5s; }
  .glow-3 { width: 250px; height: 250px; background: #23a55a; top: 40%; left: 60%; opacity: 0.2; animation-duration: 14s; }
  @keyframes floatOrb {
    0% { transform: translateY(0px) scale(1); }
    100% { transform: translateY(30px) scale(1.1); }
  }
  .bg-grid {
    position: absolute;
    top: 0; left: 0; width: 100%; height: 100%;
    background-image: linear-gradient(rgba(255, 255, 255, 0.02) 1px, transparent 1px),
                      linear-gradient(90deg, rgba(255, 255, 255, 0.02) 1px, transparent 1px);
    background-size: 32px 32px;
    z-index: 2;
    pointer-events: none;
  }

  /* Discord Profile Modal Card */
  .discord-profile-card {
    width: 100%;
    max-width: 360px;
    background: var(--discord-modal);
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 16px 40px rgba(0,0,0,0.6), 0 0 0 1px rgba(255,255,255,0.08);
    position: relative;
    z-index: 10;
    animation: cardIn 0.5s cubic-bezier(.2,.8,.2,1) both;
  }
  @keyframes cardIn { from{opacity:0; transform:translateY(12px) scale(0.98);} to{opacity:1; transform:translateY(0) scale(1);} }

  /* Banner */
  .discord-banner {
    width: 100%;
    height: 110px;
    background: #35363c;
    background-size: cover;
    background-position: center;
    position: relative;
  }

  /* Body Container inside Card */
  .discord-body {
    padding: 0 16px 16px 16px;
    position: relative;
  }

  /* Avatar Row */
  .discord-header-row {
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    margin-top: -38px;
    margin-bottom: 12px;
    position: relative;
    z-index: 2;
  }
  .discord-avatar-wrap {
    position: relative;
    width: 80px;
    height: 80px;
    border-radius: 50%;
    background: var(--discord-modal);
    padding: 4px;
  }
  .discord-avatar {
    width: 100%;
    height: 100%;
    border-radius: 50%;
    object-fit: cover;
  }
  .discord-status-dot {
    position: absolute;
    bottom: 6px;
    right: 6px;
    width: 16px;
    height: 16px;
    background: var(--discord-green);
    border: 3px solid var(--discord-modal);
    border-radius: 50%;
  }

  /* Action Buttons Top Right */
  .discord-actions-top { display: flex; gap: 8px; }
  .icon-btn {
    background: var(--discord-input);
    border: none; width: 36px; height: 36px;
    border-radius: 50%; display: flex; align-items: center; justify-content: center;
    color: var(--discord-text-normal); cursor: pointer; transition: background 0.2s;
  }
  .icon-btn:hover { background: #35363c; }
  .icon-btn svg { width: 18px; height: 18px; fill: currentColor; }

  /* User Info Box */
  .discord-user-info-box {
    background: var(--discord-bg);
    border-radius: 8px;
    padding: 12px;
    margin-bottom: 12px;
  }
  .display-name {
    font-family: 'Kanit', sans-serif;
    font-size: 1.15rem;
    font-weight: 600;
    color: var(--discord-header);
    line-height: 1.2;
    margin-bottom: 2px;
  }
  .username-sub {
    font-size: 0.85rem;
    color: var(--discord-text-muted);
    margin-bottom: 8px;
  }
  .divider {
    height: 1px;
    background: var(--border-color);
    margin: 10px 0;
  }

  /* Section Titles & Roles Tags */
  .section-title {
    font-size: 0.75rem;
    font-weight: 700;
    color: var(--discord-text-muted);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 8px;
  }
  .roles-container {
    display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 12px;
  }
  .role-tag {
    display: inline-flex; align-items: center; gap: 6px;
    background: var(--discord-input); padding: 4px 10px; border-radius: 6px;
    font-size: 0.8rem; color: var(--discord-text-normal);
    border: 1px solid rgba(255,255,255,0.04);
  }
  .role-dot {
    width: 8px; height: 8px; border-radius: 50%;
    background: {{ role_color | default('#57F287') }};
  }

  /* Member Since */
  .member-info {
    font-size: 0.82rem; color: var(--discord-text-muted);
    margin-bottom: 4px; display: flex; align-items: center; gap: 6px;
  }

  /* Action Button Bottom */
  .discord-btn-primary {
    display: flex; align-items: center; justify-content: center; gap: 8px;
    width: 100%; background: var(--discord-blurple); color: #fff;
    font-weight: 600; font-size: 0.95rem; padding: 10px; border-radius: 4px;
    text-decoration: none; border: none; cursor: pointer; transition: background 0.2s;
    font-family: 'Sarabun', sans-serif;
  }
  .discord-btn-primary:hover { background: #4752c4; }

  /* Phase Control */
  .phase { display: none; }
  .phase.active { display: block; }
  
  .loading-box { text-align: center; padding: 30px 10px; }
  .spinner-discord {
    width: 40px; height: 40px; border: 3px solid var(--discord-input);
    border-top-color: var(--discord-blurple); border-radius: 50%;
    animation: spin 0.8s linear infinite; margin: 0 auto 16px auto;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
  .loading-text { font-size: 0.95rem; color: var(--discord-text-normal); font-weight: 500; }
</style>
</head>
<body>

  <!-- เลเยอร์พื้นหลัง -->
  <div class="bg-glow-container">
    <div class="glow-orb glow-1"></div>
    <div class="glow-orb glow-2"></div>
    <div class="glow-orb glow-3"></div>
  </div>
  <div class="bg-grid"></div>

  <div class="discord-profile-card">
    
    <div class="discord-banner" style="background-image: url('{{ banner_url | default('') }}');"></div>

    <div class="discord-body">

      <!-- Phase 1: หน้าจอตรวจสอบเริ่มต้น (Verification Gate) -->
      <div class="phase active" id="phase-verify">
        <div class="loading-box" style="padding: 15px 0;">
          <div style="font-size: 2.2rem; margin-bottom: 8px;">🛡️</div>
          <div class="display-name" style="margin-bottom: 4px;">ระบบตรวจสอบสิทธิ์</div>
          <div class="username-sub" style="margin-bottom: 20px;">กรุณายืนยันตัวตนเพื่อรับยศอัตโนมัติ</div>
          <button type="button" class="discord-btn-primary" onclick="startVerification()">
            <span>ยืนยันตัวตน (Verify)</span>
          </button>
        </div>
      </div>

      <!-- Phase 2: หน้าจอโหลดกำลังตรวจสอบ -->
      <div class="phase" id="phase-checking">
        <div class="loading-box">
          <div class="spinner-discord"></div>
          <div class="loading-text">{{ status_text | default('กำลังตรวจสอบและเพิ่มยศ...') }}</div>
          <div style="font-size: 0.8rem; color: var(--discord-text-muted); margin-top: 6px;">โปรดรอสักครู่ ระบบกำลังเชื่อมต่อกับ Discord</div>
        </div>
      </div>

      <!-- Phase 3: หน้าจอผลลัพธ์โปรไฟล์ Discord -->
      <div class="phase" id="phase-result">
        
        <div class="discord-header-row">
          <div class="discord-avatar-wrap">
            <img src="{{ user.avatar_url }}" alt="Avatar" class="discord-avatar">
            <div class="discord-status-dot"></div>
          </div>
          <div class="discord-actions-top">
            <button class="icon-btn" title="ข้อความ">
              <svg viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12c0 1.54.36 3 1 4.3L2 22l5.7-1c1.3.64 2.76 1 4.3 1 5.52 0 10-4.48 10-10S17.52 2 12 2zm0 18c-1.31 0-2.54-.34-3.62-.94l-.26-.15-3.32.58.59-3.23-.16-.27C5.34 14.54 5 13.31 5 12c0-3.87 3.13-7 7-7s7 3.13 7 7-3.13 7-7 7z"/></svg>
            </button>
            <button class="icon-btn" title="เพิ่มเติม">
              <svg viewBox="0 0 24 24"><path d="M12 8c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2zm0 2c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2zm0 6c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2z"/></svg>
            </button>
          </div>
        </div>

        {% if user %}
        <div class="discord-user-info-box">
          <!-- ชื่อใหญ่ (Global Name หรือ Username) -->
          <div class="display-name">{{ user.global_name or user.username }}</div>
          <!-- ชื่อ Username รองด้านล่าง -->
          <div class="username-sub">@{{ user.username }}</div>
          
          <div class="divider"></div>

          <div class="section-title">บทบาท</div>
          <div class="roles-container">
            {% if role_name %}
            <div class="role-tag">
              <span class="role-dot"></span>
              <span>{{ role_name }}</span>
            </div>
            {% endif %}
            <div class="role-tag">
              <span class="role-dot" style="background: var(--discord-green);"></span>
              <span>User</span>
            </div>
          </div>

          <div class="divider"></div>

          <div class="member-info">
            <span>DISCORD MEMBER • ตั้งแต่ระบบเชื่อมต่อสำเร็จ</span>
          </div>
        </div>
        {% endif %}

        <div style="font-size: 0.85rem; color: var(--discord-text-normal); margin-bottom: 14px; text-align: center;">
          {{ result_message | default('เพิ่มยศเข้าสู่บัญชีของคุณเรียบร้อยแล้ว!') }}
        </div>

        <a href="{{ button_url | default('https://discord.com/app') }}" class="discord-btn-primary">
          {{ button_text | default('กลับไปที่ Discord') }}
        </a>

      </div>

    </div>
  </div>

  <script>
    function startVerification() {
      const verifyPhase = document.getElementById('phase-verify');
      verifyPhase.classList.remove('active');
      verifyPhase.style.display = 'none';
      
      const checkingPhase = document.getElementById('phase-checking');
      checkingPhase.classList.add('active');
      checkingPhase.style.display = 'block';

      const CHECK_DELAY_MS = 4000; 
      setTimeout(function () {
        checkingPhase.classList.remove('active');
        checkingPhase.style.display = 'none';
        document.getElementById('phase-result').classList.add('active');
      }, CHECK_DELAY_MS);
    }
  </script>

</body>
</html>
"""
app = Flask(__name__)

def get_role_name(guild_id, role_id):
    try:
        resp = requests.get(
            f"https://discord.com/api/v10/guilds/{guild_id}/roles",
            headers={"Authorization": f"Bot {BOT_TOKEN}"},
        )
        resp.raise_for_status()
        for role in resp.json():
            if str(role.get("id")) == str(role_id):
                return role.get("name")
    except Exception as e:
        print("ดึงชื่อยศไม่สำเร็จ:", e)
    return None

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
