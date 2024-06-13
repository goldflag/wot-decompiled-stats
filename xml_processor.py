import os
import json
from lxml import etree
from typing import Dict, List, Union
import requests
import json
import sys
import re
import polib
from dotenv import load_dotenv
load_dotenv()

def get_msgstr(nation: str, msgid: str) -> str | None:

    # If the nation is 'uk', change it to 'gb' to match the .po file name
    if nation == 'uk':
        nation = 'gb'

    path = os.path.join('wot-src', 'sources', 'res', 'text', 'lc_messages', f'{nation}_vehicles.po')
    try:
        # Load the .po file
        po = polib.pofile(path)
        
        # Find the entry with the given msgid
        entry = po.find(msgid)
        
        # If the entry is found, return the msgstr, otherwise return None
        if entry:
            return entry.msgstr
        else:
            return None
    except FileNotFoundError:
        print(f'Error: The file {path} was not found.')
        return None
    except IOError as e:
        print(f'Error: There was a problem reading the file: {e}')
        return None
    except Exception as e:
        print(f'An unexpected error occurred: {e}')
        return None

# def xml_to_dict(element) -> Dict:
#     if len(element) == 0:
#         return element.text
#     return {child.tag: xml_to_dict(child) for child in element}

def xml_to_json(xml_file: str) -> Dict:
    # Read the XML content from the file
    with open(xml_file, 'r', encoding='utf-8') as file:
        xml_content = file.read()
    
    # Remove XML comments using a regular expression
    cleaned_xml_content = re.sub(r'<!--.*?-->', '', xml_content, flags=re.DOTALL)
    
    # Convert cleaned XML content to bytes
    cleaned_xml_content_bytes = cleaned_xml_content.encode('utf-8')
    
    # Parse the cleaned XML content as bytes
    parser = etree.XMLParser(recover=True)
    tree = etree.fromstring(cleaned_xml_content_bytes, parser=parser)
    
    # Convert the XML tree to a dictionary
    xml_dict = xml_to_dict(tree, os.path.basename(xml_file))
    
    return xml_dict

def is_float(value: str) -> bool:
    try:
        float(value)
        return True
    except ValueError:
        return False

def xml_to_dict(root: etree._Element, file: str) -> Dict:
    result: Dict[str, Union[str, int, float, List, Dict]] = {}
    for child in root:
        if child.tag == 'tags':
            if child.text is not None:
                result[child.tag] = [tag.strip() for tag in child.text.split()]
            else:
                result[child.tag] = []
        elif child.tag == 'price' and file == 'list.xml' and child.find('gold') is not None:
            result[child.tag] = { 'gold': int(child.text.strip()) }
        elif len(child) == 0:
            if child.text is not None:
                text = child.text.strip()
                if text.isdigit():
                    result[child.tag] = int(text)
                elif is_float(text):
                    result[child.tag] = float(text)
                elif ' ' in text:
                    values = text.split()
                    if all(is_float(val) for val in values):
                        result[child.tag] = [float(val) for val in values]
                    else:
                        result[child.tag] = values
                else:
                    result[child.tag] = text
            else:
                result[child.tag] = None
        else:
            result[child.tag] = xml_to_dict(child, file)
    return result

nation_to_id = {
    'ussr': 0,
    'germany': 1,
    'usa': 2,
    'china': 3,
    'france': 4,
    'uk': 5,
    'japan': 6,
    'czech': 7,
    'sweden': 8,
    'poland': 9,
    'italy': 10,
}


