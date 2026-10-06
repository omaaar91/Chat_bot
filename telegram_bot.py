import os
import sys
import asyncio
import logging
from typing import Dict, List
from dotenv import load_dotenv

# دعم طباعة الحروف العربية في موجه الأوامر على ويندوز
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# تحميل متغيرات البيئة
load_dotenv()

from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode, ChatAction
from aiogram.filters import CommandStart, Command
from aiogram.client.default import DefaultBotProperties

# استدعاء دالة الأجينت والـ RAG من main.py
from main import ask_bot

# إعداد التسجيل (Logging)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(message)s"
)
logger = logging.getLogger(__name__)

# فحص التوكن
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
if not TELEGRAM_BOT_TOKEN:
    logger.error("❌ خطأ: لم يتم العثور على TELEGRAM_BOT_TOKEN في ملف .env")
    sys.exit(1)

# ذاكرة المحادثة لكل مستخدم (تخزين آخر 6 رسائل لكل مستخدم)
user_histories: Dict[int, List[dict]] = {}
MAX_HISTORY = 6

def get_formatted_history(user_id: int) -> str:
    """تنسيق سجل المحادثة كنص للأجينت"""
    if user_id not in user_histories or not user_histories[user_id]:
        return "لا يوجد سجل سابق."
    
    formatted = []
    for msg in user_histories[user_id]:
        role = "العميل" if msg["role"] == "user" else "البوت"
        formatted.append(f"{role}: {msg['content']}")
    return "\n".join(formatted)

def add_to_history(user_id: int, user_text: str, bot_reply: str):
    """إضافة السؤال والإجابة إلى سجل المحادثة"""
    if user_id not in user_histories:
        user_histories[user_id] = []
    
    user_histories[user_id].append({"role": "user", "content": user_text})
    user_histories[user_id].append({"role": "bot", "content": bot_reply})
    
    # الإبقاء على آخر عدد محدد من الرسائل
    if len(user_histories[user_id]) > MAX_HISTORY * 2:
        user_histories[user_id] = user_histories[user_id][-MAX_HISTORY * 2:]

# إنشاء البوت وموزع الأحداث
bot = Bot(
    token=TELEGRAM_BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
)
dp = Dispatcher()


@dp.message(CommandStart())
async def handle_start(message: types.Message):
    """الرد على أمر /start عند بدء المحادثة"""
    user_name = message.from_user.first_name if message.from_user else "صديقي"
    
    # إعادة تعيين الذاكرة عند الضغط على start
    if message.from_user:
        user_histories[message.from_user.id] = []

    welcome_text = (
        f"أهلاً بك يا {user_name}! 👋\n\n"
        "📚 **أنا المساعد الذكي لمتجرنا لبيع الكتب في مدينة السادات.**\n\n"
        "يمكنني مساعدتك في:\n"
        "• البحث عن الكتب بجميع التصنيفات (شعر، موسيقى، روايات، تاريخ، إلخ).\n"
        "• معرفة الأسعار، التقييمات، وروابط الشراء المباشرة.\n"
        "• معرفة عنوان المتجر، مواعيد العمل، وسياسة الاسترجاع.\n"
        "• إتمام وتأكيد طلبات الشراء حتى باب منزلك.\n\n"
        "💬 **فقط اكتب سؤالك وسأجيبك فوراً!**\n"
        "🧹 استخدم أمر /clear في أي وقت لبدء محادثة جديدة."
    )
    await message.answer(welcome_text, parse_mode=ParseMode.MARKDOWN)


@dp.message(Command("clear"))
async def handle_clear(message: types.Message):
    """مسح سياق المحادثة"""
    if message.from_user and message.from_user.id in user_histories:
        user_histories[message.from_user.id] = []
    await message.answer("🧹 تم مسح ذاكرة المحادثة بنجاح! يمكنك الآن بدء موضوع جديد.")


@dp.message(Command("help"))
async def handle_help(message: types.Message):
    """عرض المساعدة والتعليمات"""
    help_text = (
        "💡 **كيفية استخدام البوت:**\n\n"
        "1. اكتب اسم الكتاب أو التصنيف الذي تبحث عنه (مثال: 'اي كتب الموسيقى عندكم؟').\n"
        "2. يمكنك الاستفسار عن تفاصيل المتجر (مثال: 'المكان بتاعكم فين؟' أو 'مواعيد العمل ايه؟').\n"
        "3. لشراء كتاب، فقط اطلب ذلك وسأساعدك في خطوات الطلب والتوصيل.\n"
        "4. استخدم /clear لمسح المحادثة السابقة والبدء من جديد."
    )
    await message.answer(help_text, parse_mode=ParseMode.MARKDOWN)


@dp.message()
async def handle_all_messages(message: types.Message):
    """استقبال رسائل المستخدم وتمريرها للأجينت والـ RAG"""
    if not message.text or not message.from_user:
        return

    user_id = message.from_user.id
    user_question = message.text.strip()

    # إظهار حالة "يكتب الآن..." في تليجرام
    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    # تجهيز سجل المحادثة السابق
    history_text = get_formatted_history(user_id)

    try:
        # تشغيل دالة ask_bot في Thread منفصل لعدم تجميد الأحداث غير المتزامنة (async)
        bot_response = await asyncio.to_thread(ask_bot, user_question, history_text)

        # حفظ السؤال والإجابة في السجل
        add_to_history(user_id, user_question, bot_response)

        # إرسال الرد للمستخدم بتنسيق Markdown مع fallback إذا وجد خطأ في التنسيق
        try:
            await message.answer(bot_response, parse_mode=ParseMode.MARKDOWN)
        except Exception:
            await message.answer(bot_response)

    except Exception as e:
        logger.error(f"خطأ أثناء معالجة رسالة المستخدم: {e}", exc_info=True)
        await message.answer("⚠️ عذراً، حدث خطأ أثناء معالجة طلبك. يرجى المحاولة مرة أخرى.")


async def main():
    logger.info("🚀 جاري بدء تشغيل بوت تليجرام...")
    # حذف أي رسائل قديمة كانت معلقة أثناء توقف البوت
    await bot.delete_webhook(drop_pending_updates=True)
    
    # بدء استقبال الرسائل (Polling)
    print("\n" + "=" * 50)
    print("🤖 البوت يعمل الآن بنجاح ومستعد لاستقبال الرسائل!")
    print(f"🔗 يمكنك التحدث معه الآن على تليجرام.")
    print("=" * 50 + "\n")
    
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("🛑 تم إيقاف البوت.")
