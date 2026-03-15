#!/usr/bin/env python3
"""
টেলিগ্রাম বট: জেনারেটর (Generator) – সম্পূর্ণ ভাষা-সচেতন
Poppler PATH সহ - সব প্ল্যাটফর্মের জন্য উপযোগী
"""

import os
import tempfile
import zipfile
import subprocess
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
from pdf2image import convert_from_path, pdfinfo_from_path
from pypdf import PdfReader, PdfWriter

# ================= কনফিগারেশন =================
BOT_TOKEN = os.environ.get("BOT_TOKEN")  # আপনার বট টোকেন দিন

# ================= Poppler PATH ডিটেকশন =================
def get_poppler_path():
    """
    সিস্টেম অনুযায়ী Poppler-এর PATH ডিটেক্ট করে
    """
    # সম্ভাব্য পাথগুলো চেক করা
    possible_paths = [
        '/usr/bin',                          # Linux (GitHub Actions, Ubuntu)
        '/usr/local/bin',                    # macOS (Homebrew)
        '/data/data/com.termux/files/usr/bin', # Termux (Android)
        'C:\\poppler\\bin',                   # Windows (যদি ম্যানুয়ালি ইনস্টল করা হয়)
        'C:\\Program Files\\poppler\\bin',    # Windows
    ]
    
    # কোন পাথে pdftoppm আছে?
    for path in possible_paths:
        pdftoppm_path = os.path.join(path, 'pdftoppm')
        if os.path.exists(pdftoppm_path) or os.path.exists(pdftoppm_path + '.exe'):
            print(f"✅ Poppler found at: {path}")
            return path
    
    # যা which কমান্ড দিয়ে খোঁজা
    try:
        result = subprocess.run(['which', 'pdftoppm'], capture_output=True, text=True)
        if result.returncode == 0:
            path = os.path.dirname(result.stdout.strip())
            print(f"✅ Poppler found via which: {path}")
            return path
    except:
        pass
    
    print("⚠️ Poppler not found. Using default PATH.")
    return None

POPPLER_PATH = get_poppler_path()

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
        'pdf2img_processing': "⏳ PDF প্রক্রিয়াকরণ হচ্ছে (মোট {pages} পৃষ্ঠা)...",
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
        
        # Diagnose
        'diagnose_title': "🔍 ডায়াগনস্টিক রিপোর্ট",
        'poppler_status': "Poppler অবস্থান: {path}",
        'poppler_not_found': "Poppler পাওয়া যায়নি। PDF→ছবি কাজ করবে না।",
        
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
        'pdf2img_processing': "⏳ Processing PDF ({pages} pages)...",
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
        
        # Diagnose
        'diagnose_title': "🔍 Diagnostic Report",
        'poppler_status': "Poppler path: {path}",
        'poppler_not_found': "Poppler not found. PDF→Image will not work.",
        
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

# ================= ডায়াগনস্টিক কমান্ড =================
async def diagnose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """সিস্টেম ডায়াগনস্টিক রিপোর্ট দেখায়"""
    import sys
    
    msg = f"**{get_text('diagnose_title', context)}**\n\n"
    
    # পাইথন ভার্সন
    msg += f"🐍 Python: {sys.version}\n"
    
    # pdf2image ভার্সন
    import pdf2image
    msg += f"📦 pdf2image: {pdf2image.__version__}\n"
    
    # Poppler স্ট্যাটাস
    if POPPLER_PATH:
        msg += f"✅ {get_text('poppler_status', context, path=POPPLER_PATH)}\n"
        
        # pdftoppm ভার্সন
        try:
            result = subprocess.run([os.path.join(POPPLER_PATH, 'pdftoppm'), '-v'], 
                                   capture_output=True, text=True)
            msg += f"   pdftoppm: {result.stderr.strip()}\n"
        except:
            pass
    else:
        msg += f"❌ {get_text('poppler_not_found', context)}\n"
    
    await update.message.reply_text(msg)

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
        [InlineKeyboardButton("🔍 Diagnose", callback_data="diagnose")],
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

# ================= ইমেজ টু পিডিএফ =================
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

