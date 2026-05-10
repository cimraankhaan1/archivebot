import os
import time
import asyncio
import threading
from pyrogram import Client, filters, errors
from internetarchive import upload
from http.server import BaseHTTPRequestHandler, HTTPServer

# --- CONFIG ---
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
IA_ACCESS_KEY = os.getenv("IA_ACCESS_KEY")
IA_SECRET_KEY = os.getenv("IA_SECRET_KEY")

app = Client("archive_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# --- PROGRESS BAR HELPER (DOWNLOAD KALIYA) ---
async def progress(current, total, message, start_time, status):
    now = time.time()
    
    # 10-kii ilbiriqsiba mar update garee si looga fogaado Flood Wait
    last_edit = getattr(message, "last_edit_time", 0)
    if now - last_edit < 10:
        return

    percentage = current * 100 / total
    elapsed_time = now - start_time
    speed = current / elapsed_time if elapsed_time > 0 else 0
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
        message.last_edit_time = now
    except errors.FloodWait as e:
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
        # 1. DOWNLOAD (Progress bar-ka halkan ayuu ka muuqanayaa)
        path = await message.download(
            progress=progress,
            progress_args=(status_msg, start_time_dl, "Downloading")
        )

        # Markay soo dhamaato edit ka dhig fariin ah in upload la bilaabay
        await status_msg.edit_text("✅ Download dhamaaday. Hadda waxaan u upload-gareynayaa Archive.org... (Fadlan sug, kani Progress ma laha)")

        # 2. UPLOAD (BACKGROUND - Ma laha Progress Bar si uusan Error u bixin)
        identifier = f"tg_arch_{int(time.time())}_{message.id}"
        
        metadata = {
            'title': file_name,
            'mediatype': 'movies',
            'creator': 'Telegram Bot'
        }

        def do_upload():
            upload(
                identifier, 
                files=[path], 
                metadata=metadata,
                access_key=IA_ACCESS_KEY, 
                secret_key=IA_SECRET_KEY
            )

        # Upload-ka halkan ka bilow
        await asyncio.to_thread(do_upload)

        # 3. CLEANUP (Masax file-ka)
        if os.path.exists(path):
            os.remove(path)

        link = f"https://archive.org/details/{identifier}"
        await status_msg.edit_text(f"🎉 Upload-kii waa guuleystay!\n\nLink: {link}")

    except Exception as e:
        error_msg = str(e)
        print(f"Error: {error_msg}")
        try:
            await status_msg.edit_text(f"❌ Cilad ayaa dhacday:\n`{error_msg}`")
        except:
            pass

# --- KOYEB SERVER FIXED ---
class KoyebHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is Healthy")
    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

def run_dummy_server():
    server_address = ('0.0.0.0', 8000)
    httpd = HTTPServer(server_address, KoyebHandler)
    httpd.serve_forever()

if __name__ == "__main__":
    threading.Thread(target=run_dummy_server, daemon=True).start()
    app.run()
