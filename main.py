import discord
from discord.ext import commands
from discord import app_commands
import requests
import json
import time
import os
import random
import smtplib 
from email.message import EmailMessage 
import html 
import jwt 
from gevent.threadpool import ThreadPool
import requests.packages.urllib3 
from urllib.parse import urlparse, parse_qs
import asyncio 
from concurrent.futures import ThreadPoolExecutor 
from datetime import datetime, timezone, timedelta # ✅ FIX LỖI: Import datetime, timezone, timedelta

# Import thư viện cần thiết cho các dịch vụ dựa trên HTML/Scraping
try:
    from bs4 import BeautifulSoup
except ImportError:
    # Đây là cảnh báo cho người dùng nếu thiếu thư viện quan trọng
    print("CẢNH BÁO: Thư viện BeautifulSoup4 chưa được cài đặt. Lệnh cài đặt: pip install beautifulsoup4")


# =================================================================
# ⚙️ CẤU HÌNH HỆ THỐNG VÀ API (FIX TRIỆT ĐỂ CHO RENDER)
# =================================================================
STORAGE_FILE = 'active_emails.json'
DEFAULT_EXPIRY = 315360000  # 10 năm (Chủ yếu để giữ trạng thái)
MAX_RETRIES = 5 # Số lần thử lại tối đa

# ID SERVER CỦA BẠN (Sử dụng biến môi trường DISCORD_GUILD_ID khi deploy lên Render)
# Đảm bảo bạn đã thay thế "1438026770975559792" bằng ID Server Discord thật của bạn.
GUILD_ID = int(os.environ.get("DISCORD_GUILD_ID", "1438026770975559792")) # ✅ FIX TRIỆT ĐỂ 1: Đọc GUILD_ID từ Biến Môi Trường

# --- DANH SÁCH DỊCH VỤ ROUND ROBIN MỚI (24 Dịch vụ Siêu Phân Tán) ---
API_PROVIDERS_LIST = [
    'anonaddy', '1secmail', 'emailondeck', 'mailinator', 'dispostable',
    'maildrop', 'mohmal', 'throwaway', 'emaily', 'mailcatch', 
    'getnada', 'guerrillail', 'tempmailorg', 'yopmail', 'luxusmail',
    'tempmailnet', 'inboxalias', 'mailnesia', 'tmail', 'bccto',
    'snailmail', 'dropmail', 'mintemail', 'hackermail' 
]
NUM_PROVIDERS = len(API_PROVIDERS_LIST) 

# --- CẤU HÌNH PROXY & THREAD POOL ---
PROXY_SCRAPER_API = "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=5000&country=all&ssl=yes&anonymity=elite" 
PROXY_DUMMY_API = "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt" 
THREAD_POOL_EXECUTOR = ThreadPoolExecutor(max_workers=50) 

# --- CẤU HÌNH API CHI TIẾT (Giữ nguyên) ---
ONECMAIL_API_BASE_URL = "https://www.1secmail.com/api/v1/"
ONECMAIL_DOMAINS = ["1secmail.com", "1secmail.org", "1secmail.net", "wwjmp.com", "yomail.info", "youmail.win", "t1s.org"] 
EMAILONDECK_API_ALT_BASE_URL = "https://privatemail.dev" 
EMAILONDECK_DOMAINS = ["privatemail.dev", "privatemail.live"] 
MAILINATOR_DOMAIN = "mailinator.com" 
DISPOSTABLE_API_BASE_URL = "https://dispostable.com/api/mail" 
DISPOSTABLE_DOMAIN = "dispostable.com" 
MAILDROP_API_BASE_URL = "https://api.maildrop.cc"
MAILDROP_DOMAIN = "maildrop.cc"
MOHMAL_API_BASE_URL = "https://www.mohmal.com/en/api"
MOHMAL_DOMAINS = ["mohmal.com", "mohmal.in", "mohmal.org"]
THROWAWAY_API_BASE_URL = "https://www.throwawaymail.com/api/v1"
THROWAWAY_DOMAINS = ["throwawaymail.com", "tmail.ws"]
EMAILY_API_BASE_URL = "https://api.email.ly/v1"
EMAILY_DOMAIN = "email.ly"
MAILCATCH_API_BASE_URL = "https://mailcatch.com/en/inbox"
MAILCATCH_DOMAIN = "mailcatch.com"
GETNADA_API_BASE_URL = "https://getnada.com/api/v1"
GETNADA_DOMAINS = ["getnada.com", "getnada.me", "getnada.net"]
GUERRILLAMAIL_API_BASE_URL = "https://api.guerrillamail.com/ajax.php"
TEMPMAILORG_API_BASE_URL = "https://api.temp-mail.io/v1" 
YOPMAIL_API_BASE_URL = "http://www.yopmail.com/en/inbox" 
YOPMAIL_DOMAIN = "yopmail.com"
LUXUSMAIL_API_BASE_URL = "https://api.luxusmail.org/v1" 
LUXUSMAIL_DOMAIN = "luxusmail.org"
LUXUSMAIL_DOMAINS = ["luxusmail.org", "luxusmail.com"]
TEMPMAILNET_API_BASE_URL = "https://api.tempmail.net/v1"
TEMPMAILNET_DOMAINS = ["tempmail.net", "tempmail.co"]
INBOXALIAS_API_BASE_URL = "https://www.inboxalias.com/api" 
INBOXALIAS_DOMAIN = "inboxalias.com"
MAILNESIA_API_BASE_URL = "http://mailnesia.com/mailbox"
MAILNESIA_DOMAIN = "mailnesia.com"
TMAIL_API_BASE_URL = "https://api.tmail.ws/v1" 
TMAIL_DOMAINS = ["tmail.ws", "tmail.io"]
BCCTO_API_BASE_URL = "https://bccto.me/api/v1"
BCCTO_DOMAINS = ["bccto.me", "bccto.co"]
ANONADDY_API_BASE_URL = "https://anonaddy.com/api/v1"
ANONADDY_DOMAINS = ["anonaddy.me", "anonaddy.net"]
SNAILMAIL_API_BASE_URL = "https://api.snailmail.online/v1"
SNAILMAIL_DOMAINS = ["snailmail.online", "snailmail.co"]
DROPMAIL_API_BASE_URL = "https://api.dropmail.me/api/graphql"
DROPMAIL_DOMAIN = "dropmail.me"
MINTEMAIL_API_BASE_URL = "https://www.mintemail.com/api"
MINTEMAIL_DOMAIN = "mintemail.com"
HACKERMAIL_API_BASE_URL = "https://hackermail.com/api/v1" 
HACKERMAIL_DOMAINS = ["hackermail.com", "hackermail.net"]


# 🛡️ PHÒNG THỦ CẤP CAO: RATE LIMITING & COOLDOWN 
USER_COOLDOWN_SECONDS = 120 
GLOBAL_API_DELAY = 0.5 
HUMAN_LIKE_DELAY_MIN = 1.5 
HUMAN_LIKE_DELAY_MAX = 3.0 
last_request_time = {} 

# Mảng lưu trữ domain và proxy đang hoạt động
AVAILABLE_DOMAINS = [] 
ACTIVE_PROXIES = [] 

# --- Cấu hình FINGERPRINTING và SMTP ---

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
]
REFERERS = [
    "https://mail.tm/", 
    "https://www.google.com/", 
    "https://www.bing.com/",
    "about:blank" 
]

# THAY THẾ bằng thông tin SMTP của bạn
SMTP_SERVER = "smtp.gmail.com"  
SENDER_EMAIL = "phancongtu704@gmail.com" # Thay bằng Email Gửi của bạn
SENDER_PASSWORD = os.environ.get("SMTP_APP_PASSWORD") # ✅ FIX TRIỆT ĐỂ 2: Đọc Mật khẩu SMTP từ Biến Môi Trường
SMTP_PORT = 587

# --- Đọc Token Discord từ Biến Môi Trường (Cho Render) ---
TOKEN = os.environ.get("DISCORD_TOKEN") # ✅ FIX TRIỆT ĐỂ 3: Đọc Token từ Biến Môi Trường

if not TOKEN: 
    print("❌ LỖI KHẨN CẤP: Không tìm thấy Token Discord. Vui lòng đặt biến môi trường DISCORD_TOKEN trên Render.")
    # Không exit() nữa, mà cho bot crash (render sẽ báo lỗi)

# Thiết lập Intents và Bot
intents = discord.Intents.default()
# Khởi tạo Guild cho Sync nhanh
guild = discord.Object(id=GUILD_ID) 

# Sử dụng cách khởi tạo CommandTree tiêu chuẩn
bot = commands.Bot(command_prefix='!', intents=intents)
tree = app_commands.CommandTree(bot) 

# =================================================================
# 💾 HÀM QUẢN LÝ LƯU TRỮ VÀ HỖ TRỢ 
# =================================================================

