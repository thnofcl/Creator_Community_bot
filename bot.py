import logging
import os
from google import genai
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Bot Token
BOT_TOKEN = os.getenv('BOT_TOKEN')

# Gemini API Key
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
client = genai.Client(api_key=GEMINI_API_KEY)

# Bot username (will be set on startup)
BOT_USERNAME = None

# Dictionary to store user warnings
user_warnings = {}

# Welcome Message
WELCOME_MESSAGE = (
    "Creator Community မှ ကြိုဆိုလိုက်ပါတယ်။ member အသစ်များအားလုံး editing skill နှင့် graphic design ပိုင်းဆိုင်ရာ အကူအညီများ လိုအပ်ပါက မေးမြန်းဆွေးနွေးနိုင်ပါသည်။\n\n"
    "Group rule များကို /rules နှိပ်ပြီး ဖတ်ရှုပြီးလိုက်နာပေးပါရန် မေတ္တာရပ်ခံအပ်ပါသည်။\n\n"
    "CC member အတူတကွ ပူးပေါင်းဖန်တီးကြမယ်။"
)

# Group Rules
GROUP_RULES = (
    "📋 Creator Community Group Rules\n\n"
    "1. ကုန်ပစ္စည်းရောင်းချခြင်း/ကြော်ငြာခြင်း မပြုရ\n"
    "2. ပြင်ပကြေညာများ Forward ခြင်း မပြုရ\n"
    "3. 18+ အကြောင်းအရာများ တင်ခြင်း မပြုရ (ချိုးဖောက်ရင် 2 ခါ warn တာနဲ့ ban ပါမည်)\n"
    "4. Spam များ မပြုလုပ်ရ\n"
    "5. အချင်းချင်းလေးစားပါ\n"
    "6. ခေါင်းစဉ်နှင့် ကိုက်ညီပါစေ (editing, design, content creation)\n"
    "7. မူပိုင်ခွင့်ကို လေးစားပါ\n"
    "8. အချင်းချင်း အကူအညီပေးပြီး အပြုသဘောဆောင်သော ဆွေးနွေးမှုများကိုသာ ပြုလုပ်ပါ"
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Hello! I am your Creator Community Bot. Type /rules to see the group rules.")

async def welcome_new_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        if not member.is_bot:
            if member.username:
                mention = f"@{member.username}"
            else:
                mention = member.full_name
            welcome_text = (
                f"{mention} - Creator Community မှ ကြိုဆိုလိုက်ပါတယ်။ member အသစ်များအားလုံး editing skill နှင့် graphic design ပိုင်းဆိုင်ရာ အကူအညီများ လိုအပ်ပါက မေးမြန်းဆွေးနွေးနိုင်ပါသည်။\n\n"
                "Group rule များကို /rules နှိပ်ပြီး ဖတ်ရှုပြီးလိုက်နာပေးပါရန် မေတ္တာရပ်ခံအပ်ပါသည်။\n\n"
                "CC member အတူတကွ ပူးပေါင်းဖန်တီးကြမယ်။"
            )
            await context.bot.send_message(chat_id=update.effective_chat.id, text=welcome_text)

async def show_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text=GROUP_RULES)

async def ai_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    global BOT_USERNAME
    if BOT_USERNAME is None:
        bot_info = await context.bot.get_me()
        BOT_USERNAME = bot_info.username

    message = update.message
    user_text = message.text
    chat_type = update.effective_chat.type

    # In group chats, only respond when mentioned or replied to
    if chat_type in ['group', 'supergroup']:
        is_mentioned = f"@{BOT_USERNAME}" in user_text
        is_reply_to_bot = (
            message.reply_to_message is not None
            and message.reply_to_message.from_user is not None
            and message.reply_to_message.from_user.username == BOT_USERNAME
        )

        if not is_mentioned and not is_reply_to_bot:
            return

        # Remove bot mention from the text
        user_text = user_text.replace(f"@{BOT_USERNAME}", "").strip()

    if not user_text:
        return

    prompt = (
        "You are a knowledgeable creator community assistant that helps with editing skills, graphic design, and content creation questions. "
        "Reply in Burmese/Myanmar language mixed with English technical terms. "
        "Keep your answers helpful and concise. "
        f"User asks: {user_text}"
    )
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt
        )
        ai_text = response.text
        await context.bot.send_message(chat_id=update.effective_chat.id, text=ai_text, reply_to_message_id=message.message_id)
    except Exception as e:
        logging.error(f"Error calling Gemini API: {e}")
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Sorry, I couldn't process that request right now. Please try again later.")

async def warn_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Please reply to the message of the user you want to warn.")
        return

    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    member = await context.bot.get_chat_member(chat_id, user_id)

    if member.status not in ['administrator', 'creator']:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="You must be an administrator to use this command.")
        return

    user_to_warn_id = update.message.reply_to_message.from_user.id
    user_to_warn_name = update.message.reply_to_message.from_user.full_name

    user_warnings[user_to_warn_id] = user_warnings.get(user_to_warn_id, 0) + 1
    warn_count = user_warnings[user_to_warn_id]

    if warn_count >= 2:
        try:
            await context.bot.ban_chat_member(chat_id, user_to_warn_id)
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"{user_to_warn_name} သည် 2 ကြိမ်မြောက် သတိပေးခံရ၍ အဖွဲ့မှ ban ခံရပါပြီ။")
            del user_warnings[user_to_warn_id]
        except Exception as e:
            logging.error(f"Error banning user after warnings: {e}")
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Failed to ban user after warnings. Make sure the bot has admin privileges.")
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"⚠️ {user_to_warn_name} - သတိပေးချက် {warn_count}/2 ရရှိပါပြီ။ 2 ကြိမ်မြောက် warn ရရင် ban ခံရပါမည်။")

async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Please reply to the message of the user you want to ban.")
        return

    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    member = await context.bot.get_chat_member(chat_id, user_id)

    if member.status not in ['administrator', 'creator']:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="You must be an administrator to use this command.")
        return

    user_to_ban_id = update.message.reply_to_message.from_user.id
    user_to_ban_name = update.message.reply_to_message.from_user.full_name

    try:
        await context.bot.ban_chat_member(chat_id, user_to_ban_id)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"{user_to_ban_name} has been banned.")
        if user_to_ban_id in user_warnings:
            del user_warnings[user_to_ban_id]
    except Exception as e:
        logging.error(f"Error banning user: {e}")
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Failed to ban user. Make sure the bot has admin privileges to ban members.")

def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_members))
    application.add_handler(CommandHandler("rules", show_rules))
    application.add_handler(CommandHandler("warn", warn_user))
    application.add_handler(CommandHandler("ban", ban_user))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ai_response))

    application.run_polling()

if __name__ == '__main__':
    main()
