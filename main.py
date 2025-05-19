import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

from verification import VerificationView, process_dm_captcha, active_verifications
from thread import auto_create_thread

load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
TARGET_CHANNEL_ID = 1373979886632435824
VERIFICATION_ROLE_ID = 1373971440013021205
COMMAND_PREFIX = "makaka!"
ALLOWED_USER_ID = 1047913800675905536

if DISCORD_TOKEN is None:
    print("Ошибка: Токен бота не найден...")
    exit()

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True 
intents.members = True 
intents.dm_messages = True

bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents)

@bot.event
async def on_ready():
    print(f'Бот {bot.user.name} подключен и готов к работе!')
    print(f'ID бота: {bot.user.id}')
    
    bot.add_view(VerificationView(role_id=VERIFICATION_ROLE_ID, bot_instance=bot))
    print("View для верификации (DM) зарегистрирована.")
    print('------')

@bot.event
async def on_message(message: discord.Message):
    if message.author == bot.user: 
        return

    if isinstance(message.channel, discord.DMChannel):
        await process_dm_captcha(message, bot)
        return

    await bot.process_commands(message)

    ctx = await bot.get_context(message)
    if ctx.valid: 
        return
    
    await auto_create_thread(message, TARGET_CHANNEL_ID)


@bot.command(name="verify")
@commands.guild_only() 
async def verify_command(ctx: commands.Context):
    if ctx.author.id != ALLOWED_USER_ID:
        await ctx.send("У вас нет прав для использования этой команды.", ephemeral=True)
        return

    guild = ctx.guild
    role = guild.get_role(VERIFICATION_ROLE_ID)
    if not role:
        await ctx.send(f"Ошибка: Роль с ID {VERIFICATION_ROLE_ID} не найдена...")
        return

    embed = discord.Embed(
        title="✅ Верификация на сервере",
        description=(
            f"Добро пожаловать на сервер **{ctx.guild.name}**!\n\n"
            "Чтобы получить доступ к остальным каналам и подтвердить, что вы не бот, "
            "нажмите кнопку **'Пройти верификацию'** ниже.\n\n"
            f"Капча будет отправлена вам в личные сообщения."
        ),
        color=discord.Color.green()
    )
    embed.set_footer(text="Если возникнут проблемы, обратитесь к администрации.")
    
    await ctx.send(embed=embed, view=VerificationView(role_id=VERIFICATION_ROLE_ID, bot_instance=bot))
    try:
        await ctx.message.delete()
    except discord.Forbidden:
        print(f"Не удалось удалить сообщение команды от {ctx.author.name} (нет прав).")
    except discord.HTTPException:
        print(f"Ошибка при удалении сообщения команды от {ctx.author.name}.")

try:
    bot.run(DISCORD_TOKEN)
except discord.LoginFailure:
    print("Ошибка входа...")
except Exception as e:
    print(f"Ошибка при запуске бота: {e}")