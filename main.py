import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import random
import os
from datetime import datetime
import pytz
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

def load_config():
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {"الاقسام": {}, "تفعيل_زر_التفاعل": True}

def save_config(config):
    with open('config.json', 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

config = load_config()

def get_messages(section_name):
    try:
        with open(f'data/{section_name}.txt', 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f.readlines() if line.strip()]
            return lines
    except:
        return []

class ReactButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="❤️", style=discord.ButtonStyle.secondary)
    async def react(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("تم ❤️", ephemeral=True)

@bot.event
async def on_ready():
    print(f'{bot.user} اشتغل!')
    try:
        synced = await bot.tree.sync()
        print(f'تم مزامنة {len(synced)} أمر')
    except Exception as e:
        print(e)
    check_time.start()

@tasks.loop(minutes=1)
async def check_time():
    global config
    config = load_config()  # يحدث الكونفق كل دقيقة
    tz = pytz.timezone('Asia/Riyadh')
    now = datetime.now(tz).strftime('%H:%M')
    
    for section_name, section_data in config['الاقسام'].items():
        if section_data['time'] == now:
            messages = get_messages(section_name)
            if messages:
                channel = bot.get_channel(section_data['channel_id'])
                if channel:
                    msg = random.choice(messages)
                    color = int(str(section_data['color']).replace('#', ''), 16)
                    embed = discord.Embed(
                        title=section_data['title'],
                        description=msg,
                        color=color
                    )
                    embed.set_footer(text=f"Automatic messages  •  اليوم الساعة {now}")
                    
                    view = ReactButton() if config['تفعيل_زر_التفاعل'] else None
                    await channel.send(embed=embed, view=view)

@bot.tree.command(name="قسم-جديد", description="إضافة قسم جديد")
@app_commands.describe(اسم="اسم القسم", روم="ايدي الروم", وقت="وقت الارسال 24 ساعة مثل 08:00", لون="كود اللون مثل #3498db", عنوان="عنوان الايمبيد")
async def قسم_جديد(interaction: discord.Interaction, اسم: str, روم: str, وقت: str, لون: str, عنوان: str):
    global config
    config = load_config()
    
    if اسم in config['الاقسام']:
        await interaction.response.send_message("القسم موجود مسبقاً!", ephemeral=True)
        return
    
    config['الاقسام'][اسم] = {
        "channel_id": int(روم),
        "time": وقت,
        "color": لون.replace('#', ''),
        "title": عنوان
    }
    
    save_config(config)
    
    # انشاء ملف القسم لو مو موجود
    if not os.path.exists('data'):
        os.makedirs('data')
    if not os.path.exists(f'data/{اسم}.txt'):
        with open(f'data/{اسم}.txt', 'w', encoding='utf-8') as f:
            f.write(f"رسالة تجريبية لقسم {اسم}")
    
    await interaction.response.send_message(f"تم إنشاء قسم {اسم} على الساعة {وقت} ✅\nضيف الرسائل في `data/{اسم}.txt`", ephemeral=True)

@bot.tree.command(name="حذف-قسم", description="حذف قسم")
@app_commands.describe(اسم="اسم القسم")
async def حذف_قسم(interaction: discord.Interaction, اسم: str):
    global config
    config = load_config()
    
    if اسم not in config['الاقسام']:
        await interaction.response.send_message("القسم غير موجود!", ephemeral=True)
        return
    
    del config['الاقسام'][اسم]
    save_config(config)
    await interaction.response.send_message(f"تم حذف قسم {اسم} ✅\nملف `data/{اسم}.txt` ما انحذف", ephemeral=True)

@bot.tree.command(name="الاقسام", description="عرض كل الأقسام")
async def الاقسام(interaction: discord.Interaction):
    global config
    config = load_config()
    
    if not config['الاقسام']:
        await interaction.response.send_message("مافي أقسام حالياً", ephemeral=True)
        return
    
    msg = "**الأقسام الحالية:**\n"
    for name, data in config['الاقسام'].items():
        msg += f"• **{name}** - {data['time']} - <#{data['channel_id']}>\n"
    
    await interaction.response.send_message(msg, ephemeral=True)

@bot.tree.command(name="معاينة", description="معاينة رسالة عشوائية من قسم")
@app_commands.describe(قسم="اسم القسم")
async def معاينة(interaction: discord.Interaction, قسم: str):
    global config
    config = load_config()
    
    if قسم not in config['الاقسام']:
        await interaction.response.send_message("القسم غير موجود!", ephemeral=True)
        return
    
    messages = get_messages(قسم)
    if not messages:
        await interaction.response.send_message("مافي رسائل في هذا القسم", ephemeral=True)
        return
    
    msg = random.choice(messages)
    data = config['الاقسام'][قسم]
    color = int(str(data['color']).replace('#', ''), 16)
    embed = discord.Embed(title=data['title'], description=msg, color=color)
    embed.set_footer(text="معاينة فقط")
    
    view = ReactButton() if config['تفعيل_زر_التفاعل'] else None
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

@bot.tree.command(name="اضافة", description="اضافة رسالة لقسم")
@app_commands.describe(قسم="اسم القسم", نص="نص الرسالة")
async def اضافة(interaction: discord.Interaction, قسم: str, نص: str):
    if not os.path.exists('data'):
        os.makedirs('data')
    
    with open(f'data/{قسم}.txt', 'a', encoding='utf-8') as f:
        f.write(f"\n{نص}")
    
    await interaction.response.send_message(f"تمت الإضافة لقسم {قسم} ✅", ephemeral=True)

bot.run(TOKEN)
