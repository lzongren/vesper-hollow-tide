"""Compile the photographed blades as a masked, wind-animated foliage material."""

import unreal


def foliage(root, folder, label, source):
    lib = unreal.EditorAssetLibrary
    edit = unreal.MaterialEditingLibrary
    prop = unreal.MaterialProperty
    name = label + "InWind"
    if lib.does_asset_exist(root + "/" + name):
        return lib.load_asset(root + "/" + name)
    mat = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        name, root, unreal.Material, unreal.MaterialFactoryNew()
    )
    mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_MASKED)
    mat.set_editor_property("opacity_mask_clip_value", 0.32)
    mat.set_editor_property("two_sided", True)
    mat.set_editor_property(
        "shading_model", unreal.MaterialShadingModel.MSM_TWO_SIDED_FOLIAGE
    )
    mat.set_editor_property("used_with_instanced_static_meshes", True)
    mat.set_editor_property("used_with_nanite", True)

    def node(cls, x, y):
        return edit.create_material_expression(mat, cls, x, y)

    def wire(a, p, b, q):
        if not edit.connect_material_expressions(a, p, b, q):
            raise RuntimeError("Cannot connect meadow input " + q)

    def output(a, p, channel):
        if not edit.connect_material_property(a, p, channel):
            raise RuntimeError("Cannot connect meadow property " + str(channel))

    def texture(key, kind, x, y):
        n = node(unreal.MaterialExpressionTextureSample, x, y)
        tex = lib.load_asset(folder + "/Textures/" + key)
        if not tex:
            raise RuntimeError("Missing foliage atlas " + key)
        n.set_editor_property("texture", tex)
        n.set_editor_property("sampler_type", kind)
        return n

    def scale(a, p, value, x, y):
        n = node(unreal.MaterialExpressionMultiply, x, y)
        n.set_editor_property("const_b", value)
        wire(a, p, n, "A")
        return n

    def vector(values, x, y):
        n = node(unreal.MaterialExpressionConstant3Vector, x, y)
        n.set_editor_property("constant", unreal.LinearColor(*values, 1))
        return n

    base = texture(
        label + "Blades", unreal.MaterialSamplerType.SAMPLERTYPE_COLOR, -950, 0
    )
    normal = texture(
        source + "_nor_gl", unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL, -950, 180
    )
    fade = node(unreal.MaterialExpressionPerInstanceFadeAmount, -950, 340)
    alpha = node(unreal.MaterialExpressionMultiply, -700, 300)
    wire(base, "A", alpha, "A")
    wire(fade, "", alpha, "B")
    output(alpha, "", prop.MP_OPACITY_MASK)
    output(base, "RGB", prop.MP_BASE_COLOR)
    output(scale(base, "RGB", 0.44, -600, 110), "", prop.MP_SUBSURFACE_COLOR)
    output(normal, "RGB", prop.MP_NORMAL)
    rough = node(unreal.MaterialExpressionConstant, -320, 250)
    rough.set_editor_property("r", 0.77)
    output(rough, "", prop.MP_ROUGHNESS)
    # The glTF green channel is zero at the roots. Nearby plants share the
    # same gust phase and the induced bend fades out near the ground.
    pos = node(unreal.MaterialExpressionWorldPosition, -1050, 550)
    forest_phase = node(unreal.MaterialExpressionDotProduct, -800, 540)
    wire(pos, "", forest_phase, "A")
    wire(vector((0.0027, 0.0013, 0), -1050, 660), "", forest_phase, "B")
    time = node(unreal.MaterialExpressionTime, -1050, 805)
    phase = node(unreal.MaterialExpressionAdd, -560, 600)
    wire(forest_phase, "", phase, "A")
    wire(scale(time, "", 0.45, -790, 800), "", phase, "B")
    wind = node(unreal.MaterialExpressionSine, -350, 580)
    wire(phase, "", wind, "")
    weight = node(unreal.MaterialExpressionVertexColor, -350, 750)
    bend = node(unreal.MaterialExpressionMultiply, -145, 600)
    wire(wind, "", bend, "A")
    wire(weight, "G", bend, "B")
    offset = node(unreal.MaterialExpressionMultiply, 75, 600)
    wire(bend, "", offset, "A")
    wire(vector((3.2, 1.5, -0.3), -160, 760), "", offset, "B")
    output(offset, "", prop.MP_WORLD_POSITION_OFFSET)
    edit.recompile_material(mat)
    if not lib.save_loaded_asset(mat, only_if_is_dirty=False):
        raise RuntimeError("Cannot save foliage material")
    return mat
