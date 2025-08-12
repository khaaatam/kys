import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import yt_dlp
import asyncio

# Muat variabel dari file .env
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Siapkan bot dengan semua intent dan prefix perintah '!'
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

# Dictionary untuk menyimpan status & antrian per server (guild)
server_settings = {}

@bot.event
async def on_ready():
    """Event yang dijalankan saat bot berhasil terhubung."""
    print(f'🤖 {bot.user.name} sudah siap beraksi!')
    print('-----------------------------------------')

def check_server_settings(guild_id):
    """Memastikan setiap server punya entri pengaturan sendiri."""
    if guild_id not in server_settings:
        server_settings[guild_id] = {
            'loop': False,
            'last_song': None
        }

@bot.command(name='play', help='Memutar musik dari YouTube')
async def play(ctx, *, search: str):
    """Perintah untuk mencari dan memutar musik dari YouTube."""
    guild_id = ctx.guild.id
    check_server_settings(guild_id)

    if not ctx.author.voice:
        await ctx.send(" Kamu harus berada di voice channel untuk memutar musik!")
        return

    voice_channel = ctx.author.voice.channel

    if not ctx.voice_client:
        await voice_channel.connect()
    
    YDL_OPTIONS = {'format': 'bestaudio/best', 'noplaylist': 'True'}
    FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}

    query = search
    if not (search.startswith('http://') or search.startswith('https://')):
        query = f"ytsearch:{search}"

    await ctx.send(f"🎵 Memproses `{search}`...")
    with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
        try:
            info = ydl.extract_info(query, download=False)
            if 'entries' in info:
                info = info['entries'][0]

        except Exception as e:
            await ctx.send("Gagal memproses permintaan. Coba kata kunci atau URL lain.")
            print(f"Error saat extract_info: {e}")
            return
            
    server_settings[guild_id]['last_song'] = search
    
    # ================== PERUBAHAN UNTUK KECEPATAN ADA DI SINI ==================
    
    # Kita tidak lagi menggunakan 'from_probe' yang lambat untuk video panjang.
    # Perhatikan bahwa 'await' juga dihilangkan dari baris ini.
    url = info['url']
    source = discord.FFmpegOpusAudio(url, **FFMPEG_OPTIONS)
    
    # =========================================================================

    def after_playing(error):
        if error:
            print(f'Terjadi eror saat memutar: {error}')
        
        if server_settings[guild_id].get('loop', False):
            bot.loop.create_task(play(ctx, search=server_settings[guild_id]['last_song']))

    ctx.voice_client.play(source, after=after_playing)
    await ctx.send(f"▶️ Sekarang memutar: **{info['title']}**")
    
@bot.command(name='loop', help='Mengulang lagu yang sedang diputar')
async def loop(ctx):
    """Toggle mode perulangan untuk server ini."""
    guild_id = ctx.guild.id
    check_server_settings(guild_id)

    # Balik status loop (jika True jadi False, jika False jadi True)
    server_settings[guild_id]['loop'] = not server_settings[guild_id]['loop']

    if server_settings[guild_id]['loop']:
        await ctx.send("🔁 Mode perulangan **diaktifkan**.")
    else:
        await ctx.send("🔁 Mode perulangan **dinonaktifkan**.")

@bot.command(name='stop', help='Menghentikan musik dan keluar dari voice channel')
async def stop(ctx):
    """Perintah untuk menghentikan musik dan keluar."""
    guild_id = ctx.guild.id
    check_server_settings(guild_id)
    
    if ctx.voice_client:
        # Matikan loop saat bot dihentikan
        server_settings[guild_id]['loop'] = False
        await ctx.voice_client.disconnect()
        await ctx.send("👋 Sampai jumpa!")
    else:
        await ctx.send("Aku tidak sedang berada di voice channel.")

# Jalankan bot dengan token Anda
bot.run(TOKEN)