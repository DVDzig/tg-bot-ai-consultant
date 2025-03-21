from datetime import datetime, timedelta

# Админские ID для исключения из лидерборда
ADMIN_IDS = ["150532949"]

def get_leaderboard(user_data, period="all"):
    now = datetime.now()
    leaderboard = []

    for user in user_data:
        user_id = str(user.get("user_id", ""))
        if user_id in ADMIN_IDS:
            continue

        xp = int(user.get("xp", 0))
        last_interaction_str = user.get("last_interaction", "")

        try:
            last_interaction = datetime.strptime(last_interaction_str, '%Y-%m-%d %H:%M:%S')
        except Exception:
            continue

        if period == "week" and (now - last_interaction).days > 7:
            continue
        elif period == "today" and last_interaction.date() != now.date():
            continue

        leaderboard.append((user.get("username", "Без имени"), xp))

    leaderboard.sort(key=lambda x: x[1], reverse=True)
    return leaderboard[:10]

def format_leaderboard(leaderboard, title):
    if not leaderboard:
        return f"{title} – пока нет участников."

    result_text = f"{title} – Топ 10\n\n"
    for idx, (username, xp) in enumerate(leaderboard, start=1):
        result_text += f"{idx}. {username}: {xp} XP\n"
    return result_text
