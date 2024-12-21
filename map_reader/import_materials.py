import sys

sys.path.insert(0, "/home/miguel/python/blender_silkroad_importer/map_reader")

import bpy
from bpy.types import ShaderNodeTexImage
from bmt import BMT
from ddj import DDJTextureReader
from pathlib import Path


class NodeTools:
    @staticmethod
    def create_image_node(
        ntree: bpy.types.NodeTree, image: bpy.types.Image
    ) -> ShaderNodeTexImage:
        image_node: bpy.types.ShaderNodeTexImage = ntree.nodes.new("ShaderNodeTexImage")  # type: ignore

        image_node.location = (-744, 446)
        image_node.image = image
        image_node.select = True
        image_node.update()

        ntree.nodes.active = image_node

        return image_node

    @classmethod
    def add_nodes(cls, ntree: bpy.types.NodeTree, img: bpy.types.Image):
        principled = ntree.nodes["Principled BSDF"]
        base_color_socket = principled.inputs["Base Color"]
        image_node = cls.create_image_node(ntree, img)

        mapping = ntree.nodes.new("ShaderNodeMapping")
        coord = ntree.nodes.new("ShaderNodeTexCoord")

        mapping.location = (-952, 448)
        coord.location = (-1142, 430)

        ntree.links.new(coord.outputs[2], mapping.inputs[0])
        ntree.links.new(mapping.outputs[0], image_node.inputs[0])
        ntree.links.new(image_node.outputs[0], base_color_socket)


if __name__ == "__main__":
    import bpy

    b = BMT()
    b.read(
        Path(
            "/home/miguel/python/blender_silkroad_importer/Silkroad_DATA-MAP/Data/prim/mtrl/bldg/europe/constantinople/euro_esteuro_castle_f02.bmt"
        )
    )

    d = DDJTextureReader()
    for material in b.materials:
        diffuse_path = b.path / material.diffuse.name

        if not diffuse_path.exists():
            raise Exception("diffuse path does not exist", diffuse_path)

        dds = d.convert_ddj_to_dds(diffuse_path)

        # m = bpy.data.materials.get(material.name)
        # if m is not None:
        #     continue

        # m = bpy.data.materials.new(material.name)
        # m.use_nodes = True

        # material.diffuse.name

        # ntree = m.node_tree
