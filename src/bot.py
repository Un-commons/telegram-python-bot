import os
import datetime
import requests
from random import randrange
from src import log
from dotenv import load_dotenv
from telegram import __version__ as TG_VER
from src.opsupabase import supabase

logger = log.setup_logger(__name__)
load_dotenv()

telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN")

try:
    from telegram import __version_info__
except ImportError:
    __version_info__ = (0, 0, 0, 0, 0)  # type: ignore[assignment]

if __version_info__ < (20, 0, 0, "alpha", 1):
    raise RuntimeError(
        f"This example is not compatible with your current PTB version {TG_VER}. To view the "
        f"{TG_VER} version of this example, "
        f"visit https://docs.python-telegram-bot.org/en/v{TG_VER}/examples.html"
    )
from telegram import (
    KeyboardButton,
    KeyboardButtonPollType,
    Poll,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    PollAnswerHandler,
    PollHandler,
    filters,
)



async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Inform user about what this bot can do"""
    await update.message.reply_text(
        "Please select /poll_list to get the Poll List, /poll id  to start a  poll"
    )


async def me(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Get the user id"""
    try :
        user_id = update.effective_user.id
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Your Telegram User ID: {user_id}")
        logger.info(f"User ID: {user_id} ; Poll From User : {update.message} ")
    except Exception as e:
        logger.error(f"Error fetching user id, Error: {e}")
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Error occurred while fetching User ID.")
        return


async def poll_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Get the poll list  from the supabase"""
    try :
        result = supabase.table("polls").select("*").execute()
        logger.info(f"Poll List: {result}")
        if result:
            polls_formatted_data = [f"{item['id']} - {item['title']}\n" for item in result.data]
            formatted_string = ''.join(polls_formatted_data)
            await context.bot.send_message(
                chat_id=update.effective_chat.id, text=f"The created polls are here, you can choose one to vote: \n ID - TITLE \n{formatted_string}"
            )

    except Exception as e:
        logger.error(f"Error fetching data from Supabase, Error: {e}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id, text=f"Error from Supabase: {e}!\n Please contact the administrator to check! Thank you!"
        )
        return


async def poll(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ poll the vote """
    try :
        logger.info(f"Poll From User : {update.message} ")
        vote_id = update.message.text.split("/poll ")[-1]
        member_result = supabase.table("members").select("*").eq("tg_user_id",int(update.message.from_user.id)).execute()
        logger.info(f"Get Member Result: {member_result} ")
        if member_result.data is None or len(member_result.data) == 0:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Sorry! Only members can start this poll."
            )
            return
        if vote_id.isdigit() is not True:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"Please vote use the command: /poll poll_id, Thank you!"
            )
            return
        result = supabase.table("polls").select("*").eq("id",int(vote_id.strip())).execute()
        logger.info(f"The vote_id: {int(vote_id.strip())} info: {result}")

    except Exception as e:
        logger.error(f"Error fetching data from Supabase, Error: {e}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Error from Supabase: {e}!\n Please contact the administrator to check! Thank you!"
        )
        return
    if len(result.data) == 0:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Can't find the vote_id: {vote_id}! Please use the command: /poll_list check the vote detail!"
        )
        return
    else:
        # 选择一个投票
        poll_data = result.data[0]

        # 从 Supabase 数据中提取投票信息
        poll_title = poll_data["title"]
        poll_options = poll_data["options"]
        poll_only_members = poll_data["only_members"]
        poll_is_anonymous = poll_data["is_anonymous"]
        poll_allows_multiple_answers = poll_data["allows_multiple_answers"]

        poll_id = poll_data["id"]

        # 发起投票
        message = await context.bot.send_poll(
            update.effective_chat.id,
            poll_title,
            poll_options,
            is_anonymous=poll_is_anonymous,  # 投票不再匿名以记录投票者信息
            allows_multiple_answers=poll_allows_multiple_answers,
        )

        # 保存一些关于投票的信息，供稍后在 receive_poll_answer 中使用
        payload = {
            message.poll.id: {
                "questions": poll_options,
                "message_id": message.message_id,
                "chat_id": update.effective_chat.id,
                "answers": 0,
                "only_members": poll_only_members,
                "poll_id": poll_id
            }
        }
        context.bot_data.update(payload)


