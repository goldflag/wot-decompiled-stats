import os
import subprocess
import shutil

def extract_7z(pkg_path, res_path):
    # Ensure the destination folder exists
    if not os.path.exists(res_path):
        os.makedirs(res_path)

    # Use 7z to extract the .pkg file
    try:
        # Call the 7z command with subprocess
        result = subprocess.run(['7z', 'x', pkg_path, f'-o{res_path}'], check=True, capture_output=True, text=True)
        print(f"Successfully extracted {pkg_path} to {res_path}")
        print(result.stdout)
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

def main():
    low_tiers = ["01", "02", "03", "04"]
    high_tiers = ["05", "06", "07", "08", "09", "10"]
    
    src_dirs = []
    
    for tier in low_tiers:
        pkg_path = f"D:\\Games\\World_of_Tanks_NA\\res\\packages\\vehicles_level_{tier}.pkg"
        pkg_res_path = f"D:\\Games\\World_of_Tanks_NA\\res\\packages\\{tier}"
        extract_7z(pkg_path, pkg_res_path)
        src_dirs.append(pkg_res_path)
    
    for tier in high_tiers:
        pkg1_path = f"D:\\Games\\World_of_Tanks_NA\\res\\packages\\vehicles_level_{tier}-part1.pkg"
        pkg2_path = f"D:\\Games\\World_of_Tanks_NA\\res\\packages\\vehicles_level_{tier}-part2.pkg"
        pkg1_res_path = f"D:\\Games\\World_of_Tanks_NA\\res\\packages\\{tier}-part1"
        pkg2_res_path = f"D:\\Games\\World_of_Tanks_NA\\res\\packages\\{tier}-part2"
        extract_7z(pkg1_path, pkg1_res_path)
        extract_7z(pkg2_path, pkg2_res_path)
        src_dirs.append(pkg1_res_path)
        src_dirs.append(pkg2_res_path)
    
    dst_dir = "D:\\Games\\World_of_Tanks_NA\\res\\packages\\merged"
    merge_directories(src_dirs, dst_dir)
    print(f"Successfully merged directories into {dst_dir}")


if __name__ == '__main__':
    main()