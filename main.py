import os
import threading
import discord
from discord import app_commands
from discord.ext import commands
from flask import Flask, redirect, request, render_template_string
import requests

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CLIENT_ID = os.environ.get("CLIENT_ID")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET")
REDIRECT_URI = "https://sssssssssssssssssssss-5l9s.onrender.com/callback"

GUILD_ID = 1401504117511164076
ROLE_ID = 1401506804671971398

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
<title>{{ title | default('กำลังตรวจสอบ') }}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Kanit:wght@300;400;500;600;700&family=Sarabun:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
  :root{
    --bg-0:#07070c;
    --violet:#8b5cf6;
    --magenta:#ec4899;
    --cyan:#22d3ee;
    --green:#57F287;
    --red:#ED4245;
    --text-hi:#f5f4fb;
    --text-lo:#9695ac;
    --card:rgba(255,255,255,0.05);
    --card-border:rgba(255,255,255,0.1);
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
    padding:calc(20px + env(safe-area-inset-top)) calc(16px + env(safe-area-inset-right)) calc(20px + env(safe-area-inset-bottom)) calc(16px + env(safe-area-inset-left));
  }

  /* ---------- background atmosphere ---------- */
  .noise{
    position:fixed;inset:0;
    background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='120' height='120'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.035'/%3E%3C/svg%3E");
    mix-blend-mode:overlay;
    pointer-events:none;
    z-index:5;
  }
  .blob{
    position:fixed;
    border-radius:50%;
    filter:blur(min(90px, 12vw));
    opacity:0.5;
    will-change:transform;
    transition:background 0.6s ease;
  }
  .blob-1{
    width:clamp(260px, 62vw, 520px);
    height:clamp(260px, 62vw, 520px);
    background:radial-gradient(circle at 30% 30%, var(--violet), transparent 70%);
    top:-14vh; left:-14vw;
    animation:drift1 22s ease-in-out infinite;
  }
  .blob-2{
    width:clamp(220px, 55vw, 460px);
    height:clamp(220px, 55vw, 460px);
    background:radial-gradient(circle at 60% 40%, var(--cyan), transparent 70%);
    bottom:-16vh; right:-12vw;
    animation:drift2 26s ease-in-out infinite;
  }
  .blob-3{
    width:clamp(170px, 43vw, 360px);
    height:clamp(170px, 43vw, 360px);
    background:radial-gradient(circle at 50% 50%, var(--magenta), transparent 70%);
    bottom:8%; left:6%;
    opacity:0.32;
    animation:drift3 30s ease-in-out infinite;
  }
  body.phase-success .blob-3{ background:radial-gradient(circle at 50% 50%, var(--green), transparent 70%); }
  body.phase-error .blob-3{ background:radial-gradient(circle at 50% 50%, var(--red), transparent 70%); }

  @keyframes drift1{ 0%,100%{transform:translate(0,0) scale(1);} 50%{transform:translate(4vw,3vh) scale(1.12);} }
  @keyframes drift2{ 0%,100%{transform:translate(0,0) scale(1);} 50%{transform:translate(-3vw,-2vh) scale(1.08);} }
  @keyframes drift3{ 0%,100%{transform:translate(0,0) scale(1);} 50%{transform:translate(2vw,-3vh) scale(1.15);} }

  .stars{
    position:fixed;inset:0;
    background-image:
      radial-gradient(1px 1px at 20% 30%, rgba(255,255,255,0.5), transparent),
      radial-gradient(1px 1px at 70% 20%, rgba(255,255,255,0.4), transparent),
      radial-gradient(1.5px 1.5px at 85% 60%, rgba(255,255,255,0.35), transparent),
      radial-gradient(1px 1px at 40% 80%, rgba(255,255,255,0.4), transparent),
      radial-gradient(1px 1px at 60% 65%, rgba(255,255,255,0.3), transparent),
      radial-gradient(1px 1px at 10% 60%, rgba(255,255,255,0.3), transparent);
    opacity:0.6;
  }

  /* floating particles — signature ambient detail */
  .particles{ position:fixed; inset:0; pointer-events:none; z-index:2; }
  .particle{
    position:absolute;
    bottom:-6%;
    width:var(--ps,4px); height:var(--ps,4px);
    border-radius:50%;
    background:var(--pc, var(--cyan));
    box-shadow:0 0 6px 1px var(--pc, var(--cyan));
    opacity:0;
    animation:rise var(--pd,14s) linear infinite;
    animation-delay:var(--pdelay,0s);
  }
  @keyframes rise{
    0%{ transform:translateY(0) translateX(0); opacity:0; }
    8%{ opacity:0.7; }
    50%{ transform:translateY(-52vh) translateX(var(--px,10px)); }
    92%{ opacity:0.4; }
    100%{ transform:translateY(-100vh) translateX(calc(var(--px,10px) * -1)); opacity:0; }
  }

  /* ---------- card shell ---------- */
  .card-wrap{ position:relative; z-index:10; width:100%; max-width:380px; }
  .card-glow{
    position:absolute; inset:-3px; border-radius:23px;
    background:linear-gradient(120deg, var(--violet), var(--cyan), var(--magenta), var(--violet));
    background-size:300% 300%;
    filter:blur(20px);
    opacity:0.4;
    z-index:-1;
    animation:glowDrift 6s ease-in-out infinite;
    transition:opacity 0.6s ease;
  }
  @keyframes glowDrift{
    0%,100%{ background-position:0% 50%; opacity:0.35; }
    50%{ background-position:100% 50%; opacity:0.55; }
  }
  body.phase-success .card-glow{ background:linear-gradient(120deg, var(--green), var(--cyan), var(--green)); background-size:300% 300%; opacity:0.45; }
  body.phase-error .card-glow{ background:linear-gradient(120deg, var(--red), var(--magenta), var(--red)); background-size:300% 300%; opacity:0.45; }

  .card{
    position:relative;
    width:100%;
    padding:clamp(34px, 8vw, 46px) clamp(24px, 7vw, 36px) clamp(28px, 6vw, 36px);
    background:linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0.03));
    border:1px solid var(--card-border);
    border-radius:20px;
    backdrop-filter:blur(24px) saturate(150%);
    -webkit-backdrop-filter:blur(24px) saturate(150%);
    box-shadow:
      0 30px 70px -20px rgba(0,0,0,0.7),
      inset 0 1px 0 rgba(255,255,255,0.09);
    text-align:center;
    animation:cardIn 0.7s cubic-bezier(.2,.8,.2,1) both, floatCard 6.5s ease-in-out 0.7s infinite;
    overflow:hidden;
  }
  @keyframes cardIn{ from{opacity:0; transform:translateY(14px) scale(0.97);} to{opacity:1; transform:translateY(0) scale(1);} }
  @keyframes floatCard{ 0%,100%{ transform:translateY(0); } 50%{ transform:translateY(-6px); } }

  .card::before{
    content:"";
    position:absolute;
    top:0; left:-70%;
    width:45%; height:100%;
    background:linear-gradient(100deg, transparent, rgba(255,255,255,0.09), transparent);
    transform:skewX(-18deg);
    animation:cardSheen 5.5s ease-in-out infinite;
    pointer-events:none;
    z-index:2;
  }
  @keyframes cardSheen{ 0%{left:-70%;} 35%{left:130%;} 100%{left:130%;} }

  .eyebrow{
    display:inline-flex; align-items:center; gap:6px;
    font-size:clamp(10px, 2.6vw, 11px);
    font-weight:500;
    letter-spacing:1.6px;
    text-transform:uppercase;
    color:var(--text-lo);
    margin-bottom:clamp(18px, 5vw, 22px);
    opacity:0.85;
  }
  .eyebrow::before, .eyebrow::after{
    content:"";
    width:14px; height:1px;
    background:linear-gradient(90deg, transparent, var(--text-lo));
  }
  .eyebrow::after{ background:linear-gradient(90deg, var(--text-lo), transparent); }

  /* ---------- phases ---------- */
  .phase{ display:none; position:relative; z-index:3; }
  .phase.active{ display:block; animation:phaseIn 0.55s cubic-bezier(.2,.8,.2,1) both; }
  @keyframes phaseIn{ from{opacity:0; transform:translateY(8px);} to{opacity:1; transform:translateY(0);} }

  /* ---------- checking phase ---------- */
  .loader{
    position:relative;
    width:clamp(84px, 22vw, 100px);
    height:clamp(84px, 22vw, 100px);
    margin:0 auto clamp(24px, 6vw, 30px);
    display:flex;
    align-items:center;
    justify-content:center;
  }
  /* soft sonar rings breathing outward — no rotation */
  .sonar{
    position:absolute;
    inset:0;
    border-radius:50%;
    border:1.5px solid var(--cyan);
    opacity:0;
    animation:sonar 2.8s cubic-bezier(.25,.7,.4,1) infinite;
  }
  .sonar.s2{ animation-delay:0.7s; border-color:var(--violet); }
  .sonar.s3{ animation-delay:1.4s; border-color:var(--magenta); }
  @keyframes sonar{
    0%{ transform:scale(0.4); opacity:0; }
    12%{ opacity:0.9; }
    100%{ transform:scale(1.15); opacity:0; }
  }

  /* rich mesh-gradient halo, colour drifting in place — no rotation */
  .halo{
    position:absolute;
    inset:6%;
    border-radius:50%;
    background:
      radial-gradient(circle at 30% 28%, rgba(139,92,246,0.95), transparent 55%),
      radial-gradient(circle at 72% 35%, rgba(34,211,238,0.9), transparent 55%),
      radial-gradient(circle at 50% 78%, rgba(236,72,153,0.85), transparent 55%);
    filter:blur(11px) saturate(140%);
    opacity:0.65;
    animation:meshDrift 5.5s ease-in-out infinite;
  }
  @keyframes meshDrift{
    0%,100%{ filter:blur(11px) saturate(140%) hue-rotate(0deg); opacity:0.55; transform:scale(1); }
    50%{ filter:blur(14px) saturate(170%) hue-rotate(30deg); opacity:0.8; transform:scale(1.06); }
  }

  .glass{
    position:absolute;
    inset:14%;
    border-radius:50%;
    background:radial-gradient(circle at 35% 30%, rgba(255,255,255,0.16), rgba(10,10,16,0.6) 60%);
    border:1px solid rgba(255,255,255,0.22);
    backdrop-filter:blur(6px);
    box-shadow:
      inset 0 1px 1px rgba(255,255,255,0.25),
      inset 0 -6px 14px rgba(0,0,0,0.35),
      0 0 26px rgba(139,92,246,0.4);
  }

  /* twinkling sparks inside the orb — opacity/scale only, never rotate */
  .spark{
    position:absolute;
    width:3px; height:3px;
    border-radius:50%;
    background:#fff;
    opacity:0;
    box-shadow:0 0 6px 1.5px rgba(255,255,255,0.9);
    animation:twinkle 2.2s ease-in-out infinite;
  }
  .spark.sp1{ top:22%; left:32%; animation-delay:0.1s; }
  .spark.sp2{ top:66%; left:70%; animation-delay:0.7s; }
  .spark.sp3{ top:30%; left:74%; animation-delay:1.3s; }
  .spark.sp4{ top:72%; left:28%; animation-delay:1.7s; }
  @keyframes twinkle{
    0%,100%{ transform:scale(0.4); opacity:0; }
    50%{ transform:scale(1.4); opacity:1; }
  }

  /* faceted crystal core, breathing */
  .core{
    position:absolute; top:50%; left:50%;
    width:20px; height:20px; margin:-10px 0 0 -10px;
    clip-path:polygon(50% 0%, 90% 25%, 100% 70%, 50% 100%, 0% 70%, 10% 25%);
    background:linear-gradient(160deg, #ffffff 0%, #c9b8ff 22%, var(--violet) 55%, var(--cyan) 100%);
    box-shadow:0 0 22px 7px rgba(139,92,246,0.85), 0 0 40px 12px rgba(34,211,238,0.3);
    animation:breathe 2.4s ease-in-out infinite;
  }
  @keyframes breathe{ 0%,100%{transform:scale(1); filter:brightness(1);} 50%{transform:scale(1.28); filter:brightness(1.25);} }

  .title{
    font-family:'Kanit',sans-serif;
    font-weight:600;
    font-size:clamp(19px, 4.8vw, 21px);
    letter-spacing:0.1px;
    background:linear-gradient(90deg, #c4b5fd, #67e8f9 55%, #f5a8d0);
    -webkit-background-clip:text; background-clip:text; color:transparent;
    background-size:200% 100%;
    animation:shine 4s linear infinite;
    margin-bottom:10px;
  }
  @keyframes shine{ 0%{background-position:0% 50%;} 100%{background-position:200% 50%;} }
  .subtitle{
    font-size:clamp(12.5px, 3.4vw, 13.5px);
    line-height:1.7;
    color:var(--text-lo);
    font-weight:300;
    margin-bottom:clamp(22px, 5.5vw, 28px);
    padding:0 4px;
  }

  .status-line{
    display:flex; align-items:center; justify-content:center; gap:10px;
    width:100%; padding:13px 16px; border-radius:12px;
    border:1px solid rgba(255,255,255,0.1);
    background:linear-gradient(135deg, rgba(139,92,246,0.25), rgba(34,211,238,0.18));
    color:var(--text-hi);
    font-size:clamp(13px, 3.4vw, 14px);
    font-weight:500; letter-spacing:0.2px;
    overflow:hidden; position:relative;
  }
  .status-line .dots span{
    display:inline-block; width:5px; height:5px; margin-left:3px;
    border-radius:50%; background:var(--cyan);
    animation:bounce 1.2s ease-in-out infinite;
  }
  .status-line .dots span:nth-child(2){animation-delay:0.15s;}
  .status-line .dots span:nth-child(3){animation-delay:0.3s;}
  @keyframes bounce{ 0%,80%,100%{transform:translateY(0); opacity:0.5;} 40%{transform:translateY(-4px); opacity:1;} }
  .status-line::before{
    content:""; position:absolute; top:0; left:-60%; width:40%; height:100%;
    background:linear-gradient(120deg, transparent, rgba(255,255,255,0.28), transparent);
    transform:skewX(-20deg);
    animation:sweep 2.6s ease-in-out infinite;
  }
  @keyframes sweep{ 0%{left:-60%;} 60%{left:130%;} 100%{left:130%;} }

  .step-dots{
    display:flex; justify-content:center; gap:6px;
    margin-top:20px;
  }
  .step-dots span{
    width:5px; height:5px; border-radius:50%;
    background:rgba(255,255,255,0.15);
  }
  .step-dots span.on{
    background:var(--cyan);
    box-shadow:0 0 6px 1px var(--cyan);
  }

  .hint{
    margin-top:16px;
    font-size:clamp(10.5px, 2.9vw, 11.5px);
    color:rgba(150,149,172,0.7);
    font-weight:300;
  }

  /* ---------- result phase ---------- */
  @keyframes successPop{ 0%{transform:scale(0.7); opacity:0;} 100%{transform:scale(1); opacity:1;} }
  @keyframes shake{ 0%,100%{transform:translateX(0);} 20%,60%{transform:translateX(-5px);} 40%,80%{transform:translateX(5px);} }
  @keyframes badgeIn{ 0%{transform:translateY(10px) scale(0.9); opacity:0;} 100%{transform:translateY(0) scale(1); opacity:1;} }
  @keyframes shimmer{ 0%{background-position:-200% 0;} 100%{background-position:200% 0;} }
  @keyframes confettiFall{ 0%{transform:translateY(-20px) rotate(0deg); opacity:1;} 100%{transform:translateY(220px) rotate(360deg); opacity:0;} }
  @keyframes drawCircle{ from{ stroke-dashoffset:64; } to{ stroke-dashoffset:0; } }
  @keyframes drawCheck{ from{ stroke-dashoffset:24; } to{ stroke-dashoffset:0; } }

  .confetti{ position:absolute; top:0; left:0; width:100%; height:100%; pointer-events:none; overflow:hidden; z-index:0; }
  .confetti span{ position:absolute; top:-10px; width:6px; height:10px; border-radius:1px; opacity:0.9; animation:confettiFall 2.6s ease-in forwards; }
  #phase-result > *:not(.confetti){ position:relative; z-index:1; }

  .result-icon-wrap{ position:relative; width:clamp(80px, 20vw, 92px); height:clamp(80px, 20vw, 92px); margin:0 auto clamp(20px, 5vw, 24px); }
  .result-ring{
    position:absolute; inset:0; border-radius:50%;
    border:1px solid rgba(255,255,255,0.08);
  }
  .result-ring::before{
    content:""; position:absolute; inset:-6px; border-radius:50%;
    border:1px solid currentColor; opacity:0.25;
  }
  .result-icon{
    position:absolute; inset:8px; border-radius:50%;
    display:flex; align-items:center; justify-content:center;
  }
  .result-icon svg{ width:56%; height:56%; overflow:visible; }
  .draw-circle{ stroke-dasharray:64; stroke-dashoffset:64; animation:drawCircle 0.6s ease-out forwards; }
  .draw-check{ stroke-dasharray:24; stroke-dashoffset:24; animation:drawCheck 0.45s 0.5s ease-out forwards; }
  .result-icon .spinner{
    width:42%; height:42%; border-radius:50%;
    background:radial-gradient(circle, #fff, var(--violet) 70%);
    box-shadow:0 0 16px 4px rgba(139,92,246,0.7);
    animation:breathe 1.1s ease-in-out infinite;
  }
  #phase-result.state-success .result-ring{ color:var(--green); }
  #phase-result.state-success .result-icon{
    background:radial-gradient(circle, rgba(87,242,135,0.22), rgba(87,242,135,0.06));
    box-shadow:0 0 26px rgba(87,242,135,0.3);
    animation:successPop 0.55s cubic-bezier(.2,1.4,.4,1);
  }
  #phase-result.state-success .result-icon svg{ color:var(--green); }
  #phase-result.state-error .result-ring{ color:var(--red); }
  #phase-result.state-error .result-icon{
    background:radial-gradient(circle, rgba(237,66,69,0.22), rgba(237,66,69,0.06));
    box-shadow:0 0 26px rgba(237,66,69,0.25);
    animation:shake 0.5s ease-out;
  }
  #phase-result.state-error .result-icon svg{ color:var(--red); }
  #phase-result.state-processing .result-ring{ color:var(--violet); }
  #phase-result.state-processing .result-icon{
    background:radial-gradient(circle, rgba(139,92,246,0.2), rgba(139,92,246,0.05));
  }

  .result-title{
    font-family:'Kanit',sans-serif;
    font-size:clamp(20px, 5.2vw, 23px);
    font-weight:600;
    margin-bottom:12px;
    letter-spacing:0.1px;
  }
  #phase-result.state-success .result-title{ color:var(--green); }
  #phase-result.state-error .result-title{ color:var(--red); }
  #phase-result.state-processing .result-title{ color:var(--violet); }

  .result-message{
    font-size:clamp(13px, 3.6vw, 14.5px);
    color:var(--text-lo);
    line-height:1.7;
    margin-bottom:clamp(20px, 5.5vw, 24px);
    font-weight:300;
  }

  .user-info{
    display:flex; flex-direction:column; gap:12px;
    background:rgba(0,0,0,0.24); border-radius:14px;
    padding:clamp(12px, 3.2vw, 15px);
    margin-bottom:clamp(16px, 4.5vw, 20px);
    border:1px solid rgba(255,255,255,0.06);
  }
  .user-info-top{
    display:flex; align-items:center; justify-content:center; gap:12px;
  }
  .user-avatar{ width:46px; height:46px; border-radius:50%; border:2px solid var(--green); object-fit:cover; flex-shrink:0; box-shadow:0 0 12px rgba(87,242,135,0.35); }
  .user-details{ text-align:left; min-width:0; display:flex; flex-direction:column; gap:2px; }
  .user-name{ font-weight:600; color:var(--text-hi); font-size:0.95rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
  .user-id{ font-size:0.78rem; color:var(--text-lo); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
  .user-uid{
    display:inline-flex; align-items:center; gap:5px;
    margin-top:3px;
    font-family:'Courier New',ui-monospace,monospace;
    font-size:0.72rem;
    letter-spacing:0.2px;
    color:var(--cyan);
    background:rgba(34,211,238,0.1);
    border:1px solid rgba(34,211,238,0.25);
    border-radius:6px;
    padding:2px 7px;
    width:fit-content;
    max-width:100%;
    white-space:nowrap;
    overflow:hidden;
    text-overflow:ellipsis;
  }
  .user-uid::before{
    content:"";
    width:5px; height:5px; border-radius:50%;
    background:var(--cyan);
    box-shadow:0 0 5px 1px var(--cyan);
    flex-shrink:0;
    animation:breathe 2.4s ease-in-out infinite;
  }

  .role-badge{
    display:flex; align-items:center; justify-content:center; gap:8px;
    padding:10px 20px;
    border-radius:999px;
    background:linear-gradient(90deg, rgba(87,242,135,0.12) 0%, rgba(87,242,135,0.26) 50%, rgba(87,242,135,0.12) 100%);
    background-size:200% 100%;
    border:1px solid var(--green);
    box-shadow:0 0 18px rgba(87,242,135,0.15);
    animation:badgeIn 0.5s ease-out 0.15s both, shimmer 2.5s linear infinite;
    max-width:100%;
  }
  .role-dot{ width:9px; height:9px; border-radius:50%; flex-shrink:0; background:{{ role_color | default('#57F287') }}; box-shadow:0 0 8px {{ role_color | default('#57F287') }}; }
  .role-name{ font-weight:600; font-size:0.9rem; color:var(--text-hi); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }

  .result-btn{
    display:inline-flex; align-items:center; justify-content:center; gap:9px;
    padding:15px 26px;
    font-size:clamp(14px, 3.8vw, 15px);
    font-weight:600; border:none;
    border-radius:12px; cursor:pointer; transition:all 0.25s ease;
    text-decoration:none; width:100%; font-family:'Sarabun',sans-serif;
  }
  .result-btn svg{ width:16px; height:16px; fill:currentColor; }
  .btn-success{
    background:linear-gradient(135deg, var(--green), #3ed875);
    color:#0a1f10; box-shadow:0 6px 22px rgba(87,242,135,0.4);
  }
  .btn-retry{
    background:rgba(255,255,255,0.08); color:var(--text-hi);
    border:1px solid rgba(255,255,255,0.16);
  }
  .result-btn:active{ transform:scale(0.98); }
  @media (hover:hover){
    .result-btn:hover{ transform:translateY(-2px); }
    .btn-success:hover{ box-shadow:0 10px 30px rgba(87,242,135,0.5); }
    .btn-retry:hover{ background:rgba(255,255,255,0.14); }
  }
</style>
</head>
<body class="phase-checking">

  <div class="blob blob-1"></div>
  <div class="blob blob-2"></div>
  <div class="blob blob-3"></div>
  <div class="stars"></div>

  <div class="particles" id="particles"></div>
  <div class="noise"></div>

  <div class="card-wrap">
    <div class="card-glow"></div>
    <div class="card">

      <!-- phase 1: checking -->
      <div class="phase active" id="phase-checking">
        <div class="eyebrow">ระบบยืนยันตัวตน</div>

        <div class="loader">
          <div class="sonar s1"></div>
          <div class="sonar s2"></div>
          <div class="sonar s3"></div>
          <div class="halo"></div>
          <div class="glass"></div>
          <span class="spark sp1"></span>
          <span class="spark sp2"></span>
          <span class="spark sp3"></span>
          <span class="spark sp4"></span>
          <div class="core"></div>
        </div>

        <div class="title">{{ title | default('กำลังตรวจสอบ') }}</div>
        <div class="subtitle">
          {{ subtitle | default('ระบบกำลังตรวจสอบสิทธิ์ของคุณ<br>โปรดรอสักครู่ ระบบใกล้จะเสร็จสมบูรณ์แล้ว') | safe }}
        </div>

        <div class="status-line">
          {{ status_text | default('กำลังตรวจสอบข้อมูล') }}
          <span class="dots"><span></span><span></span><span></span></span>
        </div>

        <div class="step-dots">
          <span class="on"></span><span class="on"></span><span></span><span></span>
        </div>

        <div class="hint">การดำเนินการนี้อาจใช้เวลาสักครู่ กรุณาอย่าปิดหน้าต่างนี้</div>
      </div>

      <!-- phase 2: result -->
      <div class="phase state-{{ result_state | default('success') }}" id="phase-result">
        {% if (result_state | default('success')) == 'success' %}
        <div class="confetti" id="confetti"></div>
        {% endif %}

        <div class="result-icon-wrap">
          <div class="result-ring"></div>
          <div class="result-icon">
            {% if (result_state | default('success')) == 'success' %}
              <svg viewBox="0 0 24 24" class="draw-icon" fill="none" xmlns="http://www.w3.org/2000/svg"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="1.6" class="draw-circle"/><path d="M7.5 12.5l3 3 6-6.5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="draw-check"/></svg>
            {% elif (result_state | default('success')) == 'processing' %}
              <div class="spinner"></div>
            {% else %}
              <svg viewBox="0 0 24 24" class="draw-icon" fill="none" xmlns="http://www.w3.org/2000/svg"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="1.6" class="draw-circle"/><path d="M8.5 8.5l7 7M15.5 8.5l-7 7" stroke="currentColor" stroke-width="2" stroke-linecap="round" class="draw-check"/></svg>
            {% endif %}
          </div>
        </div>

        <h1 class="result-title">{{ result_title | default('ให้ยศสำเร็จ') }}</h1>

        {% if user %}
        <div class="user-info">
          <div class="user-info-top">
            <img src="{{ user.avatar_url }}" alt="Avatar" class="user-avatar">
            <div class="user-details">
              <div class="user-name">{{ user.username }}</div>
              <div class="user-id">@{{ user.global_name or user.username }}</div>
              <div class="user-uid">ID: {{ user.id }}</div>
            </div>
          </div>
          {% if (result_state | default('success')) == 'success' and role_name %}
          <div class="role-badge">
            <span class="role-dot"></span>
            <span class="role-name">{{ role_name }}</span>
          </div>
          {% endif %}
        </div>
        {% endif %}

        <p class="result-message">{{ result_message | default('คุณได้รับยศเรียบร้อยแล้ว ยินดีต้อนรับเข้าสู่เซิร์ฟเวอร์') }}</p>

        <a href="{{ button_url | default('https://discord.com/app') }}"
           class="result-btn {{ 'btn-success' if (result_state | default('success')) == 'success' else 'btn-retry' }}"
           {% if (result_state | default('success')) == 'success' %}onclick="openDiscord(event)"{% endif %}>
          {{ button_text | default('กลับไปที่ Discord') }}
        </a>
      </div>

    </div>
  </div>

  <script>
    function openDiscord(event) {
      event.preventDefault();
      const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
      const discordAppUrl = 'discord://';
      const discordWebUrl = 'https://discord.com/app';
      if (isMobile) {
        window.location.href = discordAppUrl;
        setTimeout(() => { window.location.href = discordWebUrl; }, 1500);
      } else {
        window.location.href = discordWebUrl;
      }
    }

    function spawnConfetti() {
      const colors = ['#57F287', '#8b5cf6', '#22d3ee', '#ffffff'];
      const container = document.getElementById('confetti');
      if (!container) return;
      for (let i = 0; i < 26; i++) {
        const piece = document.createElement('span');
        piece.style.left = Math.random() * 100 + '%';
        piece.style.background = colors[Math.floor(Math.random() * colors.length)];
        piece.style.animationDelay = (Math.random() * 0.4) + 's';
        piece.style.animationDuration = (2 + Math.random() * 0.8) + 's';
        container.appendChild(piece);
      }
    }

    // ambient floating particles
    (function spawnParticles() {
      const wrap = document.getElementById('particles');
      const colors = ['#8b5cf6', '#22d3ee', '#ec4899'];
      const count = 18;
      for (let i = 0; i < count; i++) {
        const p = document.createElement('span');
        p.className = 'particle';
        p.style.left = Math.random() * 100 + '%';
        p.style.setProperty('--ps', (2 + Math.random() * 3) + 'px');
        p.style.setProperty('--pc', colors[Math.floor(Math.random() * colors.length)]);
        p.style.setProperty('--pd', (10 + Math.random() * 10) + 's');
        p.style.setProperty('--pdelay', (Math.random() * -14) + 's');
        p.style.setProperty('--px', (Math.random() * 60 - 30) + 'px');
        wrap.appendChild(p);
      }
    })();

    // transition from "checking" to the result phase after the check completes
    const CHECK_DELAY_MS = {{ check_delay_ms | default(2500) }};
    const RESULT_STATE = "{{ result_state | default('success') }}";

    setTimeout(function () {
      const checking = document.getElementById('phase-checking');
      const result = document.getElementById('phase-result');
      checking.classList.remove('active');
      result.classList.add('active');
      document.body.classList.remove('phase-checking');
      document.body.classList.add('phase-' + RESULT_STATE);
      if (RESULT_STATE === 'success') spawnConfetti();
    }, CHECK_DELAY_MS);
  </script>

</body>
</html>
"""

app = Flask(__name__)


def get_role_name(guild_id, role_id):
    """ดึงชื่อยศจริงจาก Discord API เพื่อเอาไปโชว์ใน role-badge"""
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
        subtitle="กำลังนำคุณไปหน้ายืนยันตัวตนผ่าน Discord<br>โปรดรอสักครู่",
        result_state="processing",
        result_title="เตรียมยืนยันตัวตน",
        result_message="กรุณากดยืนยันตัวตนผ่านบัญชี Discord ของคุณ เพื่อรับสิทธิ์เข้าถึงห้องต่างๆ ภายในเซิร์ฟเวอร์",
        button_url=discord_login_url,
        button_text="🚀 เข้าสู่ระบบผ่าน Discord",
        user=None,
    )


@app.route("/callback", strict_slashes=False)
def callback():
    code = request.args.get("code")
    error = request.args.get("error")

    if error:
        return render_template_string(
            HTML_TEMPLATE,
            title="เกิดข้อผิดพลาด",
            result_state="error",
            result_title="เกิดข้อผิดพลาด",
            result_message=f"Discord ปฏิเสธการเข้าสู่ระบบ: {error}",
            button_url="/",
            button_text="กลับไปหน้าหลัก",
            user=None,
        )

    if not code:
        return render_template_string(
            HTML_TEMPLATE,
            title="เกิดข้อผิดพลาด",
            result_state="error",
            result_title="เกิดข้อผิดพลาด",
            result_message="ไม่พบรหัสยืนยันตัวตน กรุณาลองใหม่อีกครั้ง",
            button_url="/",
            button_text="กลับไปหน้าหลัก",
            user=None,
        )

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
        return render_template_string(
            HTML_TEMPLATE,
            title="เกิดข้อผิดพลาด",
            result_state="error",
            result_title="เกิดข้อผิดพลาด",
            result_message="เกิดข้อผิดพลาดในการดึง Token จาก Discord",
            button_url="/",
            button_text="กลับไปหน้าหลัก",
            user=None,
        )

    user_headers = {"Authorization": f"Bearer {access_token}"}
    user_data = requests.get("https://discord.com/api/users/@me", headers=user_headers).json()
    user_id = user_data.get("id")
    username = user_data.get("username")
    global_name = user_data.get("global_name", username)
    avatar_id = user_data.get("avatar")

    if avatar_id:
        avatar_url = f"https://cdn.discordapp.com/avatars/{user_id}/{avatar_id}.png"
    else:
        avatar_url = "https://cdn.discordapp.com/embed/avatars/0.png"

    user_info = {
        "id": user_id,
        "username": username,
        "global_name": global_name,
        "avatar_url": avatar_url,
    }

    bot_headers = {"Authorization": f"Bot {BOT_TOKEN}"}
    add_role_url = f"https://discord.com/api/v10/guilds/{GUILD_ID}/members/{user_id}/roles/{ROLE_ID}"
    r = requests.put(add_role_url, headers=bot_headers)

    if r.status_code in [204, 200]:
        return render_template_string(
            HTML_TEMPLATE,
            title="ยืนยันตัวตนสำเร็จ",
            result_state="success",
            result_title="ให้ยศสำเร็จ",
            result_message="ระบบได้ทำการเพิ่มยศให้คุณเรียบร้อยแล้ว สามารถกลับเข้าสู่ Discord ได้เลย",
            button_url="https://discord.com/app",
            button_text="กลับไปที่ Discord",
            user=user_info,
            role_name=get_role_name(GUILD_ID, ROLE_ID) or "Verified",
        )
    else:
        return render_template_string(
            HTML_TEMPLATE,
            title="เกิดข้อผิดพลาด",
            result_state="error",
            result_title="เกิดข้อผิดพลาด",
            result_message="ไม่สามารถเพิ่มยศได้ (บอทอาจจะยศต่ำกว่ายศที่ต้องการให้ หรือไม่ได้อยู่ในกิลด์)",
            button_url="/",
            button_text="ลองใหม่อีกครั้ง",
            user=user_info,
        )


def run_web():
    app.run(host="0.0.0.0", port=5000)


class VerifyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)
        
        # เพิ่มปุ่มยืนยันตัวตนถาวร (Persistent View)
        self.add_view(VerifyView())

    async def setup_hook(self):
        await self.tree.sync()
        print(f"Logged in as {self.user} (ID: {self.user.id})")

    async def on_ready(self):
        print(f"Bot พร้อมใช้งานแล้ว: {self.user}")

class VerifyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(
            discord.ui.Button(
                label="ยืนยันตัวตนเข้าดิส",
                url="https://discord.com/oauth2/authorize?client_id=1292567654405771334&response_type=code&redirect_uri=https%3A%2F%2Fsssssssssssssssssssss-5l9s.onrender.com%2Fcallback&scope=identify+guilds.join",
                style=discord.ButtonStyle.link,
                emoji="<a:emoji_125:1283873278129213471>",
            )
        )

bot = VerifyBot()

if __name__ == "__main__":
    web_thread = threading.Thread(target=run_web)
    web_thread.daemon = True
    web_thread.start()

    bot.run(BOT_TOKEN)
