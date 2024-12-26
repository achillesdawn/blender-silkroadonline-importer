import bpy
from bpy.types import ShaderNodeTexImage

class NodeTool:
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
    def add_nodes(cls, ntree: bpy.types.NodeTree, img: bpy.types.Image, alpha: bool = False):
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

        if alpha:
            ntree.links.new(principled.inputs["Alpha"], image_node.outputs[1])