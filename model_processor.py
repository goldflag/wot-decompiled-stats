import os
import subprocess
import shutil
import json
from dotenv import load_dotenv
load_dotenv()

def extract_7z(pkg_path, res_path):
    # Ensure the destination folder exists
    if not os.path.exists(res_path):
        os.makedirs(res_path)

    # Use 7z to extract the .pkg file
    try:
        # Call the 7z command with subprocess
        subprocess.run(['7z', 'x', pkg_path, f'-o{res_path}'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        print(f"Successfully extracted {pkg_path} to {res_path}")
    except subprocess.CalledProcessError as e:
        print(f"An error occurred while extracting the package: {e}")
        print(e.stderr)

def merge_directories(src_dirs, dst_dir):
    if not os.path.exists(dst_dir):
        os.makedirs(dst_dir)
    
    for src_dir in src_dirs:
        for root, dirs, files in os.walk(src_dir):
            for dir_name in dirs:
                src_subdir = os.path.join(root, dir_name)
                dst_subdir = os.path.join(dst_dir, dir_name)
                shutil.copytree(src_subdir, dst_subdir, dirs_exist_ok=True)
        print(f"Successfully merged {src_dir}")

wot_path = os.getenv('WOT_PATH', 'C:\\Games\\World_of_Tanks_NA')
merged_path = f"{wot_path}\\res\\packages\\merged"

def extract_tank_model_pkgs():
    low_tiers = ["01", "02", "03", "04"]
    high_tiers = ["05", "06", "07", "08", "09", "10"]
    
    src_dirs = []
    
    for tier in low_tiers:
        pkg_path = f"{wot_path}\\res\\packages\\vehicles_level_{tier}.pkg"
        pkg_res_path = f"{wot_path}\\res\\packages\\{tier}"
        extract_7z(pkg_path, pkg_res_path)
        src_dirs.append(pkg_res_path)
    
    for tier in high_tiers:
        pkg1_path = f"{wot_path}\\res\\packages\\vehicles_level_{tier}-part1.pkg"
        pkg2_path = f"{wot_path}\\res\\packages\\vehicles_level_{tier}-part2.pkg"
        pkg1_res_path = f"{wot_path}\\res\\packages\\{tier}-part1"
        pkg2_res_path = f"{wot_path}\\res\\packages\\{tier}-part2"
        extract_7z(pkg1_path, pkg1_res_path)
        extract_7z(pkg2_path, pkg2_res_path)
        src_dirs.append(pkg1_res_path)
        src_dirs.append(pkg2_res_path)
    
    print(f"Merging directories...")
    merge_directories(src_dirs, merged_path)
    print(f"Successfully merged directories into {merged_path}")


def convert_models():

    file_path = "tank_map.json"
    # tank map generated in xml_processor.py
    with open(file_path, "r") as json_file:
        tank_map = json.load(json_file)

    counter = 0

    # Iterate over each folder in the base path
    for tank_name in os.listdir(merged_path):
        folder_path = os.path.join(merged_path, tank_name)
        
        # Check if the item is a directory
        if os.path.isdir(folder_path):
            # Construct the paths for the input and output files
            input_path = os.path.join(folder_path, "normal", "lod0")
            
            # Check if the "normal/lod0" folder exists
            if os.path.exists(input_path):
                counter += 1
                # Iterate over each ".primitives_processed" file in the "normal/lod0" folder
                for file_name in os.listdir(input_path):
                    if file_name.endswith(".primitives_processed"):

                        # Construct the full input file path
                        input_file = os.path.join(input_path, file_name)
                        output_obj_path = os.path.join(folder_path, f"{file_name.split('.')[0]}.obj")
                        output_glb_path = os.path.join("useful", str(tank_map.get(tank_name, {}).get("id")), f"{file_name.split('.')[0]}.glb")
                        # output_glb_path = os.path.join(folder_path, f"{file_name.split('.')[0]}.glb")

                        # Run the command using subprocess to convert primitives to OBJ
                        command = [
                            "python",
                            ".\\wot-model-converter\\convert-primitive.py",
                            "-o",
                            output_obj_path,
                            input_file
                        ]
                        try:
                            subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                            # print(f"Converted {input_file} to {output_obj_path}")
                        except subprocess.CalledProcessError as e:
                            print(f"An error occurred while converting the model to .obj: {e}")
                            print(e.stderr)
                            continue
                        
                        # Convert OBJ to GLB with textures using Blender
                        blender_command = [
                            "blender",
                            "--background",
                            "--python", "convert_obj_to_glb_with_textures.py",
                            "--", output_obj_path, output_glb_path
                        ]
                        try:
                            subprocess.run(blender_command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                            print(f"{counter} - Converted {file_name.split('.')[0]} on {tank_name}")
                        except subprocess.CalledProcessError as e:
                            print(f"An error occurred while converting {output_obj_path} to .glb: {e}")
                            print(e.stderr)


def main():
    extract_tank_model_pkgs()
    convert_models()

if __name__ == '__main__':
    main()