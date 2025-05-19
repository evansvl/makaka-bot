import discord
import random
import string
import io
from PIL import Image, ImageDraw, ImageFont
import os
import asyncio

def generate_captcha_text(length=6):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def generate_captcha_image(text: str, width=320, height=100):
    image = Image.new('RGB', (width, height), color=(220, 220, 220))
    draw = ImageDraw.Draw(image)
    font_name = "dejavusans.ttf" if os.name != 'nt' else "arial.ttf"
    font_size = random.randint(45, 55)
    try:
        font_path = font_name
        if os.name == 'nt':
             font_path_win = os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts", font_name)
             if os.path.exists(font_path_win): font_path = font_path_win
        elif os.path.exists(f"/usr/share/fonts/truetype/dejavu/{font_name}"):
            font_path = f"/usr/share/fonts/truetype/dejavu/{font_name}"
        font = ImageFont.truetype(font_path, size=font_size)
    except IOError:
        print(f"Шрифт '{font_name}' не найден, используется стандартный шрифт.")
        font = ImageFont.load_default()

    text_bbox = draw.textbbox((0,0), text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    x = (width - text_width - text_bbox[0]) / 2
    y = (height - text_height - text_bbox[1]) / 2

    for _ in range(random.randint(300, 500)):
        dot_x, dot_y = random.randint(0, width - 1), random.randint(0, height - 1)
        dot_color = (random.randint(0, 200), random.randint(0, 200), random.randint(0, 200))
        draw.point((dot_x, dot_y), fill=dot_color)

    for _ in range(random.randint(5, 10)):
        line_x1, line_y1 = random.randint(0, width -1), random.randint(0, height -1)
        line_x2, line_y2 = random.randint(0, width -1), random.randint(0, height -1)
        line_color = (random.randint(100, 200), random.randint(100, 200), random.randint(100, 200))
        draw.line([(line_x1, line_y1), (line_x2, line_y2)], fill=line_color, width=random.randint(1,2))

    text_color = (random.randint(0, 80), random.randint(0, 80), random.randint(0, 80))
    draw.text((x, y), text, font=font, fill=text_color)

    num_strikethrough_lines = random.randint(1, 3)
    for i in range(num_strikethrough_lines):
        line_y_offset = (text_height / (num_strikethrough_lines + 1)) * (i + 1) - (text_height / 2)
        strikethrough_y = y + text_height / 2 + line_y_offset + random.randint(-5, 5)
        start_x, end_x = x + random.randint(-10, 0), x + text_width + random.randint(0, 10)
        strikethrough_color = (random.randint(0, 150), random.randint(0, 150), random.randint(0, 150))
        draw.line([(start_x, strikethrough_y), (end_x, strikethrough_y)], fill=strikethrough_color, width=random.randint(2, 3))

    image_bytes = io.BytesIO()
    image.save(image_bytes, format='PNG')
    image_bytes.seek(0)
    return image_bytes

active_verifications = {}
VERIFICATION_TIMEOUT = 300

class VerificationView(discord.ui.View):
    def __init__(self, role_id: int, bot_instance):
        super().__init__(timeout=None)
        self.role_id = role_id
        self.bot = bot_instance
    @discord.ui.button(label="Пройти верификацию", style=discord.ButtonStyle.green, custom_id="persistent_verification_button_dm")
    async def verify_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = interaction.user
        guild = interaction.guild

        if not guild:
            await interaction.response.send_message("Эта команда должна использоваться на сервере.", ephemeral=True)
            return

        if user.id in active_verifications:
            try:
                dm_msg = await user.fetch_message(active_verifications[user.id]['message_id'])
                await interaction.response.send_message(
                    f"Вы уже начали процесс верификации. Пожалуйста, проверьте ваши личные сообщения от меня ({dm_msg.jump_url}). "
                    f"Осталось попыток: {active_verifications[user.id]['attempts_left']}",
                    ephemeral=True
                )
            except discord.NotFound:
                 del active_verifications[user.id]
                 await interaction.response.send_message(
                    "Кажется, предыдущая сессия верификации была прервана. Попробуйте снова.",
                    ephemeral=True
                )
            except Exception as e:
                print(f"Ошибка при проверке активной верификации для {user.name}: {e}")
                await interaction.response.send_message("Произошла ошибка. Попробуйте снова.", ephemeral=True)
            return
        
        role_to_assign = guild.get_role(self.role_id)
        if not role_to_assign:
            await interaction.response.send_message("Критическая ошибка: Роль для верификации не найдена. Обратитесь к администратору.", ephemeral=True)
            return

        member = guild.get_member(user.id)
        if not member:
             await interaction.response.send_message("Не удалось получить информацию о вас как участнике сервера.", ephemeral=True)
             return

        if role_to_assign in member.roles:
            await interaction.response.send_message(f"Вы уже верифицированы и имеете роль **{role_to_assign.name}**.", ephemeral=True)
            return
        
        await interaction.response.send_message(
            "Капча для верификации была отправлена вам в личные сообщения. Пожалуйста, проверьте их.",
            ephemeral=True
        )

        captcha_text = generate_captcha_text()
        try:
            image_data_bytes = generate_captcha_image(captcha_text)
            captcha_file = discord.File(fp=image_data_bytes, filename="captcha.png")
        except Exception as e:
            print(f"Ошибка генерации изображения капчи: {e}")
            await interaction.followup.send("Произошла ошибка при генерации капчи. Попробуйте позже.", ephemeral=True)
            return

        try:
            dm_message_content = (
                f"Здравствуйте! Для верификации на сервере **{guild.name}** введите код с картинки ниже.\n"
                f"У вас **5** попыток. Время на ввод капчи: {VERIFICATION_TIMEOUT // 60} минут."
            )
            dm_message = await user.send(content=dm_message_content, file=captcha_file)
            
            active_verifications[user.id] = {
                "captcha_text": captcha_text,
                "attempts_left": 5,
                "guild_id": guild.id,
                "role_id": self.role_id,
                "message_id": dm_message.id,
                "interaction_token": interaction.token
            }
            
            self.bot.loop.create_task(self.captcha_timeout(user.id, guild.name))

        except discord.Forbidden:
            await interaction.followup.send(
                "Не удалось отправить вам капчу в личные сообщения. "
                "Убедитесь, что ваши ЛС открыты для участников этого сервера (Настройки пользователя -> Конфиденциальность -> 'Разрешить личные сообщения от участников сервера'), и попробуйте снова.",
                ephemeral=True
            )
        except Exception as e:
            print(f"Ошибка при отправке ЛС с капчей для {user.name}: {e}")
            await interaction.followup.send(
                 "Произошла ошибка при отправке вам капчи. Пожалуйста, попробуйте позже.",
                 ephemeral=True
            )

    async def captcha_timeout(self, user_id: int, guild_name: str):
        await asyncio.sleep(VERIFICATION_TIMEOUT)
        if user_id in active_verifications:
            user = self.bot.get_user(user_id)
            if user:
                try:
                    original_dm_message_id = active_verifications[user_id].get('message_id')
                    dm_message = None
                    if original_dm_message_id:
                        try:
                            dm_message = await user.fetch_message(original_dm_message_id)
                        except discord.NotFound:
                            pass
                        except discord.Forbidden:
                            pass

                    await user.send(
                        f"Время на прохождение верификации для сервера **{guild_name}** истекло. "
                        "Нажмите кнопку верификации на сервере еще раз, если хотите попробовать снова."
                    )
                    if dm_message:
                        pass
                except discord.Forbidden:
                    print(f"Не удалось отправить сообщение об истечении таймаута капчи пользователю {user_id} (ЛС закрыты).")
                except Exception as e:
                    print(f"Ошибка при отправке сообщения о таймауте капчи пользователю {user_id}: {e}")
            del active_verifications[user_id]
            print(f"Сессия верификации для {user_id} истекла и удалена.")

async def process_dm_captcha(message: discord.Message, bot: 'discord.ext.commands.Bot'):
    """Обрабатывает сообщения в ЛС, проверяя их на ответы капчи."""
    if message.author.bot:
        return
    if not isinstance(message.channel, discord.DMChannel):
        return

    user_id = message.author.id
    if user_id not in active_verifications:
        return

    session = active_verifications[user_id]
    user_input = message.content.strip().upper()
    correct_captcha = session["captcha_text"].upper()

    guild = bot.get_guild(session["guild_id"])
    if not guild:
        await message.channel.send("Ошибка: Сервер, для которого вы проходили верификацию, больше не доступен.")
        if user_id in active_verifications:
            del active_verifications[user_id]
        return

    if user_input == correct_captcha:
        role = guild.get_role(session["role_id"])
        if not role:
            await message.channel.send("Ошибка: Роль для верификации не найдена на сервере.")
            if user_id in active_verifications: del active_verifications[user_id]
            return

        member = guild.get_member(user_id)
        if not member:
            await message.channel.send("Ошибка: Не удалось найти вас на сервере.")
            if user_id in active_verifications: del active_verifications[user_id]
            return

        try:
            if role not in member.roles:
                await member.add_roles(role, reason="Успешная верификация через капчу")
                await message.channel.send(f"🎉 Поздравляю! Вы успешно верифицированы на сервере **{guild.name}** и получили роль **{role.name}**.")
            else:
                await message.channel.send(f"У вас уже есть роль **{role.name}** на сервере **{guild.name}**.")
            if user_id in active_verifications: del active_verifications[user_id]
        except discord.Forbidden:
            await message.channel.send("Ошибка: У меня нет прав для выдачи вам роли на сервере. Пожалуйста, обратитесь к администратору.")
        except Exception as e:
            await message.channel.send(f"Произошла непредвиденная ошибка при выдаче роли: {e}")
            print(f"Ошибка при выдаче роли {user_id} на сервере {guild.id}: {e}")
    else:
        session["attempts_left"] -= 1
        if session["attempts_left"] > 0:
            await message.channel.send(
                f"Неверный код. Попробуйте еще раз. Осталось попыток: **{session['attempts_left']}**."
            )
        else:
            await message.channel.send(
                f"Вы исчерпали все попытки. Для новой попытки верификации, пожалуйста, снова нажмите кнопку на сервере **{guild.name}**."
            )
            if user_id in active_verifications: del active_verifications[user_id]