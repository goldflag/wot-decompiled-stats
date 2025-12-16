import gzip
import shutil
import os
import json
import time
from typing import Any, Dict, List, Union
import requests
import json
import sys
import utils
from pathlib import Path
from dotenv import load_dotenv
from bs4 import BeautifulSoup

load_dotenv()

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
                'name': utils.get_msgstr(tank_nation, gun),
                'id': gun,
                'maxAmmo': gun_info.get('maxAmmo'),
                'aimTime': gun_info.get('aimingTime'),
                'accuracy': gun_info.get('shotDispersionRadius'),
                'reloadTime': gun_info.get('reloadTime'),
                'clip': gun_info.get('clip'),
                'burst': gun_info.get('burst'),
                'autoreload': gun_info.get('autoreload'),
                'dualGun': gun_info.get('dualGun'),
                'twinGun': gun_info.get('twinGun'),
                'arc': gun_info.get('turretYawLimits'),
                'elevation': -min(gun_info.get('pitchLimits', {}).get('minPitch')),
                'depression': max(gun_info.get('pitchLimits', {}).get('maxPitch')),
                'elevationLimits': {
                    'elevation': gun_info.get('pitchLimits', {}).get('minPitch'),
                    'depression': gun_info.get('pitchLimits', {}).get('maxPitch'),
                }, 
                'gunArc': gun_info.get('turretYawLimits'),
                'dispersion': {
                    'turretRotation': gun_info.get('shotDispersionFactors', {}).get('turretRotation'),
                    'afterShot': gun_info.get('shotDispersionFactors', {}).get('afterShot'),
                    'whileDamaged': gun_info.get('shotDispersionFactors', {}).get('whileGunDamaged'),
                },
            }

            with open(Path("raw") / tank_nation / "guns.json") as f:
                gun_data = json.load(f)
                current_gun = gun_data['shared'].get(gun, {})
                current_gun["name"] = utils.get_msgstr(tank_nation, gun)

                with open(Path("raw") / tank_nation / "shells.json") as f:
                    shells = json.load(f)

                    for shell_id in current_gun.get('shots', {}).keys():
                        current_shell = shells.get(shell_id, {})
                        current_shell["image"] = shells["icons"][current_shell.get("icon")][0].rsplit('.png', 1)[0]
                        current_shell["name"] = utils.get_msgstr(tank_nation, shell_id)
                        current_gun["shots"][shell_id].update(current_shell)

                    gun_entry["level"] = current_gun["level"]
                    gun_entry["weight"] = current_gun["weight"]
                    gun_entry["shells"] = list(current_gun["shots"].values())

                    # fill in missing values from the gun data
                    if gun_entry.get('reloadTime') is None:
                        gun_entry['reloadTime'] = current_gun['reloadTime']

                    if gun_entry.get('maxAmmo') is None:
                        gun_entry['maxAmmo'] = current_gun['maxAmmo']

                    if gun_entry.get('accuracy') is None:
                        gun_entry['accuracy'] = current_gun['shotDispersionRadius']

                    if gun_entry.get('aimTime') is None:
                        gun_entry['aimTime'] = current_gun['aimingTime']

                    if gun_entry.get('dispersion').get('turretRotation') is None:
                        gun_entry['dispersion']['turretRotation'] = current_gun['shotDispersionFactors']['turretRotation']
                        gun_entry['dispersion']['afterShot'] = current_gun['shotDispersionFactors']['afterShot']
                        gun_entry['dispersion']['whileDamaged'] = current_gun['shotDispersionFactors']['whileGunDamaged']
                    
                    if gun_entry.get('clip') is None:
                        gun_entry['clip'] = current_gun.get('clip')

                    if gun_entry.get('burst') is None:
                        gun_entry['burst'] = current_gun.get('burst')

                    if gun_entry.get('autoreload') is None:
                        gun_entry['autoreload'] = current_gun.get('autoreload')

                    if gun_entry.get('dualAccuracy') is None:
                        gun_entry['dualAccuracy'] = current_gun.get('dualAccuracy')

            guns_arr.append(gun_entry)

        turret_armor = [info.get('armor')[info.get('primaryArmor')[0]], info.get('armor')[info.get('primaryArmor')[1]], info.get('armor')[info.get('primaryArmor')[2]]] if info.get('primaryArmor') != None else []

        if len(turret_armor) == 3:
            if not isinstance(turret_armor[0] , (int, float, complex)):
                turret_armor[0] = 0
            if not isinstance(turret_armor[1] , (int, float, complex)):
                turret_armor[1] = 0
            if not isinstance(turret_armor[2] , (int, float, complex)):
                turret_armor[2] = 0
            
        turrets_arr.append({
            'name': utils.get_msgstr(tank_nation, turret),
            'id': turret,
            'traverse': info.get('rotationSpeed'),
            'viewRange': info.get('circularVisionRadius'),
            'level': info.get('level'),
            'guns': guns_arr,
            'gunPosition': info.get('gunPosition'),
            'hp': info.get('maxHealth') + data.get('hull', {}).get('maxHealth'),
            'weight': info.get('weight'),
            'viewportHealth': info.get('surveyingDeviceHealth'),
            'ringHealth': info.get('turretRotatorHealth'),
            'armor': turret_armor,
            'openTop': info.get('ceilless') == 'true',
            'pitch': info.get('gunJointPitch'),
        })
    return turrets_arr

