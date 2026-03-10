#!/usr/bin/env python3
"""
টেলিগ্রাম বট: জেনারেটর (Generator)
বৈশিষ্ট্য: QR জেনারেটর, ছবি<->PDF কনভার্সন, PDF মার্জ/স্প্লিট/পাসওয়ার্ড, গ্রুপ মেম্বারশিপ চেক
"""

import os
import tempfile
import zipfile
from io import BytesIO

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)

import qrcode
from PIL import Image
from pdf2image import convert_from_path
from pypdf import PdfReader, PdfWriter

# ================= কনফিগারেশন =================
BOT_TOKEN = "8720821797:AAFQRaB6a7N06WgtCNxxtN0SPYc2_Ywx3yI"  # আপনার বট টোকেন
GROUP_CHAT_ID = -4931220826  # ⚠️ এখানে আপনার গ্রুপের সঠিক চ্যাট আইডি বসান (নিচের নির্দেশনা দেখুন)
GROUP_INVITE_LINK = "https://t.me/+hgds2QYqh9piNmM1"  # আপনার গ্রুপ লিংক

# কনভারসেশন স্টেট (ধাপ)
QR_TEXT, IMAGES_TO_PDF, PDF_TO_IMAGES, PDF_MERGE, PDF_SPLIT, PDF_PROTECT = range(6)

# ================= গ্রুপ মেম্বারশিপ চেক ফাংশন (ডিবাগ প্রিন্ট সহ) =================
async def is_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user_id = update.effective_user.id
    try:
        print(f"🔍 Checking user {user_id} in group {GROUP_CHAT_ID}")
        member = await context.bot.get_chat_member(chat_id=GROUP_CHAT_ID, user_id=user_id)
        print(f"✅ Member status: {member.status}")
        if member.status in ["member", "administrator", "creator"]:
            return True
        else:
            await update.effective_message.reply_text(
                f"❌ আপনি গ্রুপের সদস্য নন। প্রথমে গ্রুপে জয়েন করুন:\n{GROUP_INVITE_LINK}\nতারপর আবার চেষ্টা করুন।"
            )
            return False
    except Exception as e:
        print(f"❌ ERROR in is_member: {e}")
        await update.effective_message.reply_text(
            f"⚠️ গ্রুপ ভেরিফিকেশন ত্রুটি:\n\n{str(e)}\n\nসম্ভাব্য কারণ:\n"
            "1. GROUP_CHAT_ID ভুল (সঠিক আইডি @getidsbot দিয়ে বের করুন)\n"
            "2. বট গ্রুপের সদস্য নয় (গ্রুপে বটকে অ্যাড করুন)\n"
            "3. বটকে গ্রুপ থেকে বের করে দেওয়া হয়েছে (পুনরায় অ্যাড করুন)"
        )
        return False

