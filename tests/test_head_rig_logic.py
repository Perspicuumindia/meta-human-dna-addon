import os
import bpy
import math
import json
import pytest
from mathutils import Vector
from pathlib import Path
from pprint import pformat
from meta_human_dna.constants import (
    POSES_FOLDER, 
    CUSTOM_BONE_SHAPE_NAME, 
    CUSTOM_BONE_SHAPE_SCALE
)
from constants import TEST_FBX_POSES_FOLDER, TEST_JSON_POSES_FOLDER
from utilities.bones import (
    get_bone_differences,
    show_differences
)
from meta_human_dna.ui.callbacks import (
    get_active_rig_logic,
)

def get_all_pose_names() -> list[str]:
    pose_names = []
    for root, _, files in os.walk(POSES_FOLDER):
        for file in files:
            if file == 'pose.json':
                pose_name = str(Path(root).relative_to(POSES_FOLDER))
                if 'wrinkle_maps' not in pose_name:
                    pose_names.append(str(Path(root).relative_to(POSES_FOLDER)))
    return pose_names

def import_fbx_pose(file_path: Path) -> bpy.types.Object:
    armature_name = 'joints_grp'

    bpy.ops.wm.fbx_import(filepath=str(file_path))
    file_path = Path(file_path)

    # Remove the extra empties
    rig_empty = bpy.data.objects.get('rig')
    if rig_empty:
        for child in rig_empty.children_recursive:
            if child.name in [armature_name, 'head_lod0_mesh']:
                continue
            bpy.data.objects.remove(child)
        bpy.data.objects.remove(rig_empty)

    # rename the armature
    armature_object = bpy.data.objects.get(armature_name)
    armature_object.name = f'{file_path.stem}_head_rig' # type: ignore
    armature_object.data.name = f'{file_path.stem}_head_rig' # type: ignore
    sphere_object = bpy.data.objects[CUSTOM_BONE_SHAPE_NAME] 
    for bone in armature_object.data.bones: # type: ignore
        bone.name = bone.name.replace('DHIhead:', '')
        armature_object.pose.bones[bone.name].rotation_mode = 'XYZ' # type: ignore
        # set the custom shape for the face bones to make them easier to see
        armature_object.pose.bones[bone.name].custom_shape = sphere_object # type: ignore
        armature_object.pose.bones[bone.name].custom_shape_scale_xyz.x = CUSTOM_BONE_SHAPE_SCALE.x/50 # type: ignore
        armature_object.pose.bones[bone.name].custom_shape_scale_xyz.y = CUSTOM_BONE_SHAPE_SCALE.y/50 # type: ignore
        armature_object.pose.bones[bone.name].custom_shape_scale_xyz.z = CUSTOM_BONE_SHAPE_SCALE.z/50 # type: ignore

    # rename the mesh
    head_mesh = bpy.data.objects.get('head_lod0_mesh')
    head_mesh.name = f'{file_path.stem}_mesh' # type: ignore
    head_mesh.data.name = f'{file_path.stem}_mesh' # type: ignore

    # fix the head mesh rotation and scale
    armature_object.scale = Vector((0.01, 0.01, 0.01)) # type: ignore
    armature_object.rotation_mode = 'XYZ' # type: ignore
    armature_object.rotation_euler.x += math.radians(90) # type: ignore
    armature_object.hide_set(True) # type: ignore

    return armature_object # type: ignore

@pytest.mark.parametrize(
    ('pose_name', 'source_rig_name'), 
    [ 
        # (pose_name, 'male_01_head_rig') for pose_name in get_all_pose_names()
        (pose_name, 'ada_head_rig') for pose_name in get_all_pose_names()
    ]
)
def test_pose(
    load_dna, 
    pose_name: str, 
    source_rig_name: str, 
    changed_head_bone_name: str,
    show: bool = False,
    skip_fbx_import: bool = False
):
    use_fbx_files = os.environ.get('META_HUMAN_DNA_ADDON_TESTS_UPDATE_HEAD_JSON_POSES')
    
    tolerance = 0.001
    
    if use_fbx_files:
        fbx_file_path = TEST_FBX_POSES_FOLDER / source_rig_name / f"{pose_name}.fbx"
        # import the fbx file
        if not skip_fbx_import:
            armature_object = import_fbx_pose(
                file_path=fbx_file_path
            )
        else:
            armature_object = bpy.data.objects[f'{fbx_file_path.stem}_head_rig']

        # set the current pose
        bpy.context.window_manager.meta_human_dna.face_pose_previews = str(POSES_FOLDER / pose_name / "thumbnail-preview.png") # type: ignore

        # check that the poses match
        differences, target_locations = get_bone_differences(
            source_rig_name=source_rig_name, 
            target_rig_name=armature_object.name, 
            tolerance=tolerance
        )

        # cache bone locations to json for faster testing than importing fbx files
        json_pose_file_path = TEST_JSON_POSES_FOLDER / source_rig_name / f'{pose_name}.json'
        os.makedirs(json_pose_file_path.parent, exist_ok=True)
        with open(json_pose_file_path, 'w') as file:
            json.dump(target_locations, file, indent=2)

        if differences and show:
            show_differences(source_rig_name, armature_object.name, differences)
    else:
        # load bone locations from json
        json_pose_file_path = TEST_JSON_POSES_FOLDER / source_rig_name / f'{pose_name}.json'
        with open(json_pose_file_path, 'r') as file:
            target_locations = json.load(file)
        # set the current pose
        bpy.context.window_manager.meta_human_dna.face_pose_previews = str(POSES_FOLDER / pose_name / "thumbnail-preview.png") # type: ignore

        # check that the poses match
        differences, target_locations = get_bone_differences(
            source_rig_name=source_rig_name,
            target_bone_locations=target_locations,
            tolerance=tolerance
        )

    # ignore differences caused by testing bone changes
    differences = [(bone_name, value) for (bone_name, value) in differences if bone_name != changed_head_bone_name]

    assert not differences, \
    (
        f'In the pose "{pose_name}" the following bone location differences '
        f'exceeds the tolerance {tolerance}:\n{pformat(differences)}'
    )

@pytest.mark.parametrize(
    ('enum_index', 'active_face_material_name'), 
    [
        (0, 'combined'),
        (1, 'masks'),
        (2, 'normals'),
        (3, 'topology')
    ]
)
def test_active_face_material(load_dna, enum_index, active_face_material_name):
    pytest.skip('TODO: Fix this')
    bpy.context.scene.meta_human_dna.active_face_material = active_face_material_name # type: ignore
    instance = get_active_rig_logic()
    assert instance, 'No active rig logic found'

    assert instance.active_face_material == enum_index, \
    (
        f'The active face material should be "{enum_index}" '
        f'but is "{instance.active_face_material}"'
    )