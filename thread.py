import discord

async def auto_create_thread(message: discord.Message, target_channel_id: int):
    if message.author.bot:
        return
    if message.channel.id != target_channel_id:
        return

    try:
        thread_name = "Комментарии"
        thread_name = thread_name[:100]

        created_thread = await message.create_thread(
            name=thread_name,
            auto_archive_duration=10080
        )
        print(f"Создана ветка '{created_thread.name}' для сообщения ID {message.id} в канале '{message.channel.name}'")

    except discord.Forbidden:
        print(f"Ошибка: У бота нет прав на создание веток в канале '{message.channel.name}' (ID: {message.channel.id}).")
    except discord.HTTPException as e:
        print(f"Ошибка HTTP при создании ветки: {e.status} - {e.text}")
    except Exception as e:
        print(f"Произошла непредвиденная ошибка при создании ветки: {e}")