import discord 
from discord.ext import commands
import logging
from dotenv import load_dotenv
import yt_dlp
import asyncio
import os
import re
import requests


load_dotenv()

token = os.getenv('DISCORD_TOKEN')
rito_token = os.getenv('RIOT_API_KEY')

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

gaymer = "GAYMER"
last_played = {}  # {guild_id: (url, title)}
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    print('------')
    #bot.loop.create_task(clear_log_periodic())

@bot.event
async def on_member_join(member):
    await member.send(f'Hello, {member.name}!')

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if "MitzuPitzu" in message.content.lower():
        await message.channel.send(f'Ce-ti trebe {message.author.mention}?')

    if "miau" in message.content.lower():
        await message.channel.send(f'Miau fa!')

    if "ovidiu" in message.content.lower():
        await message.channel.send(f'Ce-i cu ovi iar?')

    if "pula" in message.content.lower():
        await message.channel.send(f'Ia zi papusa, vrei putina pl?')

    if "sal" in message.content.lower():
        await message.channel.send(f'Sal, boss {message.author.mention}! Ce mai zici?')

    if "papa" in message.content.lower():
        await message.channel.send(f'Pleci ? Mă părăsești!')

    if "lol" in message.content.lower():
        await message.channel.send(f'Iar 0/10 yasuo top?')

    if "esti prost" in message.content.lower():
        await message.channel.send(f'S-ar putea... da măcar nu-s singurul 😎 - mai e si ma-t...')

    if "pisi" in message.content.lower():
        await message.channel.send(f'Miau miau, vino să-ți dau un pula!')

    if "mancare" in message.content.lower():
        await message.channel.send(f'Ce mâncare? N-ai mancat suficienta bataie?')

    if "somn" in message.content.lower():
        await message.channel.send(f'Noapte bună și vise cu pixeli!')

    await bot.process_commands(message)


#functie de stergere automata a discord.log = economisire de spatiu

async def clear_log_periodic():
    while True:
        try:
            with open("discord.log", "w", encoding="utf-8") as f:
                f.write("")
            print("[LOG CLEANER] Logul a fost golit.")
        except Exception as e:
            print(f"[LOG CLEANER] Eroare la ștergerea logului: {e}")
        await asyncio.sleep(300)




# !hello 
@bot.command()
async def hello(ctx):
    await ctx.send(f"Cine drq vorbeste cu tine {ctx.author.mention}!")

@bot.command()
async def role(ctx):
    role = discord.utils.get(ctx.guild.roles, name=gaymer)
    if role:
        await ctx.author.add_roles(role)
        await ctx.send(f'{ctx.author.mention} a fost adaugat la rolul {gaymer}!')
    else:
        await ctx.send(f'Rolul {gaymer} nu a fost gasit!')



song_queue = {}  # Coada de melodii per server
last_played = {}  # Ultima melodie redată

# Join voice channel
async def join_vc(ctx):
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        try:
            print(f"[DEBUG] Încearcă să se conecteze la canalul: {channel.name}")
            vc = await channel.connect()
            print(f"[DEBUG] S-a conectat la canalul: {channel.name}")
            return vc
        except Exception as e:
            await ctx.send(f"❌ Eroare la conectare în voice: {e}")
            print(f"[ERROR CONNECT]: {e}")
            return None
    else:
        await ctx.send("❌ Trebuie să fii într-un voice channel mai întâi.")
        return None