# ================= স্টার্ট কমান্ড =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_member(update, context):
        return

    keyboard = [
        [InlineKeyboardButton("🔳 QR কোড জেনারেট", callback_data="qr")],
        [InlineKeyboardButton("📄 PDF কনভার্টার", callback_data="pdf")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "স্বাগতম *জেনারেটর* বটে! নিচের অপশন থেকে বেছে নিন:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

# ================= কলব্যাক হ্যান্ডলার (মেনু) =================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not await is_member(update, context):
        return ConversationHandler.END

    if query.data == "qr":
        await query.edit_message_text("আপনার টেক্সট বা লিংক পাঠান (যার জন্য QR বানাব):")
        return QR_TEXT

    elif query.data == "pdf":
        keyboard = [
            [InlineKeyboardButton("🖼️ ছবি → PDF", callback_data="img2pdf")],
            [InlineKeyboardButton("📑 PDF → ছবি", callback_data="pdf2img")],
            [InlineKeyboardButton("🔗 PDF মার্জ", callback_data="merge_pdf")],
            [InlineKeyboardButton("✂️ PDF স্প্লিট", callback_data="split_pdf")],
            [InlineKeyboardButton("🔐 PDF পাসওয়ার্ড", callback_data="protect_pdf")],
            [InlineKeyboardButton("🔙 মূল মেনু", callback_data="back_to_main")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("PDF অপশন নির্বাচন করুন:", reply_markup=reply_markup)
        return

    elif query.data == "img2pdf":
        await query.edit_message_text("এক বা একাধিক ছবি (jpg/png) পাঠান। শেষে '/done' লিখে PDF বানাতে বলুন।")
        return IMAGES_TO_PDF

    elif query.data == "pdf2img":
        await query.edit_message_text("একটি PDF ফাইল পাঠান। আমি প্রতিটি পৃষ্ঠার ছবি বানিয়ে ZIP করে দেব।")
        return PDF_TO_IMAGES

    elif query.data == "merge_pdf":
        await query.edit_message_text("একাধিক PDF ফাইল পাঠান। শেষে '/done' লিখুন।")
        return PDF_MERGE

    elif query.data == "split_pdf":
        await query.edit_message_text("একটি PDF পাঠান, তারপর পৃষ্ঠা নম্বর দিন (যেমন: 1-3,5,7-9)।")
        return PDF_SPLIT

    elif query.data == "protect_pdf":
        await query.edit_message_text("একটি PDF পাঠান, তারপর পাসওয়ার্ড দিন।")
        return PDF_PROTECT

    elif query.data == "back_to_main":
        await start(update, context)
        return ConversationHandler.END

    return ConversationHandler.END

# ================= QR কোড জেনারেট =================
async def qr_receive_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_member(update, context):
        return ConversationHandler.END

    text = update.message.text
    if not text:
        await update.message.reply_text("কোনো টেক্সট পাওয়া যায়নি। আবার চেষ্টা করুন।")
        return QR_TEXT

    try:
        img = qrcode.make(text)
        bio = BytesIO()
        img.save(bio, 'PNG')
        bio.seek(0)
        await update.message.reply_photo(photo=bio, caption="✅ আপনার QR কোড প্রস্তুত!")
    except Exception as e:
        await update.message.reply_text(f"QR তৈরি করতে সমস্যা: {str(e)}")

    await start(update, context)
    return ConversationHandler.END

# ================= ইমেজ টু পিডিএফ =================
async def images_to_pdf_collect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_member(update, context):
        return ConversationHandler.END

    if not update.message.photo:
        await update.message.reply_text("দয়া করে একটি ছবি পাঠান।")
        return IMAGES_TO_PDF

    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)

    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        await file.download_to_drive(tmp.name)
        tmp_path = tmp.name

    if 'images' not in context.user_data:
        context.user_data['images'] = []
    context.user_data['images'].append(tmp_path)

    await update.message.reply_text(f"ছবি যোগ হয়েছে (মোট {len(context.user_data['images'])}টি)। আরও পাঠান অথবা /done দিন।")
    return IMAGES_TO_PDF

async def images_to_pdf_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_member(update, context):
        return ConversationHandler.END

    images = context.user_data.get('images', [])
    if not images:
        await update.message.reply_text("কোনো ছবি পাওয়া যায়নি।")
        return ConversationHandler.END

    try:
        images_pil = [Image.open(img).convert('RGB') for img in images]
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_pdf:
            pdf_path = tmp_pdf.name
        images_pil[0].save(pdf_path, save_all=True, append_images=images_pil[1:], quality=95)

        with open(pdf_path, "rb") as f:
            await update.message.reply_document(document=f, filename="converted.pdf")

    except Exception as e:
        await update.message.reply_text(f"PDF তৈরি করতে সমস্যা: {str(e)}")
    finally:
        for img in images:
            try:
                os.unlink(img)
            except:
                pass
        try:
            os.unlink(pdf_path)
        except:
            pass
        context.user_data['images'] = []

    await start(update, context)
    return ConversationHandler.END

# ================= PDF টু ইমেজ =================
async def pdf_to_images_handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_member(update, context):
        return ConversationHandler.END

    doc = update.message.document
    if not doc or not doc.file_name.lower().endswith('.pdf'):
        await update.message.reply_text("একটি PDF ফাইল পাঠান।")
        return PDF_TO_IMAGES

    file = await context.bot.get_file(doc.file_id)
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_pdf:
        pdf_path = tmp_pdf.name
        await file.download_to_drive(pdf_path)

    try:
        images = convert_from_path(pdf_path, dpi=150)

        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp_zip:
            zip_path = tmp_zip.name
        with zipfile.ZipFile(zip_path, 'w') as zf:
            for i, img in enumerate(images):
                img_bytes = BytesIO()
                img.save(img_bytes, format='PNG')
                img_bytes.seek(0)
                zf.writestr(f"page_{i+1}.png", img_bytes.read())

        with open(zip_path, "rb") as f:
            await update.message.reply_document(document=f, filename="images.zip")

    except Exception as e:
        await update.message.reply_text(f"PDF প্রক্রিয়ায় সমস্যা: {str(e)}")
    finally:
        try:
            os.unlink(pdf_path)
            os.unlink(zip_path)
        except:
            pass

    await start(update, context)
    return ConversationHandler.END

# ================= PDF মার্জ =================
async def merge_pdf_collect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_member(update, context):
        return ConversationHandler.END

    doc = update.message.document
    if not doc or not doc.file_name.lower().endswith('.pdf'):
        await update.message.reply_text("একটি PDF ফাইল পাঠান।")
        return PDF_MERGE

    file = await context.bot.get_file(doc.file_id)
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        await file.download_to_drive(tmp.name)
        if 'pdfs' not in context.user_data:
            context.user_data['pdfs'] = []
        context.user_data['pdfs'].append(tmp.name)

    await update.message.reply_text(f"PDF যোগ হয়েছে (মোট {len(context.user_data['pdfs'])}টি)। আরও PDF পাঠান অথবা /done দিন।")
    return PDF_MERGE

async def merge_pdf_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_member(update, context):
        return ConversationHandler.END

    pdfs = context.user_data.get('pdfs', [])
    if len(pdfs) < 2:
        await update.message.reply_text("মার্জ করতে কমপক্ষে ২টি PDF দরকার।")
        return ConversationHandler.END

    merger = PdfWriter()
    for pdf in pdfs:
        merger.append(pdf)

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        output = tmp.name
        merger.write(output)
        merger.close()

    with open(output, "rb") as f:
        await update.message.reply_document(document=f, filename="merged.pdf")

    for pdf in pdfs:
        try:
            os.unlink(pdf)
        except:
            pass
    os.unlink(output)
    context.user_data['pdfs'] = []

    await start(update, context)
    return ConversationHandler.END

# ================= PDF স্প্লিট =================
async def split_pdf_get_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_member(update, context):
        return ConversationHandler.END

    doc = update.message.document
    if not doc or not doc.file_name.lower().endswith('.pdf'):
        await update.message.reply_text("একটি PDF ফাইল পাঠান।")
        return PDF_SPLIT

    file = await context.bot.get_file(doc.file_id)
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        pdf_path = tmp.name
        await file.download_to_drive(pdf_path)
        context.user_data['split_pdf'] = pdf_path

    await update.message.reply_text("এখন পৃষ্ঠা নম্বর দিন (যেমন: 1-3,5,7-9):")
    return PDF_SPLIT

async def split_pdf_get_pages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_member(update, context):
        return ConversationHandler.END

    page_spec = update.message.text.strip()
    pdf_path = context.user_data.get('split_pdf')
    if not pdf_path:
        await update.message.reply_text("প্রথমে PDF দিন।")
        return ConversationHandler.END

    try:
        reader = PdfReader(pdf_path)
        total = len(reader.pages)

        pages = set()
        for part in page_spec.split(','):
            part = part.strip()
            if '-' in part:
                start, end = map(int, part.split('-'))
                pages.update(range(start, end+1))
            else:
                if part.isdigit():
                    pages.add(int(part))

        valid_pages = [p-1 for p in pages if 1 <= p <= total]

        if not valid_pages:
            await update.message.reply_text("কোনো বৈধ পৃষ্ঠা পাওয়া যায়নি।")
            return PDF_SPLIT

        writer = PdfWriter()
        for p in valid_pages:
            writer.add_page(reader.pages[p])

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            output = tmp.name
            writer.write(output)

        with open(output, "rb") as f:
            await update.message.reply_document(document=f, filename="split.pdf")

        os.unlink(output)

    except Exception as e:
        await update.message.reply_text(f"স্প্লিট করতে সমস্যা: {str(e)}")
    finally:
        os.unlink(pdf_path)
        context.user_data.pop('split_pdf', None)

    await start(update, context)
    return ConversationHandler.END

# ================= PDF পাসওয়ার্ড প্রোটেক্ট =================
async def protect_pdf_get_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_member(update, context):
        return ConversationHandler.END

    doc = update.message.document
    if not doc or not doc.file_name.lower().endswith('.pdf'):
        await update.message.reply_text("একটি PDF ফাইল পাঠান।")
        return PDF_PROTECT

    file = await context.bot.get_file(doc.file_id)
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        pdf_path = tmp.name
        await file.download_to_drive(pdf_path)
        context.user_data['protect_pdf'] = pdf_path

    await update.message.reply_text("এখন পাসওয়ার্ড দিন:")
    return PDF_PROTECT

async def protect_pdf_set_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_member(update, context):
        return ConversationHandler.END

    password = update.message.text.strip()
    pdf_path = context.user_data.get('protect_pdf')
    if not pdf_path:
        await update.message.reply_text("প্রথমে PDF দিন।")
        return ConversationHandler.END

    if not password:
        await update.message.reply_text("পাসওয়ার্ড খালি রাখা যাবে না। আবার চেষ্টা করুন।")
        return PDF_PROTECT

    try:
        reader = PdfReader(pdf_path)
        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)
        writer.encrypt(password)

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            output = tmp.name
            writer.write(output)

        with open(output, "rb") as f:
            await update.message.reply_document(document=f, filename="protected.pdf")

        os.unlink(output)

    except Exception as e:
        await update.message.reply_text(f"পাসওয়ার্ড সেট করতে সমস্যা: {str(e)}")
    finally:
        os.unlink(pdf_path)
        context.user_data.pop('protect_pdf', None)

    await start(update, context)
    return ConversationHandler.END

# ================= ফলব্যাক হ্যান্ডলার =================
async def fallback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_member(update, context):
        return
    await update.message.reply_text("কমান্ড বুঝতে পারিনি। /start দিন।")

# ================= মেইন ফাংশন =================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # কনভারসেশন হ্যান্ডলার
    conv_handler_img2pdf = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^img2pdf$")],
        states={
            IMAGES_TO_PDF: [
                MessageHandler(filters.PHOTO, images_to_pdf_collect),
                CommandHandler("done", images_to_pdf_done),
            ],
        },
        fallbacks=[CommandHandler("cancel", lambda u,c: u.message.reply_text("বাতিল"))],
    )

    conv_handler_pdf2img = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^pdf2img$")],
        states={
            PDF_TO_IMAGES: [
                MessageHandler(filters.Document.PDF, pdf_to_images_handle),
            ],
        },
        fallbacks=[],
    )

    conv_handler_merge = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^merge_pdf$")],
        states={
            PDF_MERGE: [
                MessageHandler(filters.Document.PDF, merge_pdf_collect),
                CommandHandler("done", merge_pdf_done),
            ],
        },
        fallbacks=[],
    )

    conv_handler_split = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^split_pdf$")],
        states={
            PDF_SPLIT: [
                MessageHandler(filters.Document.PDF, split_pdf_get_file),
                MessageHandler(filters.TEXT & ~filters.COMMAND, split_pdf_get_pages),
            ],
        },
        fallbacks=[],
    )

    conv_handler_protect = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^protect_pdf$")],
        states={
            PDF_PROTECT: [
                MessageHandler(filters.Document.PDF, protect_pdf_get_file),
                MessageHandler(filters.TEXT & ~filters.COMMAND, protect_pdf_set_password),
            ],
        },
        fallbacks=[],
    )

    conv_handler_qr = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^qr$")],
        states={
            QR_TEXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, qr_receive_text),
            ],
        },
        fallbacks=[],
    )

    # হ্যান্ডলার যোগ
    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler_qr)
    app.add_handler(conv_handler_img2pdf)
    app.add_handler(conv_handler_pdf2img)
    app.add_handler(conv_handler_merge)
    app.add_handler(conv_handler_split)
    app.add_handler(conv_handler_protect)
    app.add_handler(CallbackQueryHandler(button_handler, pattern="^(pdf|back_to_main)$"))
    app.add_handler(MessageHandler(filters.ALL, fallback))

    print("বট চালু হয়েছে...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