def save_emails(emails_dict):
    """Lưu dữ liệu email vào file JSON."""
    try:
        with open(STORAGE_FILE, 'w', encoding='utf-8') as f:
            # Chuyển đổi keys sang string để lưu JSON
            json.dump({str(k): v for k, v in emails_dict.items()}, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Lỗi khi lưu file JSON: {e}")

def load_emails():
    """Tải dữ liệu email từ file JSON."""
    if os.path.exists(STORAGE_FILE):
        try:
            with open(STORAGE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Chuyển đổi keys từ string về int
                # Lưu ý: Python đọc key JSON là string, nhưng user ID Discord là số nguyên
                return {int(k) if str(k).isdigit() else k: v for k, v in data.items()}
            except (json.JSONDecodeError, ValueError):
                print("Cảnh báo: File lưu trữ bị hỏng hoặc trống, tạo mới.")
                return {}
        except Exception as e:
            print(f"Lỗi khi tải file JSON: {e}")
            return {}
    return {}
        
active_emails = load_emails() 


def get_active_email(user_id):
    """Tìm và trả về đối tượng email đang hoạt động (provider='active') cho user_id."""
    
    # Tìm email có user_id khớp với user_id hiện tại và đang hoạt động
    # Sử dụng list() để tạo bản sao và tránh lỗi RuntimeError khi thay đổi kích thước
    for email, email_data in list(active_emails.items()): 
        if email_data.get('user_id') == str(user_id) and email_data.get('status', 'active') == 'active':
            
            # Kiểm tra thời gian hết hạn (NẾU HẾT HẠN, BÁO LÀ HẾT HẠN)
            if time.time() > email_data.get('expires_at', 0):
                # Đánh dấu là hết hạn
                active_emails[email]['status'] = 'expired'
                save_emails(active_emails) 
                return None 
                
            return {
                'email': email,
                'session_id': email_data.get('session_id'),
                'account_id': email_data.get('account_id'),
                'provider': email_data.get('provider'),
                'expires_at': email_data.get('expires_at')
            }
    return None

def mask_email(email):
    """Che địa chỉ email (ví dụ: ph...704@gmail.com)"""
    if '@' not in email:
        return email
    local_part, domain = email.split('@')
    if len(local_part) > 5:
        masked_local = local_part[:2] + '...' + local_part[-3:]
    else:
        masked_local = local_part
    return f"{masked_local}@{domain}"


# =================================================================
# 🌐 HÀM KIỂM TRA VÀ TẢI PROXY CÔNG CỘNG (Giữ nguyên)
# =================================================================
def check_proxy_health(proxy_ip):
    """Kiểm tra một Proxy cụ thể có hoạt động không."""
    if proxy_ip is None:
        return None 
        
    if not proxy_ip.startswith(('http://', 'https://')):
        proxy_url = f"http://{proxy_ip}"
    else:
        proxy_url = proxy_ip
        
    proxies = {
        'http': proxy_url, 
        'https': proxy_url
    }
    test_url = "https://www.google.com" 
    headers = {'User-Agent': random.choice(USER_AGENTS)}

    try:
        start_time = time.time()
        # Giảm timeout để kiểm tra Proxy nhanh hơn
        response = requests.get(test_url, proxies=proxies, headers=headers, timeout=5, verify=False) 
        end_time = time.time()
        
        # Chỉ chấp nhận 200 OK và độ trễ dưới 4.0s (Proxy chất lượng)
        if response.status_code == 200 and (end_time - start_time) < 4.0:
            latency = end_time - start_time
            print(f"✅ Proxy {proxy_ip} hoạt động. Độ trễ: {latency:.2f}s")
            return proxy_url
        
    except requests.exceptions.RequestException:
        pass 
    except Exception:
        pass
        
    return None

def fetch_proxies_from_url(url):
    """Tải Proxy thô từ một URL."""
    try:
        response = requests.get(url, timeout=15, verify=False)
        response.raise_for_status()
        # Lọc bỏ các dòng trống
        return [p.strip() for p in response.text.split('\n') if p.strip()]
    except Exception as e:
        print(f"❌ Lỗi khi tải Proxy từ {url}: {e}")
        return []

def fetch_and_test_proxies():
    """Lấy và kiểm tra Proxy từ 2 nguồn, lưu vào ACTIVE_PROXIES."""
    global ACTIVE_PROXIES
    
    print("⏳ Bắt đầu tìm kiếm và kiểm tra Proxy công cộng (Chế độ Kiên nhẫn)...")
    
    requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)
    
    # Lấy Proxy từ Nguồn 1
    raw_proxies_1 = fetch_proxies_from_url(PROXY_SCRAPER_API)
    # Lấy Proxy từ Nguồn 2
    raw_proxies_2 = fetch_proxies_from_url(PROXY_DUMMY_API)
    
    all_raw_proxies = list(set(raw_proxies_1 + raw_proxies_2))
    
    print(f"Đã tìm thấy {len(all_raw_proxies)} Proxy thô từ 2 nguồn. Đang kiểm tra chất lượng...")
    
    # Dùng ThreadPoolExecutor cho kiểm tra Proxy
    working_proxies = []
    with ThreadPoolExecutor(max_workers=50) as executor:
        futures = [executor.submit(check_proxy_health, p) for p in all_raw_proxies]
        for future in futures:
            proxy = future.result()
            if proxy is not None:
                working_proxies.append(proxy)
    
    ACTIVE_PROXIES = working_proxies
    
    if ACTIVE_PROXIES:
        print(f"🎉 Đã tìm thấy {len(ACTIVE_PROXIES)} Proxy công cộng hoạt động! Bot sẽ dùng chúng.")
    else:
        print("⚠️ KHẨN CẤP: Không tìm thấy Proxy công cộng nào. Bot sẽ dùng IP gốc (Rủi ro chặn IP).")
# =================================================================
# 🛡️ HÀM BẢO VỆ TỐI ĐA (Cơ chế Roaming và Throttling) (Giữ nguyên)
# =================================================================
def check_user_cooldown(user_id):
    """Kiểm tra Cooldown cá nhân."""
    if user_id in last_request_time:
        elapsed = time.time() - last_request_time[user_id]
        if elapsed < USER_COOLDOWN_SECONDS:
            remaining = USER_COOLDOWN_SECONDS - elapsed
            return False, remaining
    return True, 0

def update_user_cooldown(user_id):
    """Cập nhật thời gian yêu cầu cuối cùng của người dùng."""
    last_request_time[user_id] = time.time()


def make_api_request_blocking(user_id, method, url, data=None, token=None, params=None):
    """
    Thực hiện request API ở chế độ Siêu An toàn (Blocking/Sync Version).
    Phiên bản V12.2: Ưu tiên Proxy cho các API Scraping/HTML.
    """
    
    global ACTIVE_PROXIES
    last_error = "Lỗi nội bộ."
    
    # 0. GLOBAL RATE LIMITING
    global_time_elapsed = time.time() - last_request_time.get('GLOBAL_API_CALL', 0)
    if global_time_elapsed < GLOBAL_API_DELAY:
        time.sleep(GLOBAL_API_DELAY - global_time_elapsed) 
    last_request_time['GLOBAL_API_CALL'] = time.time()
    
    full_proxy_list = ACTIVE_PROXIES + [None] 
    
    # 🌟 CÁC API CẦN BẢO VỆ PROXY ĐẶC BIỆT (Scraping/HTML)
    SCRAPING_APIS = ['mailcatch', 'yopmail', 'mailnesia', 'mintemail', 'dispostable'] 
    
    for attempt in range(MAX_RETRIES):
        
        # 🛡️ BƯỚC 1: ĐỘ TRỄ CỰC ĐẠI VÀ NGẪU NHIÊN (Human-Like Delay)
        delay = random.uniform(HUMAN_LIKE_DELAY_MIN, HUMAN_LIKE_DELAY_MAX) 
        print(f"ĐỘ TRỄ AN TOÀN (Human-Like): {delay:.2f}s...")
        time.sleep(delay) 
        
        # 1.1 LỰA CHỌN PROXY TỐI ƯU
        proxy_url = None
        proxy_info = "IP GỐC (RỦI RO)"
        
        if method == 'GET' and any(api in url for api in SCRAPING_APIS):
            # Nếu là API Scraping, ưu tiên sử dụng Proxy hoạt động
            if ACTIVE_PROXIES:
                proxy_url = random.choice(ACTIVE_PROXIES)
                proxy_info = f"PROXY SCRAPING ({proxy_url.split('/')[-1]})"
            else:
                proxy_info = "IP GỐC (SCRAPING RẤT RỦI RO)"
        else:
            # Đối với các API JSON khác, dùng Roaming bình thường (Proxy hoặc IP Gốc)
            proxy_choice = random.choice(full_proxy_list)
            if proxy_choice is not None:
                proxy_url = proxy_choice
                proxy_info = proxy_url.split('/')[-1]
            # Nếu proxy_url là None, nó sẽ là IP Gốc
            
        proxies = {'http': proxy_url, 'https': proxy_url} if proxy_url else None
            
        # 1.2 Tạo Headers (Fingerprinting & Spoofing)
        headers = {
            'User-Agent': random.choice(USER_AGENTS), 
            'Accept': 'application/json',
            'Content-Type': 'application/json', 
            'Connection': 'keep-alive', 
            'Referer': random.choice(REFERERS) 
        }
        if token:
            headers['Authorization'] = f'Bearer {token}'
        
        # Xử lý đặc biệt cho một số API không dùng JSON mặc định
        if any(api in url for api in SCRAPING_APIS): 
            headers['Accept'] = 'text/html,text/plain'
            if 'Content-Type' in headers:
                del headers['Content-Type']
        elif 'getnada' in url:
            headers['Accept'] = 'text/plain' 
        elif 'guerrillamail' in url:
            if 'Content-Type' in headers:
                del headers['Content-Type'] 
        elif 'dropmail' in url:
            headers['Content-Type'] = 'application/json' 

        requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

        try:
            # 1.3 Gửi Request (Timeout 8s)
            timeout = 8 
            
            # Khởi tạo session để tái sử dụng kết nối (Tăng tốc độ)
            with requests.Session() as session:
                session.headers.update(headers)
                if proxies:
                    session.proxies.update(proxies)
                session.verify = False # Tắt xác thực SSL
                
                response = None
                if method == 'GET':
                    response = session.get(url, timeout=timeout, params=params)
                elif method == 'POST':
                    if data is not None and any(api in url for api in SCRAPING_APIS):
                        response = session.post(url, data=data, timeout=timeout, params=params)
                    elif data is not None and 'dropmail' in url:
                        response = session.post(url, data=data, timeout=timeout)
                    else:
                        response = session.post(url, json=data, timeout=timeout, params=params)
                elif method == 'DELETE':
                    response = session.delete(url, timeout=timeout, params=params)
                else:
                    raise ValueError("Method not supported")

            response.raise_for_status() 
            
            # ... (Xử lý phản hồi JSON/Text/HTML) ...
            content_type = response.headers.get('Content-Type', '').lower()
            if 'application/json' in content_type:
                data = response.json()
            elif response.text.strip():
                data = response.text 
            else:
                data = {} 
                
            print(f"✅ Lần thử {attempt+1} thành công. Proxy/IP: {proxy_info}")
            
            return data, None
            
        except requests.exceptions.RequestException as e:
            
            # Xử lý lỗi đặc biệt: 500, 403, 429
            status_code = response.status_code if 'response' in locals() and response is not None else 'N/A'
            if status_code in [500, 403, 429] and proxy_url is None:
                # Nếu là lỗi server/chặn IP và đang dùng IP gốc, thoát vòng lặp ngay
                last_error = f"LỖI IP GỐC BỊ CHẶN ({status_code}): {url}. {e}"
                print(f"❌ Lần thử {attempt+1} thất bại. {last_error}")
                break
            
            # Nếu đang dùng Proxy và bị lỗi, loại bỏ tạm thời
            if proxy_url is not None:
                if proxy_url in ACTIVE_PROXIES:
                    ACTIVE_PROXIES.remove(proxy_url)
                    print(f"🚨 Loại bỏ Proxy {proxy_url} khỏi vòng quay tạm thời do bị lỗi.")
                
            last_error = f"Lỗi Proxy/IP {proxy_info}: {e}. Status: {status_code}"
            print(f"❌ Lần thử {attempt+1} thất bại. {last_error}")
            
        except json.JSONDecodeError as e:
            last_error = f"Lỗi phản hồi (Không phải JSON). IP/Proxy: {proxy_info}. Chi tiết: {e}. Phản hồi: {response.text[:50]}"
            print(f"❌ Lần thử {attempt+1} thất bại. {last_error}")
            if proxy_url is None:
                break
            
        except Exception as e:
            last_error = f"Lỗi xử lý không xác định: {e}"
            print(f"❌ Lần thử {attempt+1} thất bại. {last_error}")
            break 

    final_error_mode = "IP GỐC THẤT BẠI" if not ACTIVE_PROXIES else "PROXY ROAMING THẤT BẠI"
    return None, f"Bot không thể kết nối hoặc API bị chặn ({final_error_mode}). Chi tiết: {last_error}"


# 🔔 Hàm ASYNC gọi hàm BLOCKING (Thay thế hàm make_api_request cũ)
async def make_api_request(user_id, method, url, data=None, token=None, params=None):
    """Sử dụng ThreadPoolExecutor để chạy hàm blocking API call."""
    return await bot.loop.run_in_executor(
        THREAD_POOL_EXECUTOR,
        lambda: make_api_request_blocking(user_id, method, url, data, token, params)
    )

# =================================================================
# 📧 HÀM API EMAIL ẢO 
# =================================================================

async def create_1secmail_email(user_id):
    username = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=10))
    domain = random.choice(ONECMAIL_DOMAINS)
    email = f"{username}@{domain}"
    print(f"Tạo 1secmail thành công: {email}")
    return email, username, time.time() + DEFAULT_EXPIRY, domain, '1secmail'