async def receive_poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Summarize a users poll vote"""
    # if update.poll.is_closed:
    #     return

    answer = update.poll_answer
    poll_answer_id = answer.poll_id
    logger.info(f"Receive Poll Answer: {answer} From {answer.user.id }")
    logger.info(f"Receive Poll Answer Context: {context.bot_data} ")

    try:
        voted_option = context.bot_data[poll_answer_id]["questions"][answer.option_ids[0]]
    except KeyError:
        # this means this poll answer update is from an old poll, we can't do our answering then
        return

    # Get if this poll is members only
    only_members = context.bot_data[poll_answer_id]["only_members"]
    poll_id = context.bot_data[poll_answer_id]["poll_id"]
    print("only_members",only_members)
    if only_members:
        # Check if the user is a member
        member_result = supabase.table("members").select("*").eq("tg_user_id",
                                                                 int(answer.user.id)).execute()
        logger.info(f"Get Vote Member Result: {member_result} ")
        if member_result.data is None or len(member_result.data) == 0:
            return
    # Save the vote in the poll_votes table
    try:
        supabase.table("poll_votes").insert(
            {"poll_id": poll_id, "option": voted_option, "tg_user_id": answer.user.id}).execute()
    except Exception as e:
        print(f"Error saving vote to Supabase, Error: {e}")
        return



async def receive_poll(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """On receiving polls, reply to it by a closed poll copying the received poll"""
    username = update.effective_user.username
    print("receive_poll user: ",username)
    answer = update.poll_answer
    poll_answer_id = answer.poll_id
    only_members = context.bot_data[poll_answer_id]["only_members"]
    poll_id = context.bot_data[poll_answer_id]["poll_id"]
    print("receive_poll only_members", only_members)
    actual_poll = update.effective_message.poll
    # Only need to set the question and options, since all other parameters don't matter for
    # a closed poll
    await update.effective_message.reply_poll(
        question=actual_poll.question,
        options=[o.text for o in actual_poll.options],
        # with is_closed true, the poll/quiz is immediately closed
        is_closed=True,
        reply_markup=ReplyKeyboardRemove(),
    )

def ask_question(question,type=None):
    from src.config import login_url,apikey,quivr_api_url
    login_email: str = os.getenv("quivr_login_email")
    login_password: str = os.getenv("quivr_login_password")

    from src.quivr_script import get_token,quivr_question,quivr_tg_question,quivr_chat
    token = get_token(login_url, login_email, login_password, apikey)
    # if type == "new":
    #     chat_id = quivr_chat(quivr_api_url, question=question, token=token)
    #     assistant_text = quivr_question(quivr_api_url, chat_id=chat_id, question=question, token=token)
    # else:
    #     assistant_text = quivr_tg_question(quivr_api_url, question=question, token=token)
    chat_id = quivr_chat(quivr_api_url, question=question, token=token)
    logger.info(f"ChatID: {chat_id}")

    assistant_text = quivr_question(quivr_api_url, chat_id=chat_id, question=question, token=token)
    return assistant_text


async def chat(update: Update, context):
    question = update.message.text.split(' ', 1)[1]  # split the message into command and question, and get the question part
    question = question.strip().replace('\n', '')
    logger.info(f"question: {question}")
    answer = ask_question(question=question)
    await update.message.reply_text(answer)

async def newchat(update: Update, context):
    question = update.message.text.split(' ', 1)[1]  # split the message into command and question, and get the question part
    answer = ask_question(question,type="new")
    await update.message.reply_text(answer)

async def crawl(update: Update, context):
    url = update.message.text.split(' ', 1)[1]  # split the message into command and question, and get the question part
    from src.quivr_script import get_token, crawl_url
    from src.config import login_url, apikey, quivr_api_url
    login_email: str = os.getenv("quivr_login_email")
    login_password: str = os.getenv("quivr_login_password")
    logger.info(f"Get Input:{url}")
    token = get_token(login_url, login_email, login_password, apikey)
    response = crawl_url(quivr_api_url, url, token)
    logger.info(f"crawl_url_response:{response}")
    await update.message.reply_text(response)

async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display a help message"""
    await update.message.reply_text("Use /poll_list, /poll poll_id or /help to use this vote bot.")


def run_telegram_bot():
    """Run bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(telegram_bot_token).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("me", me))
    application.add_handler(CommandHandler("poll", poll))
    application.add_handler(CommandHandler("poll_list", poll_list))

    application.add_handler(CommandHandler("help", help_handler))
    application.add_handler(MessageHandler(filters.POLL, receive_poll))
    application.add_handler(PollAnswerHandler(receive_poll_answer))
    # application.add_handler(PollHandler(receive_poll_answer))
    application.add_handler(CommandHandler("chat", chat))
    application.add_handler(CommandHandler("newchat", newchat))
    application.add_handler(CommandHandler("crawl", crawl))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


