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

# --- PROGRESS BAR HELPER ---
async def progress(current, total, message, start_time, status):
    now = time.time()
    diff = now - start_time
    if diff < 2: return # Update 2-dii ilbiriqsiba mar si aan bot-ka loo xiran

    percentage = current * 100 / total
    speed = current / diff
    eta = round((total - current) / speed) if speed > 0 else 0
    
    # Progress Bar [■■■□□]
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
    await message.reply_text("👋 Kusoo dhawow Bot-ka! Iisoo dir filim (ilaa 2GB) si aan Archive ugu xareeyo.")

@app.on_message(filters.video | filters.document)
async def handle_media(client, message):
    file_obj = message.video or message.document
    file_name = file_obj.file_name or "video.mp4"
    
    status_msg = await message.reply_text("⏳ Isku diyaarinaya soo dejinta...")
    start_time = time.time()

    try:
        # 1. DOWNLOAD (ilaa 2GB)
        path = await message.download(
            progress=progress,
            progress_args=(status_msg, start_time, "Downloading")
        )

        await status_msg.edit_text("✅ Download dhamaaday. Hadda waxaan u upload-gareynayaa Archive.org... (Fadlan sug)")

        # 2. UPLOAD TO ARCHIVE
        # Waxaan identifier-ka ka dhigaynaa mid gaar ah
        identifier = f"tg_archive_{int(time.time())}_{message.id}"
        
        metadata = {
            'title': file_name,
            'mediatype': 'movies',
            'creator': 'Telegram Archive Bot'
        }

        # Upload-ka u dir thread kale
        def do_upload():
            upload(identifier, files=[path], 
                   metadata=metadata,
                   access_key=IA_ACCESS_KEY, 
                   secret_key=IA_SECRET_KEY)

        await asyncio.to_thread(do_upload)

        # 3. CLEANUP (Nadiifi Disk-ga)
        if os.path.exists(path):
            os.remove(path)

        link = f"https://archive.org/details/{identifier}"
        await status_msg.edit_text(f"🎉 Upload-kii waa guuleystay!\n\nLink: {link}")

    except Exception as e:
        await status_msg.edit_text(f"❌ Cilad: {str(e)}")

# --- KOYEB SERVER ---
def run_dummy_server():
    server_address = ('0.0.0.0', 8000)
    httpd = HTTPServer(server_address, BaseHTTPRequestHandler)
    httpd.serve_forever()

if __name__ == "__main__":
    threading.Thread(target=run_dummy_server, daemon=True).start()
    print("🤖 Bot is running...")
    app.run()
