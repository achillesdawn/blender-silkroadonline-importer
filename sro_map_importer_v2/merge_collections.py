import bpy

def merge_meshes_in_collections():
    context = bpy.context
    assert context

    bpy.ops.object.select_all(action='DESELECT')

    for collection in bpy.data.collections:
        print(f"processing collection: {collection.name}")
        meshes = [obj for obj in collection.objects if obj.type == 'MESH']

        if len(meshes) == 0:
            print(f"  No meshes found in collection: {collection.name}")
            continue

        for ob in meshes:
            ob.select_set(True)

        context.view_layer.objects.active = meshes[0]

        bpy.ops.object.join()

        merged_mesh = context.view_layer.objects.active
        merged_mesh.name = f"{collection.name}_merged"

        print(f"  Meshes merged into: {merged_mesh.name}")

        bpy.ops.object.select_all(action='DESELECT')


merge_meshes_in_collections()