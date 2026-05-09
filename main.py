import discord
from discord import app_commands
from discord.ext import tasks
import json
import random
import os
from collections import deque # منع التكرار
from datetime import datetime
import pytz

# ========== الاعدادات ==========
TOKEN = os.getenv("TOKEN")
CONFIG_FILE = "config.json"
TZ = pytz.timezone('Asia/Riyadh')
IMAGE_HISTORY_LIMIT = 180 # منع التكرار: عدد الصور قبل ما نسمح بالتكرار

intents = discord.Intents.default()
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

# ========== ذاكرة البوت ==========
CACHE = {
    "رسائل": {},
    "صور": {},
    "تاريخ_الصور": {} # منع التكرار: نخزن هنا آخر الصور المرسلة
}

# ========== تحميل الكونفيق ==========
def load_config():
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

config = load_config()

# ========== تحميل الملفات للذاكرة ==========
def reload_cache():
    global CACHE
    CACHE = {"رسائل": {}, "صور": {}, "تاريخ_الصور": {}}
    config = load_config()

    for قسم_اسم, data in config["الاقسام"].items():
        # تحميل الرسائل
        try:
            with open(data["file"], "r", encoding="utf-8") as f:
                CACHE["رسائل"][قسم_اسم] = [line.strip() for line in f if line.strip()]
        except:
            CACHE["رسائل"][قسم_اسم] = []
            print(f"ملف {data['file']} غير موجود")

        # تحميل الصور
        try:
            with open(data["images_file"], "r", encoding="utf-8") as f:
                CACHE["صور"][قسم_اسم] = [line.strip() for line in f if line.strip()]
        except:
            CACHE["صور"][قسم_اسم] = []
            print(f"ملف {data['images_file']} غير موجود")
        
        # منع التكرار: ننشئ قائمة تاريخ فارغة لكل قسم
        CACHE["تاريخ_الصور"][قسم_اسم] = deque(maxlen=IMAGE_HISTORY_LIMIT)

    return CACHE

# نحملها أول ما يشتغل البوت
reload_cache()

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

# ========== دالة اختيار صورة بدون تكرار ==========
def get_unique_image(قسم_اسم):
    صور_القسم = CACHE["صور"].get(قسم_اسم, [])
    if not صور_القسم:
        return "https://images.unsplash.com/photo-1564769625392-651b9e1e2a8a?w=1200&h=600&fit=crop"

    تاريخ_القسم = CACHE["تاريخ_الصور"][قسم_اسم]
    
    # الصور المتاحة = كل الصور - الصور اللي انرسلت آخر 180 مرة
    صور_متاحة = [صورة for صورة in صور_القسم if صورة not in تاريخ_القسم]

    # لو كل الصور انرسلت وخلصت، نفضي التاريخ ونبدأ من جديد
    if not صور_متاحة:
        صور_متاحة = صور_القسم
        تاريخ_القسم.clear()

    صورة_مختارة = random.choice(صور_متاحة)
    تاريخ_القسم.append(صورة_مختارة) # نضيفها للتاريخ
    return صورة_مختارة

# ========== دالة بناء الامبد ==========
def build_embed(قسم_اسم, data, message):
    embed = discord.Embed(
        title=f"**{data['title']}**",
        description=f"> {message}",
        color=int(data["color"].replace("#", ""), 16),
        timestamp=datetime.now(TZ)
    )

    # منع التكرار: نستخدم الدالة الجديدة
    embed.set_image(url=get_unique_image(قسم_اسم))

    embed.set_footer(
        text="رسائل تلقائية • بوت الخواطر",
        icon_url=bot.user.avatar.url if bot.user.avatar else None
    )
    embed.add_field(name="\u200b", value="▬▬▬", inline=False)
    return embed

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

    رسائل_القسم = CACHE["رسائل"].get(قسم_اسم, [])
    if not رسائل_القسم:
        print(f"لا توجد رسائل في قسم {قسم_اسم}")
        return

    message = random.choice(رسائل_القسم)
    embed = build_embed(قسم_اسم, data, message)

    view = ReactButton() if config["تفعيل_زر_التفاعل"] else None
    await channel.send(embed=embed, view=view)

    # تحديث الاحصائيات
    if قسم_اسم not in config["احصائيات"]["اجمالي_المرسل"]:
        config["احصائيات"]["اجمالي_المرسل"][قسم_اسم] = 0
    config["احصائيات"]["اجمالي_المرسل"][قسم_اسم] += 1
    save_config(config)

# ========== التاسك اليومي ==========
@tasks.loop(minutes=1)
async def daily_sender():
    now = datetime.now(TZ).strftime("%H:%M")
    config = load_config()

    for قسم_اسم, data in config["الاقسام"].items():
        if data["time"] == now:
            await send_message(قسم_اسم)

# ========== الاوامر ==========
@tree.command(name="تحديث", description="تحديث الرسائل والصور من الملفات")
async def تحديث(interaction: discord.Interaction):
    config = load_config()

    if interaction.user.id not in config["ايدي_الادمن"]:
        return await interaction.response.send_message("ما عندك صلاحية", ephemeral=True)

    await interaction.response.defer(ephemeral=True)
    reload_cache()

    تقرير = "**تم التحديث ✅**\n"
    for قسم in CACHE["رسائل"]:
        عدد_الرسائل = len(CACHE["رسائل"][قسم])
        عدد_الصور = len(CACHE["صور"][قسم])
        تقرير += f"**{قسم}:** {عدد_الرسائل} رسالة | {عدد_الصور} صورة\n"

    await interaction.followup.send(تقرير, ephemeral=True)

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

    رسائل_القسم = CACHE["رسائل"].get(قسم, [])
    if not رسائل_القسم:
        return await interaction.followup.send("لا توجد رسائل في هذا القسم", ephemeral=True)

    message = random.choice(رسائل_القسم)
    embed = build_embed(قسم, data, message)

    view = ReactButton() if config["تفعيل_زر_التفاعل"] else None
    await interaction.followup.send(embed=embed, view=view, ephemeral=True)

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
    bot.add_view(ReactButton())
    print(f"تم تسجيل الدخول باسم {bot.user}")
    daily_sender.start()

bot.run(TOKEN)
