#!/usr/bin/python3
# Bill Sideris <bill88t@feline.gr>

# This file is licenced under the GPLv3 Licence.

import re
import json
import base64
import requests
import discord
import asyncio
import json
import datetime
from discord.ext import commands, tasks

from credentials import *

# Secrets must contain:

# TOKEN = str
# CHANNEL_ID = int
# AUTHORIZED_ROLE = str

day_map = {
    "ΔΕΥΤΕΡΑ": 0,
    "ΤΡΙΤΗ": 1,
    "ΤΕΤΑΡΤΗ": 2,
    "ΠΕΜΠΤΗ": 3,
    "ΠΑΡΑΣΚΕΥΗ": 4,
    "ΣΑΒΒΑΤΟ": 5,
    "ΚΥΡΙΑΚΗ": 6,
}

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


def odd_week(date_str: str = "2025-03-10") -> int:
    start_date = datetime.datetime.strptime(date_str, "%Y-%m-%d")
    today = datetime.datetime.today()
    return bool(((today - start_date).days // 7) % 2)


def gen_schedule(week: bool = False) -> list:
    js_code = None

    try:
        response = requests.get("https://iam.uniwa.gr/static/js/main.fa92022a.js")
        response.raise_for_status()
        js_code = response.text
    except requests.RequestException as e:
        print(f"Error fetching JavaScript: {e}")

    if not js_code:
        return

    json_pattern = re.compile(r"({.*?})", re.DOTALL)
    json_candidates = json_pattern.findall(js_code)

    days = [None] * 7
    for candidate in json_candidates:
        try:
            parsed = json.loads(candidate.replace("\n", ""))
            if (
                ("day" in parsed)
                and ("timeslots" not in parsed)
                and (days[day_map[parsed["day"]]] is None or odd_week())
            ):
                days[day_map[parsed["day"]]] = parsed
        except json.JSONDecodeError:
            continue

    if not week:
        return [days[datetime.datetime.today().weekday()]]
    else:
        return days


@tasks.loop(time=datetime.time(hour=3, minute=30, second=0))
async def send_daily_message(week: bool = False):
    schedules = gen_schedule(week)
    channel = bot.get_channel(CHANNEL_ID)
    doverride = 0

    for schedule in schedules:
        is_weekday = (
            datetime.datetime.today().weekday() if not week else doverride
        ) < 5
        doverride += 1
        breakfast_time = "07:30-09:00" if is_weekday else "Δεν έχει."
        lunch_time = "12:30-15:30" if is_weekday else "13:00-18:00"
        supper_time = "18:00-20:00"

        message = f'# Ημερήσιο πρόγραμμα: {schedule["day"]}\n\nΠρωινό - **{breakfast_time}**\nΜεσημεριανό - **{lunch_time}**\nΒραδινό - **{supper_time}**\n\n# Μενού:\n'
        if schedule["breakfast"]:
            message += "**Πρωινό:**\n"
            for i in schedule["breakfast"]:
                message += f"- *{i}*\n"

        message += f'**Μεσημεριανό:**\n- *{schedule["gevmaKirios"]}*\n- *{schedule["gevmaEidiko"]}*\n- *{schedule["gevmaPrwtoPiato"]}*\n- *{schedule["gevmaSinodeutika"]}*\n'
        if schedule["gevmaEpidorpio"]:
            message += f'- **{schedule["gevmaEpidorpio"]}**\n'

        message += f'**Βραδινό:**\n- *{schedule["deipnoKirios"]}*\n- *{schedule["deipnoEidiko"]}*\n- *{schedule["deipnoSinodeutika"]}*\n'
        if schedule["deipnoEpidorpio"]:
            message += f'- **{schedule["deipnoEpidorpio"]}**\n'

        if channel:
            await channel.send(message)
            await asyncio.sleep(2)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    send_daily_message.start()


@bot.command()
async def resend(ctx):
    if any(role.name == AUTHORIZED_ROLE for role in ctx.author.roles):
        await send_daily_message()
    else:
        print("Unauthorized execution of !resend.")


@bot.command()
async def week(ctx):
    if any(role.name == AUTHORIZED_ROLE for role in ctx.author.roles):
        await send_daily_message(week=True)
    else:
        print("Unauthorized execution of !resend.")


if __name__ == "__main__":
    bot.run(TOKEN)