async def check_1secmail_inbox(user_id, username, domain):
    url = f"{ONECMAIL_API_BASE_URL}"
    params = {"action": "getMessages", "login": username, "domain": domain}
    response, error = await make_api_request(user_id, 'GET', url, params=params) 
    
    if not response or not isinstance(response, list):
        print(f"1secmail: Lỗi khi kiểm tra inbox: {error}")
        return []
        
    formatted_messages = []
    for msg_summary in response:
        msg_id = msg_summary.get('id')
        read_url = f"{ONECMAIL_API_BASE_URL}"
        read_params = {"action": "readMessage", "login": username, "domain": domain, "id": msg_id}
        msg_detail, detail_error = await make_api_request(user_id, 'GET', read_url, params=read_params) 
        
        if msg_detail:
            sender = msg_detail.get('from', 'Người gửi ẩn danh')
            subject = msg_detail.get('subject', 'Không có tiêu đề')
            text_body = msg_detail.get('textBody', '')
            body_snippet = text_body.strip() if text_body else 'Không có nội dung'

            if len(body_snippet) > 150:
                body_snippet = body_snippet[:150] + '...'
            formatted_messages.append({'from': sender, 'subject': subject, 'body': body_snippet})
            
    return formatted_messages

async def create_emailondeck_alt_email(user_id):
    domain = random.choice(EMAILONDECK_DOMAINS)
    username = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=10))
    password = ''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*', k=16))
    email = f"{username}@{domain}"
    account_data = {"address": email, "password": password}
    response, error = await make_api_request(user_id, 'POST', f"{EMAILONDECK_API_ALT_BASE_URL}/accounts", data=account_data) 

    if response and response.get('id'):
        account_id = response['id']
        login_response, login_error = await make_api_request(user_id, 'POST', f"{EMAILONDECK_API_ALT_BASE_URL}/token", data=account_data) 
        
        if login_response and login_response.get('token'):
            jwt_token = login_response['token']
            expiry_time = time.time() + DEFAULT_EXPIRY 
            print(f"Tạo EmailOnDeck (Alt) thành công: {email}")
            return email, jwt_token, expiry_time, account_id, 'emailondeck'
        
        await delete_emailondeck_alt_account(account_id, None) 
        return None, f"EmailOnDeck (Alt): Lỗi đăng nhập/lấy Token: {login_error}", None, None, 'emailondeck'

    return None, error, None, None, 'emailondeck'

async def check_emailondeck_alt_inbox(user_id, jwt_token):
    response, error = await make_api_request(user_id, 'GET', f"{EMAILONDECK_API_ALT_BASE_URL}/messages", token=jwt_token) 
    
    if not response or not isinstance(response, list):
        print(f"EmailOnDeck (Alt): Lỗi khi kiểm tra inbox: {error}")
        return []
    
    formatted_messages = []
    for msg in response:
        sender = msg.get('from', {}).get('address', 'Người gửi ẩn danh')
        subject = msg.get('subject', 'Không có tiêu đề')
        body_snippet = msg.get('intro', 'Không có nội dung').strip()
        if len(body_snippet) > 150:
            body_snippet = body_snippet[:150] + '...'
        formatted_messages.append({'from': sender, 'subject': subject, 'body': body_snippet})
    return formatted_messages

async def delete_emailondeck_alt_account(account_id, jwt_token):
    if account_id and jwt_token:
        response, error = await make_api_request(None, 'DELETE', f"{EMAILONDECK_API_ALT_BASE_URL}/accounts/{account_id}", token=jwt_token) 
        if error:
            print(f"Cảnh báo: Không thể xóa EmailOnDeck (Alt) {account_id}. Lỗi: {error}")
        else:
            print(f"Đã xóa EmailOnDeck (Alt) thành công: {account_id}")
    else:
        pass 

async def create_mailinator_email(user_id):
    username = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=10))
    email = f"{username}@{MAILINATOR_DOMAIN}"
    print(f"Tạo Mailinator thành công: {email}")
    return email, username, time.time() + DEFAULT_EXPIRY, None, 'mailinator'

async def check_mailinator_inbox(user_id, username):
    url_alt = f"https://www.mailinator.com/v3/api/public/inbox/{username}"
    response_alt, error_alt = await make_api_request(user_id, 'GET', url_alt) 
    
    if not response_alt or not isinstance(response_alt.get('msgs'), list):
        print(f"Mailinator: Lỗi khi kiểm tra inbox: {error_alt}")
        return []
        
    formatted_messages = []
    for msg in response_alt['msgs']:
        sender = msg.get('fromfull', 'Người gửi ẩn danh')
        subject = msg.get('subject', 'Không có tiêu đề')
        body_snippet = "Không thể trích xuất nội dung ngắn trong API công khai."
        formatted_messages.append({'from': sender, 'subject': subject, 'body': body_snippet})
            
    return formatted_messages

async def create_dispostable_email(user_id):
    username = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=10))
    email = f"{username}@{DISPOSTABLE_DOMAIN}"
    print(f"Tạo Dispostable thành công: {email}")
    return email, username, time.time() + DEFAULT_EXPIRY, DISPOSTABLE_DOMAIN, 'dispostable'

async def check_dispostable_inbox(user_id, username):
    url = f"{DISPOSTABLE_API_BASE_URL}/inbox/{username}"
    response, error = await make_api_request(user_id, 'GET', url) 
    
    if not response or not isinstance(response, list):
        print(f"Dispostable: Lỗi khi kiểm tra inbox: {error}")
        return []
        
    formatted_messages = []
    for msg in response:
        sender = msg.get('from', 'Người gửi ẩn danh')
        subject = msg.get('subject', 'Không có tiêu đề')
        body_snippet = msg.get('body_text_short', 'Không có nội dung').strip()
        if len(body_snippet) > 150:
            body_snippet = body_snippet[:150] + '...'
            
        formatted_messages.append({'from': sender, 'subject': subject, 'body': body_snippet})
            
    return formatted_messages

async def create_maildrop_email(user_id):
    username = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=10))
    email = f"{username}@{MAILDROP_DOMAIN}"
    print(f"Tạo Maildrop thành công: {email}")
    return email, username, time.time() + DEFAULT_EXPIRY, None, 'maildrop'

async def check_maildrop_inbox(user_id, username):
    url = f"{MAILDROP_API_BASE_URL}/inbox/{username}"
    response, error = await make_api_request(user_id, 'GET', url) 
    
    if not response or not isinstance(response.get('messages'), list):
        print(f"Maildrop: Lỗi khi kiểm tra inbox: {error}")
        return []
        
    formatted_messages = []
    for msg in response['messages']:
        sender = msg.get('from', 'Người gửi ẩn danh')
        subject = msg.get('subject', 'Không có tiêu đề')
        body_snippet = msg.get('message_snippet', 'Không có nội dung').strip()
        if len(body_snippet) > 150:
            body_snippet = body_snippet[:150] + '...'
            
        formatted_messages.append({'from': sender, 'subject': subject, 'body': body_snippet})
            
    return formatted_messages

