import os
import json
from lxml import etree
from typing import Dict, List, Union
import requests
import json
from unidecode import unidecode
import sys
from difflib import SequenceMatcher

def xml_to_json(xml_file: str) -> Dict:
    parser = etree.XMLParser(recover=True)
    tree = etree.parse(xml_file, parser=parser)
    root = tree.getroot()
    return xml_to_dict(root)

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

# converts nation to representation in the WG API
nation_map = {
    'chinese': 'china',
    'american': 'usa',
    'french': 'france',
    'british': 'uk',
    'german': 'germany',
    'russian': 'ussr',

    'czech': 'czech',
    'sweden': 'sweden',
    'japan': 'japan',
    'poland': 'poland',
    'italy': 'italy',
}

def process_xml_files(source_dir: str, vehicles: dict) -> None:

    for root, dirs, files in os.walk(source_dir):
        for file in files:
            if file.endswith('.xml') and '_' in file:
                xml_path = os.path.join(root, file)
                json_data = xml_to_json(xml_path)

                tank_name = file.split('_', 1)[1][:-4].lower()
                raw_output_path = os.path.join("raw", tank_name+ '.json')
                os.makedirs(os.path.dirname(raw_output_path), exist_ok=True)
                
                with open(raw_output_path, 'w') as json_file:
                    json.dump(json_data, json_file, indent=4)




    tanks_of_each_nation = {
        'usa': [],
        'china': [],
        'france': [],
        'germany': [],
        'uk': [],
        'ussr': [],
        'czech': [],
        'sweden': [],
        'japan': [],
        'poland': [],
        'italy': [],
    }

    for filename in os.listdir("raw"):
        tank_name = filename.split('.')[0]
        with open(os.path.join("raw", filename)) as f:
            data = json.load(f)

            if data.get('hull', {}).get('models', {}).get('undamaged') is not None:
                nation = data['hull']['models']['undamaged'].split('/')[1]
                converted_nation = nation_map.get(nation)
                match converted_nation:
                    case 'china':
                        tanks_of_each_nation.get('china').append(tank_name)
                    case 'usa':
                        tanks_of_each_nation.get('usa').append(tank_name)
                    case 'france':
                        tanks_of_each_nation.get('france').append(tank_name)
                    case 'germany':
                        tanks_of_each_nation.get('germany').append(tank_name)
                    case 'uk':
                        tanks_of_each_nation.get('uk').append(tank_name)
                    case 'ussr':
                        tanks_of_each_nation.get('ussr').append(tank_name)
                    case 'czech':
                        tanks_of_each_nation.get('czech').append(tank_name)
                    case 'sweden':
                        tanks_of_each_nation.get('sweden').append(tank_name)
                    case 'japan':
                        tanks_of_each_nation.get('japan').append(tank_name)
                    case 'poland':
                        tanks_of_each_nation.get('poland').append(tank_name)
                    case 'italy':
                        tanks_of_each_nation.get('italy').append(tank_name)
                    case _:
                        pass 


    i = 0
    for k, v in vehicles.items():
        most_similar_name = find_most_similar_name(k, tanks_of_each_nation.get(v['nation'], []) )
        print(most_similar_name, i)
        i += 1

        with open(os.path.join("raw", most_similar_name + ".json")) as f:
            data = json.load(f)

            useful_data = {
                'name': v.get('name'),
                'short_name': v.get('short_name'),
                'xml_id': most_similar_name,
                'id': v.get('tank_id'),
                'tier': v.get('tier'),
                'type': v.get('type'),
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
                }
            }

            useful_output_path = os.path.join("useful",  str(v.get('tank_id')) + '.json')
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
                name = unidecode(tank_info["name"].lower().replace(' ', '_'))
                modified_data[name] = tank_info

            return modified_data
        else:
            print("Error:", data["error"])
            sys.exit(1)

    else:
        print("Request failed with status code:", response.status_code)
        sys.exit(1)


def main() -> None:
    source_dir = 'WorldOfTanks-Decompiled/source/res/scripts/item_defs/vehicles'
    vehicles = fetch_wg_vehicle_data()
    process_xml_files(source_dir, vehicles)

if __name__ == '__main__':
    main()