# ================= PDF টু ইমেজ (Poppler PATH সহ) =================
async def pdf_pdf2img(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(get_text('pdf2img_prompt', context))
    return PDF_TO_IMAGES

async def pdf_to_images_handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.document or not update.message.document.file_name.lower().endswith('.pdf'):
        await update.message.reply_text(get_text('pdf_invalid', context))
        return PDF_TO_IMAGES
    
    doc = update.message.document
    file = await context.bot.get_file(doc.file_id)
    
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_pdf:
        pdf_path = tmp_pdf.name
        await file.download_to_drive(pdf_path)
    
    try:
        # PDF থেকে পৃষ্ঠা সংখ্যা বের করুন (Poppler PATH সহ)
        if POPPLER_PATH:
            info = pdfinfo_from_path(pdf_path, poppler_path=POPPLER_PATH)
            total_pages = info['pages']
            await update.message.reply_text(
                get_text('pdf2img_processing', context, pages=total_pages)
            )
            
            # ইমেজ কনভার্ট করুন (Poppler PATH সহ)
            images = convert_from_path(pdf_path, dpi=150, poppler_path=POPPLER_PATH)
        else:
            # Poppler না থাকলে try without path
            info = pdfinfo_from_path(pdf_path)
            total_pages = info['pages']
            await update.message.reply_text(
                get_text('pdf2img_processing', context, pages=total_pages)
            )
            images = convert_from_path(pdf_path, dpi=150)
        
        # একাধিক ছবি থাকলে ZIP করে পাঠান
        if len(images) > 1:
            with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp_zip:
                zip_path = tmp_zip.name
            
            with zipfile.ZipFile(zip_path, 'w') as zf:
                for i, img in enumerate(images):
                    img_bytes = BytesIO()
                    img.save(img_bytes, format='PNG')
                    img_bytes.seek(0)
                    zf.writestr(f"page_{i+1}.png", img_bytes.read())
            
            with open(zip_path, "rb") as f:
                await update.message.reply_document(
                    document=f,
                    filename="images.zip",
                    caption=get_text('pdf2img_success', context)
                )
            os.unlink(zip_path)
        else:
            # একটি মাত্র ছবি থাকলে সরাসরি পাঠান
            img_bytes = BytesIO()
            images[0].save(img_bytes, format='PNG')
            img_bytes.seek(0)
            await update.message.reply_photo(
                photo=img_bytes,
                caption=get_text('pdf2img_success', context)
            )
            
    except Exception as e:
        error_msg = str(e)
        if "poppler" in error_msg.lower():
            error_msg += "\n\n💡 সমাধান: System-এ Poppler ইনস্টল করুন।"
        await update.message.reply_text(get_text('pdf2img_error', context, error=error_msg))
        import traceback
        traceback.print_exc()
    finally:
        os.unlink(pdf_path)
    
    keyboard = [[InlineKeyboardButton(get_text('back_btn', context), callback_data="back_to_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(get_text('welcome', context), reply_markup=reply_markup)
    return ConversationHandler.END

# ================= PDF মার্জ =================
async def pdf_merge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(get_text('merge_prompt', context))
    return PDF_MERGE

async def merge_pdf_collect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.document or not update.message.document.file_name.lower().endswith('.pdf'):
        await update.message.reply_text(get_text('pdf_invalid', context))
        return PDF_MERGE
    
    doc = update.message.document
    file = await context.bot.get_file(doc.file_id)
    
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        await file.download_to_drive(tmp.name)
        if 'pdfs' not in context.user_data:
            context.user_data['pdfs'] = []
        context.user_data['pdfs'].append(tmp.name)
    
    await update.message.reply_text(
        get_text('merge_added', context, count=len(context.user_data['pdfs']))
    )
    return PDF_MERGE

async def merge_pdf_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pdfs = context.user_data.get('pdfs', [])
    if len(pdfs) < 2:
        await update.message.reply_text(get_text('merge_need_more', context))
        return ConversationHandler.END
    
    try:
        merger = PdfWriter()
        for pdf in pdfs:
            merger.append(pdf)
        
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            output = tmp.name
            merger.write(output)
            merger.close()
        
        with open(output, "rb") as f:
            await update.message.reply_document(
                document=f,
                filename="merged.pdf",
                caption=get_text('merge_success', context)
            )
        os.unlink(output)
        
    except Exception as e:
        await update.message.reply_text(get_text('merge_error', context, error=str(e)))
    finally:
        for pdf in pdfs:
            try: os.unlink(pdf)
            except: pass
        context.user_data['pdfs'] = []
    
    keyboard = [[InlineKeyboardButton(get_text('back_btn', context), callback_data="back_to_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(get_text('welcome', context), reply_markup=reply_markup)
    return ConversationHandler.END

# ================= PDF স্প্লিট =================
async def pdf_split(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(get_text('split_prompt', context))
    return PDF_SPLIT

async def split_pdf_get_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.document or not update.message.document.file_name.lower().endswith('.pdf'):
        await update.message.reply_text(get_text('pdf_invalid', context))
        return PDF_SPLIT
    
    doc = update.message.document
    file = await context.bot.get_file(doc.file_id)
    
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        pdf_path = tmp.name
        await file.download_to_drive(pdf_path)
        context.user_data['split_pdf'] = pdf_path
    
    await update.message.reply_text(get_text('split_page_prompt', context))
    return PDF_SPLIT

async def split_pdf_get_pages(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            await update.message.reply_text(get_text('split_invalid', context))
            return PDF_SPLIT
        
        writer = PdfWriter()
        for p in valid_pages:
            writer.add_page(reader.pages[p])
        
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            output = tmp.name
            writer.write(output)
        
        with open(output, "rb") as f:
            await update.message.reply_document(
                document=f,
                filename="split.pdf",
                caption=get_text('split_success', context)
            )
        os.unlink(output)
        
    except Exception as e:
        await update.message.reply_text(get_text('split_error', context, error=str(e)))
    finally:
        os.unlink(pdf_path)
        context.user_data.pop('split_pdf', None)
    
    keyboard = [[InlineKeyboardButton(get_text('back_btn', context), callback_data="back_to_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(get_text('welcome', context), reply_markup=reply_markup)
    return ConversationHandler.END

# ================= PDF পাসওয়ার্ড =================
async def pdf_protect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(get_text('protect_prompt', context))
    return PDF_PROTECT

async def protect_pdf_get_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.document or not update.message.document.file_name.lower().endswith('.pdf'):
        await update.message.reply_text(get_text('pdf_invalid', context))
        return PDF_PROTECT
    
    doc = update.message.document
    file = await context.bot.get_file(doc.file_id)
    
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        pdf_path = tmp.name
        await file.download_to_drive(pdf_path)
        context.user_data['protect_pdf'] = pdf_path
    
    await update.message.reply_text(get_text('protect_pass_prompt', context))
    return PDF_PROTECT

async def protect_pdf_set_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    password = update.message.text.strip()
    pdf_path = context.user_data.get('protect_pdf')
    
    if not pdf_path:
        await update.message.reply_text("প্রথমে PDF দিন।")
        return ConversationHandler.END
    
    if not password:
        await update.message.reply_text(get_text('protect_empty', context))
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
            await update.message.reply_document(
                document=f,
                filename="protected.pdf",
                caption=get_text('protect_success', context)
            )
        os.unlink(output)
        
    except Exception as e:
        await update.message.reply_text(get_text('protect_error', context, error=str(e)))
    finally:
        os.unlink(pdf_path)
        context.user_data.pop('protect_pdf', None)
    
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
    elif query.data == "diagnose":
        await diagnose(update, context)
    elif query.data == "back_to_main":
        return await back_to_main(update, context)
    elif query.data == "img2pdf":
        return await pdf_img2pdf(update, context)
    elif query.data == "pdf2img":
        return await pdf_pdf2img(update, context)
    elif query.data == "merge_pdf":
        return await pdf_merge(update, context)
    elif query.data == "split_pdf":
        return await pdf_split(update, context)
    elif query.data == "protect_pdf":
        return await pdf_protect(update, context)
    
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
        fallbacks=[CommandHandler("cancel", lambda u,c: u.message.reply_text(get_text('cancel', c)))],
    )
    
    conv_handler_img2pdf = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^img2pdf$")],
        states={
            IMAGES_TO_PDF: [
                MessageHandler(filters.PHOTO, images_to_pdf_collect),
                CommandHandler("done", images_to_pdf_done),
            ]
        },
        fallbacks=[CommandHandler("cancel", lambda u,c: u.message.reply_text(get_text('cancel', c)))],
    )
    
    conv_handler_pdf2img = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^pdf2img$")],
        states={
            PDF_TO_IMAGES: [
                MessageHandler(filters.Document.PDF, pdf_to_images_handle),
            ]
        },
        fallbacks=[CommandHandler("cancel", lambda u,c: u.message.reply_text(get_text('cancel', c)))],
    )
    
    conv_handler_merge = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^merge_pdf$")],
        states={
            PDF_MERGE: [
                MessageHandler(filters.Document.PDF, merge_pdf_collect),
                CommandHandler("done", merge_pdf_done),
            ]
        },
        fallbacks=[CommandHandler("cancel", lambda u,c: u.message.reply_text(get_text('cancel', c)))],
    )
    
    conv_handler_split = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^split_pdf$")],
        states={
            PDF_SPLIT: [
                MessageHandler(filters.Document.PDF, split_pdf_get_file),
                MessageHandler(filters.TEXT & ~filters.COMMAND, split_pdf_get_pages),
            ]
        },
        fallbacks=[CommandHandler("cancel", lambda u,c: u.message.reply_text(get_text('cancel', c)))],
    )
    
    conv_handler_protect = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^protect_pdf$")],
        states={
            PDF_PROTECT: [
                MessageHandler(filters.Document.PDF, protect_pdf_get_file),
                MessageHandler(filters.TEXT & ~filters.COMMAND, protect_pdf_set_password),
            ]
        },
        fallbacks=[CommandHandler("cancel", lambda u,c: u.message.reply_text(get_text('cancel', c)))],
    )
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("diagnose", diagnose))
    app.add_handler(conv_handler_qr)
    app.add_handler(conv_handler_img2pdf)
    app.add_handler(conv_handler_pdf2img)
    app.add_handler(conv_handler_merge)
    app.add_handler(conv_handler_split)
    app.add_handler(conv_handler_protect)
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.ALL, fallback))
    
    print(f"✅ Bot started with Poppler path: {POPPLER_PATH}")
    app.run_polling()

if __name__ == "__main__":
    # কনভারসেশন স্টেট (গ্লোবাল ভেরিয়েবল)
    QR_TEXT, IMAGES_TO_PDF, PDF_TO_IMAGES, PDF_MERGE, PDF_SPLIT, PDF_PROTECT = range(6)
    main()