def get_tank_name_from_file(filename: str):
    isSiegeFile = '_siege_mode' in filename
    if isSiegeFile:
        filename = filename.replace('_siege_mode', '')
    return filename.split('.')[0]

def add_tank_stats(tank_stats: List[Dict], data: dict[str, Any], tank_api_data: Any) -> None:
    stats = data.get('stats')
    gun = sorted(stats.get('turrets')[-1].get('guns'), key=lambda x: x['level'])[-1]
    chassis = stats.get('chassis')[-1]
    engine = stats.get('engines')[-1]
    radio = stats.get('radios')[-1]
    shell = gun.get('shells')[0]
    secondShell = gun.get('shells')[1] if gun.get('shells') and len(gun.get('shells')) > 1 else None
    thirdShell = gun.get('shells')[2] if gun.get('shells') and len(gun.get('shells')) > 2 else None

    if gun.get('reloadTime') is None:
        return

    clip = gun.get('clip')
    burst = gun.get('burst')
    intra_clip_reload = 60 / clip.get('rate') if clip and clip.get('rate') else None

    number_of_shots = clip.get('count') if clip else None
    # factors in autocannons that shoot multiple shots in a burst
    if burst and clip:
        number_of_shots = number_of_shots / burst.get('count')

    time_to_empty_clip = gun.get('reloadTime') + (number_of_shots - 1) * intra_clip_reload if intra_clip_reload else None
    if burst and clip:
        # add time to empty clip for each burst shot
        time_to_empty_clip = time_to_empty_clip + number_of_shots * (60 / burst.get('rate')) * (burst.get('count') - 1)


    def getRof():
        if intra_clip_reload: 
            if gun.get('autoreload'):
                return 60 / min(gun.get('autoreload').get('reloadTime'))
            if burst and clip:
                return 60 / time_to_empty_clip * clip.get('count')
            return 60 / time_to_empty_clip * number_of_shots 
        return 60 / gun.get('reloadTime')

    # take into account Polish TDs with alpha damage dropoff over distance
    alpha_damage1 = shell.get('damage').get('armor')[0] if isinstance(shell.get('damage').get('armor'), list) else shell.get('damage').get('armor')

    alpha_damage2 = None
    if secondShell:
        alpha_damage2 = secondShell.get('damage').get('armor')[0] if isinstance(secondShell.get('damage').get('armor'), list) else secondShell.get('damage').get('armor') 
    alpha_damage3 = None
    if thirdShell:
        alpha_damage3 = thirdShell.get('damage').get('armor')[0] if isinstance(thirdShell.get('damage').get('armor'), list) else thirdShell.get('damage').get('armor') 


    weight = data.get('stats').get('hull').get('weight') + stats.get('turrets')[-1].get('weight') + stats.get('chassis')[-1].get('weight') + engine.get('weight') + radio.get('weight') + gun.get('weight')
    rof = getRof()

    tank_stats.append({
        'tank_id': data.get('id'),
        'name':  data.get('shortName'),
        'image': tank_api_data.get('images').get('contour_icon'),
        'bigImage': tank_api_data.get('images').get('big_icon'),
        'nation': utils.nation_conv[data.get('nation')],
        'tier': data.get('tier'),
        'role': data.get('role').rsplit('_', 1)[-1] if data.get('role') else None,
        'class': utils.class_conv[data.get('type')],
        'isPrem': tank_api_data.get('is_premium'),
        'caliber': shell.get('caliber'),
        'dpm1': rof * alpha_damage1,
        'dpm2': rof * alpha_damage2 if alpha_damage2 else None,
        'dpm3': rof * alpha_damage3 if alpha_damage3 else None,
        'alpha1': alpha_damage1,
        'alpha2': alpha_damage2,
        'alpha3': alpha_damage3,
        'reload': min(gun.get('autoreload').get('reloadTime')) if gun.get('autoreload') else gun.get('reloadTime'),
        'shell1': shell.get('kind'),
        'shell2': secondShell.get('kind') if secondShell else None,
        'shell3': thirdShell.get('kind') if thirdShell else None,
        'pen1': shell.get('piercingPower')[0],
        'pen2': secondShell.get('piercingPower')[0] if secondShell else None,
        'pen3': thirdShell.get('piercingPower')[0] if thirdShell else None,
        'shellVelocity1': shell.get('speed'),
        'shellVelocity2': secondShell.get('speed') if secondShell else None,
        'shellVelocity3': thirdShell.get('speed') if thirdShell else None,
        'intraClipReload': intra_clip_reload,
        'aimTime': gun.get('aimTime'),
        'accuracy': gun.get('accuracy'),
        'maxAmmo': gun.get('maxAmmo'),
        'potentialDamage': (gun.get('maxAmmo') if gun.get('maxAmmo') else 0) * alpha_damage1,
        'gunDepression': gun.get('depression'),
        'gunElevation': gun.get('elevation'),
        'turretTraverseDispersion': gun.get('dispersion').get('turretRotation'),
        'vehicleMovementDispersion': chassis.get('dispersion').get('vehicleMovement'),
        'vehicleRotationDispersion': chassis.get('dispersion').get('vehicleRotation'),
        'forwardSpeed': stats.get('speedLimit').get('forward'),
        'backwardSpeed': stats.get('speedLimit').get('backward'),
        'weight': weight,
        'power': engine.get('power'),
        'traverseSpeed': chassis.get('rotationSpeed'),
        'turretTraverseSpeed': stats.get('turrets')[-1].get('traverse'),
        'specificPower': engine.get('power') * 1000 / weight ,
        'viewRange': stats.get('turrets')[-1].get('viewRange'),
        'hp': stats.get('turrets')[-1].get('hp'),
    })