# Comanda !play
@bot.command()
async def play(ctx, *, query: str):
    print(f"[DEBUG] Comanda !play primită cu: {query}")
    if not ctx.author.voice:
        await ctx.send("Trebuie să fii într-un voice channel.")
        return

    vc = ctx.voice_client or await join_vc(ctx)
    if not vc:
        print("[DEBUG] VoiceClient este None")
        return



    # Setări yt_dlp pentru căutare YouTube
    ydl_opts = {
    'format': 'bestaudio[ext=webm]/bestaudio/best',
    'quiet': True,
    'noplaylist': True,
    'default_search': 'auto',       # caută singur pe YouTube
    'source_address': '0.0.0.0',    # previne probleme de rețea
    'cachedir': False               # evită cache care poate bloca
}

    if not query.startswith("http"):
        query = f"ytsearch1:{query}"



    try:
       with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = await asyncio.to_thread(ydl.extract_info, query, download=False)
    
        # Verifică dacă info e dintr-un search sau link direct
        if 'entries' in info and isinstance(info['entries'], list):
            if not info['entries']:
                await ctx.send("❌ Nu am găsit rezultate pentru căutare.")
                return
            info = info['entries'][0]



        stream_url = info.get('url')
        title = info.get('title', 'Unknown')
        if not stream_url:
            await ctx.send("❌ Nu am găsit un link valid pentru redare.")
            return

        last_played[ctx.guild.id] = (stream_url, title)

    except Exception as e:
        await ctx.send(f"❌ Eroare la extragerea melodiei: {e}")
        return

    # Coadă per server
    guild_id = ctx.guild.id
    if guild_id not in song_queue:
        song_queue[guild_id] = []

    song_queue[guild_id].append((title, stream_url))
    await ctx.send(f"✅ Adăugat în coadă: **{title}**")

    # Dacă nu e deja ceva care se redă, începe redarea
    if not vc.is_playing() and not vc.is_paused():
        await play_from_queue(ctx, vc)
# 🔧 Funcție pentru inițializare audio
def create_source(url):
    print(f"[DEBUG FFMPEG] Pornesc redare din: {url}")
    return discord.FFmpegPCMAudio(
        url,
        before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
        options="-vn"
    )

# 🔁 Funcție internă care redă din coadă
async def play_from_queue(ctx, vc):
    guild_id = ctx.guild.id

    if not song_queue.get(guild_id):
        await ctx.send("📭 Coada s-a terminat.")

        # 🔍 Verificăm dacă mai e cineva în canal (în afară de bot)
        members = [m for m in vc.channel.members if not m.bot]
        if len(members) == 0:
            await ctx.send("👋")
            if vc.is_connected():
                await vc.disconnect()
        else:
            await ctx.send("👂.")
        return

    title, stream_url = song_queue[guild_id].pop(0)

    def after_playing(error):
        if error:
            print(f"[After Play Error] {error}")
        fut = asyncio.run_coroutine_threadsafe(play_from_queue(ctx, vc), bot.loop)
        try:
            fut.result()
        except Exception as e:
            print(f"[Queue Error] {e}")

    try:
        source = create_source(stream_url)
        await asyncio.sleep(1)  # 🕐 Așteaptă o secundă pentru ca conexiunea voice să fie stabilă
        vc.play(source, after=after_playing)

        await ctx.send(f"🎶 Se redă: **{title}**")
        print("[DEBUG] play() executat cu succes")
    except Exception as e:
        await ctx.send(f"❌ Nu am putut reda piesa: **{title}**\n📛 Eroare: `{e}`")
        print(f"[ERROR @play_from_queue]: {e}")
        print(f"[DEBUG STREAM URL]: {stream_url}")




@bot.command()
async def queue(ctx):
    guild_id = ctx.guild.id
    queue = song_queue.get(guild_id)

    if not queue or len(queue) == 0:
        await ctx.send("📭 Coada este goală.")
        return

    msg = "\n".join([f"{i+1}. {title}" for i, (title, _) in enumerate(queue)])
    await ctx.send(f"📜 **Coada curentă:**\n{msg}")


@bot.command()
async def skip(ctx):
    vc = ctx.voice_client
    if vc and vc.is_playing():
        vc.stop()  # declanșează funcția `after=` care redă următoarea
        await asyncio.sleep(1)
        await ctx.send("⏭️ Am sărit la următoarea piesă.")
    else:
        await ctx.send("❌ Nu e nimic de sărit.")


@bot.command()
async def clear(ctx):
    guild_id = ctx.guild.id
    song_queue[guild_id] = []
    await ctx.send("🧹 Coada a fost curățată.")



