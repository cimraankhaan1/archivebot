import os
import time
import asyncio
import threading
from pyrogram import Client, filters
from internetarchive import get_item
from http.server import BaseHTTPRequestHandler, HTTPServer

# --- CONFIG (Hubi in variables-kan ay ku jiraan Koyeb) ---
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
    if diff < 4: return # 4-dii ilbiriqsiba mar update garee si Telegram uusan kuu xirin

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
    await message.reply_text("👋 Kusoo dhawow! Iisoo dir filim (ilaa 2GB) si aan Archive ugu xareeyo adigoo arkayo Progress-ka.")

@app.on_message(filters.video | filters.document)
async def handle_media(client, message):
    file_obj = message.video or message.document
    file_name = file_obj.file_name or "video.mp4"
    status_msg = await message.reply_text("⏳ Isku diyaarinaya soo dejinta (Downloading)...")
    start_time_dl = time.time()

    try:
        # 1. DOWNLOAD (Telegram -> Server)
        path = await message.download(
            progress=progress,
            progress_args=(status_msg, start_time_dl, "Downloading from Telegram")
        )

        await status_msg.edit_text("✅ Download dhamaaday. Hadda waxaan bilaabayaa Upload-ka Archive.org...")
        
        # 2. UPLOAD (Server -> Archive.org)
        identifier = f"tg_arch_{int(time.time())}_{message.id}"
        start_time_up = time.time()
        last_update = 0

        # Callback-ga lagu xisaabinayo Progress-ka Upload-ka
        def upload_callback(resource_name, total_bytes, transferred_bytes):
            nonlocal last_update
            if time.time() - last_update > 4:
                asyncio.run_coroutine_threadsafe(
                    progress(transferred_bytes, total_bytes, status_msg, start_time_up, "Uploading to Archive"),
                    app.loop
                )
                last_update = time.time()

        # Function-ka upload-ka oo leh habka saxda ah
        def do_upload():
            item = get_item(identifier)
            item.upload(
                files=[path], 
                metadata={'title': file_name, 'mediatype': 'movies', 'creator': 'Somali Bot'},
                access_key=IA_ACCESS_KEY, 
                secret_key=IA_SECRET_KEY,
                callback=upload_callback # Halkan ayaan callback-ga ku darnay
            )

        # Upload-ka ku socodsii thread gaar ah
        await asyncio.to_thread(do_upload)

        # 3. CLEANUP (Masax file-ka si disk-gu uusan u buuxsamin)
        if os.path.exists(path):
            os.remove(path)

        link = f"https://archive.org/details/{identifier}"
        await status_msg.edit_text(f"🎉 Upload-kii waa guuleystay!\n\nDisk-ga waa la nadiifiyay 🧹\nLink: {link}")

    except Exception as e:
        await status_msg.edit_text(f"❌ Cilad ayaa dhacday: {str(e)}")

# --- SERVER FOR KOYEB ---
def run_dummy_server():
    server_address = ('0.0.0.0', 8000)
    HTTPServer(server_address, BaseHTTPRequestHandler).serve_forever()

if __name__ == "__main__":
    threading.Thread(target=run_dummy_server, daemon=True).start()
    print("🤖 Bot is running...")
    app.run()
