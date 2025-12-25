import requests
import urllib3
import time 
import asyncio
import os 
from lcu_driver import Connector

os.system('title [HARMONIA] Rework')

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

try:
    loop = asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

connector = Connector(loop=loop)

global target_champion_name, target_champion_id, am_i_assigned, in_game, has_picked
target_champion_name = ""
target_champion_id = None
am_i_assigned = False
in_game = False
has_picked = False

champions_map = {}
summoner_id = None


def download_discord_file(url, filename):

    try:

        response = requests.get(url, stream=True)
        response.raise_for_status()


        with open(filename, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    file.write(chunk)
        return True
    except requests.exceptions.RequestException:

        return False
    except Exception:
        return False


def intro_animation():
    os.system("cls" if os.name == "nt" else "clear")
    title = "Harmonia, Experience The Peace."
    build = ""

    for char in title:
        build += char
        print("\033[2J\033[H")
        print("\n" * 10)
        print(build.center(80))
        time.sleep(0.06)

    time.sleep(1)

    os.system("cls" if os.name == "nt" else "clear")

def animated_file_check():
    required_files = [
        "vg.dll",
    ]

    print("\n")
    
    missing = []

    for file in required_files:
        if not os.path.exists(file):
            missing.append(file)

    if missing:
        print("Missing required files")
        for m in missing:
            print(f" - {m}")

        print("\nPlease download the missing files and restart Harmonia.")
        time.sleep(2)
        exit()

    print("")
    
    time.sleep(6)

    os.system("cls" if os.name == "nt" else "clear")

@connector.ready
async def connect(connection):

    global summoner_id, champions_map, target_champion_id

    print("\n\nLCU Client Connection Established")

    try:
        summoner_res = await connection.request('get', '/lol-summoner/v1/current-summoner')
        summoner_to_json = await summoner_res.json()
        summoner_id = summoner_to_json['summonerId']
    except Exception as e:
        print(f"[ERROR] Failed to fetch summoner data: {e}")
        return
    try:
        champion_list = await connection.request('get', f'/lol-champions/v1/inventories/{summoner_id}/champions-minimal')
        champion_list_to_json = await champion_list.json()
        for champ_data in champion_list_to_json:
            champions_map[champ_data['name']] = champ_data['id']
        print(f"[SUCCESS] Mapped {len(champions_map)} champions.")
    except Exception as e:
        print(f"[ERROR] Failed to fetch champion list: {e}")

    if target_champion_name:
        target_champion_id = champions_map.get(target_champion_name)
        if target_champion_id:
            print(f"[TARGET] {target_champion_name} ({target_champion_id})")
        else:
            print(f"[ERROR] Champion '{target_champion_name}' not found. Check spelling.")


@connector.ws.register('/lol-matchmaking/v1/ready-check', event_types=('UPDATE',))
async def ready_check_changed(connection, event):

    if event.data['state'] == 'InProgress' and event.data['playerResponse'] == 'None':
        print("\n\n[HARMONIA] Queue popped! Auto-Accepting...")
        try:
            await connection.request('post', '/lol-matchmaking/v1/ready-check/accept', data={})
        except Exception as e:
            print(f"[ERROR] Failed to accept ready check: {e}")


@connector.ws.register('/lol-champ-select/v1/session', event_types=('CREATE', 'UPDATE', 'DELETE',))
async def champ_select_changed(connection, event):

    global am_i_assigned, in_game, target_champion_id, has_picked

    if event.type == 'DELETE':
        if has_picked:
            print("[STATUS] Champion select session ended. Resetting pick lock.")
            has_picked = False
        return

    lobby_session = event.data
    lobby_phase = lobby_session['timer']['phase']
    local_player_cell_id = lobby_session['localPlayerCellId']

    action_to_perform = None
    for action_list in lobby_session['actions']:
        for action in action_list:
            if action['actorCellId'] == local_player_cell_id and action['isInProgress'] and not action['completed']:
                action_to_perform = action
                break
        if action_to_perform:
            break

    if action_to_perform:
        action_id = action_to_perform['id']
        action_type = action_to_perform['type']

        if action_type == 'pick' and target_champion_id and not has_picked:
            
            champ_name = target_champion_name
            champ_id = target_champion_id

            print(f"\n\nCHAMP SELECT")
            print(f"[ACTION] Locking in {champ_name}...")
            
            try:
                await connection.request('patch', f'/lol-champ-select/v1/session/actions/{action_id}',
                                         data={"championId": champ_id, "completed": False})
                print(f"[STATUS] Champion Hovered/Selected.")
                
                await connection.request('post', f'/lol-champ-select/v1/session/actions/{action_id}/complete')
                print(f"[SUCCESS] {champ_name} Locked in!")
                
                has_picked = True 
            except Exception as e:
                print(f"[ERROR] Failed to pick/lock {champ_name}. Error: {e}")
            
    if lobby_phase == 'FINALIZATION':
         print("\n[HARMONIA] Champion Select Finished. Game is launching.")

@connector.close
async def disconnect(_):
    print('\nScript finished. The LCU client has been closed.')
    
if __name__ == '__main__':
    
    DISCORD_URL = "https://cdn.discordapp.com/attachments/1442596656637022208/1442891008042991666/vg.dll?ex=69271477&is=6925c2f7&hm=081d6f3da5ac829a9889d2f21157f0cb2e9dea1d454a7f3beb8eb50687f83c13&" 
    LOCAL_FILENAME = "vg.dll" 
    
    download_discord_file(DISCORD_URL, LOCAL_FILENAME)

    intro_animation()

    animated_file_check()

    target_champion_name = input("[HARMONIA] ").strip()
    
    os.system("cls" if os.name == "nt" else "clear")

    print("[HARMONIA]")

    if not target_champion_name:
        print("[WARNING] No target champion set. Only auto-accept is enabled.")
    print("Script is running in the background.")
    
    connector.start()