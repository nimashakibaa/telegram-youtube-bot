import os
import json
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# جایگزین توکن خودت کن
TELEGRAM_BOT_TOKEN = "7906093779:AAFGQWU1RcE110iXwZvJdrsn4iwLMXrc5e0"
YOUTUBE_API_KEY = "AIzaSyDu42N1sfyMognq102zaJC-AEfJlgIgB9Q"

CHANNELS_FILE = "channels.json"

def load_channels():
    if not os.path.exists(CHANNELS_FILE):
        return []
    with open(CHANNELS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_channels(channels):
    with open(CHANNELS_FILE, "w", encoding="utf-8") as f:
        json.dump(channels, f, ensure_ascii=False, indent=2)

async def get_latest_videos(channel_id, max_results=5):
    import httpx
    url = (
        f"https://www.googleapis.com/youtube/v3/search?"
        f"key={YOUTUBE_API_KEY}&channelId={channel_id}&part=snippet,id&order=date&maxResults={max_results}"
    )
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        if response.status_code != 200:
            return []
        data = response.json()
        videos = []
        for item in data.get("items", []):
            if item["id"]["kind"] == "youtube#video":
                videos.append({
                    "videoId": item["id"]["videoId"],
                    "title": item["snippet"]["title"],
                })
        return videos

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "/addchannel <ChannelID> - اضافه کردن یک کانال جدید\n"
        "/removechannel <شماره کانال> - حذف یک کانال\n"
        "/listchannels - دیدن لیست کانال‌های ذخیره شده\n"
        "/check - بررسی و ارسال ویدیوی جدید برای همه کانال‌ها\n"
        "/latest [تعداد] - ارسال ویدیوهای آخر (پیش‌فرض ۵ تا)\n"
        "/activate <شماره1> <شماره2> ... - فعال یا غیرفعال کردن کانال‌ها با شماره\n"
        "/clear - حذف همه کانال‌ها\n"
        "/start - نمایش این پیام"
    )
    await update.message.reply_text(text)

async def add_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text(
            "لطفا شناسه کانال و نام کانال را وارد کنید. مثال:\n"
            "/addchannel UChIJN1t_tDeuEmsRUsoyG83frY4 MyChannelName"
        )
        return
    channel_id = context.args[0]
    channel_name = " ".join(context.args[1:])
    channels = load_channels()
    for ch in channels:
        if ch['id'] == channel_id:
            await update.message.reply_text("این کانال قبلا اضافه شده است.")
            return
    new_channel = {"id": channel_id, "name": channel_name, "active": True}
    channels.append(new_channel)
    save_channels(channels)
    await update.message.reply_text(f"کانال '{channel_name}' با شناسه {channel_id} اضافه شد و فعال گردید.")

async def remove_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("لطفا شماره کانال برای حذف را وارد کنید. مثال:\n/removechannel 2")
        return
    idx = int(context.args[0]) - 1
    channels = load_channels()
    if idx < 0 or idx >= len(channels):
        await update.message.reply_text("شماره کانال نامعتبر است.")
        return
    removed = channels.pop(idx)
    save_channels(channels)
    await update.message.reply_text(f"کانال شماره {idx+1} با شناسه {removed['id']} حذف شد.")

async def list_channels(update, context):
    channels = load_channels()
    if not channels:
        await update.message.reply_text("هیچ کانالی ثبت نشده است.")
        return

    msg = ""
    for i, ch in enumerate(channels, 1):
        status = "✅ فعال" if ch.get('active', False) else "❌ غیرفعال"
        name = ch.get('name', '') or "نامشخص"
        channel_id = ch.get('id', 'نامشخص')
        msg += f"{i}. {name} - {status}\n   شناسه کانال: {channel_id}\n"

    await update.message.reply_text(msg)




async def activate_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("لطفا شماره کانال‌هایی که می‌خواهید فعال شوند را وارد کنید. مثال:\n/activate 1 3 5")
        return
    indices = []
    for arg in context.args:
        if arg.isdigit():
            indices.append(int(arg)-1)
        else:
            await update.message.reply_text(f"مقدار '{arg}' معتبر نیست. فقط عدد وارد کنید.")
            return
    channels = load_channels()
    if any(i < 0 or i >= len(channels) for i in indices):
        await update.message.reply_text("یکی از شماره‌ها خارج از محدوده است.")
        return
    for i, ch in enumerate(channels):
        ch['active'] = (i in indices)
    save_channels(channels)
    await update.message.reply_text("کانال‌ها به‌روزرسانی شدند.")

async def clear_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    save_channels([])
    await update.message.reply_text("همه کانال‌ها حذف شدند.")

async def check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    channels = load_channels()
    active_channels = [ch for ch in channels if ch.get('active', False)]
    if not active_channels:
        await update.message.reply_text("هیچ کانال فعالی وجود ندارد.")
        return
    for ch in active_channels:
        channel_id = ch['id']
        name = ch.get('name', '')
        videos = await get_latest_videos(channel_id, 1)
        if not videos:
            await update.message.reply_text(f"هیچ ویدیوی جدیدی در کانال {name or channel_id} پیدا نشد.")
            continue
        video = videos[0]
        await update.message.reply_text(f"ویدیوی جدید کانال {name or channel_id}:\n{video['title']}\nhttps://www.youtube.com/watch?v={video['videoId']}")

async def latest_videos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args

    count = 5  # پیش‌فرض 5 تا ویدیو
    if args and args[0].isdigit():
        count = int(args[0])

    channels = load_channels()
    active_channels = [ch for ch in channels if ch.get('active', False)]

    if not active_channels:
        await update.message.reply_text("هیچ کانال فعالی وجود ندارد.")
        return

    for ch in active_channels:
        channel_id = ch['id']
        name = ch.get('name', '')
        videos = await get_latest_videos(channel_id, count)
        if not videos:
            await update.message.reply_text(f"هیچ ویدیویی در کانال {name or channel_id} پیدا نشد.")
            continue

        message_text = f"آخرین {count} ویدیو از کانال {name or channel_id}:\n"
        for video in videos:
            message_text += f"{video['title']}\nhttps://www.youtube.com/watch?v={video['videoId']}\n\n"

        await update.message.reply_text(message_text)

async def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("addchannel", add_channel))
    app.add_handler(CommandHandler("removechannel", remove_channel))
    app.add_handler(CommandHandler("listchannels", list_channels))
    app.add_handler(CommandHandler("activate", activate_channels))
    app.add_handler(CommandHandler("clear", clear_channels))
    app.add_handler(CommandHandler("check", check))
    app.add_handler(CommandHandler("latest", latest_videos))

    print("✅ Bot is running...")
    await app.run_polling()

if __name__ == "__main__":
    import nest_asyncio
    import asyncio
    nest_asyncio.apply()
    asyncio.run(main())