async def create_mohmal_email(user_id):
    domain = random.choice(MOHMAL_DOMAINS)
    url = f"{MOHMAL_API_BASE_URL}?action=genRandomMail&domain={domain}"
    response, error = await make_api_request(user_id, 'GET', url) 

    if response and isinstance(response, dict) and response.get('result'):
        email = response['result']
        username = email.split('@')[0]
        print(f"Tạo Mohmal thành công: {email}")
        return email, username, time.time() + DEFAULT_EXPIRY, domain, 'mohmal'
    
    return None, error, None, None, 'mohmal'

async def check_mohmal_inbox(user_id, username, domain):
    email = f"{username}@{domain}"
    url = f"{MOHMAL_API_BASE_URL}?action=getEmailList&email={email}"
    response, error = await make_api_request(user_id, 'GET', url) 
    
    if not response or not isinstance(response, dict) or not isinstance(response.get('result'), list):
        print(f"Mohmal: Lỗi khi kiểm tra inbox: {error}")
        return []
        
    formatted_messages = []
    for msg in response['result']:
        sender = msg.get('from', 'Người gửi ẩn danh')
        subject = msg.get('subject', 'Không có tiêu đề')
        body_snippet = msg.get('body', 'Không có nội dung').strip()
        
        if len(body_snippet) > 150:
            body_snippet = body_snippet[:150] + '...'
            
        formatted_messages.append({'from': sender, 'subject': subject, 'body': body_snippet})
            
    return formatted_messages

async def create_throwaway_email(user_id):
    domain = random.choice(THROWAWAY_DOMAINS)
    url_session = f"{THROWAWAY_API_BASE_URL}/session/new"
    
    response_session, error_session = await make_api_request(user_id, 'POST', url_session) 
    
    if response_session and isinstance(response_session, dict) and response_session.get('id'):
        session_id = response_session['id']
        email = f"{session_id}@{domain}"
        expiry_time = time.time() + (60 * 60) # 1 giờ
        print(f"Tạo Throwaway Mail thành công: {email}")
        
        return email, session_id, expiry_time, domain, 'throwaway'
        
    return None, error_session, None, None, 'throwaway'

async def check_throwaway_inbox(user_id, session_id):
    url = f"{THROWAWAY_API_BASE_URL}/session/{session_id}/mail"
    response, error = await make_api_request(user_id, 'GET', url) 
    
    if not response or not isinstance(response, dict) or not isinstance(response.get('mails'), list):
        print(f"Throwaway Mail: Lỗi khi kiểm tra inbox: {error}")
        return []
        
    formatted_messages = []
    for msg in response['mails']:
        sender = msg.get('from', 'Người gửi ẩn danh')
        subject = msg.get('subject', 'Không có tiêu đề')
        body_snippet = msg.get('text', 'Không có nội dung').strip()
        
        if len(body_snippet) > 150:
            body_snippet = body_snippet[:150] + '...'
            
        formatted_messages.append({'from': sender, 'subject': subject, 'body': body_snippet})
            
    return formatted_messages

async def create_emaily_email(user_id):
    username = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=10))
    email = f"{username}@{EMAILY_DOMAIN}"
    print(f"Tạo Email.ly thành công: {email}")
    return email, username, time.time() + DEFAULT_EXPIRY, None, 'emaily'

async def check_emaily_inbox(user_id, username):
    url = f"{EMAILY_API_BASE_URL}/inbox/{username}/messages"
    response, error = await make_api_request(user_id, 'GET', url) 
    
    if not response or not isinstance(response, dict) or not isinstance(response.get('messages'), list):
        print(f"Email.ly: Lỗi khi kiểm tra inbox: {error}")
        return []
        
    formatted_messages = []
    for msg in response['messages']:
        sender = msg.get('sender', 'Người gửi ẩn danh')
        subject = msg.get('subject', 'Không có tiêu đề')
        body_snippet = msg.get('summary', 'Không có nội dung').strip()
        if len(body_snippet) > 150:
            body_snippet = body_snippet[:150] + '...'
            
        formatted_messages.append({'from': sender, 'subject': subject, 'body': body_snippet})
            
    return formatted_messages

async def create_mailcatch_email(user_id):
    username = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=10))
    email = f"{username}@{MAILCATCH_DOMAIN}"
    print(f"Tạo MailCatch thành công: {email}")
    return email, username, time.time() + DEFAULT_EXPIRY, None, 'mailcatch'

async def check_mailcatch_inbox(user_id, username):
    url = f"{MAILCATCH_API_BASE_URL}/{username}"
    # MailCatch dùng HTML Scraping
    html_content, error = await make_api_request(user_id, 'GET', url) 
    
    if not html_content or not isinstance(html_content, str):
        print(f"MailCatch: Lỗi khi kiểm tra inbox (HTML): {error}")
        return []
        
    messages = []
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Tìm bảng inbox
        inbox_table = soup.find('table', class_='table')
        if inbox_table:
            email_rows = inbox_table.find_all('tr')[1:] # Bỏ hàng tiêu đề
            for row in email_rows:
                cols = row.find_all('td')
                if len(cols) >= 3:
                    sender = cols[1].text.strip()
                    subject = cols[2].text.strip()
                    messages.append({'from': sender, 'subject': subject, 'body': 'Không thể trích xuất nội dung ngắn (API HTML).'})
    except Exception as e:
        print(f"MailCatch: Lỗi parsing HTML: {e}")
        return []
        
    return messages

async def create_getnada_email(user_id):
    username = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=10))
    domain = random.choice(GETNADA_DOMAINS)
    email = f"{username}@{domain}"
    url = f"{GETNADA_API_BASE_URL}/mailbox/{email}"
    # GetNada không cần gọi API tạo, chỉ cần gọi API check
    print(f"Tạo GetNada thành công: {email}")
    return email, username, time.time() + DEFAULT_EXPIRY, domain, 'getnada'

async def check_getnada_inbox(user_id, email):
    url = f"{GETNADA_API_BASE_URL}/mailbox/{email}"
    response, error = await make_api_request(user_id, 'GET', url) 
    
    if not response or not isinstance(response, dict) or not isinstance(response.get('msgs'), list):
        print(f"GetNada: Lỗi khi kiểm tra inbox: {error}")
        return []
        
    formatted_messages = []
    for msg in response['msgs']:
        sender = msg.get('f', 'Người gửi ẩn danh')
        subject = msg.get('s', 'Không có tiêu đề')
        # Nội dung cần gọi API chi tiết
        body_snippet = "Không thể trích xuất nội dung ngắn trong API công khai."
            
        formatted_messages.append({'from': sender, 'subject': subject, 'body': body_snippet})
            
    return formatted_messages

async def create_guerrillamail_email(user_id):
    url = GUERRILLAMAIL_API_BASE_URL
    params = {"action": "get_email_address"}
    response, error = await make_api_request(user_id, 'GET', url, params=params) 

    if response and isinstance(response, dict) and response.get('email_addr'):
        email = response['email_addr']
        session_id = response.get('sid_token')
        print(f"Tạo Guerrilla Mail thành công: {email}")
        return email, session_id, time.time() + DEFAULT_EXPIRY, None, 'guerrillail'
    
    return None, error, None, None, 'guerrillail'

async def check_guerrillamail_inbox(user_id, session_id):
    url = GUERRILLAMAIL_API_BASE_URL
    params = {"action": "get_email_list", "offset": 0, "sid_token": session_id}
    response, error = await make_api_request(user_id, 'GET', url, params=params) 

    if not response or not isinstance(response, dict) or not isinstance(response.get('list'), list):
        print(f"Guerrilla Mail: Lỗi khi kiểm tra inbox: {error}")
        return []
        
    formatted_messages = []
    for msg in response['list']:
        sender = msg.get('mail_from', 'Người gửi ẩn danh')
        subject = msg.get('mail_subject', 'Không có tiêu đề')
        body_snippet = "Không thể trích xuất nội dung ngắn trong API công khai."
        formatted_messages.append({'from': sender, 'subject': subject, 'body': body_snippet})
            
    return formatted_messages

async def create_tempmailorg_email(user_id):
    username = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=10))
    domain = "temp-mail.io"
    email = f"{username}@{domain}"
    print(f"Tạo Temp-Mail.org (Alt) thành công: {email}")
    return email, username, time.time() + DEFAULT_EXPIRY, domain, 'tempmailorg'

async def check_tempmailorg_inbox(user_id, username, domain):
    email = f"{username}@{domain}"
    url = f"{TEMPMAILORG_API_BASE_URL}/mailbox/{email}"
    response, error = await make_api_request(user_id, 'GET', url) 
    
    if not response or not isinstance(response, list):
        print(f"Temp-Mail.org: Lỗi khi kiểm tra inbox: {error}")
        return []
        
    formatted_messages = []
    for msg in response:
        sender = msg.get('from', 'Người gửi ẩn danh')
        subject = msg.get('subject', 'Không có tiêu đề')
        body_snippet = msg.get('body', 'Không có nội dung').strip()
        if len(body_snippet) > 150:
            body_snippet = body_snippet[:150] + '...'
            
        formatted_messages.append({'from': sender, 'subject': subject, 'body': body_snippet})
            
    return formatted_messages

async def create_yopmail_email(user_id):
    username = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=10))
    email = f"{username}@{YOPMAIL_DOMAIN}"
    print(f"Tạo Yopmail thành công: {email}")
    return email, username, time.time() + DEFAULT_EXPIRY, None, 'yopmail'

