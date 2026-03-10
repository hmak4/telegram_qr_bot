#!/usr/bin/env python3
"""
টেলিগ্রাম বট: জেনারেটর (Generator) – সম্পূর্ণ ভাষা-সচেতন
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
BOT_TOKEN = os.environ.get("BOT_TOKEN") # ⚠️ আপনার বট টোকেন দিন

# কনভারসেশন স্টেট
QR_TEXT, IMAGES_TO_PDF, PDF_TO_IMAGES, PDF_MERGE, PDF_SPLIT, PDF_PROTECT = range(6)

# ================= ভাষা সংক্রান্ত ডাটা =================
LANGUAGES = {
    'bn': {
        # Main menu
        'welcome': "🤖 *জেনারেটর বট*\n\nনিচের অপশন থেকে বেছে নিন:",
        'qr_btn': "🔳 QR কোড",
        'pdf_btn': "📄 PDF",
        'lang_btn': "🌐 ভাষা",
        'settings_btn': "⚙️ সেটিংস",
        'back_btn': "🔙 মেনুতে ফিরুন",
        
        # Language menu
        'select_lang': "ভাষা নির্বাচন করুন:",
        'bengali': "বাংলা",
        'english': "ইংরেজি",
        
        # QR
        'qr_prompt': "আপনার টেক্সট বা লিংক পাঠান:",
        'qr_success': "✅ আপনার QR কোড প্রস্তুত!",
        'qr_error': "QR তৈরি করতে সমস্যা: {error}",
        'no_text': "❌ কোনো টেক্সট পাওয়া যায়নি।",
        
        # PDF menu
        'pdf_menu': "📄 PDF অপশন:",
        'img2pdf_btn': "🖼️ ছবি → PDF",
        'pdf2img_btn': "📑 PDF → ছবি",
        'merge_btn': "🔗 PDF মার্জ",
        'split_btn': "✂️ PDF স্প্লিট",
        'protect_btn': "🔐 PDF পাসওয়ার্ড",
        
        # Image to PDF
        'img2pdf_prompt': "ছবি পাঠান। শেষে /done লিখুন।",
        'img_added': "ছবি যোগ হয়েছে (মোট {count}টি)।",
        'img_none': "কোনো ছবি নেই।",
        'pdf_created': "✅ PDF তৈরি!",
        'pdf_error': "PDF ত্রুটি: {error}",
        
        # PDF to Image
        'pdf2img_prompt': "PDF ফাইল পাঠান:",
        'pdf_invalid': "PDF ফাইল পাঠান।",
        'pdf2img_success': "✅ ছবি তৈরি!",
        'pdf2img_error': "PDF ত্রুটি: {error}",
        
        # Merge
        'merge_prompt': "PDF পাঠান। শেষে /done লিখুন।",
        'merge_added': "PDF যোগ হয়েছে (মোট {count}টি)।",
        'merge_need_more': "কমপক্ষে ২টি PDF দরকার।",
        'merge_success': "✅ মার্জ সম্পন্ন!",
        'merge_error': "মার্জ ত্রুটি: {error}",
        
        # Split
        'split_prompt': "PDF পাঠান:",
        'split_page_prompt': "পৃষ্ঠা নম্বর দিন (যেমন: 1-3,5):",
        'split_invalid': "বৈধ পৃষ্ঠা নেই।",
        'split_success': "✅ স্প্লিট সম্পন্ন!",
        'split_error': "স্প্লিট ত্রুটি: {error}",
        
        # Password
        'protect_prompt': "PDF পাঠান:",
        'protect_pass_prompt': "পাসওয়ার্ড দিন:",
        'protect_empty': "পাসওয়ার্ড খালি হবে না।",
        'protect_success': "✅ পাসওয়ার্ড সুরক্ষিত!",
        'protect_error': "পাসওয়ার্ড ত্রুটি: {error}",
        
        # Settings
        'about': "জেনারেটর বট v2.0\nQR ও PDF টুলস",
        
        # Misc
        'cancel': "বাতিল",
        'unknown': "বুঝতে পারিনি। /start দিন।"
    },
    'en': {
        # Main menu
        'welcome': "🤖 *Generator Bot*\n\nChoose an option:",
        'qr_btn': "🔳 QR Code",
        'pdf_btn': "📄 PDF",
        'lang_btn': "🌐 Language",
        'settings_btn': "⚙️ Settings",
        'back_btn': "🔙 Back to Menu",
        
        # Language menu
        'select_lang': "Select Language:",
        'bengali': "Bengali",
        'english': "English",
        
        # QR
        'qr_prompt': "Send text or link:",
        'qr_success': "✅ QR Code ready!",
        'qr_error': "QR error: {error}",
        'no_text': "❌ No text received.",
        
        # PDF menu
        'pdf_menu': "📄 PDF Options:",
        'img2pdf_btn': "🖼️ Image → PDF",
        'pdf2img_btn': "📑 PDF → Image",
        'merge_btn': "🔗 Merge PDF",
        'split_btn': "✂️ Split PDF",
        'protect_btn': "🔐 Password PDF",
        
        # Image to PDF
        'img2pdf_prompt': "Send images. Type /done when finished.",
        'img_added': "Image added (total {count}).",
        'img_none': "No images.",
        'pdf_created': "✅ PDF created!",
        'pdf_error': "PDF error: {error}",
        
        # PDF to Image
        'pdf2img_prompt': "Send PDF file:",
        'pdf_invalid': "Send a PDF file.",
        'pdf2img_success': "✅ Images created!",
        'pdf2img_error': "PDF error: {error}",
        
        # Merge
        'merge_prompt': "Send PDFs. Type /done when finished.",
        'merge_added': "PDF added (total {count}).",
        'merge_need_more': "Need at least 2 PDFs.",
        'merge_success': "✅ Merge complete!",
        'merge_error': "Merge error: {error}",
        
        # Split
        'split_prompt': "Send PDF:",
        'split_page_prompt': "Enter page numbers (e.g., 1-3,5):",
        'split_invalid': "No valid pages.",
        'split_success': "✅ Split complete!",
        'split_error': "Split error: {error}",
        
        # Password
        'protect_prompt': "Send PDF:",
        'protect_pass_prompt': "Enter password:",
        'protect_empty': "Password cannot be empty.",
        'protect_success': "✅ Password protected!",
        'protect_error': "Password error: {error}",
        
        # Settings
        'about': "Generator Bot v2.0\nQR & PDF Tools",
        
        # Misc
        'cancel': "Cancel",
        'unknown': "Not recognized. Use /start."
    }
}

# ================= হেলপার ফাংশন =================
def get_text(key, context, **kwargs):
    """ভাষা অনুযায়ী টেক্সট রিটার্ন করে"""
    lang = context.user_data.get('language', 'bn')
    text = LANGUAGES[lang].get(key, key)
    if kwargs:
        text = text.format(**kwargs)
    return text

# ================= স্টার্ট =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """মূল মেনু দেখায়"""
    keyboard = [
        [
            InlineKeyboardButton(get_text('qr_btn', context), callback_data="qr"),
            InlineKeyboardButton(get_text('pdf_btn', context), callback_data="pdf")
        ],
        [
            InlineKeyboardButton(get_text('lang_btn', context), callback_data="language"),
            InlineKeyboardButton(get_text('settings_btn', context), callback_data="settings")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        get_text('welcome', context),
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

# ================= ভাষা মেনু =================
async def language_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton(get_text('bengali', context), callback_data="set_lang_bn")],
        [InlineKeyboardButton(get_text('english', context), callback_data="set_lang_en")],
        [InlineKeyboardButton(get_text('back_btn', context), callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        get_text('select_lang', context),
        reply_markup=reply_markup
    )

# ================= ভাষা সেট =================
async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "set_lang_bn":
        context.user_data['language'] = 'bn'
    elif query.data == "set_lang_en":
        context.user_data['language'] = 'en'
    
    # নতুন ভাষায় মূল মেনু দেখাও
    keyboard = [
        [
            InlineKeyboardButton(get_text('qr_btn', context), callback_data="qr"),
            InlineKeyboardButton(get_text('pdf_btn', context), callback_data="pdf")
        ],
        [
            InlineKeyboardButton(get_text('lang_btn', context), callback_data="language"),
            InlineKeyboardButton(get_text('settings_btn', context), callback_data="settings")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        get_text('welcome', context),
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

# ================= সেটিংস =================
async def settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("ℹ️ About", callback_data="about")],
        [InlineKeyboardButton(get_text('back_btn', context), callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        get_text('about', context),
        reply_markup=reply_markup
    )

# ================= QR কোড =================
async def qr_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(get_text('qr_prompt', context))
    return QR_TEXT

async def qr_receive_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if not text:
        await update.message.reply_text(get_text('no_text', context))
        return QR_TEXT

    try:
        img = qrcode.make(text)
        bio = BytesIO()
        img.save(bio, 'PNG')
        bio.seek(0)
        
        keyboard = [[InlineKeyboardButton(get_text('back_btn', context), callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_photo(
            photo=bio,
            caption=get_text('qr_success', context),
            reply_markup=reply_markup
        )
    except Exception as e:
        await update.message.reply_text(get_text('qr_error', context, error=str(e)))

    return ConversationHandler.END

# ================= PDF মেনু =================
async def pdf_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton(get_text('img2pdf_btn', context), callback_data="img2pdf")],
        [InlineKeyboardButton(get_text('pdf2img_btn', context), callback_data="pdf2img")],
        [InlineKeyboardButton(get_text('merge_btn', context), callback_data="merge_pdf")],
        [InlineKeyboardButton(get_text('split_btn', context), callback_data="split_pdf")],
        [InlineKeyboardButton(get_text('protect_btn', context), callback_data="protect_pdf")],
        [InlineKeyboardButton(get_text('back_btn', context), callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        get_text('pdf_menu', context),
        reply_markup=reply_markup
    )

# ================= PDF অপশন হ্যান্ডলার =================
# (সংক্ষেপে শুধু img2pdf দেখালাম, বাকিগুলো একই প্যাটার্ন)

async def pdf_img2pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(get_text('img2pdf_prompt', context))
    return IMAGES_TO_PDF

async def images_to_pdf_collect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        return IMAGES_TO_PDF
        
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        await file.download_to_drive(tmp.name)
        tmp_path = tmp.name
    
    if 'images' not in context.user_data:
        context.user_data['images'] = []
    context.user_data['images'].append(tmp_path)
    
    await update.message.reply_text(
        get_text('img_added', context, count=len(context.user_data['images']))
    )
    return IMAGES_TO_PDF

async def images_to_pdf_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    images = context.user_data.get('images', [])
    if not images:
        await update.message.reply_text(get_text('img_none', context))
        return ConversationHandler.END
    
    try:
        images_pil = [Image.open(img).convert('RGB') for img in images]
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_pdf:
            pdf_path = tmp_pdf.name
        images_pil[0].save(pdf_path, save_all=True, append_images=images_pil[1:], quality=85)
        
        with open(pdf_path, "rb") as f:
            await update.message.reply_document(
                document=f,
                filename="converted.pdf",
                caption=get_text('pdf_created', context)
            )
    except Exception as e:
        await update.message.reply_text(get_text('pdf_error', context, error=str(e)))
    finally:
        for img in images:
            try: os.unlink(img)
            except: pass
        try: os.unlink(pdf_path)
        except: pass
        context.user_data['images'] = []
    
    keyboard = [[InlineKeyboardButton(get_text('back_btn', context), callback_data="back_to_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(get_text('welcome', context), reply_markup=reply_markup)
    return ConversationHandler.END

# ================= ব্যাক টু মেইন =================
async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [
            InlineKeyboardButton(get_text('qr_btn', context), callback_data="qr"),
            InlineKeyboardButton(get_text('pdf_btn', context), callback_data="pdf")
        ],
        [
            InlineKeyboardButton(get_text('lang_btn', context), callback_data="language"),
            InlineKeyboardButton(get_text('settings_btn', context), callback_data="settings")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        get_text('welcome', context),
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    return ConversationHandler.END

# ================= কলব্যাক হ্যান্ডলার =================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "qr":
        return await qr_menu(update, context)
    elif query.data == "pdf":
        return await pdf_menu(update, context)
    elif query.data == "language":
        await language_menu(update, context)
    elif query.data in ["set_lang_bn", "set_lang_en"]:
        await set_language(update, context)
    elif query.data == "settings":
        await settings_menu(update, context)
    elif query.data == "about":
        await query.edit_message_text(get_text('about', context))
    elif query.data == "back_to_main":
        return await back_to_main(update, context)
    elif query.data == "img2pdf":
        return await pdf_img2pdf(update, context)
    # PDF এর অন্যান্য অপশন এখানে যোগ করবেন
    
    return ConversationHandler.END

# ================= ফলব্যাক =================
async def fallback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(get_text('unknown', context))

# ================= মেইন =================
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Conversation Handlers
    conv_handler_qr = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^qr$")],
        states={QR_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, qr_receive_text)]},
        fallbacks=[],
    )
    
    conv_handler_img2pdf = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^img2pdf$")],
        states={
            IMAGES_TO_PDF: [
                MessageHandler(filters.PHOTO, images_to_pdf_collect),
                CommandHandler("done", images_to_pdf_done),
            ]
        },
        fallbacks=[],
    )
    
    # অন্যান্য কনভারসেশন হ্যান্ডলার যোগ করবেন...
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler_qr)
    app.add_handler(conv_handler_img2pdf)
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.ALL, fallback))
    
    print("✅ Bot started (fully multilingual)")
    app.run_polling()

if __name__ == "__main__":
    main()
