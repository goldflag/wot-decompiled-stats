import os
import json
from lxml import etree
from typing import Dict, List, Union
import requests
import json
import sys
from difflib import SequenceMatcher
import re
from dotenv import load_dotenv
load_dotenv()


def xml_to_dict(element) -> Dict:
    if len(element) == 0:
        return element.text
    return {child.tag: xml_to_dict(child) for child in element}

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
    xml_dict = xml_to_dict(tree)
    
    return xml_dict

def is_float(value: str) -> bool:
    try:
        float(value)
        return True
    except ValueError:
        return False

def xml_to_dict(root: etree._Element) -> Dict:
    result: Dict[str, Union[str, int, float, List, Dict]] = {}
    for child in root:
        if child.tag == 'tags':
            if child.text is not None:
                result[child.tag] = [tag.strip() for tag in child.text.split()]
            else:
                result[child.tag] = []
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
            result[child.tag] = xml_to_dict(child)
    return result

def find_most_similar_name(tank: str, tanks: List[str]) -> str:
    similarity_scores = [SequenceMatcher(None, tank, s).ratio() for s in tanks]
    max_index = similarity_scores.index(max(similarity_scores))
    return tanks[max_index]

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

def process_xml_files(source_dir: str, vehicles: dict) -> None:

    tank_map = {}

    for root, dirs, files in os.walk(source_dir):
        for file in files:
            xml_path = os.path.join(root, file)
            json_data = xml_to_json(xml_path)
            if file.endswith('.xml') and '_' in file:
                # tank_name = file.split('_', 1)[1][:-4].lower()
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
                        }


    file_path = "tank_map.json"
    with open(file_path, "w") as json_file:
        json.dump(tank_map, json_file)


    for filename in os.listdir("raw"):
        tank_name = filename.split('.')[0]
        tank_id = tank_map.get(tank_name, {}).get('id')
        print(tank_name, tank_id)
        if tank_id is None:
            continue

        if tank_id not in vehicles:
            print(f"Tank {tank_name} not found in WG API")
            continue

        with open(os.path.join("raw", filename)) as f:
            data = json.load(f)

            turrets_arr = []
            turrets = data.get('turrets0', {})
            for turret, info in turrets.items():
                guns_arr = []
                guns = info.get('guns', {})
                for gun, gun_info in guns.items():
                    guns_arr.append({
                        'name': gun,
                        'max_ammo': gun_info.get('maxAmmo'),
                        'aim_time': gun_info.get('aimingTime'),
                        'accuracy': gun_info.get('shotDispersionRadius'),
                        'reload_time': gun_info.get('reloadTime'),
                        'arc': gun_info.get('turretYawLimits'),
                        'elevation': -min(gun_info.get('pitchLimits', {}).get('minPitch')),
                        'depression': max(gun_info.get('pitchLimits', {}).get('maxPitch')),
                        'dispersion': {
                            'turret_rotation': gun_info.get('shotDispersionFactors', {}).get('turretRotation'),
                            'after_shot': gun_info.get('shotDispersionFactors', {}).get('afterShot'),
                            'while_damaged': gun_info.get('shotDispersionFactors', {}).get('whileGunDamaged'),
                        },
                    })

                turrets_arr.append({
                    'name': turret,
                    'traverse': info.get('rotationSpeed'),
                    'view_range': info.get('circularVisionRadius'),
                    'guns': guns_arr,
                    'gun_position': info.get('gunPosition'),
                    'hp': info.get('maxHealth') + data.get('hull', {}).get('maxHealth')
                })

            chassis_arr = []
            chassis = data.get('chassis', {})
            for chassis_name, chassis_info in chassis.items():
                chassis_arr.append({
                    'name': chassis_name,
                    'max_load': chassis_info.get('maxLoad'),
                    'terrain_resistance': chassis_info.get('terrainResistance'),
                    'rotation_speed': chassis_info.get('rotationSpeed'),
                    'rotates_in_place': chassis_info.get('rotationIsAroundCenter'),
                    'repair_time': chassis_info.get('repairTime'),
                    'hull_position': chassis_info.get('hullPosition'),
                    'track_health': chassis_info.get('maxHealth'),
                    'track_repaired_health': chassis_info.get('maxRegenHealth'),
                })


            tank_api_data = vehicles.get(tank_id, {})

            if tank_api_data is None:
                continue

            useful_data = {
                'name': tank_api_data.get('name'),
                'short_name': tank_api_data.get('short_name'),
                'xml_id': tank_name,
                'id': tank_api_data.get('tank_id'),
                'tier': tank_api_data.get('tier'),
                'type': tank_api_data.get('type'),
                'stats': {
                    'speed_limit': {
                        'forward': data.get('speedLimits', {}).get('forward'),
                        'backward': data.get('speedLimits', {}).get('backward'),
                    },
                    'camo': {
                        "moving": data.get('invisibility', {}).get('moving'),
                        "stationary": data.get('invisibility', {}).get('still'),
                        "camo_bonus": data.get('invisibility', {}).get('camouflageBonus'),
                        "fire_penalty": data.get('invisibility', {}).get('firePenalty'),
                    },
                    'turrets': turrets_arr,
                    'turret_position': data.get('hull', {}).get('turretPositions', {}).get('turret'),
                    'chassis': chassis_arr,
                    'hull': {
                        'ammo_rack_health': data.get('hull', {}).get('ammoBayHealth'),
                        'ammo_rack_health_repaired': data.get('hull', {}).get('ammoBayHealth', {}).get('maxRegenHealth'),
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