@bot.command()
async def pause(ctx):
    vc = ctx.voice_client
    if vc and vc.is_playing():
        vc.pause()
        await ctx.send("⏸️ Muzica a fost pusă pe pauză.")
    else:
        await ctx.send("❌ Nu se redă nimic acum.")


@bot.command()
async def resume(ctx):
    vc = ctx.voice_client
    if vc and vc.is_paused():
        vc.resume()
        await ctx.send("▶️ Muzica a fost reluată.")
    else:
        await ctx.send("❌ Nu există muzică pusă pe pauză.")

@bot.command()
async def stop(ctx):
    vc = ctx.voice_client
    if vc and (vc.is_playing() or vc.is_paused()):
        vc.stop()
        await asyncio.sleep(1)
        await ctx.send("⏹️ Muzica a fost oprită.")
    else:
        await ctx.send("❌ Nu este nimic de oprit.")


@bot.command()
async def leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("👋 Botul a părăsit canalul vocal.")
    else:
        await ctx.send("❌ Nu sunt într-un canal vocal.")

@bot.command()
async def replay(ctx):
    vc = ctx.voice_client or await join_vc(ctx)
    if not vc:
        return

    if ctx.guild.id not in last_played:
        await ctx.send("❌ Nu am ce să redau. Dă mai întâi `!play`.")
        return

    url, title = last_played[ctx.guild.id]

    if vc.is_playing():
        vc.stop()
        await asyncio.sleep(1)

    source = discord.FFmpegPCMAudio(
    url,
    before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    options="-vn"  # dezactivează video (care poate cauza eroarea)
)

    vc.play(source)
    await ctx.send(f"🔁 Se redă din nou: **{title}**")




import json

def load_champion_names():
    url = "http://ddragon.leagueoflegends.com/cdn/14.8.1/data/en_US/champion.json"
    response = requests.get(url)
    data = response.json()["data"]

    id_to_name = {}
    for champ_name, champ_info in data.items():
        id_to_name[int(champ_info["key"])] = champ_info["name"]
    
    return id_to_name



from datetime import datetime

def convert_timestamp(ms):
    dt = datetime.fromtimestamp(ms / 1000.0)
    return dt.strftime("%Y-%m-%d %H:%M")



