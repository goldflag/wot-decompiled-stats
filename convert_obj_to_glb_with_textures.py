import bpy
import sys
import os

def make_image_paths_absolute(mtl_dir):
    """Make image paths in materials absolute based on the .mtl directory."""
    for mat in bpy.data.materials:
        if mat.use_nodes:
            for node in mat.node_tree.nodes:
                if node.type == 'TEX_IMAGE':
                    image = node.image
                    if image and not os.path.isabs(image.filepath):
                        abs_path = os.path.join(mtl_dir, image.filepath)
                        if os.path.exists(abs_path):
                            image.filepath = abs_path
                        image.reload()

def convert_obj_to_glb(obj_file, glb_file):
    """Convert an OBJ file to a GLB file with textures."""
    input_dir = os.path.dirname(obj_file)

    # Clear existing data
    bpy.ops.wm.read_factory_settings(use_empty=True)

    # Import the OBJ file
    bpy.ops.import_scene.obj(filepath=obj_file)

    # Make texture paths absolute and pack them
    make_image_paths_absolute(input_dir)

    # Pack all images into the GLB file
    for image in bpy.data.images:
        if image.filepath:
            try:
                image.pack()
            except RuntimeError as e:
                print(f"Error packing image {image.filepath}: {e}")

    # Export to GLB with textures
    bpy.ops.export_scene.gltf(filepath=glb_file, export_format='GLB', export_image_format='AUTO')

# Get the input and output file paths from command line arguments
obj_file = sys.argv[sys.argv.index("--") + 1]
glb_file = sys.argv[sys.argv.index("--") + 2]

# Convert OBJ to GLB
convert_obj_to_glb(obj_file, glb_file)
