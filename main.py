import discord
from discord.ext import commands
from discord import app_commands
import requests
import json
import os
import sqlite3 # Thư viện mới để lưu trữ dữ liệu

# --- Cấu hình và Thiết lập Database ---
BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN") 
API_BASE_URL = "https://api.mail.tm"
DB_NAME = "bot_data.db" # Tên file database SQLite

def init_db():
    """Khởi tạo kết nối và tạo bảng nếu chưa tồn tại."""
    # Kết nối đến database (nếu file không tồn tại, nó sẽ được tạo)
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Tạo bảng để lưu thông tin email ảo
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

# --- Khởi tạo Bot ---
init_db() # Gọi hàm khởi tạo ngay khi script chạy

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# --- Các hàm thao tác với Database ---

def get_user_email(user_id):
    """Lấy thông tin email từ database theo user_id."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT email, account_id, auth_token FROM emails WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result # Trả về tuple (email, account_id, auth_token) hoặc None

def save_user_email(user_id, email, account_id, auth_token):
    """Lưu thông tin email mới vào database."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Sử dụng INSERT OR REPLACE để cập nhật nếu đã tồn tại, hoặc thêm mới
    cursor.execute("""
        INSERT OR REPLACE INTO emails (user_id, email, account_id, auth_token) 
        VALUES (?, ?, ?, ?)
    """, (user_id, email, account_id, auth_token))
    conn.commit()
    conn.close()

# --- 1. Sự kiện Khởi động Bot ---
@bot.event
async def on_ready():
    print(f'🤖 Đã đăng nhập với tên: {bot.user}')
    try:
        synced = await bot.tree.sync()
        print(f"✨ Đã đồng bộ {len(synced)} lệnh Slash.")
    except Exception as e:
        print(f"Lỗi đồng bộ lệnh: {e}")

# --- 2. Lệnh /layemail (Đã Cập Nhật Persistence) ---
@bot.tree.command(name="layemail", description="Lấy một địa chỉ email ảo tạm thời (đã lưu bền vững).")
async def layemail(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True) 

    user_id = interaction.user.id
    
    # Kiểm tra database thay vì dictionary
    existing_email_data = get_user_email(user_id)
    
    if existing_email_data:
        email_address = existing_email_data[0]
        await interaction.followup.send(
            f"Bạn đã có email được lưu bền vững rồi: **`{email_address}`**.\n"
            "Sử dụng lệnh `/xemthu` để kiểm tra thư.", 
            ephemeral=True
        )
        return

    # 1. Tạo một tài khoản email ảo mới (Sử dụng API Mail.tm như cũ)
    try:
        # Code tạo email và đăng nhập...
        response = requests.post(f"{API_BASE_URL}/accounts", 
                                 json={"address": "", "password": "temp_password_123"},
                                 headers={"Content-Type": "application/json"})
        response.raise_for_status() 
        account_data = response.json()
        
        email_address = account_data['address']
        account_id = account_data['id']
        
        login_response = requests.post(f"{API_BASE_URL}/token",
                                       json={"address": email_address, "password": "temp_password_123"},
                                       headers={"Content-Type": "application/json"})
        login_response.raise_for_status()
        token_data = login_response.json()
        
        auth_token = token_data['token']
        
        # 2. LƯU VÀO DATABASE thay vì dictionary
        save_user_email(user_id, email_address, account_id, auth_token)
        
        await interaction.followup.send(
            f"📧 **Email ảo tạm thời (BỀN VỮNG)** của bạn là: \n"
            f"**`{email_address}`**\n"
            f"Email này đã được lưu vào database và sẽ **không bị mất khi bot khởi động lại!**\n"
            "Sử dụng lệnh `/xemthu` để kiểm tra thư!",
            ephemeral=True
        )

    except requests.exceptions.RequestException as e:
        print(f"Lỗi API khi lấy email: {e}")
        await interaction.followup.send("❌ Đã xảy ra lỗi khi kết nối với dịch vụ email ảo. Vui lòng thử lại sau.", ephemeral=True)
    except Exception as e:
        print(f"Lỗi không xác định: {e}")
        await interaction.followup.send("❌ Đã xảy ra lỗi không xác định.", ephemeral=True)

# --- 3. Lệnh /xemthu (Đã Cập Nhật Persistence) ---
@bot.tree.command(name="xemthu", description="Kiểm tra hộp thư của email ảo đã lưu.")
async def xemthu(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True, ephemeral=True) 

    user_id = interaction.user.id
    
    # Lấy thông tin từ database
    email_data = get_user_email(user_id)
    
    if not email_data:
        await
