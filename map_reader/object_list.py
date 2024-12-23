from pathlib import Path


def read_object_list(path: Path) -> dict[int, str]:
    resources: dict[int, str] = {}

    with open(path, "rb") as f:
        lines = f.readlines()

    header = lines[0]
    num_objects = lines[1]

    print(header, num_objects)

    for line in lines[2:]:
        res_id, rest = line.split(b" ", 1)
        name = rest.split(b" ", 1)[-1]

        resources[int(res_id)] = (
            name.decode("latin-1").strip().strip('"').replace("\\", "/")
        )

    return resources