@bot.command()
async def stats(ctx, *, input_text: str):
    try:
        name, tag = input_text.split('#')
    except ValueError:
        await ctx.send("❌ Format invalid. Folosește: `Nume#TAG` (ex: MitzuPitzu#EUNE)")
        return

    riot_headers = {"X-Riot-Token": rito_token}
    url = f"https://europe.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{name}/{tag}"
    
    response = requests.get(url, headers=riot_headers)
 
    if response.status_code != 200:
        await ctx.send(f"❌ Nu am putut găsi invocatorul: `{name}#{tag}`\nCod răspuns: {response.status_code}")
        return

    data = response.json()
    puuid = data['puuid']


    url_champ= f"https://eun1.api.riotgames.com/lol/champion-mastery/v4/champion-masteries/by-puuid/{puuid}"
    response_champ = requests.get(url_champ, headers=riot_headers)
    

    if response_champ.status_code != 200:
        await ctx.send(f"❌ Nu am putut găsi invocatorul: `{name}#{tag}`\nCod răspuns: {response_champ.status_code}")
        return
    
    data_champ = response_champ.json()

    champion_dict = load_champion_names()

    top_champs = ""
    for champ in data_champ[:10]:
        championId = champ['championId']
        champ_name = champion_dict.get(championId, f"ID:{championId}")
        championLevel = champ['championLevel']
        championPoints = champ['championPoints']
        championlastPlayTime = champ['lastPlayTime']
        last_played = convert_timestamp(championlastPlayTime)

        top_champs += f"🔸 {champ_name} | Nivel {championLevel} | {championPoints} puncte | Ultimul joc: {last_played}\n"





    summoner_url = f"https://eun1.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
    summoner_resp = requests.get(summoner_url, headers=riot_headers)
    if summoner_resp.status_code != 200:
        await ctx.send("❌ Eroare la obținerea profilului.")
        return

    summoner_data = summoner_resp.json()
    summoner_id = summoner_data['id']
    summoner_level = summoner_data['summonerLevel']

    
    rank_url = f"https://eun1.api.riotgames.com/lol/league/v4/entries/by-summoner/{summoner_id}"
    rank_resp = requests.get(rank_url, headers=riot_headers)
    rank_text = "❌ Nicio informație de ranked."
    if rank_resp.status_code == 200:
        ranks = rank_resp.json()
        lines = []
        for entry in ranks:
            q = "Solo" if entry['queueType'] == "RANKED_SOLO_5x5" else "Flex"
            winrate = round((entry['wins'] / (entry['wins'] + entry['losses'])) * 100)
            games_played = entry['wins'] + entry['losses']
            lines.append(f"🏆 **{q}**: {entry['tier']} {entry['rank']} ({entry['leaguePoints']} LP) | {entry['wins']}W/{entry['losses']}L | WR: {winrate}% din {games_played} meciuri! ")
            
        if lines:
            rank_text = "\n".join(lines)

    
    live_url = f"https://eun1.api.riotgames.com/lol/spectator/v4/active-games/by-summoner/{summoner_id}"
    live_resp = requests.get(live_url, headers=riot_headers)

    live_status = "🔴 Nu este într-un meci acum."
    if live_resp.status_code == 200:
        live_data = live_resp.json()
        # Găsește participantul nostru
        for participant in live_data['participants']:
            if participant['summonerName'].lower() == name.lower():
                champ_id = participant['championId']
                champ_name = champion_dict.get(champ_id, f"ID:{champ_id}")
                game_mode = live_data.get('gameMode', 'Unknown')
                live_status = f"🟢 Este într-un meci acum ({game_mode}) cu **{champ_name}**!"
                break

# Mesaj  
    await ctx.send(
        f"📛 **{name}#{tag}** (Lvl {summoner_level})\n\n"
        f"📈 **Rank:**\n{rank_text}\n\n"
        f"{live_status}\n\n"
        f"🎯 **Top 10 campioni:**\n{top_champs}"
    )







@bot.command()
async def test_play(ctx):
    if not ctx.author.voice:
        await ctx.send("🔇 Trebuie să fii într-un canal vocal.")
        return

    channel = ctx.author.voice.channel
    await ctx.send(f"🔌 Mă conectez la: {channel.name}")

    try:
        vc = await channel.connect()
        await asyncio.sleep(1)

        if not vc or not vc.is_connected():
            await ctx.send("❌ Voice client NU este conectat (is_connected = False).")
            return

        await ctx.send("✅ Sunt conectat. Încerc să redau un sunet de test...")

        test_url = "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3"
        source = discord.FFmpegPCMAudio(test_url)
        vc.play(source)

        await ctx.send("🎵 Se redă sunetul. Aștept 10 secunde înainte să ies...")
        await asyncio.sleep(10)

        await vc.disconnect()
        await ctx.send("👋 Am ieșit din voice.")

    except Exception as e:
        await ctx.send(f"❌ Eroare: {e}")

@bot.command()
async def test_connect(ctx):
    if not ctx.author.voice:
        await ctx.send("🔇 Trebuie să fii într-un canal vocal.")
        return

    channel = ctx.author.voice.channel
    await ctx.send(f"🔌 Încerc să mă conectez la: {channel.name}")

    try:
        vc = await channel.connect()
        await asyncio.sleep(1)

        if vc.is_connected():
            await ctx.send("✅ M-am conectat cu succes! Stau 5 secunde...")
            await asyncio.sleep(5)
            await vc.disconnect()
            await ctx.send("👋 M-am deconectat.")
        else:
            await ctx.send("❌ M-am conectat dar `is_connected()` e False.")

    except Exception as e:
        await ctx.send(f"❌ Eroare la conectare: `{e}`")





bot.run(token, log_handler=handler, log_level=logging.DEBUG)