async def check_yopmail_inbox(user_id, username):
    url = f"{YOPMAIL_API_BASE_URL}/{username}"
    # Yopmail dùng HTML Scraping
    html_content, error = await make_api_request(user_id, 'GET', url) 
    
    if not html_content or not isinstance(html_content, str):
        print(f"Yopmail: Lỗi khi kiểm tra inbox (HTML): {error}")
        return []
        
    messages = []
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Tìm danh sách mail
        mail_list = soup.find('div', id='mail')
        if mail_list:
            for mail in mail_list.find_all('div', class_='m'): # Giả định cấu trúc HTML
                sender_tag = mail.find('div', class_='mname')
                subject_tag = mail.find('div', class_='lsub')
                
                sender = sender_tag.text.strip() if sender_tag else 'Người gửi ẩn danh'
                subject = subject_tag.text.strip() if subject_tag else 'Không có tiêu đề'
                
                messages.append({'from': sender, 'subject': subject, 'body': 'Không thể trích xuất nội dung ngắn (API HTML).'})
    except Exception as e:
        print(f"Yopmail: Lỗi parsing HTML: {e}")
        return []
        
    return messages

async def create_luxusmail_email(user_id):
    username = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=10))
    domain = random.choice(LUXUSMAIL_DOMAINS)
    email = f"{username}@{domain}"
    print(f"Tạo LuxusMail thành công: {email}")
    return email, username, time.time() + DEFAULT_EXPIRY, domain, 'luxusmail'

async def check_luxusmail_inbox(user_id, username, domain):
    url = f"{LUXUSMAIL_API_BASE_URL}/mailbox/{username}@{domain}"
    response, error = await make_api_request(user_id, 'GET', url) 

    if not response or not isinstance(response, dict) or not isinstance(response.get('emails'), list):
        print(f"LuxusMail: Lỗi khi kiểm tra inbox: {error}")
        return []
        
    formatted_messages = []
    for msg in response['emails']:
        sender = msg.get('sender', 'Người gửi ẩn danh')
        subject = msg.get('subject', 'Không có tiêu đề')
        body_snippet = msg.get('body_text', 'Không có nội dung').strip()
        if len(body_snippet) > 150:
            body_snippet = body_snippet[:150] + '...'
            
        formatted_messages.append({'from': sender, 'subject': subject, 'body': body_snippet})
            
    return formatted_messages

async def create_tempmailnet_email(user_id):
    username = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=10))
    domain = random.choice(TEMPMAILNET_DOMAINS)
    email = f"{username}@{domain}"
    print(f"Tạo TempMail.net thành công: {email}")
    return email, username, time.time() + DEFAULT_EXPIRY, domain, 'tempmailnet'

async def check_tempmailnet_inbox(user_id, username, domain):
    email = f"{username}@{domain}"
    url = f"{TEMPMAILNET_API_BASE_URL}/mailbox/{email}"
    response, error = await make_api_request(user_id, 'GET', url) 
    
    if not response or not isinstance(response, list):
        print(f"TempMail.net: Lỗi khi kiểm tra inbox: {error}")
        return []
        
    formatted_messages = []
    for msg in response:
        sender = msg.get('from', 'Người gửi ẩn danh')
        subject = msg.get('subject', 'Không có tiêu đề')
        body_snippet = msg.get('body', 'Không có nội dung').strip()
        if len(body_snippet) > 150:
            body_snippet = body_snippet[:150] + '...'
            
        formatted_messages.append({'from': sender, 'subject': subject, 'body': body_snippet})
            
    return formatted_messages

async def create_inboxalias_email(user_id):
    username = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=10))
    email = f"{username}@{INBOXALIAS_DOMAIN}"
    print(f"Tạo Inbox Alias thành công: {email}")
    return email, username, time.time() + DEFAULT_EXPIRY, None, 'inboxalias'

async def check_inboxalias_inbox(user_id, username):
    url = f"{INBOXALIAS_API_BASE_URL}/inbox/{username}"
    response, error = await make_api_request(user_id, 'GET', url) 
    
    if not response or not isinstance(response, dict) or not isinstance(response.get('messages'), list):
        print(f"Inbox Alias: Lỗi khi kiểm tra inbox: {error}")
        return []
        
    formatted_messages = []
    for msg in response['messages']:
        sender = msg.get('from', 'Người gửi ẩn danh')
        subject = msg.get('subject', 'Không có tiêu đề')
        body_snippet = msg.get('body_text', 'Không có nội dung').strip()
        if len(body_snippet) > 150:
            body_snippet = body_snippet[:150] + '...'
            
        formatted_messages.append({'from': sender, 'subject': subject, 'body': body_snippet})
            
    return formatted_messages

async def create_mailnesia_email(user_id):
    username = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=10))
    email = f"{username}@{MAILNESIA_DOMAIN}"
    print(f"Tạo Mailnesia thành công: {email}")
    return email, username, time.time() + DEFAULT_EXPIRY, None, 'mailnesia'

async def check_mailnesia_inbox(user_id, username):
    url = f"{MAILNESIA_API_BASE_URL}/{username}"
    # Mailnesia dùng HTML Scraping
    html_content, error = await make_api_request(user_id, 'GET', url) 
    
    if not html_content or not isinstance(html_content, str):
        print(f"Mailnesia: Lỗi khi kiểm tra inbox (HTML): {error}")
        return []
        
    messages = []
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        inbox_table = soup.find('table', id='inbox_table')
        if inbox_table:
            email_rows = inbox_table.find_all('tr')[1:]
            for row in email_rows:
                cols = row.find_all('td')
                if len(cols) >= 4:
                    sender = cols[2].text.strip()
                    subject = cols[3].text.strip()
                    messages.append({'from': sender, 'subject': subject, 'body': 'Không thể trích xuất nội dung ngắn (API HTML).'})
    except Exception as e:
        print(f"Mailnesia: Lỗi parsing HTML: {e}")
        return []
        
    return messages

async def create_tmail_email(user_id):
    username = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=10))
    domain = random.choice(TMAIL_DOMAINS)
    email = f"{username}@{domain}"
    print(f"Tạo Tmail thành công: {email}")
    return email, username, time.time() + DEFAULT_EXPIRY, domain, 'tmail'

async def check_tmail_inbox(user_id, username, domain):
    email = f"{username}@{domain}"
    url = f"{TMAIL_API_BASE_URL}/mailbox/{email}"
    response, error = await make_api_request(user_id, 'GET', url) 
    
    if not response or not isinstance(response, list):
        print(f"Tmail: Lỗi khi kiểm tra inbox: {error}")
        return []
        
    formatted_messages = []
    for msg in response:
        sender = msg.get('from', 'Người gửi ẩn danh')
        subject = msg.get('subject', 'Không có tiêu đề')
        body_snippet = msg.get('body', 'Không có nội dung').strip()
        if len(body_snippet) > 150:
            body_snippet = body_snippet[:150] + '...'
            
        formatted_messages.append({'from': sender, 'subject': subject, 'body': body_snippet})
            
    return formatted_messages

async def create_bccto_email(user_id):
    username = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=10))
    domain = random.choice(BCCTO_DOMAINS)
    email = f"{username}@{domain}"
    print(f"Tạo bccto thành công: {email}")
    return email, username, time.time() + DEFAULT_EXPIRY, domain, 'bccto'

async def check_bccto_inbox(user_id, username, domain):
    email = f"{username}@{domain}"
    url = f"{BCCTO_API_BASE_URL}/mailbox/{email}"
    response, error = await make_api_request(user_id, 'GET', url) 
    
    if not response or not isinstance(response, list):
        print(f"bccto: Lỗi khi kiểm tra inbox: {error}")
        return []
        
    formatted_messages = []
    for msg in response:
        sender = msg.get('from', 'Người gửi ẩn danh')
        subject = msg.get('subject', 'Không có tiêu đề')
        body_snippet = msg.get('body', 'Không có nội dung').strip()
        if len(body_snippet) > 150:
            body_snippet = body_snippet[:150] + '...'
            
        formatted_messages.append({'from': sender, 'subject': subject, 'body': body_snippet})
            
    return formatted_messages

async def create_anonaddy_email(user_id):
    username = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=10))
    domain = random.choice(ANONADDY_DOMAINS)
    email = f"{username}@{domain}"
    print(f"Tạo AnonAddy (Alt) thành công: {email}")
    return email, username, time.time() + DEFAULT_EXPIRY, domain, 'anonaddy'

async def check_anonaddy_inbox(user_id, username, domain):
    url = f"{ANONADDY_API_BASE_URL}/messages"
    params = {"search": f"{username}@{domain}"}
    response, error = await make_api_request(user_id, 'GET', url, params=params) 

    if not response or not isinstance(response, dict) or not isinstance(response.get('data'), list):
        print(f"AnonAddy: Lỗi khi kiểm tra inbox: {error}")
        return []
        
    formatted_messages = []
    for item in response['data']:
        msg = item.get('attributes', {})
        sender = msg.get('from', 'Người gửi ẩn danh')
        subject = msg.get('subject', 'Không có tiêu đề')
        body_snippet = msg.get('body', 'Không có nội dung').strip()
        if len(body_snippet) > 150:
            body_snippet = body_snippet[:150] + '...'
            
        formatted_messages.append({'from': sender, 'subject': subject, 'body': body_snippet})
            
    return formatted_messages

async def create_snailmail_email(user_id):
    username = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=10))
    domain = random.choice(SNAILMAIL_DOMAINS)
    email = f"{username}@{domain}"
    print(f"Tạo SnailMail thành công: {email}")
    return email, username, time.time() + DEFAULT_EXPIRY, domain, 'snailmail'

async def check_snailmail_inbox(user_id, username, domain):
    email = f"{username}@{domain}"
    url = f"{SNAILMAIL_API_BASE_URL}/messages?to={email}"
    response, error = await make_api_request(user_id, 'GET', url) 
    
    if not response or not isinstance(response, dict) or not isinstance(response.get('messages'), list):
        print(f"SnailMail: Lỗi khi kiểm tra inbox: {error}")
        return []
        
    formatted_messages = []
    for msg in response['messages']:
        sender = msg.get('from', 'Người gửi ẩn danh')
        subject = msg.get('subject', 'Không có tiêu đề')
        body_snippet = msg.get('text', 'Không có nội dung').strip()
        if len(body_snippet) > 150:
            body_snippet = body_snippet[:150] + '...'
            
        formatted_messages.append({'from': sender, 'subject': subject, 'body': body_snippet})
            
    return formatted_messages

