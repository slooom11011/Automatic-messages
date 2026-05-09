import discord
from discord.ext import commands, tasks
from discord import app_commands
import json, random, pytz, os
from datetime import datetime, time

TOKEN = os.getenv("TOKEN")
SAUDI = pytz.timezone('Asia/Riyadh')
CONFIG_PATH = "config.json"
DATA_PATH = "data"

def load_config():
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_config(data):
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_quote(section):
    path = f"{DATA_PATH}/{section}.txt"
    if not os.path.exists(path): return None
    with open(path, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f if line.strip()]
    if not lines: return None
    config = load_config()
    used = config["الاقسام"][section].get("المستخدم", [])
    available = [q for q in lines if q not in used]
    if not available:
        available = lines
        config["الاقسام"][section]["المستخدم"] = []
    chosen = random.choice(available)
    config["الاقسام"][section]["المستخدم"].append(chosen)
    if len(config["الاقسام"][section]["المستخدم"]) > config["اعدادات_عامة"]["عدد_التذكر"]:
        config["الاقسام"][section]["المستخدم"].pop(0)
    save_config(config)
    return chosen

class LoveButton(discord.ui.View):
    def __init__(self, section):
        super().__init__(timeout=None)
        self.section = section

    @discord.ui.button(label="❤️", style=discord.ButtonStyle.red, custom_id="love_btn")
    async def love(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = load_config()
        config["احصائيات"]["التفاعلات"][self.section] = config["احصائيات"]["التفاعلات"].get(self.section, 0) + 1
        save_config(config)
        await interaction.response.send_message("شكراً لتفاعلك ❤️", ephemeral=True)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    await bot.tree.sync()
    daily_sender.start()

async def send_section(section):
    config = load_config()
    data = config["الاقسام"][section]
    if not data["مفعل"]: return
    channel = bot.get_channel(int(data["روم"]))
    if not channel: return
    quote = get_quote(section)
    if not quote: return

    embed = discord.Embed(description=f"**{quote}**", color=int(data["لون"].replace("#",""), 16))
    embed.set_author(name=data["عنوان"])
    if data.get("صورة"): embed.set_image(url=data["صورة"])
    num = config["احصائيات"]["اجمالي_المرسل"].get(section, 0) + 1
    embed.set_footer(text=f"الرسالة رقم {num}")
    config["احصائيات"]["اجمالي_المرسل"][section] = num
    save_config(config)

    view = LoveButton(section) if config["اعدادات_عامة"]["تفعيل_زر_التفاعل"] else None
    await channel.send(embed=embed, view=view)

@tasks.loop(minutes=1)
async def daily_sender():
    now = datetime.now(SAUDI)
    today = now.strftime("%A")
    config = load_config()
    if today in config["اعدادات_عامة"]["ايام_الصمت"]: return
    for section, data in config["الاقسام"].items():
        if data["مفعل"] and now.strftime("%H:%M") == data["وقت"]:
            await send_section(section)

@bot.tree.command(name="قسم-جديد", description="إنشاء قسم جديد للإرسال اليومي")
@app_commands.describe(اسم="اسم القسم", روم="ايدي الروم", وقت="HH:MM بتوقيت الرياض", لون="كود اللون #hex", عنوان="عنوان الايمبيد")
async def new_section(interaction: discord.Interaction, اسم: str, روم: str, وقت: str, لون: str = "#3498db", عنوان: str = "رسالة اليوم"):
    config = load_config()
    if اسم in config["الاقسام"]:
        return await interaction.response.send_message("القسم موجود مسبقاً", ephemeral=True)
    try:
        datetime.strptime(وقت, "%H:%M")
        int(روم)
    except:
        return await interaction.response.send_message("تأكد من صيغة الوقت HH:MM وايدي الروم", ephemeral=True)

    config["الاقسام"][اسم] = {"روم": روم, "وقت": وقت, "لون": لون, "عنوان": عنوان, "صورة": "", "مفعل": True, "المستخدم": []}
    config["احصائيات"]["اجمالي_المرسل"][اسم] = 0
    config["احصائيات"]["التفاعلات"][اسم] = 0
    save_config(config)
    with open(f"{DATA_PATH}/{اسم}.txt", 'w', encoding='utf-8'): pass
    await interaction.response.send_message(f"تم إنشاء قسم {اسم} ✅ ارفع ملف {اسم}.txt في مجلد data وضيف المحتوى", ephemeral=True)

@bot.tree.command(name="الاقسام", description="عرض كل الأقسام المضافة")
async def list_sections(interaction: discord.Interaction):
    config = load_config()
    if not config["الاقسام"]:
        return await interaction.response.send_message("مافيه أقسام مضافة", ephemeral=True)
    desc = "\n".join([f"**{k}**: روم <#{v['روم']}> | {v['وقت']} | {'مفعل' if v['مفعل'] else 'موقوف'}" for k,v in config["الاقسام"].items()])
    embed = discord.Embed(title="الأقسام الحالية", description=desc, color=0x2ecc71)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="اضافة", description="إضافة نص لقسم معين")
@app_commands.describe(قسم="اسم القسم", النص="المحتوى المراد إضافته")
async def add_quote(interaction: discord.Interaction, قسم: str, النص: str):
    config = load_config()
    if قسم not in config["الاقسام"]:
        return await interaction.response.send_message("القسم غير موجود", ephemeral=True)
    with open(f"{DATA_PATH}/{قسم}.txt", 'a', encoding='utf-8') as f:
        f.write(f"\n{النص}")
    await interaction.response.send_message(f"تمت الإضافة لقسم {قسم} ✅", ephemeral=True)

@bot.tree.command(name="معاينة", description="معاينة شكل الإرسال لقسم")
@app_commands.describe(قسم="اسم القسم")
async def preview(interaction: discord.Interaction, قسم: str):
    config = load_config()
    if قسم not in config["الاقسام"]:
        return await interaction.response.send_message("القسم غير موجود", ephemeral=True)
    await interaction.response.defer(ephemeral=True)
    await send_section(قسم)
    await interaction.followup.send("تم الإرسال للمعاينة ✅", ephemeral=True)

bot.run(TOKEN)
