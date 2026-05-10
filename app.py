import os
import time
import asyncio
import threading
from pyrogram import Client, filters, errors
from internetarchive import get_item
from http.server import BaseHTTPRequestHandler, HTTPServer

# --- CONFIG ---
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
IA_ACCESS_KEY = os.getenv("IA_ACCESS_KEY")
IA_SECRET_KEY = os.getenv("IA_SECRET_KEY")

app = Client("archive_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# --- PROGRESS BAR HELPER ---
async def progress(current, total, message, start_time, status):
    now = time.time()
    # Aad u muhiim: 15 ilbiriqsi kasta oo kaliya edit samee si Telegram uusan kuu xannibin
    last_edit = getattr(message, "last_edit_time", 0)
    if now - last_edit < 15: 
        return

    percentage = current * 100 / total
    speed = current / (now - start_time) if (now - start_time) > 0 else 0
    eta = round((total - current) / speed) if speed > 0 else 0
    
    completed = int(percentage / 10)
    bar = "■" * completed + "□" * (10 - completed)
    
    progress_str = (
        f"**{status}**: {percentage:.2f}%\n"
        f"[{bar}]\n"
        f"{current/1024/1024:.2f} MB of {total/1024/1024:.2f} MB\n"
        f"Speed: {speed/1024/1024:.2f} MB/sec\n"
        f"ETA: {eta}s"
    )
    
    try:
        await message.edit_text(progress_str)
        message.last_edit_time = now # Keydi waqtigii u dambeeyay ee la edit gareeyay
    except errors.FloodWait as e:
        # Haddii Telegram ay na dhahdo sug, waan sugeynaa inta ay na dhahdo
        await asyncio.sleep(e.value)
    except Exception:
        pass

# --- HANDLERS ---
@app.on_message(filters.video | filters.document)
async def handle_media(client, message):
    file_obj = message.video or message.document
    file_name = file_obj.file_name or "video.mp4"
    status_msg = await message.reply_text("⏳ Isku diyaarinaya soo dejinta (Downloading)...")
    status_msg.last_edit_time = time.time()
    start_time_dl = time.time()

    try:
        # 1. DOWNLOAD
        path = await message.download(
            progress=progress,
            progress_args=(status_msg, start_time_dl, "Downloading")
        )

        await status_msg.edit_text("✅ Download dhamaaday. Hadda waxaan u upload-gareynayaa Archive.org...")
        
        # 2. UPLOAD (ARCHIVE.ORG)
        identifier = f"tg_arch_{int(time.time())}_{message.id}"
        start_time_up = time.time()
        last_up_time = 0

        def upload_callback(resource_name, total_bytes, transferred_bytes):
            nonlocal last_up_time
            now = time.time()
            if now - last_up_time > 15:
                asyncio.run_coroutine_threadsafe(
                    progress(transferred_bytes, total_bytes, status_msg, start_time_up, "Uploading to Archive"),
                    app.loop
                )
                last_up_time = now

        def do_upload():
            item = get_item(identifier)
            item.upload(
                files=[path], 
                metadata={'title': file_name, 'mediatype': 'movies', 'creator': 'Somali Bot'},
                access_key=IA_ACCESS_KEY, 
                secret_key=IA_SECRET_KEY,
                callback=upload_callback
            )

        await asyncio.to_thread(do_upload)

        if os.path.exists(path):
            os.remove(path)

        link = f"https://archive.org/details/{identifier}"
        await status_msg.edit_text(f"🎉 Upload-kii waa guuleystay!\n\nLink: {link}")

    except Exception as e:
        print(f"Error: {e}")
        try:
            await status_msg.edit_text(f"❌ Cilad ayaa dhacday. Isku day mar kale dhowr daqiiqo ka dib.")
        except:
            pass

# --- KOYEB SERVER FIXED ---
class KoyebHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is Alive")

    def do_HEAD(self): # Tani waxay xallineysaa Error 501 ee logs-kaaga
        self.send_response(200)
        self.end_headers()

def run_dummy_server():
    server_address = ('0.0.0.0', 8000)
    HTTPServer(server_address, KoyebHandler).serve_forever()

if __name__ == "__main__":
    threading.Thread(target=run_dummy_server, daemon=True).start()
    app.run()
