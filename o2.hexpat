struct MapObj{
    u32 id;
    float location[3]; // X coord (from left bottom corner of region)
    u16 is_static;
    float yaw; // Angle on Axis Y
    u16 uid; // Unique id of object, if same, object is not shown
    u16 short_0;
    bool is_big;
    bool is_struct;
    u16 region_id;
};

struct Lod {
    u16 object_count;
    MapObj obs[object_count];
};

struct MapBlock {
    Lod lod[4];
};

struct Ofile {
    char signature[12];
    MapBlock blocks[6*6];
};


Ofile file @ 0;