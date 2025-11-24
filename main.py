import discord
from discord.ext import commands
from discord import app_commands
import requests
import os
import sqlite3
import random # Dùng để tạo mật khẩu ngẫu nhiên
import string

# --- Cấu hình & Database ---
BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN") 
API_BASE_URL = "https://api.mail.tm"
DB_NAME = "bot_data.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS emails (
            user_id INTEGER PRIMARY KEY,
            email TEXT NOT NULL,
            account_id TEXT NOT NULL,
            auth_token TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def get_user_email(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT email, account_id, auth_token FROM emails WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result 

def save_user_email(user_id, email, account_id, auth_token):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO emails (user_id, email, account_id, auth_token) 
        VALUES (?, ?, ?, ?)
    """, (user_id, email, account_id, auth_token))
    conn.commit()
    conn.close()

def generate_safe_password(length=12):
    characters = string.ascii_letters + string.digits + string.punctuation
    return ''.join(random.choice(characters) for i in range(length))

# --- Khởi tạo Bot ---
init_db()

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f'Bot đã đăng nhập: {bot.user}')
    try:
        synced = await bot.tree.sync()
        print(f"Đã đồng bộ {len(synced)} lệnh Slash.")
    except Exception as e:
        print(f"Lỗi đồng bộ lệnh: {e}")

# --- Lệnh /layemail ---
@bot.tree.command(name="layemail", description="Lấy một địa chỉ email ảo vĩnh viễn.")
async def layemail(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True, ephemeral=True) 

    user_id = interaction.user.id
    existing_email_data = get_user_email(user_id)
    
    if existing_email_data:
        email_address = existing_email_data[0]
        await interaction.followup.send(
            f"Bạn đã có email được lưu: **`{email_address}`**.\n"
            "Sử dụng lệnh `/xemthu` để kiểm tra thư.", 
        )
        return

    try:
        ACCOUNT_PASSWORD = generate_safe_password() 
        
        # 1. TẠO TÀI KHOẢN (Status code phải là 201)
        response = requests.post(
            f"{API_BASE_URL}/accounts", 
            json={"address": "", "password": ACCOUNT_PASSWORD},
            headers={"Content-Type": "application/json"}
        )
        if response.status_code != 201:
            print(f"LỖI TẠO TÀI KHOẢN ({response.status_code}): {response.text}")
            await interaction.followup.send("❌ Lỗi API: Không thể tạo tài khoản email ảo. Vui lòng kiểm tra console.")
            return

        account_data = response.json()
        email_address = account_data['address']
        account_id = account_data['id']
        
        # 2. ĐĂNG NHẬP LẤY TOKEN (Status code phải là 200)
        login_response = requests.post(
            f"{API_BASE_URL}/token",
            json={"address": email_address, "password": ACCOUNT_PASSWORD},
            headers={"Content-Type": "application/json"}
        )
        if login_response.status_code != 200:
            print(f"LỖI LẤY TOKEN ({login_response.status_code}): {login_response.text}")
            await interaction.followup.send("❌ Lỗi API: Không thể lấy token truy cập. Vui lòng kiểm tra console.")
            return

        token_data = login_response.json()
        auth_token = token_data['token']
        
        # Lưu vào DATABASE
        save_user_email(user_id, email_address, account_id, auth_token)
        
        await interaction.followup.send(
            f"📧 Email ảo của bạn là: **`{email_address}`**\n"
            "Email này đã được lưu vĩnh viễn trong database của bot.\n"
            "Sử dụng lệnh `/xemthu` để kiểm tra thư!",
        )

    except requests.exceptions.RequestException as e:
        print(f"LỖI KẾT NỐI MẠNG: {e}")
        await interaction.followup.send("❌ Lỗi kết nối mạng hoặc dịch vụ email ảo không khả dụng. Vui lòng thử lại sau.")
    except Exception as e:
        print(f"LỖI KHÔNG XÁC ĐỊNH: {e}")
        await interaction.followup.send("❌ Đã xảy ra lỗi không xác định. Vui lòng kiểm tra console bot.")

# --- Lệnh /xemthu ---
@bot.tree.command(name="xemthu", description="Kiểm tra hộp thư của email ảo đã lưu.")
async def xemthu(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True, ephemeral=True) 

    user_id = interaction.user.id
    email_data = get_user_email(user_id)
    
    if not email_data:
        await interaction.followup.send("🚫 Bạn chưa có email ảo được lưu. Vui lòng dùng lệnh `/layemail` trước.")
        return
        
    email_address, account_id, auth_token = email_data
    
    try:
        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
        response = requests.get(f"{API_BASE_URL}/messages", headers=headers)
        
        # Kiểm tra trạng thái phản hồi
        if response.status_code != 200:
            print(f"LỖI LẤY THƯ ({response.status_code}): {response.text}")
            await interaction.followup.send("❌ Lỗi API: Không thể lấy thư. Có thể token đã hết hạn hoặc tài khoản bị xóa.")
            return

        messages = response.json().get('hydra:member', [])
        
        if not messages:
            await interaction.followup.send(f"Inbox của **`{email_address}`** không có thư mới nào.")
            return

        embed = discord.Embed(
            title=f"📬 Hộp Thư Email: `{email_address}`",
            description=f"Tìm thấy **{len(messages)}** thư mới nhất.",
            color=discord.Color.blue()
        )
        
        for i, message in enumerate(messages[:5]): 
            subject = message.get('subject', '(Không có tiêu đề)')
            sender = message.get('from', {}).get('address', 'Ẩn danh')
            snippet = message.get('intro', 'Không có nội dung xem trước.')
            
            embed.add_field(
                name=f"✉️ {i+1}. Từ: {sender}",
                value=f"**Tiêu đề**: {subject}\n"
                      f"**Xem trước**: *{snippet[:100]}...*", 
                inline=False
            )
            
        embed.set_footer(text="Nội dung đầy đủ của thư không được hiển thị.")

        await interaction.followup.send(embed=embed)

    except requests.exceptions.RequestException as e:
        print(f"LỖI KẾT NỐI MẠNG: {e}")
        await interaction.followup.send("❌ Lỗi kết nối mạng hoặc dịch vụ email ảo không khả dụng.")
    except Exception as e:
        print(f"LỖI KHÔNG XÁC ĐỊNH: {e}")
        await interaction.followup.send("❌ Đã xảy ra lỗi không xác định. Vui lòng kiểm tra console bot.")

# --- Chạy Bot ---
if BOT_TOKEN:
    bot.run(BOT_TOKEN)
else:
    print("❌ Lỗi: Thiếu biến môi trường DISCORD_BOT_TOKEN.")
    
