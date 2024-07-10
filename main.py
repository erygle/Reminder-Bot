import discord
import os
from discord.message import Message
from dotenv import load_dotenv
from datetime import datetime
import requests
import re
import math
import random
from keep_alive import keep_alive
import pytz
import aiohttp

load_dotenv()  # .env dosyasını yükler ve ortam değişkenlerine ekler

intents = discord.Intents.default()  # Varsayılan intentleri kullanır
intents.messages = True  # Mesajlarla ilgili etkinlikleri izlemeye izin verir
intents.guilds = True  # Sunucu (guild) etkinliklerini izlemeye izin verir
intents.message_content = True

client = discord.Client(intents=intents)

events = []
current_page = 0
page_size = 5

@client.event
async def on_ready():
    print(f"Logged in as {client.user}")
    await fetch_events()

async def fetch_events():
    global events, current_page, page_size
    print("Fetching today's historical events...")

    now = datetime.now(pytz.timezone('Europe/Istanbul'))
    date = now.strftime("%m/%d")  # API'nin beklediği formatta tarih

    url = f'https://api.wikimedia.org/feed/v1/wikipedia/en/onthisday/all/{date}'

    response = requests.get(url)

    if response.status_code == 200:
        events = response.json().get('events', [])
        if not events:
            print("No historical events found for today.")
            return

        current_page = 0
        total_pages = math.ceil(len(events) / page_size)
        response_message = f"Number of historical events: *{len(events)}*. Total pages: *{total_pages}*.\n"
        print(response_message)
    else:
        print(f"An error occurred while fetching today's historical events. Status code: {response.status_code}")

def split_message(message, max_length=2000):
    # Mesajı parçalara bölen yardımcı fonksiyon
    return [message[i:i + max_length] for i in range(0, len(message), max_length)]

def clean_text(text):
    # Metni temizleyen yardımcı fonksiyon
    text = re.sub(r'\s+', ' ', text)  # Fazla boşlukları temizle
    text = text.replace("\n", " ")  # Yeni satırları boşlukla değiştir
    text = re.sub(r'([a-zA-Z])([\.,!?])', r'\1 \2', text)  # Noktalama işaretlerinden önce boşluk ekle
    return text

def get_page(events, page, page_size):
    start = page * page_size
    end = start + page_size
    return events[start:end]

def create_response_message(events, page, page_size):
    total_events = len(events)
    total_pages = math.ceil(total_events / page_size)
    page_events = get_page(events, page, page_size)

    response_message=""
    #response_message = f"Page {page + 1}/{total_pages}\n"
    for event in page_events:
        year = event['year']
        description = clean_text(event['text'])
        response_message += f"`{year}` - *{description}*\n"  # İtalik yapmak için yıldız işaretleri kullanılır

    response_message += f"Page {page + 1}/{total_pages}\n"
    
    return response_message

@client.event
async def on_message(message):
    global events, current_page, page_size

    if message.author == client.user:
        return

    content = message.content.lower()  # Mesaj içeriğini küçük harfe çevir

    if content.startswith("hello"):
        await message.channel.send("Hello!")

    if any(content.startswith(prefix) for prefix in ["eyvallah", "eyv", "eyw"]):
        await message.channel.send("Ne demek canım")

    if any(content.startswith(greet) for greet in ["selamın aleyküm", "selamınaleyküm", "sa", "sea"]):
        async with aiohttp.ClientSession() as session:
            async with session.get("https://cdn.discordapp.com/attachments/1260191025528307725/1260517782672506900/image.png?ex=668f9c2a&is=668e4aaa&hm=16a4b7bf641bf5b6d5bb4e5442c7e3946a6fe498046d298f323fface92a2af8b&") as resp:
                if resp.status == 200:
                    data = await resp.read()
                    with open("image.png", "wb") as f:
                        f.write(data)
                    await message.channel.send(file=discord.File("image.png"))
    
    if content.startswith(".events"):
        await message.channel.send("Fetching today's historical events...")

        now = datetime.now(pytz.timezone('Europe/Istanbul'))
        date = now.strftime("%m/%d")  # API'nin beklediği formatta tarih

        url = f'https://api.wikimedia.org/feed/v1/wikipedia/en/onthisday/all/{date}'

        response = requests.get(url)

        if response.status_code == 200:
            events = response.json().get('events', [])
            if not events:
                await message.channel.send("No historical events found for today.")
                return

            current_page = 0
            total_pages = math.ceil(len(events) / page_size)
            response_message = f"Number of historical events: *{len(events)}*. Total pages: *{total_pages}*.\n"
            response_message += create_response_message(events, current_page, page_size)

            for part in split_message(response_message):
                await message.channel.send(part)
        else:
            await message.channel.send(f"An error occurred while fetching today's historical events. Status code: {response.status_code}")

    if content.startswith(".next"):
        total_pages = math.ceil(len(events) / page_size)
        if current_page < total_pages - 1:
            current_page += 1
            response_message = create_response_message(events, current_page, page_size)

            for part in split_message(response_message):
                await message.channel.send(part)
        else:
            await message.channel.send("No more events to display.")

    if content.startswith(".page"):
        total_pages = math.ceil(len(events) / page_size)
        try:
            page_number = int(message.content.split()[1]) - 1
            if 0 <= page_number < total_pages:
                current_page = page_number
                response_message = create_response_message(events, current_page, page_size)

                for part in split_message(response_message):
                    await message.channel.send(part)
            else:
                await message.channel.send(f"Invalid page number. Please enter a number between 1 and {total_pages}.")
        except (IndexError, ValueError):
            await message.channel.send("Please provide a valid page number after the .page command.")

    if content.startswith(".random"):
        if not events:
            await fetch_events()
        random_event = random.choice(events)
        year = random_event['year']
        description = clean_text(random_event['text'])
        await message.channel.send(f"`{year}` - *{description}*")

    if content.startswith(".quote"):
        url_quote = 'https://zenquotes.io/api/today'
        response = requests.get(url_quote)
        if response.status_code == 200:
            data = response.json()
            quote = data[0]['q']
            author = data[0]['a']
            await message.channel.send(f'*"{quote}"* - {author}')  # Sözün kendisi italik yapılır
        else:
            await message.channel.send("An error occurred while fetching the quote.")

    if content.startswith(".date"):
        now = datetime.now(pytz.timezone('Europe/Istanbul'))
        date_time = now.strftime("%Y-%m-%d %H:%M:%S %Z%z")
        await message.channel.send(f"Current date and time: {date_time}")

    if content.startswith(".help"):
        help_message = (
            "**Here are the available commands:**\n"
            "`hello` - Greet the bot.\n"
            "`.events` - Fetch and display today's historical events.\n"
            "`.next` - Display the next page of historical events.\n"
            "`.page <number>` - Display a specific page of historical events.\n"
            "`.random` - Display a random historical event from today.\n"
            "`.quote` - Display a random quote.\n"
            "`.date` - Display the current date and time.\n"
            "`.help` - Display this help message."
        )
        await message.channel.send(help_message)
    
keep_alive()
client.run(os.getenv('TOKEN'))