def process_xml_files(source_dir: str, vehicles: dict) -> None:
    tank_map = {}
    source_path = Path(source_dir)
    
    for root, dirs, files in os.walk(source_path):
        root_path = Path(root)
        for file in files:
            xml_path = root_path / file
            json_data = utils.xml_to_json(str(xml_path))
            
            if file.endswith('.xml') and '_' in file:
                raw_output_path = Path("raw") / (file + '.json')
                raw_output_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(raw_output_path, 'w') as json_file:
                    json.dump(json_data, json_file, indent=4)

            if file == 'list.xml':
                nation_from_path = root_path.parts[-1]
                nation_id = nation_to_id.get(nation_from_path)
                for name, value in json_data.items():
                    if isinstance(value, dict):
                        id = (value.get('id')<<8) + 1 + (nation_id<<4)
                        tank_map[name] = {
                            'id': id,
                            'price': value.get('price'),
                            'tags': value.get('tags'),
                            'tier': value.get('level'),
                            'nation': nation_from_path,
                            'name': vehicles.get(id, {}).get('name') 
                        }

            if file in ['guns.xml', 'turrets.xml', 'chassis.xml', 'engines.xml', 'radios.xml', 'shells.xml', 'fuelTanks.xml']:
                nation_from_path = root_path.parts[-2]
                raw_output_path = Path("raw") / nation_from_path / (file[:-4] + '.json')
                raw_output_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(raw_output_path, 'w') as json_file:
                    json.dump(json_data, json_file, indent=4)
        
    with open(Path("tank_map.json"), "w") as json_file:
        json.dump(tank_map, json_file)

    # list of tank stats for /tank-stats page
    tank_stats = []
    raw_dir = Path("raw")
    for filename in os.listdir(raw_dir):
        tank_name = get_tank_name_from_file(filename)
        tank_id = tank_map.get(tank_name, {}).get('id')
        tank_nation = tank_map.get(tank_name, {}).get('nation')

        if tank_id is None:
            continue

        print(tank_name, tank_id)

        if tank_id not in vehicles:
            print(f"Tank {tank_name} not found in WG API")
            continue

        tank_api_data = vehicles.get(tank_id, {})

        if tank_api_data is None:
            continue

        fetch_models(tank_id)

        with open(raw_dir / filename) as f:
            data = json.load(f)

        turrets_arr = get_turret_data(data, tank_nation)

        chassis_arr = []
        chassis = data.get('chassis', {})
        for chassis_name, chassis_info in chassis.items():


            chassis_data = data['physics']['detailed']['chassis'][chassis_name]
            axle_steering_lock_angles = chassis_data.get('axleSteeringLockAngles')
            if axle_steering_lock_angles and isinstance(axle_steering_lock_angles, list):
                wheelAngle = -axle_steering_lock_angles[0]
            else:
                wheelAngle = None 

            chassisPhysics = chassis_data['grounds']

            trackArmor = chassis_info.get('armor', {}).get('leftTrack')

            chassis_arr.append({
                'name': utils.get_msgstr(tank_nation, chassis_name),
                'id': chassis_name,
                'maxLoad': chassis_info.get('maxLoad'),
                'weight': chassis_info.get('weight'),
                # https://www.reddit.com/r/WorldofTanks/comments/o7c1io/hidden_mobility_stats_why_obj_277_is_faster_than/
                'terrainResistance': [
                    chassisPhysics['firm']['rollingFriction'] / 0.0805,
                    chassisPhysics['medium']['rollingFriction'] / 0.0805,
                    chassisPhysics['soft']['rollingFriction'] / 0.0805,
                ],
                'rotationSpeed': chassis_info.get('rotationSpeed'),
                'rotatesInPlace': chassis_info.get('rotationIsAroundCenter'),
                'dispersion': chassis_info.get('shotDispersionFactors'),
                'repairTime': chassis_info.get('repairTime'),
                'hullPosition': chassis_info.get('hullPosition'),
                'maxHealth': chassis_info.get('maxHealth'),
                'maxRegenHealth': chassis_info.get('maxRegenHealth'),
                'level': chassis_info.get('level'),
                'armor': trackArmor or chassis_info.get('wheels', {}).get('wheel', {}).get('armor', {}).get('wheel', 0),
                'wheeled': False if trackArmor else True,
                'wheelAngle': wheelAngle
            })


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
                current_engine["name"] = utils.get_msgstr(tank_nation, engine_id)
                current_engine["realPower"] = data['physics']['detailed']['engines'][engine_id]['smplEnginePower']
                # if info != "shared":
                #     current_engine.update({"xp": info.get("unlocks").get("engine").get("cost")})
                engines_list.append(current_engine)

        radios_list = []
        for radio_id, info in data['radios'].items():
            with open(os.path.join("raw", tank_nation, "radios.json")) as f:
                radio_data = json.load(f)
                current_radio = radio_data['shared'].get(radio_id, {})
                current_radio["name"] = utils.get_msgstr(tank_nation, radio_id)
                # if info != "shared":
                #     current_radio.update({"xp": info.get("unlocks").get("engine").get("cost")})
                radios_list.append(current_radio)

        fuel_tank = None
        for fuel_tank_id, info in data['fuelTanks'].items():
            with open(os.path.join("raw", tank_nation, "fuelTanks.json")) as f:
                fuel_tank_data = json.load(f)
                fuel_tank = fuel_tank_data['shared'].get(fuel_tank_id, {})

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
            'tags': tank_map.get(tank_name, {}).get('tags'),
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
                'fuelTank': fuel_tank,
                'hull': {
                    'ammoRackHealth': hull.get('ammoBayHealth'),
                    'armor': [hull.get('armor')[hull.get('primaryArmor')[0]], hull.get('armor')[hull.get('primaryArmor')[1]], hull.get('armor')[hull.get('primaryArmor')[1]]] if hull.get('primaryArmor') != None else [],
                    'weight': hull.get('weight'),
                },
            }
        }

        if "siege_mode" in data:
            useful_data['stats']['siegeMode'] = {
                'switchOnTime': data.get('siege_mode', {}).get('switchOnTime'),
                'switchOffTime': data.get('siege_mode', {}).get('switchOffTime'),
            }
        if "hull_aiming" in data:
            useful_data['stats']['hydropneumatic'] = {
                'depression': data.get('hull_aiming', {}).get('pitch', {}).get('wheelsCorrectionAngles', {}).get('pitchMin'),
                'elevation': data.get('hull_aiming', {}).get('pitch', {}).get('wheelsCorrectionAngles', {}).get('pitchMax'),
            }
        if "rocketAcceleration" in data:
            useful_data['stats']['rocketAcceleration'] = {
                'initialCooldown': data.get('rocketAcceleration', {}).get('deployTime'),
                'cooldown': data.get('rocketAcceleration', {}).get('reloadTime'),
                'uses': data.get('rocketAcceleration', {}).get('reuseCount'),
                'duration': data.get('rocketAcceleration', {}).get('duration'),
            }

        useful_output_path = Path("useful") / str(tank_id) / ('siege-stats.json' if '_siege_mode' in filename else 'stats.json')
        useful_output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(useful_output_path, 'w') as json_file:
            json.dump(useful_data, json_file, indent=4)

        if not '_siege_mode' in filename:
            add_tank_stats(tank_stats, useful_data, tank_api_data)

    tank_stats.sort(key=lambda x: x['dpm1'], reverse=True)
    with open(Path("tank_stats.json"), "w") as json_file:
        json.dump(tank_stats, json_file)


