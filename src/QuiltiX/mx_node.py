import os
import re
from pathlib import Path

import MaterialX as mx  # type: ignore


class MxStdLibNotFoundError(Exception):
    def __init__(self):
        super().__init__("Could not find MaterialX StdLib")


def get_mx_stdlib_paths():
    """Get the path to the stdlib of MaterialX definitions. This directory is the parent of the "libraries" directory
    containing the stdlib namespaces.

    1) Use PXR_MTLX_STDLIB_SEARCH_PATHS
    2) Search in pxr python lib (this might include USD specific node defs)
    3) Search in mx python lib

    Returns:
        list(str): List of MaterialX stdlib paths
    """
    stdlib_namespaces = {"bxdf", "lights", "pbrlib", "stdlib", "targets"}

    def recurse_find_mx_stdlib_in_dir(root_dir):
        for (root, dirs, _) in os.walk(root_dir):
            if Path(root).name == "libraries" and stdlib_namespaces.issubset(dirs):
                return Path(root).parent.as_posix()

    # TODO: which env vars are the needed ones?
    # MATERIALX_STDLIB_DIR, PXR_MTLX_STDLIB_SEARCH_PATHS, PXR_USDMTLX_STDLIB_SEARCH_PATHS
    # Going with this:
    # https://github.com/PixarAnimationStudios/USD/blob/v23.02/pxr/usd/usdMtlx/testenv/testUsdMtlxParser.py#L26
    if stdlib_env := os.getenv("PXR_MTLX_STDLIB_SEARCH_PATHS"):
        paths = [os.path.normpath(path) for path in stdlib_env.split(os.pathsep) if path]
        paths = list(set(paths))
        return paths

    import pxr  # type: ignore
    if pxr_stdlib := recurse_find_mx_stdlib_in_dir(os.path.dirname(pxr.__file__)):
        return [pxr_stdlib]

    if mx_stdlib := recurse_find_mx_stdlib_in_dir(os.path.dirname(mx.__file__)):
        return [mx_stdlib]

    raise MxStdLibNotFoundError


def get_mx_custom_lib_paths():
    if customlib_env := os.getenv("PXR_MTLX_PLUGIN_SEARCH_PATHS"):
        paths = [os.path.normpath(path) for path in customlib_env.split(os.pathsep) if path]
        paths = list(set(paths))
        return paths

    return []


def get_mx_node_group_dict(mx_node_defs):
    # mx_node_group_dict_example = {
    #     "procedural" : {
    #         "constant" : {
    #             "float": <MaterialX.PyMaterialXCore.NodeDef object at 0x000001C98B084AB0>,
    #             "vector2": <MaterialX.PyMaterialXCore.NodeDef object at 0x000001C98B084AF0>
    #         }
    #     }
    # }
    # { node_group : { node_def_name : {node_def_type: node_def} } }

    mx_node_group_dict = {}
    for mx_node_def in mx_node_defs:
        mx_node_group = mx_node_def.getNodeGroup() or "Other"
        mx_node_def_name = mx_node_def.getNodeString()
        mx_node_group_dict.setdefault(mx_node_group, {})
        mx_node_group_key = mx_node_group_dict[mx_node_group]

        mx_node_def_type = get_mx_node_def_type(mx_node_def)
        mx_node_group_key.setdefault(mx_node_def_name, {})[mx_node_def_type] = mx_node_def

    return mx_node_group_dict


def get_mx_node_def_type(mx_node_def):
    # return mx_node_def.getType()

    mx_node_def_string = mx_node_def.getNodeString()
    mx_node_def_full_name = mx_node_def.getName()

    # Some node definitions only have one type.
    all_but_type_pattern = (
        f"(ND_{mx_node_def_string}_)|(ND_{mx_node_def_string})"
    )
    all_but_type_match = re.match(
        all_but_type_pattern, mx_node_def_full_name
    )
    all_but_type_string = (
        all_but_type_match.groups()[0]
        if all_but_type_match and all_but_type_match.groups()[0]
        else "ND_"
    )
    mx_node_def_type = mx_node_def_full_name.replace(all_but_type_string, "")
    return mx_node_def_type