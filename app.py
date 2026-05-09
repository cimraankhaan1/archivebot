import os
import asyncio
import tempfile
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes
from internetarchive import upload

# Soo qaad keys-ka
BOT_TOKEN = os.getenv("BOT_TOKEN")
IA_ACCESS_KEY = os.getenv("IA_ACCESS_KEY")
IA_SECRET_KEY = os.getenv("IA_SECRET_KEY")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Kusoo dhawow Bot-ka ugu fiican ee Koyeb ku shaqeeya!\n\n"
        "Fadlan ii soo dir Filim (Video) ama Document (ka yar 20MB) si aan ugu xareeyo Archive.org."
    )

async def handle_movie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    
    if message.video:
        file_obj = message.video
    elif message.document:
        file_obj = message.document
    else:
        return

    # Hubi xajmiga (20MB limit)
    if file_obj.file_size > 20 * 1024 * 1024:
        await message.reply_text("❌ Cilad: File-ku wuxuu ka weyn yahay 20MB. Telegram Bot API-ga caadiga ah ma ogola.")
        return

    await message.reply_text("⏳ Waan helay file-ka. Waxaan bilaabayaa soo dejinta (Downloading)...")

    try:
        telegram_file = await context.bot.get_file(file_obj.file_id)
        file_name = file_obj.file_name if hasattr(file_obj, 'file_name') and file_obj.file_name else f"movie_{file_obj.file_id}.mp4"
        
        with tempfile.TemporaryDirectory() as temp_dir:
            download_path = os.path.join(temp_dir, file_name)
            await telegram_file.download_to_drive(download_path)
            
            await message.reply_text("✅ Soo dejintu way dhamaatay. Waxaan u wareejinayaa Archive.org 📤...\n(Fadlan sug, tani wax yar ayay qaadan kartaa)")

            identifier = f"tg_bot_movie_{file_obj.file_id}" 
            
            metadata = {
                'title': file_name,
                'mediatype': 'movies',
                'description': 'Filimkan waxaa lagu soo upload-gareeyay Telegram Bot Koyeb.',
                'creator': 'Somali Telegram Bot'
            }

            # Upload-ka u dir Thread kale si bot-ku uusan u xanibmin
            def do_upload():
                upload(
                    identifier, 
                    files=[download_path], 
                    metadata=metadata,
                    access_key=IA_ACCESS_KEY, 
                    secret_key=IA_SECRET_KEY,
                    verbose=True
                )

            await asyncio.to_thread(do_upload)

            archive_link = f"https://archive.org/details/{identifier}"
            await message.reply_text(f"🎉 Upload-kii waa guuleystay!\n\nHalkan ka daawo ama kala deg:\n{archive_link}")

    except Exception as e:
        await message.reply_text(f"❌ Cilad ayaa dhacday:\n{str(e)}")

def main():
    if not BOT_TOKEN or not IA_ACCESS_KEY or not IA_SECRET_KEY:
        print("⚠️ FADLAN Geli BOT_TOKEN, IA_ACCESS_KEY, iyo IA_SECRET_KEY Koyeb Environment Variables-ka!")
        return

    print("🤖 Bot-ku Koyeb ayuu ka shidmay oo wuu shaqeynayaa...")
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.ALL, handle_movie))
    
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == "__main__":
    main()