async def create_dropmail_email(user_id):
    # Dropmail dùng GraphQL, tạo session và lấy email
    query = 'mutation {createSession {id, expiresAt, emails {address}}}'
    data = {'query': query}
    response, error = await make_api_request(user_id, 'POST', DROPMAIL_API_BASE_URL, data=json.dumps(data)) 
    
    if response and isinstance(response, dict) and response.get('data', {}).get('createSession'):
        session_data = response['data']['createSession']
        session_id = session_data['id']
        emails = session_data['emails']
        
        if emails:
            email = emails[0]['address']
            
            # Chuyển đổi thời gian expiresAt từ ISO 8601 sang timestamp
            try:
                # Định dạng thời gian Dropmail trả về
                dt_object = datetime.fromisoformat(session_data['expiresAt'].replace('Z', '+00:00'))
                expiry_time = dt_object.timestamp()
            except ValueError:
                expiry_time = time.time() + DEFAULT_EXPIRY 
            
            print(f"Tạo Dropmail thành công: {email}")
            return email, session_id, expiry_time, DROPMAIL_DOMAIN, 'dropmail'
        
    return None, error, None, None, 'dropmail'

async def check_dropmail_inbox(user_id, session_id):
    query = f"""
    query {{
      session(id: "{session_id}") {{
        mails {{
          fromAddr
          subject
          text
        }}
      }}
    }}
    """
    data = {'query': query}
    response, error = await make_api_request(user_id, 'POST', DROPMAIL_API_BASE_URL, data=json.dumps(data)) 

    if not response or not isinstance(response, dict) or not isinstance(response.get('data', {}).get('session', {}).get('mails'), list):
        print(f"Dropmail: Lỗi khi kiểm tra inbox: {error}")
        return []

    formatted_messages = []
    for msg in response['data']['session']['mails']:
        sender = msg.get('fromAddr', 'Người gửi ẩn danh')
        subject = msg.get('subject', 'Không có tiêu đề')
        body_snippet = msg.get('text', 'Không có nội dung').strip()
        if len(body_snippet) > 150:
            body_snippet = body_snippet[:150] + '...'
            
        formatted_messages.append({'from': sender, 'subject': subject, 'body': body_snippet})
            
    return formatted_messages

async def create_mintemail_email(user_id):
    username = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=10))
    email = f"{username}@{MINTEMAIL_DOMAIN}"
    print(f"Tạo MintEmail thành công: {email}")
    return email, username, time.time() + DEFAULT_EXPIRY, None, 'mintemail'

async def check_mintemail_inbox(user_id, username):
    url = f"{MINTEMAIL_API_BASE_URL}/check"
    params = {"email": f"{username}@{MINTEMAIL_DOMAIN}"}
    html_content, error = await make_api_request(user_id, 'GET', url, params=params) 

    if not html_content or not isinstance(html_content, str):
        print(f"MintEmail: Lỗi khi kiểm tra inbox (Text/HTML): {error}")
        return []

    messages = []
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        # MintEmail API trả về text, không phải HTML chuẩn
        if "No emails found" in html_content:
            return []
            
        # Tìm email IDs từ phản hồi text
        email_links = [line.split("mailId=")[-1].strip() for line in html_content.split('\n') if "mailId=" in line]

        for mail_id in email_links:
            messages.append({'from': 'MintEmail API', 'subject': f"Thư mới (ID: {mail_id})", 'body': 'Không thể trích xuất nội dung ngắn trong API đơn giản.'})
    except Exception as e:
        print(f"MintEmail: Lỗi parsing Text/HTML: {e}")
        return []
        
    return messages

async def create_hackermail_email(user_id):
    username = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=10))
    domain = random.choice(HACKERMAIL_DOMAINS)
    email = f"{username}@{domain}"
    print(f"Tạo HackerMail thành công: {email}")
    return email, username, time.time() + DEFAULT_EXPIRY, domain, 'hackermail'

async def check_hackermail_inbox(user_id, username, domain):
    email = f"{username}@{domain}"
    url = f"{HACKERMAIL_API_BASE_URL}/mailbox/{email}"
    response, error = await make_api_request(user_id, 'GET', url) 

    if not response or not isinstance(response, list):
        print(f"HackerMail: Lỗi khi kiểm tra inbox: {error}")
        return []
        
    formatted_messages = []
    for msg in response:
        sender = msg.get('from', 'Người gửi ẩn danh')
        subject = msg.get('subject', 'Không có tiêu đề')
        body_snippet = msg.get('body', 'Không có nội dung').strip()
        if len(body_snippet) > 150:
            body_snippet = body_snippet[:150] + '...'
            
        formatted_messages.append({'from': sender, 'subject': subject, 'body': body_snippet})
            
    return formatted_messages

# =================================================================
# 🔄 HÀM ROUND ROBIN VÀ CHECK INBOX CHUNG
# =================================================================

async def get_temp_email(user_id):
    """
    Sử dụng thuật toán Round Robin để chọn một dịch vụ email ảo ổn định
    và tạo email cho người dùng.
    """
    
    # Dùng user_id để tính toán index
    random.shuffle(API_PROVIDERS_LIST) 
    
    # Bắt đầu vòng lặp tìm kiếm
    for api_choice in API_PROVIDERS_LIST:
        
        email, session_id, expiry_time, account_id, provider = None, None, None, None, None

        
        # Logic tạo email cho 24 dịch vụ (Giữ nguyên)
        if api_choice == '1secmail':
            email, session_id, expiry_time, account_id, provider = await create_1secmail_email(user_id)
        elif api_choice == 'emailondeck':
            email, session_id, expiry_time, account_id, provider = await create_emailondeck_alt_email(user_id)
        elif api_choice == 'mailinator':
            email, session_id, expiry_time, account_id, provider = await create_mailinator_email(user_id)
        elif api_choice == 'dispostable':
            email, session_id, expiry_time, account_id, provider = await create_dispostable_email(user_id)
        elif api_choice == 'maildrop':
            email, session_id, expiry_time, account_id, provider = await create_maildrop_email(user_id)
        elif api_choice == 'mohmal':
            email, session_id, expiry_time, account_id, provider = await create_mohmal_email(user_id)
        elif api_choice == 'throwaway':
            email, session_id, expiry_time, account_id, provider = await create_throwaway_email(user_id)
        elif api_choice == 'emaily':
            email, session_id, expiry_time, account_id, provider = await create_emaily_email(user_id)
        elif api_choice == 'mailcatch':
            email, session_id, expiry_time, account_id, provider = await create_mailcatch_email(user_id)
        elif api_choice == 'getnada':
            email, session_id, expiry_time, account_id, provider = await create_getnada_email(user_id)
        elif api_choice == 'guerrillail':
            email, session_id, expiry_time, account_id, provider = await create_guerrillamail_email(user_id)
        elif api_choice == 'tempmailorg':
            email, session_id, expiry_time, account_id, provider = await create_tempmailorg_email(user_id)
        elif api_choice == 'yopmail':
            email, session_id, expiry_time, account_id, provider = await create_yopmail_email(user_id)
        elif api_choice == 'luxusmail':
            email, session_id, expiry_time, account_id, provider = await create_luxusmail_email(user_id)
        elif api_choice == 'tempmailnet':
            email, session_id, expiry_time, account_id, provider = await create_tempmailnet_email(user_id)
        elif api_choice == 'inboxalias':
            email, session_id, expiry_time, account_id, provider = await create_inboxalias_email(user_id)
        elif api_choice == 'mailnesia':
            email, session_id, expiry_time, account_id, provider = await create_mailnesia_email(user_id)
        elif api_choice == 'tmail':
            email, session_id, expiry_time, account_id, provider = await create_tmail_email(user_id)
        elif api_choice == 'bccto':
            email, session_id, expiry_time, account_id, provider = await create_bccto_email(user_id)
        elif api_choice == 'anonaddy':
            email, session_id, expiry_time, account_id, provider = await create_anonaddy_email(user_id)
        elif api_choice == 'snailmail':
            email, session_id, expiry_time, account_id, provider = await create_snailmail_email(user_id)
        elif api_choice == 'dropmail':
            email, session_id, expiry_time, account_id, provider = await create_dropmail_email(user_id)
        elif api_choice == 'mintemail':
            email, session_id, expiry_time, account_id, provider = await create_mintemail_email(user_id)
        elif api_choice == 'hackermail':
            email, session_id, expiry_time, account_id, provider = await create_hackermail_email(user_id)
        
        # Nếu email được tạo thành công
        if email:
            # Ghi vào active_emails (sử dụng email làm key)
            active_emails[email] = {
                'user_id': str(user_id),
                'session_id': session_id, 
                'account_id': account_id, 
                'provider': provider,
                'expires_at': expiry_time,
                'status': 'active'
            }
            # Lưu lại file
            await bot.loop.run_in_executor(THREAD_POOL_EXECUTOR, lambda: save_emails(active_emails))
            
            # Trả về kết quả
            return email, provider, session_id
        
        # Nếu tạo email thất bại, thử dịch vụ tiếp theo

    return None, None, None # Thất bại sau khi thử tất cả

