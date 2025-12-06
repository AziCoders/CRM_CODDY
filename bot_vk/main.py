from vkbottle import Bot, Message
from vkbottle.bot import Message

bot = Bot("<VK_GROUP_TOKEN>")

@bot.on.message(text="привет")
async def hi_handler(message: Message):
    await message.answer("Привет! Я рабочий VK-бот для CRM 😊")

bot.run_forever()
