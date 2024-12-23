from pathlib import Path
import struct
from io import BufferedReader
from dataclasses import dataclass

POINTERS = "<IIIIIIII"


@dataclass
class BSRMaterial:
    _id: int
    name: str


@dataclass
class Mesh:
    name: str
    flag: int = 0


@dataclass
class Bbox:
    root_mesh: str
    bbox: tuple[float]
    bbox_max: tuple[float]


class BSRReader:
    bbox_info: Bbox
    materials: list[BSRMaterial]
    meshes: list[Mesh]

    def __init__(self) -> None:
        self.p_material = 0
        self.p_mesh = 0
        self.p_skeleton = 0
        self.p_animation = 0
        self.p_mesh_group = 0
        self.p_animation_group = 0
        self.p_palette = 0
        self.p_bbox = 0

        self.is_prim_mesh = 0
        self.has_mod_data = 0

        self.materials = []
        self.meshes = []

    def read_bbox(self, f: BufferedReader):
        f.seek(self.p_bbox)

        FLOAT_VECTOR = "<ffffff"

        n: int = struct.unpack("<I", f.read(4))[0]
        root_mesh = f.read(n)
        bbox: tuple[float] = struct.unpack(
            FLOAT_VECTOR, f.read(struct.calcsize(FLOAT_VECTOR))
        )
        bbox_max: tuple[float] = struct.unpack(
            FLOAT_VECTOR, f.read(struct.calcsize(FLOAT_VECTOR))
        )

        self.bbox_info = Bbox(root_mesh.decode("utf-8"), bbox, bbox_max)

    def read_materials(self, f: BufferedReader):
        f.seek(self.p_material)

        n: int = struct.unpack("<I", f.read(4))[0]
        for _ in range(n):
            material_id, name_length = struct.unpack("<II", f.read(8))
            material_name = f.read(name_length).decode()
            material_name = material_name.replace("\\", "/")
            # print(material_name)
            material = BSRMaterial(material_id, material_name)
            self.materials.append(material)

    def read_meshes(self, f: BufferedReader):
        f.seek(self.p_mesh)

        n: int = struct.unpack("<I", f.read(4))[0]
        for _ in range(n):
            name_length = struct.unpack("<I", f.read(4))[0]
            mesh_name = f.read(name_length).decode()
            mesh_name = mesh_name.replace("\\", "/")

            flag = 0
            if self.is_prim_mesh:
                flag: int = struct.unpack("<I", f.read(4))[0]

            mesh = Mesh(mesh_name, flag=flag)
            self.meshes.append(mesh)

    def read(self, filepath: Path):

        self.__init__()

        print("[ BSRReader ] reading", filepath)

        with open(filepath, "rb") as f:
            _header = f.read(12)

            (
                self.p_material,
                self.p_mesh,
                self.p_skeleton,
                self.p_animation,
                self.p_mesh_group,
                self.p_animation_group,
                self.p_palette,
                self.p_bbox,
            ) = struct.unpack(POINTERS, f.read(struct.calcsize(POINTERS)))

            self.is_prim_mesh, self.has_mod_data, _, _, _ = struct.unpack(
                "<IIIII", f.read(4 * 5)
            )

            res_type, n = struct.unpack("<II", f.read(8))
            name = f.read(n)

            print(f"{res_type=} {name=}")

            self.read_bbox(f)

            self.read_materials(f)

            self.read_meshes(f)
            
        print("[ BSRReader ] succesful read")


if __name__ == "__main__":
    filepath = Path(
        "/home/miguel/python/blender_silkroad_importer/Silkroad_DATA-MAP/Data/res/bldg/europe/constantinople/euro_constan_inn01.bsr"
    )
    b = BSRReader()
    b.read(filepath)