async def check_inbox(user_id, email_data):
    """Gọi hàm kiểm tra hộp thư tương ứng với provider."""
    provider = email_data.get('provider')
    email = email_data.get('email')
    
    if not provider:
        return []
        
    # Phân tích cú pháp email
    if '@' in email:
        username, domain = email.split('@')
    else:
        username = email 
        domain = None
        
    # Lấy các giá trị đặc biệt
    session_id = email_data.get('session_id')
    account_id = email_data.get('account_id')

    # Logic kiểm tra inbox cho 24 dịch vụ (Giữ nguyên)
    if provider == '1secmail':
        return await check_1secmail_inbox(user_id, username, domain)
    elif provider == 'emailondeck':
        return await check_emailondeck_alt_inbox(user_id, session_id)
    elif provider == 'mailinator':
        return await check_mailinator_inbox(user_id, username)
    elif provider == 'dispostable':
        return await check_dispostable_inbox(user_id, username)
    elif provider == 'maildrop':
        return await check_maildrop_inbox(user_id, username)
    elif provider == 'mohmal':
        return await check_mohmal_inbox(user_id, username, domain)
    elif provider == 'throwaway':
        return await check_throwaway_inbox(user_id, session_id)
    elif provider == 'emaily':
        return await check_emaily_inbox(user_id, username)
    elif provider == 'mailcatch':
        return await check_mailcatch_inbox(user_id, username)
    elif provider == 'getnada':
        return await check_getnada_inbox(user_id, email)
    elif provider == 'guerrillail':
        return await check_guerrillamail_inbox(user_id, session_id)
    elif provider == 'tempmailorg':
        return await check_tempmailorg_inbox(user_id, username, domain)
    elif provider == 'yopmail':
        return await check_yopmail_inbox(user_id, username)
    elif provider == 'luxusmail':
        return await check_luxusmail_inbox(user_id, username, domain)
    elif provider == 'tempmailnet':
        return await check_tempmailnet_inbox(user_id, username, domain)
    elif provider == 'inboxalias':
        return await check_inboxalias_inbox(user_id, username)
    elif provider == 'mailnesia':
        return await check_mailnesia_inbox(user_id, username)
    elif provider == 'tmail':
        return await check_tmail_inbox(user_id, username, domain)
    elif provider == 'bccto':
        return await check_bccto_inbox(user_id, username, domain)
    elif provider == 'anonaddy':
        return await check_anonaddy_inbox(user_id, username, domain)
    elif provider == 'snailmail':
        return await check_snailmail_inbox(user_id, username, domain)
    elif provider == 'dropmail':
        return await check_dropmail_inbox(user_id, session_id)
    elif provider == 'mintemail':
        return await check_mintemail_inbox(user_id, username)
    elif provider == 'hackermail':
        return await check_hackermail_inbox(user_id, username, domain)
        
    return []

async def delete_account(email_data):
    """Xóa tài khoản dựa trên nhà cung cấp dịch vụ (Chỉ áp dụng cho các API cần Token)."""
    provider = email_data.get('provider')
    
    if provider == 'emailondeck':
        account_id = email_data.get('account_id')
        session_id = email_data.get('session_id') # session_id ở đây là JWT token
        await delete_emailondeck_alt_account(account_id, session_id)
    # Các dịch vụ khác không cần gọi delete API
    pass 

def generate_verification_code():
    return str(random.randint(100000, 999999))

def send_real_test_email_blocking(recipient_email):
    """Gửi email TEST thực tế qua SMTP (Blocking/Sync Version)."""
    # Kiểm tra mật khẩu mặc định/an toàn
    if not SENDER_PASSWORD or SENDER_PASSWORD.strip() == "": # Sửa kiểm tra, không dùng mật khẩu mặc định
        return None, "Lỗi cấu hình SMTP. Vui lòng đặt SENDER_PASSWORD và kiểm tra Mật khẩu Ứng dụng (App Password)."
    
    code = generate_verification_code()
    msg = EmailMessage()
    msg['Subject'] = f'Mã Xác Nhận TEST (Đừng dùng mã này): {code}'
    msg['From'] = SENDER_EMAIL
    msg['To'] = recipient_email
    
    body = f"""
    Xin chào,
    
    Đây là email thử nghiệm từ Bot Discord của bạn để kiểm tra tính năng email ảo.
    
    - Địa chỉ gửi đi (SMTP): {SENDER_EMAIL}
    - Địa chỉ nhận: {recipient_email}
    
    Nếu bạn thấy email này trong /checkemail, bot của bạn đang hoạt động tốt.
    
    Mã xác nhận TEST (Không dùng): {code}
    
    Trân trọng,
    Bot Discord Temp Mail
    """
    msg.set_content(body)

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as smtp:
            smtp.starttls()  # Bắt buộc cho Gmail
            smtp.login(SENDER_EMAIL, SENDER_PASSWORD)
            smtp.send_message(msg)
        return code, None
    except smtplib.SMTPAuthenticationError:
        return None, "Lỗi xác thực (SMTP Authentication Error). Kiểm tra lại Email/App Password SMTP."
    except smtplib.SMTPConnectError:
        return None, "Lỗi kết nối SMTP. Kiểm tra lại SMTP_SERVER và SMTP_PORT."
    except Exception as e:
        return None, f"Lỗi gửi email không xác định: {e}"

async def send_real_test_email(recipient_email):
    """Chạy hàm gửi email blocking trong executor."""
    return await bot.loop.run_in_executor(
        THREAD_POOL_EXECUTOR,
        lambda: send_real_test_email_blocking(recipient_email)
    )

# =================================================================
# 🤖 BOT EVENTS & LỆNH SLASH
# =================================================================

@bot.event
async def on_ready():
    """Xử lý khi Bot sẵn sàng."""
    print(f'🔥 Bot đã đăng nhập với tên: {bot.user}')
    
    # Tải Proxy trong background
    await bot.loop.run_in_executor(THREAD_POOL_EXECUTOR, fetch_and_test_proxies)

    # BẮT BUỘC: ĐỒNG BỘ HÓA TẤT CẢ LỆNH GLOBAL LÊN GUILD CỤ THỂ 
    try:
        # Đồng bộ hóa Guild cục bộ để apply các lệnh
        synced = await tree.sync(guild=discord.Object(id=GUILD_ID))
        print(f"✅ Đã đồng bộ hóa {len(synced)} lệnh Slash lên Guild ID: {GUILD_ID}")
        print(f"Danh sách lệnh: {[s.name for s in synced]}")
    except Exception as e:
        print(f"❌ Lỗi khi đồng bộ hóa lệnh Slash: {e}")
        
    mode_status = "PROXY & IP ROAMING" if ACTIVE_PROXIES else "IP GỐC (RỦI RO)"
    await bot.change_presence(activity=discord.Game(name=f"/getemail | {NUM_PROVIDERS} Dịch vụ | Cooldown {USER_COOLDOWN_SECONDS}s"))


# === LỆNH SLASH ĐƯỢC THÊM TRỰC TIẾP VÀO TREE ===

@tree.command(name='getemail', description=f'Tạo một email ảo mới. (Cooldown {USER_COOLDOWN_SECONDS}s)', guild=guild)
async def get_temp_email_slash(interaction: discord.Interaction):
    """Lệnh Slash tạo email ảo, tích hợp Cooldown cá nhân và Round Robin."""
    await interaction.response.defer(ephemeral=True) 
    user_id = interaction.user.id
    
    # 1. Kiểm tra Cooldown
    can_request, remaining_time = check_user_cooldown(user_id)
    if not can_request:
        await interaction.followup.send(f"⌛ Bạn phải chờ thêm **{remaining_time:.1f} giây** trước khi gọi lệnh API tiếp theo. (Bảo vệ IP)")
        return

    # 2. Kiểm tra email đang hoạt động
    existing_email_data = get_active_email(user_id)
    if existing_email_data:
        email = existing_email_data['email']
        provider = existing_email_data['provider'].upper()
        # Tính thời gian còn lại
        time_left_seconds = int(existing_email_data['expires_at'] - time.time())
        time_left_readable = str(timedelta(seconds=time_left_seconds)).split('.')[0]
        
        embed = discord.Embed(
            title="⚠️ | ĐÃ CÓ EMAIL ĐANG HOẠT ĐỘNG",
            description=f"Bạn đã có một email ảo đang hoạt động. Vui lòng sử dụng lệnh `/deleteemail` trước khi tạo mới.",
            color=0xF1C40F
        )
        embed.add_field(name="Địa chỉ Email", value=f"```fix\n{email}\n```", inline=False)
        embed.add_field(name="Nhà cung cấp", value=f"**{provider}**", inline=True)
        embed.add_field(name="Thời gian còn lại", value=f"**{time_left_readable}**", inline=True)
        await interaction.followup.send(embed=embed)
        return

    # 3. Tạo email mới và Cập nhật Cooldown
    update_user_cooldown(user_id)
    email, provider, session_id = await get_temp_email(user_id)

    # 4. Phản hồi
    if email:
        # Tính thời gian còn lại (Dùng DEFAULT_EXPIRY cho bot tự tính nếu API không trả về)
        if email in active_emails and active_emails[email].get('expires_at'):
            time_left_seconds = int(active_emails[email]['expires_at'] - time.time())
            time_left_readable = str(timedelta(seconds=time_left_seconds)).split('.')[0]
            expiry_note = f"Còn lại **{time_left_readable}** (Cho đến khi bạn dùng `/deleteemail` hoặc bot khởi động lại)."
        else:
             expiry_note = "Email sẽ tồn tại cho đến khi bạn dùng lệnh `/deleteemail` hoặc bot bị khởi động lại."
            
        embed = discord.Embed(
            title="📧 | TẠO EMAIL ẢO THÀNH CÔNG!",
            description=f"Địa chỉ email ảo mới đã được tạo cho bạn.",
            color=0x2ECC71
        )
        embed.add_field(name="Địa chỉ Email", value=f"```fix\n{email}\n```", inline=False)
        embed.add_field(name="Nhà cung cấp", value=f"**{provider.upper()}**", inline=True)
        embed.add_field(name="Hộp thư", value="Sử dụng lệnh `/checkemail`", inline=True)
        embed.add_field(name="Hết hạn", value=expiry_note, inline=False)
        embed.set_footer(text=f"Cooldown cá nhân: {USER_COOLDOWN_SECONDS} giây | Powered by {provider.upper()}")
        await interaction.followup.send(embed=embed)
    else:
        # Nếu thất bại, không cần cập nhật Cooldown nữa (vì đã cập nhật ở trên)
        # Bắt buộc phải lưu lại active_emails, nếu không có thể bị mất trạng thái
        await bot.loop.run_in_executor(THREAD_POOL_EXECUTOR, lambda: save_emails(active_emails))

        detailed_error = session_id if session_id else "Lỗi kết nối API không xác định."

        embed = discord.Embed(
            title=f"❌ | THÔNG BÁO LỖI KHẨN CẤP (Dịch vụ: {provider.upper() if provider else 'N/A'})",
            description="Bot không thể tạo email mới sau lần thử. (Lỗi API của dịch vụ được chỉ định)",
            color=0xE74C3C
        )
        embed.add_field(name="Chi tiết Lỗi Lần Cuối", value=f"```❌ Lỗi cuối: {detailed_error}```", inline=False)
        await interaction.followup.send(embed=embed)


