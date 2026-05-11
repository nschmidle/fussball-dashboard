import json
import os
import subprocess
import time

import requests

API_BASE = "https://api.openligadb.de"

LEAGUES = {
    "bl1":  "1. Bundesliga",
    "bl2":  "2. Bundesliga",
    "bl3":  "3. Liga",
    "dfb":  "DFB-Pokal",
    "ucl":  "Champions League",
    "uel":  "Europa League",
}

POLL_INTERVAL = 30

KNOWN_GOALS_FILE = "known_goals.json"
HAS_WINDOWS_NOTIFY = os.name == "nt" or subprocess.run(
    "which powershell.exe", shell=True, capture_output=True
).returncode == 0


def load_known_goals():
    if os.path.exists(KNOWN_GOALS_FILE):
        with open(KNOWN_GOALS_FILE) as f:
            return set(json.load(f))
    return set()


def save_known_goals(goal_ids):
    with open(KNOWN_GOALS_FILE, "w") as f:
        json.dump(list(goal_ids), f)


def notify_windows(title, text):
    cmd = [
        "powershell.exe",
        "-Command",
        f"""
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
$template = [Windows.UI.Notifications.ToastTemplateType]::ToastText02
$toastXml = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent($template)
$textNodes = $toastXml.GetElementsByTagName("text")
$textNodes.Item(0).AppendChild($toastXml.CreateTextNode("{title}")) > $null
$textNodes.Item(1).AppendChild($toastXml.CreateTextNode("{text}")) > $null
$toast = [Windows.UI.Notifications.ToastNotification]::new($toastXml)
$notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("Bundesliga Watcher")
$notifier.Show($toast)
"""
    ]
    try:
        subprocess.run(cmd, capture_output=True, timeout=5)
    except Exception:
        pass


def notify(text):
    print(f"\n\u26bd  GOAL! {text}")
    print("\a", end="", flush=True)
    if HAS_WINDOWS_NOTIFY:
        if " \u2192 " in text:
            title, body = text.split(" \u2192 ", 1)
            notify_windows(title, body)


def poll():
    known_goals = load_known_goals()
    notify_type = "Windows + Terminal" if HAS_WINDOWS_NOTIFY else "Terminal"

    print(f"Watching: {', '.join(LEAGUES.values())}")
    print(f"Polling every {POLL_INTERVAL}s  |  Notifications: {notify_type}")
    print(f"Known goals: {len(known_goals)}  |  Ctrl+C to stop\n")

    while True:
        try:
            new_goals = 0
            for shortcut, name in LEAGUES.items():
                resp = requests.get(
                    f"{API_BASE}/getmatchdata/{shortcut}", timeout=10
                )
                resp.raise_for_status()
                matches = resp.json()

                for match in matches:
                    t1 = match["team1"]["teamName"]
                    t2 = match["team2"]["teamName"]
                    group = match.get("group", {}).get("groupName", "")
                    league_label = f"[{name}]" if len(LEAGUES) > 1 else ""

                    for goal in match["goals"]:
                        gid = goal["goalID"]
                        if gid not in known_goals:
                            known_goals.add(gid)
                            new_goals += 1
                            scorer = goal["goalGetterName"]
                            minute = goal["matchMinute"]
                            s1 = goal["scoreTeam1"]
                            s2 = goal["scoreTeam2"]
                            notify(
                                f"{league_label} {scorer} ({minute}') \u2192 "
                                f"{t1} {s1}:{s2} {t2}"
                            )

            if new_goals:
                save_known_goals(known_goals)
                print(f"(+{new_goals} new, {len(known_goals)} total goals tracked)")

        except KeyboardInterrupt:
            raise
        except Exception as e:
            print(f"Error: {e}")

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    poll()
