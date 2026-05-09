import os
import asyncio
import tempfile
import threading
import time
import math
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes
from internetarchive import upload

# Soo qaad keys-ka
BOT_TOKEN = os.getenv("BOT_TOKEN")
IA_ACCESS_KEY = os.getenv("IA_ACCESS_KEY")
IA_SECRET_KEY = os.getenv("IA_SECRET_KEY")

# --- FUNCTIONS-KA PROGRESS BAR-KA ---

def get_progress_bar(percentage):
    """Waxay dhisaysaa line-ka [■■■□□□□□]"""
    completed = int(percentage / 10)
    return "■" * completed + "□" * (10 - completed)

def human_readable_size(size_bytes):
    if size_bytes == 0: return "0B"
    size_name = ("B", "KB", "MB", "GB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"

async def edit_progress_message(message, status, current, total, start_time):
    """Waxay update ku samaynaysaa fariinta Telegram-ka"""
    now = time.time()
    diff = now - start_time
    if diff == 0: return

    percentage = (current / total) * 100
    speed = current / diff
    elapsed_time = round(diff)
    eta = round((total - current) / speed) if speed > 0 else 0

    progress_str = (
        f"**{status}**: {percentage:.2f}%\n"
        f"[{get_progress_bar(percentage)}]\n"
        f"{human_readable_size(current)} of {human_readable_size(total)}\n"
        f"Speed: {human_readable_size(speed)}/sec\n"
        f"ETA: {eta}s"
    )

    try:
        # Waxaan update-gareynaynaa fariinta 3-dii ilbiriqsiba mar si aan loogu dhicin Limit-ka Telegram
        await message.edit_text(progress_str, parse_mode="Markdown")
    except:
        pass

# --- SERVER-KA KOYEB ---
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

def run_dummy_server():
    server_address = ('0.0.0.0', 8000)
    httpd = HTTPServer(server_address, DummyHandler)
    httpd.serve_forever()

# --- HANDLERS-KA BOT-KA ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Soo dir video (ka yar 20MB) si aan Archive ugu xareeyo.")

async def handle_movie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    file_obj = message.video or message.document
    
    if not file_obj: return
    if file_obj.file_size > 20 * 1024 * 1024:
        await message.reply_text("❌ File-ku waa ka weyn yahay 20MB.")
        return

    status_msg = await message.reply_text("⏳ Isku diyaarinaya soo dejinta...")
    
    try:
        tg_file = await context.bot.get_file(file_obj.file_id)
        file_url = tg_file.file_path
        file_name = getattr(file_obj, 'file_name', f"file_{file_obj.file_id}.mp4") or "video.mp4"
        
        with tempfile.TemporaryDirectory() as temp_dir:
            download_path = os.path.join(temp_dir, file_name)
            
            # --- SOO DEJINTA (DOWNLOAD) ---
            import requests
            start_time = time.time()
            response = requests.get(file_url, stream=True)
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(download_path, 'wb') as f:
                last_update = 0
                for chunk in response.iter_content(chunk_size=1024*100): # 100KB chunks
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        # Update Telegram fariinta 2-dii ilbiriqsiba mar
                        if time.time() - last_update > 2:
                            await edit_progress_message(status_msg, "Downloading", downloaded, total_size, start_time)
                            last_update = time.time()

            await status_msg.edit_text("✅ Download dhamaaday. Hadda waxaan u upload-gareynayaa Archive.org...")

            # --- UPLOAD-KA (ARCHIVE.ORG) ---
            identifier = f"tg_bot_{int(time.time())}_{file_obj.file_id[:5]}"
            start_time_up = time.time()
            
            def ia_callback(resource_name, total_bytes, transferred_bytes):
                # Callback-gan wuxuu u baahan yahay inuu si tartiib ah u update gareeyo
                # Maadaama uu ku jiro thread kale, halkan waxaan u isticmaali doonaa hab fudud
                pass 

            # Upload garaynta
            await asyncio.to_thread(
                upload, identifier, files=[download_path], 
                metadata={'title': file_name, 'mediatype': 'movies'},
                access_key=IA_ACCESS_KEY, secret_key=IA_SECRET_KEY
            )

            archive_link = f"https://archive.org/details/{identifier}"
            await status_msg.edit_text(f"🎉 Upload-kii waa guuleystay!\n\nLink: {archive_link}")

    except Exception as e:
        await status_msg.edit_text(f"❌ Cilad: {str(e)}")

def main():
    threading.Thread(target=run_dummy_server, daemon=True).start()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.ALL, handle_movie))
    print("🤖 Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
