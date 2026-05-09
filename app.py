import os
import time
import asyncio
import threading
from pyrogram import Client, filters
from internetarchive import upload
from http.server import BaseHTTPRequestHandler, HTTPServer

# --- CONFIG ---
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
IA_ACCESS_KEY = os.getenv("IA_ACCESS_KEY")
IA_SECRET_KEY = os.getenv("IA_SECRET_KEY")

app = Client("archive_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# --- PROGRESS BAR HELPER (DOWNLOAD & UPLOAD) ---
async def progress(current, total, message, start_time, status):
    now = time.time()
    diff = now - start_time
    if diff < 3: return # 3-dii ilbiriqsiba mar update garee si aan laguu xirin

    percentage = current * 100 / total
    speed = current / diff
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
    except:
        pass

# --- HANDLERS ---
@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply_text("👋 Iisoo dir filim si aan Archive ugu xareeyo Progress Bar-na aan kuu tusiyo!")

@app.on_message(filters.video | filters.document)
async def handle_media(client, message):
    file_obj = message.video or message.document
    file_name = file_obj.file_name or "video.mp4"
    status_msg = await message.reply_text("⏳ Isku diyaarinaya soo dejinta...")
    start_time_dl = time.time()

    try:
        # 1. DOWNLOAD PROGRESS-KII HORE
        path = await message.download(
            progress=progress,
            progress_args=(status_msg, start_time_dl, "Downloading")
        )

        await status_msg.edit_text("✅ Download dhamaaday. Isku diyaarinaya Upload-ka...")
        
        # 2. UPLOAD PROGRESS (ARCHIVE.ORG)
        identifier = f"tg_arch_{int(time.time())}"
        start_time_up = time.time()
        last_update = 0

        # Callback function for Archive.org upload
        def upload_callback(resource_name, total_bytes, transferred_bytes):
            nonlocal last_update
            # Si aan fariinta Telegram-ka loo update-gareyn mar walba (waa inuu 3s ka badnaadaa)
            if time.time() - last_update > 3:
                # Maadaama callback-gu uusan ahayn Async, waxaan isticmaalaynaa loop-ka bot-ka
                asyncio.run_coroutine_threadsafe(
                    progress(transferred_bytes, total_bytes, status_msg, start_time_up, "Uploading to Archive"),
                    app.loop
                )
                last_update = time.time()

        # Upload-ka u dir thread kale si bot-ku uusan u istaagin
        def do_upload():
            upload(identifier, files=[path], 
                   metadata={'title': file_name, 'mediatype': 'movies'},
                   access_key=IA_ACCESS_KEY, secret_key=IA_SECRET_KEY,
                   callback=upload_callback) # Halkaan ayaan callback-ga ku darnay

        await asyncio.to_thread(do_upload)

        # 3. CLEANUP
        if os.path.exists(path):
            os.remove(path)

        link = f"https://archive.org/details/{identifier}"
        await status_msg.edit_text(f"🎉 Upload-kii waa guuleystay!\n\nLink: {link}")

    except Exception as e:
        await status_msg.edit_text(f"❌ Cilad: {str(e)}")

# --- SERVER ---
def run_dummy_server():
    server_address = ('0.0.0.0', 8000)
    HTTPServer(server_address, BaseHTTPRequestHandler).serve_forever()

if __name__ == "__main__":
    threading.Thread(target=run_dummy_server, daemon=True).start()
    app.run()
