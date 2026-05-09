import discord
from discord import app_commands
from discord.ext import tasks
import json
import random
import os
from datetime import datetime
import pytz

# ========== الاعدادات ==========
TOKEN = os.getenv("TOKEN")  # حاط التوكن في Railway Variables
CONFIG_FILE = "config.json"
TZ = pytz.timezone('Asia/Riyadh')  # توقيت السعودية

intents = discord.Intents.default()
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

# ========== تحميل الكونفيق ==========
def load_config():
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

config = load_config()

# ========== زر التفاعل ==========
class ReactButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="تفاعل ❤️", style=discord.ButtonStyle.green, custom_id="react_button")
    async def react(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = load_config()
        user_id = str(interaction.user.id)
        
        if user_id not in config["احصائيات"]["التفاعلات"]:
            config["احصائيات"]["التفاعلات"][user_id] = 0
        config["احصائيات"]["التفاعلات"][user_id] += 1
        save_config(config)
        
        await interaction.response.send_message("تم تسجيل تفاعلك ❤️", ephemeral=True)

# ========== دالة الارسال ==========
async def send_message(قسم_اسم):
    config = load_config()
    if قسم_اسم not in config["الاقسام"]:
        return
    
    data = config["الاقسام"][قسم_اسم]
    channel = bot.get_channel(data["channel_id"])
    if not channel:
        print(f"الروم {data['channel_id']} غير موجود")
        return
    
    try:
        with open(data["file"], "r", encoding="utf-8") as f:
            messages = [line.strip() for line in f if line.strip()]
        
        if not messages:
            print(f"الملف {data['file']} فاضي")
            return
        
        message = random.choice(messages)
        embed = discord.Embed(
            title=data["title"],
            description=message,
            color=int(data["color"].replace("#", ""), 16)
        )
        
        view = ReactButton() if config["تفعيل_زر_التفاعل"] else None
        await channel.send(embed=embed, view=view)
        
        # تحديث الاحصائيات
        if قسم_اسم not in config["احصائيات"]["اجمالي_المرسل"]:
            config["احصائيات"]["اجمالي_المرسل"][قسم_اسم] = 0
        config["احصائيات"]["اجمالي_المرسل"][قسم_اسم] += 1
        save_config(config)
        
    except Exception as e:
        print(f"خطأ في ارسال {قسم_اسم}: {e}")

# ========== التاسك اليومي ==========
@tasks.loop(minutes=1)
async def daily_sender():
    now = datetime.now(TZ).strftime("%H:%M")
    config = load_config()
    
    for قسم_اسم, data in config["الاقسام"].items():
        if data["time"] == now:
            await send_message(قسم_اسم)

# ========== الاوامر ==========
@tree.command(name="معاينة", description="معاينة رسالة عشوائية من قسم معين")
@app_commands.describe(قسم="اسم القسم")
async def معاينة(interaction: discord.Interaction, قسم: str):
    config = load_config()
    
    if interaction.user.id not in config["ايدي_الادمن"]:
        return await interaction.response.send_message("ما عندك صلاحية", ephemeral=True)
    
    if قسم not in config["الاقسام"]:
        return await interaction.response.send_message(f"القسم {قسم} غير موجود", ephemeral=True)
    
    await interaction.response.defer(ephemeral=True)
    
    data = config["الاقسام"][قسم]
    
    try:
        with open(data["file"], "r", encoding="utf-8") as f:
            messages = [line.strip() for line in f if line.strip()]
        
        if not messages:
            return await interaction.followup.send("الملف فاضي", ephemeral=True)
        
        message = random.choice(messages)
        embed = discord.Embed(
            title=data["title"],
            description=message,
            color=int(data["color"].replace("#", ""), 16)
        )
        
        view = ReactButton() if config["تفعيل_زر_التفاعل"] else None
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        
    except Exception as e:
        await interaction.followup.send(f"خطأ: {e}", ephemeral=True)

@tree.command(name="ارسل_الان", description="ارسل رسالة من قسم معين الحين")
@app_commands.describe(قسم="اسم القسم اللي تبي ترسل منه")
async def ارسل_الان(interaction: discord.Interaction, قسم: str):
    config = load_config()
    
    if interaction.user.id not in config["ايدي_الادمن"]:
        return await interaction.response.send_message("ما عندك صلاحية", ephemeral=True)
    
    if قسم not in config["الاقسام"]:
        return await interaction.response.send_message(f"القسم {قسم} غير موجود", ephemeral=True)
    
    await interaction.response.defer(ephemeral=True)
    await send_message(قسم)
    await interaction.followup.send(f"تم ارسال رسالة من قسم {قسم} ✅", ephemeral=True)

# ========== تشغيل البوت ==========
@bot.event
async def on_ready():
    await tree.sync()
    print(f"تم تسجيل الدخول باسم {bot.user}")
    daily_sender.start()

bot.run(TOKEN)