def get_turret_data(data, tank_nation: str):
    turrets_arr = []
    turrets = data.get('turrets0', {})
    for turret, info in turrets.items():
        guns_arr = []
        guns = info.get('guns', {})
        for gun, gun_info in guns.items():

            gun_entry = {
                'name': get_msgstr(tank_nation, gun),
                'id': gun,
                'maxAmmo': gun_info.get('maxAmmo'),
                'aimTime': gun_info.get('aimingTime'),
                'accuracy': gun_info.get('shotDispersionRadius'),
                'reloadTime': gun_info.get('reloadTime'),
                'arc': gun_info.get('turretYawLimits'),
                'elevation': -min(gun_info.get('pitchLimits', {}).get('minPitch')),
                'depression': max(gun_info.get('pitchLimits', {}).get('maxPitch')),
                'dispersion': {
                    'turretRotation': gun_info.get('shotDispersionFactors', {}).get('turretRotation'),
                    'afterShot': gun_info.get('shotDispersionFactors', {}).get('afterShot'),
                    'whileDamaged': gun_info.get('shotDispersionFactors', {}).get('whileGunDamaged'),
                },
            }
            with open(os.path.join("raw", tank_nation, "guns.json")) as f:
                gun_data = json.load(f)
                current_gun = gun_data['shared'].get(gun, {})
                current_gun["name"] = get_msgstr(tank_nation, gun)

                with open(os.path.join("raw", tank_nation, "shells.json")) as f:
                    shells = json.load(f)

                    for shell_id in current_gun.get('shots', {}).keys():
                        current_shell = shells.get(shell_id, {})
                        current_gun["shots"][shell_id].update(current_shell)

                    gun_entry["level"] = current_gun["level"]
                    gun_entry["weight"] = current_gun["weight"]
                    gun_entry["shells"] = list(current_gun["shots"].values())

            guns_arr.append(gun_entry)

        turrets_arr.append({
            'name': get_msgstr(tank_nation, turret),
            'id': turret,
            'traverse': info.get('rotationSpeed'),
            'viewRange': info.get('circularVisionRadius'),
            'level': info.get('level'),
            'guns': guns_arr,
            'gunPosition': info.get('gunPosition'),
            'hp': info.get('maxHealth') + data.get('hull', {}).get('maxHealth'),
            'armor': [info.get('armor')[info.get('primaryArmor')[0]], info.get('armor')[info.get('primaryArmor')[1]], info.get('armor')[info.get('primaryArmor')[1]]] if info.get('primaryArmor') != None else [],
        })
    return turrets_arr