@tree.command(name='checkemail', description=f'Kiểm tra hộp thư của email ảo đã tạo. (Cooldown {USER_COOLDOWN_SECONDS}s)', guild=guild)
async def check_email_inbox_slash(interaction: discord.Interaction):
    """Lệnh Slash kiểm tra hộp thư email ảo."""
    user_id = interaction.user.id
    
    can_request, remaining_time = check_user_cooldown(user_id)
    if not can_request:
        await interaction.response.send_message(f"⌛ Bạn phải chờ thêm **{remaining_time:.1f} giây** trước khi gọi lệnh API tiếp theo. (Bảo vệ IP)", ephemeral=True)
        return
        
    email_data = get_active_email(user_id)
    if not email_data:
        await interaction.response.send_message("❌ Email ảo của bạn đã **HẾT HẠN** hoặc chưa được tạo. Vui lòng tạo email mới bằng lệnh `/getemail`.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    update_user_cooldown(user_id)
    
    email = email_data['email']
    provider = email_data['provider']
    
    messages = await check_inbox(user_id, email_data)

    embed = discord.Embed(
        title=f"📥 | HỘP THƯ EMAIL: {mask_email(email)}",
        description=f"**Nhà cung cấp:** `{provider.upper()}`\n**Trạng thái:** Tìm thấy **{len(messages)}** thư mới.",
        color=0x3498DB
    )
    
    if not messages:
        embed.add_field(name="Hộp thư trống!", value="Không tìm thấy thư mới nào trong hộp thư của bạn.", inline=False)
    else:
        # Hiển thị tối đa 5 thư
        for i, msg in enumerate(messages[:5]):
            body_snippet = msg['body'].replace('\n', ' ').strip()
            if len(body_snippet) > 150:
                body_snippet = body_snippet[:150] + '...'
            
            embed.add_field(
                name=f"✉️ {i+1}. Từ: {msg['from']}",
                value=f"**Tiêu đề:** `{msg['subject']}`\n**Nội dung:** *{body_snippet}*",
                inline=False
            )
        if len(messages) > 5:
            embed.set_footer(text=f"Đã hiển thị 5/{len(messages)} thư. Vui lòng kiểm tra trên web để xem toàn bộ.")

    await interaction.followup.send(embed=embed)


@tree.command(name='deleteemail', description='Xóa email ảo hiện tại của bạn.', guild=guild)
async def delete_temp_email_slash(interaction: discord.Interaction):
    """Lệnh Slash xóa email ảo."""
    user_id = interaction.user.id
    email_data = get_active_email(user_id)
    
    if not email_data:
        await interaction.response.send_message("❌ Bạn không có email ảo nào đang hoạt động.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    
    email = email_data['email']
    provider = email_data['provider']
    
    # 1. Gọi hàm xóa API (nếu có)
    await delete_account(email_data)
    
    # 2. Xóa khỏi dictionary và lưu file
    if email in active_emails:
        del active_emails[email]
    
    await bot.loop.run_in_executor(THREAD_POOL_EXECUTOR, lambda: save_emails(active_emails))

    embed = discord.Embed(
        title="🗑️ | ĐÃ XÓA EMAIL THÀNH CÔNG!",
        description=f"Địa chỉ email **`{mask_email(email)}`** của nhà cung cấp **{provider.upper()}** đã bị xóa khỏi hệ thống.",
        color=0xE74C3C
    )
    embed.add_field(name="Lưu ý", value="Địa chỉ này không còn được theo dõi. Các thư cũ có thể vẫn tồn tại trên máy chủ của nhà cung cấp dịch vụ trong một thời gian ngắn.", inline=False)
    
    await interaction.followup.send(embed=embed)


@tree.command(name='testemail', description='Gửi email test từ Gmail thật đến email ảo của bạn.', guild=guild)
async def send_test_email_slash(interaction: discord.Interaction):
    """Lệnh Slash gửi email test thật."""
    user_id = interaction.user.id
    email_data = get_active_email(user_id)
    
    if not email_data:
        await interaction.response.send_message("❌ Vui lòng tạo email ảo bằng lệnh `/getemail` trước khi gửi email test.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    recipient_email = email_data['email']
    provider = email_data['provider'].upper()
    
    # Gửi email test (chạy trong Thread)
    code, error = await send_real_test_email(recipient_email)
    
    if code:
        embed = discord.Embed(
            title="📧 | ĐÃ GỬI EMAIL TEST THÀNH CÔNG!",
            description=f"Đã gửi một email test từ **`{SENDER_EMAIL}`** đến email ảo của bạn.",
            color=0x3498DB
        )
        embed.add_field(
            name="Địa chỉ Nhận", 
            value=f"**{recipient_email}** (Provider: {provider})", 
            inline=false
        )
        embed.add_field(
            name="Bước tiếp theo", 
            value="Bạn vui lòng chờ khoảng 10-30 giây, sau đó sử dụng lệnh `/checkemail` để xác nhận bot đã nhận được thư.", 
            inline=false
        )
        embed.set_footer(text="Mã xác nhận 6 chữ số đã được gửi đi.")
        await interaction.followup.send(embed=embed)
    else:
        embed = discord.Embed(
            title="❌ | THÔNG BÁO LỖI KHẨN CẤP",
            description=f"Bot không thể gửi email test do **Lỗi Xác thực/Kết nối SMTP.**",
            color=0xE74C3C
        )
        embed.add_field(name="Chi tiết Lỗi", value=f"```Lỗi cấu hình SMTP. {error}```", inline=false)
        await interaction.followup.send(embed=embed)


@tree.command(name='providers', description=f'Xem danh sách 24 nhà cung cấp dịch vụ email ảo hiện tại.', guild=guild)
async def show_providers_slash(interaction: discord.Interaction):
    """Hiển thị danh sách các nhà cung cấp dịch vụ đang hoạt động."""
    # Phân nhóm các dịch vụ để hiển thị chi tiết hơn
    provider_details = {
        '1secmail': 'API nhanh, nhiều domain thay thế.',
        'getnada': 'API ổn định, tốc độ tốt.',
        'anonaddy': 'Dịch vụ nâng cao (Alt API).',
        'emailondeck': 'Dịch vụ nâng cao (Alt API).',
        'mailinator': 'Phổ biến, chỉ check được tiêu đề và người gửi.',
        'guerrillail': 'Phổ biến, API cũ, chỉ check được tiêu đề/người gửi.',
        'dispostable': 'API ổn định, hỗ trợ trích dẫn ngắn.',
        'maildrop': 'API ổn định, hỗ trợ trích dẫn ngắn.',
        'mohmal': 'API nhanh, nhiều domain thay thế.',
        'throwaway': 'API nhanh, thời gian sống ngắn.',
        'emaily': 'API ổn định, trích dẫn ngắn.',
        'luxusmail': 'API ổn định, trích dẫn ngắn.',
        'tempmailnet': 'API ổn định, trích dẫn ngắn.',
        'inboxalias': 'API ổn định, trích dẫn ngắn.',
        'tmail': 'API ổn định, nhiều domain thay thế.',
        'bccto': 'API ổn định, nhiều domain thay thế.',
        'snailmail': 'API ổn định, trích dẫn ngắn.',
        'dropmail': 'GraphQL API nâng cao.',
        'hackermail': 'API ổn định, nhiều domain thay thế.',
        'mailcatch': 'Scraping HTML, tốc độ chậm.',
        'yopmail': 'Scraping HTML, tốc độ chậm.',
        'mailnesia': 'Scraping HTML, tốc độ chậm.',
        'mintemail': 'Scraping HTML, tốc độ chậm.'
    }
    
    col_size = 6
    columns = [API_PROVIDERS_LIST[i:i + col_size] for i in range(0, NUM_PROVIDERS, col_size)]
    
    embed = discord.Embed(
        title=f"🌐 | DANH SÁCH {NUM_PROVIDERS} NHÀ CUNG CẤP DỊCH VỤ EMAIL ẢO",
        description="Bot sử dụng cơ chế **Round Robin** để luân phiên 24 dịch vụ này, kết hợp với **Proxy Roaming** để đảm bảo khả năng chống chặn IP tối đa.",
        color=0x9B59B6
    )

    for i, column in enumerate(columns):
        field_name = f"Dịch Vụ (Cột {i+1})"
        field_value = ""
        for provider in column:
            detail = provider_details.get(provider, "Dịch vụ phụ trợ.")
            field_value += f"**- {provider.upper()}**: *{detail}*\\n"
        embed.add_field(name=field_name, value=field_value, inline=True)
        
    embed.add_field(
        name="🛡️ Cơ Chế Phòng Thủ IP Cao Cấp (V12.2)",
        value=f"Các dịch vụ **Scraping (HTML)** được ưu tiên sử dụng Proxy mới liên tục để tránh bị chặn IP gốc, giúp duy trì tính năng **`/checkemail`** bền bỉ hơn.",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)


# =================================================================
# 🚀 KHỞI CHẠY BOT
# =================================================================

if __name__ == '__main__':
    # Bắt buộc phải có TOKEN để chạy
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("Bot không thể khởi động do thiếu Token Discord.")
