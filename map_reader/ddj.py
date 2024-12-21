from pathlib import Path
import struct


class DDJTextureReader:
    
    @staticmethod
    def convert_ddj_to_dds(filepath: Path) -> Path:
        if filepath.with_suffix(".dds").exists():
            return filepath.with_suffix(".dds")

        with open(filepath, "rb") as f:
            header = f.read(12)
            print(header)
            texture_size, texture_type = struct.unpack("<II", f.read(8))

            print(f"{texture_size=} {texture_type=}")

            data = f.read(texture_size - 8)

            with open(filepath.with_suffix(".dds"), "wb") as output:
                output.write(data)

            return filepath.with_suffix(".dds")


if __name__ == "__main__":
    d = DDJTextureReader()
    ddj_path = Path("Silkroad_DATA-MAP/Map/tile2d/oakk_dust_earth03.ddj")
    d.convert_ddj_to_dds(ddj_path)
