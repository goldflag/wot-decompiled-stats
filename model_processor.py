import os
import subprocess
import shutil
import json
from multiprocessing import Process, Queue, current_process
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
    shared_content = ["1", "2", "3"]
    
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

    for shared in shared_content:
        pkg_path = f"{wot_path}\\res\\packages\\shared_content-part{shared}.pkg"
        pkg_res_path = f"{wot_path}\\res\\packages\\shared-content-part{shared}"
        extract_7z(pkg_path, pkg_res_path)
        src_dirs.append(pkg_res_path)
    
    print(f"Merging directories...")
    merge_directories(src_dirs, merged_path)
    print(f"Successfully merged directories into {merged_path}")

def update_mtl_file(mtl_file_path, texture_base_path):
    """Update the paths in the MTL file to be relative to the required directories."""
    with open(mtl_file_path, 'r') as file:
        lines = file.readlines()

    with open(mtl_file_path, 'w') as file:
        for line in lines:
            if 'map_Kd' in line or 'map_norm' in line:
                texture_file = os.path.basename(line.split()[1])
                # Determine if the texture is related to tracks or other components
                if 'track' in texture_file:
                    new_texture_path = os.path.join("..", "tracks", texture_file)
                else:
                    new_texture_path = texture_file
                line = f'{line.split()[0]} {new_texture_path.replace(os.sep, "/")}\n'
            file.write(line)

def convert_to_obj(input_file, output_obj_path):
    command = [
        "python",
        ".\\wot-model-converter\\convert-primitive.py",
        "-o",
        output_obj_path,
        input_file
    ]
    try:
        subprocess.run(command, stdout=subprocess.DEVNULL, check=True)
    except subprocess.CalledProcessError as e:
        print(f"An error occurred while converting {input_file} to .obj: {e}")
        print(e.stderr)

def convert_to_glb(output_obj_path, output_glb_path, texture_base_path):
    # Update the MTL file before conversion
    mtl_file_path = output_obj_path.replace('.obj', '.mtl')
    if os.path.exists(mtl_file_path):
        update_mtl_file(mtl_file_path, texture_base_path)

    blender_command = [
        "blender",
        "--background",
        "--python", "convert_obj_to_glb_with_textures.py",
        "--", output_obj_path, output_glb_path, texture_base_path
    ]
    try:
        subprocess.run(blender_command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    except subprocess.CalledProcessError as e:
        print(f"An error occurred while converting {output_obj_path} to .glb: {e}")
        print(e.stderr)

def worker(task_queue):
    counter = 0

    while not task_queue.empty():
        task = task_queue.get()
        if task is None:
            break

        tank_name, file_name, input_file, output_obj_path, output_glb_path, tracks_texture_path = task
        convert_to_obj(input_file, output_obj_path)
        convert_to_glb(output_obj_path, output_glb_path, tracks_texture_path)
        print(f"{counter} - {current_process().name} - Converted {file_name.split('.')[0]} on {tank_name}")
        counter += 1

def convert_models():
    with open("tank_map.json", "r") as json_file:
        tank_map = json.load(json_file)

    task_queue = Queue()

    # Iterate over each folder in the base path
    for tank_name in os.listdir(merged_path)[0:100]:
        folder_path = os.path.join(merged_path, tank_name)
        
        # Check if the item is a directory
        if os.path.isdir(folder_path):
            # Construct the paths for the input and output files
            input_path = os.path.join(folder_path, "normal", "lod0")
            tracks_input_path = os.path.join(folder_path, "track")
            tracks_texture_path = os.path.join(folder_path, "..", "tracks")
            
            # Check if the "normal/lod0" folder exists
            if os.path.exists(input_path):
                # Iterate over each ".primitives_processed" file in the "normal/lod0" folder
                for file_name in os.listdir(input_path):
                    if file_name.endswith(".primitives_processed"):
                        # Construct the full input file path
                        input_file = os.path.join(input_path, file_name)
                        output_obj_path = os.path.join(folder_path, f"{file_name.split('.')[0]}.obj")
                        output_glb_path = os.path.join("useful", str(tank_map.get(tank_name, {}).get("id")), f"{file_name.split('.')[0]}.glb")
                        
                        task = (tank_name, file_name, input_file, output_obj_path, output_glb_path, folder_path)
                        task_queue.put(task)

            # Check if the "track" folder exists
            if os.path.exists(tracks_input_path):
                for file_name in os.listdir(tracks_input_path):
                    if file_name.endswith(".primitives_processed"):
                        # Construct the full input file path
                        input_file = os.path.join(tracks_input_path, file_name)
                        output_obj_path = os.path.join(folder_path, f"{file_name.split('.')[0]}.obj")
                        
                        track_path = os.path.join("useful", str(tank_map.get(tank_name, {}).get("id")), "track")
                        if not os.path.exists(track_path):
                            os.makedirs(track_path)
                        output_glb_path = os.path.join(track_path, f"{file_name.split('.')[0]}.glb")
                        
                        task = (tank_name, file_name, input_file, output_obj_path, output_glb_path, tracks_texture_path)
                        task_queue.put(task)
    
    # Start worker processes
    num_workers = os.cpu_count()
    processes = []
    for _ in range(num_workers):
        p = Process(target=worker, args=(task_queue,))
        p.start()
        processes.append(p)

    # Wait for all worker processes to finish
    for p in processes:
        p.join()


def main():
    extract_tank_model_pkgs()
    convert_models()

if __name__ == '__main__':
    main()