def process_xml_files(source_dir: str, vehicles: dict) -> None:

    tank_map = {}
    for root, dirs, files in os.walk(source_dir):
        for file in files:
            xml_path = os.path.join(root, file)
            json_data = xml_to_json(xml_path)
            if file.endswith('.xml') and '_' in file:
                raw_output_path = os.path.join("raw", file + '.json')
                os.makedirs(os.path.dirname(raw_output_path), exist_ok=True)

                with open(raw_output_path, 'w') as json_file:
                    json.dump(json_data, json_file, indent=4)

            if file == 'list.xml':
                nation_from_path = root.split('/')[-1].split('\\')[-1]
                nation_id = nation_to_id.get(nation_from_path)
                for name, value in json_data.items():
                    if isinstance(value, dict):
                        id = (value.get('id')<<8) + 1 + (nation_id<<4)
                        tank_map[name] = {
                            'id': id,
                            'price': value.get('price'),
                            'tags': value.get('tags'),
                            'tier': value.get('level'),
                            'nation': nation_from_path
                        }
            if file in ['guns.xml', 'turrets.xml', 'chassis.xml', 'engines.xml', 'radios.xml', 'shells.xml', 'fuelTanks.xml']:
                nation_from_path = root.split('/')[-1].split('\\')[-2]

                raw_output_path = os.path.join("raw", nation_from_path, file[:-4] + '.json')
                os.makedirs(os.path.dirname(raw_output_path), exist_ok=True)

                with open(raw_output_path, 'w') as json_file:
                    json.dump(json_data, json_file, indent=4)
        
    file_path = "tank_map.json"
    with open(file_path, "w") as json_file:
        json.dump(tank_map, json_file)


    for filename in os.listdir("raw"):
        tank_name = filename.split('.')[0]
        tank_id = tank_map.get(tank_name, {}).get('id')
        tank_nation = tank_map.get(tank_name, {}).get('nation')

        print(tank_name, tank_id)
        if tank_id is None:
            continue

        if tank_id not in vehicles:
            print(f"Tank {tank_name} not found in WG API")
            continue

        with open(os.path.join("raw", filename)) as f:
            data = json.load(f)

            turrets_arr = get_turret_data(data, tank_nation)

            chassis_arr = []
            chassis = data.get('chassis', {})
            for chassis_name, chassis_info in chassis.items():
                chassis_arr.append({
                    'name': get_msgstr(tank_nation, chassis_name),
                    'id': chassis_name,
                    'maxLoad': chassis_info.get('maxLoad'),
                    'terrainResistance': chassis_info.get('terrainResistance'),
                    'rotationSpeed': chassis_info.get('rotationSpeed'),
                    'rotatesInPlace': chassis_info.get('rotationIsAroundCenter'),
                    'repairTime': chassis_info.get('repairTime'),
                    'hullPosition': chassis_info.get('hullPosition'),
                    'maxHealth': chassis_info.get('maxHealth'),
                    'maxRegenHealth': chassis_info.get('maxRegenHealth'),
                    'level': chassis_info.get('level'),
                    'armor': chassis_info.get('armor', {}).get('leftTrack')
                })


            tank_api_data = vehicles.get(tank_id, {})

            if tank_api_data is None:
                continue

            crew_list = []
            for primary, secondary in data['crew'].items():
                if secondary is None:
                    secondary_list = []
                # sometimes the secondary roles are a list, sometimes they are a string (processed by xml_to_dict)
                elif isinstance(secondary, list):
                    secondary_list = secondary
                else:
                    # Split the secondary roles by whitespace and newlines, and filter out empty strings
                    secondary_list = [role.strip() for role in secondary.split() if role.strip()]
                
                crew_member = {
                    "primary": primary,
                    "secondary": secondary_list
                }
                
                crew_list.append(crew_member)

            engines_list = []
            for engine_id, info in data['engines'].items():
                with open(os.path.join("raw", tank_nation, "engines.json")) as f:
                    engine_data = json.load(f)
                    current_engine = engine_data['shared'].get(engine_id, {})
                    current_engine["name"] = get_msgstr(tank_nation, engine_id)
                    # if info != "shared":
                    #     current_engine.update({"xp": info.get("unlocks").get("engine").get("cost")})
                    engines_list.append(current_engine)

            radios_list = []
            for radio_id, info in data['radios'].items():
                with open(os.path.join("raw", tank_nation, "radios.json")) as f:
                    radio_data = json.load(f)
                    current_radio = radio_data['shared'].get(radio_id, {})
                    current_radio["name"] = get_msgstr(tank_nation, radio_id)
                    # if info != "shared":
                    #     current_radio.update({"xp": info.get("unlocks").get("engine").get("cost")})
                    radios_list.append(current_radio)

            hull = data.get('hull', {})
            useful_data = {
                'name': tank_api_data.get('name'),
                'nation': tank_nation,
                'shortName': tank_api_data.get('short_name'),
                'xmlId': tank_name,
                'id': tank_id,
                'tier': tank_api_data.get('tier'),
                'type': tank_api_data.get('type'),
                'role': data.get('postProgressionTree'),
                'crew': crew_list,
                'price': tank_map.get(tank_name, {}).get('price'),
                'stats': {
                    'speedLimit': {
                        'forward': data.get('speedLimits', {}).get('forward'),
                        'backward': data.get('speedLimits', {}).get('backward'),
                    },
                    'camo': {
                        "moving": data.get('invisibility', {}).get('moving'),
                        "stationary": data.get('invisibility', {}).get('still'),
                        "camoBonus": data.get('invisibility', {}).get('camouflageBonus'),
                        "firePenalty": data.get('invisibility', {}).get('firePenalty'),
                    },
                    'turrets': turrets_arr,
                    'turretPosition': hull.get('turretPositions', {}).get('turret'),
                    'chassis': chassis_arr,
                    'engines': engines_list,
                    'radios': radios_list,
                    'hull': {
                        'ammoRackHealth': hull.get('ammoBayHealth'),
                        'armor': [hull.get('armor')[hull.get('primaryArmor')[0]], hull.get('armor')[hull.get('primaryArmor')[1]], hull.get('armor')[hull.get('primaryArmor')[1]]] if hull.get('primaryArmor') != None else [],
                        'weight': hull.get('weight'),
                    }   
                }
            }

            useful_output_path = os.path.join("useful", str(tank_id), 'stats.json')
            os.makedirs(os.path.dirname(useful_output_path), exist_ok=True)

            with open(useful_output_path, 'w') as json_file:
                json.dump(useful_data, json_file, indent=4)


def fetch_wg_vehicle_data() -> dict: 
    url = "https://api.worldoftanks.com/wot/encyclopedia/vehicles/"
    params = {
        "application_id": os.getenv('API_KEY'),
        "fields": "name, short_name, tank_id, nation, tier, type"
    }

    response = requests.get(url, params=params)

    if response.status_code == 200:
        data = response.json()
        
        if data["status"] == "ok":
            modified_data = {}
            for tank_id, tank_info in data["data"].items():
                modified_data[int(tank_id)] = tank_info

            return modified_data
        else:
            print("Error:", data["error"])
            sys.exit(1)

    else:
        print("Request failed with status code:", response.status_code)
        sys.exit(1)


def main() -> None:
    source_dir = 'wot-src/sources/res/scripts/item_defs/vehicles'
    vehicles = fetch_wg_vehicle_data()
    process_xml_files(source_dir, vehicles)

if __name__ == '__main__':
    main()