nationmap = {
    'r': 'ussr',
    'g': 'germany',
    'z': 'czech',
    'f': 'france',
    'j': 'japan',
    'p': 'poland',
    's': 'sweden',
    'b': 'uk',
    'c': 'china',
    'i': 'italy',
    'a': 'usa'
}

def fetch_models(id: int):
    # Load the tank_id_to_code mapping
    mapping_path = Path("sitedata") / "tank_id_to_code.json"
    
    if not mapping_path.exists():
        print(f"Mapping file not found at {mapping_path}")
        return
    
    with open(mapping_path, 'r', encoding='utf-8') as f:
        tank_id_to_code = json.load(f)
    
    # Convert id to string for dictionary lookup
    id_str = str(id)
    
    if id_str not in tank_id_to_code:
        # print(f"Model not found for tank ID: {id}")
        return  # Exit the function early
    
    output_path = Path("useful") / str(id) / "armor.json"

    if output_path.exists():
        print(f"Model for tank ID {id} already exists at {output_path}")
        return  # Exit the function if the file already exists

    time.sleep(0.8)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Get the vehicle code from our mapping
    vehicle_code = tank_id_to_code[id_str]
    # Get the first character of the vehicle code for the nation
    nation_code = vehicle_code[0]
    
    url = f"https://gamemodels3d.com/games/worldoftanks/data/current/{nationmap.get(nation_code)}/{vehicle_code}/armor/vehicle.model"

    print("Fetching model for tank ID:", id)
    response = requests.get(url, stream=True)

    if response.status_code == 200:

        with gzip.open(response.raw, 'rb') as f_in:
            with open(output_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        print(f"Model saved to {output_path}")
    else:
        print("Request failed with status code:", response.status_code)

def download_files(vehicles: dict): 
    """
    Downloads the HTML files for each country from gamemodels3d.com,
    parses them to extract vehicle information, and creates a mapping
    between tank_id and vehicle code.
    
    Args:
        vehicles: Dictionary of tank data from WG API, keyed by tank_id
        
    Returns:
        Path to the output directory
    """
    # Create a directory to store the output files if it doesn't exist
    output_dir = Path("sitedata")
    output_dir.mkdir(exist_ok=True)
    
    # Get the list of countries from the nationmap values
    countries = set(nationmap.values())
    
    # Dictionary to store the mapping between tank_id and vehicle code
    tank_id_to_code = {}
    
    for country in countries:
        url = f"https://gamemodels3d.com/games/worldoftanks/vehicles/{country}"
        
        print(f"Downloading and parsing data for {country} from {url}")
        try:
            response = requests.get(url)
            
            if response.status_code == 200:
                # Parse HTML
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Find all vehicle links
                vehicle_links = soup.select('a.button_vehicle')
                
                # Extract vehicle code and name
                vehicle_tuples = []
                for link in vehicle_links:
                    href = link.get('href')
                    title = link.get('title')
                    if href and title:
                        vehicle_tuples.append([href, title])
                
                # Match vehicle names with WG API data to create mapping
                for tank_id, tank_info in vehicles.items():
                    tank_name = tank_info.get("name", "")
                    for code, name in vehicle_tuples:
                        # Check if the names match (case-insensitive)
                        if name.lower() == tank_name.lower():
                            tank_id_to_code[tank_id] = code
                            break
                
                print(f"Processed {len(vehicle_tuples)} vehicles for {country}")
            else:
                print(f"Request failed for {country} with status code: {response.status_code}")
        except Exception as e:
            print(f"Error processing {country}: {str(e)}")
    
    # Save the tank_id to vehicle code mapping
    mapping_path = output_dir / "tank_id_to_code.json"
    with open(mapping_path, 'w', encoding='utf-8') as f_out:
        json.dump(tank_id_to_code, f_out, ensure_ascii=False, indent=2)
    
    print(f"Created mapping for {len(tank_id_to_code)} tanks, saved to {mapping_path}")
    return output_dir

def fetch_wg_vehicle_data() -> dict: 
    url = "https://api.worldoftanks.asia/wot/encyclopedia/vehicles/"
    params = {
        "application_id": os.getenv('API_KEY'),
        "fields": "name, short_name, tank_id, nation, tier, type, is_premium, images"
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
    print("Fetching API data...")
    vehicles = fetch_wg_vehicle_data()
    download_files(vehicles)
    print("Processing XML files...")
    source_dir = Path('wot-src/sources/res/scripts/item_defs/vehicles')
    process_xml_files(str(source_dir), vehicles)

if __name__ == '__main__':
    main()